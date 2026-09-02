"""催进度的判定：安静天数、跟进上限、日期防御。

## 为什么固化成工具再测

`outcome.md` 的 Step 2b 用一整段规定了这套判定，但原来**全靠每次现算**。
本仓库在同一件事上栽过：`fetch_details.py` 的「撞限流就停」也曾是临时写的，
写错一次就把 13 个 URL 全发了出去。判定逻辑不能靠每次现写。

而且这里的错是**静默**的，三种都不会报错、只会悄悄做错事：

- 安静天数从投递日算而不是从上次跟进算 → 跟进过一次之后立刻又判「该催」，
  于是催第二遍、第三遍
- 已跟进次数数错 → 催第三次，`outcome.md` 明令禁止
- 日期解析不了就估一个 → 催早催晚都由这个估值造成，用户还看不出是估的
"""

import csv
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import followups as fu  # noqa: E402

TODAY = date(2026, 7, 31)
A = lambda **kw: fu.assess({"company": "某所", "role": "某岗", **kw}, TODAY, 10)


class QuietDaysCountFromTheLastAction(unittest.TestCase):
    """跟进过就从**跟进日**算，没跟进过才从投递日算。

    从投递日算是最容易犯的错：一个 6-25 投递、7-18 跟进过的岗，按投递日算是
    36 天「早该催了」，按跟进日算才 13 天。前者会让人在跟进后没几天又催一遍。
    """

    def test_no_followup_counts_from_applied(self):
        r = A(date="2026-07-15", status="applied", notes="已投递")
        self.assertEqual(r["quiet_days"], 16)
        self.assertTrue(r["due"])

    def test_with_followup_counts_from_the_followup(self):
        r = A(date="2026-06-25", status="applied",
              notes="已投递 | followed up 2026-07-18")
        self.assertEqual(r["quiet_days"], 13, "从投递日算成 36 天了")
        self.assertTrue(r["due"])

    def test_recent_followup_is_not_due_again(self):
        """刚跟进过就不该再催——这正是「从投递日算」会犯的错。"""
        r = A(date="2026-05-01", status="applied",
              notes="已投递 | followed up 2026-07-29")
        self.assertFalse(r["due"], "跟进才 2 天又判该催")
        self.assertEqual(r["quiet_days"], 2)

    def test_too_recent_is_not_due(self):
        self.assertFalse(A(date="2026-07-28", status="applied", notes="")["due"])


class TwoFollowupsIsTheCeiling(unittest.TestCase):
    """`outcome.md`：第二次仍然沉默之后，诚实的做法是记录结果，不是坚持。"""

    def test_two_followups_stops(self):
        r = A(date="2026-06-20", status="applied",
              notes="| followed up 2026-07-01 | followed up 2026-07-20")
        self.assertFalse(r["due"], "催第三遍了")
        self.assertEqual(r["n_followups"], 2)
        self.assertIn("记录结果", r["why_not"], "没告诉用户该转去记结果")

    def test_one_followup_still_allowed(self):
        r = A(date="2026-06-01", status="applied", notes="| followed up 2026-07-10")
        self.assertTrue(r["due"])
        self.assertEqual(r["n_followups"], 1)


