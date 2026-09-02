# -*- coding: utf-8 -*-
"""接 offer 那一节问了「有没有书面」，没说「先后」；也没算走掉那笔年终奖。

`job-offer.md` Step 4 的离职过渡清单已经很全 —— 离职证明、竞业、入职日期、
三方协议、offer 的书面形式。后面「谈好的数，和到手的数，不是一个数」
还逐条算了试用期折扣、公积金基数、基本工资占比。

缺的是两件国内最贵的事：

## 一、顺序

全仓扫过（2026-08-23）：`提离职` / `先别提` / `递辞职` / `反悔` / `撤回 offer`
**一次都没出现**。清单问了「拿到的是正式 offer letter 还是口头/微信」——
那是**有没有**；而真正让人两头落空的是**先后**：口头 offer 反悔在国内不算罕见
（HC 被砍、部门重组、背调卡住），而辞呈递了就基本回不去。

## 二、走掉的那笔年终奖

`年终奖` 在全仓出现 4 次，没有一次说的是**时点**：国内多数公司次年 1-3 月发，
政策里通常写着「发放时仍在职」—— 年中或年底跳槽，上一整年挣的那笔多半就没了
（常见 1-3 个月）。它正属于「谈好的数 vs 到手的数」那一节管的东西，
而且是那一节里**唯一能反过来向对方要钱**的一条（签字费）。

金九银十正是跳槽高峰，这一条对着日历就会反复用到。
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OF = (ROOT / "workflows" / "job-offer.md").read_text(encoding="utf-8")


def step4() -> str:
    i = OF.index("## Step 4: 接之前先确认这几件")
    return OF[i:OF.index("## Step 5", i)]


def takehome() -> str:
    i = OF.index("### 谈好的数，和到手的数，不是一个数")
    return OF[i:OF.index("## Step 5", i)]


class TheOrderIsSpelledOut(unittest.TestCase):
    def test_the_rule_exists(self):
        self.assertIn("**顺序：书面 offer 到手、背调过了，再提离职。**", step4(),
                      "清单仍然只问「有没有书面」，没说先后")

    def test_it_distinguishes_itself_from_the_checklist_item(self):
        """上面那条问的是有没有，这条管的是先后 —— 不点破就会被当成重复。"""
        seg = " ".join(step4().split())
        self.assertRegex(seg, r"问的是\*\*有没有\*\*，这一条管的是\*\*先后\*\*")

    def test_it_says_why_the_offer_can_evaporate(self):
        """「可能反悔」太虚。国内真会发生的三种要点名。"""
        seg = " ".join(step4().split())
        for w in ("HC 被砍", "部门重组", "背调卡在某一条"):
            with self.subTest(w=w):
                self.assertIn(w, seg)

    def test_it_says_the_resignation_is_one_way(self):
        """这一条的分量全在这里：另一边回不去。"""
        self.assertRegex(" ".join(step4().split()),
                         r"辞呈一旦递了，现单位那边基本回不去")

    def test_it_says_the_order_voids_the_rest(self):
        self.assertRegex(" ".join(step4().split()),
                         r"顺序错了，上面每一条都白问")

    def test_it_names_who_it_does_not_apply_to(self):
        """已经离职的人（活动用户就是）照这条走会卡住 —— 要写清不适用。"""
        seg = " ".join(step4().split())
        self.assertRegex(seg, r"已经离职、或没有现单位要辞的人")

    def test_it_sits_after_the_written_form_item(self):
        seg = step4()
        self.assertLess(seg.index("**offer 的书面形式**"),
                        seg.index("**顺序：书面 offer 到手"))

    def test_the_checklist_it_builds_on_survives(self):
        seg = step4()
        for item in ("**离职证明**", "**竞业限制**", "**入职日期**",
                     "**三方协议**", "**offer 的书面形式**"):
            with self.subTest(item=item):
                self.assertIn(item, seg)


class TheForfeitedBonusIsCounted(unittest.TestCase):
    def test_the_item_exists(self):
        self.assertIn("**现在这家的年终奖，走了还拿得到吗？**", takehome(),
                      "「到手多少」那一节仍然没算走掉的年终奖")

    def test_it_names_the_clause_that_costs_the_money(self):
        seg = " ".join(takehome().split())
        self.assertRegex(seg, r"次年 1-3 月\*\*发")
        self.assertRegex(seg, r"发放时仍在职")

    def test_it_gives_the_magnitude(self):
        """不给量级，读的人不会为它去谈。"""
        self.assertRegex(" ".join(takehome().split()), r"常见 1-3 个月")

    def test_it_turns_the_loss_into_a_lever(self):
        """这是那一节里唯一能反过来要钱的一条 —— 不说怎么要就只是坏消息。"""
        seg = " ".join(takehome().split())
        self.assertIn("签字费", seg)
        self.assertRegex(seg, r"签字费能不能覆盖")

    def test_it_says_why_the_lever_works(self):
        seg = " ".join(takehome().split())
        self.assertRegex(seg, r"不动 offer 上那个年包数字")

    def test_it_asks_about_the_new_employer_too(self):
        """只算旧的那笔，可能拿一笔确定的钱换一笔条件相同的钱。"""
        seg = " ".join(takehome().split())
        self.assertRegex(seg, r"同时问新公司那半边")
        self.assertRegex(seg, r"有没有同样的在职条款")

    def test_it_splits_the_two_halves_for_the_unemployed(self):
        """已经离职的人只有后半条成立 —— 说清楚，别让他跳过整条。"""
        self.assertRegex(" ".join(takehome().split()),
                         r"前半条不适用，后半条照问")

    #: 中文数词 → 阿拉伯数字。开头那句用的是「三条」「五条」这种写法，
    #: 而这条要拿它和实际条数比，不能只查阿拉伯数字。
    _CN = {"一": 1, "两": 2, "二": 2, "三": 3, "四": 4, "五": 5,
           "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}

    def test_the_count_in_the_lead_matches(self):
        """开头写「三条」而下面四条，是这个仓库点名过的那类不一致。

        **2026-08-25 改成现推。** 原来钉死「必须是 4 条」加一句
        「四条都**可以谈**」—— 加第五条时它红了，而那正是它该做的事；
        但钉一个写死的数意味着**每加一条都要来改测试**，改的人顺手把数一改
        就过了，等于没守。现在从实际条数推，开头那句的数对不上才红。

        顺带：那句开头本来就自相矛盾 —— 写着「下面这**三**条……**四条**都
        可以谈」，两个数在同一句里就对不上，而下面实际是四条。
        它躲在散文里，一直没被数出来。
        """
        seg = takehome()
        n = len(re.findall(r"^- \[ \] \*\*", seg, re.M))
        self.assertGreaterEqual(n, 4, f"这一节只剩 {n} 条")
        lead = seg[:seg.index("- [ ] **")]
        said = [self._CN[m] for m in re.findall(r"下面这\*{0,2}([一两二三四五六七八九十])条",
                                                lead)]
        self.assertTrue(said, f"开头没说这一节有几条：{lead[:80]}")
        self.assertEqual(
            said[0], n,
            f"开头说 {said[0]} 条，下面实际 {n} 条 —— "
            f"「数字 5、点开 4，用户会以为漏了一个」")

    def test_the_lead_does_not_claim_they_are_all_negotiable(self):
        """**培训服务期违约金谈不了** —— 它是你欠现单位的，不是新东家能补的。
        一句「都可以谈」会让人拿它去要签字费，对面会觉得他没算清自己的账。"""
        lead = takehome()[:takehome().index("- [ ] **")]
        self.assertRegex(lead, r"唯一谈不了的是培训服务期违约金")
        self.assertNotRegex(lead, r"[一两二三四五六七八九十]条都\*\*可以谈\*\*")

    def test_the_three_existing_items_survive(self):
        seg = takehome()
        for item in ("**试用期：多长、几折、什么条件转正。**",
                     "**公积金和社保按什么基数缴",
                     "**基本工资占薪资总额的多少。**"):
            with self.subTest(item=item):
                self.assertIn(item, seg)

    def test_the_legal_disclaimer_still_closes_the_section(self):
        """新条目不能插到那句免责之后 —— 它是整节的收尾。"""
        seg = takehome()
        self.assertLess(seg.index("现在这家的年终奖"),
                        seg.index("法条以当地实际执行为准"))

    def test_they_are_all_settled_before_nodding(self):
        """这一节的前提：每一条都要在点头之前弄清楚。

        **2026-08-25 从「谈」改成「弄清楚」。** 加进来的培训服务期违约金
        **谈不了**（那是你欠现单位的，不是新东家能补的），可它同样必须在点头
        之前算清楚 —— 说成「都要谈」既不准，也会让人拿它去要签字费。
        这条钉的是**时点**（点头之前），那一点没变。
        """
        self.assertRegex(" ".join(takehome().split()),
                         r"都要在点头\*\*之前\*\*弄清楚")


class TheNeighbouringRulesAreIntact(unittest.TestCase):
    def test_the_background_check_section_survives(self):
        """顺序那条把「背调过了」当条件 —— 背调那一节得还在。"""
        self.assertIn("## Step 2: 背调红线自查（**这一节不许跳过**）", OF)

    def test_the_tax_app_redline_survives(self):
        """**要那句红线本身，不是「个税 APP」出现过。** 那份文档里这四个字
        出现两次，只删一处照样绿（变异实测）。"""
        prep = (ROOT / "workflows" / "reference"
                / "07-interview-prep.md").read_text(encoding="utf-8")
        self.assertIn("红线：口头报的薪资必须经得起个税 APP 记录核对", prep)

    def test_the_noncompete_item_still_flags_assumed_values(self):
        self.assertIn("← 假设值", step4())

    def test_the_interview_side_still_asks_these_earlier(self):
        """`07` 那一节写着「这几条不问，等 offer 下来再问就晚了」——
        这里是最后一道关，不是唯一一道。"""
        prep = (ROOT / "workflows" / "reference"
                / "07-interview-prep.md").read_text(encoding="utf-8")
        self.assertRegex(" ".join(prep.split()),
                         r"这几条不问，等 offer 下来再问就晚了")


if __name__ == "__main__":
    unittest.main()
