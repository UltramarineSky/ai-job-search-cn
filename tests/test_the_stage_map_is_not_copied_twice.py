# -*- coding: utf-8 -*-
"""面试阶段地图有正本也有抄件，而抄件把 10 关压成了 3 关。

`07-interview-prep.md`「一、国内面试阶段地图」是正本，10 行，每行带
「谁面 / 主要考察 / 应对要点」。而 `job-interview.md` Step 3.1 第 4 点
自己又写了一句：

    电话初筛问动机和时间线；专业面问职位描述里那套技术；
    终面问价值观、薪资，以及「你还有什么顾虑」。

丢的不是细节，是**四整关**加**一句会花掉他几万块的错话**：

| 抄件 | 正本 | 代价 |
|---|---|---|
| 薪资在**终面** | **HR 初面就「薪资摸底」**，另有独立的「谈薪」关 | 初筛电话里那句「你现在多少」当场把议价区间锚死，而 `/job-offer` 的谈薪打法要几周之后才跑 |
| 初筛问「动机和时间线」 | HR 初面考**稳定性、离职原因**、薪资摸底 | 「为什么离职」是国内 HR 一面必答题，抄件里整条没有 |
| （没有） | 在线测评 / 笔试机试 / 群面无领导 / 演练实操 | 正本对其中两关明写「**STAR 案例在这一关用不上**」，而 3.2 无条件发 STAR —— 笔试是校招刷人最多的一关 |
| （没有） | 交叉面、背调 | 背调那行是全表唯一一条红线（口头报的薪资要经得起个税 APP 记录核对） |

## 这一轮做了什么

1. **3.1 第 4 点不再复述**，改成「照那张表现查」，并把上面这张分叉表原样记下来
   —— 抄件删掉不写理由，下一个人会「顺手」再抄一份。
2. **3.2 加一道岔口**：先看这一关是不是那三类不用 STAR 的，是的话改产出那一关
   真正要备的东西（题型、时长、评分表、用物）。

## 为什么不是「把抄件补全」

补全就是抄第二遍。正本每加一关、每改一句应对要点，抄件都不会跟着动 ——
这个仓库为「一条规则两份实现」反复付过学费。
"""
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
IV = (ROOT / "workflows" / "job-interview.md").read_text(encoding="utf-8")
REF = (ROOT / "workflows" / "reference"
       / "07-interview-prep.md").read_text(encoding="utf-8")


def flat(s: str) -> str:
    s = " ".join(re.sub(r"^\s*(?:>|#:?)\s?", "", s, flags=re.M).split())
    return re.sub(r"(?<=[一-鿿，。；：、（）「」])"
                  r" +(?=[一-鿿，。；：、（）「」])", "", s)


def seg(start: str, end: str) -> str:
    i = IV.index(start)
    return flat(IV[i:IV.index(end, i)])


