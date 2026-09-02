# -*- coding: utf-8 -*-
"""「金九银十」的十月，头一周是七天法定长假 —— 而工具一个字都没提过。

全仓搜过（2026-08-24）：`国庆` 0 命中、`黄金周` 0 命中、`长假` 0 命中。

而面板在十月会说「现在已经进金九银十了——条件变了，值得再投一轮」。
10 月 3 日读到这句话的人照做，投出去的东西要到 10 月 8 日才有人打开；
更糟的是七天之后工具会按静默线提醒他「该催了」，
而对面**根本没上过班**。

## 它和春节那个坎是两件事，别合并

    春节   三四周的冻结，**压过**月份表 —— 那段时间「现在是淡季」这句话
           既太轻也太晚，他要知道的是「没回音不怪你的材料」。
    国庆   七天的暂停，落在旺季**正中间**。十月是旺季没错，但头一周没人上班
           —— 所以它是**补一句**，不是改结论。

这个区别不是修辞：春节那支 `return`，国庆这支拼在句尾。合成一个「假期」概念
就会在十月把「该投」整句盖掉，而那正好说反。

## 不用查表

国庆是**公历固定**的 10 月 1–7 日。春节要表是因为它是农历的
（`SPRING_FESTIVAL`）—— 两处不必长一个样。
"""
import datetime as dt
import pathlib
import re
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import build_dashboard as bd  # noqa: E402

BD = (ROOT / "tools" / "build_dashboard.py").read_text(encoding="utf-8")


def flat(s: str) -> str:
    s = " ".join(re.sub(r"^\s*(?:>|#:?)\s?", "", s, flags=re.M).split())
    return re.sub(r"(?<=[一-鿿，。；：、（）「」])"
                  r" +(?=[一-鿿，。；：、（）「」])", "", s)


class ThePhaseTracksTheHoliday(unittest.TestCase):
    def _p(self, m, d, y=2026):
        return bd.national_day_phase(dt.date(y, m, d))

    def test_the_holiday_itself_is_covered(self):
        for d in (1, 4, bd.NATIONAL_DAY_LAST):
            with self.subTest(d=d):
                self.assertEqual(self._p(10, d)[0], "假期")

    def test_the_days_just_before_count_too(self):
        """9 月 29 号发出去的，当天也没人看了 —— 假期实际比日历长。"""
        self.assertEqual(self._p(9, 30 - bd.NATIONAL_DAY_BEFORE + 1)[0], "假期")

    def test_earlier_september_says_nothing(self):
        self.assertIsNone(self._p(9, 20))

    def test_coming_back_is_its_own_phase(self):
        """「假期中」和「刚回来」该做的事不同：一个是等，一个是别急着改材料。"""
        for d in (bd.NATIONAL_DAY_LAST + 1, bd.NATIONAL_DAY_AFTER):
            with self.subTest(d=d):
                self.assertEqual(self._p(10, d)[0], "刚回来")

    def test_late_october_says_nothing(self):
        self.assertIsNone(self._p(10, bd.NATIONAL_DAY_AFTER + 1))

    def test_it_works_in_any_year(self):
        """公历固定 —— 不查表，也就没有「表用完了」这回事。"""
        for y in (2027, 2035, 2099):
            with self.subTest(y=y):
                self.assertEqual(self._p(10, 3, y)[0], "假期")

    def test_the_holiday_message_says_what_changes(self):
        msg = self._p(10, 3)[1]
        self.assertIn("要等节后才有人看", msg)
        self.assertIn("别按这几天的沉默下结论", msg)


    def test_the_back_to_work_message_says_be_patient(self):
        msg = self._p(10, 10)[1]
        self.assertIn("积压", msg)
        self.assertIn("先别急着改材料", msg)

    def test_no_markdown_or_jargon(self):
        for d in (3, 10):
            with self.subTest(d=d):
                msg = self._p(10, d)[1]
                self.assertNotIn("**", msg)
                for w in ("硬门", "四维", "判词", "台账", "短名单"):
                    self.assertNotIn(w, msg)


