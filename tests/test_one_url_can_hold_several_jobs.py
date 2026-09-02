# -*- coding: utf-8 -*-
"""同一个链接挂着不同的岗，不是重复。

## 实测

`check_the_archive_was_consulted` 判「热库和存档各有一份」时只比 `norm_url`。
2026-08-30 它报了 6 个，**6 个全是同一链接、不同职位名**：

    AI应用工程师(J11182)          vs  数字电路设计工程师(J11077)
    后端开发（路网数据方向）实习生    vs  Android研发工程师-豆包输入法
    AI Agent 评测工程师           vs  AI Agent 工程师
    AI产品经理                    vs  Agent产品经理
    运营实习生（路网数据方向）       vs  Android研发工程师-豆包输入法
    AI架构师（百亿市值…）          vs  AI负责人（百亿市值…）

前程无忧的 `jobs.51job.com/all/<码>.html` 是**公司页不是职位页**
（`job-apply.md` 那张分流表里的「职位聚合页」说的就是它）。
一个都不是重复 —— 而报文写着「其中 5 个两边的结论已经不一样了」，
还给了「逐个看 `/job-apply <链接>`」：**6 次手工，去看 6 个不存在的问题。**

## 这是同一个形状的第五次

那条检查自己的 docstring 里数着前四次，共同点写得清清楚楚：
**「同一个岗有多把钥匙，而查重只试了其中一把」**。
而它自己**把两把钥匙当成了一把** —— 职位库的键是 `链接#职位名`，
`norm_url` 把后半截剥掉了。

## 判据对齐职位库

职位库的键怎么算，检查就怎么算。任一边没有职位名时只按链接判 ——
分不出来时宁可报，那是原来的行为。
"""
import json
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import _cli  # noqa: E402
import audit_pipeline as ap  # noqa: E402


#: 一看就像链接的名字。绑 `seen` 的键时不许用这些 —— 键是 `<url>#<职位名>`。
URLISH = ("url", "u", "link", "href", "job_url")


class TheKeyIsNotCalledAUrl(unittest.TestCase):
    """遍历职位库时，键不许起一个像链接的名字。

    实测 2026-08-31：全仓十来处 `for k, e in seen.items()`，**只有一处例外** ——
    `export_web_data.py` 写的是 `for url, e in seen.items()`，而那正是产出面板
    那份 `data.json` 的文件。同一个作用域里还躺着 `e["url"]`（真链接），
    于是 `e.get("url") or url` 读起来像「取链接，取不到再取链接」，实际是
    「取链接，取不到就拿键顶上」—— 键带着 `#职位名`，顶上去就是一个打不开的地址。

    **今天没出事**是因为 1839 条每一条都有 `url` 字段，那个 `or` 从没触发过。
    这条钉的是名字，不是那次侥幸。
    """

    def _loops(self):
        import re as _re
        out = []
        for f in sorted((ROOT / "tools").glob("*.py")):
            for m in _re.finditer(
                    r"for\s+([A-Za-z_]\w*)\s*,\s*\w+\s+in\s+"
                    r"(?:seen|store|library)\.items\(\)",
                    f.read_text(encoding="utf-8")):
                out.append((f.name, m.group(1)))
        return out

    def test_the_scan_finds_the_loops(self):
        """**先证明扫得到。** 一处都没收集到时下面那条永远绿。"""
        got = self._loops()
        self.assertGreaterEqual(len(got), 5,
                                f"只扫到 {got} —— 正则八成坏了")

    def test_none_of_them_is_named_like_a_link(self):
        bad = [f"{fn}: for {name}, ..." for fn, name in self._loops()
               if name.lower() in URLISH]
        self.assertEqual(
            bad, [],
            "职位库的键起了个像链接的名字（键是 <url>#<职位名>）："
            + "; ".join(bad))


