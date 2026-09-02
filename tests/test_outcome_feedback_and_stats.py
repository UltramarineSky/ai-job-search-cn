# -*- coding: utf-8 -*-
"""投出去之后：反馈在页面上填，统计自己算出来。

用户 2026-08-13 提了三件事，每一件都决定了一处设计：

1. **「`/job-outcome <公司>` 这个格式过低」** —— 记一笔不该回命令行敲公司名。
   页面上早就有状态按钮，缺的是**原因**。
2. **「很多是没反馈也就不会填」** —— 这句是整个设计的支点。沉默**不产生事件**：
   没有邮件、没有电话、没有状态变化。要求用户手动记「这个没回我」，等于让他为
   「什么都没发生」每周点几十次，而那正是他不会做的事。所以「大概率没戏」
   **按投递日期算出来**，不问用户。
3. **「有些直接明确拒绝，也没具体理由」** —— 所以原因**永远可选**，且第一个
   选项就是「没说原因」。它不是必经步骤，是记完状态之后愿意补才补。
"""

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import tracker as tk  # noqa: E402


class ReasonIsOptionalAndTyped(unittest.TestCase):

    def test_first_option_is_no_reason_given(self):
        """最常见的情况要排第一个——多数拒信不说理由。"""
        self.assertEqual(tk.REASONS[0][0], "no_reason")
        self.assertIn("没说原因", tk.REASONS[0][1])

    def test_reasons_are_a_closed_list(self):
        """做成固定选项才统计得出来；自由文本汇不成分布。"""
        self.assertGreaterEqual(len(tk.REASONS), 6)
        self.assertIn("other", dict(tk.REASONS), "得留一个「其它」给真给了理由的少数情况")

    def test_writing_a_reason_migrates_an_old_csv(self, ):
        """存量台账没有 outcome_reason 列——写的时候要**自己补上**。

        少这一步，`save()` 按旧 cols 写盘，值被静默丢掉：接口报成功、盘上没有。
        """
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "t.csv"
            p.write_text("date,company,role,status,notes,source\n"
                         "2026-08-01,甲,乙,applied,,https://x/1\n", encoding="utf-8")
            cols, rows = tk.load(p)
            self.assertNotIn("outcome_reason", cols)
            r = tk.set_status(p, rows[0], {"company": "甲", "title": "乙",
                                           "url": "https://x/1"},
                              "rejected", "2026-08-13", reason="salary")
            self.assertTrue(r["ok"])
            cols2, rows2 = tk.load(p)
            self.assertIn("outcome_reason", cols2, "旧文件没补列，值会被丢掉")
            self.assertEqual(rows2[0]["outcome_reason"], "salary")
            self.assertIn("薪资谈不拢", rows2[0]["notes"], "notes 里没留人话")

    def test_no_reason_still_writes_the_status(self):
        """不填原因是**正常路径**，不能因此拒绝写状态。"""
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "t.csv"
            p.write_text("date,company,role,status,notes,source\n"
                         "2026-08-01,甲,乙,applied,,https://x/1\n", encoding="utf-8")
            cols, rows = tk.load(p)
            r = tk.set_status(p, rows[0], {"company": "甲", "title": "乙",
                                           "url": "https://x/1"},
                              "rejected", "2026-08-13")
            self.assertTrue(r["ok"])
            self.assertEqual(tk.load(p)[1][0]["status"], "rejected")


