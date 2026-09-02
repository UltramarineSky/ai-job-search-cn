# -*- coding: utf-8 -*-
"""「走了会失去什么」这一节只算了年终奖，而它常常不是最大的一笔。

`job-offer.md` 那条年终奖写得很好，范式也立对了：

> 先算清楚**你要放弃多少**，再拿这个数去谈**签字费**（入职时一次性补）——
> 这是国内谈薪里最容易谈下来的一项，因为对方清楚你在放弃什么。

而同一套逻辑还管着三样东西，此前**一处都没提过**（全仓搜 2026-08-24，
`workflows/` + `tools/` + `profile.example/`）：

    未归属          0 命中
    年假            0 命中
    服务期违约金     0 命中
    薪资倒挂        0 命中

（`归属` / `行权` 各有几处命中，但逐个看过：`成本归属`、`它该归属的那个渠道`、
`没有执行权限`——**都是别的意思**。）

## 三样，三种处理 —— 混成一类就会有两样被办错

    未归属的股票/期权    离职即作废   → 和年终奖同一招：算出来，去谈签字费
    未休年假            依法应折现   → 不是「失去」，是**别忘了要**
    培训服务期违约金     真要掏钱     → 谈不了签字费（那是你欠对方的），
                                       但必须先算进去，它可能直接翻转结论

## 为什么这一条要紧

国内互联网普遍四年归属。干了一两年就跳的人，未归属那部分常常**比年终奖大得多**，
而它在「你还没提离职」之前才有谈判价值 —— 提了之后对面知道你已经没有退路。

## 不写死任何数额

各家的归属表、年假条款、违约金算法差别很大，而这三样都是白纸黑字写死的。
所以这一条只给**去哪儿看**和**怎么用**，数额一律回他手上那份协议原文 ——
判据形状与同一份文件里中留服、社保断缴那两条一致。
"""
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
OFFER = (ROOT / "workflows" / "job-offer.md").read_text(encoding="utf-8")


def flat(s: str) -> str:
    s = " ".join(re.sub(r"^\s*(?:>|#:?)\s?", "", s, flags=re.M).split())
    return re.sub(r"(?<=[一-鿿，。；：、（）「」])"
                  r" +(?=[一-鿿，。；：、（）「」])", "", s)


def seg() -> str:
    i = OFFER.index("- [ ] **走了还会丢掉什么 —— 年终奖不是唯一一笔。**")
    return flat(OFFER[i:OFFER.index("> 法条以当地实际执行为准", i)])


class TheItemExists(unittest.TestCase):
    def test_it_is_in_the_pre_accept_checklist(self):
        i = OFFER.index("## Step 4: 接之前先确认这几件")
        j = OFFER.index("- [ ] **走了还会丢掉什么")
        self.assertLess(i, j)

    def test_it_sits_right_after_the_bonus_item(self):
        """它借的是年终奖那条立的范式 —— 隔开了就读不出这层关系。"""
        a = OFFER.index("- [ ] **现在这家的年终奖，走了还拿得到吗？**")
        b = OFFER.index("- [ ] **走了还会丢掉什么")
        self.assertLess(a, b)
        self.assertLess(b - a, 1400)

    def test_it_names_the_pattern_it_borrows(self):
        self.assertRegex(seg(), r"先算清你要放弃多少，再拿这个数去谈签字费")

    def test_the_bonus_item_still_states_that_pattern(self):
        """借的那条没了，这一条就成了自说自话。"""
        i = OFFER.index("- [ ] **现在这家的年终奖，走了还拿得到吗？**")
        s = flat(OFFER[i:i + 900])
        self.assertRegex(s, r"先算清楚\*\*你要放弃多少\*\*，再拿这个数去谈\*\*签字费\*\*")

    def test_it_carries_the_zero_hit_measurement(self):
        s = seg()
        self.assertIn("2026-08-24", s)
        self.assertRegex(s, r"`未归属`、`年假`、`服务期违约金` 均 0 命中")


class TheThreeAreTreatedDifferently(unittest.TestCase):
    """混成一类就会有两样被办错 —— 这是这一条全部的价值。"""

    def _rows(self):
        i = OFFER.index("      | | 是什么 | 怎么办 |")
        body = OFFER[i:OFFER.index("\n\n", i)]
        return [r for r in body.splitlines() if r.strip().startswith("| **")]

    def test_there_are_exactly_three(self):
        self.assertEqual(len(self._rows()), 3)

    def test_the_equity_one_goes_to_the_signing_bonus(self):
        r = next(r for r in self._rows() if "期权" in r)
        self.assertIn("作废", r)
        self.assertIn("签字费", r)

    def test_the_annual_leave_one_is_not_a_loss(self):
        """依法应折现 —— 把它写成「会失去」，他就不会去要了。"""
        r = next(r for r in self._rows() if "年假" in r)
        self.assertIn("折现", r)
        self.assertRegex(flat(r), r"不是「失去」，是\*\*别忘了要\*\*")

    def test_the_penalty_one_cannot_be_negotiated_away(self):
        """它是你欠对方的 —— 拿去谈签字费是把两笔账搞混。"""
        r = next(r for r in self._rows() if "违约金" in r)
        self.assertRegex(flat(r), r"不能拿去谈签字费")
        self.assertRegex(flat(r), r"必须先算进去")

    def test_the_penalty_one_can_flip_the_decision(self):
        r = next(r for r in self._rows() if "违约金" in r)
        self.assertRegex(flat(r), r"直接改变这个 offer 值不值")

    def test_the_equity_one_says_why_it_can_be_the_biggest(self):
        """不说这句，读的人会按「反正没多少」跳过它。"""
        s = seg()
        self.assertRegex(s, r"国内互联网普遍分四年归属")
        self.assertRegex(s, r"这常常比年终奖大得多")


