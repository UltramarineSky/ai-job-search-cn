# -*- coding: utf-8 -*-
"""「其中 15 个排了两周以上，从它们开始」—— 而名单上认不出是哪 15 个。

那句话一直在印，用的是 `counts["ready_old"]`：材料备好、还没投、而且
`first_seen` 超过 `STALE_POSTING_DAYS` 的岗数。

**这个数一直只作为一个计数出去。** 逐岗的值被挡在 `_first_seen` 那个局部字典里，
理由写着「职位字典里没有这个字段（面板不显示它），不必为一个计数多带一列出去」
—— 而那句话已经变成循环：面板不显示是因为没导出，没导出是因为面板不显示。

实测活动用户 2026-08-25：

    材料就绪、还没投            60 个
    其中排了两周以上            15 个（15 / 26 / 27 / 32 天）
    这 15 个落在首屏那 6 行里    **0 个** —— 全在折叠起来的「可以考虑」那一档

也就是说：面板一边说「从它们开始」，一边按分数排给他看，**没有任何一处标出
是哪几个**。照那句话做，他得逐个点开 60 次 —— 而点开也看不到，这个数没上过屏。

## 两个「天数」不是一回事

    staleDays    抓到它那天，招聘方上一次刷新在多久以前（只有猎聘给，覆盖约 10%）
    queuedDays   它进库到今天多少天（`first_seen`，100% 有）

前者说的是**招聘方没动**，后者说的是**你没发**。两个都可能出现在同一行上，
所以小标换了颜色 —— 同色就读成一件事了。

## 只标少数派

判据抄 `staleDays` 那条的：「『排了 3 天』是噪音，『排了 26 天』才是要人改主意
的信息」。也只给「材料备好、还没投」的岗 —— 别的岗排多久都不构成一个动作。
"""
import json
import pathlib
import re
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import _cli  # noqa: E402
import build_dashboard as bd  # noqa: E402
import export_web_data as ex  # noqa: E402

EX = (ROOT / "tools" / "export_web_data.py").read_text(encoding="utf-8")
BD = (ROOT / "tools" / "build_dashboard.py").read_text(encoding="utf-8")
TYPES = (ROOT / "web" / "src" / "types.ts").read_text(encoding="utf-8")
LIST = (ROOT / "web" / "src" / "components"
        / "Shortlist.tsx").read_text(encoding="utf-8")
CSS = (ROOT / "web" / "src" / "theme" / "cockpit.css").read_text(encoding="utf-8")


def flat(s: str) -> str:
    s = " ".join(re.sub(r"^\s*(?:>|#:?|//:?)\s?", "", s, flags=re.M).split())
    return re.sub(r"(?<=[一-鿿，。；：、（）「」])"
                  r" +(?=[一-鿿，。；：、（）「」])", "", s)


class TheNumberReachesEachJob(unittest.TestCase):
    def test_the_field_is_filled_where_funnels_are_known(self):
        """判据要看 `funnels`，而它是字典建好之后才算的。

        **钉行，不钉窗口。** 中间那段说明会长，窗口一切就断（这一轮实测被
        自己的注释撑破过一次）。
        """
        self.assertIn('j["funnels"] = funnels_of(j)', EX)
        self.assertIn('j["queuedDays"] = _q', EX)
        self.assertLess(EX.index('j["funnels"] = funnels_of(j)'),
                        EX.index('j["queuedDays"] = _q'))

    def test_the_placeholder_keeps_the_key_stable(self):
        """有的岗有这个键、有的没有，前端就得两套写法。"""
        self.assertIn('"queuedDays": None,', EX)

    def test_only_ready_and_unsent_get_it(self):
        """那个 `if` 是**紧挨着算天数那一行**的，钉它本身。"""
        lines = EX.splitlines()
        i = next(n for n, l in enumerate(lines) if "_q = _days_since(" in l)
        guard = lines[i - 1]
        self.assertIn('"materials" in j["funnels"]', guard)
        self.assertIn('"applied" not in j["funnels"]', guard)

    def test_the_threshold_decides_the_flag_not_the_number(self):
        """**天数全给，「够不够久」单独标。**

        2026-08-25 改的：原来只在超阈值时才填 `queuedDays`，等于把判据烧进数据
        —— `doctor.ready_age` 因此拿不到原始天数，退去读了 `staleDays`，
        报出一个和面板差 5 个的数。
        """
        line = next(l for l in EX.splitlines() if 'j["queuedLong"] = _q' in l)
        self.assertIn("_q > STALE_POSTING_DAYS", line)
        self.assertNotIn("STALE_POSTING_DAYS",
                         next(l for l in EX.splitlines()
                              if 'j["queuedDays"] = _q' in l))

    def test_it_uses_the_same_clock_as_the_count(self):
        """逐岗那个数和顶上那句 `ready_old` 必须同源，否则一屏两个数。

        **判的是那一行本身，不是它附近。** 一个 300 字的窗口里，
        `_first_seen_all` 会从注释里绿过去 —— 变异实测：把那行换成一个
        就地展开的字典推导，这条照样绿。
        """
        line = next(l for l in EX.splitlines() if "_q = _days_since(" in l)
        self.assertIn("_first_seen_all.get(", line)
        # 顶上那个计数读的必须是同一份
        self.assertIn('_days_since(_first_seen_all.get(j.get("url")) or "")', EX)

    def test_the_reason_is_recorded(self):
        i = EX.index('"queuedDays": None,')
        seg = flat(EX[max(0, i - 1800):i])
        self.assertRegex(seg, r"\*\*它在你手上排了多久。\*\*")
        self.assertRegex(seg, r"那句话已经变成循环：面板不显示是因为\s*没导出，"
                              r"没导出是因为面板不显示")
        self.assertIn("2026-08-25", seg)

    def test_it_distinguishes_the_two_day_counts(self):
        """两个「天数」混起来是这一条最容易出的错。"""
        i = EX.index('"queuedDays": None,')
        seg = flat(EX[max(0, i - 1800):i])
        self.assertRegex(seg, r"和上面那个 `staleDays` 不是一回事")
        self.assertRegex(seg, r"只有猎聘给，\s*实测覆盖约 10%")

    def test_the_old_excuse_is_gone(self):
        """那句「面板不显示它，不必多带一列」不许再作为一条生效的理由。"""
        self.assertEqual(EX.count("不必为一个计数多带一列出去"), 1)
        i = EX.index("不必为一个计数多带一列出去")
        self.assertIn("已经变成循环", EX[i:i + 200])