class UndoTakesTheReasonWithIt(unittest.TestCase):
    """撤销要把**原因**一起撤掉，不能只退状态。

    2026-08-13 实测：点「挂了」选原因「简历没过」→ 点「撤销」→
    状态回到 `applied`，而 `outcome_reason` 还留着 `resume`。
    一条「已投递」却带着拒绝原因的记录：`outcome_stats()` 数拒绝原因分布时
    会把它算进去，用户回看台账也讲不通。

    根因是**加列时只改了写入侧**（`set_status` 会补列、会写值），
    撤销侧（`undo`）根本不知道有这一列——面板上那颗按钮声称「可撤销」，
    撤的却只有一半。
    """

    def _csv(self, d):
        p = Path(d) / "t.csv"
        p.write_text("date,company,role,status,notes,source\n"
                     "2026-08-01,甲,乙,applied,,https://x/1\n", encoding="utf-8")
        return p, {"company": "甲", "title": "乙", "url": "https://x/1"}

    def test_undo_clears_the_reason(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            p, job = self._csv(d)
            row = tk.load(p)[1][0]
            r = tk.set_status(p, row, job, "rejected", "2026-08-13", reason="resume")
            self.assertEqual(tk.load(p)[1][0]["outcome_reason"], "resume")
            row = tk.load(p)[1][0]
            self.assertTrue(tk.undo(p, row, r["prev"], "2026-08-13")["ok"])
            back = tk.load(p)[1][0]
            self.assertEqual(back["status"], "applied", "状态没退回去")
            self.assertEqual((back.get("outcome_reason") or "").strip(), "",
                             "状态退回了，拒绝原因却还留着——一条「已投递」带着拒绝理由")

    def test_undo_of_a_new_row_still_deletes_it(self):
        """`prev is None`（页面刚建的行）那条路不受影响：整行删掉。"""
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "t.csv"
            p.write_text("date,company,role,status,notes,source\n", encoding="utf-8")
            job = {"company": "甲", "title": "乙", "url": "https://x/1"}
            r = tk.set_status(p, None, job, "applied", "2026-08-13")
            self.assertIsNone(r["prev"])
            row = tk.load(p)[1][0]
            out = tk.undo(p, row, r["prev"], "2026-08-13")
            self.assertTrue(out["ok"])
            self.assertTrue(out["deleted"])
            self.assertEqual(tk.load(p)[1], [], "刚建的行该被整行删掉")

    def test_undo_restores_every_column_except_the_notes_trail(self):
        """**守整类错，不只 outcome_reason 这一列。**

        「加列时只改写入侧、漏掉撤销侧」是结构性风险：`set_status` 和 `undo`
        是两条代码路径，改前者的人看不见后者。上面那条测试钉的是已经踩过的
        那一列；这条把不变式本身钉死——对已有行 set → undo 之后，
        **除 notes（撤销要留痕）外，每一列都必须回到 set 之前的值**。
        以后任何新列写了忘撤，不用等有人在面板上点出脏数据，这里当场红。
        """
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "t.csv"
            p.write_text("date,company,role,status,notes,source\n"
                         "2026-08-01,甲,乙,applied,,https://x/1\n", encoding="utf-8")
            before = dict(tk.load(p)[1][0])
            job = {"company": "甲", "title": "乙", "url": "https://x/1"}
            r = tk.set_status(p, tk.load(p)[1][0], job, "rejected", "2026-08-13",
                              reason="salary")
            row = tk.load(p)[1][0]
            self.assertTrue(tk.undo(p, row, r["prev"], "2026-08-13")["ok"])
            after = dict(tk.load(p)[1][0])
            drift = {k for k in set(before) | set(after)
                     if k != "notes"
                     and (before.get(k) or "").strip() != (after.get(k) or "").strip()}
            self.assertEqual(drift, set(),
                             f"撤销后这些列没回到原值：{drift} —— "
                             "多半是新列只改了写入侧、漏了撤销侧")

    def test_terminal_states_cannot_be_left(self):
        """清空原因之所以安全，靠的是这条：终结态出不去。

        所以一行的 `outcome_reason` 只可能来自**刚被撤销的那一次** `set_status`，
        不存在「撤销后该恢复成上一个原因」的情形。这条断言就是那个前提——
        哪天终结态之间可以互相转移了，上面那个「无条件清空」就得重新想。
        """
        for terminal in ("rejected", "ghosted"):
            reachable = [s for s in ("applied", "interview", "offer",
                                     "rejected", "ghosted", "hired")
                         if tk.can_go(terminal, s)]
            self.assertEqual(reachable, [],
                             f"{terminal} 现在能走到 {reachable}——"
                             "undo 里那句「无条件清空原因」的前提没了")


class SilenceIsComputedNotAsked(unittest.TestCase):

    def test_the_threshold_exists_and_is_explained(self):
        src = (ROOT / "tools" / "export_web_data.py").read_text(encoding="utf-8")
        self.assertIn("SILENT_DAYS", src)
        self.assertIn("不问用户", src, "没写清为什么不让用户填——下一个人会把它改成必填")

    def test_stats_ship_in_the_snapshot(self):
        f = ROOT / "web" / "public" / "data.json"
        if not f.is_file():
            self.skipTest("没有面板快照")
        d = json.loads(f.read_text(encoding="utf-8"))
        s = d.get("outcomeStats")
        if not s:
            self.skipTest("这份快照是旧的，跑一次 export_web_data.py")
        for k in ("total", "buckets", "repliedRate", "byBand", "reasons", "silentDays"):
            with self.subTest(key=k):
                self.assertIn(k, s)
        self.assertTrue(d.get("outcomeReasons"), "原因词表没送到前端，芯片会渲染不出来")

    def test_the_panel_renders_it(self):
        tsx = (ROOT / "web" / "src" / "components" / "OutcomeStats.tsx").read_text(encoding="utf-8")
        self.assertIn("大概率没戏", tsx)
        self.assertIn("不用你去点", tsx, "没告诉用户这个数是算出来的，他会以为自己漏填了")
        app = (ROOT / "web" / "src" / "App.tsx").read_text(encoding="utf-8")
        self.assertIn("OutcomeStatsPanel", app, "组件没挂上，写了等于没写")

    def test_reason_chips_do_not_block_the_status(self):
        """原因是**记完之后**才出现的，不能挡在状态按钮前面。"""
        tsx = (ROOT / "web" / "src" / "components" / "JobReadout.tsx").read_text(encoding="utf-8")
        self.assertIn("marked && marked.value === \"rejected\"", tsx,
                      "原因那排不是挂在「已记下」之后的——它会变成必经步骤")
        self.assertIn("可以不填", tsx)


if __name__ == "__main__":
    unittest.main()


class TheBucketsAddUp(unittest.TestCase):
    """分桶是算术，必须自洽——**每个投递恰好落一个桶**。

    现有守卫覆盖了写入、撤销、终态、阈值、渲染，唯独没验算术。
    分桶用的是 if/elif 链（约面 / 被拒 / 撤回 / 没下文 / 超时没动静 / 还在等），
    改一条分支就可能漏掉或重复计一类——而页面只显示各桶的数，
    **加起来对不上总数这件事，肉眼永远看不出来**。
    """

    def _stats(self, jobs):
        import export_web_data as ex
        return ex.outcome_stats(jobs, [])

    def test_every_applied_job_lands_in_exactly_one_bucket(self):
        import export_web_data as ex
        jobs = [
            {"applied": {"status": "interview", "date": "2026-08-19"}, "score": 70},
            {"applied": {"status": "offer", "date": "2026-08-19"}, "score": 70},
            {"applied": {"status": "rejected", "date": "2026-08-19"}, "score": 55},
            {"applied": {"status": "withdrawn", "date": "2026-08-19"}, "score": 55},
            {"applied": {"status": "no response", "date": "2026-08-19"}, "score": 45},
            {"applied": {"status": "applied", "date": "2000-01-01"}, "score": 45},  # 超时
            {"applied": {"status": "applied", "date": "2026-08-19"}, "score": 65},  # 还在等
            {"applied": {"status": "applied"}, "dupOf": "x", "score": 65},          # 重复挂法，不算
            {"score": 80},                                                          # 没投，不算
        ]
        s = ex.outcome_stats(jobs, [])
        self.assertEqual(s["total"], 7, "重复挂法或没投的岗被算进总数了")
        self.assertEqual(sum(b["n"] for b in s["buckets"]), s["total"],
                         f"各桶之和 != 总数：{s['buckets']}")

    def test_band_counts_only_include_decidable_replies(self):
        """撤回的岗 `replied` 是 None——它不该进按分数段的分母。"""
        import export_web_data as ex
        jobs = [
            {"applied": {"status": "withdrawn", "date": "2026-08-19"}, "score": 70},
            {"applied": {"status": "interview", "date": "2026-08-19"}, "score": 70},
        ]
        s = ex.outcome_stats(jobs, [])
        sent = sum(b["sent"] for b in s["byBand"])
        self.assertEqual(sent, 1, "撤回的岗被算进了回复率的分母")

    def test_real_export_is_self_consistent(self):
        """控制测试：真实导出里各桶之和必须等于总数。"""
        f = ROOT / "web" / "public" / "data.json"
        if not f.is_file():
            self.skipTest("还没导出过")
        s = json.loads(f.read_text(encoding="utf-8")).get("outcomeStats") or {}
        if not s:
            self.skipTest("还没有投递")
        self.assertEqual(sum(b["n"] for b in s["buckets"]), s["total"],
                         f"真实数据里各桶之和对不上总数：{s['buckets']} vs {s['total']}")
        sent = sum(b["sent"] for b in s.get("byBand") or [])
        self.assertLessEqual(sent, s["total"], "按分数段的投递数超过了总投递数")
