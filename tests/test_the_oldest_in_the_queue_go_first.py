# -*- coding: utf-8 -*-
"""备好没投的 63 个岗按分数排，而岗位会在他发出去之前先下线。

面板已经会说「先发这 4 个『值得投』的，另外 59 个是『可以考虑』」——
判词分档回答的是**该不该发**。它没回答**先发哪个**，而那个问题有答案：

实测活动用户 2026-08-23，有材料没投的岗按**队列岗龄**（`first_seen` → 今天）
分桶，已下线的比例是：

    ≤7 天    2/27
    8-14 天  2/95
    >14 天   8/34   ← 23%

**超过两周那一档，将近四分之一已经没了。** 而他手上正有 13 个在那一档，
另有 12 个是「材料做出来了、岗却在他发出去之前先下线」的既成事实。

## 这个岗龄和 `staleDays` 不是一回事

`staleDays` 说的是「**抓到它那天**，它上一次刷新在多久以前」，靠猎聘的 `date`，
实测 2638 个岗里只有 259 个有（10%）。
这里说的是「**它在我手上排了多久**」，靠 `first_seen`，100% 有。
前者是招聘方的行为，后者是队列的行为 —— 回答的是两个问题。

## 先发老的，不是「老的更值得投」

分数一点没变，变的只是**还剩多少时间**：新的明天还在，老的可能就没了。
所以这一句只加在既有那两档后面，**不改分档**。
"""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import build_dashboard as bd  # noqa: E402
import export_web_data as ex  # noqa: E402

BD = (ROOT / "tools" / "build_dashboard.py").read_text(encoding="utf-8")
EX = (ROOT / "tools" / "export_web_data.py").read_text(encoding="utf-8")


class TheCountIsProduced(unittest.TestCase):
    def test_the_key_exists(self):
        self.assertIn('"ready_old": sum(', EX, "导出侧还没有这个数")

    def test_it_uses_the_existing_threshold(self):
        """14 天这个数仓库里已经有了（`STALE_POSTING_DAYS`），别再立一个。

        **要那行代码，不是常量名出现过。** 上面那段注释里就写着
        「阈值直接用 `STALE_POSTING_DAYS`（14）」—— 只验名字的话，
        把代码里的比较换成 `> 21` 照样绿（变异实测）。"""
        i = EX.index('"ready_old": sum(')
        self.assertIn("a > STALE_POSTING_DAYS", EX[i:i + 400],
                      "比较那一行没用共享阈值")

    def test_it_counts_the_same_set_as_ready(self):
        """分子必须是 `ready` 的子集 —— 口径一分叉，两个数就没法一起读。"""
        i = EX.index('"ready_old": sum(')
        seg = EX[i:i + 400]
        self.assertIn('"materials" in j["funnels"]', seg)
        self.assertIn('"applied" not in j["funnels"]', seg)

    def test_it_reads_first_seen_not_the_posting_date(self):
        """用 `date` 就变成另一个问题了（而且只有 10% 的岗有）。

        **变量名 2026-08-25 改过：`_first_seen` → `_first_seen_all`。**
        那天逐岗也开始要这个数（`queuedDays`，名单上标「排了 N 天没发」），
        于是那份查找表提前建、两处共用；原来那份局部的删掉了。
        """
        i = EX.index('"ready_old": sum(')
        self.assertIn("_first_seen_all.get(", EX[i:i + 400])

    def test_the_lookup_is_built_from_seen(self):
        self.assertIn('_first_seen_all = {e.get("url"): e.get("first_seen")', EX)

    def test_only_one_lookup_is_built(self):
        """**两处必须读同一份。** 各建一份就是等它们哪天不一致。"""
        self.assertEqual(EX.count('= {e.get("url"): e.get("first_seen")'), 1,
                         "又建了第二份 first_seen 查找表")

    def test_the_per_job_field_reads_the_same_one(self):
        """逐岗那个 `queuedDays` 和这里的计数同源 —— 否则一屏两个数。"""
        line = next(l for l in EX.splitlines() if "_q = _days_since(" in l)
        self.assertIn("_first_seen_all.get(", line)

    def test_the_two_ages_are_distinguished(self):
        i = EX.index('"ready_old": sum(')
        seg = " ".join(EX[max(0, i - 900):i].split())
        self.assertRegex(seg, r"和 `staleDays` 不是一回事")
        self.assertRegex(seg, r"它在我手上排了多久")

    def test_the_measurement_is_recorded(self):
        i = EX.index('"ready_old": sum(')
        seg = " ".join(EX[max(0, i - 900):i].split())
        self.assertRegex(seg, r"≤7 天 2/27、8-14 天 2/95、>14 天 8/34（23%）")
        self.assertIn("2026-08-23", seg)


