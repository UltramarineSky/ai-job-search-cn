# -*- coding: utf-8 -*-
"""面板劝用户做的事，工具里必须有对应的材料。

2026-08-22 实测撞上：面板在**两个地方**把内推说成回报最高的动作
（投后统计「与其再投一个，不如找个能说上话的人」、短名单表头「那批才有人可找」），
而整个 `workflows/` 里「内推」只作为投递记录的一个渠道取值出现过 ——
`06-outreach-templates.md` 一个字都没有。**劝人做一件没有材料的事，等于没劝。**

这与「指过去是死胡同」是同一族：`/job-outcome followup` 曾经吐 53 行公司名
然后结束、`/job-scrape` 的正文指向一个不存在的文件。区别只是这次断在
「建议 → 话术」这一层。

这里不去做通用的建议扫描（那要判断哪句话算「建议」，误报会淹掉真问题），
只钉住已经出过事的这一条，以及它的触发有没有真的接上流水线。
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TPL = (ROOT / "workflows" / "reference"
       / "06-outreach-templates.md").read_text(encoding="utf-8")
APPLY = (ROOT / "workflows" / "job-apply.md").read_text(encoding="utf-8")
PANEL = "\n".join(
    p.read_text(encoding="utf-8")
    for p in (ROOT / "web" / "src").rglob("*.tsx"))


class ReferralAdviceHasMaterial(unittest.TestCase):
    def test_the_panel_does_recommend_it(self):
        """判据的前提：面板确实在劝内推。哪天不劝了，下面几条也就不必成立。"""
        self.assertIn("内推", PANEL, "面板不再提内推了——这个文件可以整个删掉")

    def test_there_is_a_channel_teaching_it(self):
        """劝了就得有话术。"""
        self.assertIn("内推请托", TPL, "话术库里没有内推这一档")
        self.assertRegex(TPL, r"##\s*渠道\s*5[：:]\s*内推请托",
                         "内推没有独立成一个渠道，只是被顺带提了一句")

    def test_the_china_specific_mechanics_are_stated(self):
        """光有「写短一点」没用。国内内推的机制决定了这段话怎么写，缺一条就写错。

        - 一个岗通常只能被一个人推 → 所以要先问「还没人推过吧」
        - 推荐人有奖金 → 那是他愿意帮的正当理由，分寸要交代
        - 有有效期 → 所以别说「以后帮我留意」
        """
        for what, why in (("还没人推过", "撞车这条没写，用户会和别人推同一个岗"),
                          ("内推奖金", "没交代推荐人为什么愿意帮忙"),
                          ("有效期", "没说内推会过期")):
            with self.subTest(what=what):
                self.assertIn(what, TPL, why)

    def test_it_asks_for_submission_not_endorsement(self):
        """只求「把简历提上去」，不求背书——对方不认识你，逼他担保是给他出难题。"""
        self.assertIn("内推系统", TPL, "没说清要对方做的到底是哪个动作")
        self.assertRegex(TPL, r"不求.*背书|不求「背书」|不求背书",
                         "没写明「不求背书」这条边界")

    def test_the_trigger_is_wired_into_the_pipeline(self):
        """话术躺在参考文件里不会自己产出——`/job-apply` 要有触发和起草两步。"""
        self.assertIn("1.6c", APPLY, "job-apply 没有内推请托的触发判定")
        self.assertRegex(APPLY, r"###\s*渠道\s*5[：:]\s*内推请托",
                         "job-apply 没有起草这一节的步骤")

    def test_the_trigger_excludes_the_two_kinds_with_nobody_to_find(self):
        """猎头代招和匿名公司都没有人可找 —— 判据必须把这两类排除掉。

        漏掉任何一类，产出里就会出现一段「去找某上海知名公司的人内推」，
        而那家公司叫什么都不知道。
        """
        # 锚小节标题：「1.6c」在这份文档里还出现在渠道 5 的抬头里。
        seg = APPLY[APPLY.index("### 1.6c 要不要内推请托"):]
        seg = seg[:seg.index("\n## ")] if "\n## " in seg else seg
        self.assertIn("isHeadhunter", seg, "触发判据没提猎头代招")
        self.assertRegex(seg, r"隐去|匿名|未公开", "触发判据没排除公司名隐去的岗")

    def test_the_output_skeleton_has_a_home_for_it(self):
        """产出物的骨架里要有这一节，否则起草出来没地方放。"""
        body = TPL[TPL.index("## 产出格式"):]
        self.assertIn("## 内推请托（场景触发）", body,
                      "outreach.md 的骨架里没有内推请托这一节")


if __name__ == "__main__":
    unittest.main()
