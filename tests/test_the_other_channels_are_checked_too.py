# -*- coding: utf-8 -*-
"""开场白之外那几段对外文案，此前一个检查器都没有。

上一条自检（`check_greeting_keeps_the_five_rules`）的免责里自己写着这句：
「同一批文件里还有 23 段邮件 / 网申自评 / 求职信 / 内推请托，它们同样受
`03-writing-style.md` 约束，**但眼下没有检查器**」。

## 两套规则的适用面不同

`06-outreach-templates.md` 渠道 1 那五类禁区末尾有一句 ⚠️：

> **五条只管渠道 1。** 渠道 2（邮件）、3（网申自评）、4（求职信）不受此限
> —— 那些场合对方已经在读你的完整材料，谈条件、讲缺口都是正常的。

而 `03` 的风格铁律**没有**这个豁免：AI 味、互联网黑话、翻译腔，在哪个渠道
都不该有。所以判据拆成两个函数（`greeting_hits` = 五类禁区 + 风格铁律，
`style_hits` = 只有风格铁律）—— 混在一起，新渠道要么被五类禁区误伤，
要么整个查不上。

## 实测（2026-08-27）

开场白之外 30 段：邮件正文 9、网申自评 9、内推请托 9、求职信 3。
**网申自评 9 段里 5 段踩线**（翻译腔 4、互联网黑话 1「闭环」），其余三个渠道
0 段。集中在网申自评不是巧合：那一段是写给系统看的自述，最容易滑进
「正是我这两年在做的」这类自我认证句式 —— `STYLE_PATTERNS` 那三条正则
本来就是冲着它去的。
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import _cli  # noqa: E402
import audit_pipeline as ap  # noqa: E402

SRC = (ROOT / "tools" / "audit_pipeline.py").read_text(encoding="utf-8")
CLI = (ROOT / "tools" / "_cli.py").read_text(encoding="utf-8")
REF = (ROOT / "workflows" / "reference"
       / "06-outreach-templates.md").read_text(encoding="utf-8")


class TheTwoRuleSetsStaySeparate(unittest.TestCase):
    """五类禁区只管渠道 1；风格铁律管所有渠道。混起来两头都错。"""

    #: 渠道 1 禁、渠道 2-4 允许 —— 06 那段 ⚠️ 明说的。
    ALLOWED_ELSEWHERE = "我目前离职随时到岗，期望 45-60k。"
    #: 哪个渠道都禁。
    BANNED_EVERYWHERE = "把这条链路闭环掉。"

    def test_the_greeting_bans_do_not_leak_into_style_hits(self):
        self.assertEqual(_cli.style_hits(self.ALLOWED_ELSEWHERE), [],
                         "谈钱谈到岗时间在邮件里是正常的 —— 别拿五类禁区去卡它")

    def test_the_greeting_still_catches_them(self):
        cats = {c for c, _ in _cli.greeting_hits(self.ALLOWED_ELSEWHERE)}
        self.assertIn("先谈钱", cats)
        self.assertIn("抢答到岗时间", cats)

    def test_the_style_rules_apply_everywhere(self):
        for fn in (_cli.style_hits, _cli.greeting_hits):
            with self.subTest(fn=fn.__name__):
                self.assertTrue(fn(self.BANNED_EVERYWHERE),
                                "互联网黑话在哪个渠道都不该有")

    def test_the_exemption_is_still_written_in_the_framework(self):
        """这条测试的全部依据就是 06 那句话。它没了，拆分就没有理由了。"""
        self.assertIn("**五条只管渠道 1。**", REF)

    def test_greeting_hits_borrows_style_hits(self):
        """两处各写一份词表，同一个「闭环」迟早一边算违规、另一边不算。"""
        i = CLI.index("def greeting_hits(")
        end = CLI.find("\ndef ", i + 10)
        self.assertIn("style_hits(t)", CLI[i:end if end > 0 else len(CLI)])


class OneSlicerNotTwo(unittest.TestCase):
    """`_greeting_of` 的 docstring 自己写着：同一份文本两个读法，就是两套标准。"""

    def test_the_greeting_uses_the_shared_slicer(self):
        i = SRC.index("def _greeting_of(")
        end = SRC.find("\ndef ", i + 10)
        self.assertIn("_named_section(", SRC[i:end if end > 0 else len(SRC)])

    def test_the_new_check_uses_it_too(self):
        i = SRC.index("def check_other_channels_keep_the_style_rules(")
        end = SRC.find("\ndef ", i + 10)
        self.assertIn("_named_section(", SRC[i:end if end > 0 else len(SRC)])

    def test_it_slices_all_four_channels(self):
        i = SRC.index("def check_other_channels_keep_the_style_rules(")
        end = SRC.find("\ndef ", i + 10)
        seg = SRC[i:end if end > 0 else len(SRC)]
        for ch in ("邮件", "网申自评", "求职信", "内推请托"):
            with self.subTest(channel=ch):
                self.assertIn(f'"{ch}"', seg)

    def test_the_slicer_stops_at_the_next_heading(self):
        text = ("## 网申自评\n把这条链路闭环掉。\n\n## 自检\n这里不算\n")
        self.assertIn("闭环", ap._named_section(text, "网申自评"))
        self.assertNotIn("这里不算", ap._named_section(text, "网申自评"))

    def test_a_missing_section_is_empty_not_an_error(self):
        self.assertEqual(ap._named_section("## 别的\nx\n", "网申自评"), "")


class ItReportsWhatItFound(unittest.TestCase):
    def _run(self, files: dict):
        import tempfile
        from unittest import mock
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name, body in files.items():
                d = root / "users" / "u" / "documents" / "applications" / name
                d.mkdir(parents=True)
                (d / "outreach.md").write_text(body, encoding="utf-8")
            with mock.patch.object(ap, "ROOT", root), \
                 mock.patch.object(ap, "_USER", ["u"]):
                return ap.check_other_channels_keep_the_style_rules({}, {})

    DIRTY = "## 网申自评\n\n多模态这个组合，正是我这三年一直在做的事情，把链路闭环掉。\n"
    CLEAN = "## 网申自评\n\n我做过一年 40 个开源项目，其中一条线专做流程提效。\n"

    def test_a_dirty_segment_is_reported(self):
        got = self._run({"蓝湾智投科技_AI产品经理": self.DIRTY})
        self.assertTrue(got, "网申自评踩了风格铁律却没报")
        self.assertIn("网申自评", got[0][2])
        self.assertIn("/job-apply", got[0][2], "没给该敲的那条命令")

    def test_a_clean_corpus_says_nothing(self):
        self.assertEqual(self._run({"蓝湾智投科技_AI产品经理": self.CLEAN}), [])

    def test_money_and_start_date_are_fine_here(self):
        """渠道 2-4 的豁免要真的生效，不然这条检查会把正常文案报成问题。"""
        body = "## 邮件\n\n我目前离职，随时到岗；期望 45-60k，可以谈。\n"
        self.assertEqual(self._run({"蓝湾智投科技_AI产品经理": body}), [])

    def test_a_placeholder_segment_is_not_counted(self):
        """「无」「见上」这类占位不是一段文案 —— **它不该进分母**。

        第一版只断言「占位段不报」，而占位本来就不踩线，报不报都一样：
        把那道长度过滤整个删掉，测试照样绿（变异当场露馅）。
        判据要落在**分母**上：一份踩线 + 一份占位，那一档是 1/1 不是 1/2。
        """
        got = self._run({"蓝湾智投科技_AI产品经理": self.DIRTY,
                         "川流互联_AI应用产品经理": "## 网申自评\n\n无\n"})
        self.assertTrue(got)
        self.assertIn("1/1 段", got[0][2],
                      f"占位段进了分母 —— 那一档看起来像「一半没问题」：{got[0][2]}")

    def test_it_says_which_channel_and_how_many(self):
        got = self._run({"蓝湾智投科技_AI产品经理": self.DIRTY,
                         "川流互联_AI应用产品经理": self.CLEAN})
        msg = got[0][2]
        self.assertIn("1/2 段", msg, f"按渠道的分子分母不对：{msg}")

    def test_no_active_user_is_silent(self):
        old = list(ap._USER)
        try:
            ap._USER[:] = []
            self.assertEqual(ap.check_other_channels_keep_the_style_rules({}, {}), [])
        finally:
            ap._USER[:] = old


class TheOldDisclaimerIsGone(unittest.TestCase):
    def test_it_no_longer_says_there_is_no_checker(self):
        self.assertNotIn("但眼下没有检查器", SRC,
                         "免责还写着没有检查器 —— 而它现在有了")

    def test_it_points_at_the_new_one(self):
        self.assertIn("由「对外文案：另外几个渠道的文风」", SRC)

    def test_the_check_is_registered(self):
        uses = [ln for ln in SRC.splitlines()
                if "check_other_channels_keep_the_style_rules" in ln
                and not ln.lstrip().startswith("def ")]
        self.assertTrue(uses, "写了检查却没挂进清单")
        self.assertTrue(any("(" in ln and "," in ln for ln in uses), uses)


if __name__ == "__main__":
    unittest.main()
