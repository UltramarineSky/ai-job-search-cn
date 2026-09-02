# -*- coding: utf-8 -*-
"""报告推荐「AI原生 p2 × 前程无忧」—— `p2` 是页码，这条指令跑不了。

`query_yield` 的产出表一页一行（`研发效能`、`研发效能 p6`、`研发效能 p7`…），
那是有意的：翻到第几页、哪一页开始颗粒无收，是真信息。**但结论不该跟着行走。**

此前三段结论里只有「该停一停的词」把翻页并回了主词，而且它的注释已经写清了理由
（一个词拆成七八行，每行都不够门槛，于是永远报不出来）。「达标」和
「下一轮最值钱的格子」没并 —— **同一份报告里两个分母**。

代价实测（2026-08-23，活动用户）：不并时达标 3 个词，其中两个是**页**：

    AI原生 p2      16 抓 4 高匹配 = 25% ✓     而 AI原生 整词 50 抓 6 = 12%
    企业AI应用 p3  10 抓 4 高匹配 = 40% ✓     而整词 87 抓 11 = 13%

于是 9 个推荐格子里 **6 个建立在一页的运气上**，而且那 6 条粘进 CLI 会搜到空
（`-q "AI原生 p2"` 搜的是这个字符串本身）。`is_runnable` 本来就是为
「粘进 CLI 只会报错」的来源设的，但它只挡了「账号求职期望(…)」那一类。

方向也说得通：扩到一个新平台时跑的是**词**、从第 1 页开始，
所以能预测产出的是整词的命中率，不是某一页的。
"""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tests"))
import query_yield as Q  # noqa: E402
from _srcscan import strip_comments  # noqa: E402


def _rows(n, hi):
    """造 n 个条目，其中 hi 个算高匹配。判高低走 `is_high`，这里给判词。"""
    out = [{"rank_verdict": "值得投", "status": "ranked"} for _ in range(hi)]
    out += [{"rank_verdict": "不建议", "status": "ranked"} for _ in range(n - hi)]
    return out


class PagesFoldBackIntoTheWord(unittest.TestCase):
    def test_base_query_strips_the_page(self):
        for raw, want in (("研发效能 p6", "研发效能"), ("MCP p4", "MCP"),
                          ("AI原生", "AI原生"), ("AI赋能 p10", "AI赋能")):
            with self.subTest(raw=raw):
                self.assertEqual(Q.base_query(raw), want)

    def test_it_does_not_eat_a_real_word(self):
        """`p` 开头的词是真的（`p8` 职级、`SAP p2p`）。只剥**结尾**那个 ` pN`。"""
        for raw in ("p2p支付", "SAP", "GPT-4", "AI p"):
            with self.subTest(raw=raw):
                self.assertEqual(Q.base_query(raw), raw)

    def test_merge_pages_sums_across_pages_and_portals(self):
        by = {"甲": {"猎聘": _rows(10, 1)},
              "甲 p2": {"猎聘": _rows(6, 4), "BOSS": _rows(4, 0)},
              "乙": {"猎聘": _rows(3, 3)}}
        m = Q.merge_pages(by)
        self.assertEqual(sorted(m), ["乙", "甲"])
        self.assertEqual(len(m["甲"]["猎聘"]), 16)
        self.assertEqual(len(m["甲"]["BOSS"]), 4)


class TheQualifyingListJudgesWordsNotPages(unittest.TestCase):
    def test_a_lucky_page_does_not_qualify_the_word(self):
        """实测那个形状：整词 12%，其中一页 25%。"""
        by = {"甲": {"猎聘": _rows(34, 2)},
              "甲 p2": {"猎聘": _rows(16, 4)}}
        _table, keep = Q.render(by)
        self.assertEqual([k[0] for k in keep], [],
                         "一页的运气把整词 12% 的词判成了达标")

    def test_a_word_split_across_pages_can_still_qualify(self):
        """反过来那一半：每页都不够 MIN_NEW，合起来够。
        这正是停用清单那段注释早就写下的理由。"""
        by = {"甲": {"猎聘": _rows(3, 2)},
              "甲 p2": {"猎聘": _rows(3, 1)},
              "甲 p3": {"猎聘": _rows(2, 1)}}
        _table, keep = Q.render(by)
        self.assertEqual([k[0] for k in keep], ["甲"])
        self.assertEqual(keep[0][1], 8, "合计没把三页加起来")

    def test_the_kept_name_never_carries_a_page(self):
        by = {"甲 p2": {"猎聘": _rows(8, 4)}}
        _table, keep = Q.render(by)
        self.assertEqual([k[0] for k in keep], ["甲"])

    def test_the_table_still_shows_one_row_per_page(self):
        """并的是结论，不是表。翻页深度是真信息，不许一起并掉。"""
        by = {"甲": {"猎聘": _rows(4, 0)}, "甲 p2": {"猎聘": _rows(4, 0)}}
        table, _keep = Q.render(by)
        self.assertIn("| 甲 |", table)
        self.assertIn("| 甲 p2 |", table)