class TheOriginalStillHasAllTenStages(unittest.TestCase):
    """整条改动建立在「正本更全」上。正本瘦了，这条就该重看。"""

    def _rows(self):
        i = REF.index("| 阶段 | 谁面 | 主要考察 | 应对要点 |")
        body = REF[i:REF.index("\n\n", REF.index("| **背调**", i))]
        return [r for r in body.splitlines() if r.startswith("| **")]

    def test_it_is_still_the_longer_one(self):
        self.assertGreaterEqual(len(self._rows()), 10,
                                "正本关数变少了 —— 去看是不是被谁精简了")

    def test_the_stages_the_abstract_dropped_are_all_there(self):
        got = " ".join(self._rows())
        for k in ("在线测评", "笔试 / 机试", "群面 / 无领导小组",
                  "演练 / 实操 / 试讲", "交叉面", "背调"):
            with self.subTest(k=k):
                self.assertIn(k, got)

    def test_salary_is_probed_at_the_first_hr_round(self):
        """**这是整条最贵的一格。** 它挪走了，上面那张分叉表就要重写。"""
        row = next(r for r in self._rows() if "HR 初面" in r)
        self.assertIn("薪资摸底", row)
        self.assertIn("先别报死区间", row)

    def test_leaving_reason_is_a_first_round_question(self):
        row = next(r for r in self._rows() if "HR 初面" in r)
        self.assertIn("离职原因", row)

    def test_two_stages_say_star_does_not_apply(self):
        """两行措辞不完全一样（一行写「这一关」、一行写「这里」），
        所以按**行**数，不按字面串数 —— 3.2 那道岔口引的就是这两行。"""
        rows = [r for r in self._rows() if "STAR 案例在这" in r and "用不上" in r]
        self.assertEqual(
            len(rows), 2,
            f"正本里说「STAR 用不上」的关变成了 {len(rows)} 个 —— "
            f"3.2 那道岔口该跟着改")
        self.assertTrue(any("笔试" in r for r in rows))
        self.assertTrue(any("演练" in r for r in rows))

    def test_the_ordinal_warning_is_still_there(self):
        """3.1 现在直接指着它。它没了，那句「别从序数推」就落空了。"""
        self.assertIn("「二面」不是这张表里的一行", REF)
        self.assertRegex(flat(REF), r"这一关是谁面你？")


class TheWorkflowNoLongerKeepsACopy(unittest.TestCase):
    def _seg(self):
        return seg("4. **这一关是什么性质**", "### 3.2 STAR 案例怎么对上题")

    def test_it_points_at_the_canonical_table(self):
        s = self._seg()
        self.assertIn("07-interview-prep.md", s)
        self.assertIn("一、国内面试阶段地图", s)

    def test_it_says_it_will_not_restate(self):
        """不写这句，下一个人会「顺手」再摘一份要点进来。"""
        self.assertRegex(self._seg(), r"这里不复述那张表")

    def test_the_old_three_stage_sentence_is_gone(self):
        self.assertNotIn("终面问价值观、薪资，以及「你还有什么顾虑」", IV)
        self.assertNotIn("电话初筛问动机和时间线", IV)

    def test_it_tells_you_to_identify_the_row_first(self):
        """表是按身份索引的，而 HR 通知里写的是序数 —— 不定行就查不了表。"""
        s = self._seg()
        self.assertRegex(s, r"先定这一关是表里哪一行，别从序数推")
        self.assertRegex(s, r"这一关是谁面你？")

    def test_it_has_a_fallback_when_the_round_is_unknown(self):
        """问不出来是常事。只给「去问」等于把流程停在这儿。"""
        self.assertRegex(self._seg(), r"按 07 那条的降级走")

    def test_the_divergence_is_recorded(self):
        """删掉抄件不写它丢过什么，这条规矩活不过下一次编辑。"""
        s = self._seg()
        self.assertRegex(s, r"抄件把 10 关压成了 3 关")
        self.assertRegex(s, r"抄件必分叉")

    def test_it_names_the_salary_cost(self):
        s = self._seg()
        self.assertRegex(s, r"当场锚死")
        self.assertRegex(s, r"那时已经晚了几周")

    def test_it_names_the_four_lost_stages(self):
        s = self._seg()
        for k in ("在线测评", "笔试", "群面", "演练"):
            with self.subTest(k=k):
                self.assertIn(k, s)

    def test_it_names_the_backcheck_red_line(self):
        self.assertRegex(self._seg(), r"个税 APP 记录核对")

    def test_the_other_three_sources_survive(self):
        """第 4 点是四个来源里的一个，别把另外三个挤掉。"""
        s = seg("从四个来源推", "### 3.2 STAR 案例怎么对上题")
        self.assertIn("前几关记下的反馈", s)
        self.assertIn("匹配评估里的缺口", s)
        self.assertIn("职位描述里明写的要求", s)


