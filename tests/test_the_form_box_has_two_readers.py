# -*- coding: utf-8 -*-
"""渠道 3 的四段结构假设了读它的人是用人方，而路由把资格审查也送进来了。

`job-apply.md` 1.5a 把**三种东西**一起判成「无对话方」并路由到渠道 3：

    网申表单 / 校招官网 / 考编·事业单位报名系统

而这个框有**两种读者**：用人部门 / HR（判断你能不能干），和**资格审查人员**
（拿你填的字段逐条对招聘公告上的资格条件，对不上就出局）。

**别按渠道名字分。** 第一版就是按名字分的，当场被自己的守卫逮到：
「校招网申」两边都有 —— 大厂民企的校招看能力，国企银行事业单位的校招先过
资格审查。判据只能是**入口形态**：给的是一份带公告编号与报名起止时间的招聘公告，
还是一个 JD 页面。

而渠道 3 的第 3 段写着：

> **缺口与应对** —— 如实说明一个缺口，以及你打算怎么补。
> 这一段不是减分项：网申自评里主动谈缺口的人极少，反而显得可信。

**那句话在互联网/民企网申里成立，在形式审查那一关正好说反** ——
一条不符就是一条不符，写出来只是递一个划掉你的理由。

## 这正是这个仓库反复点名的那个问题

> *这条规则里藏了一个关于用户是谁的假设吗？*

`04` 的强度维为同一件事写过一整段（写死一份行业黑话词表，换个行业整维静默失效），
这一条是它在话术侧的同族。

## 判不出来时倒向哪一边

**倒向「不写缺口」。** 代价不对称：对企业网申少写一段缺口只是少一点加分，
对资格审查多写一段缺口是直接给对方一条依据。
（同 `job-apply.md` 5b 期望年包那条、`job-resume.md` 2.6 期望薪资那条，
这个仓库对不对称的代价一贯这么判。）
"""
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
TPL = (ROOT / "workflows" / "reference"
       / "06-outreach-templates.md").read_text(encoding="utf-8")
APPLY = (ROOT / "workflows" / "job-apply.md").read_text(encoding="utf-8")
EVAL = (ROOT / "workflows" / "reference"
        / "04-job-evaluation.md").read_text(encoding="utf-8")


def flat(s: str) -> str:
    s = " ".join(re.sub(r"^\s*(?:>|#:?)\s?", "", s, flags=re.M).split())
    return re.sub(r"(?<=[一-鿿，。；：、（）「」])"
                  r" +(?=[一-鿿，。；：、（）「」])", "", s)


def seg() -> str:
    i = TPL.index("### ⚠️ 上面那四段假设了读它的人是用人方")
    return flat(TPL[i:TPL.index("## 渠道 4：正式求职信", i)])


