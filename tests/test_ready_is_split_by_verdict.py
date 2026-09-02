# -*- coding: utf-8 -*-
"""「材料备好还没投」要按判词分两档报，不能加成一个数去催人发。

2026-08-13 全面检查时发现：面板和自检都说「还有 **63** 个岗材料就绪但没投」，
而那 63 个里 **59 个的判词是「可以考虑」**，真正备好能直接发的只有 4 个。

两档的定义在 `04-job-evaluation.md` 里本来就不是一回事：

    值得投（60-74）  投，在沟通中主动补缺口      ← 一个动作
    可以考虑（45-59）先问清楚关键信息再决定      ← 一个待办

把它们加在一起，用户读到的是「63 次复制粘贴」，实际是「4 次复制粘贴 + 59 件
要先想清楚的事」。这不是数错了——两个数各自都对——是**把两种性质不同的东西
装进了同一个进度条**，而那个进度条正好是面板最显眼的一行。

这条守卫钉三件事：分档函数认得判词、两个入口都拿得到这个数、文案真的分开说。
"""

import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import build_dashboard as bd  # noqa: E402
import export_web_data as ex  # noqa: E402


class TheSplitKnowsTheBands(unittest.TestCase):
    """`is_strong` 只认「可以直接发」那两档，且容前缀后缀。"""

    def test_strong_bands(self):
        for v in ("强匹配", "值得投", "粗筛：强匹配", "粗筛：值得投"):
            with self.subTest(v=v):
                self.assertTrue(ex.is_strong(v), f"{v} 应该算可以直接发")

    def test_weak_and_out_bands(self):
        for v in ("可以考虑", "粗筛：可以考虑", "不建议", "跳过",
                  "不满足硬性条件（学历）", "硬门 FAIL (学历院校)", "", None):
            with self.subTest(v=v):
                self.assertFalse(ex.is_strong(v or ""),
                                 f"{v!r} 不该算「可以直接发」")

    def test_it_is_a_subset_of_sellable(self):
        """强档必须是可投档的子集——否则会出现「能直接发但进不了名单」的岗。"""
        for v in ex.STRONG_VERDICTS:
            self.assertIn(v, ex.SELLABLE_VERDICTS)

    def test_the_subset_holds_at_the_function_level_not_just_the_constants(self):
        """**常量是子集，不代表函数行为是子集。**

        第一版这条只比了 `STRONG_VERDICTS ⊆ SELLABLE_VERDICTS` 两个元组，绿得很稳；
        而 `is_strong` 当时写的是 `startswith`、`is_sellable` 是精确 `in`，
        于是「值得投（附条件）」这类判词 `is_strong` 真、`is_sellable` 假——
        一个岗被算进「先发这 N 个」，却根本不在那张名单里。

        判词加后缀是常事（`不满足硬性条件 (学历)` 就是这么来的），所以这里拿
        **带后缀、带前缀、新造**的判词去撞两个函数，而不是只看两个常量。
        """
        probes = [
            "值得投", "强匹配", "粗筛：值得投", "粗筛：强匹配",       # 正常
            "值得投（附条件）", "值得投 · 待确认", "强匹配（学历存疑）",   # 带后缀
            "可以考虑", "粗筛：可以考虑",                            # 弱档
            "不建议", "跳过", "不满足硬性条件（学历）", "硬门 FAIL (年限)",
            "待定", "粗筛：待定", "", "  ",                        # 新造 / 空
        ]
        for v in probes:
            with self.subTest(verdict=v):
                if ex.is_strong(v):
                    self.assertTrue(
                        ex.is_sellable(v),
                        f"{v!r} 算「可以直接发」却进不了「可以投的岗位」——"
                        f"用户会按提示去发，数得到、找不着")

    def test_doctor_matches_export_on_every_probe(self):
        """两份副本在**每一个**探针上都要给同一个答案，不能只在常见判词上一致。"""
        import doctor as dr
        for v in ("值得投", "值得投（附条件）", "粗筛：强匹配", "强匹配（学历存疑）",
                  "可以考虑", "待定", "不满足硬性条件（学历）", ""):
            with self.subTest(verdict=v):
                self.assertEqual(dr._re_strong(v), ex.is_strong(v),
                                 f"{v!r} 上两个入口不一致")

    def test_doctor_keeps_its_copy_in_sync(self):
        """`doctor` 不 import 仓库模块（它要在环境半坏时能跑），所以持一份副本。

        副本就得有人盯着，否则两个入口会对同一批岗给出不同的数。
        """
        import doctor as dr
        for v in ("值得投", "粗筛：强匹配"):
            self.assertEqual(dr._re_strong(v), ex.is_strong(v), v)
        for v in ("可以考虑", "不建议", "不满足硬性条件（年限）"):
            self.assertEqual(dr._re_strong(v), ex.is_strong(v), v)


