# -*- coding: utf-8 -*-
"""Step 3 那张比较表要两个 offer 同时在手，而没有一步负责促成它。

`/job-offer` 的 Step 3 是「多个 offer 横向比较」，写得很细：同一把尺、
四维打分、总分差 ≤5 算持平、不可逆项单列。**可它整个建立在一个前提上** ——
两个 offer 同时摆在桌上。

在国内那个前提不是自然发生的，是答复期决定的：offer 普遍带一个几天的期限
（口头多半只给一句「你尽快定」），而另一家还在走流程。不去问期限、不去谈
延期、不去拿它催那一家，这张表多数时候根本摆不出来。

实测 2026-08-25，`job-offer.md` 全文：

    答复期   0 命中
    有效期   0 命中
    宽限     0 命中
    延期     0 命中

整份文件里唯一和时间沾边的是 Step 4 的「入职日期」和试用期法定上限 —— 那是
点头**之后**的事。

## 三件事，一件都不能省

    问出一个日期        「尽快」不是期限，要问出日期来
    那个日期可以谈      没有法律规定 offer 有几天有效期，是对方自己写的
    它是加速别家的杠杆  国内唯一有效的催法，因为它给了对方推动审批的理由

第三件要和「拿另一家的报价压薪资」分开：前者只是陈述一个事实，后者是报价
博弈，谈砸了两边都可能收手。

## 记在 `notes`，不新开一列

台账里已经有一列（`contact_person`）是「有人读、没人写」的活教训 ——
再加一列没人填的只会重演。
"""
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
OFFER = (ROOT / "workflows" / "job-offer.md").read_text(encoding="utf-8")
OUT = (ROOT / "workflows" / "job-outcome.md").read_text(encoding="utf-8")
APPLY = (ROOT / "workflows" / "job-apply.md").read_text(encoding="utf-8")


def flat(s: str) -> str:
    s = " ".join(re.sub(r"^\s*(?:>|#:?)\s?", "", s, flags=re.M).split())
    return re.sub(r"(?<=[一-鿿，。；：、（）「」])"
                  r" +(?=[一-鿿，。；：、（）「」])", "", s)


def seg() -> str:
    i = OFFER.index("## Step 0.5: 先问出一个日期")
    return flat(OFFER[i:OFFER.index("## Step 1: 算可守区间", i)])


class ItSitsWhereItIsUsable(unittest.TestCase):
    def test_the_step_exists(self):
        self.assertIn("## Step 0.5: 先问出一个日期 —— 它决定后面几步跑不跑得完",
                      OFFER)

    def test_it_comes_before_the_money(self):
        """**顺序就是判据。** 期限管着后面每一步排不排得下。"""
        self.assertLess(OFFER.index("## Step 0: 守卫与取数"),
                        OFFER.index("## Step 0.5:"))
        self.assertLess(OFFER.index("## Step 0.5:"),
                        OFFER.index("## Step 1: 算可守区间"))

    def test_it_says_it_is_the_first_thing(self):
        self.assertRegex(seg(), r"拿到 offer 之后第一件事不是算薪资")

    def test_it_carries_the_zero_hit_measurement(self):
        s = seg()
        self.assertIn("2026-08-25", s)
        for w in ("答复期", "有效期", "宽限", "延期"):
            with self.subTest(w=w):
                self.assertIn(w, s)
        self.assertRegex(s, r"一个都没有")

    def test_those_words_appear_nowhere_else_in_the_file(self):
        """**自引陷阱。** 那句实测说的是「这一节之外没有」——现算一遍。

        修好之后这条仍然成立：新写的字全在这一节和 Step 3 那个指针里。
        哪天别处也开始讲答复期，两处就该合并，这条会红。
        """
        i = OFFER.index("## Step 0.5:")
        j = OFFER.index("## Step 1: 算可守区间")
        k = OFFER.index("## Step 3: 多个 offer 横向比较")
        m = OFFER.index("**用同一把尺**")
        outside = OFFER[:i] + OFFER[j:k] + OFFER[m:]
        for w in ("答复期", "有效期", "宽限", "延期"):
            with self.subTest(w=w):
                self.assertNotIn(w, outside)


