# -*- coding: utf-8 -*-
"""「待核实的信息」那一节 223 份里有内容，面板上只有 42 份 —— 卡在解析这一层。

`parse_quality` 只认一种形状：

    - **标题**：正文

**而那是规格里不存在的形状。** `04-job-evaluation.md` 给这一节的模板就一行：

    - ...（这个岗是真是假，你看出了什么；正面信号也写；没有就写「无」）

一个纯文本项目符号，**没有粗体标题**。于是照规格写的那些一条都读不到。

实测活动用户 2026-08-23，223 份带这一节的深评：

    写了「无」          27   ← 本来就没内容
    解析得到            42
    **有内容却读不到   151**  ← 其中 138 份就是「没有粗体标题的纯文本」
    整节空               3

**68% 的内容卡在解析这一层。** 而这一节正是「这个岗是真是假」的落点 ——
蓄水池、匿名雇主、平台字段自相矛盾都写在这里，用户一条都看不见。

改完：**193 份 / 251 条**（余下 30 份是写了「无」或整节空，本来就不该上屏）。

## 显示层跟着改了一处

`<strong>{q.title}</strong>：{q.detail}` 遇到空标题会在行首吊一个冒号 ——
和隔壁「缺口」那条注释记的「xx —— 。」是同一族残句。`key={q.title}` 同理，
一堆空标题会撞成同一个 key。
"""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import export_web_data as ex  # noqa: E402

EX = (ROOT / "tools" / "export_web_data.py").read_text(encoding="utf-8")
JR = (ROOT / "web" / "src" / "components"
      / "JobReadout.tsx").read_text(encoding="utf-8")
EVAL = (ROOT / "workflows" / "reference"
        / "04-job-evaluation.md").read_text(encoding="utf-8")


def parse(body: str):
    return ex.parse_quality("## 待核实的信息\n" + body + "\n\n## 下一节\n")


class APlainBulletCounts(unittest.TestCase):
    def test_it_is_read(self):
        got = parse("- 融资阶段字段写「其他」，实际轮次不明。")
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["title"], "")
        self.assertIn("融资阶段字段写", got[0]["detail"])

    def test_the_titled_shape_still_works(self):
        got = parse("- **强度信号全缺**：JD 未提任何工作制信息。")
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["title"], "强度信号全缺")
        self.assertIn("JD 未提任何工作制信息", got[0]["detail"])

    def test_bold_followed_by_a_comma_is_not_a_title(self):
        """`- **公司实名可核实**，但本轮没做核查` —— 那个粗体是句中强调。
        硬拆成「标题：正文」会把一句话腰斩。"""
        got = parse("- **公司实名可核实（甲公司）**，但本轮批量没做独立核查。")
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["title"], "")
        self.assertIn("但本轮批量没做独立核查", got[0]["detail"])

    def test_a_bare_none_is_skipped(self):
        """写「无」是照规格办事，不该在面板上占一行。"""
        for body in ("- 无", "- 无。", "- —", "- 不适用"):
            with self.subTest(body=body):
                self.assertEqual(parse(body), [])

    def test_an_empty_section_yields_nothing(self):
        self.assertEqual(parse(""), [])

    def test_mixed_shapes_all_land(self):
        got = parse("- 纯文本一条\n"
                    "- **有标题**：带正文\n"
                    "- 无\n"
                    "- **强调**，接着说")
        self.assertEqual(len(got), 3)
        self.assertEqual([g["title"] for g in got], ["", "有标题", ""])

    def test_continuation_lines_still_attach(self):
        got = parse("- 公司实名可核实，但本轮批量没做独立的公司事实核查——\n"
                    "  发开场白前建议自己查一条公司近况。")
        self.assertEqual(len(got), 1)
        self.assertIn("发开场白前建议自己查一条", got[0]["detail"])

    def test_a_blank_line_breaks_the_continuation(self):
        got = parse("- 第一条\n\n这是散文，不该被接到上一条上")
        self.assertEqual(len(got), 1)
        self.assertNotIn("这是散文", got[0]["detail"])

    def test_the_section_heading_is_still_flexible(self):
        """「信息质量」是内部词，AI 守规则会写成「待核实的信息」。"""
        for h in ("## 信息质量", "## 待核实的信息", "### 职位真伪信号",
                  "## 存疑的地方"):
            with self.subTest(h=h):
                got = ex.parse_quality(h + "\n- 一条\n\n## 下一节\n")
                self.assertEqual(len(got), 1, f"{h} 认不出来")

    def test_it_stops_at_the_next_heading(self):
        got = ex.parse_quality("## 待核实的信息\n- 一条\n\n## 建议\n- 不该算进来\n")
        self.assertEqual(len(got), 1)


