# -*- coding: utf-8 -*-
"""换工作时社保断一个月，几年后才显形 —— 而全流程一个字都没提过。

实测 2026-08-24 全仓搜：

    社保断缴      0 命中
    断缴          0 命中
    连续缴纳      0 命中

而这是国内换工作**最常踩、代价最大、且完全可以避免**的一个坑：

    社保按自然月缴。上家缴到离职当月（有的公司离职当月就不缴），
    新公司多数从入职次月起申报 —— 两头一错，中间断一个月。

工资单上看不出来，人事也不会主动提。它要到几年后买房、摇号、办积分落户的
时候才显形，那时补不回来。

## 为什么它挂在「入职日期」旁边

`job-offer.md` 已经有一条「**入职日期**：和现单位的离职周期（通常 30 天）
对得上吗？谈了吗？」—— 断缴就是那一条的**隐藏成本**。分开放，他会把入职日期
只当成一个日程问题。

## 这一条不许写死任何数

各地口径差到没有通用答案（连续几年、能不能补缴、补缴算不算连续，
每个城市都不一样）。所以这里只写**机制**与**影响分档**，年限一律推给
工作城市社保局当期口径 —— 判据形状照抄同一份文件里中留服那条
「以官网当期公告为准，别照抄任何转述」。

## 也不许给那条捷径

第三方机构挂靠代缴是虚构劳动关系，查实反而影响购房资格与落户，
还可能牵连新东家的用工合规。这一条要明写，因为它是网上最容易搜到的答案。
"""
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
OFFER = (ROOT / "workflows" / "job-offer.md").read_text(encoding="utf-8")
TPL = (ROOT / "profile.example" / "candidate.md").read_text(encoding="utf-8")


def flat(s: str) -> str:
    s = " ".join(re.sub(r"^\s*(?:>|#:?)\s?", "", s, flags=re.M).split())
    return re.sub(r"(?<=[一-鿿，。；：、（）「」])"
                  r" +(?=[一-鿿，。；：、（）「」])", "", s)


class TheItemExists(unittest.TestCase):
    def _seg(self) -> str:
        i = OFFER.index("- [ ] **离职日到入职日中间有没有空一个自然月")
        return flat(OFFER[i:OFFER.index("- [ ] **三方协议**", i)])

    def test_it_is_in_the_pre_accept_checklist(self):
        i = OFFER.index("## Step 4: 接之前先确认这几件")
        j = OFFER.index("- [ ] **离职日到入职日中间有没有空一个自然月")
        self.assertLess(i, j)

    def test_it_sits_next_to_the_start_date_item(self):
        """断缴是「入职日期」那条的隐藏成本。分开放，他会只当成日程问题。"""
        a = OFFER.index("- [ ] **入职日期**")
        b = OFFER.index("- [ ] **离职日到入职日中间有没有空一个自然月")
        self.assertLess(a, b)
        self.assertLess(b - a, 400, "隔太远了，读的人不会把两条连起来")

    def test_it_explains_the_mechanism(self):
        """只说「会断缴」，他不知道断在哪、也不知道为什么会断。"""
        s = self._seg()
        self.assertRegex(s, r"社保按\*\*自然月\*\*缴")
        self.assertRegex(s, r"新公司多数从入职\*\*次月\*\*起申报")

    def test_it_says_why_nobody_notices(self):
        s = self._seg()
        self.assertRegex(s, r"工资单上看不出来，人事也不会主动提")
        self.assertRegex(s, r"几年后才显形")


class ItGradesTheCostInsteadOfShouting(unittest.TestCase):
    """本地户口、不打算买房的人，这一条对他影响很小 —— 一刀切就是吓唬人。"""

    def _seg(self) -> str:
        i = OFFER.index("- [ ] **离职日到入职日中间有没有空一个自然月")
        return flat(OFFER[i:OFFER.index("- [ ] **三方协议**", i)])

    def test_the_heaviest_case_is_named(self):
        s = self._seg()
        self.assertRegex(s, r"户口不在工作城市")
        self.assertRegex(s, r"连续缴纳满 N 年")

    def test_the_medical_case_is_separate(self):
        """医保断缴是另一件事，时间尺度也不同 —— 混在一起说会被一起忽略。"""
        self.assertRegex(self._seg(), r"报销停掉")

    def test_the_light_case_says_do_not_scare_him(self):
        s = self._seg()
        self.assertRegex(s, r"影响小")
        self.assertRegex(s, r"别当大事吓他")

    def test_it_reads_the_profile_value(self):
        """清单里别的条目也这么做 —— 把资料里那格念出来，不让他再去翻。"""
        self.assertIn("{{`profile` 个人信息的「户口所在地」取值}}", OFFER)

    def test_the_profile_field_it_reads_actually_exists(self):
        """字段名对不上，这一条就是写给空气看的。"""
        self.assertIn("**户口所在地：** [YOUR_HUKOU]", TPL)


