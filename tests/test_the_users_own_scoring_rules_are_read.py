# -*- coding: utf-8 -*-
"""资料模板 20 节，逐节找消费方 —— 两节没有。

这个仓库为这类事付过代价：「明确排除」那一节曾经**没有任何消费者**，
`/job-setup` 认真问了、认真写进了资料，而框架全文引用过其它七八节、
唯独没引用过它 —— 一位教师写下「明确排除：无编制的长期代课岗」，
一个编外合同制的岗照样满分落进「值得投」。

同一把尺子量下来，眼下还有两节零消费：

## 一、「因此，岗位筛选时的判据」

它就压在人人都读的「明确的能力边界」下面，写的是候选人**按关键词给打分器
的规则**：「JD 出现 X → 真实缺口，**不得用相近表述充数**」「JD 出现 Y →
真实强项」，还带「这类岗分两种判」的细则。比上面两节更直接：那两节要你自己推，
这一节直接给结论。

**但它不是死的 —— 这一点必须说清楚。** 实测 2026-08-23：命中该用户写的
「真实缺口」关键词的岗，技能分中位数 **38.5**；命中「真实强项」的 **58**，
差 20 分，方向完全对。规则**在生效**。

靠的是 `/job-rank` Step 1「整份资料读一遍」时的自觉 —— 而 Step 2 分发子代理时
只有枚举里的东西进得了提示（那一步明写着「不要让代理再去读一遍资料文件」）。
**能生效和被要求生效是两件事**：前者会在某次重写枚举时无声消失。

## 二、「发表与获奖」

`/job-setup` Section 5 专门问它，全仓只有 `job-setup.md` 自己提到它 ——
**写它的人就是唯一提到它的人**。而国内 JD 的加分项常点名
「有专利 / 论文 / 软著 / 获奖者优先」，那正是第 1.3 条加分项要匹配的东西。
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVAL = (ROOT / "workflows" / "reference"
        / "04-job-evaluation.md").read_text(encoding="utf-8")
RANK = (ROOT / "workflows" / "job-rank.md").read_text(encoding="utf-8")
TPL = (ROOT / "profile.example" / "candidate.md").read_text(encoding="utf-8")


def dim12() -> str:
    i = EVAL.index("#### 1.2 业务领域匹配")
    return EVAL[i:EVAL.index("#### 1.3", i)]


def bonus() -> str:
    i = EVAL.index("- **加分项修正**")
    return EVAL[i:i + 700]


class TheKeywordRulebookIsNamed(unittest.TestCase):
    def test_dimension_one_two_names_it(self):
        self.assertIn("因此，岗位筛选时的判据", dim12(),
                      "打分那一维仍然只点了「技能」「明确的能力边界」两节")

    def test_it_says_what_that_section_contains(self):
        """只给个节名，读的人不知道该拿它干什么。"""
        seg = " ".join(dim12().split())
        self.assertRegex(seg, r"按关键词写给打分器的规则")
        self.assertIn("不得用相近表述充数", seg)

    def test_it_says_why_that_section_outranks_the_other_two(self):
        seg = " ".join(dim12().split())
        self.assertRegex(seg, r"上面两节要你自己去推，这一节直接给结论")

    def test_it_admits_the_rule_already_works(self):
        """**不许把它写成「这条规则从没生效过」。** 实测是生效的 ——
        夸大缺陷会让下一个人照着一个假前提去改别处。"""
        seg = " ".join(dim12().split())
        self.assertRegex(seg, r"它是\*\*在生效的\*\*")
        self.assertRegex(seg, r"技能分中位数 38\.5")
        self.assertRegex(seg, r"命中「真实强项」的 58")

    def test_it_says_why_it_still_needs_naming(self):
        """「已经生效」正是这条最容易被当成多余删掉的理由。"""
        seg = " ".join(dim12().split())
        self.assertRegex(seg, r"能生效和被要求生效是两件事")
        self.assertRegex(seg, r"不要让代理再去读一遍资料文件")

    def test_it_carries_the_date(self):
        self.assertIn("2026-08-23", dim12())

    def test_it_handles_the_empty_case(self):
        """多数人这一节是空的 —— 不写清会逼着执行者硬找规则。"""
        self.assertRegex(" ".join(dim12().split()),
                         r"这一节是空的、或只有占位符 → 跳过")

    def test_the_two_original_sections_survive(self):
        seg = dim12()
        self.assertIn("「技能」「明确的能力边界」做差", seg)


class TheBatchPromptCarriesIt(unittest.TestCase):
    """分发给子代理时只有枚举里的东西进得了提示 —— 那份枚举必须点它的名。"""

    def _spec(self) -> str:
        i = RANK.index("每个代理要用的东西**全部写进提示里**")
        return RANK[i:RANK.index("\n- 每个代理用网页抓取能力", i)]

    def test_the_enumeration_names_it(self):
        self.assertIn("因此，岗位筛选时的判据", self._spec())

    def test_it_says_to_pass_it_verbatim(self):
        """蒸馏成「强/中/弱三类领域」会把结论降级成素材。"""
        seg = " ".join(self._spec().split())
        self.assertRegex(seg, r"原样带过去，别改写成三类领域")
        self.assertRegex(seg, r"它给的是结论，不是素材")

    def test_the_rest_of_the_enumeration_survives(self):
        seg = self._spec()
        for w in ("技能匹配的强/中/弱三类领域", "期望薪资区间与底线",
                  "硬门判据", "候选人自己划的「明确排除」"):
            with self.subTest(w=w):
                self.assertIn(w, seg)

    def test_the_no_reread_rule_survives(self):
        """整条论证建立在「代理只看提示」上。"""
        self.assertIn("**不要**让代理再去读一遍资料文件", self._spec())


class ThePublicationsSectionHasAConsumer(unittest.TestCase):
    def test_the_bonus_rule_names_it(self):
        self.assertIn("发表与获奖", bonus(),
                      "「发表与获奖」仍然只有写它的人提到它")

    def test_it_says_what_jds_actually_write(self):
        seg = " ".join(bonus().split())
        self.assertRegex(seg, r"有专利 / 论文 / 软著 / 获奖 / 行业评优者优先")

    def test_it_refuses_to_pad(self):
        """加分项是 +2 一条，最容易被拿别处的成果凑。"""
        self.assertRegex(" ".join(bonus().split()),
                         r"不要拿别处的成果去凑")

    def test_the_empty_case_is_covered(self):
        self.assertRegex(" ".join(bonus().split()), r"那一节是「无」就当没有")

    def test_the_bonus_arithmetic_survives(self):
        seg = bonus()
        self.assertIn("每命中一条 **+2**，最多 **+8**", seg)
        self.assertIn("一条都没命中时不扣分", seg)


class TheSectionsReallyExistInTheTemplate(unittest.TestCase):
    """引的两节要真在模板里 —— 不然是把执行者指向一个不存在的小节。"""

    def test_the_keyword_rulebook_is_a_template_section(self):
        """`^` 要按行匹配 —— 少了 `re.M` 它只认文件第一行。"""
        self.assertRegex(TPL, r"(?m)^#{3,4} 因此，岗位筛选时的判据")

    def test_it_sits_under_the_boundary_section(self):
        self.assertLess(TPL.index("## 明确的能力边界"),
                        TPL.index("因此，岗位筛选时的判据"))

    def test_the_publications_section_exists(self):
        self.assertIn("## 发表与获奖", TPL)

    def test_setup_still_collects_both(self):
        s = (ROOT / "workflows" / "job-setup.md").read_text(encoding="utf-8")
        for w in ("发表与获奖", "能力边界"):
            with self.subTest(w=w):
                self.assertIn(w, s, f"`/job-setup` 不再收「{w}」了")

    def test_the_precedent_is_still_on_the_record(self):
        """「明确排除」那次事故是这条检查存在的理由。"""
        self.assertIn("这一节原来**没有任何消费者**", EVAL)


if __name__ == "__main__":
    unittest.main()
