# -*- coding: utf-8 -*-
"""这个工具是照「有经验的社招」写的，每一处都要单独补。

2026-08-22 连着四轮在同一条轴上找到东西 —— 每一处单看都对，合起来看是同一个
盲点：**默认用户有工作经历**。

| 哪里 | 社招写法对应届生的后果 |
|---|---|
| 简历章节顺序（`05`） | 教育背景排第 6，最强信号压在最弱两段下面 |
| 季节日历（`season_note`） | 八月被告知「淡季」，而那是秋招提前批 |
| offer 谈判（`job-offer` Step 1） | 三个数里「当前」填不出来，整张表塌掉 |
| 背调红线（`job-offer` Step 2） | 五条一条都不适用，而学信网那条根本没写 |
| 开场白的佐证（`06` 渠道 1） | 「可验证的数字或作品名」照有工作经历的人写，而同一节禁止抽象形容词 —— 学生要么编，要么落回「学习能力强」 |

**这张表就是这条轴的清单。** 加新的阶段敏感内容时也要加进来 ——
手工名单漏一条，那一处就没人要求它分流（同 `JD_READERS` 那张表的用法）。

判据一律认资料里的「求职状态」这一个字段，**不猜**（不看年龄、学历、工作年限）：
猜错的代价是给一个正在秋招的人说「现在别投」，或者让一个还没工作过的人
去算「涨幅百分比」。
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tests"))
import build_dashboard as B  # noqa: E402
from _srcscan import code_of  # noqa: E402

#: 阶段敏感的点：(说明, 文件, 必须出现的判据词)
STAGE_POINTS = [
    ("简历章节顺序", "workflows/reference/05-cv-templates.md",
     "「教育背景」要提到「工作经历」之前"),
    ("offer 可守区间", "workflows/job-offer.md", "应届生：上面那三个数里有一个不存在"),
    ("背调红线", "workflows/job-offer.md", "应届生查的是另外几样"),
    ("开场白的佐证", "workflows/reference/06-outreach-templates.md",
     "还没工作过的人，第 2 行拿什么填"),
]


class EveryKnownPointBranches(unittest.TestCase):
    def test_each_one_has_its_branch(self):
        for label, rel, needle in STAGE_POINTS:
            with self.subTest(point=label):
                t = (ROOT / rel).read_text(encoding="utf-8")
                self.assertIn(needle, t, f"{label} 没有应届分支了")

    def test_the_season_calendar_branches_in_code(self):
        """这一处在代码里，不在文档里 —— 单列。"""
        self.assertEqual(B.hiring_calendar("在读")[8][0], "旺")
        self.assertEqual(B.hiring_calendar("在职")[8][0], "淡")


class TheJudgementIsAlwaysTheSameField(unittest.TestCase):
    def test_the_docs_branch_on_the_stated_status(self):
        for label, rel, _ in STAGE_POINTS:
            with self.subTest(point=label):
                t = (ROOT / rel).read_text(encoding="utf-8")
                self.assertRegex(
                    t, r"求职状态|应届生 / 在校生|在读 / 应届",
                    f"{label} 没说清按哪个字段分流")

    def test_the_code_path_reads_only_that_field(self):
        # **只扫代码。** docstring 里恰恰写着「不看年龄、学历、工作年限」——
        # 那正是这条测试要保住的那句话。连着注释一起扫等于禁止把理由写下来，
        # 而这个坑 2026-08-22 一天栽了七次，修法收在 `_srcscan` 里。
        seg = code_of("tools/export_web_data.py", "def candidate_stage(")
        self.assertIn("求职状态", seg)
        for w in ("年限", "年龄", "学历"):
            with self.subTest(w=w):
                self.assertNotIn(w, seg, f"阶段判定里掺进了「{w}」")


class TheGreetingTellsStudentsWhatCounts(unittest.TestCase):
    """禁掉套话而不给替代，等于把人推向编造。"""

    TPL = (ROOT / "workflows" / "reference"
           / "06-outreach-templates.md").read_text(encoding="utf-8")

    def _seg(self):
        i = self.TPL.index("还没工作过的人，第 2 行拿什么填")
        return self.TPL[i:i + 1400]

    def test_it_names_the_sources_of_evidence(self):
        for src in ("实习", "竞赛", "毕设"):
            with self.subTest(src=src):
                self.assertIn(src, self._seg(), f"没说「{src}」怎么当佐证")

    def test_school_counts_in_campus_hiring(self):
        """这一点和社招相反 —— 不说明的话，学生会照社招的规矩把它藏起来。"""
        seg = self._seg()
        self.assertIn("学校与专业", seg)
        self.assertRegex(seg, r"和社招相反|社招简历上摆学校是弱信号",
                         "没说清这一条在两个阶段是反的")

    def test_thin_material_is_not_an_excuse(self):
        """「没有亮眼的东西」既不是编造的理由，也不是套话的理由。"""
        self.assertRegex(self._seg(), r"不是编造的理由", "没堵住这个口子")

    def test_the_boundary_rule_still_applies(self):
        self.assertIn("铁律 3", self._seg(), "这一档没重申能力边界禁区")


class TheCampusBackgroundCheckNamesTheRealOnes(unittest.TestCase):
    """校招背调查的是学历和实习，不是薪资和离职证明。"""

    OFF = (ROOT / "workflows" / "job-offer.md").read_text(encoding="utf-8")

    def _seg(self):
        i = self.OFF.index("### 应届生查的是另外几样")
        return self.OFF[i:i + 1400]

    def test_the_first_item_is_the_degree_registry(self):
        self.assertIn("学信网", self._seg(), "校招背调第一项不见了")

    def test_internships_are_covered(self):
        seg = self._seg()
        self.assertIn("实习", seg, "没查实习经历")
        self.assertRegex(seg, r"出事率最高|朋友公司挂的",
                         "没说清实习那条为什么最要紧")

    def test_it_says_the_social_list_does_not_apply(self):
        """不说这句，读者会以为两张表都要过一遍。"""
        self.assertRegex(self._seg(), r"一条都不适用")


if __name__ == "__main__":
    unittest.main()
