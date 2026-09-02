# -*- coding: utf-8 -*-
"""「这两周正好把简历和材料备齐，到时候集中投」——对手上攒着 62 份的人，这是让他压着不发。

金九银十确实是内地招聘一年里最大的时间杠杆，`season_note` 提前 N 天说这件事是对的。
但那句建议**预设了「材料还没备好」**，而实测活动用户 2026-08-23：

    备好没发的       62 份
    材料做出来了、岗却先关了   11 个

**旺季的价值在新岗多、HR 活跃 —— 那是给下一批用的；手上这批的窗口是各自的
职位挂多久，跟旺季没关系。** 两件事不冲突，但说反了就会让人白等两周，
而那 11 个已经说明了压着的代价。

所以分流：手上够投一轮时（`SHORTLIST_FLOOR`）改说「这批别等，旺季用来补新的」，
并把 11 这个数摆出来当证据 —— 没有它，那句话只是个说法。
手上没料时原话不变。
"""
import datetime as dt
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import build_dashboard as B  # noqa: E402

#: 全投在淡季（社招 7-8 月），而九月旺季就在眼前。
SLACK = [7, 7, 8, 8, 8]
BEFORE = dt.date(2026, 8, 23)


def _note(ready=0, lost=0, today=BEFORE, months=None):
    """季节那一句。**`lost` 不再进它** —— 2026-09-01 搬去了 `_ready_text`
    （理由同 `TheClauseHasOneHome` 当初挪走「排了两周以上」那一句：
    `season_note` 说不出话时返回空串，把跟季节无关的事放它那儿，
    那些时候整句就没了）。参数留着是因为好几条用例拿它当「有丢过」的开关。
    """
    del lost
    return B.season_note(months or SLACK, today, "在职", ready)


def _ready(lost=0, old_n=0):
    """材料那一句 —— 「已经白做了几个」现在住这儿。"""
    return B._ready_text(62, 30, old_n, None, lost)


class TheHeadsUpWindowIsPinned(unittest.TestCase):
    """提前 `SEASON_HEADS_UP_DAYS` 天说旺季 —— 这个数此前**一条测试都没有**。

    它是面板上那句「另外：那批全投在淡季，而金九银十还有 N 天开始」的窗口，
    定义处写着理由：「一个月：再早说，用户这一个月什么也做不了，那就成了噪音。」

    没人钉它的话，两个方向都会静默出事：

        调大到 90  → 三个月前就开始念叨，那句话变成噪音，读的人从此略过整段
        调小到 3   → 等于没有这句提醒，而它是内地招聘一年里最大的那个时间杠杆

    所以钉**边界行为**（不是那个数字长什么样）：差 31 天说，差 32 天闭嘴。
    """

    #: 淡季投的那几个月 —— 让 `season_note` 走到「那批全投在淡季」那一支。
    SLACK = [7, 7, 8, 8, 8]

    def _note(self, day):
        return B.season_note(self.SLACK, day, "在职", 0, None) or ""

    def test_it_speaks_up_at_the_edge(self):
        """9 月 1 日往前数 31 天 = 8 月 1 日，正好在窗口里。"""
        got = self._note(dt.date(2026, 8, 1))
        self.assertIn("还有 31 天开始", got,
                      "窗口边界上不说了 —— 这个提醒缩水了")

    def test_it_stays_quiet_one_day_earlier(self):
        """再往前一天就是 32 天，超出窗口 —— 早说等于噪音。"""
        self.assertNotIn("天开始", self._note(dt.date(2026, 7, 31)),
                         "窗口被放宽了 —— 提前一个多月念叨，读的人会略过整段")

    def test_the_countdown_is_the_real_gap(self):
        """句子里那个数就是真实天数，不是一个写死的说法。"""
        for day, ahead in ((dt.date(2026, 8, 2), 30),
                           (dt.date(2026, 8, 31), 1)):
            with self.subTest(day=day):
                self.assertIn(f"还有 {ahead} 天开始", self._note(day))

    def test_the_reason_for_the_number_is_written_down(self):
        """改这个数的人要看得见「为什么是一个月」。"""
        src = (ROOT / "tools" / "build_dashboard.py").read_text(
            encoding="utf-8")
        i = src.index("SEASON_HEADS_UP_DAYS = ")
        seg = " ".join(src[max(0, i - 400):i].split())
        self.assertIn("再早说", seg, "那个数没留下理由")


