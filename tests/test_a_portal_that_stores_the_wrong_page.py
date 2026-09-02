# -*- coding: utf-8 -*-
"""同一个文件里两条相反的抓链接规则，执行者挑了错的那条。

`cdp-portals.md` 前程无忧那一节里：

- 一处写着「**别把 `a.comp` 当详情链接**——它指向的是**公司页**
  （`/all/co*.html`，里面是公司简介不是 JD）。第一版就是拿它当详情链接，
  读出来一篇公司介绍，于是判定「前程无忧拿不到 JD」」；
- 另一处写着「⚠️ **详情链接必须用 `a[href*="jobs.51job.com/all/"]` 限定**」——
  **而那个模式把 `/all/co` 一起收了**，正是上一处点名不许用的公司页。

一条规则两个说法，执行者只能挑一条。**代价（实测 2026-08-25）：
前程无忧三条通道合计 164 个岗，取到过 JD 的 1 个。**同期猎聘 1220/1901。

证据不用推理：一个 `/all/co…` 链接底下挂着**三个毫不相干的岗**
（安卓研发工程师 / 运营实习生 / 后端开发实习生）——真的职位页不可能是三个职位。
同一节里那条「URL 不是职位唯一标识：实测同一 URL 下挂着两个不同职位」
记的就是这个现象，但它把原因写成了「51job 的 URL 就是这样」，
**而真正的原因是存错了页**。

## 这一条同时立了一个机械判据

文档改对了只管这一次。`audit_pipeline.check_a_portal_never_yields_a_jd`
换个渠道、换个时间照样查得出来：**抓取率低 + 一个链接挂 3 个以上的岗**。
"""
import pathlib
import re
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import audit_pipeline as ap  # noqa: E402

PORTALS = (ROOT / "workflows" / "reference"
           / "cdp-portals.md").read_text(encoding="utf-8")


def flat(s: str) -> str:
    s = " ".join(re.sub(r"^\s*(?:>|#:?)\s?", "", s, flags=re.M).split())
    return re.sub(r"(?<=[一-鿿，。；：、（）「」])"
                  r" +(?=[一-鿿，。；：、（）「」])", "", s)


class TheTwoRulesNoLongerContradict(unittest.TestCase):

    def test_the_loose_selector_is_gone(self):
        """`a[href*="jobs.51job.com/all/"]` 收了公司页 —— 不许再作为「必须」的写法。"""
        self.assertNotIn('详情链接必须用 `a[href*="jobs.51job.com/all/"]` 限定', PORTALS)

    def test_the_new_rule_excludes_the_company_prefix(self):
        self.assertIn(':not([href*="/all/co"])', PORTALS)

    def test_the_company_page_rule_is_still_there(self):
        """两条里对的那一条不许被顺手删掉。"""
        self.assertIn("别把 `.joblist-item` 上那个 `a.comp` 当详情链接", PORTALS)
        self.assertIn("/all/co*.html", PORTALS)

    def test_the_two_now_point_at_each_other(self):
        """改对不够，要让下一个人看见它们说的是同一件事。"""
        i = PORTALS.index(':not([href*="/all/co"])')
        seg = flat(PORTALS[max(0, i - 600):i + 2200])
        self.assertIn("别把 `a.comp` 当详情链接", seg)

    def test_it_records_the_cost(self):
        i = PORTALS.index(':not([href*="/all/co"])')
        seg = flat(PORTALS[i:i + 2200])
        self.assertIn("164 个岗", seg)
        self.assertIn("取到过 JD 的 1 个", seg)

    def test_it_records_the_evidence_not_just_the_conclusion(self):
        """「一个链接挂三个不相干的岗」是这条的证据，删了就只剩断言。"""
        i = PORTALS.index(':not([href*="/all/co"])')
        seg = flat(PORTALS[i:i + 2200])
        self.assertIn("三个毫不相干的岗", seg)
        self.assertIn("真的职位页不可能是三个职位", seg)

    def test_it_names_the_shape_that_works(self):
        """光说别用什么不够，要说用什么 —— 实测通的那个形状。"""
        seg = flat(PORTALS[PORTALS.index(':not([href*="/all/co"])'):][:2200])
        self.assertIn("jobs.51job.com/<城市>-<区码>/<职位id>.html", seg)
        self.assertIn("2026-08-25", seg)

    def test_the_dedup_key_rule_survives(self):
        """去重键带职位名那条不许因为「链接修好了」被删 —— 它防的是另一件事。"""
        self.assertIn("去重键仍然要带职位名", PORTALS)
        self.assertIn("<url>#<职位名>", PORTALS)


