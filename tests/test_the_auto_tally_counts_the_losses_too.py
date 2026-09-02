# -*- coding: utf-8 -*-
"""`/job-auto` 的总账**只报流入** —— 而它正是造出那个队列的命令。

总账要四个数：评了多少、可投多少、出了多少份材料、队列还剩多少。四个都是流入。
而每跑一趟，「备好没发」那一队就更长一点，队头在烂：岗位下线，材料跟着白做。

实测活动用户 2026-08-25：

    有材料没投   67 个
    其中已下线   12 个   ← 这 12 份材料全是白做的
    还活着       55 个   （放了中位 14 天、14 份排了两周以上）

**同一个病，这是第三次只治一半。** 面板早就在说
（`build_dashboard.season_note`），自检 2026-08-24 才补上
（`doctor.ready_age` 的说明记着那次），而造出这个队列的命令自己一个字没有。

一份材料是一次公司调研加起草审稿两轮，比一次待评贵得多 —— 而总账同一时刻
会说「出材料 N 份」，读起来像又前进了一步。
"""
from __future__ import annotations

import importlib
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
doctor = importlib.import_module("doctor")

AUTO = (ROOT / "workflows" / "job-auto.md").read_text(encoding="utf-8")


def section() -> str:
    i = AUTO.index("### 总账还要有一行")
    j = AUTO.find("\n## ", i)
    return AUTO[i:j if j > 0 else len(AUTO)]


class TheTallyMustNameTheBacklog(unittest.TestCase):

    def test_the_section_exists(self):
        self.assertIn("### 总账还要有一行", AUTO)

    def test_it_says_the_four_numbers_are_all_inflow(self):
        """不说这句，读的人看不出为什么还要加一行。"""
        self.assertIn("全是流入", section())

    def test_all_three_numbers_are_required(self):
        """**钉在「缺一不可」那一句里**，不是整节里有没有那两个字。

        变异检验逮到：把「有几个岗在你发出去之前就下线了」从要求里删掉，
        底下那段实测说明里还有「12 个已经下线」——整节找关键词照样绿。
        这个仓库同一个毛病已经第五次：**断言被窗口里别处的同一个词喂饱。**
        """
        seg = section()
        i = seg.index("缺一不可")
        # 要求那一句到句号为止：三个数都得在这一句里点名。
        demand = seg[i:seg.index("。", i) + 1]
        for k in ("备好没发", "最久", "下线"):
            with self.subTest(k=k):
                self.assertIn(k, demand,
                              f"「缺一不可」那一句里没点名「{k}」：{demand}")

    def test_it_names_the_command_that_prints_them(self):
        """**每一处引导都要写出该敲的命令**（`AGENTS.md`）。"""
        self.assertIn("python tools/doctor.py", section())

    def test_it_points_at_the_judge_not_a_second_copy(self):
        """措辞与「有没有话说」的判据只有一份 —— 在 `ready_note`。"""
        self.assertIn("doctor.ready_note()", section())

    def test_it_does_not_turn_into_a_gate_on_making_materials(self):
        """**这一行不是让 auto 少出材料。**

        出材料花的是 AI 的工时不是他的（2026-08-12 裁定，那道点头闸门已撤）。
        把「积压多」写成「少出点」会直接推翻那条裁定。
        """
        seg = section()
        self.assertIn("不是让 auto 少出材料", seg)
        self.assertIn("2026-08-12", seg)

    def test_it_records_that_this_is_the_third_half_treated(self):
        seg = section()
        self.assertIn("第三次只治一半", seg)
        self.assertIn("build_dashboard.season_note", seg)
        self.assertIn("doctor.ready_age", seg)


class TheNumbersItAsksForReallyExist(unittest.TestCase):
    """**现拿代码来对。** 要求报三个数，而那三个数得真的算得出来。"""

    def test_ready_age_returns_all_three_keys(self):
        a = doctor.ready_age(ROOT / "users" / _active())
        if not a:
            self.skipTest("没有面板快照 —— 那时它按约定返回 {}，不猜")
        for k in ("n", "old", "lost", "median"):
            with self.subTest(k=k):
                self.assertIn(k, a)

    def test_ready_note_says_nothing_when_there_is_nothing_to_say(self):
        """一个都没过期、也没排超过两周 → 空串，这一行不占地方。"""
        with tempfile.TemporaryDirectory() as td:
            self.assertEqual(doctor.ready_note(Path(td)), "",
                             "没有快照时也该闭嘴，而不是编一句")

    def test_the_two_referenced_names_are_real(self):
        """引一条不存在的东西，这个仓库栽过一次（规则真、出处假）。"""
        self.assertTrue(hasattr(doctor, "ready_age"))
        self.assertTrue(hasattr(doctor, "ready_note"))
        bd = importlib.import_module("build_dashboard")
        self.assertTrue(hasattr(bd, "season_note"))


class ItIsNotZeroByAccident(unittest.TestCase):
    """现算：这一行对活动用户此刻的数据真的有话说。"""

    def test_the_live_note_carries_the_loss(self):
        udir = ROOT / "users" / _active()
        if not udir.is_dir():
            self.skipTest("没有活动用户")
        a = doctor.ready_age(udir)
        if not a or not a.get("n"):
            self.skipTest("手上没有备好没发的材料 —— 好事")
        note = doctor.ready_note(udir)
        if not a.get("lost") and not a.get("old"):
            self.assertEqual(note, "", "没什么可说时却说了话")
            self.skipTest("既没过期也没排太久")
        self.assertTrue(note, "有话说却返回了空串")
        self.assertIn(str(a["n"]), note)
        if a.get("lost"):
            self.assertIn("白做", note,
                          "有材料因为岗位下线而白做，那句话却没提")


def _active() -> str:
    p = ROOT / ".active_user"
    return p.read_text(encoding="utf-8").strip() if p.is_file() else ""


if __name__ == "__main__":
    unittest.main()
