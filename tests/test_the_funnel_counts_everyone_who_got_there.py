# -*- coding: utf-8 -*-
"""漏斗那几根条是**累计**的，Step 2 的归一表是互斥的——中间要换一次算法。

`/job-html-report` 同一个文件里隔着一百多行写着两句话：

    Step 2  「先把投递记录里的取值映射成五个标准桶」  ← 互斥，一行只落一格
    Step 3  「已投递 → 面试中 → …，每根条 = 走到这一步的数量」  ← 累计

照互斥表画累计漏斗，每一格都比真的少：「已投递」只剩还停在已投递的那些，
「面试中」不含已经拿到 offer 的，而漏斗会不再逐级递减。

实测 2026-08-27 当时没显形：88 行里 87 个还停在「已投递」，两种算法只差 1。
**它要等到真有人走到面试才露出来，而那正是这张报表最有用的时候**——
所以不能靠「跑一次看看对不对」发现，只能钉在文档上。

总览页那条漏斗早就是累计的，且把理由写在函数注释里
（`funnels_of`：「一个岗可以同时在『已投递』和『面试中』里」）。
两块屏幕上「面试中」是同一个词，就必须是同一个数 ——
`test_report_wording_matches_the_panel` 已经钉住了「同一个词」，
这条钉住「同一个数」。
"""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

REPORT = (ROOT / "workflows" / "job-html-report.md").read_text(encoding="utf-8")
EXPORT = (ROOT / "tools" / "export_web_data.py").read_text(encoding="utf-8")

#: 漏斗那一条的唯一锚（`test_test_anchors_are_unambiguous` 要求锚唯一）。
ANCHOR = "**投递漏斗**（横向条形）"


class TheFunnelSaysItIsCumulative(unittest.TestCase):
    def setUp(self):
        self.assertEqual(REPORT.count(ANCHOR), 1, "锚不唯一了")
        self.seg = REPORT[REPORT.index(ANCHOR):][:2200]

    def test_it_says_the_two_tables_differ(self):
        self.assertIn("累计", self.seg, "没说明这一张是累计口径")
        self.assertIn("互斥", self.seg,
                      "没点破 Step 2 那张表是互斥的——转换那一步就没有理由")

    def test_each_bar_lists_the_statuses_it_counts(self):
        """光说「累计」不够，要给出每根条数哪些状态，否则还是各人各解。"""
        for st in ("interview", "offer", "hired"):
            with self.subTest(st=st):
                self.assertIn(st, self.seg, f"没说「{st}」算进哪根条")
        self.assertIn("interview_only", self.seg,
                      "没交代 interview_only 为什么不进「面试中」——"
                      "下一个人会觉得漏了，然后单方面加上去")

    def test_the_interview_bar_includes_everyone_past_it(self):
        """「面试中」必须含已经走更远的那些，否则漏斗不再逐级递减。"""
        i = self.seg.index("面试中 |")
        row = self.seg[i:self.seg.index(chr(10), i)]
        for st in ("interview", "offer", "hired"):
            with self.subTest(st=st):
                self.assertIn(st, row, f"「面试中」那一行漏了 {st}")

    def test_the_pie_is_explicitly_left_exclusive(self):
        """别把累计推广到环形图——饼图的片本来就该互不重叠。"""
        self.assertRegex(self.seg, r"环形图?[^。]{0,40}互不重叠|互斥的地方只有",
                         "没划清哪张图仍然用互斥口径")

    def test_it_points_at_the_one_authority(self):
        self.assertIn("funnels_of", self.seg, "没指向总览页那条同源判据")


class TheAuthorityStillSaysCumulative(unittest.TestCase):
    """引用的那句话得真在正本里——引对了名字、引错了内容一样会分叉。"""

    def test_funnels_of_is_still_the_cumulative_one(self):
        i = EXPORT.index("def funnels_of(")
        doc = EXPORT[i:i + 1400]
        self.assertIn("累计口径", doc,
                      "funnels_of 改成互斥了？那报表那一节要跟着改")
        self.assertIn("INTERVIEW_STATUSES", EXPORT[i:i + 2600],
                      "面试那一格的成员判据换了地方，报表那张表要跟着核")

    def test_the_report_does_not_copy_the_member_list(self):
        """报表要**指向**正本，不是抄一份成员清单下来。"""
        i = REPORT.index(ANCHOR)
        self.assertIn("_INTERVIEW_STATUSES", REPORT[i:i + 2400],
                      "没指名成员清单的正本在哪，抄件迟早各长各的")

    def test_the_interview_statuses_match_what_the_report_lists(self):
        """正本的成员集合与报表那一行逐个对上，不靠人眼。"""
        src = (ROOT / "tools" / "build_dashboard.py").read_text(encoding="utf-8")
        m = re.search(r"_INTERVIEW_STATUSES\s*=\s*[{(]([^})]*)[})]", src)
        self.assertIsNotNone(m, "找不到 _INTERVIEW_STATUSES 的定义")
        members = set(re.findall(r"[\"']([a-z_ ]+)[\"']", m.group(1)))
        self.assertTrue(members, "INTERVIEW_STATUSES 解析出来是空的")
        i = REPORT.index(ANCHOR)
        row_i = REPORT.index("面试中 |", i)
        row = REPORT[row_i:REPORT.index(chr(10), row_i)]
        missing = sorted(s for s in members if s not in row)
        self.assertEqual(missing, [],
                         f"正本的「面试中」含 {sorted(members)}，"
                         f"而报表那一行没写上 {missing}")


if __name__ == "__main__":
    unittest.main()