class TheFlagCarriesTheJudgement(unittest.TestCase):
    """天数全给、「够不够久」单独标 —— 判据只有一份，在 Python 那边。"""

    def test_the_placeholder_carries_both_keys(self):
        self.assertIn('"queuedDays": None, "queuedLong": False,', EX)

    def test_the_export_says_where_the_judgement_moved(self):
        i = EX.index('j["queuedLong"] = _q')
        seg = flat(EX[max(0, i - 1400):i])
        self.assertRegex(seg, r"\*\*原始天数全给，「够不够久」单独标一个。\*\*")
        self.assertRegex(seg, r"判据仍然只有一份，只是搬了个位置")

    def test_the_export_carries_that_measurement(self):
        i = EX.index('j["queuedLong"] = _q')
        seg = EX[max(0, i - 1400):i]
        self.assertIn("2026-08-25", seg)
        self.assertIn("只有 10 个有", seg)

    def test_the_type_exists(self):
        self.assertIn("queuedLong?: boolean;", TYPES)

    def test_the_type_says_why_the_number_is_not_gated(self):
        i = TYPES.index("queuedLong?: boolean;")
        seg = flat(TYPES[max(0, i - 800):i])
        # `flat()` 剥不掉 TS 块注释的 `*` 前缀，跨行的短语别一次断言完
        self.assertRegex(seg, r"那样等于把判据烧进数据")
        self.assertIn("`doctor.ready_age` 当初", seg)
        self.assertIn("就是这么退去读了 `staleDays`", seg)

    def test_doctor_says_which_day_count_it_reads(self):
        dr = (ROOT / "tools" / "doctor.py").read_text(encoding="utf-8")
        i = dr.index('ages = sorted(j["queuedDays"]')
        seg = flat(dr[max(0, i - 1400):i])
        self.assertRegex(seg, r"\*\*读 `queuedDays`，不是 `staleDays`。\*\*")
        self.assertRegex(seg, r"「其中 10 份排了\s*两周以上」实际等于「有这个字段的有 10 个」")