class TheStarStepHasAFork(unittest.TestCase):
    """**这是抄件那四关缺失的实际后果。** 补上指针还不够，得让 3.2 分岔。"""

    def _seg(self):
        return seg("### 3.2 STAR 案例怎么对上题", "### 3.3 口径对照单")

    def test_it_checks_which_round_first(self):
        self.assertRegex(self._seg(), r"先看第 1 点定出来的是哪一关")

    def test_it_names_the_three_rounds_that_do_not_use_star(self):
        s = self._seg()
        for k in ("笔试 / 机试", "演练 / 实操 / 试讲", "在线测评"):
            with self.subTest(k=k):
                self.assertIn(k, s)

    def test_it_says_what_to_produce_instead(self):
        """只说「不用 STAR」，这一节就空了 —— 要给他那一关真正要备的。"""
        s = self._seg()
        self.assertRegex(s, r"题型、时长、能不能用 IDE")
        self.assertRegex(s, r"按哪一版评分表")

    def test_it_forbids_making_those_details_up(self):
        """题型时长评分表都是要**问**的，编一个比不写更糟。"""
        self.assertRegex(self._seg(), r"别自己编")

    def test_it_says_why_it_matters(self):
        self.assertRegex(self._seg(), r"校招刷人最多的那一关")

    def test_the_star_path_itself_survives(self):
        """岔口是加在前面的，原来那条主路一个字不动。

        **验那条指令，不验文件名。** 第一版只查 `profile/interview-star.md`
        出现过 —— 而这一节里它出现**两次**（一次是「去拿」、一次是「点头后
        追加进去」），于是把「去拿」那句整个删掉，测试照样全绿（变异实测）。
        """
        s = self._seg()
        self.assertRegex(s, r"拿 `profile/interview-star\.md` 里现成的 STAR 案例")
        self.assertRegex(s, r"「本条可答的问题类型」标签")
        self.assertRegex(s, r"绝不加工|不加工")
        self.assertRegex(s, r"只有用户明确点头")


class TheDownstreamStepsAreUntouched(unittest.TestCase):
    """这一条只动 3.1 与 3.2。别的步骤一个字都不该变。"""

    def test_the_questions_step_still_reads_the_evaluation(self):
        self.assertRegex(flat(IV), r"先把 `evaluation\.md` 的「投前必问」搬过来")

    def test_the_questions_step_still_judges_by_who_can_answer(self):
        self.assertRegex(flat(IV), r"这一关坐在对面的人答不答得了")

    def test_the_mock_interview_still_follows_the_reference(self):
        self.assertRegex(flat(IV), r"严格照 `07-interview-prep\.md` 的模拟面规程")


class TheSignalItLeansOnIsReal(unittest.TestCase):
    """现算：这两处此前真的对不上，而且现在真的只剩一份。"""

    def test_the_workflow_no_longer_lists_stages_of_its_own(self):
        """**判据是「有没有第二张按关分类的清单」**，不是某几个词在不在。

        抄件的形状是「A 关问 X；B 关问 Y；C 关问 Z」—— 一句话里塞三个以上
        「某关问某某」。这条扫的就是那个形状。
        """
        bad = [ln for ln in IV.splitlines()
               if len(re.findall(r"(初筛|初面|专业面|业务面|终面|交叉面|群面|笔试)"
                                 r"[^；。\n]{0,12}(问|考|考察)", ln)) >= 3]
        self.assertEqual(bad, [], f"又出现了一份按关分类的清单：{bad}")

    def test_the_salary_word_now_reaches_the_interview_flow(self):
        """此前 `/job-interview` 全文 0 次提薪资摸底 —— 而它是一面就问的。"""
        self.assertIn("薪资摸底", IV)

    def test_the_reference_is_the_only_place_with_the_table(self):
        """整张表只许有一份。哪天别处也画一张，这条会红。"""
        hits = []
        for f in sorted((ROOT / "workflows").rglob("*.md")):
            if f.name == "07-interview-prep.md":
                continue
            if "| 阶段 | 谁面 |" in f.read_text(encoding="utf-8", errors="replace"):
                hits.append(f.name)
        self.assertEqual(hits, [], f"这几处也画了那张表：{hits}")


if __name__ == "__main__":
    unittest.main()