class TheRecommendationIsRunnable(unittest.TestCase):
    def _gaps(self, by, ran=frozenset()):
        """**打生产函数，不许抄一份。** 第一版在这里照抄了 `main` 里那段逻辑，
        于是把生产代码改回不折页，这一族照样全绿（变异实测抓到 2 条空转）。
        为此把那段逻辑抽成了 `next_cells`。"""
        _t, keep = Q.render(by, ran)
        return Q.next_cells(by, keep, ran)

    def test_no_cell_names_a_page(self):
        by = {"甲 p2": {"猎聘": _rows(8, 4)}}
        for q, _p in self._gaps(by):
            with self.subTest(q=q):
                self.assertNotRegex(q, r"\sp\d+$", "推荐了一条带页码的查询")

    def test_a_portal_reached_only_via_a_later_page_is_not_a_gap(self):
        """`AI原生 p2` 在猎聘跑过，就说明 `AI原生` 在猎聘跑过。
        不折页的话会推荐一个已经挖过的格子。"""
        by = {"甲": {"BOSS": _rows(8, 4)}, "甲 p2": {"猎聘": _rows(2, 1)}}
        got = {p for _q, p in self._gaps(by)}
        self.assertNotIn("猎聘", got, "把已经挖过的平台又推荐了一遍")

    def test_ran_pairs_are_folded_too(self):
        """跑过但零产出的格子记在 `ran_pairs` 里，同样按主词折。"""
        by = {"甲": {"BOSS": _rows(8, 4)}}
        got = {p for _q, p in self._gaps(by, ran={("甲 p3", "智联")})}
        self.assertNotIn("智联", got)

    def test_the_account_expectation_guard_survives(self):
        """`is_runnable` 原来那半（账号求职期望不能当查询词）不许被带掉。"""
        self.assertFalse(Q.is_runnable("账号求职期望(AI产品经理)"))
        self.assertTrue(Q.is_runnable("AI应用产品经理"))

    def test_the_real_report_recommends_nothing_with_a_page(self):
        """跑真数据兜底 —— 构造数据能造出对的形状，也能造漏。"""
        import contextlib
        import io
        if not (ROOT / ".active_user").is_file():
            self.skipTest("没有活动用户")
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                Q.main([])
        except SystemExit:
            pass
        out = buf.getvalue()
        if "最值钱的格子" not in out:
            self.skipTest("这份数据没有推荐块")
        block = out[out.index("最值钱的格子"):]
        block = block[:block.index("\n\n")] if "\n\n" in block else block
        bad = [ln for ln in block.splitlines() if re.search(r"\sp\d+\s*×", ln)]
        self.assertEqual(bad, [], f"报告里仍有带页码的推荐：{bad}")


class OneDenominatorPerReport(unittest.TestCase):
    """三段结论必须共用一份合并视图 —— 各写各的就等着它们分叉，
    这次的 bug 就是「停用清单并了、另外两段没并」。"""

    SRC = (ROOT / "tools" / "query_yield.py").read_text(encoding="utf-8")

    def test_the_page_regex_is_defined_once(self):
        code = strip_comments(self.SRC)
        self.assertEqual(code.count(r'p\d+$'), 1,
                         "翻页正则又被抄了一份，两处迟早认得不一样")

    def test_every_conclusion_goes_through_merge_pages(self):
        code = strip_comments(self.SRC)
        self.assertGreaterEqual(code.count("merge_pages("), 4,
                                "有结论没走合并视图（定义 1 + 达标/停用/空格子 各 1）")

    def test_main_actually_calls_the_extracted_function(self):
        """**结构断言，因为行为断言够不着。** 上面那一族打的是 `next_cells`；
        有人把它在 `main` 里内联回一份自己的实现，那一族照样全绿
        （变异实测确认过）。而真实数据里达标的词恰好不带页码，
        跑 `main` 也看不出来。所以这里盯「`main` 有没有在用它」。"""
        code = strip_comments(self.SRC)
        i = code.index("def main(")
        self.assertIn("next_cells(", code[i:], "main 又自己拼了一份空格子逻辑")

    def test_the_reason_is_written_down(self):
        """一个合并函数看着像重构，理由不挨着写就会被下一版摊平回去。"""
        i = self.SRC.index("def merge_pages(")
        seg = self.SRC[i:i + 1600]
        self.assertIn("表格照旧一页一行", seg)
        self.assertRegex(seg, r"AI原生 p2 × 前程无忧|这条指令跑不了")
        self.assertRegex(seg, r"6 个建立在一页的运气上", "没留下实测的量")


if __name__ == "__main__":
    unittest.main()