class DatesAreParsedDefensivelyNeverGuessed(unittest.TestCase):

    def test_common_formats_parse(self):
        for s in ["2026-07-12", "2026/07/12", "2026.07.12", "2026年07月12日"]:
            with self.subTest(s=s):
                self.assertEqual(fu.parse_date(s), date(2026, 7, 12))

    def test_unparseable_is_reported_not_estimated(self):
        for bad in ["", "上个月", "07-12", "忘了"]:
            with self.subTest(bad=bad):
                r = A(date=bad, status="applied", notes="")
                self.assertFalse(r["due"], f"「{bad}」被猜出了一个日期还判了该催")
                self.assertIsNone(r["quiet_days"])
                self.assertIn("解析不了", r["why_not"])

    def test_broken_dates_are_always_surfaced(self):
        """日期缺失是**数据缺陷**，不是「这条不该催」——必须报出来让用户补。"""
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            u = tmp / "users" / "张三"
            u.mkdir(parents=True)
            (tmp / ".active_user").write_text("张三", encoding="utf-8")
            hdr = ["date", "company", "role", "status", "notes", "channel",
                   "contact_person"]
            with (u / "job_search_tracker.csv").open("w", encoding="utf-8",
                                                     newline="") as f:
                w = csv.DictWriter(f, fieldnames=hdr)
                w.writeheader()
                w.writerow({"date": "", "company": "某所", "role": "某岗",
                            "status": "applied", "notes": "", "channel": "",
                            "contact_person": ""})
            saved = fu.ROOT
            try:
                fu.ROOT = tmp
                import contextlib
                import io
                buf = io.StringIO()
                with contextlib.redirect_stdout(buf):
                    fu.main(["--today", "2026-07-31", "--user", "张三"])
                out = buf.getvalue()
            finally:
                fu.ROOT = saved
        self.assertIn("解析不了", out, "日期坏掉的行被静默吞了")


class FinalStatusesAreNeverChased(unittest.TestCase):

    def test_resolved_are_excluded(self):
        for s in ["rejected", "hired", "no response", "withdrawn",
                  "offer declined", "interview_only"]:
            with self.subTest(status=s):
                r = A(date="2026-01-01", status=s, notes="")
                self.assertFalse(r["due"], f"「{s}」已终结却还在催")
                self.assertIn("已终结", r["why_not"])

    def test_interview_and_offer_are_still_open(self):
        """流程还在走的不算终结——面试后没消息，照样该催。"""
        for s in ["interview", "offer"]:
            with self.subTest(status=s):
                self.assertTrue(A(date="2026-07-01", status=s, notes="")["due"],
                                f"「{s}」是进行中，不该被当成终结态")


class ThresholdMatchesTheWorkflow(unittest.TestCase):

    def test_default_is_ten_days(self):
        # 锚在**值**上，不锚在字面量上：默认现在来自 `QUIET_DAYS`
        # （2026-08-13 收拢成唯一定义），源码里已经没有 `default=10` 这个串了，
        # 而它守的规矩——「默认就是 10 天」——一个字没变。
        self.assertEqual(fu.QUIET_DAYS, 10,
                         "默认阈值与 outcome.md 的 10 天不一致")
        import inspect
        self.assertIn("default=QUIET_DAYS", inspect.getsource(fu.main),
                      "命令行默认没接到那个常量上，两边还能各走各的")

    def test_max_followups_is_two(self):
        self.assertEqual(fu.MAX_FOLLOWUPS, 2)

    def test_workflow_still_says_ten_and_two(self):
        """文档与工具必须同口径——改了一边没改另一边，就会各说各的。"""
        t = (ROOT / "workflows" / "job-outcome.md").read_text(encoding="utf-8")
        self.assertIn("10", t)
        # 原来这行写的是 `assertIn("two", t.lower() + "两次")` —— 在尾巴上拼一个
        # 中文串**并不会**让 "two" 命中，所以它实际只验了英文那一款。
        # 2026-08-20 把 job-outcome.md 翻成中文，它当场露馅。改成两款都收。
        self.assertTrue("两次" in t or "two" in t.lower(),
                        "job-outcome.md 里找不到「最多跟进两次」这条上限了")


