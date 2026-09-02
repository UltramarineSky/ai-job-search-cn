# -*- coding: utf-8 -*-
"""同一句话，两个数：`/job-upskill` 说 607、面板说 687。

两处都用同一个 `gap_split.read_pair`、都印着「可回读两笔分数的评估 / 有完整评分的」，
而实测活动用户 2026-08-23：

    面板（`resume_insight`）  687 = 593 ranked + 14 已下线 + 80 他点掉的
    /job-upskill（`split`）   607 = 593 ranked + 14 已下线

**两个数都对**，因为两处问的不是同一个问题：

    学什么（upskill）        他没拒绝的岗在要什么 —— 拒绝掉的不该进学习计划
    市场怎么读你（面板）      市场里有多大一块对得上你 —— 他拒不拒绝不影响市场

**但两处都只说「评分」，用户只会以为其中一个坏了。** 所以各自把口径印出来。

顺带修了 `split` 那句过滤的**意思**。它原来写的是
`if e.get("status") != "ranked": continue`，注释说「只看已打分的」——
可「已打分」本来就由 `read_pair` 判（读不出两笔就 None，下一行就是）。
那句 status 过滤在偷偷多干两件事：

- **对的**：排掉他点「不投」的（80 个）。
- **错的**：连**已下线**的也排掉了（14 个）。岗位关了不等于那份技能需求消失 ——
  上个月招 Dify 的岗今天下线了，市场依然在要 Dify。为一个「还能不能投」的状态
  丢掉市场信号，是把两件事搅在一起。

改成按意思写：只排他点掉的。593 → 607。
"""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tests"))
import export_web_data as X  # noqa: E402
import gap_split as gs  # noqa: E402
from _srcscan import code_of  # noqa: E402

RREAD = (ROOT / "web" / "src" / "components"
         / "ResumeRead.tsx").read_text(encoding="utf-8")
GS = (ROOT / "tools" / "gap_split.py").read_text(encoding="utf-8")


def _e(stack, domain, **over):
    return {"rank_breakdown": {"专业能力": stack, "业务领域": domain},
            "title": "示例", **over}


class TheFilterSaysWhatItMeans(unittest.TestCase):
    def test_scored_is_decided_by_read_pair(self):
        """判「已打分」的是 `read_pair`，不是 status。

        **只扫代码。** docstring 里逐字引着旧写法 `!= "ranked"`（那正是这条
        要保住的那段说明），连注释一起扫等于禁止把理由写下来 ——
        这个坑本仓库栽过七次以上，修法收在 `tests/_srcscan.py`。
        """
        seg = code_of("tools/gap_split.py", "def split(")
        self.assertIn("read_pair(e)", seg)
        self.assertNotIn('!= "ranked"', seg, "又按实现状态过滤了")

    def test_only_what_he_rejected_is_dropped(self):
        self.assertEqual(len(gs.split({"a": _e(85, 30, status="skipped")})[gs.PICK]), 0)
        self.assertEqual(len(gs.split({"a": _e(85, 30, status="expired")})[gs.PICK]), 1)
        self.assertEqual(len(gs.split({"a": _e(85, 30, status="ranked")})[gs.PICK]), 1)

    def test_junk_rows_do_not_crash_it(self):
        self.assertEqual(sum(len(v) for v in gs.split({"a": None, "b": 3}).values()), 0)

    def test_the_reason_for_keeping_closed_jobs_is_written_down(self):
        """这一条看起来像遗漏（「下线的岗还算它干嘛」），理由必须挨着写。"""
        seg = GS[GS.index("def split("):GS.index("def verdict(")]
        self.assertRegex(seg, r"岗位关了不等于|需求消失",
                         "没写清为什么已下线的还留着")


class EachSideNamesItsCorpus(unittest.TestCase):
    def test_the_cli_prints_its_scope(self):
        self.assertRegex(GS, r"评过分、你没点掉的",
                         "终端那行没说清它数的是哪一批")

    def test_the_scope_slot_is_not_clobbered_by_applied_mode(self):
        """`--applied` 有自己的口径说明（「只算投过的那批」），
        默认那句不许把它盖掉。"""
        i = GS.index('scope = "（只算投过的那批）"')
        j = GS.index("if not scope:")
        self.assertLess(i, j, "默认口径写在了 --applied 之前，会把它冲掉")

    def test_the_panel_prints_its_scope(self):
        i = RREAD.index("有完整评分的")
        self.assertRegex(RREAD[i:i + 300], r"含你点过「不投」的",
                         "面板那句没说清它把拒绝掉的也算了进来")

    def test_the_panel_says_why_that_is_right(self):
        """只说「含点掉的」是个事实，读者会以为那是 bug。要说出为什么该含。"""
        i = RREAD.index("有完整评分的")
        self.assertRegex(RREAD[i:i + 300], r"市场是什么样不因为你拒绝而改变|不影响市场")


class OnRealDataTheGapIsExactlyTheRejected(unittest.TestCase):
    def test_the_two_populations_differ_only_by_what_he_rejected(self):
        p = ROOT / ".active_user"
        if not p.is_file():
            self.skipTest("没有活动用户")
        ud = ROOT / "users" / p.read_text(encoding="utf-8").strip()
        sj = ud / "job_scraper" / "seen_jobs.json"
        if not sj.is_file():
            self.skipTest("还没抓过职位")
        raw = json.loads(sj.read_text(encoding="utf-8"))
        seen = raw.get("seen", raw)
        pairs = [v for v in seen.values()
                 if isinstance(v, dict) and gs.read_pair(v)]
        if len(pairs) < 50:
            self.skipTest("语料太少，比不出什么")
        panel = len(pairs)                       # resume_insight 不排任何状态
        cli = sum(len(v) for v in gs.split(seen).values())
        rejected = sum(1 for v in pairs if v.get("status") == "skipped")
        self.assertEqual(panel - cli, rejected,
                         f"面板 {panel}、命令行 {cli}，差额不等于你点掉的 {rejected}")

    def test_the_panel_side_really_counts_everything(self):
        """`resume_insight` 一旦也开始按状态过滤，上面那条就悄悄失去意义。"""
        src = (ROOT / "tools" / "export_web_data.py").read_text(encoding="utf-8")
        i = src.index("def resume_insight(")
        seg = src[i:src.index("\ndef ", i + 10)]
        head = seg[:seg.index("if dm_ >= SWEET_SPOT_DOMAIN")]
        self.assertNotIn('"skipped"', head,
                         "市场统计开始排除他拒绝的岗了 —— 那就不是市场了")


if __name__ == "__main__":
    unittest.main()