class ItGetsAnActualDate(unittest.TestCase):
    def test_it_says_soon_is_not_a_deadline(self):
        self.assertRegex(seg(), r"「尽快」不是期限")

    def test_it_gives_the_words_to_ask_with(self):
        """只说「去问」他张不开口 —— 这份文件通篇给的是可以照着说的话。"""
        self.assertIn("这个 offer 最晚什么时候答复？", OFFER)

    def test_the_fallback_is_a_scheduling_aid_not_a_rule(self):
        """三天是常见下限，不是规矩 —— 写死成规矩会让人早两天慌。"""
        s = seg()
        self.assertRegex(s, r"三个工作日")
        self.assertRegex(s, r"三天是常见下限，不是规矩")

    def test_it_says_to_ask_again(self):
        self.assertRegex(seg(), r"在下一次沟通里再问一次")


class TheDateIsNegotiable(unittest.TestCase):
    """**这是这一节最值钱的一句。** 不说，多数人会把它当成硬期限。"""

    def test_it_says_there_is_no_law_behind_it(self):
        self.assertRegex(seg(), r"没有哪条法律规定 offer 有几天有效期")

    def test_it_says_why_hr_usually_agrees(self):
        """给理由，不然读的人不敢开口。"""
        self.assertRegex(seg(), r"他们那边同样卡在审批、背调、入职批次上")

    def test_it_gives_the_wording(self):
        self.assertIn("能不能宽限到周五？", OFFER)

    def test_it_forbids_inventing_a_competing_offer(self):
        """编一个不存在的 offer 是这一节唯一能把事办砸的做法。"""
        s = seg()
        self.assertRegex(s, r"\*\*别编一个不存在的 offer 去要期限。\*\*")
        self.assertRegex(s, r"被戳穿的代价是这个 offer 当场没了")

    def test_it_says_why_that_is_checkable(self):
        """理由不是道德，是「对方核得到」—— 那才拦得住人。"""
        self.assertRegex(seg(), r"同一个岗常有两家猎头在推")

    def test_the_thing_it_cites_is_real(self):
        """引的是 `/job-apply` 那一节 —— 它没了，这句话就成了空话。"""
        self.assertRegex(flat(APPLY), r"两边猎头撞车对候选人是减分的")

    def test_no_competing_offer_is_still_a_valid_reason(self):
        """没有别家就不敢要期限，是这条禁令最容易带出的副作用。"""
        self.assertRegex(seg(), r"没有别家就直说需要时间做决定")

    def test_a_hard_no_is_taken_at_face_value(self):
        self.assertRegex(seg(), r"那就是真期限.{0,20}别赌")


class ItIsAlsoTheLeverOnTheOtherCompany(unittest.TestCase):
    def test_it_names_the_lever(self):
        self.assertRegex(seg(), r"这个日期是你唯一能加速别家的杠杆")

    def test_it_gives_the_wording(self):
        self.assertIn("流程上有没有可能往前赶一赶？", OFFER)

    def test_it_says_why_it_works(self):
        """在国内管用是有原因的 —— 说出来，他才会用。"""
        self.assertRegex(seg(), r"给了对方一个\*\*可以拿去推动内部审批的理由\*\*")

    def test_it_routes_the_drafting_to_the_command(self):
        s = seg()
        self.assertIn("/job-outcome followup", s)
        self.assertRegex(s, r"要点名是哪一家、哪个日期")

    def test_that_command_really_drafts_follow_ups(self):
        self.assertIn("followup", OUT)
        self.assertRegex(flat(OUT), r"\*\*按用户自己的语气\*\*起草一条简短的跟进")

    def test_it_separates_this_from_squeezing_the_salary(self):
        """**两件事混起来最贵。** 一个是陈述事实，一个是报价博弈。"""
        s = seg()
        self.assertRegex(s, r"别拿它当筹码去压薪资")
        self.assertRegex(s, r"谈砸了两边都可能收手")
        self.assertRegex(s, r"两件事别混")


class TheClockSetsThePace(unittest.TestCase):
    def _rows(self):
        i = OFFER.index("| 手上还有 | 先做什么 |")
        return [r for r in OFFER[i:OFFER.index("\n\n", i)].splitlines()
                if r.strip().startswith("| **")]

    def test_there_are_three(self):
        self.assertEqual(len(self._rows()), 3)

    def test_the_shortest_one_keeps_the_unskippable_step(self):
        """「今天就要」也不许跳背调红线 —— 那一节自己写着不许跳过。"""
        r = next(r for r in self._rows() if "今天就要" in r)
        self.assertIn("Step 2", r)

    def test_it_says_why_that_one_survives(self):
        r = next(r for r in self._rows() if "今天就要" in r)
        self.assertRegex(flat(r), r"报错一个数字的代价，比晚一天答复大得多")

    def test_the_unskippable_step_still_says_so(self):
        self.assertIn("## Step 2: 背调红线自查（**这一节不许跳过**）", OFFER)

    def test_the_middle_one_lets_the_checklist_run_late(self):
        r = next(r for r in self._rows() if "三天左右" in r)
        self.assertRegex(flat(r), r"Step 4 的清单边谈边问，不必等齐")