class TheListMarksThem(unittest.TestCase):
    def test_the_type_exists(self):
        self.assertIn("queuedDays?: number | null;", TYPES)

    def test_the_type_says_it_is_not_staleDays(self):
        i = TYPES.index("queuedDays?: number | null;")
        seg = flat(TYPES[max(0, i - 1100):i])
        self.assertRegex(seg, r"和 `staleDays` 不是一回事")
        self.assertRegex(seg, r"标记要标少数派")
        # 那批 100% 都有 —— 说清这一点，下一个人才不会又把判据烧进数据
        self.assertIn("那批 100% 都有", seg)

    def test_the_chip_renders(self):
        self.assertIn("{job.queuedLong && job.queuedDays != null && (", LIST)
        self.assertIn('className="queued-chip"', LIST)

    def test_the_chip_reads_the_flag_not_a_local_threshold(self):
        """阈值只许有一份，在 Python 那边（同 `Gate.offSpec` 的做法）。"""
        i = LIST.index('className="queued-chip"')
        seg = LIST[max(0, i - 900):i + 400]
        self.assertIn("job.queuedLong", seg)
        self.assertNotIn("> 14", seg)

    def test_the_chip_says_the_number(self):
        i = LIST.index('className="queued-chip"')
        self.assertIn("排了 {job.queuedDays} 天没发", LIST[i:i + 200])

    def test_it_sits_next_to_the_other_chip(self):
        """两个都可能出现在同一行 —— 挨着才看得出是两件事。"""
        a = LIST.index('className="queued-chip"')
        b = LIST.index('className="stale-chip"')
        self.assertLess(abs(a - b), 1600)

    def test_the_tooltip_says_why_it_matters(self):
        i = LIST.index("job.queuedDays != null")
        seg = LIST[i:i + 700]
        self.assertIn("分数不会因为放久了变低", seg)
        self.assertIn("在发出去之前就下线", seg)

    def test_the_comment_says_why_the_chip_is_needed(self):
        i = LIST.index("顶上那句「从它们开始」指的就是这几个")
        seg = flat(LIST[i:i + 700])
        self.assertRegex(seg, r"名单按分数排、没有任何东西标出是哪几个")
        self.assertRegex(seg, r"那个是招聘方多久没动这个岗，\s*这个是\*\*你压了它多久\*\*")

    def test_the_style_exists_and_differs(self):
        self.assertIn(".queued-chip {", CSS)
        i = CSS.index(".queued-chip {")
        self.assertIn("var(--caution)", CSS[i:CSS.index("}", i)])

    def test_the_style_says_why_a_different_colour(self):
        i = CSS.index(".queued-chip {")
        seg = flat(CSS[max(0, i - 400):i])
        self.assertRegex(seg, r"混成一个颜色就读成同一件事了")

    def test_the_style_does_not_stretch_chinese(self):
        i = CSS.index(".queued-chip {")
        self.assertNotIn("letter-spacing", CSS[i:CSS.index("}", i)])

    def test_the_other_chip_is_untouched(self):
        self.assertIn("抓到时已 {job.staleDays} 天没刷新", LIST)


class TheNudgeNamesTheMarker(unittest.TestCase):
    """「从它们开始」得说得出「哪几个」。

    ⚠️ **2026-08-30 起这句话在 `_ready_text._tail`，不在 `season_note`。**
    它原来两处各一份：当年面板走的是「零回音」那一支，到不了 `_ready_text`，
    所以季节那句里也补了一份。「零回音」那一支撤掉、`season_note` 接进
    ready 那一支之后，**两处同时触发**，用户那句「下一步」里同一件事说了两遍。
    合并时留下的是 `_ready_text` 那一份（`season_note` 说不出话时返回空串，
    而「先发排得最久的」跟季节无关）。完整的账在
    `test_the_oldest_in_the_queue_go_first.TheClauseHasOneHome`。
    """

    def _seg(self) -> str:
        """只切 `_tail()` 那个函数体 —— 拿全文去断言会从别处绿过去。"""
        i = BD.index("    def _tail() -> str:")
        return BD[i:BD.index("    def _join(", i)]

    def test_it_says_what_to_look_for(self):
        self.assertRegex(flat(self._seg()), r"名单上标着「排了 N 天没发」的就是")

    def test_the_marker_it_names_really_exists(self):
        """指一个不存在的标记，比不指更坏。"""
        self.assertIn("排了 {job.queuedDays} 天没发", LIST)

    def test_it_does_not_name_a_tier(self):
        """那 15 个落在哪一档随数据变 —— 写死档名就是等它过期。"""
        # **只看这一句，不看它前面那半段。** 原来按 `return (f"` 切源码 ——
        # 2026-09-01 那个函数改成攒句子，锚点不在了，守卫报 substring not
        # found（不是断言失败，是抽取器坏了）。
        #
        # ⚠️ 改成现算之后**第一版把整句都收了进来**，当场红在「可以考虑」
        # 和「值得投」上 —— 而那两个词是**前半句**该说的（判词分档回答
        # 「该不该发」）。这一条管的只有后半句（岗龄回答「先发哪个」）。
        # 拿「有它」减「没它」把那一句单独摘出来。
        out = (bd._ready_text(62, 30, 13)
               .replace(bd._ready_text(62, 30, 0), ""))
        self.assertIn("两周以上", out, "抽取器没拿到那句话")
        for t in ("可以考虑", "值得投", "强匹配"):
            with self.subTest(t=t):
                self.assertNotIn(t, out)

    def test_the_reason_is_recorded(self):
        seg = flat(self._seg())
        self.assertRegex(seg, r"那 15 个一个都不在首屏那 6 行里")
        self.assertRegex(seg, r"\*\*不说是哪一档\*\*")

    def test_the_original_half_survives(self):
        """「分数没变，是它们还剩的时间少了」是这句最值钱的一半。"""
        self.assertIn("分数没变，是它们还剩的时间少了", self._seg())

    def test_there_is_no_sibling_any_more(self):
        """**上一版这条钉的是「必须有两份」。**

        原话：「`_ready_text` 那一处说的是同一件事的另一个入口，别被这次改动
        带掉」，断言 `BD.count(...) == 2`。它数的是源码里的份数，而两处会不会
        同时触发取决于分支 —— 分支一合并，这条照样绿，而屏幕上开始说两遍。
        """
        made = [ln for ln in BD.splitlines()
                if "分数没变，是它们还剩的时间少了" in ln and 'f"' in ln]
        self.assertEqual(len(made), 1)

    def test_it_disappears_when_there_are_none(self):
        """**钉行为，不钉那一行长什么样。**

        原来断言源码里有 `if not old_n:`。2026-09-01 那个函数改成攒句子
        （多了一句「已经白做了几个」，见 `_tail`），守卫当场红 —— 而行为
        一点没变。这个仓库为这一脚立过规矩：判据钉行为，不钉实现位置。
        """
        self.assertNotIn("两周以上", bd._ready_text(62, 30, 0))
        self.assertIn("两周以上", bd._ready_text(62, 30, 13))


