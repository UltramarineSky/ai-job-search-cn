# -*- coding: utf-8 -*-
"""被硬性条件挡住的岗，要能一眼看出是哪几道门挡的。

门名一直**是存着的**：`seen_jobs.json` 里 1136 条硬门 FAIL，1135 条带门名
（99%）。可它此前只出现在一个地方——「不投的岗位」那两千多行里、每行一个小戳的
悬浮提示。**要看清全貌得悬停一千多次**，于是这一千多个岗为什么被砍，用户根本
不知道。（2026-08-22 实测发现；同一族的前科：`channel` 存了没人读、
`isHeadhunter` 存了字段名对不上。）

全貌才指得出动作，而三档各指向完全不同的动作：

    工作年限 488（43%）  层级整体够不着 —— 该往下调层级，或核对年限按总年限还是方向年限算
    你资料里写明不要的 405  **他自己设的那份清单** —— 唯一一个想通了就能改的
    学历与院校 220       市场那边的门，改不了，但知道有两成关着比不知道强
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import export_web_data as X  # noqa: E402


def tally(*reasons):
    return {r["gate"]: r["n"] for r in
            X.gate_fail_tally([{"gateFailReason": r} for r in reasons])}


class GateFailTally(unittest.TestCase):
    def test_the_same_gate_written_three_ways_is_one_bucket(self):
        """门名是自由文本，实测 106 种写法。不归一的话表里全是长尾，读不出结论。"""
        t = tally("不满足硬性条件 (明确排除)",
                  "不满足硬性条件 (候选人明确排除)",
                  "不满足硬性条件 (明确排除（行业背景硬要求）)")
        self.assertEqual(t, {"你资料里写明不要的": 3}, f"没归成一档：{t}")

    def test_a_job_blocked_by_two_gates_still_counts_once(self):
        """一条挂两道门的按第一道算——拆开会让总数大于岗数，那一行就不再是「几个岗」。"""
        t = tally("不满足硬性条件 (工作年限 + 行业背景硬要求)")
        self.assertEqual(sum(t.values()), 1, f"一个岗被数了多次：{t}")
        self.assertIn("工作年限", t)

    def test_a_missing_gate_name_is_its_own_bucket(self):
        """漏填门名是**数据缺陷**，不是「有这么一道门」。混进「其它」就永远查不出来。"""
        t = tally("不满足硬性条件", "不满足硬性条件 (学历院校)")
        self.assertEqual(t.get("没说是哪道"), 1, f"漏填的没单列：{t}")

    def test_jobs_that_passed_are_not_counted(self):
        """只数被挡住的。没有 `gateFailReason` 的岗不进这张表。"""
        self.assertEqual(X.gate_fail_tally(
            [{"verdict": "值得投"}, {"gateFailReason": ""}]), [])

    def test_it_is_sorted_biggest_first(self):
        """倒序 —— 这一行要回答的是「主要死在哪」，最大的那一档得排在最前面。"""
        out = X.gate_fail_tally(
            [{"gateFailReason": "不满足硬性条件 (学历院校)"}]
            + [{"gateFailReason": "不满足硬性条件 (工作年限)"}] * 3)
        self.assertEqual([r["gate"] for r in out], ["工作年限", "学历与院校"])

    def test_the_panel_reads_it(self):
        """算出来没人渲染，等于又存了一份没人读的字段——这个仓库的常见死法。"""
        app = (ROOT / "web" / "src" / "App.tsx").read_text(encoding="utf-8")
        self.assertIn("gateFailTally", app, "面板没渲染这张表")
        load = (ROOT / "web" / "src" / "data" / "load.ts").read_text(encoding="utf-8")
        self.assertIn("gateFailTally", load, "快照加载时没把这个字段带进来")

    def test_the_gate_name_does_not_collide_with_the_shelf_action(self):
        """这一档挨着「不投的岗位」摆，名字里不许有「排除」。

        「排除」在这一页已经是**「不投」那个动作**的同义词。用内部门名
        「候选人明确排除」的话，用户会把它读成「我在这一页点掉的 405 个」，
        而它其实是他资料里写明不要的那些。`test_web_copy.ACTIONS` 也盯着这组词。
        """
        t = tally("不满足硬性条件 (候选人明确排除)")
        for name in t:
            self.assertNotIn("排除", name, f"台面上的门名撞了「不投」的同义词：{name}")

    def test_the_one_the_user_can_change_is_called_out_with_its_command(self):
        """那一档是他自己设的，要说出改它的命令（面板每处引导都要写命令）。"""
        app = (ROOT / "web" / "src" / "App.tsx").read_text(encoding="utf-8")
        seg = app[app.index("gateFailTally"):][:2000]
        self.assertIn("--section exclusions", seg, "没给出改排除列表的命令")
        setup = (ROOT / "workflows" / "job-setup.md").read_text(encoding="utf-8")
        self.assertRegex(setup, r"\|\s*`exclusions`\s*\|",
                         "面板印的 --section exclusions 在 job-setup 里查无此名")


class ItCountsTheSameJobsAsTheLineAboveIt(unittest.TestCase):
    """这张表就摆在成分行下面一行。**两行必须是同一批岗。**

    成分行（`shelf-tally` 第一句）按优先级把搁置区拆成五档，一个岗只进一档：

        已下线 → 你自己点的不投 → 规则判的 → 硬性条件没过 → 分太低

    分档行原来数的是「全库所有带门名的岗」，于是同一件事在相邻两行出了三个数：

        2026-08-22 实测  成分行 983 · 分档行 1001（含 14 个重复挂法）
        排掉重复挂法后    成分行 983 · 分档行 987（含 4 个他手点了不投的）

    那 4 个「手点不投 + 硬门没过」两边都算得通——**正因为都算得通，才必须钉死
    一个口径**。这一族（同一个数在两处不一样）在本仓库反复出现，判据一律是：
    挨着摆的两个数，谁在上面谁定口径。
    """

    def test_duplicates_are_not_counted(self):
        """重复挂法在页面上一行都不渲染，算进来只会让合计虚高。"""
        rows = [{"gateFailReason": "不满足硬性条件 (工作年限)"},
                {"gateFailReason": "不满足硬性条件 (工作年限)", "dupOf": "abc"}]
        self.assertEqual(sum(r["n"] for r in X.gate_fail_tally(rows)), 1)

    def test_the_two_tiers_above_it_win(self):
        """已下线、手点不投——成分行把它们归在别档，这里就不能再数一遍。"""
        for field in ("skipped", "expired"):
            with self.subTest(field=field):
                rows = [{"gateFailReason": "不满足硬性条件 (学历院校)", field: True}]
                self.assertEqual(X.gate_fail_tally(rows), [],
                                 f"`{field}` 的岗在两行里各算了一次")

    def test_the_tier_below_it_is_still_counted(self):
        """只让上面两档抢人。分太低那档在成分行里排在硬性条件**之后**，
        所以一个既没过硬门、分又低的岗归硬性条件——这里不能跟着排掉。"""
        rows = [{"gateFailReason": "不满足硬性条件 (工作年限)", "score": 12}]
        self.assertEqual(sum(r["n"] for r in X.gate_fail_tally(rows)), 1)

    def test_the_composition_line_uses_that_same_order(self):
        """口径写在两处，改一处就分叉——把成分行的顺序钉在这里。"""
        app = (ROOT / "web" / "src" / "App.tsx").read_text(encoding="utf-8")
        seg = app[app.index("shelf-tally"):][:1800]
        order = ["已下线", "你自己点的不投", "规则判的", "硬性条件没过", "分太低"]
        at = {w: seg.find(w) for w in order}
        self.assertNotIn(-1, at.values(), f"成分行少了一档：{at}")

    def test_every_shelved_job_lands_in_exactly_one_bucket(self):
        """五档要盖全搁置区——漏一档，剩下的数加起来对不上标题上那个总数。"""
        seg = (ROOT / "web" / "src" / "App.tsx").read_text(encoding="utf-8")
        i = seg.index("shelfKinds")
        # 判的顺序就是优先级，`else if` 串起来保证一个岗只落一档。
        self.assertRegex(seg[i:i + 900],
                         r"(?s)j\.expired.*else if.*j\.skipped"
                         r".*else if.*j\.ruleSkipped.*else",
                         "分档没按优先级依次判，会出现一个岗进两档")


if __name__ == "__main__":
    unittest.main()