class TheAuditCatchesItMechanically(unittest.TestCase):
    """文档改对了只管这一次；判据换个渠道换个时间照样查得出来。"""

    def _fn(self):
        return ap.check_a_portal_never_yields_a_jd

    def test_it_is_registered(self):
        self.assertIn(self._fn(), [f for _n, f in ap.CHECKS])

    def test_the_two_thresholds_are_named(self):
        self.assertIsInstance(ap._JD_RATE_MIN_JOBS, int)
        self.assertIsInstance(ap._SAME_URL_TOO_MANY, int)

    def test_two_is_not_enough_to_accuse(self):
        """**2 有良性解释**（重复挂牌、同岗两次抓取），猎聘就有一对而它的链接是好的。"""
        self.assertGreaterEqual(ap._SAME_URL_TOO_MANY, 3)

    def test_the_reason_for_three_is_written_down(self):
        src = (ROOT / "tools" / "audit_pipeline.py").read_text(encoding="utf-8")
        i = src.index("_SAME_URL_TOO_MANY = ")
        seg = flat(src[max(0, i - 700):i])
        self.assertIn("2 不够", seg)
        self.assertIn("而猎聘的链接是好的", seg)

    def test_a_low_rate_alone_is_not_enough(self):
        """**BOSS / 智联的低抓取率是设计如此**（JD 只能在抓取当次取），报它们是误报。"""
        src = (ROOT / "tools" / "audit_pipeline.py").read_text(encoding="utf-8")
        i = src.index("def check_a_portal_never_yields_a_jd")
        seg = flat(src[i:i + 4000])
        self.assertIn("低抓取率本身不是判据", seg)
        self.assertIn("误报一次，这条就会被整条忽略", seg)

    def test_it_groups_by_site_not_by_channel(self):
        """同一家有好几个通道标记，按通道拆开判据就失灵 —— 实测记在注释里。"""
        src = (ROOT / "tools" / "audit_pipeline.py").read_text(encoding="utf-8")
        i = src.index("def check_a_portal_never_yields_a_jd")
        seg = src[i:i + 4000]
        self.assertIn("by[_site(e)].append(e)", seg)
        self.assertIn("按通道拆开的代价实测过", flat(seg))

    def test_that_normaliser_really_merges_the_channels(self):
        """引的 `_site` 得真把三个 51job 标记并成一家。"""
        got = {ap._site({"portal": p})
               for p in ("51job", "51job-cdp", "51job-browser")}
        self.assertEqual(got, {"前程无忧"})