class TheGuidanceSaysWhichToSendFirst(unittest.TestCase):
    def test_it_adds_the_clause(self):
        s = bd._ready_text(63, 4, 13)
        self.assertIn("有 13 个已经排了两周以上，先发它们", s)

    def test_it_stays_quiet_with_none(self):
        """没有那一批时一个字都不说 —— 否则每次都多一句噪音。"""
        s = bd._ready_text(63, 4, 0)
        self.assertNotIn("两周", s)
        self.assertEqual(s, bd._ready_text(63, 4))

    def test_it_does_not_change_the_tier_split(self):
        """判词分档回答「该不该发」，岗龄回答「先发哪个」—— 两件事。"""
        s = bd._ready_text(63, 4, 13)
        self.assertIn("先发这 4 个「值得投」的", s)
        self.assertIn("另外 59 个是「可以考虑」", s)

    def test_it_works_on_the_all_maybe_branch(self):
        s = bd._ready_text(63, 0, 13)
        self.assertIn("都是「可以考虑」这一档", s)
        self.assertIn("先发它们", s)

    def test_it_works_on_the_legacy_branch(self):
        """老调用点不传 `strong` —— 那一支也要能带上这句。"""
        s = bd._ready_text(63, None, 13)
        self.assertIn("先发它们", s)

    def test_the_legacy_branch_keeps_its_tail_when_quiet(self):
        """没有老岗时，那一句「投完回来记一笔」不能被顺手删掉。"""
        self.assertIn("投完回来记一笔", bd._ready_text(63))

    def test_it_says_why_not_that_they_are_better(self):
        """「先发老的」最容易被读成「老的更值得投」。"""
        s = bd._ready_text(63, 4, 13)
        self.assertIn("分数没变，是它们还剩的时间少了", s)

    def test_it_carries_the_evidence(self):
        s = bd._ready_text(63, 4, 13)
        self.assertIn("已经有近四分之一在发出去之前下线", s)

    def test_no_markdown_reaches_the_panel(self):
        """这句进纯文本节点，`**` 会连星号一起显示。"""
        for args in ((63, 4, 13), (63, 0, 13), (63, None, 13)):
            with self.subTest(args=args):
                self.assertNotIn("**", bd._ready_text(*args))

    def test_the_caller_passes_it(self):
        self.assertIn('counts.get("ready_old") or 0', BD,
                      "算出来了却没传进去")

    def test_the_reason_is_in_the_docstring(self):
        i = BD.index("def _ready_text(")
        seg = " ".join(BD[i:BD.index("def _tail()", i)].split())
        self.assertRegex(seg, r"≤7 天 2/27、8-14 天 2/95、>14 天 8/34（23%）")
        self.assertRegex(seg, r"判词分档回答「该不该发」，岗龄回答「先发哪个」")


