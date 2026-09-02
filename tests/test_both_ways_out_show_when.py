# -*- coding: utf-8 -*-
"""出局两条路，只有一条把日期带到了屏幕上。

搁置区里「已下线」印着「（2026-08-14 标的）」，而「你排除的」只有一句理由 ——
`skip_date` 库里 88 条、叠加层里还有一份，**导出从没带过它**。
实测活动用户 2026-08-25：面板上 96 个不投的岗，一个日期都没有。

为什么这个日期要紧：**求职拖久了，标准自己会动。** 第一周否掉的和上周否掉的
不是一回事，而搁置区里它们长得一模一样。

## 同一条对称规则，这是第二半

2026-08-25 刚给 `job-rank.md` 补过「出局两条路都得记日期」（那次修的是**写入端**：
它只说「把 status 置为 expired」，没说记日期，于是执行者自己发明了 `expired_date`）。
**写入端补上了，显示端还是不对称的** —— 这一份补的是后半。

## 加的时候当场踩了一个

叠加层一行上只有**一个** `date`，而 `decision` 可能是 `skipped` 也可能是
`expired`。第一版两条线都无条件读它，于是面板上标了「已下线」的两个岗
同时报出一个它从没有过的「不投日期」（96 个不投的岗，带 `skipDate` 的却有 97 个）。
`expiredDate` 那一侧本来就有同样的毛病，溢出 8 个 —— 它没露馅，只是因为渲染
那一支被 `gone` 挡着。**挡得住不等于算得对。**
"""
import json
import pathlib
import re
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import _cli  # noqa: E402
import audit_pipeline as ap  # noqa: E402
import export_web_data as ex  # noqa: E402

EX = (ROOT / "tools" / "export_web_data.py").read_text(encoding="utf-8")
TYPES = (ROOT / "web" / "src" / "types.ts").read_text(encoding="utf-8")
SHELF = (ROOT / "web" / "src" / "components"
         / "Shortlist.tsx").read_text(encoding="utf-8")
RANK = (ROOT / "workflows" / "job-rank.md").read_text(encoding="utf-8")


def flat(s: str) -> str:
    s = " ".join(re.sub(r"^\s*(?:>|#:?)\s?", "", s, flags=re.M).split())
    return re.sub(r"(?<=[一-鿿，。；：、（）「」])"
                  r" +(?=[一-鿿，。；：、（）「」])", "", s)


class TheDateBelongsToItsOwnDecision(unittest.TestCase):
    """`_decision_date`：叠加层那一个 `date` 只归它自己那条路。"""

    def test_a_skip_row_gives_the_skip_date(self):
        self.assertEqual(
            ex._decision_date({"decision": "skipped", "date": "2026-08-19"},
                              "skipped", None), "2026-08-19")

    def test_a_skip_row_gives_nothing_to_the_expired_line(self):
        """**这就是当场踩的那个。** 标了不投的岗不该报出一个「下线日期」。"""
        self.assertIsNone(
            ex._decision_date({"decision": "skipped", "date": "2026-08-19"},
                              "expired", None))

    def test_an_expired_row_gives_nothing_to_the_skip_line(self):
        self.assertIsNone(
            ex._decision_date({"decision": "expired", "date": "2026-08-19"},
                              "skipped", None))

    def test_the_library_key_still_comes_through(self):
        """命令行 `/job-rank --skip` 写的是库里那个键，没有叠加层这一行。"""
        self.assertEqual(ex._decision_date(None, "skipped", "2026-08-11"),
                         "2026-08-11")
        self.assertEqual(ex._decision_date({}, "skipped", "2026-08-11"),
                         "2026-08-11")

    def test_the_overlay_wins_over_the_library(self):
        self.assertEqual(
            ex._decision_date({"decision": "skipped", "date": "2026-08-19"},
                              "skipped", "2026-08-11"), "2026-08-19")

    def test_a_row_with_no_date_falls_back_not_crashes(self):
        self.assertEqual(
            ex._decision_date({"decision": "skipped"}, "skipped", "2026-08-11"),
            "2026-08-11")
        self.assertIsNone(ex._decision_date({"decision": "skipped"}, "skipped", None))

    def test_nothing_anywhere_is_none_not_empty_string(self):
        """空串会让 `if job.skipDate` 那一支变成假，但键还在 —— 不如不给。"""
        self.assertIsNone(ex._decision_date(None, "skipped", ""))

    def test_the_reason_is_recorded(self):
        doc = flat(ex._decision_date.__doc__ or "")
        self.assertIn("叠加层一行上只有一个 `date`", doc.replace("**", ""))
        self.assertIn("挡得住不等于算得对", doc)
        self.assertIn("2026-08-25", doc)