class TheJudgeFiresOnlyOnTheRealShape(unittest.TestCase):
    """喂构造数据：该报的报、不该报的一个都不许报。"""

    def _run(self, rows, bodies=()):
        """`rows` = [(portal, title, url)]，`bodies` = 有 JD 的那些 url。"""
        import jd_store as st
        seen = {f"k{i}": {"portal": p, "title": t, "url": u}
                for i, (p, t, u) in enumerate(rows)}
        real_load, real_has = st.load, st.has_body
        st.load = lambda user, url, title: {"description": "x" * 200} if url in bodies else None
        st.has_body = lambda d: bool(d)
        old = list(ap._USER)
        try:
            ap._USER[:] = ["someone"]
            return ap.check_a_portal_never_yields_a_jd(seen, {})
        finally:
            ap._USER[:] = old
            st.load, st.has_body = real_load, real_has

    def _many(self, portal, n, url=None):
        return [(portal, f"岗{i}", url or f"https://x/{i}") for i in range(n)]

    def test_a_company_page_shape_is_caught(self):
        rows = self._many("51job", 25, url="https://jobs.51job.com/all/coX.html")
        got = self._run(rows)
        self.assertEqual(len(got), 1)
        self.assertIn("前程无忧", got[0][2])
        self.assertIn("一个链接底下挂着", got[0][2])

    def test_a_healthy_portal_is_silent(self):
        rows = self._many("liepin-search", 40)
        self.assertEqual(self._run(rows, bodies={r[2] for r in rows}), [])

    def test_a_low_rate_without_collisions_is_silent(self):
        """**这是 BOSS / 智联那一档**：抓取率低，但每个岗都有自己的链接。"""
        rows = self._many("boss-browser", 40)
        self.assertEqual(self._run(rows), [])

    def test_two_on_one_url_is_silent(self):
        """重复挂牌会撞出 2 来，那不是存错页。"""
        rows = self._many("liepin-search", 30)
        rows[1] = ("liepin-search", "岗1", rows[0][2])
        self.assertEqual(self._run(rows), [])

    def test_a_small_portal_is_not_accused(self):
        """样本太小时「一个都没有」可能只是还没轮到它抓。"""
        rows = self._many("51job", 5, url="https://jobs.51job.com/all/coX.html")
        self.assertEqual(self._run(rows), [])

    def test_a_collision_on_a_working_portal_is_silent(self):
        """撞了 3 个但 JD 抓得到 —— 那是别的问题，不归这条管。"""
        rows = self._many("51job", 25, url="https://jobs.51job.com/all/coX.html")
        self.assertEqual(self._run(rows, bodies={rows[0][2]}), [])

    def test_no_active_user_is_silent(self):
        """**要喂真会走进循环的数据。**

        第一版传的是空 `seen`，于是循环体一次都没进去 —— `_USER[0]` 那一下
        根本没被碰到，把守卫整行删掉测试照样绿（2026-08-25 变异检验逮到）。
        现在喂一批必然触发报告的岗：没有活动用户时它仍要闭嘴，而不是抛
        `IndexError`。
        """
        rows = [("51job", f"岗{i}", "https://jobs.51job.com/all/coX.html")
                for i in range(25)]
        seen = {f"k{i}": {"portal": p, "title": t, "url": u}
                for i, (p, t, u) in enumerate(rows)}
        old = list(ap._USER)
        try:
            ap._USER[:] = []
            self.assertEqual(ap.check_a_portal_never_yields_a_jd(seen, {}), [])
        finally:
            ap._USER[:] = old

    def test_the_message_says_what_to_do(self):
        rows = self._many("51job", 25, url="https://jobs.51job.com/all/coX.html")
        msg = self._run(rows)[0][2]
        self.assertIn("/job-scrape", msg)
        self.assertIn("cdp-portals.md", msg)

    def test_the_message_names_the_likely_cause(self):
        """只说「取不到 JD」等于把诊断留给读的人。"""
        rows = self._many("51job", 25, url="https://jobs.51job.com/all/coX.html")
        msg = self._run(rows)[0][2]
        self.assertIn("多半是存错了页", msg)

    def test_the_message_names_the_jobs_that_share_it(self):
        """点名那几个岗，读的人一眼看得出它们互不相干。"""
        rows = [("51job", "安卓工程师", "https://jobs.51job.com/all/coX.html"),
                ("51job", "运营实习生", "https://jobs.51job.com/all/coX.html"),
                ("51job", "后端实习生", "https://jobs.51job.com/all/coX.html")]
        rows += self._many("51job", 22)
        msg = self._run(rows)[0][2]
        for t in ("安卓工程师", "运营实习生", "后端实习生"):
            with self.subTest(t=t):
                self.assertIn(t, msg)