class TheTextSaysBothNumbers(unittest.TestCase):

    def test_mixed_batch_names_both(self):
        t = bd._ready_text(63, 4)
        self.assertIn("4", t)
        self.assertIn("59", t, "另一档的条数也要说出来，否则用户以为只剩 4 个")
        self.assertIn("可以考虑", t)

    def test_all_weak_does_not_say_go_send_them(self):
        """一个「值得投」都没有时，不能催人去发——那一档的定义是先问清楚。"""
        t = bd._ready_text(59, 0)
        self.assertIn("59", t)
        self.assertIn("先问清楚", t)
        self.assertNotIn("先发这", t)

    def test_all_strong_keeps_the_plain_sentence(self):
        self.assertEqual(bd._ready_text(4, 4), bd._ready_text(4, None))

    def test_unknown_split_falls_back_instead_of_guessing(self):
        """兜底路径（数目录）读不到判词，那时只能说总数，**不许猜**。"""
        t = bd._ready_text(63, None)
        self.assertIn("63", t)
        self.assertNotIn("值得投", t)
        self.assertNotIn("可以考虑", t)


class BothEntryPointsCarryIt(unittest.TestCase):
    """面板快照要导出这个数，`doctor` 要读得到它。"""

    def test_snapshot_exports_both_counts(self):
        f = ROOT / "web" / "public" / "data.json"
        if not f.is_file():
            self.skipTest("这台机器还没跑过导出")
        ns = json.loads(f.read_text(encoding="utf-8")).get("nextStep") or {}
        self.assertIn("ready", ns, "快照没带 ready——doctor 那行读它的代码就是死的")
        self.assertIn("readyStrong", ns)
        if isinstance(ns["ready"], int) and isinstance(ns.get("readyStrong"), int):
            self.assertLessEqual(ns["readyStrong"], ns["ready"],
                                 "能直接发的不可能多于备好的总数")

    def test_count_ready_returns_a_triple(self):
        """签名是 `(总数, 其中强档, 「可以考虑」里真列了问题的)`。

        少解一个值不会报错，只会静默拿错东西 —— 所以长度要钉住。
        2026-08-13 从 1 变 2、2026-08-30 从 2 变 3，两次都是加一个
        「这句话说准了没有」所需的数。

        **读不到的那两个交回 `None`，不许猜 0**：0 的意思是「一个都没有」，
        而那时的实情是「不知道」。调用方对着 `None` 会退回不分档的旧文案，
        对着 0 会说出一句斩钉截铁的假话。
        """
        import doctor as dr
        with tempfile.TemporaryDirectory() as t:
            udir = Path(t) / "users" / "某人"
            (udir / "documents" / "applications").mkdir(parents=True)
            out = dr.count_ready(udir, {})
        self.assertIsInstance(out, tuple)
        self.assertEqual(len(out), 3)
        self.assertEqual(out[0], 0)
        self.assertIsNone(out[1], "读不到判词时第二个数要交回 None，不许猜 0")
        self.assertIsNone(out[2], "读不到那一节时第三个数要交回 None，不许猜 0")


class TheDefinitionIsWrittenDown(unittest.TestCase):
    """两档为什么不能加在一起，要写在框架里，不能只活在代码注释。"""

    def test_the_framework_defines_both_bands(self):
        t = (ROOT / "workflows" / "reference" / "04-job-evaluation.md").read_text(
            encoding="utf-8")
        self.assertIn("先问清楚", t, "「可以考虑」那一档的定义没了")
        self.assertRegex(t, r"值得投.*?投，", "「值得投」那一档的定义没了")


if __name__ == "__main__":
    unittest.main()