class TheDueListHasNoDanglingSeparator(unittest.TestCase):
    """`channel` 为空时，那一行不许以「· 」收尾。

    2026-08-21 对真实台账跑 `python tools/followups.py`：**18 行全部以
    「安静 11 天 · 」结尾**——一个吊在末尾、后面什么都没有的点。

    根因是格式串无条件拼了 ` · {channel}`，而**面板按钮写的行不填 `channel`**
    （实测 83 行里全空）。与 `doctor.py` 那个吊着的「或者」同一族：
    **分隔符要跟着它分隔的东西走**，被分隔的那一半不在，分隔符就不该出现。

    这类毛病不影响正确性，只影响「这东西看着专不专业」——而它出现在
    用户每次催进度都会看的那一屏上。
    """

    def _run(self, channel: str) -> str:
        import contextlib
        import io
        import tempfile

        import followups as fu

        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            (tmp / "users" / "张三").mkdir(parents=True)
            (tmp / "users" / "张三" / "job_search_tracker.csv").write_text(
                "date,company,sector,role,role_type,channel,status,"
                "contact_person,fit_rating,notes,cv_file,cover_letter_file,"
                "source,outcome_reason\n"
                f"2026-07-01,某公司,,某岗位,,{channel},applied,,,,,,"
                "https://x/1,\n", encoding="utf-8")
            (tmp / ".active_user").write_text("张三", encoding="utf-8")
            saved = fu.ROOT
            fu.ROOT = tmp
            out = io.StringIO()
            try:
                with contextlib.redirect_stdout(out):
                    fu.main([])
            finally:
                fu.ROOT = saved
        return out.getvalue()

    def test_empty_channel_leaves_no_trailing_separator(self):
        text = self._run("")
        lines = [l for l in text.splitlines() if l.strip().startswith("·")]
        self.assertTrue(lines, f"该催的那一行没印出来：{text!r}")
        for l in lines:
            with self.subTest(line=l):
                self.assertFalse(
                    l.rstrip().endswith("·"),
                    f"渠道为空却留下了吊着的分隔符：{l!r}")

    def test_a_real_channel_still_shows(self):
        """反向：有渠道时要照常显示，别把分隔符连同内容一起删了。"""
        text = self._run("猎聘")
        self.assertIn("· 猎聘", text, f"有渠道却没显示：{text!r}")


class WhoYouChaseSplitsTheList(unittest.TestCase):
    """催猎头顾问和催企业 HR 是两件事，清单要分开。

    平铺一列 53 行是**没法照着做的**：对象不同（顾问 / HR）、能不能催也不同
    （BOSS 有聊天框，猎聘纯网申多半没有对话入口）。判据见 `followups.agency_map`。
    """

    def _run(self, jobs):
        import contextlib
        import io
        import json
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            u = tmp / "users" / "张三"
            (u / "job_scraper").mkdir(parents=True)
            (tmp / ".active_user").write_text("张三", encoding="utf-8")
            (u / "job_scraper" / "seen_jobs.json").write_text(
                json.dumps({"seen": {j["url"]: j for j in jobs}}), encoding="utf-8")
            hdr = ["date", "company", "role", "status", "notes", "channel",
                   "contact_person", "source"]
            with (u / "job_search_tracker.csv").open("w", encoding="utf-8",
                                                     newline="") as f:
                w = csv.DictWriter(f, fieldnames=hdr)
                w.writeheader()
                for j in jobs:
                    w.writerow({"date": "2026-07-01", "company": j["company"],
                                "role": "某岗", "status": "applied", "notes": "",
                                "channel": "", "contact_person": "",
                                "source": j["url"]})
                # 台账里多一条库里没有的：对不上就**不猜**，单独一组
                w.writerow({"date": "2026-07-01", "company": "手填的公司",
                            "role": "某岗", "status": "applied", "notes": "",
                            "channel": "", "contact_person": "", "source": ""})
            saved = fu.ROOT
            try:
                fu.ROOT = tmp
                buf = io.StringIO()
                with contextlib.redirect_stdout(buf):
                    fu.main(["--today", "2026-07-31", "--user", "张三"])
                return buf.getvalue()
            finally:
                fu.ROOT = saved

    JOBS = [{"url": "u1", "company": "某公司", "isHeadhunter": True},
            {"url": "u2", "company": "示例科技", "isHeadhunter": False}]

    def test_each_kind_gets_its_own_group(self):
        out = self._run(self.JOBS)
        for want in ("猎头代招", "企业直招", "拿不准是猎头还是直招"):
            self.assertIn(want, out, f"少了「{want}」这一组：{out}")

    def test_a_job_lands_in_the_right_group(self):
        """分对组才有意义——分错等于把人指向错的对象。"""
        out = self._run(self.JOBS)
        hh = out.index("猎头代招")
        direct = out.index("企业直招")
        self.assertLess(hh, out.index("某公司"), "猎头岗没落在猎头那组")
        self.assertLess(direct, out.index("示例科技"), "直招岗没落在直招那组")
        self.assertLess(out.index("某公司"), direct, "猎头岗跑到直招组后面去了")

    def test_no_empty_group_is_printed(self):
        """只有猎头时不该印一个空的「企业直招」标题。"""
        out = self._run([self.JOBS[0]])
        self.assertNotIn("企业直招", out, f"印了空组：{out}")

    def test_a_missing_job_store_does_not_crash(self):
        """库文件不在（还没抓过）也要照常出清单，只是全落到「对不上」。"""
        out = self._run([])
        self.assertIn("该催的", out)


