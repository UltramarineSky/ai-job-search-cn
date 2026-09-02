# -*- coding: utf-8 -*-
"""催猎头和催 HR 该问的不是同一件事，而起草那一步给两类的内容一模一样。

`followups.py` 把清单分成两组，并在抬头上印出各自的道理：

> **猎头代招**：顾问有推荐费驱动，多半会回，还能问出「岗位还在不在」
> 「用人方那边什么反馈」。这批性价比最高，先做。
>
> **企业直招**：BOSS 是聊天框，随时能追一句；猎聘/智联走站内信，
> 多半没有对话入口。具名的公司还能同时找人内推。

也就是说**工具那一侧早就知道两类该问什么**。而 `job-outcome.md` 的起草步骤
第 3 条给两类写的是同一句：「一句客气地问进度」。第 4 步那张表只管**形态**
（多长、发到哪儿），一个字都没管**问什么**。

两个问题只有猎头答得上：

- **「这个岗现在还在招吗」** —— 投出去之后岗位关掉，平台不会通知你。
  实测活动用户 2026-08-23：库里 **20 个岗已下线**，其中 6 个是浏览器实抓时
  看见页面写着「该职位已暂停招聘」。
- **「用人方那边有没有给到反馈」** —— HR 答不了这一问，**他自己就是用人方**。

而直招那边不加这两问：真正能改变结果的是找人内推，那是另一条动作。
"""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import followups as F  # noqa: E402

OUTCOME = (ROOT / "workflows" / "job-outcome.md").read_text(encoding="utf-8")
FU = (ROOT / "tools" / "followups.py").read_text(encoding="utf-8")


def _draft() -> str:
    """起草那一步的第 3 条，到第 4 条为止。"""
    i = OUTCOME.index("3. 写 **60 到 120 字**左右")
    j = OUTCOME.index("4. 按 `channel` 那一列", i)
    return OUTCOME[i:j]


class TheDraftStepBranchesOnWho(unittest.TestCase):
    def test_the_agency_branch_exists(self):
        self.assertIn("猎头那一批，最后那句「问进度」要换成两个他答得上的问题",
                      _draft(), "起草那一步仍然给两类写同一句")

    def test_both_questions_are_named(self):
        seg = " ".join(_draft().split())
        self.assertIn("这个岗现在还在招吗", seg)
        self.assertIn("用人方那边有没有给到反馈", seg)

    def test_it_says_why_hr_cannot_answer_the_second(self):
        """不写这一句，下一版会「为了对称」把两问也加给直招。"""
        self.assertRegex(" ".join(_draft().split()),
                         r"HR 答不了第二问 —— \*\*他自己就是用人方\*\*")

    def test_the_direct_branch_explicitly_does_not_get_them(self):
        """光说「猎头加两问」还不够：不写清另一边不加，就是让人自己猜。"""
        seg = " ".join(_draft().split())
        self.assertIn("不加那两问", seg)

    def test_the_referral_lever_is_not_folded_in(self):
        """具名公司找人内推是**另一条动作**，塞进跟进里会把一条 60 字的
        问进度写成一段求人办事。"""
        self.assertRegex(" ".join(_draft().split()), r"那是另一条动作")

    def test_it_carries_the_measured_cost(self):
        seg = " ".join(_draft().split())
        self.assertIn("20 个岗下线", seg)
        self.assertRegex(seg, r"该职位已暂停招聘")

    def test_it_says_the_platform_does_not_tell_you(self):
        """这才是第一问值钱的理由 —— 不写下来它读起来像客套。"""
        self.assertRegex(" ".join(_draft().split()),
                         r"投出去之后岗位关掉，平台不会通知你")

    def test_it_closes_the_loop_on_a_closed_job(self):
        """问到了却不记，下一轮还会把它排进来。"""
        seg = " ".join(_draft().split())
        self.assertIn("记成 `expired`", seg)
        self.assertRegex(seg, r"别再排进下一轮跟进")

    def test_it_does_not_duplicate_the_form_table(self):
        """第 4 步那张表管形态（多长、发到哪儿）。这一条只管问什么 ——
        抄过来两处就会各长各的（这个仓库的常客）。"""
        seg = _draft()
        self.assertRegex(" ".join(seg.split()), r"管的是\*\*形态\*\*")
        for w in ("2-3 句", "站内私信", "BOSS 直聘"):
            with self.subTest(w=w):
                self.assertNotIn(w, seg, f"把第 4 步那张表的「{w}」抄过来了")
        rows = re.findall(r"^\s*\|", seg, re.M)
        self.assertEqual(rows, [], "这一条自己又画了一张表")

    def test_the_original_three_beats_survive(self):
        """重申兴趣 / 价值提醒 / 问进度 —— 那三句是两类共用的骨架。"""
        seg = _draft()
        for beat in ("一句重申对**这个具体岗位**的兴趣", "具体的价值提醒",
                     "一句客气地问进度", "不要施压"):
            with self.subTest(beat=beat):
                self.assertIn(beat, seg)

    def test_the_length_and_salutation_rules_survive(self):
        seg = _draft()
        self.assertIn("60 到 120 字", seg)
        self.assertIn("contact_person", seg)


class TheReasonComesFromTheToolNotFromNowhere(unittest.TestCase):
    """判据是引用工具已经在印的那两段。它们变了，这一条要跟着。"""

    def test_the_agency_blurb_still_says_it(self):
        self.assertIn("还能问出「岗位还在不在」", FU,
                      "猎头那组的抬头改了 —— 起草那一步引的是它")
        self.assertIn("「用人方那边什么反馈」", FU)

    def test_the_direct_blurb_still_mentions_referral(self):
        self.assertIn("具名的公司还能同时找人内推", FU)

    def test_the_draft_step_quotes_them(self):
        seg = _draft()
        self.assertIn("followups.py", seg, "没说清判据出自哪里")
        self.assertIn("岗位还在不在", seg, "没把工具那句原话引过来")

    def test_the_two_groups_still_exist(self):
        self.assertIn("猎头代招 —— 催顾问", FU)
        self.assertIn("企业直招 —— 催 HR", FU)

    def test_the_tool_can_still_tell_them_apart(self):
        """分不出猎头还是直招时，这条分支就无从执行 —— `agency_map` 是那道判据。"""
        self.assertTrue(hasattr(F, "agency_map"))


class TheExpiryLoopIsReal(unittest.TestCase):
    """第一问的价值建立在「岗位真会悄悄关掉」上。哪天不成立了，这段要重写。"""

    def test_the_store_records_expiry(self):
        import json
        p = ROOT / ".active_user"
        if not p.is_file():
            self.skipTest("没有活动用户")
        u = p.read_text(encoding="utf-8").strip()
        sp = ROOT / "users" / u / "job_scraper" / "seen_jobs.json"
        if not sp.is_file():
            self.skipTest("这个用户还没有职位库")
        seen = json.loads(sp.read_text(encoding="utf-8"))["seen"]
        n = sum(1 for v in seen.values()
                if isinstance(v, dict) and v.get("status") == "expired")
        if not n:
            self.skipTest("这份库里还没有已下线的岗")
        self.assertGreater(n, 0)

    def test_expired_is_a_status_the_outcome_flow_can_write(self):
        """起草那一步让人「记成 expired」—— 那个状态得真的写得进去。"""
        self.assertIn("expired", OUTCOME)


if __name__ == "__main__":
    unittest.main()
