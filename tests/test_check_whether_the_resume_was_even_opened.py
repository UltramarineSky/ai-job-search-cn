# -*- coding: utf-8 -*-
"""面板和自检都说「问题多半在简历或投递方式上」—— 那是两个假设焊在一起。

零回音时，两处给的下一步都是「先催一遍，再回头审一遍简历」：

    面板（`build_dashboard._why_silent`）  「…这批才是信号。先催一遍…再回头审一遍简历。」
    自检（`doctor.next_step`）             「企业直招那批也全没回音，问题多半在简历或投递方式上。」

**「简历」和「投递方式」是两个完全不同的病，治法也完全不同** —— 而工具没有
任何一处去分辨是哪一个，直接开了「审简历」这一味药。

## 平台白给这个答案

国内主流平台在「投递记录 / 我的投递」里逐条标着这份简历有没有被打开
（猎聘、智联写「已查看 / 未查看」，BOSS 看那条会话对面点没点开）。它一眼就能分：

    大多已查看、还是没回  →  HR 打开了没往下走  →  这才轮到审简历
    大多未查看            →  简历根本没被打开    →  改简历没用，要换的是投什么岗、什么时候投

实测 2026-08-23：全仓 `已查看` / `未查看` / `简历状态` 这几个词**一次都没出现过**。
而活动用户 85 笔投递 0 回音、76 笔过了静默线，面板正照着未分辨的诊断让他去审简历。

## 为什么落在 Step 2b，而不是面板上

面板那句的顺序本来就是「**先催一遍**…再回头审简历」，而「催」就是
`/job-outcome followup` —— 检查放在那儿，天然排在审简历之前，
面板一个字都不用改。

而且这条**只对企业直招那一组成立**：猎头那组的「已查看」是顾问看了、
不是用人方看了。Step 2b 本来就已经按组分好（「猎头那批，催之前先看一眼邮箱」，
末句还写着「直招那一组不受影响」）—— 这条正是它的姊妹条，挂在同一个位置。
"""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import build_dashboard as bd  # noqa: E402

OUT = (ROOT / "workflows" / "job-outcome.md").read_text(encoding="utf-8")
BD = (ROOT / "tools" / "build_dashboard.py").read_text(encoding="utf-8")
DOC = (ROOT / "tools" / "doctor.py").read_text(encoding="utf-8")


def step2b() -> str:
    i = OUT.index("## Step 2b：跟进分支")
    return OUT[i:OUT.index("## Step 3", i)]


def block() -> str:
    """只切这一块，**不要一路切到 Step 2b 末尾**。

    后面还有一张「按平台调整跟进形态」的表；切过头的话，
    「这一块有几行」那条断言数到的是 7 行而不是 2 行（实测）。
    """
    seg = step2b()
    i = seg.index("**直招那批，催之前先看一眼投递记录页。**")
    end = seg.index("是两件事」。", i) + len("是两件事」。")
    return seg[i:end]


class TheCheckExists(unittest.TestCase):
    def test_step2b_has_it(self):
        self.assertIn("**直招那批，催之前先看一眼投递记录页。**", step2b(),
                      "催之前仍然没有任何一处去分辨简历有没有被打开")

    def test_it_names_where_to_look_per_platform(self):
        """「去看一下」不是指令。要说清在哪个页面、那一栏叫什么。"""
        seg = " ".join(block().split())
        self.assertIn("投递记录 / 我的投递", seg)
        self.assertRegex(seg, r"猎聘、智联写\s*「已查看 / 未查看」")
        self.assertIn("BOSS 看那条会话对面点没点开", seg)

    def test_it_splits_the_two_diagnoses(self):
        """整条的价值就在这个二分。少一边就退回原来那句糊在一起的话。"""
        seg = " ".join(block().split())
        self.assertRegex(seg, r"大多\*\*已查看\*\*、还是没回")
        self.assertRegex(seg, r"大多\*\*未查看\*\*")

    def test_each_branch_gives_a_different_action(self):
        rows = [ln for ln in block().splitlines()
                if ln.strip().startswith("|") and "---" not in ln
                and "你看到的" not in ln]
        self.assertEqual(len(rows), 2, f"不是两行：{rows}")
        self.assertIn("/job-resume", rows[0])
        self.assertIn("改简历没用", rows[1])

    def test_the_unopened_branch_says_what_to_change_instead(self):
        """「改简历没用」不是行动。得说清换什么。"""
        seg = " ".join(block().split())
        self.assertRegex(seg, r"要换的是投什么岗、什么时候投")
        self.assertIn("蓄水池", seg, "没点名最常见的那一类")

    def test_it_cites_the_existing_reservoir_rule(self):
        """蓄水池的判据框架里已经有了，引它，别另立一条。"""
        self.assertIn("04-job-evaluation.md", block())
        self.assertIn("蓄水池嫌疑",
                      (ROOT / "workflows" / "reference"
                       / "04-job-evaluation.md").read_text(encoding="utf-8"))

    def test_it_only_applies_to_direct_hires(self):
        """猎头那组的「已查看」是顾问看了 —— 混进去这条就废了。"""
        seg = " ".join(block().split())
        self.assertRegex(seg, r"只对直招这一组有意义")
        self.assertRegex(seg, r"是顾问看了，不是用人方看了")

    def test_it_has_a_degraded_path(self):
        """平台不显示、或他懒得逐条看 —— 不能因此卡住催进度。"""
        seg = " ".join(block().split())
        self.assertRegex(seg, r"照常往下催")

    def test_the_degraded_path_still_withholds_the_conclusion(self):
        """这才是降级里要紧的一半：没查过，就不能照「审简历」那条走。"""
        seg = " ".join(block().split())
        self.assertRegex(seg, r"别把「审简历」当成已经定下的\s*下一步")
        self.assertRegex(seg, r"「『没查』和『查过没有』是两件事」")


class TheSiblingItPairsWithIsIntact(unittest.TestCase):
    """它挂在「猎头那批先看邮箱」旁边。那一条没了，这条就落了单。"""

    def test_the_agency_half_survives(self):
        self.assertIn("**猎头那批，催之前先看一眼邮箱。**", step2b())

    def test_the_agency_half_still_hands_off_to_this_one(self):
        """末句「直招那一组不受影响」正是这条的挂点。"""
        self.assertIn("直招那一组不受影响：他们本来就多半不走邮件", step2b())

    def test_this_one_comes_after_it(self):
        self.assertLess(step2b().index("**猎头那批，催之前先看一眼邮箱。**"),
                        step2b().index("**直招那批，催之前先看一眼投递记录页。**"))

    def test_the_two_group_split_still_exists(self):
        """整条建立在 `followups.py` 真的把清单切成猎头/直招两组上。"""
        fu = (ROOT / "tools" / "followups.py").read_text(encoding="utf-8")
        self.assertIn('(True, "猎头代招 —— 催顾问"', fu)
        self.assertIn('(False, "企业直招 —— 催 HR"', fu)




if __name__ == "__main__":
    unittest.main()