class TheForkExists(unittest.TestCase):
    def test_the_section_exists(self):
        self.assertIn("### ⚠️ 上面那四段假设了读它的人是用人方 —— 有一类不是", TPL)

    def test_it_sits_inside_channel_three(self):
        """放在别处等于没放 —— 写自评框的人读的是渠道 3。"""
        a = TPL.index("## 渠道 3：网申自评 / 求职动机")
        b = TPL.index("### ⚠️ 上面那四段假设了读它的人是用人方")
        self.assertLess(a, b)
        self.assertLess(b, TPL.index("## 渠道 4：正式求职信"))

    def test_it_names_the_routing_that_merged_them(self):
        """不指出路由把三类合在一起，读的人不知道这条为什么存在。"""
        s = seg()
        self.assertIn("job-apply.md", s)
        self.assertRegex(s, r"1\.5a 把\*\*三种东西\*\*一起路由到这条渠道")

    def test_the_routing_it_cites_really_merges_them(self):
        """引一条不存在的路由，这一整条就悬空了。"""
        i = APPLY.index("### 1.5a 有没有对话方")
        row = flat(APPLY[i:APPLY.index("### 1.5b", i)])
        self.assertRegex(row, r"网申表单、校招官网、考编/事业单位报名系统")
        self.assertIn("无对话方", row)

    def test_it_names_who_reads_each(self):
        """「读者不同」是这一整条的支点，不说清就只是又一张表。

        **两处都要钉**：开头那个「两种读者」的列举（它是这一节的论点），
        和下面那张表里的那一格（它是对照）。第一版只钉了表格那一格 ——
        把开头的列举整条删掉照样绿（变异实测），而删掉之后这一节读起来
        就成了「有两种写法」，不再是「因为读它的人不是同一个人」。
        """
        s = seg()
        self.assertRegex(s, r"这个框有\*\*两种读者\*\*")
        self.assertRegex(s, r"用人部门 / HR —— 他要判断你能不能干")
        self.assertRegex(s, r"\*\*资格审查人员\*\* —— 他只做一件事")
        # 下面那张表里的对照
        self.assertRegex(s, r"用人部门 / HR，要判断你能不能干")
        self.assertRegex(s, r"审查人员，只核符不符合公告条件")

    def test_the_gap_paragraph_flips(self):
        """**这是唯一真正反过来的那一段。** 其余三段只是侧重不同。"""
        s = seg()
        self.assertRegex(s, r"\*\*不写\*\*。形式审查里一条不符就是一条不符")
        self.assertRegex(s, r"只是递一个划掉你的理由")

    def test_the_understanding_paragraph_changes_shape(self):
        s = seg()
        self.assertRegex(s, r"逐条对着招聘公告的资格条件\*\*，用公告的原词")

    def test_it_adds_the_stability_note(self):
        """体制内那一关问的是「能不能长期做」，不是「你多能干」。"""
        self.assertRegex(seg(), r"为什么选这个地方、能不能长期做")

    def test_it_says_how_to_tell_them_apart(self):
        """给了两套写法却不给判据，执行者只能猜。"""
        s = seg()
        self.assertRegex(s, r"公告编号、报名起止时间")
        self.assertRegex(s, r"给的是一个 JD 页面 → 前一类")

    def test_unknown_falls_to_the_safe_side(self):
        s = seg()
        self.assertRegex(s, r"判不出来就问用户一句")
        self.assertRegex(s, r"别按前一类默认")

    def test_the_asymmetry_is_spelled_out(self):
        """只说「倒向哪边」，下一个人会觉得两边差不多，然后改回去。"""
        s = seg()
        self.assertRegex(s, r"少写一段缺口只是少一点加分")
        self.assertRegex(s, r"多写一段缺口是直接给对方一条依据")

    def test_it_names_the_recurring_question(self):
        """这条属于这个仓库点过名的那一类 —— 归类写下来，下次才认得出。"""
        self.assertRegex(seg(), r"这条规则里藏了一个关于用户是谁的假设吗？")


class TheOriginalFourSectionsSurvive(unittest.TestCase):
    """这一条是加一道分流，不是改默认写法。四段一个字都不许动。"""

    def _base(self) -> str:
        i = TPL.index("## 渠道 3：网申自评 / 求职动机")
        return flat(TPL[i:TPL.index("### ⚠️ 上面那四段", i)])

    def test_the_four_sections_are_intact(self):
        s = self._base()
        for k in ("对岗位的理解", "匹配点", "缺口与应对", "为什么是这家"):
            with self.subTest(k=k):
                self.assertIn(k, s)

    def test_the_default_still_says_write_the_gap(self):
        """默认那一支必须仍然是「照写」—— 否则分流就成了单向禁令。"""
        self.assertRegex(self._base(), r"这一段不是减分项")

    def test_the_plain_text_rule_survives(self):
        """网申框多半不认 markdown —— 这条比分流更早，别被挤掉。"""
        self.assertRegex(self._base(), r"输出必须是\*\*纯文本\*\*")