class ItIsWrittenDownWithoutANewColumn(unittest.TestCase):
    """加一列没人填的，正是上一课的原样重演。"""

    def test_it_goes_into_notes(self):
        s = seg()
        self.assertRegex(s, r"写进 `job_search_tracker\.csv` 那一行的 `notes` 里")
        self.assertRegex(s, r"offer 答复期 2026-09-03")

    def test_it_refuses_a_new_column(self):
        s = seg()
        self.assertRegex(s, r"\*\*不要为它新开一列\*\*")
        self.assertIn("contact_person", s)

    def test_the_lesson_it_cites_is_real(self):
        """`contact_person` 真的是那个教训 —— 它被修好了这条也仍然成立。"""
        self.assertIn("### 顺手把对方的姓名记下来（`contact_person` 列）", OUT)

    def test_the_column_list_did_not_grow(self):
        """现算：台账表头还是那 13 列，没被这一条顶出第 14 列。"""
        import sys
        sys.path.insert(0, str(ROOT / "tools"))
        head = re.search(r"date,company,sector,[^\n]+", OUT)
        self.assertTrue(head)
        self.assertNotIn("deadline", head.group(0))
        self.assertNotIn("offer_due", head.group(0))


class TheComparisonStepPointsBack(unittest.TestCase):
    def _lead(self) -> str:
        i = OFFER.index("## Step 3: 多个 offer 横向比较")
        return flat(OFFER[i:OFFER.index("**用同一把尺**", i)])

    def test_it_says_the_premise_is_not_free(self):
        self.assertRegex(self._lead(),
                         r"两个 offer 同时在手不是自然发生的，是 Step 0\.5 争取来的")

    def test_it_says_what_to_do_with_only_one(self):
        """否则读到这里手上只有一个的人会以为自己该干等。"""
        self.assertRegex(self._lead(), r"手上只有一个时先回 Step 0\.5，别在这里干等")

    def test_the_step_it_points_at_exists(self):
        self.assertIn("## Step 0.5:", OFFER)

    def test_the_comparison_table_itself_is_untouched(self):
        """这是加一段引子，那张表一个字不许动。"""
        self.assertIn("**用同一把尺**", OFFER)
        self.assertRegex(flat(OFFER), r"总分差 ≤5 视为持平")
        self.assertRegex(flat(OFFER), r"\*\*年包一样不等于到手一样。\*\*")


class TheDateIsCapturedWhenItIsKnown(unittest.TestCase):
    """他刚跟 HR 聊完，那句话就在眼前；等跑 `/job-offer` 时已经要去翻记录。"""

    def _seg(self) -> str:
        i = OUT.index("**同一轮里还要问出一个日期")
        return flat(OUT[i:OUT.index("`/job-offer` 后面几步怎么排", i) + 200])

    def test_the_ask_is_there(self):
        self.assertRegex(self._seg(), r"这个 offer 最晚什么时候答复？")

    def test_it_says_why_now_and_not_later(self):
        s = self._seg()
        self.assertRegex(s, r"此刻他刚跟 HR 聊完，那句话就在眼前")
        self.assertRegex(s, r"多半已经要回去翻聊天记录")

    def test_it_writes_to_notes_too(self):
        self.assertRegex(self._seg(), r"写进这一行的 `notes`")
        self.assertRegex(self._seg(), r"\*\*不新开一列\*\*")

    def test_it_does_not_become_a_required_question(self):
        """这一步是记结果的，别把可选补充变成必答题（同一节的既有边界）。"""
        self.assertRegex(self._seg(), r"问不出来别追")
        self.assertRegex(flat(OUT), r"\*\*这一步不许改 `status`\*\*")

    def test_it_points_at_the_one_source_of_truth(self):
        """判据只留一份 —— 这里不复述 Step 0.5 那三件事。"""
        s = self._seg()
        self.assertRegex(s, r"判据都在 `job-offer\.md` 的「Step 0\.5」那一节")
        self.assertNotIn("没有哪条法律", s)

    def test_the_neighbouring_prompt_survives(self):
        """「谈薪准备要发生在报数字之前」是这一段原有的话，别挤掉。"""
        self.assertRegex(flat(OUT), r"谈薪的准备必须发生在报数字\*\*之前\*\*")


if __name__ == "__main__":
    unittest.main()
