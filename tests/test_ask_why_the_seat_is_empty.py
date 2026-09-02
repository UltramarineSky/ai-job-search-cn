# -*- coding: utf-8 -*-
"""反问清单里缺了国内信息量最大的那一条：这个岗为什么空着。

`07-interview-prep.md` 的反问清单写得很全 —— 岗位、团队、技术、文化、
待遇（薪资结构 / 公积金 / 试用期 / 流程时间线，还有「哪一轮问什么本身是一道
考题」和优先级）。但整份清单里没有一条问**这个位置为什么空着**。

实测 2026-08-23：全仓 `新设` / `替补` / `为什么空缺` / `上一位` / `前任` /
`离职率` **一次都没出现过**。

两种答案要接的下一句完全不同，而这决定了这个岗值不值得继续：

    新增 → 方向可能还没定、预算只批到年底，做半年被并掉
    替补 → 上一位做了多久？只做几个月、或者「换过几个人了」，问题多半不在人身上

## 它和第三步「蓄水池嫌疑」是同一件事的两面

框架第三步看的是**这条职位在被怎样发布**（反复顶上去却一直没招到）；
这一条问的是**这个位置为什么空着**。两边都指向同一个问题时，
那就不是发布方式的事了。

## 顺带修掉一处它自己引发的冲突

`job-interview.md` Step 3.5 的默认档是「初筛问岗位与团队，专业面问技术与成长」——
而这一条归在「关于岗位」，照那句会被排进 **HR 初筛**，恰恰是它最问不出东西的
一轮（HR 通常只知道有这个 headcount，不知道人为什么走）。
那一节本来就有正确的判据在下面（「**这一关答不了的**……都是把问题递错了人」），
只是上面那句默认档会先把它排错。所以给默认档加了一句：分类只是默认档，
真正的判据是这一关的人答不答得了。
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PREP = (ROOT / "workflows" / "reference"
        / "07-interview-prep.md").read_text(encoding="utf-8")
JI = (ROOT / "workflows" / "job-interview.md").read_text(encoding="utf-8")
EVAL = (ROOT / "workflows" / "reference"
        / "04-job-evaluation.md").read_text(encoding="utf-8")


def about_the_job() -> str:
    i = PREP.index("**关于岗位**")
    return PREP[i:PREP.index("**关于团队**", i)]


class TheQuestionExists(unittest.TestCase):
    def test_it_is_in_the_list(self):
        self.assertIn("「这个岗是新增的，还是有人走了补上来的？」", about_the_job(),
                      "反问清单里仍然没有一条问这个位置为什么空着")

    def test_it_is_first_in_its_group(self):
        """信息量最大的排第一 —— 反问只有几分钟，顺序就是优先级。"""
        seg = about_the_job()
        self.assertLess(seg.index("新增的，还是有人走了补上来的"),
                        seg.index("日常的工作节奏"))

    def test_both_answers_have_a_follow_up(self):
        """只问不接，等于什么也没问到。两种答案各要接一句。"""
        seg = " ".join(about_the_job().split())
        self.assertRegex(seg, r"\*\*新增\*\* → 「这条线是什么时候立的？")
        self.assertRegex(seg, r"\*\*替补\*\* → 「上一位在这个位置上做了多久？」")

    def test_each_follow_up_says_what_the_answer_means(self):
        """给个问题不给判读，用户听完还是不知道该怎么想。"""
        seg = " ".join(about_the_job().split())
        self.assertRegex(seg, r"预算只批到年底，做半年被并掉")
        self.assertRegex(seg, r"问题多半不在人身上")

    def test_it_says_which_round_to_ask_in(self):
        seg = " ".join(about_the_job().split())
        self.assertRegex(seg, r"在用人部门那一轮问，不在 HR 面问")
        self.assertRegex(seg, r"HR 通常只知道有这个 headcount")

    def test_it_treats_the_dodge_as_a_signal(self):
        """答不答得痛快本身是信息 —— 这一句是这条问题真正的杠杆。"""
        self.assertRegex(" ".join(about_the_job().split()),
                         r"痛快说还是绕开——本身就是一条信号")

    def test_it_cites_the_rule_it_leans_on(self):
        """「哪一轮问什么本身是一道考题」是既有规则，引它、别另立一条。"""
        self.assertIn("哪一轮问什么本身是一道考题", about_the_job())
        self.assertIn("**哪一轮问什么，本身就是一道考题。**", PREP)

    def test_it_links_to_the_posting_side_signal(self):
        seg = about_the_job()
        self.assertIn("蓄水池嫌疑", seg)
        self.assertRegex(" ".join(seg.split()),
                         r"那条看\*\*这条职位在被怎样发布\*\*")

    def test_the_posting_side_signal_really_exists(self):
        """引了框架那一条，它得真的在。"""
        self.assertIn("| **蓄水池嫌疑** |", EVAL)

    def test_the_overtime_question_keeps_its_note(self):
        """顺手补的那半句：国内直接问「要不要加班」是减分的。"""
        self.assertRegex(" ".join(about_the_job().split()),
                         r"国内直接问「要不要加班」是减分的")

    def test_the_rest_of_the_group_survives(self):
        seg = about_the_job()
        for q in ("日常的工作节奏", "成功的标准是什么", "最大挑战是什么"):
            with self.subTest(q=q):
                self.assertIn(q, seg)


class TheRoundMappingDoesNotMisrouteIt(unittest.TestCase):
    def _s35(self) -> str:
        i = JI.index("### 3.5 你该问他们什么")
        return JI[i:JI.index("### 3.6 时间地点这些", i)]

    def test_the_default_is_marked_as_a_default(self):
        self.assertRegex(" ".join(self._s35().split()),
                         r"分类只是默认档")

    def test_the_real_criterion_is_who_can_answer(self):
        self.assertRegex(" ".join(self._s35().split()),
                         r"这一关坐在对面的人答不答得了")

    def test_the_exception_is_named(self):
        seg = self._s35()
        self.assertIn("这个岗是新增的还是有人走了补上来的", seg)
        self.assertRegex(" ".join(seg.split()), r"这一条要留到用人部门那一轮")

    def test_it_points_at_the_judgement(self):
        self.assertIn("07-interview-prep.md", self._s35())

    def test_the_default_mapping_itself_survives(self):
        """默认档没被删掉 —— 它对其余几组仍然是对的。"""
        self.assertIn("初筛问岗位与团队，", self._s35())
        self.assertIn("专业面问技术与成长", self._s35())

    def test_the_existing_wrong_recipient_rule_survives(self):
        """下面那条本来就对，这次只是让它不被上面那句抢先排错。"""
        self.assertIn("都是把问题递错了人", self._s35())

    def test_the_must_ask_section_still_comes_first(self):
        """反问的主体是 `evaluation.md` 的「投前必问」，分类只是补足。"""
        seg = self._s35()
        self.assertLess(seg.index("投前必问"), seg.index("分类只是默认档"))


class TheInterviewCommandStillReadsTheReference(unittest.TestCase):
    """这一条加在 `07` 里。`/job-interview` 不读它的话，等于没加。"""

    def test_it_reads_the_reference(self):
        self.assertIn("workflows/reference/07-interview-prep.md", JI)

    def test_the_prep_pack_has_a_reverse_question_section(self):
        self.assertIn("### 3.5 你该问他们什么", JI)

    def test_the_stage_map_still_distinguishes_the_rounds(self):
        """「用人部门那一轮」要是分不出来，这条就落不了地。"""
        for role in ("HR 初面", "专业面 / 业务面"):
            with self.subTest(role=role):
                self.assertIn(role, PREP)


if __name__ == "__main__":
    unittest.main()