class TheClauseHasOneHome(unittest.TestCase):
    """**这句话只许有一个住址：`_ready_text`。**

    它原来有两份。写第二份时的理由记在这个类的旧名字里
    （`TheSeasonBranchSaysItToo`）：那时面板走的是「零回音」那一支，
    根本到不了 `_ready_text`，所以季节那一句里也补了一份。

    后来两件事凑到一起：

    1. 「零回音」那一支 2026-08-29 按用户裁定撤了（工具不催）；
    2. `season_note` 被接到 ready 那一支上 —— 它回答的本来就是
       「现在该不该发」，接得对。

    于是两处**同时触发**。实测 2026-08-30 面板上那句「下一步」230 字，
    「其中 N 个排了两周以上……分数没变，是它们还剩的时间少了」出现两次 ——
    而那是这一页最该被读的一行。

    ## 当时的守卫把「两个住址」当成了正确状态

        def test_the_sibling_sentence_is_untouched(self):
            # 注释原话：「`_ready_text` 那一处说的是同一件事的另一个入口，
            #            别被这次改动带掉。」
            self.assertEqual(BD.count("分数没变，是它们还剩的时间少了"), 2)

    它数的是**源码里的份数**，而两处会不会同时触发取决于分支 ——
    分支一合并，这条照样绿。判据现在反过来：**只许有一份**。

    ## 为什么留下的是 `_ready_text` 那一份

    `season_note` 说不出话时返回空串（淡季、样本不足、阶段不明都会）。
    把这句话放在它那儿，那些时候整句就没了 —— 而「先发排得最久的」
    跟季节无关，它讲的是岗位下线。
    """

    import datetime as _dt
    #: 北京时间 8 月下旬：全投在淡季（7-8 月），金九银十在 31 天内。
    TODAY = _dt.date(2026, 8, 23)
    MONTHS = [8] * 20

    def test_the_clause_lives_in_ready_text(self):
        s = bd._ready_text(62, 30, 13)
        self.assertIn("这里面有 13 个已经排了两周以上，先发它们", s)

    def test_it_says_why_not_that_they_are_better(self):
        self.assertIn("分数没变，是它们还剩的时间少了", bd._ready_text(62, 30, 13))

    def test_it_says_how_to_spot_them(self):
        """「从它们开始」得说得出「哪几个」—— 这一半是从季节那句并过来的。"""
        self.assertIn("名单上标着「排了 N 天没发」的就是", bd._ready_text(62, 30, 13))

    def test_it_stays_quiet_with_none(self):
        self.assertNotIn("两周以上", bd._ready_text(62, 30, 0))

    def test_the_season_line_no_longer_repeats_it(self):
        s = bd.season_note(self.MONTHS, self.TODAY, "离职，正在找工作",
                           ready=62)
        self.assertNotIn("两周以上", s)
        self.assertNotIn("分数没变", s)

    def test_the_season_line_gave_up_the_losses_too(self):
        """**同一次迁移的第二句。** 「已经白做了几个」2026-09-01 也搬走了 ——
        理由和上面那句一模一样（这个类的说明里写着：`season_note` 说不出话时
        返回空串，跟季节无关的事放它那儿，那些时候整句就没了）。

        当天就兑现了：进金九银十，那一支改走「已经进旺季」的 return，
        12 个白做的材料在面板上一个字也没提。
        """
        s = bd.season_note(self.MONTHS, self.TODAY, "离职，正在找工作",
                           ready=62)
        self.assertNotIn("下线", s)
        self.assertIn("个岗在你发出去之前就下线了",
                      bd._ready_text(62, 30, 0, None, 11))

    def test_the_season_halves_survive(self):
        """并掉一份不等于把季节那句也改了 —— 它自己那几半要原样在。"""
        s = bd.season_note(self.MONTHS, self.TODAY, "离职，正在找工作",
                           ready=62)
        self.assertIn("手上那 62 份备好的别等", s)
        self.assertIn("旺季用来补新的", s)

    def test_no_markdown(self):
        for s in (bd._ready_text(62, 30, 13, None, 11),
                  bd.season_note(self.MONTHS, self.TODAY, "离职，正在找工作",
                                 ready=62)):
            with self.subTest(s=s[:20]):
                self.assertNotIn("**", s)

    def test_only_one_producer_in_the_source(self):
        """**这条是上一版那条的反面：只许有一个生产者。**

        ⚠️ **数的是生产者，不是这句话出现几次。** 上一版数全文，而说明
        「为什么只留一份」的注释里也写着这句话 —— 一写就数出 3 个。
        判据是「哪几行真的会把它拼进输出」，也就是带 f-string 的那几行。
        """
        made = [ln for ln in BD.splitlines()
                if "分数没变，是它们还剩的时间少了" in ln and 'f"' in ln]
        self.assertEqual(
            len(made), 1,
            "这句话又长出第二个生产者了 —— 两处会在同一支分支上同时触发：\n  "
            + "\n  ".join(ln.strip() for ln in made))

    def test_the_two_do_not_repeat_each_other_on_screen(self):
        """真正要防的是**屏幕上**说两遍，不是源码里有两份 —— 拼起来数一次。"""
        head = bd._ready_text(62, 30, 13, None, 11)
        tail = bd.season_note(self.MONTHS, self.TODAY, "离职，正在找工作",
                              ready=62)
        self.assertEqual((head + tail).count("两周以上"), 1)
        self.assertEqual((head + tail).count("分数没变"), 1)
        self.assertEqual((head + tail).count("在你发出去之前就下线了"), 1)

    def test_the_caller_no_longer_passes_it(self):
        """参数删了才不会有人再把那份文案加回去。"""
        self.assertEqual(BD.count('counts.get("ready_old") or 0'), 1)
        self.assertNotIn("ready_old: int = 0", BD)