class TheSpecReallySaysPlain(unittest.TestCase):
    """整条改动建立在「规格给的就是纯文本项目符号」上。"""

    def test_the_template_line_is_a_bare_bullet(self):
        i = EVAL.index("### 职位真伪信号")
        seg = EVAL[i:EVAL.index("### 投前必问", i)]
        # **`assertRegex` 的第三个参数是 `msg`，不是 flags。** 传 `re.M`
        # 进去它只是个消息对象，多行模式根本没开 —— 第一版就这么落空的。
        # 要按行匹配就把 `(?m)` 写进正则里。
        self.assertRegex(seg, r"(?m)^- \.\.\.（这个岗是真是假")

    def test_the_template_does_not_mandate_a_bold_title(self):
        i = EVAL.index("### 职位真伪信号")
        seg = EVAL[i:EVAL.index("### 投前必问", i)]
        self.assertNotRegex(seg, r"(?m)^- \*\*.+?\*\*[：:]")

    def test_the_none_convention_is_in_the_spec(self):
        i = EVAL.index("### 职位真伪信号")
        seg = EVAL[i:EVAL.index("### 投前必问", i)]
        self.assertIn("没有就写「无」", seg)


class TheReasonIsRecorded(unittest.TestCase):
    def _doc(self) -> str:
        i = EX.index("def parse_quality(")
        return " ".join(EX[i:EX.index("    lines = text.splitlines()", i)].split())

    def test_it_says_the_shape_was_never_specified(self):
        self.assertRegex(self._doc(), r"那是\*\*规格里不存在的形状\*\*")

    def test_it_carries_the_breakdown(self):
        seg = self._doc()
        self.assertRegex(seg, r"\*\*有内容却读不到 151\*\*")
        self.assertRegex(seg, r"138 份就是「没有粗体标题的纯文本」")
        self.assertIn("2026-08-23", seg)

    def test_it_says_why_the_section_matters(self):
        """不说清丢的是什么，下一版会觉得「不就是几条提示」。"""
        seg = self._doc()
        self.assertRegex(seg, r"蓄水池、匿名雇主、字段自相矛盾都写在这里")

    def test_the_comma_case_is_explained_at_the_code(self):
        i = EX.index('b = re.match(r"\\s*-\\s+(.*)", ln)')
        # 注释跨了行，拉平之后中间会夹两样东西：行首的 `#`，以及折行本身
        # 留下的那个空格（`句中强调， 不是标题`）。抹掉 `#`，空格用 `\s*` 兜。
        seg = " ".join(EX[i:i + 500].replace("#", " ").split())
        self.assertRegex(seg, r"那里的粗体是句中强调，\s*不是标题")


class ThePanelRendersATitlelessNote(unittest.TestCase):
    def _seg(self) -> str:
        i = JR.index('<ul className="quality-list">')
        return JR[i:JR.index("</ul>", i)]

    def test_no_dangling_colon(self):
        seg = self._seg()
        self.assertIn("q.title ? (", seg, "空标题仍然会吊一个冒号")

    def test_the_titled_branch_survives(self):
        self.assertIn("<strong>{q.title}</strong>：{q.detail}", self._seg())

    def test_the_titleless_branch_shows_the_detail(self):
        """**只看 `) : (` 之后那一支。** `q.detail` 在有标题那一支里也出现，
        从三元开头切会被它满足 —— 把 else 换成 `null` 照样绿（变异实测）。"""
        seg = self._seg()
        i = seg.index(") : (")
        self.assertIn("q.detail", seg[i:], "空标题那一支什么都不显示")

    def test_the_key_no_longer_collides(self):
        seg = self._seg()
        self.assertNotIn("key={q.title}", seg, "一堆空标题会撞成同一个 key")
        self.assertIn("key={`${i}-${q.title}`}", seg)

    def test_the_reason_is_at_the_code(self):
        seg = " ".join(self._seg().split())
        self.assertRegex(seg, r"标题可能是空的")
        self.assertRegex(seg, r"和隔壁「缺口」那条注释说的「xx —— 。」是同一族残句")

    def test_the_footnote_survives(self):
        """「不算进分数」那句是这一栏的定性，不能被这次改动带掉。"""
        self.assertIn("这些是信息本身没核实清楚，不是岗位的缺点，所以不扣分", JR)


if __name__ == "__main__":
    unittest.main()
