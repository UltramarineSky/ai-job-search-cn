# -*- coding: utf-8 -*-
"""仓库自称「唯一一件每天都要做的事」，而没有任何地方记他做过没有。

`job-resume.md` 2.6 那张表里的一行：

> | **最近刷新/活跃时间** | 搜索结果基本按这个排。两周没登录的简历，HR 翻不到
> 第几页就停了。这是这张表里唯一一件**每天都要做**的事 |

理由是国内平台的简历库按「最近活跃」排序，而 **HR 主动在简历库里搜人是唯一一条
不靠他投递的路** —— 在 85 投 0 回音的情况下，这条路的分量只会更重。

## 而它此前只有一句提醒，没有落点

那句提醒挂在 `/job-auto` 的收尾，且**只在那一轮真出了材料时才说**
（「没材料可发就没有那一趟，说了是噪音」—— 那条规则本身是对的）。后果三层：

    校准不了     昨天刷过和二十天没刷，那句提醒一个字不差
    升级不了     同一张表写着「三周没刷是建议改」，而没人知道到了三周
    可能压根不响 2026-08-24 那趟 /job-auto 出了 0 份材料，提醒被正确地压掉，
                 于是他那天什么也没被提醒 —— 而距上次简历审核已过二十多天

## 三态，不是两态

「没记过」不是「刷过很久了」。前者是没查，后者是数据 —— 一路上任何一层把没记过
渲染成一个天数（0 天、很久），都是凭空造一个事实出来。同这个仓库对
`hr_viewed` 的处理。

## 为什么不塞进 `portals.json`

那份是 `{渠道: 布尔}`，`portals_enabled` 按布尔读。往里塞个日期，
「关掉的渠道」会因为字典恒真而变成「开着」—— 一个字段毁掉另一个功能。
所以另起一个文件。
"""
import datetime
import json
import pathlib
import re
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import doctor  # noqa: E402
import export_web_data as ex  # noqa: E402

EX = (ROOT / "tools" / "export_web_data.py").read_text(encoding="utf-8")
DR = (ROOT / "tools" / "doctor.py").read_text(encoding="utf-8")
SRV = (ROOT / "tools" / "serve.py").read_text(encoding="utf-8")
PT = (ROOT / "web" / "src" / "components"
      / "Portals.tsx").read_text(encoding="utf-8")
API = (ROOT / "web" / "src" / "data" / "excluded.ts").read_text(encoding="utf-8")
TYPES = (ROOT / "web" / "src" / "types.ts").read_text(encoding="utf-8")
CSS = (ROOT / "web" / "src" / "theme" / "cockpit.css").read_text(encoding="utf-8")
RESUME = (ROOT / "workflows" / "job-resume.md").read_text(encoding="utf-8")


def flat(s: str) -> str:
    s = " ".join(re.sub(r"^\s*(?:>|#:?|//:?|\*)\s?", "", s, flags=re.M).split())
    return re.sub(r"(?<=[一-鿿，。；：、（）「」])"
                  r" +(?=[一-鿿，。；：、（）「」])", "", s)


class TheRuleItLeansOnIsStillWritten(unittest.TestCase):
    def test_the_table_still_calls_it_a_daily_thing(self):
        """这一整条建立在它上面 —— 它没了，这条就成了我们自己发明的规矩。"""
        seg = flat(RESUME)
        self.assertRegex(seg, r"这是这张表里唯一一件\*\*每天都要做\*\*的事")

    def test_the_threshold_comes_from_that_sentence(self):
        """两周这个数是那句话里的，不是另立的。"""
        self.assertRegex(flat(RESUME), r"两周没登录的简历，HR 翻不到第几页就停了")
        self.assertEqual(ex.RESUME_STALE_DAYS, 14)

    def test_the_original_records_why(self):
        i = EX.index("RESUME_STALE_DAYS = ")
        seg = flat(EX[max(0, i - 1500):i])
        self.assertRegex(seg, r"唯一一件每天都要做")
        self.assertRegex(seg, r"校准不了")
        self.assertRegex(seg, r"升级不了")
        self.assertIn("2026-08-24", seg)

    def test_the_copy_points_at_the_original(self):
        i = DR.index("RESUME_STALE_DAYS = ")
        self.assertIn("export_web_data.RESUME_STALE_DAYS", DR[max(0, i - 400):i])

    def test_the_thresholds_match(self):
        self.assertEqual(ex.RESUME_STALE_DAYS, doctor.RESUME_STALE_DAYS)