class TheSignalItLeansOnIsReal(unittest.TestCase):
    """整条建立在「排得久的更容易已经下线」上。有语料时验一次。"""

    def test_the_old_bucket_really_expires_more(self):
        import json
        import datetime as dt
        p = ROOT / ".active_user"
        if not p.is_file():
            self.skipTest("没有活动用户")
        u = p.read_text(encoding="utf-8").strip()
        f = ROOT / "users" / u / "job_scraper" / "seen_jobs.json"
        w = ROOT / "web" / "public" / "data.json"
        if not (f.is_file() and w.is_file()):
            self.skipTest("没有语料或没导出过")
        seen = json.loads(f.read_text(encoding="utf-8"))["seen"]
        jobs = json.loads(w.read_text(encoding="utf-8"))["jobs"]
        by = {j.get("url"): j for j in jobs if j.get("url")}
        today = dt.date.today()
        old = [0, 0]
        new = [0, 0]
        for e in seen.values():
            if not isinstance(e, dict):
                continue
            j = by.get(e.get("url"))
            if not j or not j.get("materials") or j.get("applied"):
                continue
            raw = e.get("first_seen")
            if not raw:
                continue
            age = (today - dt.date.fromisoformat(raw[:10])).days
            box = old if age > ex.STALE_POSTING_DAYS else new
            box[1] += 1
            if j.get("expired") or e.get("status") == "expired":
                box[0] += 1
        if old[1] < 10 or new[1] < 10:
            self.skipTest("样本太小，说明不了")
        self.assertGreater(old[0] / old[1], new[0] / new[1],
                           f"排得久的反而更不容易下线（老 {old}, 新 {new}）—— "
                           f"那上面那句建议的依据就不成立了")


class TheNeighbouringRulesAreIntact(unittest.TestCase):
    def test_the_stale_threshold_is_still_fourteen(self):
        self.assertEqual(ex.STALE_POSTING_DAYS, 14)

    def test_the_posting_age_field_still_means_something_else(self):
        i = EX.index("def posting_age(")
        seg = " ".join(EX[i:i + 900].split())
        self.assertRegex(seg, r"抓到它那天，它上一次刷新在多久以前")

    def test_the_tier_split_reason_survives(self):
        """「63 个里 59 个是可以考虑」那次实测是分档的理由。"""
        self.assertRegex(" ".join(BD.split()), r"\*\*59 个是「可以考虑」\*\*")

    def test_the_expired_unsent_note_survives(self):
        """「材料做出来了、岗却先关了」那句是同一件事的另一半。"""
        self.assertRegex(" ".join(BD.split()), r"在你发出去之前就下线了")


if __name__ == "__main__":
    unittest.main()
