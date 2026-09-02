# -*- coding: utf-8 -*-
"""判词取「分数档」与「技能与经验天花板」里较低的那个 —— 框架的核心映射。

`04-job-evaluation.md` 定了两道：

- **分数档**：75+ 强匹配 · 60-74 值得投 · 45-59 可以考虑 · 30-44 不建议 · <30 跳过
- **判词天花板**（按技能与经验）：≥80 不封 · 60-79 封到「值得投」·
  40-59 封到「可以考虑」· <40 封到「不建议」

天花板那条是补「传导」用的：总分里薪资占 25%，钱给够就能把技能 28 的岗抬到
60 分。04 举了三个实测例子，原话是「值得投三个字会让人真的去投、去定制材料、
去准备面试」。

两个数都是执行者手写进 `rank_breakdown` 的，而自检的四十多条检查
**一条都没在算这个映射**（2026-08-26 之前）。

## 抓到的那一个，根因不是判错

全库 664 个三项齐全的岗，超卖的只有 1 个：59 分 · 技能 65 → 写着「值得投」。
那份评估的注脚记着「2026-08-20 校准：技能与经验 69 → 65」—— 技能一改，
总分从 60 落到 59，**而结论那一行没跟着动**。同一个文件里当时并存着三代状态：
得分 59（08-20）、结论「值得投」（08-11）、页脚「判词为『可以考虑』」（更早）。

所以这条检查真正防的是**改了一处忘了另一处**。

## 只报超卖

判词低于上限是允许的（硬门 FLAG、信息不足、用户偏好都可能再压一档，04 没规定
必须顶格）。实测低于上限的有 11 个 —— 一起报，这条就长期红着，然后被当噪音。
"""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import audit_pipeline as ap  # noqa: E402

SRC = (ROOT / "tools" / "audit_pipeline.py").read_text(encoding="utf-8")
FRAMEWORK = (ROOT / "workflows" / "reference"
             / "04-job-evaluation.md").read_text(encoding="utf-8")


def _job(score, skill, verdict, title="蓝湾智投科技"):
    return {"t": {"title": title, "rank_score": score, "rank_verdict": verdict,
                  "rank_breakdown": {"技能与经验": skill}}}


class ItCatchesOverselling(unittest.TestCase):
    def test_a_verdict_above_its_score_band_fires(self):
        got = ap.check_verdict_matches_its_score(_job(59, 65, "值得投"), {})
        self.assertTrue(got, "59 分写「值得投」没被报出来")
        self.assertIn("超卖", got[0][2])
        self.assertIn("/job-apply", got[0][2], "没给该敲的那条命令")

    def test_the_ceiling_catches_what_the_score_band_would_let_through(self):
        """04 那三个实测例子的形状：钱给够，技能 28 也能爬到 60 分。

        分数档说「值得投」，天花板说「不建议」—— 取小，所以这是超卖。
        少了这一半，这条检查就漏掉框架**专门写它**的那一类。
        """
        got = ap.check_verdict_matches_its_score(_job(60, 28, "值得投"), {})
        self.assertTrue(got, "技能 28 的岗顶着「值得投」，天花板那一半没生效")

    def test_it_reports_how_far_off(self):
        msg = ap.check_verdict_matches_its_score(_job(59, 65, "值得投"), {})[0][2]
        for piece in ("59", "65", "可以考虑", "值得投"):
            self.assertIn(piece, msg, f"报告里没有「{piece}」，看不出差在哪")

    def test_it_names_the_usual_root_cause(self):
        """不是「打分打得准不准」，是改了一处忘了另一处。"""
        msg = ap.check_verdict_matches_its_score(_job(59, 65, "值得投"), {})[0][2]
        self.assertIn("改了一处忘了另一处", msg)


