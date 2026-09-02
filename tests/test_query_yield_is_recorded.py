"""搜到的岗要记下「是哪个词搜到的」，并且这份度量要能自动写回词表。

## 为什么这条值得钉住

`search-queries.md` 的词表**只在 `/job-setup` 那一次生成，之后再没人改过**。
实测：该文件的校准注释停在 2026-07-24，而候选人资料在 08-11 新增了「AI 提效 →
真实强项」这条判据——**新认定的强项一次都没被搜过**。临时补 6 个词，一轮多出 75 个
新岗；但那 6 个词没有任何地方存着，下一轮又退回旧表。

更隐蔽的是**度量缺失**：库里 991 个岗，没有一个记着来源，于是「哪个词管用」只能
靠回忆。补上 `found_by` 当轮就发现回忆是错的——按新增数排，`数字员工` 39 个高居第一，
可它的高匹配只有 2 个（5%），`流程自动化` 18 个里**一个高匹配都没有**。
之前的报告把它们当成高产词，**因为当时只有数量这一个指标**。

所以三条一起钉：字段要存、工具要能量、流程要真的调用它。
"""

import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import query_yield as qy  # noqa: E402

WF = ROOT / "workflows" / "job-scrape.md"


class TheSchemaCarriesTheQuery(unittest.TestCase):

    def test_scrape_schema_lists_found_by(self):
        t = WF.read_text(encoding="utf-8")
        self.assertIn('"found_by"', t,
                      "seen_jobs 的 schema 没列 found_by —— 落库时就会像原来一样丢掉，"
                      "「哪个词管用」重新变成不可测")

    def test_the_workflow_actually_calls_the_tool(self):
        """有工具没人调 = 没有工具。这正是 gaps 字段栽过的坑。"""
        t = WF.read_text(encoding="utf-8")
        self.assertIn("tools/query_yield.py --apply", t,
                      "流程里没有调用 query_yield —— 词表又回到「只生成一次」")

    def test_step1_tells_you_to_read_the_measured_block(self):
        t = WF.read_text(encoding="utf-8")
        self.assertIn("QUERY-YIELD", t,
                      "Step 1 没让人先看实测产出，下一轮还是照着旧词表原样重跑")


class TheToolMeasuresWhatItClaims(unittest.TestCase):

    SEEN = {
        "a": {"found_by": "智能体开发", "portal": "liepin-search", "fit": "high"},
        "b": {"found_by": "智能体开发", "portal": "liepin-search", "fit": "high"},
        "c": {"found_by": "数字员工", "portal": "liepin-search", "fit": "low"},
        "d": {"found_by": "数字员工", "portal": "51job", "fit": "low"},
        "e": {"found_by": "数字员工", "portal": "51job-cdp", "fit": "low"},
        "f": {"portal": "liepin-search", "fit": "high"},          # 早期抓的，没来源
    }

    def test_missing_provenance_is_counted_not_hidden(self):
        """没来源的要如实报出来——把 324/991 说成全部，比不报更糟。"""
        by, have, miss = qy.collect(self.SEEN)
        self.assertEqual((have, miss), (5, 1))

    def test_portal_aliases_are_merged(self):
        """`51job` 与 `51job-cdp` 是同一家。不归一，同一平台被拆成两列，
        每列都显得产出很低，然后好词被误判成没用。"""
        by, _, _ = qy.collect(self.SEEN)
        self.assertEqual(len(by["数字员工"]["前程无忧"]), 2)
        self.assertNotIn("51job-cdp", by["数字员工"])

    def test_quality_beats_quantity_in_the_keep_list(self):
        """数量多但高匹配少的词不许进「下一轮优先跑」——这正是本文件开头那个错。"""
        seen = {str(i): {"found_by": "数字员工", "portal": "liepin-search",
                         "fit": "low"} for i in range(40)}
        seen.update({f"h{i}": {"found_by": "智能体开发", "portal": "liepin-search",
                               "fit": "high"} for i in range(6)})
        by, _, _ = qy.collect(seen)
        _, keep = qy.render(by)
        names = [q for q, *_ in keep]
        self.assertIn("智能体开发", names)
        self.assertNotIn("数字员工", names,
                         "40 个新增、0 个高匹配的词被当成了达标——又在拿数量当产出")

    def test_a_column_never_run_is_a_dash_not_a_zero(self):
        """`—`（没跑过）和 `0`（跑了没产出）是两回事，混同会把还能用的词删掉。"""
        by, _, _ = qy.collect(self.SEEN)
        table, _ = qy.render(by)
        row = next(l for l in table.splitlines() if l.startswith("| 智能体开发"))
        self.assertIn("—", row, "没跑过的平台被写成了数字")

    def test_a_zero_yield_run_is_recorded_not_forgotten(self):
        """跑了返回 0 条，也必须留痕——否则会被永远重复推荐。

        实测：`AI应用落地` 在猎聘返回 0 条。0 条就没有条目、没有 `found_by`，
        那一格仍显示 `—`（没跑过），于是「最值钱的空格子」清单下一轮又把它列出来。
        本文件另一条测试专门守住 `—` 不能写成 `0`；这一条守住反面——**跑过就不能
        再显示成没跑过**。两条缺一，表给的建议就是错的。
        """
        doc = {"query_log": [{"query": "AI应用落地", "portal": "liepin-search"}]}
        pairs = qy.ran(doc)
        self.assertIn(("AI应用落地", "猎聘"), pairs, "query_log 的平台名没归一")
        table, _ = qy.render({}, pairs)
        row = next(l for l in table.splitlines() if l.startswith("| AI应用落地"))
        cells = [c.strip() for c in row.strip("|").split("|")]
        self.assertEqual(cells[1], "0", "跑过且零产出的格子应该是 0，不是 —")
        self.assertEqual(cells[2], "—", "没跑过的格子应该是 —，不是 0")

    def test_a_run_query_is_dropped_from_the_gap_list(self):
        """空格子清单是行动项。跑过的还留在里面 = 每轮重跑同一个死词。"""
        by = {"x": {"猎聘": [{"fit": "high"}] * 6}}
        ran_pairs = {("x", "前程无忧")}
        gaps = [(q, p) for q, *_ in qy.render(by, ran_pairs)[1]
                for p in qy.PORTALS if p not in by.get(q, {}) and (q, p) not in ran_pairs]
        self.assertNotIn(("x", "前程无忧"), gaps)
        self.assertIn(("x", "BOSS"), gaps)

    def test_account_expectation_never_reaches_the_runnable_block(self):
        """`-q "账号求职期望(...)"` 粘到 CLI 只会报错。它进表、不进可执行块。"""
        self.assertFalse(qy.is_runnable("账号求职期望(AI产品经理)"))
        self.assertTrue(qy.is_runnable("智能体开发"))
        block = qy.build_block(
            {"账号求职期望(AI产品经理)": {"BOSS": [{"fit": "high"}] * 8}}, "2026-08-11", 0)
        run = block.split("```")[1]
        self.assertNotIn("账号求职期望", run)