class TheSignalItLeansOnIsReal(unittest.TestCase):
    """现算：那批真的存在，而且逐岗那个数和顶上那句对得上。"""

    def _data(self):
        p = ROOT / "web" / "public" / "data.json"
        if not p.is_file():
            self.skipTest("还没导出过面板数据")
        return json.loads(p.read_text(encoding="utf-8"))

    def test_some_jobs_carry_it(self):
        d = self._data()
        n = sum(1 for j in d["jobs"] if j.get("queuedLong"))
        if not n:
            self.skipTest("没有排超过两周的 —— 好事")
        self.assertGreater(n, 0)

    def test_the_per_job_count_matches_the_headline(self):
        """**一屏两个数是这个仓库最贵的一类。** 现算对账。"""
        d = self._data()
        n = sum(1 for j in d["jobs"] if j.get("queuedLong"))
        t = str((d.get("nextStep") or {}).get("text") or "")
        m = re.search(r"其中 (\d+) 个排了两周以上", t)
        if not m:
            self.skipTest("这一轮没印那句话")
        self.assertEqual(int(m.group(1)), n, "顶上那个数和名单上标出来的对不上")

    def test_every_marked_job_is_ready_and_unsent(self):
        d = self._data()
        bad = [j["id"] for j in d["jobs"] if j.get("queuedLong")
               and ("materials" not in (j.get("funnels") or [])
                    or "applied" in (j.get("funnels") or []))]
        self.assertEqual(bad, [], f"{len(bad)} 个标错了")

    def test_the_flag_matches_the_threshold(self):
        """现算：每个标了 `queuedLong` 的都真的超了阈值，反之亦然。"""
        d = self._data()
        bad = [j["id"] for j in d["jobs"]
               if isinstance(j.get("queuedDays"), int)
               and bool(j.get("queuedLong")) != (j["queuedDays"] > ex.STALE_POSTING_DAYS)]
        self.assertEqual(bad, [], f"{len(bad)} 个标志和天数对不上")

    def test_the_raw_number_covers_everyone(self):
        """**doctor 要拿它算中位数。** 只给少数派，它就只能另找字段。"""
        d = self._data()
        live = [j for j in d["jobs"]
                if "materials" in (j.get("funnels") or [])
                and "applied" not in (j.get("funnels") or [])]
        if not live:
            self.skipTest("没有备好没发的岗")
        got = sum(1 for j in live if isinstance(j.get("queuedDays"), int))
        self.assertEqual(got, len(live), f"只有 {got}/{len(live)} 个带天数")

    def test_they_were_invisible_before(self):
        """**支点。** 它们要是本来就在首屏，这一条就没有由头。

        哪天首屏里也有了（他把老的发掉、或分档变了），这条会 skip ——
        那时上面那段实测要跟着更新。
        """
        d = self._data()
        marked = [j for j in d["jobs"] if j.get("queuedLong")]
        if not marked:
            self.skipTest("没有排超过两周的")
        strong = [j for j in marked
                  if str(j.get("verdict") or "") in ("值得投", "强匹配")]
        if strong:
            self.skipTest(f"其中 {len(strong)} 个在首屏那一档里 —— 那时它更好找")
        self.assertEqual(strong, [])


if __name__ == "__main__":
    unittest.main()
