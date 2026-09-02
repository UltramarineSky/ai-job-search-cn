# -*- coding: utf-8 -*-
"""两套记账靠的都是「流程文档写一句、AI 记得做」—— 而这正是本文件反对的做法。

`query_yield` 开头就点了病名：

> 这跟 `writeback.py` 治的是同一个病，那里的原话是「**写回靠工具，不靠纪律**」：
> 指望流程文档写一句「记得把好用的词存下来」，AI 漏一步就白干。

可 `found_by`（每个岗记哪个词搜到的）和 `query_log`（每组查询留一笔）本身
就是两条**只写在 `job-scrape.md` 里的纪律**：没有工具替它们写，也没有任何
地方检查有没有写。

实测活动用户 2026-08-23，按日对账：

    日期        新岗   query_log   found_by 覆盖
    08-11       507      34         77%
    08-12       274      15        100%
    08-13        56       0        100%    ← 查询记录整天没留
    08-14       186       0          0%    ← 两套一起丢
    08-17      1008     122        100%
    08-19       198      22        100%

**08-14 两套一起丢，9 天没人发现。08-13 只丢了一套** —— 只查 `found_by`
根本看不见它。

## 为什么这不是记账洁癖

`query_log` 的用途写在 `ran()` 的注释里：区分表里的 `0`（跑了没产出）和
`—`（还没跑过）。零产出的查询不留下任何岗，所以也没有 `found_by`；
只要那一格还是 `—`，「下一轮最值钱的格子」就会**永远推荐它**，
而抓取额度是这套系统里最稀缺的（每次请求之间要隔 8/4/3 秒、撞了风控整站冷却 24 小时）。

## 报在哪儿

`/job-scrape` Step 4.6 每轮收尾都跑本工具 —— 那是唯一还补得回来的时机：
AI 此刻仍记得哪个词搜到了什么。所以这句话走 **stderr、放最前面**，
不埋进写回块的脚注。**不改退出码**：`/job-auto` 把这一步串在链子里。
"""
import json
import pathlib
import re
import subprocess
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import query_yield as qy  # noqa: E402

QY = (ROOT / "tools" / "query_yield.py").read_text(encoding="utf-8")


def flat(s: str) -> str:
    s = " ".join(re.sub(r"^\s*>\s?", "", s, flags=re.M).split())
    return re.sub(r"(?<=[一-鿿，。；：、（）「」])"
                  r" +(?=[一-鿿，。；：、（）「」])", "", s)


def doc_of(spec: dict) -> dict:
    """`{日期: (新岗数, query_log 条数)}` → 一份最小的职位库。"""
    seen, log, i = {}, [], 0
    for day, (jobs, logs) in spec.items():
        for _ in range(jobs):
            seen[f"k{i}"] = {"first_seen": day, "found_by": "某词"}
            i += 1
        for j in range(logs):
            log.append({"query": f"词{j}", "portal": "liepin-search",
                        "date": day, "rows": 3, "new": 1})
    return {"seen": seen, "query_log": log}


