# -*- coding: utf-8 -*-
"""校招和社招的旺淡月份不一样，最要紧的分歧在七八月。

面板那句季节提示原来只有一张日历 —— 社招的（金三银四 / 金九银十、七八月淡、
年底封编制）。而对在读/应届：

    7-8 月   社招：淡季（HR 休假）      校招：**秋招提前批**，全年最早也最重要的窗口
    12-1 月  社招：淡季（等年终奖）     校招：秋招收尾 + 春招备战

**一个在读的学生八月打开面板，会被告知「七八月是淡季，HR 都在休假」—— 正好说反**，
而那正是他该动起来的时候。

判据只认资料里的「求职状态」这一个字段，**不去猜**（不看年龄、学历、工作年限）。
读不出来就一句季节的话都不说 —— **说错季节比不说更坏**：它会让人在该动的时候
按兵不动，或者在真淡季白投一轮。
"""
import datetime as dt
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import build_dashboard as B  # noqa: E402
import export_web_data as X  # noqa: E402

AUG = dt.date(2026, 8, 22)


class TheCalendarBranchesOnStage(unittest.TestCase):
    def test_august_is_slack_for_the_experienced(self):
        self.assertEqual(B.hiring_calendar("在职")[8][0], "淡")

    def test_august_is_peak_for_students(self):
        """这就是那个反着的月份。"""
        tier, why = B.hiring_calendar("在读")[8]
        self.assertEqual(tier, "旺")
        self.assertIn("提前批", why)

    def test_unknown_stage_gets_no_calendar(self):
        for v in (None, "", "   "):
            with self.subTest(v=v):
                self.assertIsNone(B.hiring_calendar(v))

    def test_it_does_not_guess_from_anything_else(self):
        """只认这一个字段。猜错的代价是给一个正在秋招的人说「现在别投」。"""
        src = (ROOT / "tools" / "build_dashboard.py").read_text(encoding="utf-8")
        i = src.index("def hiring_calendar(")
        seg = src[i:i + 700]
        for w in ("年限", "学历", "年龄"):
            with self.subTest(w=w):
                self.assertNotIn(w, seg, f"日历判定里掺进了「{w}」")


class TheNoteSaysNothingWhenItCannotTell(unittest.TestCase):
    def test_silence_beats_a_wrong_season(self):
        self.assertEqual(B.season_note([8] * 10, AUG, None), "")

    def test_the_experienced_path_is_unchanged(self):
        out = B.season_note([8] * 10, AUG, "离职，正在找工作")
        self.assertIn("金九银十", out, "社招那条路被改坏了")

    def test_a_student_gets_no_slack_excuse_in_august(self):
        """八月对他们是旺季 —— 「这批赶上了淡季」根本不成立，就该一句不说。"""
        self.assertEqual(B.season_note([8] * 10, AUG, "在读（2027 届）"), "")


class TheStageComesFromTheProfile(unittest.TestCase):
    def test_it_reads_the_raw_file_not_the_normalized_text(self):
        """`profile_text` 走 `_norm`，换行被折掉 —— 那时捕获组会吃进下一条 bullet。"""
        src = (ROOT / "tools" / "export_web_data.py").read_text(encoding="utf-8")
        i = src.index("def candidate_stage(")
        seg = src[i:src.index("\ndef ", i + 1)]
        self.assertIn("candidate.md", seg, "没有直接读原文")
        self.assertNotIn("profile_text(user)", seg, "又用了折过行的那份")

    def test_the_bold_colon_form_parses(self):
        """资料里那一行是 `- **求职状态：** 离职，正在找工作`，冒号在加粗里面。"""
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            d = root / "users" / "张三" / "profile"
            d.mkdir(parents=True)
            (d / "candidate.md").write_text(
                "- **求职状态：** 在读（2027 届）\n- **到岗时间：** 随时\n",
                encoding="utf-8")
            saved = X.ROOT
            try:
                X.ROOT = root
                self.assertEqual(X.candidate_stage("张三"), "在读")
            finally:
                X.ROOT = saved

    def test_an_unfilled_placeholder_is_not_a_stage(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            d = root / "users" / "张三" / "profile"
            d.mkdir(parents=True)
            (d / "candidate.md").write_text(
                "- **求职状态：** [YOUR_EMPLOYMENT_STATUS]\n", encoding="utf-8")
            saved = X.ROOT
            try:
                X.ROOT = root
                self.assertIsNone(X.candidate_stage("张三"))
            finally:
                X.ROOT = saved


if __name__ == "__main__":
    unittest.main()