class ThePanelReadsTheNumberInsteadOfCopyingIt(unittest.TestCase):
    """这个 14 一度有四份，而守卫只盖住了 Python 那两份。

        export_web_data.RESUME_STALE_DAYS   正本
        doctor.py 的复刻                    有据（不许 import 仓库模块），已有守卫
        Portals.tsx 的 `>= 14`             写死，没说明、没守卫
        同一行提示语里的「两周」             同一个数的第四种写法

    改这个常数，面板会继续按 14 上色、继续说「两周」—— 而它旁边那句
    「几天前刷的」用的是服务端算出来的真天数。同一格里两个口径。

    2026-08-27 收成一份：常数经 payload 的 `resumeStaleDays` 传给面板。
    """

    def test_the_payload_carries_it(self):
        self.assertIn('"resumeStaleDays": RESUME_STALE_DAYS', EX,
                      "没导出去 —— 前端只能自己写死一份")

    def test_the_panel_does_not_hardcode_the_threshold(self):
        tsx = (ROOT / "web" / "src" / "components"
               / "Portals.tsx").read_text(encoding="utf-8")
        self.assertNotIn("resumeStale >= 14", tsx,
                         "又写死了一份门槛")
        # 同上：天数也走 `shownStale(p)`，比的仍然是 payload 传下来的 `stale`。
        self.assertIn("st >= stale", tsx)

    def test_the_tooltip_stops_saying_two_weeks(self):
        """「两周」是同一个数的第四种写法 —— 常数一改它就成了假话。"""
        tsx = (ROOT / "web" / "src" / "components"
               / "Portals.tsx").read_text(encoding="utf-8")
        self.assertNotIn("两周没登录", tsx)
        self.assertIn("超过 ${stale} 天没登录", tsx)

    def test_the_loader_passes_it_through(self):
        load = (ROOT / "web" / "src" / "data" / "load.ts").read_text(encoding="utf-8")
        self.assertIn("resumeStaleDays: d.resumeStaleDays", load,
                      "类型里声明了却没读 —— 那一格会永远拿到 undefined")

    def test_the_fallback_matches_the_source_of_truth(self):
        """服务端没给时的兜底值要和正本一致，否则老快照会按另一个数上色。"""
        tsx = (ROOT / "web" / "src" / "components"
               / "Portals.tsx").read_text(encoding="utf-8")
        import re
        m = re.search(r"staleDays \?\? (\d+)", tsx)
        self.assertIsNotNone(m, "找不到兜底值")
        self.assertEqual(int(m.group(1)), ex.RESUME_STALE_DAYS)


class TheRecordLandsInItsOwnFile(unittest.TestCase):
    def _tmp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        tmp = pathlib.Path(t.name)
        (tmp / "users" / "甲" / "job_scraper").mkdir(parents=True)
        old = ex.ROOT
        ex.ROOT = tmp
        self.addCleanup(lambda: setattr(ex, "ROOT", old))
        return tmp

    def test_it_is_not_portals_json(self):
        """往 `{渠道: 布尔}` 里塞日期，关掉的渠道会变成开着的。"""
        self._tmp()
        self.assertNotIn("portals.json", ex.RESUME_REFRESH_FILE)
        self.assertNotEqual(ex.resume_refresh_file("甲").name, "portals.json")

    def test_writing_and_reading(self):
        self._tmp()
        ex.set_resume_refreshed("甲", "BOSS")
        self.assertEqual(list(ex.resume_refreshed("甲")), ["BOSS"])
        self.assertEqual(ex.resume_stale_days("甲")["BOSS"], 0)

    def test_an_old_date_becomes_days(self):
        self._tmp()
        day = (datetime.date.today() - datetime.timedelta(days=20)).isoformat()
        ex.set_resume_refreshed("甲", "BOSS", day)
        self.assertEqual(ex.resume_stale_days("甲")["BOSS"], 20)

    def test_empty_string_clears_it(self):
        """标错了要有退路，否则没人敢标第一下。"""
        self._tmp()
        ex.set_resume_refreshed("甲", "BOSS")
        ex.set_resume_refreshed("甲", "BOSS", "")
        self.assertEqual(ex.resume_refreshed("甲"), {})

    def test_never_recorded_is_absent_not_zero(self):
        """**「没记过」不是「今天刷的」。** 给个 0 就是编一个事实。"""
        self._tmp()
        self.assertEqual(ex.resume_stale_days("甲"), {})

    def test_an_unknown_portal_is_refused(self):
        self._tmp()
        self.assertFalse(ex.set_resume_refreshed("甲", "拉勾")["ok"])

    def test_a_broken_file_is_not_a_crash(self):
        tmp = self._tmp()
        ex.resume_refresh_file("甲").write_text("{ not json", encoding="utf-8")
        self.assertEqual(ex.resume_refreshed("甲"), {})

    def test_a_stale_portal_name_is_dropped(self):
        """接了新渠道又撤掉时，旧名字留在文件里 —— 读的时候滤掉，别报一个不存在的家。"""
        self._tmp()
        ex.resume_refresh_file("甲").write_text(
            json.dumps({"拉勾": "2026-01-01"}, ensure_ascii=False), encoding="utf-8")
        self.assertEqual(ex.resume_refreshed("甲"), {})