class ADayWithJobsButNoLogIsFlagged(unittest.TestCase):
    def test_a_clean_day_says_nothing(self):
        self.assertEqual(qy.unlogged_rounds(doc_of({"2026-08-12": (20, 5)})), {})

    def test_a_day_with_jobs_and_no_log_is_named(self):
        got = qy.unlogged_rounds(doc_of({"2026-08-12": (20, 5),
                                         "2026-08-14": (186, 0)}))
        self.assertEqual(got, {"2026-08-14": 186})

    def test_it_catches_the_day_found_by_misses(self):
        """08-13 那天 `found_by` 全有、`query_log` 全无 —— 只查前者看不见。"""
        doc = doc_of({"2026-08-12": (20, 5), "2026-08-13": (56, 0)})
        self.assertEqual(qy.unlogged_rounds(doc), {"2026-08-13": 56})
        self.assertEqual(qy.late_misses(doc["seen"])[0], 0,
                         "这一天 found_by 是齐的 —— 两个检查各管各的")

    def test_several_days_are_all_listed(self):
        got = qy.unlogged_rounds(doc_of({"2026-08-12": (20, 5),
                                         "2026-08-13": (56, 0),
                                         "2026-08-14": (186, 0)}))
        self.assertEqual(got, {"2026-08-13": 56, "2026-08-14": 186})

    def test_days_before_the_first_log_are_history(self):
        """`query_log` 这个机制上线之前抓的，补不上，不许报。"""
        got = qy.unlogged_rounds(doc_of({"2026-07-30": (150, 0),
                                         "2026-08-11": (507, 34)}))
        self.assertEqual(got, {})

    def test_a_tiny_day_is_not_worth_reporting(self):
        """抓到三五个的一次补漏，没留记录说明不了什么。"""
        got = qy.unlogged_rounds(doc_of({"2026-08-12": (20, 5),
                                         "2026-08-15": (3, 0)}))
        self.assertEqual(got, {})

    def test_no_log_at_all_means_no_boundary(self):
        self.assertEqual(qy.unlogged_rounds(doc_of({"2026-08-12": (20, 0)})), {})

    def test_the_archived_jobs_still_count(self):
        """归档会把某天的岗数拉到门槛以下，那天的漏记就消失了。"""
        doc = doc_of({"2026-08-12": (20, 5), "2026-08-14": (2, 0)})
        merged = dict(doc["seen"])
        for i in range(200):
            merged[f"cold{i}"] = {"first_seen": "2026-08-14",
                                  "found_by": "某词"}
        self.assertEqual(qy.unlogged_rounds(doc), {},
                         "只看热库时本来就该是空的")
        self.assertEqual(qy.unlogged_rounds(doc, merged), {"2026-08-14": 202})

    def test_junk_entries_do_not_crash(self):
        doc = doc_of({"2026-08-12": (20, 5), "2026-08-14": (20, 0)})
        doc["seen"]["junk"] = "字符串"
        self.assertEqual(qy.unlogged_rounds(doc), {"2026-08-14": 20})


class TheWarningIsLoudAndActionable(unittest.TestCase):
    def _run(self, doc: dict, tmp: pathlib.Path):
        (tmp / "job_scraper").mkdir(parents=True, exist_ok=True)
        (tmp / "profile").mkdir(parents=True, exist_ok=True)
        (tmp / "job_scraper" / "seen_jobs.json").write_text(
            json.dumps(doc, ensure_ascii=False), encoding="utf-8")
        (tmp / "profile" / "search-queries.md").write_text(
            "# 搜索词\n", encoding="utf-8")
        return subprocess.run(
            [sys.executable, "-X", "utf8", str(ROOT / "tools" / "query_yield.py"),
             "--user", tmp.name],
            capture_output=True, text=True, cwd=str(ROOT))

    def test_it_goes_to_stderr_not_the_table(self):
        i = QY.index("这份职位库有几笔抓取没留下记账")
        self.assertIn("file=sys.stderr", QY[i:i + 200])

    def test_it_is_printed_before_the_table(self):
        self.assertLess(QY.index("这份职位库有几笔抓取没留下记账"),
                        QY.index("有来源的 {have} 个"))

    def test_it_names_both_kinds(self):
        i = QY.index("这份职位库有几笔抓取没留下记账")
        seg = QY[i:i + 1200]
        self.assertIn("没记「是哪个词搜到的」", seg)
        self.assertIn("抓了岗却没留查询记录", seg)

    def test_it_says_what_the_missing_log_costs(self):
        i = QY.index("抓了岗却没留查询记录")
        seg = flat(QY[i:i + 400])
        self.assertRegex(seg, r"一直显示成「还没跑过」")
        self.assertRegex(seg, r"下一轮还会再推荐一遍")

    def test_it_points_at_where_the_rule_is(self):
        i = QY.index("这份职位库有几笔抓取没留下记账")
        self.assertIn("workflows/job-scrape.md", QY[i:i + 1400])

    def test_it_stays_silent_when_the_books_are_clean(self):
        i = QY.index("gaps = unlogged_rounds(")
        self.assertIn("if late_n or gaps:", QY[i:i + 200],
                      "没有漏记时也会印一段 —— 那就成了每轮的噪音")

    def test_the_exit_code_is_not_touched(self):
        """`/job-auto` 把这一步串在链子里，非 0 会让整条链停在数据问题上。"""
        i = QY.index("这份职位库有几笔抓取没留下记账")
        seg = QY[max(0, i - 900):i]
        self.assertIn("不改退出码", seg)
        self.assertNotIn("return 1", QY[i:i + 1400])

    def test_it_says_why_now_and_not_later(self):
        i = QY.index("这份职位库有几笔抓取没留下记账")
        seg = flat(QY[max(0, i - 900):i].replace("#", " "))
        self.assertRegex(seg, r"AI 此刻还记得哪个词搜到了什么，补得回来")
        self.assertRegex(seg, r"Step 4\.6 每轮收尾都跑本工具")


