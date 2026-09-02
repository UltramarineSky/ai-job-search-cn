# -*- coding: utf-8 -*-
"""「改简历就能补」这句话有个前提，而它从没被验证过。

面板「市场怎么读你的简历」那一栏的引导句写着：

> 你**资料里写过**、主场岗也在要、而简历里没出现的——这些不是学习任务，
> 是你会但没写上去，改简历就能补

可 `inResume` 只查了 `resume/main.typ`，**从没查过 `candidate.md`**。
对一个资料里也没有的市场词，那句话就成了「你会，去写上」—— 而他并不会。
往简历里加一条兜不住的东西，正是 `03-writing-style.md` 铁律 3（能力边界）
要挡的事，也是背调和面试里最贵的一种翻车。

（实测活动用户 2026-08-22 唯一那条缺词「prompt engineering」在资料里**确实有**
—— 这一条碰巧是真的。**碰巧成立的前提仍然是没验证的前提。**）
"""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import export_web_data as X  # noqa: E402

TSX = (ROOT / "web" / "src" / "components"
       / "ResumeRead.tsx").read_text(encoding="utf-8")
_CODE = re.sub(r"\{/\*[\s\S]*?\*/\}", "", TSX)


class ThePremiseIsActuallyChecked(unittest.TestCase):
    def test_the_profile_is_read(self):
        self.assertTrue(hasattr(X, "profile_text"), "没有读资料的那一步")

    def test_it_returns_none_when_unreadable(self):
        """读不到就是「没比对」，不是「没写」——两者在屏幕上是两件事。"""
        saved = X.ROOT
        try:
            X.ROOT = Path("/no/such/place")
            self.assertIsNone(X.profile_text("张三"))
        finally:
            X.ROOT = saved

    def test_the_flag_reaches_the_payload(self):
        src = (ROOT / "tools" / "export_web_data.py").read_text(encoding="utf-8")
        self.assertIn('"inProfile"', src, "算了没导出")
        self.assertIn("profile_text(user)", src, "导出时没调它")


class TheTwoKindsAreToldApart(unittest.TestCase):
    def test_the_component_splits_them(self):
        self.assertIn("notWritten", _CODE, "「忘了写」那一类没有单独的集合")
        self.assertIn("notHad", _CODE, "「真没有」那一类没有单独的集合")
        self.assertIn("a.inProfile === false", _CODE, "「真没有」的判据不对")

    def test_the_lacking_kind_is_not_told_to_edit_the_resume(self):
        """这一类绝不许出现「改简历就能补」。"""
        i = _CODE.index("notHad.length > 0")
        seg = _CODE[i:i + 1600]
        self.assertNotIn("改简历就能补", seg, "又在劝他写一条兜不住的东西")
        self.assertIn("别直接写进简历", seg, "没说清这一类不能直接写")

    def test_it_offers_the_real_fork(self):
        """要么补进资料（确实会、只是漏了），要么去补能力，要么认了 —— 三条都要给。"""
        i = _CODE.index("notHad.length > 0")
        seg = _CODE[i:i + 1600]
        self.assertIn("--section skills", seg, "没给「补进资料」这条路")
        self.assertIn("/job-upskill", seg, "没给「去补能力」这条路")
        self.assertRegex(seg, r"认了", "没给「认了、别投那批岗」这条路")

    def test_the_two_look_different(self):
        css = (ROOT / "web" / "src" / "theme"
               / "cockpit.css").read_text(encoding="utf-8")
        self.assertIn("data-hard", _CODE, "两类长得一样，拆开就没意义")
        self.assertRegex(css, r"\.rread-gap\[data-hard\]", "没有对应样式")

    def test_the_all_clear_line_covers_both(self):
        """两类都空才说「都提到了」——只看一类会在另一类非空时说反话。"""
        self.assertIn("notWritten.length === 0 && notHad.length === 0", _CODE)

    def test_the_command_form_exists(self):
        setup = (ROOT / "workflows" / "job-setup.md").read_text(encoding="utf-8")
        self.assertRegex(setup, r"\|\s*`skills`\s*\|",
                         "面板印的 --section skills 在 job-setup 里查无此名")


if __name__ == "__main__":
    unittest.main()
