"""职位详情库：抓过的不重抓，回填不覆盖。

## 为什么要这个库

抓一个职位本来一趟就够——详情接口返回的是搜索结果的**超集**，多一个 `description`。
但流程拆成了两趟（`/job-scrape` 取列表字段、`/job-rank` 抓 JD 正文），而**第二趟的结果用完就扔**。
实测：一批 137 份 JD 抓完躺在系统临时目录里，Windows 清一次就没了——那是 137 次请求、
三分多钟节流等待的成果。

## 这里盯的三件事

1. **「抓过」的判据是有正文**，不是有文件。只有 URL 和标题的文件不算——那些字段列表页
   就有；当成抓过会让 `/job-rank` 拿一句话去打分。
2. **一职位一文件，键用 `stable_id(url, title)`。** 不用 URL 当文件名：51job 实测同一个
   URL 下挂着两个不同职位，按 URL 存会互相覆盖，第二个职位的 JD 会顶掉第一个的。
3. **回填只补空缺。** 详情页确实比列表页权威，但静默改写一份已经拿来打过分的数据，
   会让「分数为什么变了」无从追查。不一致的如实报出来，让人看一眼。
   （实测 46 处不一致全是 `location`：详情给完整街道地址、列表给区。保住较短的那个
   反而是对的——面板上要显示的是「上海-浦东新区」，不是整条路名。）
"""

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import jd_store as st  # noqa: E402

BODY = "这是一段足够长的职位描述正文，用来通过 has_body 的长度判据。" * 3


class HasBodyIsAboutContentNotExistence(unittest.TestCase):
    def test_a_real_description_counts(self):
        self.assertTrue(st.has_body({"description": BODY}))

    def test_missing_or_empty_does_not_count(self):
        for d in (None, {}, {"description": None}, {"description": ""},
                  {"description": "   "}):
            self.assertFalse(st.has_body(d), f"{d} 不该算作抓过")

    def test_a_stub_does_not_count(self):
        """只有标题长度的占位不算——当成抓过会让 /job-rank 拿一句话去打分。"""
        self.assertFalse(st.has_body({"description": "AI产品经理，负责产品设计。"}))


class OneFilePerJobNotPerUrl(unittest.TestCase):
    def test_same_url_two_jobs_get_two_files(self):
        """51job 陷阱：按 URL 存会让第二个职位顶掉第一个的 JD。"""
        url = "https://jobs.51job.com/all/12345.html"
        self.assertNotEqual(st.key_for(url, "甲岗"), st.key_for(url, "乙岗"))

    def test_key_matches_the_id_the_page_uses(self):
        """与导出给页面的 id 必须是同一个函数算的，否则两边对不上。"""
        import export_web_data as ex
        url, title = "https://x/1", "某岗"
        self.assertEqual(st.key_for(url, title), ex.stable_id(url, title))


class _Repo:
    """临时仓库，用完还原 st.ROOT。"""

    def __enter__(self):
        self._t = tempfile.TemporaryDirectory()
        self.tmp = Path(self._t.name)
        (self.tmp / "users" / "张三" / "job_scraper").mkdir(parents=True)
        (self.tmp / ".active_user").write_text("张三", encoding="utf-8")
        self.sj = self.tmp / "users" / "张三" / "job_scraper" / "seen_jobs.json"
        self._saved = st.ROOT
        st.ROOT = self.tmp
        return self

    def __exit__(self, *a):
        st.ROOT = self._saved
        self._t.cleanup()

    def seen(self, entries):
        self.sj.write_text(json.dumps({"seen": entries}, ensure_ascii=False),
                           encoding="utf-8")

    def read(self):
        return json.loads(self.sj.read_text(encoding="utf-8"))["seen"]


class RoundTrip(unittest.TestCase):
    def test_save_then_load(self):
        with _Repo() as r:
            d = {"url": "https://x/1", "title": "某岗", "description": BODY}
            st.save("张三", d)
            got = st.load("张三", "https://x/1", "某岗")
            self.assertEqual(got["description"], BODY)

    def test_load_missing_returns_none(self):
        with _Repo():
            self.assertIsNone(st.load("张三", "https://x/nope", "无"))

    def test_half_written_file_is_treated_as_absent(self):
        """半截文件当作没有，重抓即可——比抛异常好。"""
        with _Repo() as r:
            st.save("张三", {"url": "https://x/1", "title": "某岗",
                             "description": BODY})
            p = st.store_dir("张三") / f"{st.key_for('https://x/1', '某岗')}.json"
            p.write_text("{不是合法 JSON", encoding="utf-8")
            self.assertIsNone(st.load("张三", "https://x/1", "某岗"))


