# -*- coding: utf-8 -*-
"""国内一年里最深的招聘低谷是农历的，而季节表按公历月分档。

`HIRING_SEASON` 把 12、1、2 月一起标成「年底封编制，多数人等年终奖」。
那句话没错，但它太粗，而且**边界在错的地方**：

    春节（正月初一）在公历 1 月 21 日到 2 月 20 日之间浮动，年份不同差整整一个月。
    真正的冻结是**节前两周到节后开工**那三四周：HR 大量休假、面试排不上、审批停摆。
    而「金三银四」的那个「三」，起点是**元宵之后**，不是公历 3 月 1 日。

实测 2026：春节 2 月 17、元宵 3 月 3 —— **那一年三月头一周市场还没醒，
而按月分档的表已经在喊「金三银四还有 N 天开始」了。**

全仓搜过：`春节` 0 命中、`招聘冻结` 0 命中（2026-08-24）。

## 冻结那一档最要紧的不是「淡季」，是别误诊

投在冻结期里没回音，说明不了材料的事。而这个工具在零回音时会把人指去审简历
（`no_reply_advice`）—— 在那三四周里，那是照着错的诊断动刀。

## 只有表，没有算法

农历要天文历，而这个仓库只用标准库。春节日期几十年前就定死了，抄一次即可。
**表用完就说「不知道」，绝不外推** —— 「上一年加 11 天」这种近似会错到十几天，
比不说更坏（同这个模块已有的「认不出求职状态就返回 None，不猜」）。
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


class TheTableIsAFactNotAGuess(unittest.TestCase):
    def test_the_dates_are_all_in_the_possible_window(self):
        """春节只可能落在 1/21–2/20。落在窗外的一定是抄错了。"""
        for y, (m, d) in bd.SPRING_FESTIVAL.items():
            with self.subTest(y=y):
                x = dt.date(y, m, d)
                self.assertGreaterEqual(x, dt.date(y, 1, 21), f"{y} 太早")
                self.assertLessEqual(x, dt.date(y, 2, 20), f"{y} 太晚")

    def test_consecutive_years_move_by_a_lunar_amount(self):
        """相邻两年相差 353~385 天（闰月与否）。差出这个范围就是抄错了。"""
        ys = sorted(bd.SPRING_FESTIVAL)
        for a, b in zip(ys, ys[1:]):
            if b - a != 1:
                continue
            gap = (dt.date(b, *bd.SPRING_FESTIVAL[b])
                   - dt.date(a, *bd.SPRING_FESTIVAL[a])).days
            with self.subTest(pair=(a, b)):
                self.assertTrue(353 <= gap <= 385, f"{a}→{b} 差 {gap} 天")

    def test_a_year_outside_the_table_says_nothing(self):
        """**不外推。** 近似会错到十几天，比不说更坏。"""
        self.assertIsNone(bd.spring_festival(1999))
        self.assertIsNone(bd.spring_festival(2099))
        self.assertIsNone(bd.spring_festival_phase(dt.date(2099, 2, 10)))

    def test_it_covers_enough_years_to_be_useful(self):
        self.assertGreaterEqual(len(bd.SPRING_FESTIVAL), 8)

    def test_the_reason_it_is_a_table_is_recorded(self):
        i = BD.index("SPRING_FESTIVAL = {")
        seg = flat(BD[max(0, i - 1500):i])
        self.assertRegex(seg, r"只有表，没有算法")
        self.assertRegex(seg, r"表用完就诚实地说「不知道」，绝不外推")
        self.assertRegex(seg, r"1 月 21 日到 2 月 20 日之间浮动")


class ThePhasesLineUpWithTheDate(unittest.TestCase):
    CNY = dt.date(2026, 2, 17)          # 表里那一年

    def _p(self, off):
        return bd.spring_festival_phase(self.CNY + dt.timedelta(days=off))

    def test_the_freeze_covers_both_sides(self):
        for off in (-bd.FREEZE_BEFORE, -3, 0, 3, bd.FREEZE_AFTER):
            with self.subTest(off=off):
                self.assertEqual(self._p(off)[0], "冻结")

    def test_before_the_freeze_it_says_nothing(self):
        self.assertIsNone(self._p(-bd.FREEZE_BEFORE - 1))

    def test_the_ramp_up_is_its_own_phase(self):
        """「刚开工」和「冻结」对下一步的含义相反 —— 混成一档就废了一半。"""
        for off in (bd.FREEZE_AFTER + 1, bd.LANTERN_AFTER):
            with self.subTest(off=off):
                self.assertEqual(self._p(off)[0], "刚开工")

    def test_after_the_lantern_it_says_nothing(self):
        self.assertIsNone(self._p(bd.LANTERN_AFTER + 1))

    def test_the_freeze_message_stops_the_misdiagnosis(self):
        """**这是冻结那一档存在的理由。** 零回音时工具会把人指去审简历。"""
        msg = self._p(0)[1]
        self.assertIn("没回音说明不了你材料的事", msg)
        self.assertIn("别据此改简历", msg)

    def test_the_freeze_message_says_what_to_do_instead(self):
        msg = self._p(0)[1]
        self.assertIn("节后开工那两周", msg)
        self.assertIn("现在把料备齐", msg)

    def test_it_names_the_actual_date(self):
        """「这几周是春节前后」太虚 —— 他要能自己对一下日历。"""
        self.assertIn("2 月 17 日", self._p(0)[1])

    def test_the_ramp_message_says_go(self):
        msg = self._p(bd.FREEZE_AFTER + 2)[1]
        self.assertIn("现在投是对的时候", msg)
        self.assertIn("别急着下结论", msg)

    def test_no_markdown_or_jargon_reaches_the_user(self):
        for off in (0, bd.FREEZE_AFTER + 2):
            with self.subTest(off=off):
                msg = self._p(off)[1]
                self.assertNotIn("**", msg)
                for w in ("硬门", "四维", "判词", "台账", "短名单"):
                    self.assertNotIn(w, msg)


class TheMarchWindowStartsAtTheLantern(unittest.TestCase):
    """**这是真正的错话。** 三月到了不等于开春了。"""

    SLACK = [1, 1, 1, 2, 2, 12]         # 全投在淡季

    def test_it_does_not_announce_spring_before_the_lantern(self):
        # 2026：春节 2/17 → 元宵 3/3。2/25 时三月只剩 4 天，
        # 而市场要到 3/3 才醒 —— 旧写法会喊「金三银四还有 4 天开始」。
        got = bd.season_note(self.SLACK, dt.date(2026, 2, 25), "在职")
        self.assertNotIn("金三银四还有 4 天", got)

    def test_it_does_announce_once_the_lantern_has_passed(self):
        # 2027：春节 2/6 → 元宵 2/21。2/25 时早过了，该正常预告。
        got = bd.season_note(self.SLACK, dt.date(2027, 2, 25), "在职")
        self.assertIn("金三银四还有 4 天开始", got)

    def test_the_skip_is_explained(self):
        i = BD.index("continue                    # 三月到了，元宵还没到")
        seg = flat(BD[max(0, i - 900):i])
        self.assertRegex(seg, r"三月那一档的起点跟着春节走，不是 3 月 1 日")
        self.assertRegex(seg, r"2026 年春节 2 月 17、元宵 3 月 3")

    def test_an_unknown_year_falls_back_quietly(self):
        """算不出元宵只是少几天精度，不是错话 —— 不许因此整句不说。

        （锚要带上 ` or ` 那半句：`cny = spring_festival(today.year)` 在
        `spring_festival_phase` 里也有一份，`index()` 会取到那一处。）
        """
        i = BD.index("cny = spring_festival(today.year) or ")
        seg = flat(BD[max(0, i - 900):i])
        self.assertRegex(seg, r"退回月初，并且\*\*不声张\*\*")


class TheFreezeOverridesTheMonthTable(unittest.TestCase):
    SLACK = [1, 1, 1, 2, 2, 12]

    def test_inside_the_freeze_it_says_the_freeze(self):
        got = bd.season_note(self.SLACK, dt.date(2026, 2, 17), "在职")
        self.assertIn("春节前后", got)
        self.assertNotIn("金三银四", got)

    def test_it_still_opens_with_the_same_connector(self):
        """这句话是拼在别的句子后面的，接头词不能变。"""
        got = bd.season_note(self.SLACK, dt.date(2026, 2, 17), "在职")
        self.assertTrue(got.startswith("另外："), got[:12])

    def test_it_applies_to_campus_too(self):
        """春招同样是元宵之后开 —— 学生不该被告知三月一号就开跑。

        （校招日历里的淡季只有五六月，12/1 月**根本不在表里**，
        照社招那套月份传进来会算成 2/6 不达标，整句返回空串。）
        """
        got = bd.season_note([5, 5, 5, 6, 6, 6], dt.date(2026, 2, 17), "应届")
        self.assertIn("春节前后", got)

    def test_the_month_table_still_works_outside_the_window(self):
        """只在那三四周里压过月份表，其余时候原样。"""
        got = bd.season_note([7, 7, 8, 8, 8], dt.date(2026, 8, 24), "在职")
        self.assertIn("金九银十", got)

    def test_an_unlisted_year_leaves_the_old_behaviour_alone(self):
        got = bd.season_note([7, 7, 8, 8, 8], dt.date(2099, 8, 24), "在职")
        self.assertIn("金九银十", got)

    def test_the_override_is_explained(self):
        i = BD.index("phase = spring_festival_phase(today)")
        seg = flat(BD[max(0, i - 700):i])
        self.assertRegex(seg, r"春节那个坎压过月份表")
        self.assertRegex(seg, r"那两张表按公历月分档，而这件事按农历走")


class TheThingsItLeansOnSurvive(unittest.TestCase):
    """这一条只加一层。原来那几条判据一个字都不该动。"""

    def test_it_still_refuses_when_the_stage_is_unknown(self):
        self.assertEqual(bd.season_note([1, 1, 2], dt.date(2026, 2, 17), None), "")

    def test_it_still_needs_most_of_them_in_the_slack_season(self):
        """偶尔一两个落在淡季说明不了什么 —— 八成的门槛不许被绕过。"""
        self.assertEqual(
            bd.season_note([3, 4, 9, 10, 1], dt.date(2026, 2, 17), "在职"), "")

    def test_the_two_calendars_still_split(self):
        self.assertIs(bd.hiring_calendar("在读"), bd.CAMPUS_SEASON)
        self.assertIs(bd.hiring_calendar("在职"), bd.HIRING_SEASON)
        self.assertIsNone(bd.hiring_calendar(""))

    def test_the_dont_hold_ready_materials_rule_survives(self):
        """「手上备好的别等」比季节重要，别被新分支挡掉。"""
        got = bd.season_note([7, 7, 8, 8, 8], dt.date(2026, 8, 24), "在职",
                             ready=60)
        self.assertIn("别等", got)
        # 「已经白做了 N 个」2026-09-01 搬去了 `_ready_text`（季节一变
        # 那一句整句消失，判据见那儿）。这里改成对着新住址问同一件事。
        self.assertIn("11 个岗", bd._ready_text(60, 30, 0, None, 11))


class TheSignalItLeansOnIsReal(unittest.TestCase):
    """现算：这件事此前真的一次都没被提过。"""

    def test_it_was_absent_before(self):
        hits = []
        for base in ("workflows", "tools"):
            for f in sorted((ROOT / base).rglob("*")):
                if f.suffix not in (".md", ".py") or "__pycache__" in str(f):
                    continue
                if f.name == "build_dashboard.py":
                    continue
                if "春节" in f.read_text(encoding="utf-8", errors="replace"):
                    hits.append(f.name)
        self.assertEqual(hits, [], f"这几处也讲了春节，判据可能已经分叉：{hits}")

    def test_the_current_user_would_not_see_it_today(self):
        """他的投递全在八月 —— 这一条对他现在不触发，那是对的。

        （这条不是在验功能，是在钉住「不该说的时候不说」：
        季节那一句只在能改变下一步时才出现。）
        """
        got = bd.spring_festival_phase(dt.date.today())
        if got:
            self.skipTest("今天真的在那个窗口里 —— 那就该说")
        self.assertIsNone(got)


if __name__ == "__main__":
    unittest.main()