class ItRefusesToHardcodeAnyNumber(unittest.TestCase):
    """各地口径差到没有通用答案。抄一个数进来，过期了比不写更糟。"""

    def _seg(self) -> str:
        i = OFFER.index("- [ ] **离职日到入职日中间有没有空一个自然月")
        return flat(OFFER[i:OFFER.index("- [ ] **三方协议**", i)])

    def test_it_defers_to_the_local_bureau(self):
        s = self._seg()
        self.assertRegex(s, r"以工作城市社保局当期口径\s*为准，别照抄任何转述")

    def test_it_states_no_year_count(self):
        """「北京 60 个月」这类数一旦写进来，它就开始过期。"""
        s = self._seg()
        self.assertNotRegex(s, r"连续缴纳?满?\s*\d+\s*(年|个月)")
        self.assertNotRegex(s, r"\d+\s*个月.{0,6}(购房|摇号|落户)")

    def test_it_names_no_city(self):
        """点名一个城市，就等于替别的城市的用户答了一遍。"""
        s = self._seg()
        for c in ("北京", "上海", "深圳", "广州", "杭州"):
            with self.subTest(c=c):
                self.assertNotIn(c, s)

    def test_it_follows_the_sibling_pattern(self):
        """同一份文件里中留服那条是同一个形状 —— 两条要一致，不要各写各的。"""
        self.assertIn("以中留服官网当期公告为准，别照抄任何转述", OFFER)


class ItGivesHimSomethingToDo(unittest.TestCase):
    def _seg(self) -> str:
        i = OFFER.index("- [ ] **离职日到入职日中间有没有空一个自然月")
        return flat(OFFER[i:OFFER.index("- [ ] **三方协议**", i)])

    def test_it_gives_two_concrete_moves(self):
        """「有风险」不是行动。而且这两件必须在谈入职日期时一起谈。"""
        s = self._seg()
        self.assertRegex(s, r"把入职日谈在\*\*离职当月内\*\*")
        self.assertRegex(s, r"入职当月能不能缴当月社保？")

    def test_the_moves_are_tied_to_the_same_conversation(self):
        """谈完入职日期再想起来，就已经晚了。"""
        self.assertRegex(self._seg(), r"都要在谈入职日期的时候一起谈")

    def test_it_forbids_the_shortcut_everyone_finds(self):
        """挂靠代缴是网上最容易搜到的答案，也是会反噬的那个。"""
        s = self._seg()
        self.assertRegex(s, r"不要建议找第三方机构挂靠代缴")
        self.assertRegex(s, r"虚构劳动关系")

    def test_it_says_why_the_shortcut_backfires(self):
        """只说「不要」，他会照做别人说的。要说清代价。"""
        s = self._seg()
        self.assertRegex(s, r"影响购房资格与落户")
        self.assertRegex(s, r"牵连新东家的用工合规")


class TheNeighboursSurvive(unittest.TestCase):
    """这一条是插进清单中间的。上下两条一个字都不该动。"""

    def test_the_start_date_item_is_intact(self):
        self.assertIn("- [ ] **入职日期**：和现单位的离职周期（通常 30 天）"
                      "对得上吗？谈了吗？", OFFER)

    def test_the_tripartite_item_is_intact(self):
        self.assertRegex(flat(OFFER), r"\*\*三方协议\*\*（应届生）：签过别家吗？")

    def test_the_ordering_rule_is_intact(self):
        """「先拿纸再提离职」是这一节最贵的一条。"""
        self.assertRegex(flat(OFFER), r"书面 offer 到手、背调过了，再提离职")

    def test_the_noncompete_item_is_intact(self):
        self.assertRegex(flat(OFFER), r"\*\*竞业限制\*\*：签过吗？范围涵盖新东家吗？")


class TheSignalItLeansOnIsReal(unittest.TestCase):
    """现算：这件事此前真的一次都没被提过，而且现在只有一处在讲。"""

    def test_it_was_absent_before(self):
        """哪天别处也开始讲断缴，这条会红 —— 那时要确认两处说的是同一件事。"""
        hits = []
        for f in sorted((ROOT / "workflows").rglob("*.md")):
            if f.name == "job-offer.md":
                continue
            if "断缴" in f.read_text(encoding="utf-8", errors="replace"):
                hits.append(f.name)
        self.assertEqual(hits, [], f"这几处也讲了断缴，判据可能已经分叉：{hits}")

    def test_the_conditional_can_actually_fire(self):
        """触发条件靠户口那一格。它还是占位符时这一条问不出来，但不该报错。"""
        p = ROOT / ".active_user"
        if not p.is_file():
            self.skipTest("没有活动用户")
        f = (ROOT / "users" / p.read_text(encoding="utf-8").strip()
             / "profile" / "candidate.md")
        if not f.is_file():
            self.skipTest("这位用户还没有资料")
        # **先算成布尔再断言。** `assertIn(…, 整份 candidate.md)` 失败时
        # unittest 会把资料整个印进报告（姓名、薪资、能力边界都在里面），
        # 而报告会被贴进对话与 CI 日志。判据见
        # `test_an_assertion_does_not_dump_the_profile`。
        has = "户口所在地" in f.read_text(encoding="utf-8")
        self.assertTrue(has,
                        "资料里没有这一格了 —— 那条「和工作城市是不是同一个」问不出来")


if __name__ == "__main__":
    unittest.main()
