# -*- coding: utf-8 -*-
"""「粘到{平台}的聊天框直接发」——对 71 个岗来说，那个聊天框不存在。

发出去是整条流水线里唯一要人做的那一步（`AGENTS.md`「只有一处要人」），
而面板对每个岗都印同一句话。同一个仓库的另外两处**早就分了流**：

    followups.py     「BOSS 是聊天框，随时能追一句；猎聘/智联走站内信，
                      多半没有对话入口」            ← 催的时候知道
    job-gmail-sync   「猎聘 · 企业直招 → 站内信为主」
                     「猎聘 · 猎头代招 → 邮件 / 微信居多」  ← 回音那一侧也知道

**催的时候知道形态，发的时候不知道。** 实测活动用户 2026-08-23，
当时那 264 份开场白的 (平台 × 猎头/直招) 分布是：

    猎聘 · 猎头代招   126   找的是顾问，有对话
    猎聘 · 企业直招    63   多半只有站内信 / 网申表单
    BOSS · 直招       24   聊天框
    智联 / 前程 · 直招   8   站内信为主
    没判过             11   不猜

**71 个被指去找一个多半不存在的入口。**

顺带把 `06-outreach-templates.md` 里两处自相矛盾的话对齐了：铁律 0 原写
「开场白粘进猎聘/BOSS 的聊天框」、渠道 1 的标题原写「（猎聘 / BOSS 直聘聊天框）」
—— 而同一个仓库的渠道表说猎聘企业直招走站内信。现在三处同一个模型。
`job-apply.md` 1.5a 那条（网申/考编/公共邮箱 = 无对话方，不出开场白）
讲的是**另一件事**：那里根本没有人可写；这里是有人、只是入口不同。
"""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import _cli  # noqa: E402

GSYNC = (ROOT / "workflows" / "job-gmail-sync.md").read_text(encoding="utf-8")
TPL = (ROOT / "workflows" / "reference"
       / "06-outreach-templates.md").read_text(encoding="utf-8")
READOUT = (ROOT / "web" / "src" / "components"
           / "JobReadout.tsx").read_text(encoding="utf-8")


class TheJudgeBranchesOnBothAxes(unittest.TestCase):
    def test_a_headhunter_job_always_has_someone_to_talk_to(self):
        """平台不影响这一条：猎头本人就是对话方。"""
        for p in ("猎聘", "BOSS 直聘", "智联招聘", ""):
            with self.subTest(portal=p):
                self.assertIs(_cli.has_chat_box(p, True), True)

    def test_boss_is_a_chat_box_even_for_direct_hire(self):
        self.assertIs(_cli.has_chat_box("BOSS 直聘", False), True)

    def test_the_other_portals_direct_hire_are_not(self):
        for p in ("猎聘", "智联招聘", "前程无忧"):
            with self.subTest(portal=p):
                self.assertIs(_cli.has_chat_box(p, False), False)

    def test_unjudged_is_not_answered_either_way(self):
        """**三态。** 对一个可能是猎头挂的岗说「这里没有聊天框」，
        和当初把 1358 个猎头岗印成直招是同一类事故。"""
        self.assertIsNone(_cli.has_chat_box("猎聘", None))
        self.assertIsNone(_cli.has_chat_box("", False))


class TheHintTellsHimWhereToPasteIt(unittest.TestCase):
    def test_each_branch_says_a_different_place(self):
        got = {
            "猎头": _cli.send_hint("猎聘", True),
            "BOSS": _cli.send_hint("BOSS 直聘", False),
            "猎聘直招": _cli.send_hint("猎聘", False),
            "没判过": _cli.send_hint("猎聘", None),
        }
        self.assertEqual(len(set(got.values())), 4, f"有两支说了同一句：{got}")

    def test_the_no_chat_branch_names_the_alternative(self):
        """只说「没有聊天框」等于把他丢在原地。要说出该走哪儿。"""
        self.assertIn("站内信", _cli.send_hint("猎聘", False))

    def test_the_unjudged_branch_does_not_assert(self):
        h = _cli.send_hint("猎聘", None)
        self.assertNotIn("没有聊天框", h, "没判过却断言了没有")
        self.assertRegex(h, r"先看|有就", "没告诉他怎么自己确认")

    def test_latin_portal_names_get_one_space_on_the_left_only(self):
        """「粘到BOSS 直聘的」挤在一起；两边都补又会得到「BOSS 直聘 的」——
        「的」是中文助词，前面不该有空格。"""
        self.assertIn("粘到 BOSS 直聘的聊天框", _cli.send_hint("BOSS 直聘", False))

    def test_a_chinese_portal_name_gets_no_leading_space(self):
        """**今天走不到这一支**（`CHAT_PORTALS` 里只有 BOSS，纯拉丁），
        所以要临时把一个中文平台加进词表才测得到。不这么测，
        「无脑两边都补空格」这个改动一条测试都不会红 —— 变异实测漏过一次。
        接一个中文名的新平台是随时可能发生的事（`/job-add-portal` 就干这个）。"""
        import unittest.mock as mock
        with mock.patch.object(_cli, "CHAT_PORTALS", ("脉脉",)):
            self.assertIn("粘到脉脉的聊天框", _cli.send_hint("脉脉", False))


