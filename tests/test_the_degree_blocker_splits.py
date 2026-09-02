# -*- coding: utf-8 -*-
"""「学历/专业」那一档里有两种岗，动作是相反的。

面板那条说明原来同时给两条建议：

> 多数只是「计算机相关专业优先」这类模板句，**不当真、照投**；
> 真卡的是明确要硕士的那些。**投前问一句卡不卡。**

而屏幕上只有**一个数**（215），用户没法知道自己面对的是哪一种。实测活动用户
2026-08-23：223 个里 **144 个平台字段写着硕士/博士**（他是本科，问一句也没用），
只有 79 个是本科/统招本科/不限 —— 那才是「问一句可能有戏」的那批。

**拿一个 215 去说「投前问一句」，等于让他给 144 个不可能的岗各发一条消息。**

判据用平台的 `eduLevel` 字段，而那一层的准确度是量过的
（`check_edu_field_cannot_close`：与 JD 正文实测 58% 对不上）—— 所以它
**只用来分档说明，不参与任何判定**，学历门本身照旧按 JD 正文判。
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tests"))
from _srcscan import code_of  # noqa: E402

SRC = (ROOT / "tools" / "export_web_data.py").read_text(encoding="utf-8")


class TheTwoKindsAreCounted(unittest.TestCase):
    def test_the_hard_ones_are_tallied(self):
        self.assertIn("_hard_edu", SRC, "没数出「真卡的」有多少")
        code = code_of("tools/export_web_data.py", "def resume_insight(")
        self.assertIn('("硕士", "博士")', code, "分档判据不是硕博那两档")

    def test_the_note_reports_both_numbers(self):
        i = SRC.index('"name": "学历/专业"')
        seg = SRC[i:i + 900]
        self.assertIn("_hard_edu", seg, "说明里没用上那个数")
        self.assertIn("n_edu - _hard_edu", seg, "没给出「还能问的」那一半")

    def test_each_half_gets_its_own_action(self):
        i = SRC.index('"name": "学历/专业"')
        seg = SRC[i:i + 900]
        self.assertIn("问也没用", seg, "硬卡那一半没说清「别浪费时间」")
        self.assertIn("照投", seg, "软的那一半没说清「照投」")

    def test_it_falls_back_when_nothing_is_hard(self):
        """一个硬卡都没有时不该印「其中 0 个」——退回原来那句。"""
        i = SRC.index('"name": "学历/专业"')
        seg = SRC[i:i + 900]
        self.assertIn("if _hard_edu else", seg, "没有「算不出/没有硬卡」那一支")


class TheFieldStaysOutOfTheJudgement(unittest.TestCase):
    """`eduLevel` 与 JD 正文实测 58% 对不上 —— 它只配说明，不配结案。"""

    def test_the_prescreen_rule_is_unchanged(self):
        pre = (ROOT / "tools" / "prescreen.py").read_text(encoding="utf-8")
        self.assertRegex(pre, r"只能\*\*降权泊车\*\*|只能降权",
                         "学历字段又被允许结案了")

    def test_the_audit_still_measures_the_mismatch(self):
        ap = (ROOT / "tools" / "audit_pipeline.py").read_text(encoding="utf-8")
        self.assertIn("check_edu_field_cannot_close", ap,
                      "那条量误杀率的检查不见了")


if __name__ == "__main__":
    unittest.main()