class ItAppendsInsteadOfOverriding(unittest.TestCase):
    """**这是它和春节那支唯一的、也是最要紧的区别。**"""

    SLACK = [7, 7, 8, 8, 8]

    def test_the_peak_message_survives(self):
        got = bd.season_note(self.SLACK, dt.date(2026, 10, 3), "在职")
        self.assertIn("已经进金九银十了", got)
        self.assertIn("值得再投一轮", got)

    def test_the_holiday_is_appended_after_it(self):
        got = bd.season_note(self.SLACK, dt.date(2026, 10, 3), "在职")
        self.assertLess(got.index("值得再投一轮"), got.index("国庆假期"))

    def test_it_reads_as_a_caveat_not_a_second_topic(self):
        """两个「另外」接在一起读起来像两条无关的话。"""
        got = bd.season_note(self.SLACK, dt.date(2026, 10, 3), "在职")
        self.assertEqual(got.count("另外"), 1, got)
        self.assertIn("。不过 ", got)

    def test_outside_the_window_the_message_is_unchanged(self):
        got = bd.season_note(self.SLACK, dt.date(2026, 10, 20), "在职")
        self.assertIn("已经进金九银十了", got)
        self.assertNotIn("国庆", got)

    def test_the_spring_festival_branch_still_overrides(self):
        """春节那支必须仍然是 `return` —— 两支合并就会在十月说反话。"""
        got = bd.season_note([1, 1, 1, 2, 2, 12], dt.date(2026, 2, 17), "在职")
        self.assertIn("春节前后", got)
        self.assertNotIn("值得再投一轮", got)

    def test_the_difference_is_written_down(self):
        i = BD.index("NATIONAL_DAY_BEFORE = ")
        seg = flat(BD[max(0, i - 900):i])
        self.assertRegex(seg, r"和春节那个坎是两件事，别合并")
        self.assertRegex(seg, r"落在「金九银十」的\*\*正中间\*\*")
        self.assertRegex(seg, r"它是\*\*补一句\*\*，不是改结论")

    def test_the_wiring_says_why_it_does_not_return(self):
        i = BD.index("holiday = national_day_phase(today)")
        seg = flat(BD[max(0, i - 500):i])
        self.assertRegex(seg, r"补一句，不是改结论")
        self.assertRegex(seg, r"所以它拼在句尾，不 return")

    def test_no_speculative_copy_in_the_lookahead_branch(self):
        """假期窗口整个落在旺季月份里，那一支永远轮不到 —— 别在那儿也加一份。"""
        i = BD.index('tail = ("。" + holiday[1]) if holiday else ""')
        seg = flat(BD[i:i + 400])
        self.assertRegex(seg, r"下面那条「旺季还有 N 天」永远轮不到")
        # **只数 `season_note` 函数体里那个独立的 `tail`。**
        # 同一个函数里还有 `lost_tail` / `old_tail`，别处的函数也有同名局部变量
        # —— 全文数子串会把它们全算进来（第一版就这么错的）。
        body = BD[BD.index("def season_note("):
                  BD.index("NO_REPLY_ALARM = ", BD.index("def season_note("))]
        self.assertEqual(
            len(re.findall(r"(?<![\w_])tail(?![\w_])", body)), 2,
            "预告那一支又加回去了 —— 这个函数里独立的 tail 只该出现两次"
            "（赋值一次、旺季那支拼一次）")


class TheWindowIsInsideThePeak(unittest.TestCase):
    """现算：假期窗口的每一天在两张日历上都落在旺季月份里。

    这是「只拼在旺季那一支」成立的前提 —— 哪天月份表改了，这条会红。
    """

    def test_every_day_of_the_window_is_a_peak_month(self):
        y = 2026
        d = dt.date(y, 10, 1) - dt.timedelta(days=bd.NATIONAL_DAY_BEFORE)
        end = dt.date(y, 10, bd.NATIONAL_DAY_AFTER)
        while d <= end:
            with self.subTest(d=d.isoformat()):
                self.assertEqual(bd.HIRING_SEASON.get(d.month, ("平",))[0], "旺",
                                 f"{d} 落在非旺季月份 —— "
                                 f"那「旺季还有 N 天」那一支就轮得到了，"
                                 f"tail 要在那儿也拼一份")
            d += dt.timedelta(days=1)

    def test_the_campus_calendar_agrees(self):
        """校招表里 9/10 月同样是旺（秋招正式批）—— 学生走的是那张表。"""
        for m in (9, 10):
            with self.subTest(m=m):
                self.assertEqual(bd.CAMPUS_SEASON.get(m, ("平",))[0], "旺")


class TheSignalItLeansOnIsReal(unittest.TestCase):
    def test_it_was_absent_before(self):
        hits = []
        for base in ("workflows", "tools"):
            for f in sorted((ROOT / base).rglob("*")):
                if f.suffix not in (".md", ".py") or "__pycache__" in str(f):
                    continue
                if f.name == "build_dashboard.py":
                    continue
                if "国庆" in f.read_text(encoding="utf-8", errors="replace"):
                    hits.append(f.name)
        self.assertEqual(hits, [], f"这几处也讲了国庆，判据可能已经分叉：{hits}")

    def test_it_would_fire_for_the_batch_he_is_about_to_send(self):
        """**这一条不是纸上规则。** 他手上备好没发的那批要在九月发出去，
        而十天的静默线正好跨过国庆 —— 那时这句话才是它该出现的地方。
        """
        import json
        p = ROOT / "web" / "public" / "data.json"
        if not p.is_file():
            self.skipTest("还没导出过面板数据")
        d = json.loads(p.read_text(encoding="utf-8"))
        ready = (d.get("nextStep") or {}).get("ready") or 0
        if ready < 10:
            self.skipTest("手上没有成批备好的材料")
        # 九月下旬发出去、十天静默线落在假期里 —— 那正是这条要挡的误报
        sent = dt.date(2026, 9, 25)
        self.assertIsNotNone(
            bd.national_day_phase(sent + dt.timedelta(days=10)),
            "十天静默线没落进假期窗口 —— 去看 NATIONAL_DAY_AFTER 是不是收窄了")


if __name__ == "__main__":
    unittest.main()