class ThePanelPrintsItPerJob(unittest.TestCase):
    def test_the_label_reads_the_field(self):
        # **别锚 `act-label`** —— 那个 class 在这个文件里有 4 处
        # （开场白、邮件、主题、网申自评），`index()` 取第一处纯属侥幸。
        # 锚渲染点自己独有的那个字段名。
        self.assertIn("m.sendVia", READOUT, "面板还在印那句笼统的话")
        i = READOUT.index("m.sendVia")
        self.assertIn("act-label", READOUT[max(0, i - 400):i],
                      "那句说明不在「复制开场白」旁边那一行上了")

    def test_it_falls_back_on_old_snapshots(self):
        """旧 data.json 没这个字段。没有回退的话那一行会空掉，
        而这是整页最常按的那一下旁边的说明。"""
        i = READOUT.index("m.sendVia")
        self.assertIn("??", READOUT[i:i + 200], "没有回退")

    def test_the_export_fills_it(self):
        src = (ROOT / "tools" / "export_web_data.py").read_text(encoding="utf-8")
        self.assertIn('mats["sendVia"] = _cli.send_hint(', src, "导出没算这个字段")
        i = src.index('mats["sendVia"]')
        self.assertIn("via_headhunter(", src[i:i + 200], "没把猎头三态传进去")


class TheThreePlacesTellTheSameStory(unittest.TestCase):
    """一个事实写在三处：渠道表（markdown）、催进度的分组文案、这份判据。
    分叉过一次就再也对不齐 —— 这一组盯着它们。"""

    def test_the_channel_table_still_splits_liepin(self):
        """那张表是这个模型的正本。猎聘拆成两行才谈得上分流。"""
        self.assertIn("猎聘 · 企业直招", GSYNC)
        self.assertIn("猎聘 · 猎头代招", GSYNC)

    def test_the_table_and_the_code_agree_on_boss(self):
        row = next(ln for ln in GSYNC.splitlines()
                   if ln.startswith("| **BOSS 直聘**"))
        self.assertIn("聊天框", row)
        self.assertIs(_cli.has_chat_box("BOSS 直聘", False), True)

    def test_the_table_and_the_code_agree_on_liepin_direct(self):
        row = next(ln for ln in GSYNC.splitlines()
                   if ln.startswith("| 猎聘 · 企业直招"))
        self.assertIn("站内信", row)
        self.assertIs(_cli.has_chat_box("猎聘", False), False)

    def test_the_template_no_longer_says_liepin_is_a_chat_box(self):
        """铁律 0 与渠道 1 的标题原来都写死「猎聘/BOSS 的聊天框」。"""
        head = TPL[:TPL.index("### 这 200 字在回答一个问题")]
        self.assertNotIn("粘进猎聘/BOSS 的聊天框", head, "铁律 0 还是旧说法")
        self.assertNotIn("（猎聘 / BOSS 直聘聊天框）", head, "渠道 1 标题还是旧说法")

    def test_the_template_points_at_the_split(self):
        head = TPL[:TPL.index("### 这 200 字在回答一个问题")]
        self.assertIn("企业直招", head, "没说清哪一类没有对话入口")
        self.assertIn("send_hint", head, "没指向机器可读的那份判据")

    def test_it_does_not_change_how_the_text_is_written(self):
        """入口变了，写法没变 —— 不说这句，读者会以为站内信那一类要另写一套。"""
        head = TPL[:TPL.index("### 这 200 字在回答一个问题")]
        self.assertRegex(head, r"照样适用|变的只是")

    def test_the_no_counterparty_rule_is_a_different_thing(self):
        """`job-apply.md` 1.5a 讲的是「根本没有人可写」（网申/考编/公共邮箱），
        不是「有人但入口不同」。它那句理由不许再用「没有聊天框」——
        那会和上面这套读成互相矛盾。"""
        apply_md = (ROOT / "workflows" / "job-apply.md").read_text(encoding="utf-8")
        i = apply_md.index("**无对话方时**")
        self.assertNotIn("没有聊天框", apply_md[i:i + 120])
        # **锚在那张表上，不数字符。** 原来往前取 600 字找「网申表单」——
        # 2026-08-24 在同一张表里加了一行「对方先来找你」（外加一段说明），
        # 窗口就够不到那一行了，而它要守的规则一个字没动。
        table = apply_md[apply_md.index("### 1.5a 有没有对话方"):i]
        self.assertIn("网申表单", table,
                      "1.5a 那张表里没有「网申表单」那一行了 —— "
                      "「无对话方」就没了出处")


if __name__ == "__main__":
    unittest.main()
