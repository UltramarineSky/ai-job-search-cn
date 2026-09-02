"""被否定掉的判定词不算判定词。

`evaluation.md` 的状态格是人写的中文，里头照样会出现判定码——**而且经常带否定**：

    FLAG，非 FAIL          过线但要留意
    待确认，不判 FAIL      分不清口语还是书面，按 04 的裁定不一票否决
    不算 FAIL              同上

`gate_state` 原来靠 `GATE_RULES` 的**排序**绕开第一种：FLAG 排在 FAIL 前面，
先命中就轮不到 FAIL。可那只挡得住带 FLAG 的那种写法。2026-08-20 实测栽在
后两种上——2 个岗的状态格写着「待确认，不判 FAIL」，子串撞见 FAIL 判成不满足，
而判词仍是「值得投」。面板于是同时印着「有一条不满足就别投」和「值得投」，
用户信哪个都不对。全库 57 处否定写法，其中 12 处没有 FLAG 托底。

**排序是碰运气，识别否定才是机制。** 修在 `gate_state`：先剥掉被否定的判定词
再匹配。这里钉住那条判据；全库不变量（fail 不许与可投档并存）由
`audit_pipeline.check_gate_fail_blocks_the_verdict` 兜底。
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import export_web_data as ex  # noqa: E402


class NegatedTokensDoNotCount(unittest.TestCase):

    def test_negated_fail_is_not_fail(self):
        for cell in ("待确认，不判 FAIL", "不算 FAIL", "不是 FAIL",
                     "非 FAIL", "不判FAIL"):
            with self.subTest(cell):
                self.assertNotEqual(ex.gate_state(cell), "fail",
                                    f"「{cell}」是在说**不判** FAIL，判成 fail 就等于"
                                    "把这个岗从可投名单里误杀")

    def test_the_flag_shape_still_passes(self):
        """原来靠排序侥幸走对的那种，改完必须还是 pass——别修一个坏一个。"""
        self.assertEqual(ex.gate_state("FLAG，非 FAIL"), "pass")
        self.assertEqual(ex.gate_state("**FLAG，非 FAIL**"), "pass")

    def test_a_real_fail_is_still_fail(self):
        """否定剥除不能把真的 FAIL 一起剥掉。"""
        for cell in ("FAIL", "硬门 FAIL", "**FAIL**（学历不符）"):
            with self.subTest(cell):
                self.assertEqual(ex.gate_state(cell), "fail")

    def test_plain_uncertainty_is_unknown(self):
        self.assertEqual(ex.gate_state("待确认"), "unknown")
        self.assertEqual(ex.gate_state("待确认，不判 FAIL"), "unknown",
                         "剥掉否定后剩「待确认」——那正是它的本意")

    def test_na_and_pass_survive(self):
        self.assertEqual(ex.gate_state("不适用"), "na")
        self.assertEqual(ex.gate_state("PASS"), "pass")

    def test_negation_is_stripped_not_reordered(self):
        """判据不能退回成「再加一个 token 排到前面」——那是同一个坑再踩一次。

        新写法必须在匹配**之前**把否定去掉；靠往 GATE_RULES 里塞
        「不判 FAIL」这种字面量，下一种说法（「无需判 FAIL」）照样漏。
        """
        src = (ROOT / "tools" / "export_web_data.py").read_text(encoding="utf-8")
        i = src.index("def gate_state")
        body = src[i:src.index("\n\n", i)]
        self.assertIn("NEGATED.sub", body,
                      "gate_state 没有先剥否定——靠排序绕开否定是碰运气")
        rules = src[src.index("GATE_RULES = ["):src.index("]", src.index("GATE_RULES = ["))]
        self.assertNotIn("不判", rules,
                         "否定又被塞回词表里了——词表穷举不完中文的否定说法")


if __name__ == "__main__":
    unittest.main()