class BothLinesGoThroughIt(unittest.TestCase):

    def test_the_skip_line_uses_the_judge(self):
        self.assertIn('"skipDate": _decision_date(ustate.get(k), "skipped"', EX)

    def test_the_expired_line_uses_it_too(self):
        """**两边都要过它。** 只改一边等于把不对称换了个位置。"""
        self.assertIn('"expiredDate": _decision_date(ustate.get(k), "expired"', EX)

    def test_neither_reads_the_overlay_date_raw_any_more(self):
        i = EX.index('"expiredDate"')
        seg = EX[i:i + 900]
        self.assertNotIn('ustate.get(k, {}).get("date")', seg,
                         "还有一处在裸读叠加层的 date —— 它分不出这一行是哪个决定")


class TheTypeAndTheScreenAgree(unittest.TestCase):

    def test_the_type_exists(self):
        self.assertIn("skipDate?: string;", TYPES)

    def test_it_sits_next_to_the_reason(self):
        i = TYPES.index("skipDate?: string;")
        self.assertIn("skipReason?: string;", TYPES[max(0, i - 700):i])

    def test_the_type_says_why_it_matters(self):
        i = TYPES.index("skipDate?: string;")
        seg = flat(TYPES[max(0, i - 700):i])
        self.assertIn("第一周否掉的和上周否掉的不是一回事", seg)

    def test_the_shelf_prints_it(self):
        self.assertIn("job.skipDate ? `（${job.skipDate} 标的）`", SHELF)

    def test_it_reads_the_same_way_as_the_expired_one(self):
        """两条路的措辞要一致 —— 一个说「标的」另一个说别的，读的人以为是两件事。"""
        i = SHELF.index("job.expiredDate ?")
        j = SHELF.index("job.skipDate ?")
        for k in (i, j):
            with self.subTest(at=k):
                self.assertIn("标的）", SHELF[k:k + 90])

    def test_the_reason_still_comes_first(self):
        """日期是补充，理由才是他要看的那句 —— 顺序不能倒。"""
        i = SHELF.index("job.skipDate ?")
        seg = SHELF[max(0, i - 200):i]
        self.assertIn('job.skipReason || "你排除的"', seg)


class TheSignalItLeansOnIsReal(unittest.TestCase):
    """现算：这批日期真的在盘上，而且真的分得开。"""

    def _data(self):
        p = ROOT / "web" / "public" / "data.json"
        if not p.is_file():
            self.skipTest("还没导出过面板数据")
        return json.loads(p.read_text(encoding="utf-8"))

    def test_most_skipped_jobs_now_carry_a_date(self):
        d = self._data()
        sk = [j for j in d["jobs"] if j.get("skipped")]
        if len(sk) < 10:
            self.skipTest("标不投的太少，说不出比例")
        got = sum(1 for j in sk if j.get("skipDate"))
        self.assertGreater(
            got, len(sk) * 0.8,
            f"{len(sk)} 个不投的岗只有 {got} 个带日期 —— 这条链路又断了")

    def test_no_date_leaks_across_the_two_paths(self):
        """**支点。** 标了不投的不该有下线日期，反过来也一样。"""
        d = self._data()
        bad = [j["id"] for j in d["jobs"]
               if j.get("skipDate") and j.get("expired") and not j.get("skipped")]
        self.assertEqual(bad[:5], [], f"{len(bad)} 个已下线的岗报出了「不投日期」")

    def test_the_dates_are_actually_spread_out(self):
        """全是同一天的话，「什么时候标的」这句话没有信息量。"""
        d = self._data()
        days = {j.get("skipDate") for j in d["jobs"] if j.get("skipDate")}
        if len(days) < 2:
            self.skipTest("这些不投都是同一天标的")
        self.assertGreaterEqual(len(days), 3, f"只有 {len(days)} 个不同的日期")


