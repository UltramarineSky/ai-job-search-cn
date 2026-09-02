# -*- coding: utf-8 -*-
"""写手把一条写长了就会换行，而逐行匹配的解析器只拿得到第一行。

    1. **专业这条卡得严吗？**（JD 写「计算机科学、人工智能…等相关专业背景」，
       而你是历史学本科——这是本岗唯一的真门槛风险）

第二行既不是新项也不是标题，`re.match(r"\\s*[-*]\\s+(.+)", ln)` 认不出来，
被 `continue` 丢掉。**面板上于是出现断在逗号上、引号配不上对的句子** ——
自检「面板上有句子断在半截」报的 21 处里，`askBefore` 11 处、`gaps` 9 处
全是这么来的（实测 2026-08-30；接上 `_list_items` 之后 21 → 2，
剩下那 2 处是源文本自己就不配对，不是解析器造的）。

伤在哪：那一栏面板上叫「投之前先问清」——用户**照着它去问**，而问题本身停在半句。
"""
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import export_web_data as ex  # noqa: E402


def items(text):
    return list(ex._list_items(text.splitlines()))


class AWrappedItemComesBackWhole(unittest.TestCase):
    def test_the_continuation_is_joined(self):
        t = ("1. **专业这条卡得严吗？**（JD 写「计算机科学、人工智能」，\n"
             "   而你是历史学本科）\n"
             "2. 另一条\n")
        got = items(t)
        self.assertEqual(len(got), 2)
        self.assertIn("而你是历史学本科）", got[0])
        for a, b in (("「", "」"), ("（", "）")):
            self.assertEqual(got[0].count(a), got[0].count(b), got[0])

    def test_three_lines_join_too(self):
        t = "- 第一行，\n  第二行，\n  第三行。\n"
        self.assertEqual(items(t), ["第一行， 第二行， 第三行。"])

    def test_a_blank_line_ends_the_item(self):
        """空行之后是新段落 —— 接过去会把不相干的话粘进问题里。"""
        t = "- 一条问题\n\n随后一段正文\n"
        self.assertEqual(items(t), ["一条问题"])

    def test_a_new_bullet_ends_the_item(self):
        t = "- 甲\n- 乙\n"
        self.assertEqual(items(t), ["甲", "乙"])

    def test_headings_and_table_rows_are_not_continuations(self):
        t = "- 甲\n## 标题\n| a | b |\n"
        self.assertEqual(items(t), ["甲"])

    def test_numbered_and_dashed_both_count(self):
        for t in ("1. 甲\n", "1、甲\n", "1) 甲\n", "- 甲\n", "* 甲\n"):
            with self.subTest(t=t.strip()):
                self.assertEqual(items(t), ["甲"])

    def test_an_unindented_line_is_not_a_continuation(self):
        """顶格的下一行是新段落，不是续行 —— 不然会把整节正文吸进第一条。"""
        t = "- 甲\n这是另起一段的正文\n"
        self.assertEqual(items(t), ["甲"])


class BothParsersUseIt(unittest.TestCase):
    def test_ask_before_joins(self):
        t = ("## 投前必问\n\n"
             "1. 这条卡得严吗？（JD 写「A、B」，\n"
             "   而你是 C）\n")
        got = ex.parse_ask_before(t)
        self.assertEqual(len(got), 1)
        self.assertIn("而你是 C）", got[0])

    def test_gaps_join(self):
        t = ("## 缺口\n\n"
             "- 甲能力——JD 要求「X」，\n"
             "  而你没有\n")
        got = ex.parse_gaps(t)
        self.assertEqual(len(got), 1)
        self.assertIn("而你没有", got[0]["detail"])


if __name__ == "__main__":
    unittest.main()