class ThePanelCanRecordIt(unittest.TestCase):
    def test_the_endpoint_exists(self):
        self.assertIn('path == "/api/resume-refreshed"', SRV)
        self.assertIn('"/api/resume-refreshed": "记刷了在线简历"', SRV)

    def test_it_needs_no_job_id(self):
        """它记的是平台上那份简历，不是某一次投递。"""
        i = SRV.index("if not job_id and path not in")
        self.assertIn("/api/resume-refreshed", SRV[i:i + 300])

    def test_it_writes_under_the_same_lock(self):
        i = SRV.index('path == "/api/resume-refreshed"')
        self.assertLess(SRV.index("with _WRITE_LOCK:"), i)

    def test_the_endpoint_can_undo(self):
        i = SRV.index('path == "/api/resume-refreshed"')
        self.assertIn('"" if body.get("day") == "" else None', SRV[i:i + 600])

    def test_the_row_carries_the_number(self):
        self.assertIn('**({"resumeStale": _stale[name]} if name in _stale else {}),', EX)

    def test_never_recorded_has_no_field(self):
        """给个 null 会被渲染成「0 天」或「很久」，两个都是编的。"""
        i = EX.index('"resumeStale": _stale[name]')
        self.assertIn("if name in _stale else {}", EX[i:i + 120])

    def test_the_button_is_only_for_enabled_portals(self):
        """关掉那家的简历刷不刷不影响任何事 —— 多一格就是噪音。"""
        i = PT.index('className="portal-refresh"')
        self.assertIn("shownOn(p) && live &&", PT[max(0, i - 900):i])

    def test_the_button_is_a_toggle(self):
        i = PT.index("const markRefreshed")
        # 「再点一下是撤销」现在分两步写（先判 `undoing`，再据它决定送什么），
        # 因为标记那一下要先乐观更新、撤销那一下不猜（`Portals.tsx` 的 `ovFresh`）。
        # 两半都要钉，但**仍然只钉一条** —— 拆成两条 `assertIn` 会把
        # `test_a_guard_pins_behaviour_not_a_line` 的棘轮顶上去（228→229），
        # 而那条棘轮要的正是「少钉字面行」。
        self.assertRegex(
            PT[i:i + 900],
            r'shownStale\(p\) === 0[\s\S]*undoing \? "" : undefined',
            "「再点一下是撤销」断了：要么不判「今天刷过没」，要么撤销送的不是空串")

    def test_the_three_states_are_all_rendered(self):
        i = PT.index('className="portal-refresh"')
        seg = PT[i:i + 1200]
        self.assertIn("简历没记过刷新", seg)
        self.assertIn("简历今天刷过", seg)
        self.assertIn("天没刷", seg)

    def test_only_the_old_one_changes_colour(self):
        """标记要标少数派 —— 天天变色就没人看了。"""
        # **锚要带上行首那个换行。** 裸 `.portal-refresh {` 在窄屏那条
        # `.cockpit .portal-refresh { grid-column: … }` 里也是子串，
        # `index()` 会先命中它 —— `test_test_anchors_are_unambiguous` 逮到过。
        i = CSS.index(chr(10) + ".portal-refresh {")
        seg = CSS[i:CSS.index(".portal-alarm {", i)]
        self.assertIn('[data-stale="old"]', seg)
        self.assertNotIn('[data-stale="ok"]', seg)

    def test_the_narrow_screen_gets_its_own_row(self):
        """招聘网站那一块在窄屏塌成两列，这一格不跟着就会把行挤爆。"""
        i = CSS.index(".cockpit .portal-last")
        self.assertIn(".cockpit .portal-refresh", CSS[i:i + 200])

    def test_the_client_keeps_the_undo(self):
        self.assertIn('export function postResumeRefreshed(name: string, day?: "")',
                      API)

    def test_the_type_says_the_field_may_be_absent(self):
        i = TYPES.index("resumeStale?: number;")
        seg = flat(TYPES[max(0, i - 800):i])
        self.assertRegex(seg, r"没记过时这个字段不在")