class TheTitleIsPartOfTheIdentity(unittest.TestCase):

    def test_different_titles_are_different_jobs(self):
        self.assertFalse(ap._same_job({"title": "AI应用工程师(J11182)"},
                                      {"title": "数字电路设计工程师(J11077)"}))

    def test_the_same_title_is_the_same_job(self):
        """这条检查本来要抓的那件事：同一个岗被抓了两遍。"""
        self.assertTrue(ap._same_job({"title": "AI产品经理"},
                                     {"title": "AI产品经理"}))

    def test_whitespace_does_not_split_a_job(self):
        self.assertTrue(ap._same_job({"title": " AI产品经理 "},
                                     {"title": "AI产品经理"}))

    def test_a_missing_title_falls_back_to_the_link(self):
        """分不出来时宁可报 —— 那是补这一半之前的行为。"""
        self.assertTrue(ap._same_job({"title": ""}, {"title": "AI产品经理"}))
        self.assertTrue(ap._same_job({}, {}))


class TheCheckStillCatchesARealDuplicate(unittest.TestCase):
    """收窄判据不能把它本来的用处也收掉。"""

    def _run(self, hot, cold, tmp):
        import unittest.mock
        (tmp / "users" / "u" / "job_scraper").mkdir(parents=True)
        (tmp / "users" / "u" / "job_scraper" / "archive.json").write_text(
            json.dumps({"seen": cold}, ensure_ascii=False), encoding="utf-8")
        with unittest.mock.patch.object(ap, "ROOT", tmp), \
                unittest.mock.patch.object(ap, "_USER", ["u"]):
            return ap.check_the_archive_was_consulted(hot, {})

    def test_the_same_job_in_both_stores_is_reported(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            out = self._run(
                {"k1": {"url": "https://x/1.html", "title": "AI产品经理",
                        "rank_verdict": "可以考虑"}},
                {"k2": {"url": "https://x/1.html", "title": "AI产品经理",
                        "rank_verdict": "硬门 FAIL"}},
                pathlib.Path(d))
            self.assertTrue(out, "同一个岗两边都有，一个字都没报")
            self.assertIn("热库和存档", out[0][1])

    def test_two_jobs_at_one_url_are_not_reported(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            out = self._run(
                {"k1": {"url": "https://x/1.html", "title": "AI产品经理"}},
                {"k2": {"url": "https://x/1.html", "title": "数字电路设计工程师"}},
                pathlib.Path(d))
            self.assertEqual(out, [], "把两个不同的岗报成了同一个岗的两份")

    def test_it_scans_every_archived_job_at_that_url(self):
        """一个链接下存档里有好几个时，要逐个比 —— 不能只看碰上的第一个。"""
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            out = self._run(
                {"k1": {"url": "https://x/1.html", "title": "AI产品经理"}},
                {"k2": {"url": "https://x/1.html", "title": "别的岗"},
                 "k3": {"url": "https://x/1.html", "title": "AI产品经理"}},
                pathlib.Path(d))
            self.assertTrue(out, "存档里第二个才是同名的，漏掉了")


class NothingIsFlaggedRightNow(unittest.TestCase):
    """控制用例：这台机器上那 6 个确实都不是重复。"""

    def test_the_real_store_is_clean(self):
        ptr = ROOT / ".active_user"
        if not ptr.is_file():
            self.skipTest("没有活动用户")
        user = ptr.read_text(encoding="utf-8").strip()
        f = ROOT / "users" / user / "job_scraper" / "seen_jobs.json"
        if not f.is_file():
            self.skipTest("没有职位库")
        seen = _cli.seen_of(json.loads(f.read_text(encoding="utf-8")))
        arch = _cli.archived(user, root=ROOT)
        if not arch:
            self.skipTest("没有存档")
        cold = {}
        for v in arch.values():
            if isinstance(v, dict) and v.get("url"):
                cold.setdefault(_cli.norm_url(v["url"]), []).append(v)
        n = 0
        for v in seen.values():
            if not isinstance(v, dict) or not v.get("url"):
                continue
            if any(ap._same_job(v, c)
                   for c in cold.get(_cli.norm_url(v["url"]), [])):
                n += 1
        self.assertEqual(n, 0, f"真出现了 {n} 个两边都有的岗 —— 那是真问题，去看报文")


if __name__ == "__main__":
    unittest.main()