class TheAdviceBranchesOnWhatIsInHand(unittest.TestCase):
    def test_with_nothing_ready_it_still_says_prepare(self):
        n = _note(ready=0)
        self.assertIn("金九银十", n)
        self.assertIn("备齐", n, "手上没料时那句原话不该被改掉")

    def test_with_a_round_in_hand_it_says_send_them_now(self):
        n = _note(ready=62, lost=11)
        self.assertIn("别等", n, "还在让他把备好的压到旺季")
        self.assertNotIn("备齐", n, "两句话同时出现，等于没给结论")

    def test_it_still_names_the_season(self):
        """分流之后季节那半句不许丢 —— 它才是这条提示存在的理由。"""
        self.assertIn("金九银十", _note(ready=62))

    def test_it_says_what_the_season_is_actually_for(self):
        """只说「别等」是把旺季一起否掉了。要说清旺季干什么用。"""
        self.assertRegex(_note(ready=62), r"补新的|用来补")

    def test_the_evidence_is_shown_when_there_is_some(self):
        """**这句话跟季节没关系，两季都要说。**

        它原来只住在「旺季还有 N 天」那一支里。2026-09-01 当天进了金九银十，
        `season_note` 改走「已经进旺季」那一支 return，整句消失 —— 而手上
        正有 12 个白做了。终端那边（`doctor.ready_note`）从来只问「有没有」，
        不问季节；两个入口对同一个事实一个说一个不说。
        """
        self.assertIn("11 个", _ready(lost=11))

    def test_it_is_said_in_peak_season_too(self):
        """支点：换个日子它不许消失 —— 那正是 2026-09-01 那一下。"""
        self.assertIn("11 个", _ready(lost=11))
        self.assertNotIn("下线", _note(ready=62, today=dt.date(2026, 9, 10)))

    def test_it_does_not_invent_evidence(self):
        """一个都没丢过的时候不许硬说「已经有 0 个下线了」。"""
        self.assertNotIn("下线", _ready(lost=0))
        self.assertIn("别等", _note(ready=62))

    def test_the_threshold_is_the_shared_one(self):
        """「够投一轮」这个概念全仓库只有一个数（`SHORTLIST_FLOOR`），
        `test_one_number_per_concept` 盯着它。这里不许另立一个。"""
        self.assertNotIn("别等", _note(ready=B.SHORTLIST_FLOOR - 1))
        self.assertIn("别等", _note(ready=B.SHORTLIST_FLOOR))
        src = (ROOT / "tools" / "build_dashboard.py").read_text(encoding="utf-8")
        i = src.index("def season_note(")
        seg = src[i:src.index("\ndef ", i + 10)]
        self.assertIn("SHORTLIST_FLOOR", seg, "又写了一个自己的门槛")


class TheOtherBranchesAreUntouched(unittest.TestCase):
    def test_already_in_season_is_unchanged(self):
        """旺季已经到了那一支说的是「值得再投一轮」，和这次的分流无关。"""
        n = _note(ready=62, today=dt.date(2026, 9, 10))
        self.assertIn("再投一轮", n)
        self.assertNotIn("别等", n)

    def test_applications_in_peak_season_say_nothing(self):
        """投在旺季的批次，季节解释不了它 —— 硬提一句只会给个台阶下。"""
        self.assertEqual(_note(ready=62, months=[9, 9, 10, 10]), "")

    def test_an_unknown_stage_still_says_nothing(self):
        """说错季节比不说更坏。资料里没写求职状态就一句都不说。"""
        self.assertEqual(B.season_note(SLACK, BEFORE, None, 62), "")


class TheEvidenceIsCounted(unittest.TestCase):
    def test_the_export_computes_it(self):
        src = (ROOT / "tools" / "export_web_data.py").read_text(encoding="utf-8")
        self.assertIn('"expired_unsent"', src, "没算「备好了却等到下线」")
        i = src.index('"expired_unsent"')
        seg = src[i:i + 400]
        # **不能走 `funnels`**：`is_parked` 已经把已下线的排掉了，
        # 这里数的恰恰是被排掉的那一批。
        self.assertNotIn("funnels", seg, "用 funnels 数的话这个数恒为 0")
        for w in ('j.get("materials")', 'j.get("expired")'):
            with self.subTest(w=w):
                self.assertIn(w, seg)

    def test_it_reaches_the_advice(self):
        src = (ROOT / "tools" / "build_dashboard.py").read_text(encoding="utf-8")
        i = src.index("_head = _ready_text(")
        self.assertIn("expired_unsent", src[i:i + 300], "算了没传进去")
        i2 = src.index("_season = season_note(")
        self.assertIn('counts.get("ready")', src[i2:i2 + 300])

    def test_on_real_data_it_is_not_zero_by_accident(self):
        """真数据兜底：口径写错时这个数会静默变 0，而 0 只是让那半句话消失。"""
        data = ROOT / "web" / "public" / "data.json"
        if not data.is_file():
            self.skipTest("还没导出面板数据")
        snap = json.loads(data.read_text(encoding="utf-8"))
        n = sum(1 for j in snap["jobs"]
                if j.get("materials") and j.get("expired")
                and not j.get("applied") and not j.get("dupOf"))
        if n == 0:
            self.skipTest("这份数据里确实一个都没有")
        self.assertIn(f"{n} 个", snap["nextStep"]["text"],
                      "算出来了，那句建议里却没有它")


if __name__ == "__main__":
    unittest.main()