class ItLeavesTheConservativeOnesAlone(unittest.TestCase):
    def test_a_verdict_below_the_ceiling_is_fine(self):
        for score, skill, v in ((82, 90, "值得投"), (70, 85, "可以考虑"),
                                (55, 70, "不建议"), (90, 95, "跳过")):
            with self.subTest(score=score, skill=skill, verdict=v):
                self.assertEqual(ap.check_verdict_matches_its_score(
                    _job(score, skill, v), {}), [])

    def test_exactly_on_the_ceiling_is_fine(self):
        """82 分 · 技能 65 → 天花板「值得投」，写「值得投」正好顶格，不是超卖。"""
        self.assertEqual(ap.check_verdict_matches_its_score(
            _job(82, 65, "值得投"), {}), [])

    def test_the_band_edges_are_inclusive(self):
        for score, v in ((75, "强匹配"), (60, "值得投"), (45, "可以考虑"), (30, "不建议")):
            with self.subTest(score=score):
                self.assertEqual(ap.check_verdict_matches_its_score(
                    _job(score, 95, v), {}), [], f"{score} 分该够得着「{v}」")


class ItDoesNotGuess(unittest.TestCase):
    def test_a_missing_skill_score_is_skipped(self):
        j = {"t": {"title": "x", "rank_score": 90, "rank_verdict": "强匹配",
                   "rank_breakdown": {}}}
        self.assertEqual(ap.check_verdict_matches_its_score(j, {}), [],
                         "技能没打分就判不了天花板 —— 不许当成 0")

    def test_a_missing_score_is_skipped(self):
        j = {"t": {"title": "x", "rank_verdict": "强匹配",
                   "rank_breakdown": {"技能与经验": 20}}}
        self.assertEqual(ap.check_verdict_matches_its_score(j, {}), [])

    def test_a_gate_failure_verdict_is_out_of_scope(self):
        """「不满足硬性条件（英语）」这类另有判据，不走档位表。"""
        j = _job(80, 90, "不满足硬性条件（英语）")
        self.assertEqual(ap.check_verdict_matches_its_score(j, {}), [])

    def test_the_prescreen_prefix_is_stripped(self):
        got = ap.check_verdict_matches_its_score(_job(59, 65, "粗筛：值得投"), {})
        self.assertTrue(got, "「粗筛：」前缀没剥掉，粗筛出来的判词全逃过了这条")

    def test_junk_values_do_not_crash_it(self):
        j = {"t": {"title": "x", "rank_score": "很高", "rank_verdict": "值得投",
                   "rank_breakdown": {"技能与经验": None}}}
        self.assertEqual(ap.check_verdict_matches_its_score(j, {}), [])


class TheTwoTablesMatchTheFramework(unittest.TestCase):
    """常数抄自 04，两边不许分叉 —— 分叉了这条检查就在按自己那套判人。"""

    def test_the_score_bands_are_the_framework_ones(self):
        self.assertEqual(ap._VERDICT_BANDS,
                         ((75, "强匹配"), (60, "值得投"), (45, "可以考虑"), (30, "不建议")))

    def test_the_ceilings_are_the_framework_ones(self):
        self.assertEqual(ap._VERDICT_CEILINGS,
                         ((80, "强匹配"), (60, "值得投"), (40, "可以考虑")))

    def test_the_framework_still_says_80_60_40(self):
        """04 把第二版的 70/50/30 判成过拟合并改成了 80/60/40。
        哪天它再改一次，这里必须跟着改 —— 所以钉住那句话还在。"""
        self.assertIn("改成 80/60/40 之后", FRAMEWORK)

    def test_the_ceiling_exists_because_money_can_carry_a_bad_match(self):
        """天花板的理由不是「更严一点」，是薪资 25% 能把技能 28 抬过 60。"""
        self.assertTrue(re.search(r"只要钱给够，\s*技能再差总分也能爬到 60", FRAMEWORK),
                        "04 里那句话没了 —— 天花板就成了没来由的额外收紧")


class ItIsRegistered(unittest.TestCase):
    def test_the_check_is_in_the_list(self):
        uses = [ln for ln in SRC.splitlines()
                if "check_verdict_matches_its_score" in ln
                and not ln.lstrip().startswith("def ")]
        self.assertTrue(uses, "写了检查却没挂进清单 —— 它永远不会跑")
        self.assertTrue(any("(" in ln and "," in ln for ln in uses), uses)


if __name__ == "__main__":
    unittest.main()
