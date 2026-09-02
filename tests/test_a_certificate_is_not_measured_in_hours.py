# -*- coding: utf-8 -*-
"""`[credential]` 是四个缺口标签之一 —— 而学习计划对它和其它三类做一样的事。

`/job-upskill` Step 4 给每个缺口打标：`[domain]`（领域）、`[soft]`（软技能）、
`[tooling]`（工具/流程）、**`[credential]`（资格证书）**。分类是有的。

而 Step 6「做学习计划」对**每个**缺口都走同一套四步：搜「培训 课程」找资源、
挑 2-3 个、给一条「你已经会 X，入门那几节跳过」的路线、估「约 20 小时」。
对资格证这四条全不成立：

- 搜「培训 课程」搜不到**报名简章**，而报名条件才是第一道门；
- 「跳过入门」对固定考纲不适用；
- **最要命的是估法本身**：资格证的瓶颈不是学多久，是**考试窗口** ——
  一年考一到两次、报名截止在考试前一两个月、考完出成绩再等几个月。
  学得再快也不改那个日期。

全仓扫过（2026-08-23）：`报名条件` / `考试时间` / `报考` / `考试窗口` /
`通过率` / `出成绩` **一次都没出现**。

## 评估那一侧早就要这个数

`04-job-evaluation.md` 对「候选人正在考、或有等效资格」判 FLAG，
并要求写清「差距与**取得周期**」。**取得周期怎么算，没有任何一处说过** ——
这一支补的就是它，两边说的是同一个东西。

## 也管「算不出来就别列进计划」

`job-upskill.md` Step 4.5 已经立过判据：不是学习问题就不要答成学习任务。
最早拿证日期超出这一轮求职周期时，那批岗**现在就是关着的**，
该做的是选岗 —— 硬凑一条「先学起来」是让他为一道够不着的门做无用功。
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UP = (ROOT / "workflows" / "job-upskill.md").read_text(encoding="utf-8")
EVAL = (ROOT / "workflows" / "reference"
        / "04-job-evaluation.md").read_text(encoding="utf-8")


def branch() -> str:
    i = UP.index("### `[credential]` 那一类走另一套")
    return UP[i:UP.index("### 按主题归组", i)]


class TheBranchExists(unittest.TestCase):
    def test_it_is_there(self):
        self.assertIn("### `[credential]` 那一类走另一套 —— 它不是按小时算的", UP,
                      "学习计划仍然对资格证按小时估")

    def test_it_sits_inside_step_six(self):
        self.assertLess(UP.index("## Step 6：做学习计划"),
                        UP.index("### `[credential]` 那一类走另一套"))
        self.assertLess(UP.index("### `[credential]` 那一类走另一套"),
                        UP.index("## Step 7"))

    def test_it_comes_after_the_generic_four_steps(self):
        """它是那四步的例外，摆在前面读不通。"""
        self.assertLess(UP.index("### 每个缺口都做这几步："),
                        UP.index("### `[credential]` 那一类走另一套"))

    def test_it_names_why_each_of_the_four_steps_fails(self):
        seg = " ".join(branch().split())
        self.assertRegex(seg, r"搜「培训 课程」搜不到 报名简章|搜「培训 课程」搜不到报名简章")
        self.assertRegex(seg, r"对固定考纲不适用")
        self.assertRegex(seg, r"瓶颈从来不是学多久，是\*\*考试窗口\*\*")

    def test_the_binding_constraint_is_stated(self):
        """这一句是整支的支点：学得再快也不改那个日期。"""
        self.assertRegex(" ".join(branch().split()),
                         r"学得再快也不改那个日期")


class TheFourFactsAreEnumerated(unittest.TestCase):
    def test_there_are_four_rows(self):
        rows = [ln for ln in branch().splitlines()
                if ln.strip().startswith("|") and "---" not in ln
                and "为什么要查" not in ln]
        self.assertEqual(len(rows), 4, f"不是四行：{len(rows)}")

    def test_each_row_says_what_happens_if_you_skip_it(self):
        """只列「要查什么」，读的人不会真去查。"""
        rows = [ln for ln in branch().splitlines()
                if ln.strip().startswith("|") and "---" not in ln
                and "为什么要查" not in ln]
        for r in rows:
            with self.subTest(row=r[:24]):
                self.assertEqual(r.count("|"), 4, f"这一行没有三格：{r}")
                self.assertTrue(r.split("|")[3].strip(), "「不查的后果」是空的")

    def test_the_four_are_the_right_four(self):
        seg = " ".join(branch().split())
        for w in ("报名条件", "考试时间与报名截止", "出成绩与领证周期",
                  "成绩有效期 / 滚动周期"):
            with self.subTest(w=w):
                self.assertIn(w, seg)

    def test_the_registration_gate_comes_first(self):
        """够不够格报名是第一道门 —— 排在后面读的人会先去背书。"""
        seg = branch()
        self.assertLess(seg.index("报名条件"), seg.index("考试时间与报名截止"))

    def test_it_separates_this_from_course_hunting(self):
        self.assertRegex(" ".join(branch().split()),
                         r"都是公开可查的，和课程推荐是两回事")


class TheEstimateIsADate(unittest.TestCase):
    def test_it_says_a_date_not_hours(self):
        seg = " ".join(branch().split())
        self.assertRegex(seg, r"估的是「最早哪个月能拿到」，不是「约 N 小时」")

    def test_it_says_why_a_date(self):
        self.assertRegex(" ".join(branch().split()), r"他才排得了优先级")

    def test_the_generic_hour_estimate_still_applies_to_the_others(self):
        """这一支是例外，不是把小时估法废掉 —— 技能缺口照旧。"""
        i = UP.index("### 每个缺口都做这几步：")
        seg = UP[i:UP.index("### `[credential]`", i)]
        self.assertIn("估一个「学到能上手」要多久", seg)
        self.assertIn("约 20 小时", seg)


class TheOutOfReachCaseLeavesThePlan(unittest.TestCase):
    def test_it_says_to_drop_it(self):
        seg = " ".join(branch().split())
        self.assertRegex(seg, r"直接说出来，并把它移出学习计划")

    def test_it_says_what_to_do_instead(self):
        seg = " ".join(branch().split())
        self.assertRegex(seg, r"该做的是选岗，不是学习")
        self.assertRegex(seg, r"那批要这个证的岗\*\*现在就是关着的\*\*")

    def test_it_cites_the_existing_gate(self):
        """`job-upskill.md` Step 4.5 早就立过「不是学习问题就别答成学习任务」。引它，别另立。"""
        self.assertIn("判据同 Step 4.5", branch())

    def test_step_four_five_still_exists(self):
        self.assertIn("## Step 4.5：先判断这到底是不是「学习问题」（汇总模式必做）",
                      UP)

    def test_it_calls_the_padding_out(self):
        self.assertRegex(" ".join(branch().split()),
                         r"让他为一道够不着的门做无用功")


class TheTwoSidesAgree(unittest.TestCase):
    """评估那一侧要「取得周期」，这一侧算它。两边不能各估各的。"""

    def test_it_cites_the_evaluation_rule(self):
        seg = " ".join(branch().split())
        self.assertIn("04-job-evaluation.md", seg)
        self.assertRegex(seg, r"差距与\*\*取得周期\*\*")

    def test_the_evaluation_rule_really_says_that(self):
        self.assertIn("**FLAG**，写清差距与取得周期", EVAL)

    def test_it_forbids_two_estimates(self):
        self.assertRegex(" ".join(branch().split()), r"别各估各的")

    def test_the_certificate_gate_is_still_a_gate(self):
        """整支建立在「缺证是硬门、而且是能去考的」上。"""
        self.assertIn("### 执业资格 / 证照 / 职称：把「没有证」和「能力不足」分开",
                      EVAL)
        self.assertIn("缺证是能去考的", EVAL)


class TheTagAndTheHeatMapKnowIt(unittest.TestCase):
    def test_the_tag_exists(self):
        self.assertIn("`[credential]`（资格证书）", UP)

    def test_the_heat_map_shows_the_type(self):
        """热力图的类型示例里原来没有它 —— 示例决定执行者会写什么。"""
        i = UP.index("| 优先级 | 缺口 | 类型 | 依据 |")
        self.assertIn("资格证书", UP[i:i + 500])

    def test_the_grouping_rule_survives(self):
        self.assertIn("涉及资格证就单起「资质与证照」一组", UP)

    def test_no_industry_preset_sneaks_in(self):
        """这一支绝不能点名任何一个具体证书 —— 那等于假定用户是哪一行的。"""
        for cert in ("PMP", "注会", "法考", "教资", "一建", "软考", "CPA"):
            with self.subTest(cert=cert):
                self.assertNotIn(cert, branch())


if __name__ == "__main__":
    unittest.main()