class TheAuditCatchesAMisfiledDate(unittest.TestCase):
    """写岔了键不会有任何一处报错 —— 所以要有人查。"""

    def _fn(self):
        return ap.check_out_records_carry_their_own_date

    def test_it_is_registered(self):
        self.assertIn(self._fn(), [f for _n, f in ap.CHECKS])

    def _run(self, seen):
        old = list(ap._USER)
        try:
            ap._USER[:] = ["someone"]
            return self._fn()(seen, {})
        finally:
            ap._USER[:] = old

    def test_a_clean_library_says_nothing(self):
        self.assertEqual(self._run({
            "a": {"status": "skipped", "skip_date": "2026-08-11"},
            "b": {"status": "expired", "expired_date": "2026-08-12"},
            "c": {"status": "ranked"},
        }), [])

    def test_a_skip_filed_under_expired_is_caught(self):
        got = self._run({"a": {"status": "skipped", "expired_date": "2026-08-13",
                               "title": "某岗"}})
        self.assertEqual(len(got), 1)
        self.assertIn("记在了另一条路的键上", got[0][2])

    def test_the_mirror_case_is_caught_too(self):
        got = self._run({"a": {"status": "expired", "skip_date": "2026-08-13",
                               "title": "某岗"}})
        self.assertEqual(len(got), 1)
        self.assertIn("记在了另一条路的键上", got[0][2])

    def test_no_date_at_all_is_a_different_line(self):
        got = self._run({"a": {"status": "skipped", "title": "某岗"}})
        self.assertEqual(len(got), 1)
        self.assertIn("两条都没记", got[0][2])
        self.assertNotIn("记在了另一条路的键上", got[0][2])

    def test_a_live_job_is_never_scolded(self):
        self.assertEqual(self._run({"a": {"status": "new"},
                                    "b": {"status": "ranked"}}), [])

    def test_no_active_user_is_silent(self):
        old = list(ap._USER)
        try:
            ap._USER[:] = []
            self.assertEqual(self._fn()({"a": {"status": "skipped"}}, {}), [])
        finally:
            ap._USER[:] = old

    def test_it_says_which_command_fixes_it(self):
        """`AGENTS.md`「每一处引导都要写出该敲的命令」——这一处是页面动作，
        所以点名的是页面上那个入口，不是一条编出来的命令。"""
        msg = self._run({"a": {"status": "skipped", "expired_date": "2026-08-13"}})[0][2]
        self.assertIn("在总览页「不投的岗位」里把这个岗放回来，再重标一次", msg)

    def test_a_misfiled_date_is_not_blamed_for_early_burial(self):
        """**这条原来钉的是一句错话。**

        它喂一个错键的条目，然后断言消息说「提前埋掉」「宁可少归一轮，不可早埋」。
        可 `archive._age_days` 取的是 `[叠加层 date, skip_date, expired_date,
        rank_date, first_seen]` 里**最晚**的一个 —— 记在另一条键上照样被读到，
        归档一点不受影响（实测那条真记录算出 13 天，门槛 30 天）。

        守卫钉着错的东西，就等于把错固定下来：改对了反而红。
        判据见 `test_a_misfiled_date_is_still_a_date.py`，那边直接跑 `_age_days`。
        """
        msg = self._run({"a": {"status": "skipped", "expired_date": "2026-08-13"}})[0][2]
        self.assertIn("归档不受影响", msg)
        self.assertIn("不显示日期", msg, "没说出错键真正的代价")

    def test_a_missing_date_is_the_one_that_gets_buried_early(self):
        """两条都没记才会退 —— 退到 `max(rank_date, first_seen)`，通常是评分那天。"""
        msg = self._run({"a": {"status": "skipped"}})[0][2]
        self.assertIn("提前埋掉", msg)
        self.assertIn("算老", msg)

    def test_that_archive_bias_really_is_written_down(self):
        src = (ROOT / "tools" / "archive.py").read_text(encoding="utf-8")
        self.assertIn("宁可少归一轮，不可早埋", src)

    def test_the_two_keys_it_names_are_the_ones_the_workflow_writes(self):
        self.assertIn('"skip_date": "YYYY-MM-DD"', RANK)
        self.assertIn('"expired_date": "YYYY-MM-DD"', RANK)


