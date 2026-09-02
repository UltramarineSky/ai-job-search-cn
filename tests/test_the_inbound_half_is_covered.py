# -*- coding: utf-8 -*-
"""求职有两个方向，工具原来只有一个。

`/job-resume` 的开头自己列了一张表：流程里四处碰简历，没有一处审它的内容。
补上 `/job-resume` 之后，那四处加这一处审的**仍然全是同一份 PDF** ——
而那份 PDF 只有在你投出去之后才有人看。

国内主流平台上 HR 有很大一部分工作是反过来的：**在简历库里搜，主动联系人**。
那条路的入口是**在线简历**，和 `resume/main.typ` 是两个东西。一个投了 85 个、
一个回音都没有的人，问题可能是他在搜索结果里压根不出现 —— 而只审 `.typ`
永远查不出来（2026-08-22 通读时发现：全仓 `在线简历` 只作为「要和 PDF 保持
一致的另一份文本」出现过，从没当成一条渠道）。

这里钉住那一整条路还在，以及它的两条降级路径都还在 —— 后者更容易掉：
这一节里没有一项是工具能改的，全在平台的登录态后面，很容易被写成一段
「建议你去检查一下」的空话。
"""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESUME = (ROOT / "workflows" / "job-resume.md").read_text(encoding="utf-8")


class TheInboundHalfIsCovered(unittest.TestCase):
    def test_there_is_a_step_for_the_online_profile(self):
        self.assertIn("2.6", RESUME, "少了在线简历那一步")
        self.assertIn("在线简历", RESUME)
        self.assertIn("六项检查", RESUME, "步骤数没跟着改——数和内容对不上")

    def test_it_says_which_direction_it_covers(self):
        """要说清这一节管的是**反方向**，否则读者以为又在说那份 PDF。"""
        self.assertRegex(RESUME, r"简历库里搜|主动搜|搜简历",
                         "没说清 HR 是反过来搜人的")

    def test_the_settings_that_make_you_invisible_are_named(self):
        """具体是哪几项。少一项，用户就在那一项上一直看不见自己。"""
        for item, why in (
                ("公开范围", "设成仅投递可见就永远搜不到，投多少都补不回来"),
                ("求职状态", "国内很多 HR 直接按这一项筛"),
                ("刷新", "搜索结果基本按最近活跃排"),
                ("屏蔽现任公司", "在职的人不开这个，现公司能搜到你")):
            with self.subTest(item=item):
                self.assertIn(item, RESUME, f"漏了「{item}」：{why}")

    @staticmethod
    def _section():
        """2.6 那一节的正文。**锚标题，不锚「2.6」这两个字**。

        原来三处都写 `RESUME[RESUME.index("2.6"):]` —— 而文件里第一个「2.6」
        是第 19 行的**前向引用**（「见下面 2.6」），于是切出来的是
        **从第 19 行到文件末尾**，几乎是整份文档。

        实测代价（2026-08-23）：把 2.6 节内的「没查」「必须改」全删掉，
        `test_it_does_not_pretend_to_have_checked` 与
        `test_the_findings_have_somewhere_to_go` **照样全绿** ——
        那两个词在文件别处各有 2 处和 4 处，断言落在了别人的文字上。
        整节删掉时是**另外**几条（对着整份文档的 `assertIn`）在兜底，
        这三条一直是空转的。
        """
        import re as _re
        i = RESUME.index("### 2.6 在线简历")
        m = _re.search(r"^### ", RESUME[i + 10:], _re.M)
        return RESUME[i:i + 10 + m.start()] if m else RESUME[i:]

    def test_both_degradation_paths_are_written(self):
        """有浏览器就去看，没有就给清单 —— 两条都要在，且都要落到具体动作。"""
        seg = self._section()
        self.assertIn("有浏览器能力时", seg, "没写有浏览器时怎么做")
        self.assertIn("没有浏览器能力时", seg, "没写没有浏览器时怎么做")
        self.assertRegex(seg, r"只读|不要动任何设置",
                         "没写明是只读——工具不该替用户改平台设置")

    def test_it_does_not_pretend_to_have_checked(self):
        """查不了的要如实说没查。「没查」和「查过没有」是两件事。"""
        seg = self._section()
        self.assertIn("没查", seg, "没接上「没查的」那一节的规矩")

    def test_the_findings_have_somewhere_to_go(self):
        """光列清单不够 —— 命中的问题要按代价进报告，否则读完就散了。"""
        seg = self._section()
        self.assertRegex(seg, r"必须改", "命中的问题没有归口到报告里")


if __name__ == "__main__":
    unittest.main()
