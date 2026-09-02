"""`/job-upskill` 的输入与权重：学习计划只能来自「够得着的岗」。

## 修的是两个具体错误

**① 从标题猜要求，而 JD 正文就在库里。** Step 3 原文写着「you do not have the full
posting — use the role, sector, and notes columns to infer likely required skills」。
自从有了详情库（`job_scraper/details/`），这句话是错的：实测 137 份 JD 正文在盘上，
112 份评估还带着逐条写好的缺口依据。照着旧文档做，等于把手上最好的证据扔掉去猜。

**② 权重公式把「方向不对」当成了「能力缺口」。** 原公式 `(100 - fit_rating) / 100`
——分越低权重越大。但分低绝大多数是因为岗位方向不对，不是因为能力差。实测这份语料
里分最低的八个岗是私募基金 PM、服装门店店长、电子元器件分销、伤口缝线市场 PM、
医学大数据 PM……照旧公式，学习计划会建议去补「私募尽调」「被动元件选型」
「医药商业化」。

这与评分框架的「判词天花板」是同一类病：**可行性与价值不能混为一谈**。学习计划要
回答的是「在我够得着的岗里还差什么」，不是「所有我拿不到的岗都缺什么」。
实测分档：`<40 方向不对` 52 个、`50-74 差一口气` 36 个、`≥75 够了` 11 个。

这里钉住文档里的这几条规则——`/job-upskill` 由 AI 按文档执行，没有可执行实现，
能钉住的就是规则本身不被改回去。
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UPSKILL = ROOT / "workflows" / "job-upskill.md"
EXPORT = ROOT / "tools" / "export_web_data.py"


def text() -> str:
    return UPSKILL.read_text(encoding="utf-8")


class UsesTheEvaluationCorpusNotJustTheTracker(unittest.TestCase):
    def test_details_store_is_named_as_a_source(self):
        t = text()
        self.assertIn("job_scraper/details", t,
                      "详情库（JD 正文）必须是数据源之一——它就在盘上")

    def test_rank_breakdown_fields_are_named(self):
        t = text()
        for field in ("技能与经验", "专业能力", "业务域", "依据"):
            self.assertIn(field, t, f"评估拆解里的 {field} 应当被用上，不该重新推断")

    def test_no_longer_claims_the_posting_is_unavailable(self):
        """那句「you do not have the full posting」现在是错的。"""
        t = text()
        self.assertNotIn("you do not have the full posting", t)

    def test_source_layers_must_be_disclosed(self):
        t = text()
        self.assertRegex(t, r"写明本轮用了哪几层数据|数据源.*条数",
                         "三层数据的结论强度不同，报表要写明用了哪几层")


class WeightingTargetsReachableJobs(unittest.TestCase):
    def test_old_inverted_formula_is_no_longer_an_instruction(self):
        """公式本身可以留在文档里——但只能作为**被否定的反例**引述。

        留反例是有意的：不写清楚旧公式错在哪，下次有人会觉得它更「合理」而改回去。
        所以这里不是查字符串在不在，而是查它出现的位置：
        必须落在「旧公式是错的」那段解释里，不能作为要照做的指令。
        """
        t = text()
        self.assertNotIn("Then apply a **fit weight**", t,
                         "旧的加权指令必须删掉")
        for m in re.finditer(re.escape("(100 - fit_rating) / 100"), t):
            around = t[max(0, m.start() - 400):m.end() + 200]
            self.assertIn("旧公式是错的", around,
                          "这个公式只能作为被否定的反例出现，不能当指令")

    def test_the_reachable_band_carries_the_weight(self):
        t = text()
        self.assertIn("60-79", t, "「差一口气」那档要明确写出来")
        self.assertRegex(t, r"≥\s*80", "已经够了的那档要明确写出来")
        self.assertRegex(t, r"与判词天花板同源|技能与经验自己的分档",
                         "四档必须与判词天花板同源，不能各定各的数字")

    def test_wrong_direction_jobs_contribute_nothing(self):
        t = text()
        self.assertIn("方向不对", t)
        self.assertRegex(
            t, r"<\s*40[^\n|]*\|[^\n|]*方向不对[^\n|]*\|\s*\*\*0\*\*",
            "技能 <40 的岗权重必须是 0——它们不是能力缺口")

    def test_the_reason_is_recorded_so_it_is_not_reverted(self):
        """光改公式不够：要留下实测反例，否则下次有人会觉得旧公式更「合理」。"""
        t = text()
        self.assertRegex(t, r"私募|店长|缝线|分销",
                         "要留下旧公式会推荐去学什么的实测例子")


class SeparatesLearnableFromNotLearnable(unittest.TestCase):
    def test_stack_and_domain_gaps_are_split(self):
        t = text()
        self.assertRegex(t, r"专业能力缺口.*业务域缺口|专业能力缺口与业务域缺口",
                         "两类缺口性质不同，混在一起给不出可执行的清单")

    def test_hard_gate_gaps_flag_what_cannot_be_changed(self):
        t = text()
        self.assertIn("改不了", t,
                      "改不了的硬门不该写进学习计划——写了只是让人难受")

    def test_already_have_but_not_on_resume_is_not_a_learning_task(self):
        """「会但没写上去」是改简历的事，一天；混进学习计划会让计划虚长几个月。"""
        t = text()
        self.assertIn("会但没写上去", t)
        self.assertIn("resume_insight", t,
                      "该直接引用总览页算好的结论，不要重算")

    def test_the_referenced_function_actually_exists(self):
        """引用别处的实现就得保证它在——否则是一条断掉的指路。"""
        self.assertIn("def resume_insight(", EXPORT.read_text(encoding="utf-8"))


class OutcomesAreTheGroundTruth(unittest.TestCase):
    def test_tracker_is_used_for_calibration_when_present(self):
        t = text()
        self.assertIn("地面真值", t, "投递结果是唯一能校准这份计划的东西")
        self.assertRegex(t, r"样本\s*<\s*5|样本太小",
                         "样本小的时候只能陈述不能下结论")

    def test_absence_of_calibration_must_be_stated(self):
        t = text()
        self.assertIn("尚未被任何投递结果校准", t,
                      "没有校准数据是这份计划最大的不确定性，不能默不作声")


if __name__ == "__main__":
    unittest.main()