class TheRuleItEnforcesIsStillWritten(unittest.TestCase):
    """检查在、规则不在，和规则在、检查不在，是同一个病的两面。"""

    DOC = (ROOT / "workflows" / "job-scrape.md").read_text(encoding="utf-8")

    def test_the_found_by_section_exists(self):
        self.assertIn("### ⚠️ `found_by`：不记来源，就永远不知道哪个词管用",
                      self.DOC)

    def test_the_query_log_section_exists(self):
        self.assertIn("### ⚠️ `query_log`：跑过就要留痕，哪怕一条都没搜到",
                      self.DOC)

    def test_the_zero_yield_case_is_still_spelled_out(self):
        seg = flat(self.DOC[self.DOC.index("### ⚠️ `query_log`"):][:900])
        self.assertRegex(seg, r"零产出的那些\*\*尤其\*\*要记")
        self.assertRegex(seg, r"永远推荐下去")

    def test_the_tool_still_runs_every_round(self):
        """报在收尾那一步 —— 接线断了，这两个检查就永远不会被人看到。"""
        self.assertIn("python tools/query_yield.py --apply", self.DOC)
        auto = (ROOT / "workflows" / "job-auto.md").read_text(encoding="utf-8")
        self.assertIn("python tools/query_yield.py --apply", auto)


class TheReasonIsRecorded(unittest.TestCase):
    def _doc(self) -> str:
        i = QY.index("def unlogged_rounds(")
        return flat(QY[i:QY.index("    logs: dict = defaultdict", i)])

    def test_it_carries_the_two_shapes(self):
        seg = self._doc()
        self.assertRegex(seg, r"08-13 56 个岗 · found_by 全有 · query_log \*\*0 条\*\*")
        self.assertRegex(seg, r"08-14 186 个岗 · found_by \*\*全无\*\*")
        self.assertIn("2026-08-23", seg)

    def test_it_says_why_found_by_alone_is_not_enough(self):
        self.assertRegex(self._doc(), r"只查 `found_by` 会漏掉 08-13 那一天")

    def test_it_says_it_is_not_bookkeeping_for_its_own_sake(self):
        seg = self._doc()
        self.assertRegex(seg, r"这不是记账洁癖")
        self.assertRegex(seg, r"抓取额度是这套系统里最稀缺的")

    def test_it_explains_the_merged_seen(self):
        self.assertRegex(self._doc(), r"归档的岗 也算它那天抓到过"
                                      r"|归档的岗也算它那天抓到过")


class TheSignalItLeansOnIsReal(unittest.TestCase):
    """有语料时验一次：这两个检查在真实库上确实各抓到东西。"""

    def _doc(self):
        p = ROOT / ".active_user"
        if not p.is_file():
            self.skipTest("没有活动用户")
        u = p.read_text(encoding="utf-8").strip()
        f = ROOT / "users" / u / "job_scraper" / "seen_jobs.json"
        if not f.is_file():
            self.skipTest("没有职位库")
        d = json.loads(f.read_text(encoding="utf-8"))
        if len(d.get("seen") or {}) < 500 or not d.get("query_log"):
            self.skipTest("语料太小或还没有查询记录")
        return d

    def test_the_mechanism_is_in_use_at_all(self):
        """`query_log` 一条都没有的话，这个检查没有界线可用。"""
        self.assertTrue(self._doc().get("query_log"))

    def test_the_two_checks_do_not_report_the_same_set(self):
        """报的是同一批的话，其中一个就是多余的。"""
        d = self._doc()
        late = set(qy.late_misses(d["seen"])[1])
        gaps = set(qy.unlogged_rounds(d))
        if not late or not gaps:
            self.skipTest("这份库里有一侧是干净的")
        self.assertNotEqual(late, gaps,
                            "两个检查报出完全相同的日子 —— 合成一个就行了")


if __name__ == "__main__":
    unittest.main()