class MergeFillsBlanksOnly(unittest.TestCase):
    def test_blank_fields_are_filled(self):
        with _Repo() as r:
            r.seen({"a": {"url": "https://x/1", "title": "某岗", "status": "new"}})
            st.save("张三", {"url": "https://x/1", "title": "某岗",
                             "description": BODY, "salary": "30-40k",
                             "salaryMonths": 14, "eduLevel": "本科"})
            st.merge_into_seen("张三", apply=True)
            e = r.read()["a"]
            self.assertEqual(e["salary"], "30-40k")
            self.assertEqual(e["salaryMonths"], 14)
            self.assertEqual(e["eduLevel"], "本科")

    def test_existing_values_are_never_overwritten(self):
        """**2026-08-23 起分两桶报，但一条都不许咽掉。**

        这份夹具（`上海-浦东新区` → `…某某路1528号A5座`）正是同一个地方的
        不同精度，现在归 `refined`；真的对不上的才进 `conflicts`
        （判据见 `jd_store.is_refinement`）。两个断言都留着 ——
        原来那条护的是「不能咽掉」，那个意图一个字没变。
        """
        with _Repo() as r:
            r.seen({"a": {"url": "https://x/1", "title": "某岗", "status": "new",
                          "location": "上海-浦东新区"}})
            st.save("张三", {"url": "https://x/1", "title": "某岗",
                             "description": BODY,
                             "location": "上海-浦东新区某某路1528号A5座"})
            out = st.merge_into_seen("张三", apply=True)
            self.assertEqual(r.read()["a"]["location"], "上海-浦东新区",
                             "已有值被详情覆盖了")
            self.assertEqual(out["refined"], {"location": 1},
                             "不一致要报出来，不能咽掉")
            self.assertEqual(out["conflicts"], [],
                             "同一个地方写得更细，不该报成矛盾")

    def test_a_value_that_really_differs_is_still_a_conflict(self):
        """换了城市要报 —— 跨城搬迁是一道 Pass/Fail 的门，判定会变。"""
        with _Repo() as r:
            r.seen({"a": {"url": "https://x/1", "title": "某岗", "status": "new",
                          "location": "上海-浦东新区", "salary": "15-20k",
                          "rank_verdict": "粗筛：跳过"}})
            st.save("张三", {"url": "https://x/1", "title": "某岗",
                             "description": BODY,
                             "location": "北京-朝阳区", "salary": "30-40k"})
            out = st.merge_into_seen("张三", apply=True)
            self.assertEqual(r.read()["a"]["salary"], "15-20k", "已有值被覆盖了")
            self.assertEqual({c["field"] for c in out["conflicts"]},
                             {"location", "salary"})
            self.assertTrue(all(c["judged"] for c in out["conflicts"]),
                            "判过的岗读到的一定是旧值，要标出来")

    def test_description_never_lands_in_seen_jobs(self):
        """正文留在详情库里。塞进 seen_jobs 会让它从 170KB 涨到 1.6MB，
        而那个文件每标一个「不投」都要整体重写。"""
        with _Repo() as r:
            r.seen({"a": {"url": "https://x/1", "title": "某岗", "status": "new"}})
            st.save("张三", {"url": "https://x/1", "title": "某岗",
                             "description": BODY, "salary": "30-40k"})
            st.merge_into_seen("张三", apply=True)
            self.assertNotIn("description", r.read()["a"])

    def test_dry_run_writes_nothing(self):
        with _Repo() as r:
            r.seen({"a": {"url": "https://x/1", "title": "某岗", "status": "new"}})
            st.save("张三", {"url": "https://x/1", "title": "某岗",
                             "description": BODY, "salary": "30-40k"})
            before = r.sj.read_text(encoding="utf-8")
            st.merge_into_seen("张三", apply=False)
            self.assertEqual(r.sj.read_text(encoding="utf-8"), before)


class ImportIsPicky(unittest.TestCase):
    def _src(self, files: dict) -> Path:
        d = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        for name, content in files.items():
            (d / name).write_text(content, encoding="utf-8")
        return d

    def test_err_files_and_bodyless_entries_are_not_imported(self):
        with _Repo():
            src = self._src({
                "good.json": json.dumps({"url": "https://x/1", "title": "甲",
                                         "description": BODY}, ensure_ascii=False),
                "nobody.json": json.dumps({"url": "https://x/2", "title": "乙"},
                                          ensure_ascii=False),
                "broken.json": "{不是 JSON",
                "failed.err": '{"error":"RATE_LIMITED"}',
            })
            r = st.import_dir("张三", src, apply=True)
            self.assertEqual(r["imported"], 1)
            self.assertEqual(r["no_body"], 1, "没正文的不能收，收了会让 /job-rank 以为抓过")
            self.assertEqual(r["skipped"], 1, "坏 JSON 应当跳过而不是让整批挂掉")
            self.assertIsNotNone(st.load("张三", "https://x/1", "甲"))
            self.assertIsNone(st.load("张三", "https://x/2", "乙"))

    def test_dry_run_imports_nothing(self):
        with _Repo():
            src = self._src({"good.json": json.dumps(
                {"url": "https://x/1", "title": "甲", "description": BODY},
                ensure_ascii=False)})
            r = st.import_dir("张三", src, apply=False)
            self.assertEqual(r["imported"], 1, "试运行也要如实报会收几份")
            self.assertIsNone(st.load("张三", "https://x/1", "甲"), "试运行不该落盘")


class StatusCountsWhatMatters(unittest.TestCase):
    def test_counts_only_entries_with_a_body(self):
        with _Repo() as r:
            r.seen({
                "a": {"url": "https://x/1", "title": "甲", "status": "new"},
                "b": {"url": "https://x/2", "title": "乙", "status": "new"},
                "c": {"url": "https://x/3", "title": "丙", "status": "ranked"},
            })
            st.save("张三", {"url": "https://x/1", "title": "甲", "description": BODY})
            st.save("张三", {"url": "https://x/2", "title": "乙"})   # 无正文
            s = st.status("张三")
            self.assertEqual(s["total"], 3)
            self.assertEqual(s["have"], 1)
            self.assertEqual(s["new_total"], 2)
            self.assertEqual(s["new_have"], 1, "无正文的不该算进「已有」")


if __name__ == "__main__":
    unittest.main()
