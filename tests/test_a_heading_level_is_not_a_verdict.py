# -*- coding: utf-8 -*-
r"""三级标题读不出来，判词就退回「扫全文」——然后正文里随便一句话就成了判词。

`_section()` 原来写死 `^##\s+`（正好两个井号），而 `04-job-evaluation.md` 的
输出格式里，结论那一节用的是 `### 结论：`。同一个文件里判词的锚点正则早就写成
`^##+\s*结论`，只有 `_section` 没跟上。

后果不是「读不出」，是**读错**。`parse_evaluation` 的兜底是：

    tail = _section(text, "结论") or text        # ← 读不出就扫全文
    hits = [(tail.index(b), b) for b in VERDICT_BANDS if b in tail]
    verdict = min(hits)[1]                       # ← 取最早出现的那个档位词

实测（2026-08-26）：一份 80 分、结论写着「值得投」的深评，头部有一行

    - `behavioral.md` 未填（仍是占位符），本轮**跳过**语气/文化匹配校准

——「跳过」比结论段更早出现，判词就成了「跳过」，`writeback` 照着把职位库也
改成了「跳过」。那个岗是当时分最高的一个，而「跳过」在面板上会把它扔进
「不投的岗位」。

**误报向下比向上更难发现**：向上（把不该投的说成值得投）会被用户投一次戳穿；
向下是这个岗从此不再出现在他眼前，没有任何一步会提醒他少了什么。

修的是 `_section`（`##` → `##+`）。全库 277 份实测：判词只变了 1 份，
正是被写坏的那份，跳过 → 值得投。
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from build_dashboard import _section, parse_evaluation  # noqa: E402

NL = chr(10)


def _doc(conclusion_heading: str) -> str:
    """一份最小深评：头部那句「跳过语气校准」在前，真结论在后。"""
    return NL.join([
        "# 某公司 — 某岗位",
        "",
        "## 职位评估：某公司 - 某岗位",
        "",
        "- 评估日期：2026-08-26",
        "- `behavioral.md` 未填（仍是占位符），本轮跳过语气/文化匹配校准",
        "",
        "### 评分明细",
        "",
        "**综合得分：80/100**",
        "",
        conclusion_heading,
        "",
        # 真实形状：判词写在结论段开头，后面才是「被什么压的」那句解释。
        # 框架强制要求那句解释（04「必须在依据的第一句就说清是被什么压的」），
        # 所以结论段里出现「强匹配」三个字是常态，不是异常。
        "**值得投（80）**",
        "",
        "四项算出来已经到强匹配的区间，被技能档压回值得投。",
        "",
    ])


class ASectionIsFoundAtAnyHeadingLevel(unittest.TestCase):
    def test_three_hashes_are_a_section_too(self):
        self.assertTrue(_section(_doc("### 结论"), "结论"),
                        "`### 结论` 读不出来 —— 判词会退回扫全文")

    def test_two_hashes_still_work(self):
        self.assertTrue(_section(_doc("## 结论"), "结论"), "两个井号的写法被改坏了")


class HeaderProseIsNotAVerdict(unittest.TestCase):
    """**这条是那个 bug 本身。**"""

    def test_a_skipped_calibration_note_does_not_become_the_verdict(self):
        """头部那句「本轮跳过语气校准」在结论之前，不许被当成判词。"""
        v = parse_evaluation(_doc("### 结论"))["verdict"]
        self.assertEqual(
            v, "值得投",
            "头部那句「本轮跳过语气校准」被当成了判词 —— "
            "一个 80 分的岗会因此掉进「不投的岗位」，而没有任何一步会提醒")

    def test_the_anchored_form_still_wins(self):
        """模板自己的写法（`### 结论：值得投`）本来就该直接命中锚点。"""
        v = parse_evaluation(_doc("### 结论：值得投（80）"))["verdict"]
        self.assertEqual(v, "值得投")

    def test_the_score_still_reads(self):
        self.assertEqual(parse_evaluation(_doc("### 结论"))["score"], "80")


if __name__ == "__main__":
    unittest.main()