class TheListIsOrderedByWhatIsWorthChasing(unittest.TestCase):
    """一天做不完 53 条 —— 从上往下做至少得是对的顺序。

    每条跟进 60-120 字、逐条写、不许套模板（`job-outcome.md`）。按天数平铺
    等于没有顺序，而用户没有任何依据决定先做哪几条。分数是现成的
    （实测 85 条投递 85 条取得到，50-82 分）。

    **不给「一次做几个」定数** —— 那取决于他今天有多少时间，工具不知道。
    """

    def _run(self, jobs):
        import contextlib
        import io
        import json
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            u = tmp / "users" / "张三"
            (u / "job_scraper").mkdir(parents=True)
            (tmp / ".active_user").write_text("张三", encoding="utf-8")
            (u / "job_scraper" / "seen_jobs.json").write_text(
                json.dumps({"seen": {j["url"]: j for j in jobs}}), encoding="utf-8")
            hdr = ["date", "company", "role", "status", "notes", "channel",
                   "contact_person", "source"]
            with (u / "job_search_tracker.csv").open("w", encoding="utf-8",
                                                     newline="") as f:
                w = csv.DictWriter(f, fieldnames=hdr)
                w.writeheader()
                for j in jobs:
                    w.writerow({"date": "2026-07-01", "company": j["company"],
                                "role": "某岗", "status": "applied", "notes": "",
                                "channel": "", "contact_person": "",
                                "source": j["url"]})
            saved = fu.ROOT
            try:
                fu.ROOT = tmp
                buf = io.StringIO()
                with contextlib.redirect_stdout(buf):
                    fu.main(["--today", "2026-07-31", "--user", "张三"])
                return buf.getvalue()
            finally:
                fu.ROOT = saved

    JOBS = [{"url": "u1", "company": "低分公司", "isHeadhunter": True,
             "rank_score": 51},
            {"url": "u2", "company": "高分公司", "isHeadhunter": True,
             "rank_score": 79},
            {"url": "u3", "company": "无分公司", "isHeadhunter": True}]

    def test_the_best_one_is_first(self):
        out = self._run(self.JOBS)
        self.assertLess(out.index("高分公司"), out.index("低分公司"),
                        "分高的没排在前面 —— 从上往下做就做错了顺序")

    def test_the_score_is_visible(self):
        """排了序不显示分数，用户看不出这个顺序是按什么排的。"""
        self.assertIn("79 分", self._run(self.JOBS))

    def test_a_missing_score_sinks_and_stays_blank(self):
        """取不到分数的沉底，且**不印「0 分」** —— 0 分和「不知道」是两件事。"""
        out = self._run(self.JOBS)
        self.assertLess(out.index("低分公司"), out.index("无分公司"), "没分的没沉底")
        self.assertNotIn("0 分", out, "把「取不到」印成了 0 分")

    def test_the_header_says_what_the_order_means(self):
        """顺序不说出口，等于没有 —— 他会以为还是按天数排的。"""
        self.assertRegex(self._run(self.JOBS), r"按分数从高到低|从上往下做")


if __name__ == "__main__":
    unittest.main()