class TheWriteBackIsIdempotent(unittest.TestCase):
    """幂等是硬要求：每轮 /job-scrape 都会跑一次，不幂等就会越写越长。"""

    HEAD = "# 查询\n\n## 查询分类\n\n### 优先级 1\n\n```\n-q \"x\" -l \"上海\"\n```\n"

    def test_first_insert_goes_under_the_right_heading(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "search-queries.md"
            p.write_text(self.HEAD, encoding="utf-8")
            block = qy.build_block({"x": {"猎聘": [{"fit": "high"}] * 6}}, "2026-08-11", 0)
            out = qy.write_back(p, block)
            self.assertIn("## 查询分类", out)
            self.assertIn(qy.BEGIN, out)
            self.assertIn("### 优先级 1", out, "人工维护的那块被吃掉了")

    def test_second_run_replaces_instead_of_appending(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "search-queries.md"
            p.write_text(self.HEAD, encoding="utf-8")
            b1 = qy.build_block({"x": {"猎聘": [{"fit": "high"}] * 6}}, "2026-08-11", 0)
            p.write_text(qy.write_back(p, b1), encoding="utf-8")
            b2 = qy.build_block({"y": {"猎聘": [{"fit": "high"}] * 6}}, "2026-08-12", 0)
            out = qy.write_back(p, b2)
            self.assertEqual(out.count(qy.BEGIN), 1, "重复插入了自动维护块")
            self.assertIn("2026-08-12", out)
            self.assertNotIn("2026-08-11", out, "旧内容没被替换掉")
            self.assertIn("### 优先级 1", out, "人工维护的那块被吃掉了")


class TheToolRunsOnTheRealRepo(unittest.TestCase):
    """控制测试：合成样例永远长成解析器认识的样子，真数据才会打脸。"""

    def test_dry_run_exits_clean(self):
        """**要有真数据才跑得动。** 没有活动用户时 `query_yield.py` 以 1 退出
        并说「还没有活动用户」——那是它该有的行为，不是失败。

        原来这里无条件断言退出码 0，于是干净 clone 上必红（2026-08-20 实测）。
        控制测试的价值在「拿真数据打脸合成样例」，没有真数据时它没有价值，
        跳过即可；有真数据时判据一个字不放松。
        """
        ptr = ROOT / ".active_user"
        user = ptr.read_text(encoding="utf-8").strip() if ptr.is_file() else ""
        if not user or not (ROOT / "users" / user / "job_scraper"
                            / "seen_jobs.json").is_file():
            self.skipTest("没有活动用户或职位库 —— 这条要拿真数据跑")
        r = subprocess.run([sys.executable, "tools/query_yield.py"],
                           cwd=ROOT, capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("试运行", r.stdout, "试运行没说自己是试运行——可能已经写盘了")


if __name__ == "__main__":
    unittest.main()
