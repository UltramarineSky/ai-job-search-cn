# -*- coding: utf-8 -*-
"""粗筛判完的七道门躺在盘上，一次都没上过屏。

`job-rank.md` Step 2 的子代理判完七道门，整块存进
`rank_breakdown["硬性条件"]`。而导出这边**只从 `evaluation.md` 的门表解析**
—— 那是深评才有的文件。于是粗筛的岗，门判定写了没人读。

实测（2026-08-26）：库里 125 个岗存了这份判定，面板上看得到的 **2 个**。
余下 123 个：

| 情形 | 个数 | 用户看得见吗 |
|---|---|---|
| 只有 FLAG | **50** | **看不见** —— FLAG 不淘汰，判词照常是「粗筛：可以考虑」 |
| 有 FAIL | 42 | 判词写着「硬门 FAIL」，看得出个大概，但看不出是哪几道 |
| 全 PASS | 31 | 没什么可显示 |

**FLAG 那 50 个才是真丢的。** 04 对它的规定是「留在排序里，但挂一个显眼的 ⚠
让用户自己判断」，而那个 ⚠ 对粗筛的岗从来没出现过 —— 其中几个还在可投档
（67 / 61 / 60 分「可以考虑」，门是「工作年限 FLAG」）。

这是本仓库记过的那个形状：**数据在，断在最后一层。**
同族前科：`skipReason` 一直在盘上而搁置区只显示两个字「跳过」。

## 状态词沿用同一份表

`FLAG → pass` 并在依据里写「刚过线，留意」（04 那张表叫「满足（带提醒）」）
是既有约定，`GATE_RULES` / `GATE_FLAGGED` 就是正本。这条路只换了数据来源，
判据一个字没改 —— 下面第三组钉的就是这件事。
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import _cli  # noqa: E402
import export_web_data as ex  # noqa: E402

SRC = (ROOT / "tools" / "export_web_data.py").read_text(encoding="utf-8")


def _entry(gates: dict, key="硬性条件"):
    return {"title": "AI产品经理", "rank_breakdown": {key: dict(gates)}}


FULL = {"学历与院校": "PASS", "工作年限": "FLAG", "户口与落户": "不适用",
        "应届生与三方": "PASS", "外包/驻场/派遣": "PASS",
        "执业资格/证照/职称": "不适用", "候选人明确排除": "PASS"}


class ItTurnsTheStoredJudgementIntoPanelShape(unittest.TestCase):
    def test_all_seven_come_through(self):
        got = ex.gates_from_breakdown(_entry(FULL))
        self.assertEqual(len(got), 7)
        self.assertEqual({g["name"] for g in got}, set(_cli.GATES))

    def test_the_old_key_name_is_read_too(self):
        """存量里两个名字都有：`硬性条件` 125 条、`硬门` 41 条。"""
        self.assertEqual(len(ex.gates_from_breakdown(_entry(FULL, key="硬门"))), 7)

    def test_nothing_stored_yields_nothing(self):
        for e in ({}, {"rank_breakdown": {}}, {"rank_breakdown": {"硬性条件": "全过"}}):
            with self.subTest(entry=e):
                self.assertEqual(ex.gates_from_breakdown(e), [])

    def test_a_gate_name_outside_the_seven_is_marked_not_dropped(self):
        """自造门名留着、标 `offSpec` —— 同 `parse_gates` 那一段。

        丢掉是不对的：自造的门名多半也承载了一条真信息（实测最常见的是
        「地点」「专业」「英语」）。标记的用处是**别把它算进「投前要问清楚」**
        的计数 —— 那个计数只对七道正规门负责。

        **这条第一版写的是「丢掉」，当场红。** 因为 `_cli.gate_of` 认不出时
        返回的是空串不是 `None`，而实现里写的是 `is None` —— 那一支永远不成立。
        两个错正好互相掩盖：断言错了，实现也错了，只是方向相反。
        """
        got = ex.gates_from_breakdown(_entry({**FULL, "英语": "FAIL"}))
        hit = next(g for g in got if g["name"] == "英语")
        self.assertTrue(hit.get("offSpec"), "自造门名没标记 —— 会被当成一道正规门去催")
        self.assertFalse(any(g.get("offSpec") for g in got if g["name"] != "英语"),
                         "七道正规门被误标成了自造的")

    def test_junk_values_are_skipped_not_crashed(self):
        got = ex.gates_from_breakdown(_entry({"工作年限": None, "学历与院校": "PASS"}))
        self.assertEqual([g["name"] for g in got], ["学历与院校"])


class TheFlagFinallyShows(unittest.TestCase):
    """这 50 个岗是这条路存在的全部理由。"""

    def _gate(self, verdict, name="工作年限"):
        got = ex.gates_from_breakdown(_entry({name: verdict}))
        self.assertEqual(len(got), 1)
        return got[0]

    def test_a_flag_carries_its_reminder(self):
        g = self._gate("FLAG")
        self.assertIn("留意", g["why"], "FLAG 上了屏却不带提醒 —— 那就是个干净的「满足」")

    def test_a_flag_does_not_fail_the_job(self):
        """FLAG 不淘汰。判成 fail 会让一批本该排在里面的岗凭空出局。"""
        self.assertEqual(self._gate("FLAG")["state"], "pass")

    def test_a_plain_pass_says_nothing(self):
        """没有依据原文就空着。`gate_why` 的「无说明」是另一条路的兜底 ——
        那边应该有依据，没有就是漏写；这边本来就没有，挂上去纯属噪音。"""
        self.assertEqual(self._gate("PASS")["why"], "")

    def test_fail_and_na_map_as_usual(self):
        self.assertEqual(self._gate("FAIL")["state"], "fail")
        self.assertEqual(self._gate("不适用", "户口与落户")["state"], "na")


class TheVerdictVocabularyIsNotForkedHere(unittest.TestCase):
    """状态词只有一份正本。这条路要是另立一套，同一个 FLAG 在两处会长成两样。"""

    def _seg(self):
        i = SRC.index("def gates_from_breakdown(")
        end = SRC.find("\ndef ", i + 10)
        return SRC[i:end if end > 0 else len(SRC)]

    def test_it_calls_the_shared_mappers(self):
        seg = self._seg()
        self.assertIn("gate_state(", seg)
        self.assertIn("gate_why(", seg)

    def test_it_does_not_write_its_own_table(self):
        seg = self._seg()
        for hardcoded in ('"pass"', '"fail"', '"na"', '"unknown"'):
            self.assertNotIn(hardcoded, seg,
                             f"自己写了状态字面量 {hardcoded} —— 那就是第二份表")

    def test_the_shared_table_still_maps_flag_to_pass(self):
        """上面第二组全压在这条约定上。它一变，那边就该跟着改。"""
        self.assertIn(("FLAG", "pass"), ex.GATE_RULES)


class TheDeepEvalPathStillWins(unittest.TestCase):
    """`evaluation.md` 那张表带依据原文，更全 —— 有它就该覆盖这一份。"""

    def test_the_fallback_runs_before_the_evaluation_block(self):
        i_fb = SRC.index("job[\"gates\"] = gates_from_breakdown(e)")
        i_ev = SRC.index("job[\"gates\"] = parse_gates(t)")
        self.assertLess(i_fb, i_ev,
                        "回退放到了深评之后 —— 会把带依据的那份覆盖掉")

    def test_the_fallback_only_fires_when_empty(self):
        i = SRC.index("job[\"gates\"] = gates_from_breakdown(e)")
        self.assertIn('if not job["gates"]:', SRC[i - 300:i])


if __name__ == "__main__":
    unittest.main()