class BothWaysOutAlsoShowWhy(unittest.TestCase):
    """上面那半是「什么时候」，这一半是「为什么」—— 同一个不对称的另一侧。

    `skipReason` 2026-08-25 就补上了（那条注释自己写着「数据在盘上、断在最后
    一层」）。**镜像那一半一直开着**：执行者标下线时写的 `expired_reason`
    从来没被导出过。

    实测活动用户 2026-08-31：28 个已下线的岗里 **15 个带原因**，日期跨
    2026-08-10 到 08-27 —— 是现行做法，不是历史残留。内容分两类：

        页面确认：「页面顶部写着该职位已暂停招聘」「详情页 404」        6 条
        推　　断：「浏览器打开跳到职位聚合页，岗位已不在」            5 条

    搁置区那句「已下线没什么可回看的」对前一类成立，**对后一类不成立** ——
    那 5 条正是可能标错的，而「放回」按钮的提示语问的就是「职位其实还在？」。
    用户此前没有任何依据回答它。

    ## 只进悬浮提示

    原因是整句话，摆进可见标签会撑爆版式。所以 `Shortlist` 里把可见的 `why`
    和悬浮的 `tip` 分开 —— 这条守卫钉的正是这个分工，两个方向都要成立。
    """

    def test_the_export_carries_the_reason(self):
        self.assertIn('"expiredReason"', EX,
                      "导出器还是没把下线原因带出来")
        i = EX.index('"expiredReason"')
        self.assertIn("expired_reason", EX[max(0, i - 400):i + 200],
                      "`expiredReason` 不是从库里那个字段来的")

    def test_it_is_stripped_like_every_other_display_string(self):
        """和别处一样先剥 markdown —— 面板上那些字进的是纯文本节点。"""
        i = EX.index('"expiredReason"')
        self.assertIn("plain(", EX[i:i + 120],
                      "没走 `plain()`，`**` 会原样显示在悬浮提示里")

    def test_the_type_declares_it(self):
        self.assertIn("expiredReason?: string;", TYPES,
                      "types.ts 没声明它 —— 面板读不到")

    def test_the_tooltip_shows_it_and_the_label_does_not(self):
        """**分工要两个方向都成立**：提示里有、可见标签里没有。

        只验前一半的话，把原因塞进 `why` 也能绿 —— 而那正是这条要防的
        （整句话摆进行里撑爆版式）。
        """
        sl = (ROOT / "web" / "src" / "components"
              / "Shortlist.tsx").read_text(encoding="utf-8")
        self.assertIn("job.expiredReason", sl, "面板没读这个字段")
        self.assertIn("<Tooltip title={tip}>", sl, "悬浮提示没换成 `tip`")
        # 可见那一处仍然渲染 `why`
        self.assertIn('className="shelf-why">{why}', sl,
                      "可见标签不再是 `why` —— 原因八成被塞进行里了")
        # `why` 的定义里不许出现原因
        i = sl.index("const why = gone")
        j = sl.index("const tip =", i)
        self.assertNotIn("expiredReason", sl[i:j],
                         "原因被塞进了可见标签 `why`")

    def test_the_reason_for_splitting_is_recorded(self):
        """为什么不直接塞进 `why` —— 不写下来，下一个人会「顺手合并」。"""
        sl = (ROOT / "web" / "src" / "components"
              / "Shortlist.tsx").read_text(encoding="utf-8")
        i = sl.index("<Tooltip title={tip}>")
        seg = " ".join(sl[max(0, i - 400):i].split())
        self.assertRegex(seg, r"撑爆版式|整句话",
                         "没说清为什么原因不进可见标签")