class TheTimingIsSpelledOut(unittest.TestCase):
    def test_it_says_calculate_before_negotiating(self):
        self.assertRegex(seg(), r"顺序是先算后谈")

    def test_it_says_when_the_leverage_disappears(self):
        """**这是这一条唯一有时限的部分。** 提了离职就没得谈了。"""
        s = seg()
        self.assertRegex(s, r"只在\s*「你还没提离职」的时候有谈判价值")
        self.assertRegex(s, r"对面知道你已经没有退路")

    def test_the_ordering_rule_it_leans_on_survives(self):
        """「先拿纸再提离职」是这一节最贵的一条，这一条建立在它上面。"""
        self.assertRegex(flat(OFFER), r"书面 offer 到手、背调过了，再提离职")


class ItRefusesToHardcodeAnyNumber(unittest.TestCase):
    """各家条款差别很大，而这三样都是白纸黑字写死的 —— 抄一个数进来只会错。"""

    def test_it_points_at_his_own_paperwork(self):
        s = seg()
        self.assertRegex(s, r"一律以你手上的协议原文为准")
        self.assertRegex(s, r"别照抄任何转述（含本文）")

    def test_it_names_which_documents(self):
        """只说「看协议」他不知道翻哪一份。"""
        s = seg()
        for w in ("授予协议", "员工手册", "培训协议"):
            with self.subTest(w=w):
                self.assertIn(w, s)

    def test_it_states_no_vesting_schedule_as_fact(self):
        """「四年归属」是行业常见做法，不是他那份协议的条款。"""
        s = seg()
        self.assertRegex(s, r"普遍分四年归属")
        self.assertNotRegex(s, r"你的期权(会|将|按)")

    def test_it_follows_the_sibling_pattern(self):
        """同一份文件里中留服、社保断缴两条是同一个形状 —— 三处要一致。"""
        self.assertIn("以中留服官网当期公告为准，别照抄任何转述", OFFER)
        self.assertRegex(flat(OFFER), r"以工作城市社保局当期口径\s*为准，别照抄任何转述")

    def test_the_legal_caveat_line_still_follows_it(self):
        """这一条写在那句「法条以当地实际执行为准」上面，被它罩着。"""
        self.assertLess(OFFER.index("- [ ] **走了还会丢掉什么"),
                        OFFER.index("> 法条以当地实际执行为准"))


class TheNeighboursSurvive(unittest.TestCase):
    def test_the_bonus_item_is_intact(self):
        s = flat(OFFER)
        self.assertRegex(s, r"国内多数公司的年终奖在\*\*次年 1-3 月\*\*发")
        self.assertRegex(s, r"已经离职、或现单位本来就没有年终奖的人")

    def test_the_base_salary_item_is_intact(self):
        self.assertRegex(flat(OFFER), r"\*\*基本工资占薪资总额的多少。\*\*")

    def test_the_social_insurance_item_is_intact(self):
        self.assertRegex(flat(OFFER), r"离职日到入职日中间有没有空一个自然月")


class TheSignalItLeansOnIsReal(unittest.TestCase):
    """现算：这三样此前真的一处都没被提过。"""

    def test_they_were_absent_before(self):
        hits = []
        for base in ("workflows", "tools", "profile.example"):
            d = ROOT / base
            if not d.is_dir():
                continue
            for f in sorted(d.rglob("*")):
                if f.suffix not in (".md", ".py") or "__pycache__" in str(f):
                    continue
                if f.name == "job-offer.md":
                    continue
                t = f.read_text(encoding="utf-8", errors="replace")
                if "未归属" in t or "服务期违约金" in t:
                    hits.append(f.name)
        self.assertEqual(hits, [], f"这几处也讲了，判据可能已经分叉：{hits}")

    def test_the_word_annual_leave_only_appears_here(self):
        """「年假」哪天在别处也出现，两处说的要是同一件事。"""
        hits = []
        for f in sorted((ROOT / "workflows").rglob("*.md")):
            if f.name == "job-offer.md":
                continue
            if "年假" in f.read_text(encoding="utf-8", errors="replace"):
                hits.append(f.name)
        self.assertEqual(hits, [], f"这几处也讲了年假：{hits}")


if __name__ == "__main__":
    unittest.main()