class TheSiblingJudgementsAgree(unittest.TestCase):
    """代价不对称时倒向哪边，这个仓库有一贯判法 —— 三处不许各说各的。"""

    def test_the_resume_asking_price_rule_agrees(self):
        self.assertRegex(flat(APPLY), r"判不出来时不写")

    def test_the_online_resume_rule_agrees(self):
        t = (ROOT / "workflows" / "job-resume.md").read_text(encoding="utf-8")
        self.assertRegex(flat(t), r"按可谈的下限填，不按理想值填")

    def test_the_recurring_question_is_still_asked_elsewhere(self):
        """这句话是 `04` 立的判据。它没了，这条的归类就没依据了。"""
        self.assertRegex(flat(EVAL), r"这条规则里藏了一个关于用户是谁的假设吗？")


class TheSignalItLeansOnIsReal(unittest.TestCase):
    """现算：形式审查那一类在这个仓库里真的被单独认过。"""

    def test_the_formal_review_class_is_named_elsewhere(self):
        """`04` 的境外学历那一节也为它单开了一条 —— 两处说的是同一类单位。"""
        i = EVAL.index("#### 境外学历（含港澳台）算不算「统招」")
        s = flat(EVAL[i:i + 1200])
        for w in ("国企", "事业单位", "考编", "校招网申"):
            with self.subTest(w=w):
                self.assertIn(w, s)
        self.assertIn("形式审查", s)

    def test_the_two_places_list_the_same_kinds(self):
        """两处列的单位类别要对得上，否则同一个岗在两处被判成两类。

        第一版这里就红过一次，而且报的是真事：06 把「校招官网」整个划给
        用人方那一边，04 却把「校招网申」列进形式审查。**两边都对一半** ——
        大厂民企的校招看能力，国企银行事业单位的校招先过资格审查。
        改法不是挑一边，是**别按渠道名字分，按入口形态分**。
        """
        # **先钉那句把两份文件绑在一起的话。** 光比词集不够：这一节里
        # 「别按渠道名字分」那段也提到国企/事业单位，删掉这半句照样凑得齐
        #（变异实测），而删掉之后两处就只是碰巧写了同样几个词。
        self.assertRegex(
            flat(seg()),
            r"这一关涉及的单位类别 —— 国企 / 事业单位 / 考编 / 校招网申 ——\s*"
            r"与 `04-job-evaluation\.md` 那一节里按形式审查单列的是同一批")
        a = set(re.findall(r"国企|事业单位|考编|校招网申", flat(seg())))
        i = EVAL.index("#### 境外学历（含港澳台）算不算「统招」")
        b = set(re.findall(r"国企|事业单位|考编|校招网申", flat(EVAL[i:i + 1200])))
        self.assertEqual(a, b, f"两处列的类别对不上：{a} vs {b}")

    def test_it_refuses_to_bucket_by_channel_name(self):
        """按名字分就会把「校招网申」整类判错一半。"""
        s = seg()
        self.assertRegex(s, r"别按渠道名字分，按入口形态分")
        self.assertRegex(s, r"同一个名字，两种读者")

    def test_this_channel_is_thin_in_the_corpus(self):
        """语料少不是不修的理由 —— 但要如实记着这条眼下验不了。

        （他投的全是平台内直聊，网申自评只有个位数。哪天这一类长起来，
        这条 skip 会变成真实的覆盖。）
        """
        p = ROOT / ".active_user"
        if not p.is_file():
            self.skipTest("没有活动用户")
        apps = (ROOT / "users" / p.read_text(encoding="utf-8").strip()
                / "documents" / "applications")
        if not apps.is_dir():
            self.skipTest("还没有话术")
        n = sum(1 for f in apps.glob("*/outreach.md")
                if re.search(r"^#{1,3}\s*网申自评", f.read_text(
                    encoding="utf-8", errors="replace"), re.M))
        self.assertLess(n, 60, f"网申自评已经有 {n} 份了 —— 语料够了，"
                               f"该拿真样本验这道分流，而不只是写规则")


if __name__ == "__main__":
    unittest.main()
