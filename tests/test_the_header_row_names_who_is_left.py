# -*- coding: utf-8 -*-
"""「抬头没说清在跟谁说话」那一行原来只有一个数字。

## 实测

2026-08-30 的收尾里，那一行整句是：

    4 份没写是猎头还是 HR 直招。第二轮怎么说话完全取决于这半句（…见 06
    「渠道判定」那张表）。

**不点名、不给命令、也没说这 4 份还动不动得了。** 而同一份报告里其余几条
早就走 `_cli.live_tail`（点名还能发的那几个 + 给出该敲的命令），
这一条是漏网的。`AGENTS.md`「每一处引导都要写出该敲的命令」管的正是它。

接上 `live_tail` 之后当场看出来：**那 4 份全都已经投出去或标了不投**，
于是这一行自报「补它没有意义」，按收尾的逐行过滤自动退出可操作层
（6 条 → 5 条）。一条读了做不了任何事的行，本来就不该占那个位置。

## 为什么不给一个机械修法

实测同日：判不出渠道的 11 份里 **11 份连详情库记录都没有** ——
`isHeadhunter` / `recruiter` / `recruiterTitle` 三个字段在职位库和详情库
两边全空，而 `jd_store.MERGE_FIELDS` 三个都带着。**无米可炊，不是回填断了。**
抓取当次没取到招聘者，事后只能开页面看，那正是 `/job-apply` 第 1.5 步做的事。
"""
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tests"))
from _srcscan import code_of  # noqa: E402
import _cli  # noqa: E402
import audit_pipeline as ap  # noqa: E402

FN = "def check_outreach_header_says_who_youre_talking_to("


class TheRowCanNameAndCommand(unittest.TestCase):

    def test_it_collects_the_link_not_just_the_folder_name(self):
        """只存目录名前缀的话，既点不了名也给不了命令。"""
        seg = code_of("tools/audit_pipeline.py", FN)
        self.assertIn("_kind_live.append", seg)

    def test_it_goes_through_the_shared_tail(self):
        """判定「还发不发得出去」和那条命令都只有一份实现。"""
        seg = code_of("tools/audit_pipeline.py", FN)
        self.assertIn("live_tail(user, seen, _kind_live", seg)

    def test_it_says_why_there_is_no_mechanical_fix(self):
        """不写这句，下一个人会去找那个并不存在的回填断点。"""
        seg = code_of("tools/audit_pipeline.py", FN)
        self.assertIn("两边都空", seg)


class ARowWithNothingLeftDropsOutOfTheClosing(unittest.TestCase):
    """收尾只放「他现在动得了」的事 —— 逐行过滤靠的就是那句话。"""

    def _rows(self):
        ptr = ROOT / ".active_user"
        if not ptr.is_file():
            self.skipTest("没有活动用户")
        user = ptr.read_text(encoding="utf-8").strip()
        f = ROOT / "users" / user / "job_scraper" / "seen_jobs.json"
        if not f.is_file():
            self.skipTest("没有职位库")
        seen, details = ap.load(user)
        return ap.check_outreach_header_says_who_youre_talking_to(seen, details)

    def test_the_row_carries_a_filterable_verdict(self):
        """要么点出还能补的那几个，要么明说一个都动不了 —— 不许两头都不沾。"""
        rows = [r for r in self._rows() if "没说清在跟谁说话" in r[1]]
        if not rows:
            self.skipTest("这台机器上这一行没出现")
        msg = rows[0][2]
        ok = (_cli.NO_LIVE in msg) or ("/job-apply" in msg)
        self.assertTrue(ok, "这一行既没点名、也没说一个都动不了：\n  " + msg[:200])

    def test_the_actionable_tier_drops_it_when_nothing_is_left(self):
        ptr = ROOT / ".active_user"
        if not ptr.is_file():
            self.skipTest("没有活动用户")
        user = ptr.read_text(encoding="utf-8").strip()
        rows = [r for r in self._rows() if "没说清在跟谁说话" in r[1]]
        if not rows or _cli.NO_LIVE not in rows[0][2]:
            self.skipTest("这一行现在还有活可干 —— 那它就该留在收尾里")
        got = ap.run(user, actionable=True)
        self.assertNotIn("话术抬头没说清在跟谁说话", [t for _s, t, _m in got],
                         "一个都动不了的行还留在收尾里")


if __name__ == "__main__":
    unittest.main()