class EveryPlaceThatMarksExpiredSaysWhatToRecord(unittest.TestCase):
    """**标已下线的地方不止一处**，两个字段的契约得在每一处都够得着。

    `expired_date` 的契约 2026-08-25 补在 `job-rank.md`，而 `job-apply.md`
    第 0 步那张「浏览器打开之后按看到的东西分流」的表**同样在让执行者标已下线**
    —— 它一个字段都没提。2026-08-31 给 `expired_reason` 补契约时才发现：
    新字段照着旧字段的位置放，就把旧字段那一半的缺口一起继承了。

    `job-rank.md` 自己的注释写的正是这件事：**「一条规则贴在一个写手身上，
    另一个照样会犯」**。

    ## 判据：写出来**或**引到正本，两者都行

    这个仓库两种做法都在用（`test_shared_thresholds_agree` 守的是「复述了就
    必须一致」，`EveryJdReaderRestatesTheTrustBoundary` 守的是「必须提一句」）。
    这里只要求**够得着**：要么把字段名写出来，要么引到那一段。

    ⚠️ **名单是派生的**：凡是文本里出现「标已下线」或 `"status": "expired"`
    的工作流都算 —— 手写名单只盖得住已经想到的那几个，而这条规则的历史正是
    「想到了一个、漏了另一个」。
    """

    #: 两个字段名，缺一不可。
    FIELDS = ("expired_date", "expired_reason")

    @staticmethod
    def _markers():
        import re as _re

        out = []
        for f in sorted((ROOT / "workflows").rglob("*.md")):
            t = f.read_text(encoding="utf-8")
            if _re.search(r"标\*?\*?已下线|置为 `?expired|\"status\": \"expired\"", t):
                out.append((f.relative_to(ROOT / "workflows").as_posix(), t))
        return out

    def test_the_scan_finds_them(self):
        """先证明它会亮 —— 一份都扫不到时，下面那条会在空集上永远绿。"""
        got = self._markers()
        self.assertGreaterEqual(len(got), 2,
                                f"只扫到 {len(got)} 份让标已下线的工作流，判据坏了")

    def test_each_one_can_reach_the_contract(self):
        bad = []
        for name, t in self._markers():
            missing = [k for k in self.FIELDS if k not in t]
            if not missing:
                continue
            # 引到正本也算够得着 —— **但引用必须挨着那条指令**。
            #
            # 第一版写的是「文件里出现过 `job-rank.md` 就放行」，而
            # `job-apply.md` 别处本来就引它好几次，于是**加不加那段说明都绿**。
            # 变异当场照出来：撤掉刚补的引用，这条一声不响。
            # 例外条款放宽一格，守卫就整条失效 —— 这正是本文件在别处盯的那个形状。
            near = False
            for m in re.finditer(r"标\*?\*?已下线|置为 `?expired", t):
                if "job-rank.md" in t[max(0, m.start() - 900):m.start() + 900]:
                    near = True
                    break
            if near:
                continue
            bad.append(f"{name}：没提 {missing}，"
                       "那条指令附近也没引到 job-rank.md 那一段")
        self.assertEqual(
            bad, [],
            "这些地方让执行者标已下线，却没说要记什么 —— "
            "执行者只能自己发明字段名，下游读不到：" + repr(bad))


if __name__ == "__main__":
    unittest.main()
