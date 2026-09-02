# -*- coding: utf-8 -*-
"""「挡你最多的是 X（N）」——那句话印的是 `blockers[0]`，而这个列表从没排过序。

它按**追加顺序**装：英语 → 学历 → 行业。于是实测活动用户 2026-08-23，
屏幕上写着：

    挡你最多的是英语要求（32）

而同一份数据里：

    行业经验太集中  319/687   ← 真正最多的
    学历/专业       215/960
    英语要求         32/960   ← 屏幕上说它最多

**把最小的那个说成了最大的**，而且指错了方向：真正挡他最多的正是行业经验，
那也是这批评估反复指向的同一件事（专业能力够、行业经验对不上）。
一个折叠面板的标题行，多数时候是用户唯一会读的那句话。

三项分母不同（英语/学历在 960 个硬门 FAIL 里数，行业经验在 687 个评过分的里数），
所以这里同时钉两件事：**倒序**，以及**展开后逐行印 `n/of`** ——
只印 `n` 不印分母的话，混着比就真的会误导。按率算次序也一样（46% > 22% > 3%），
不会打架。
"""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import export_web_data as X  # noqa: E402

APP = (ROOT / "web" / "src" / "App.tsx").read_text(encoding="utf-8")
RREAD = (ROOT / "web" / "src" / "components"
         / "ResumeRead.tsx").read_text(encoding="utf-8")


class TheListIsSortedBiggestFirst(unittest.TestCase):
    def test_the_producer_sorts(self):
        src = (ROOT / "tools" / "export_web_data.py").read_text(encoding="utf-8")
        i = src.index("def resume_insight(")
        seg = src[i:src.index("\ndef ", i + 10)]
        self.assertRegex(seg, r'blockers\.sort\(key=lambda b: -b\["n"\]\)',
                         "blockers 没有按个数倒序")

    def test_the_real_snapshot_is_ordered(self):
        """拿真数据兜底 —— 排序写了但被后面的代码又追加一项，照样会错。"""
        data = ROOT / "web" / "public" / "data.json"
        if not data.is_file():
            self.skipTest("还没导出过面板数据")
        import json
        ri = json.loads(data.read_text(encoding="utf-8")).get("resumeInsight")
        if not ri or len(ri.get("blockers") or []) < 2:
            self.skipTest("这份数据里挡路项不足两条")
        ns = [b["n"] for b in ri["blockers"]]
        self.assertEqual(ns, sorted(ns, reverse=True), f"没有倒序：{ns}")


class TheHeadlineReadsTheFirstOne(unittest.TestCase):
    """标题和列表必须同源。各取各的，就又能各说各的。"""

    def test_it_prints_index_zero(self):
        i = APP.index("挡你最多的是")
        seg = APP[max(0, i - 200):i + 200]
        self.assertIn("blockers[0]", seg, "标题不是取列表第一项")

    def test_it_prints_the_count(self):
        i = APP.index("挡你最多的是")
        self.assertRegex(APP[i:i + 120], r"blockers\[0\]\.n",
                         "标题只说名字不给数")


class TheDenominatorIsVisibleWhereItMatters(unittest.TestCase):
    """三项分母不同。标题只印 `n`（可以），展开的逐行必须印 `n/of`。"""

    def test_each_row_shows_its_own_denominator(self):
        i = RREAD.index("rread-bn")
        self.assertRegex(RREAD[i:i + 300], r"b\.of \? `/\$\{b\.of\}`",
                         "逐行没印分母，混着比就会误导")


class SortingDoesNotChangeWhatEachOneMeans(unittest.TestCase):
    """排序只动次序。每一项的名字、口吻、说明都不许被顺手改掉。"""

    TONES = {"英语要求": "fixed", "学历/专业": "ask", "行业经验太集中": "choose"}

    def test_the_three_kinds_keep_their_tone(self):
        src = (ROOT / "tools" / "export_web_data.py").read_text(encoding="utf-8")
        i = src.index("def resume_insight(")
        seg = src[i:src.index("\ndef ", i + 10)]
        for name, tone in self.TONES.items():
            with self.subTest(name=name):
                m = re.search(rf'"name": "{re.escape(name)}"[^}}]*?"tone": "(\w+)"',
                              seg, re.S)
                self.assertIsNotNone(m, f"{name} 那一项不见了")
                self.assertEqual(m.group(1), tone, f"{name} 的口吻变了")

    def test_the_english_note_still_refuses_to_widen_the_exclusion(self):
        """这条是用户资料里记过一次的事故：「凡沾英语一律排除」。
        面板不许建议他去加一条资料里没有的排除条款。"""
        src = (ROOT / "tools" / "export_web_data.py").read_text(encoding="utf-8")
        i = src.index('"name": "英语要求"')
        seg = src[i:i + 1600]
        self.assertIn("不用新增排除条款", seg)
        self.assertRegex(seg, r"外企.{0,12}划掉|中文工作环境")


if __name__ == "__main__":
    unittest.main()