class TheSelfcheckSaysItWhenItMatters(unittest.TestCase):
    def _note(self, days, on=True):
        with tempfile.TemporaryDirectory() as t:
            u = pathlib.Path(t) / "u"
            (u / "job_scraper").mkdir(parents=True)
            if days is not None:
                day = (datetime.date.today()
                       - datetime.timedelta(days=days)).isoformat()
                (u / "job_scraper" / "resume_refresh.json").write_text(
                    json.dumps({"BOSS": day}, ensure_ascii=False), encoding="utf-8")
            return doctor.resume_refresh_note(u, {"BOSS": on})

    def test_it_stays_quiet_when_fresh(self):
        self.assertEqual(self._note(1), "")

    def test_it_stays_quiet_just_under_the_line(self):
        self.assertEqual(self._note(doctor.RESUME_STALE_DAYS - 1), "")

    def test_it_speaks_at_the_line(self):
        said = self._note(doctor.RESUME_STALE_DAYS)
        self.assertIn("没刷新", said)
        self.assertIn("BOSS", said)

    def test_it_says_where_to_record_it(self):
        """只说「去刷一下」，那个答案又要丢一次 —— 得指到那个落点上。"""
        self.assertIn("招聘网站", self._note(20))

    def test_it_stays_quiet_for_a_switched_off_portal(self):
        """关掉那家的简历刷不刷不影响任何事。"""
        self.assertEqual(self._note(20, on=False), "")

    def test_never_recorded_says_nothing(self):
        """没记过是「没查」，不是「二十天没刷」——不许替他猜。"""
        self.assertEqual(self._note(None), "")

    def test_the_new_source_is_watched_for_freshness(self):
        """**新加一个写入源，就要挂进 `sources_mtime`。**

        实测 2026-08-24 当场撞上：命令行里清空了这个文件，而 `data.json` 里那个
        天数原样留着 —— 面板显示「今天刷过」，盘上一条记录都没有。
        点按钮那条路不受影响（写完立刻重导），漏的是**带外改动**那条。
        """
        i = SRV.index("def sources_mtime(")
        seg = SRV[i:SRV.index("def needs_reexport(", i)]
        self.assertIn('with_name("resume_refresh.json")', seg)

    def test_it_is_printed_in_the_progress_block(self):
        self.assertIn('if st.get("resume_note"):', DR)
        self.assertIn('st["resume_note"] = resume_refresh_note(', DR)

    def test_it_is_not_the_single_next_step(self):
        """自检只给一条下一步，这是一条提醒 —— 别去抢那一条。"""
        i = DR.index("def next_step(")
        # **取整个函数，不要固定窗口。** `next_step` 现在 8000 字，而这里原来
        # 只看前 6000 —— 最后 2000 字不在检查范围内，那一段里真出现
        # `resume_note` 的话这条会**静默通过**。同一课本仓库已经记过两次
        # （`test_the_padding_survives_a_job_title` 2026-08-27、
        #  `test_the_greeting_stats_are_not_stale` 2026-08-31），
        # 而那两次都是 assertIn（窗口不够会变红）；这里是 assertNotIn，
        # **方向反过来就是假绿**。
        _end = DR.find(chr(10) + "def ", i + 10)
        self.assertNotIn("resume_note", DR[i:_end if _end > 0 else len(DR)])