class TheFloorLeavesRoomForAStrayJd(unittest.TestCase):
    """`_JD_RATE_FLOOR = 0.05` —— 此前**一条测试都没提过它**。

    它定的是「低到什么程度才开始怀疑」。定义处写着为什么不用 0：
    「偶尔有一两个是从别的通道补进来的（同一个岗浏览器抓过一次）。」

    两个方向都会静默出事，而且都落在同一条消息上 ——
    那条消息给的处置是「改抓链接规则，重抓一轮 `/job-scrape`」：

        调成 0    → 补进来一个 JD 就不再怀疑；那家存的还是公司页，
                    从此没人会知道，而它的岗一个都评不了深评
        调成 0.9  → 抓得好好的渠道也被指着说「多半是存错了页」，
                    照它去改抓链接规则，是把对的改坏

    钉边界行为，个数**写死**（不从常量现算 —— 那等于让它自己给自己出题）。
    """

    COLL = "https://jobs.51job.com/all/coX.html"

    def _run(self, n, with_body):
        """`n` 个岗全挂在一个链接上，另有 `with_body` 个是别处补进来的。"""
        import jd_store as st
        rows = [("51job", f"岗{i}", self.COLL) for i in range(n - with_body)]
        rows += [("51job", f"补{i}", f"https://x/{i}")
                 for i in range(with_body)]
        seen = {f"k{i}": {"portal": p, "title": t, "url": u}
                for i, (p, t, u) in enumerate(rows)}
        bodies = {r[2] for r in rows if r[2] != self.COLL}
        real_load, real_has = st.load, st.has_body
        st.load = (lambda user, url, title:
                   {"description": "x" * 200} if url in bodies else None)
        st.has_body = lambda d: bool(d)
        old = list(ap._USER)
        try:
            ap._USER[:] = ["someone"]
            return ap.check_a_portal_never_yields_a_jd(seen, {})
        finally:
            ap._USER[:] = old
            st.load, st.has_body = real_load, real_has

    def test_a_stray_jd_does_not_clear_the_portal(self):
        """40 个岗里补进来 1 个 —— 那家存的还是公司页，照样要报。"""
        got = self._run(40, 1)
        self.assertTrue(got, "补进来一个 JD 就不吭声了 —— 剩下 39 个还是评不了")
        self.assertIn("只有 1 个取到过 JD", got[0][2])

    def test_exactly_at_the_floor_it_still_accuses(self):
        """2/40 正好 5%，落在门槛上 —— 边界上要算「几乎取不到」。"""
        self.assertTrue(self._run(40, 2))

    def test_just_above_the_floor_it_lets_go(self):
        """3/40 = 7.5%，超过门槛 —— 这家取得到，别指着它改规则。"""
        self.assertEqual(self._run(40, 3), [],
                         "抓得到 JD 的渠道也被说成存错页 —— 照它改是把对的改坏")

    def test_the_reason_for_not_using_zero_is_written_down(self):
        src = (ROOT / "tools" / "audit_pipeline.py").read_text(
            encoding="utf-8")
        i = src.index("_JD_RATE_FLOOR = ")
        self.assertIn("从别的通道补进来", flat(src[max(0, i - 300):i]),
                      "那个数没留下「为什么不用 0」的理由")

    def test_the_title_does_not_overstate_the_floor(self):
        """**标题说满了就是假话。** 这条容得下一两个 JD，标题不能写「一个都取不到」
        —— 报文里同时印着「只有 1 个取到过 JD」，两句话当场打架，
        而用户先看到的是标题。
        """
        title = self._run(40, 1)[0][1]
        self.assertNotIn("一个都", title)
        self.assertIn("几乎", title)


class TheSignalItLeansOnIsReal(unittest.TestCase):
    """现算：这位用户此刻真的处在这个状态里。"""

    def test_the_audit_reports_exactly_one_portal(self):
        p = ROOT / ".active_user"
        if not p.is_file():
            self.skipTest("没有活动用户")
        old = list(ap._USER)
        try:
            ap._USER[:] = [p.read_text(encoding="utf-8").strip()]
            seen, details = ap.load(ap._USER[0])
            got = ap.check_a_portal_never_yields_a_jd(seen, details)
        finally:
            ap._USER[:] = old
        if not got:
            self.skipTest("没有渠道处在这个状态里 —— 好事，说明重抓过了")
        self.assertEqual(len(got), 1)
        self.assertIn("个岗里只有", got[0][2])

    def test_the_healthy_portals_are_not_in_it(self):
        """**支点。** 报到猎聘头上就说明判据太松了。"""
        p = ROOT / ".active_user"
        if not p.is_file():
            self.skipTest("没有活动用户")
        old = list(ap._USER)
        try:
            ap._USER[:] = [p.read_text(encoding="utf-8").strip()]
            seen, details = ap.load(ap._USER[0])
            got = ap.check_a_portal_never_yields_a_jd(seen, details)
        finally:
            ap._USER[:] = old
        if not got:
            self.skipTest("这条没有输出")
        self.assertNotIn("猎聘", got[0][2])


if __name__ == "__main__":
    unittest.main()