class TheSignalItLeansOnIsReal(unittest.TestCase):
    def test_the_active_user_has_the_portals_file(self):
        """这一条挂在勾选框上 —— 那份文件不在，整条就是空跑。"""
        p = ROOT / ".active_user"
        if not p.is_file():
            self.skipTest("没有活动用户")
        u = p.read_text(encoding="utf-8").strip()
        f = ROOT / "users" / u / "job_scraper" / "portals.json"
        if not f.is_file():
            self.skipTest("这位用户还没设过渠道开关（缺文件 = 全开）")
        self.assertIsInstance(json.loads(f.read_text(encoding="utf-8")), dict)

    def test_the_export_hands_the_field_to_the_panel(self):
        p = ROOT / "web" / "public" / "data.json"
        if not p.is_file():
            self.skipTest("还没导出过")
        d = json.loads(p.read_text(encoding="utf-8"))
        rows = d.get("portals") or []
        if not rows:
            self.skipTest("导出里没有渠道那一块")
        # 没记过时字段就该不在 —— 这里只验「不会凭空出现一个 0」。
        for r in rows:
            with self.subTest(name=r.get("name")):
                if "resumeStale" in r:
                    self.assertIsInstance(r["resumeStale"], int)


class WhereToClickIsDefinedOnce(unittest.TestCase):
    """「哪几家能刷 / 点哪里 / 怎么算成功」只许有一份定义。

    上一轮把它写了两份：`WEB_REFRESH` 和 `job-refresh.md` Step 1 的表，
    表底下跟着一句「两边别分叉」。没有任何东西执行那句话，于是**一轮之内
    就分叉了** —— 表里写「右侧四个图标里第二个」，`WEB_REFRESH` 里写
    「右侧四个图标里的「刷新简历」」。同一个按钮，两种说法。

    而抄件还盖住了一个真缺陷：`_render` 原来只在「今天刷过」和「刷不了」
    两个分支印入口，**恰恰不印在「该刷」那一行** —— 也就是说读了输出的人
    还得再翻一份文档才知道点哪儿。表存在的唯一理由正是这个洞。

    所以两件事一起钉：正本印得全，抄件不许回来。
    """

    RR = (ROOT / "tools" / "resume_refresh.py").read_text(encoding="utf-8")
    WF = (ROOT / "workflows" / "job-refresh.md").read_text(encoding="utf-8")

    def test_the_due_line_carries_the_entry(self):
        """该刷的那一行自带入口和判成功的方式 —— 那正是它最需要的时候。

        直接拿 `WEB_REFRESH` 拼行，不去读任何真实用户的账本：
        这条验的是渲染，不是某个人的数据（`test_no_maintainer_data_in_repo`
        当场拦过一版把活动用户名写死在这儿的写法 —— 拦得对）。
        """
        import resume_refresh as rr
        rows = [{"渠道": k, "网页能刷": True, "入口": v[1], "怎么算成功": v[2],
                 "上次": "2020-01-01", "今天刷过": False, "多久没刷": 99}
                for k, v in rr.WEB_REFRESH.items() if v[0]]
        self.assertTrue(rows, "WEB_REFRESH 里一家网页能刷的都没有")
        out = rr._render(rows)
        self.assertIn("点哪里：", out, "该刷的那一行没印入口")
        self.assertIn("怎么算成功：", out, "该刷的那一行没说怎么算成功")

    def test_every_web_portal_says_how_to_verify(self):
        """网页刷得了的每一家都要有「怎么算成功」—— 智联不弹提示，
        没有这一句就没法判到底刷没刷上。"""
        import resume_refresh as rr
        for name, v in rr.WEB_REFRESH.items():
            with self.subTest(portal=name):
                self.assertEqual(len(v), 3,
                                 f"{name} 不是（能不能刷, 点哪里, 怎么算成功）三元组")
                self.assertTrue(v[1].strip() and v[2].strip(),
                                f"{name} 的入口或判据是空的")

    def test_the_workflow_does_not_redraw_the_table(self):
        """工作流不许再画一张同样的表。判据是表头里同时出现那几列 ——
        「四个按钮长得像刷新」那张表另一个表头，不会被误伤。"""
        step1 = self.WF[self.WF.index("## Step 1"):self.WF.index("## Step 2")]
        for head in ("| 平台 |", "网页能不能刷"):
            self.assertNotIn(head, step1,
                             f"Step 1 又画了一张渠道表（{head}）—— 正本在 WEB_REFRESH")

    def test_the_workflow_points_at_the_single_source(self):
        self.assertIn("WEB_REFRESH", self.WF, "工作流没说正本在哪")


if __name__ == "__main__":
    unittest.main()
