# -*- coding: utf-8 -*-
"""同一个缺陷占了两行时，报告要自己说出来 —— 而不是给两条命令。

## 实测

活动用户 2026-08-30：

    有分数没拆解（职位库里没有「技能与经验」）   11 个
    深评缺小节里的「评分明细」                  11 份
    两者交集                                   11
    只在库里缺 / 只在文件里缺                    0 / 0

**同一个缺陷的两个症状**：那一次深评没出评分明细表，于是文件里少那一节、
回写进职位库的 `rank_breakdown` 里也少那四维。

## 那该怎么办

不是合并这两条检查 —— 它们查的是**两个存储**（职位库 vs 深评文件），
今天完全重合是实测结果，不是保证。哪天只有一边缺，那才是新信息。

而是：**只有一条给命令**。收尾里出现两条可执行项、指向同一批岗，
读的人会以为要做两遍。「深评缺小节」那条本来就点名了还补得上的那几个，
这条只报数并指过去。

判据不是「文案里写了那句话」，是**行为**：这条不许调 `sendable_state`
（`--actionable` 的准入判据，见 `run()`），而重合数得**算出来**，
不是写死在句子里。
"""
import json
import pathlib
import sys
import unittest
import unittest.mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tests"))
from _live import user_or_skip  # noqa: E402
from _srcscan import code_of  # noqa: E402
import _cli  # noqa: E402
import audit_pipeline as ap  # noqa: E402


class OnlyOneRowCarriesTheCommand(unittest.TestCase):

    def test_it_stays_out_of_the_actionable_tier(self):
        """进那一档就会在收尾里多出一条指向同一批岗的可执行项。"""
        seg = code_of("tools/audit_pipeline.py",
                      "def check_scored_without_dims(")
        for name in ("sendable_state", "live_tail"):
            with self.subTest(name=name):
                self.assertNotIn(name, seg,
                                 "它进了可操作层 —— 同一批岗会被催两遍")

    #: 一个「有分数、拆解里只有元数据」的岗。链接是假的，所以
    #: `_also_missing_the_section` 在真盘上找不到它 —— 重合数由下面各条自己打桩。
    ONE = {"1": {"url": "https://x/1", "rank_score": 60,
                 "rank_verdict": "可以考虑", "rank_breakdown": {"依据": "x"}}}

    def test_it_points_at_the_row_that_does(self):
        with unittest.mock.patch.object(ap, "_also_missing_the_section",
                                        lambda _urls: 1):
            out = ap.check_scored_without_dims(self.ONE)
        self.assertTrue(out)
        self.assertIn("深评缺小节", out[0][2],
                      "没说清这批和哪一条是同一批")
        self.assertIn("别做两遍", out[0][2])

    def test_the_overlap_is_computed_not_asserted(self):
        """写死一个数就是把实测结果冻成断言 —— 它会过期。"""
        seg = code_of("tools/audit_pipeline.py",
                      "def check_scored_without_dims(")
        self.assertIn("_also_missing_the_section", seg)

    def test_the_overlap_borrows_the_shared_judge(self):
        """「缺哪几节」只有一份实现。"""
        seg = code_of("tools/audit_pipeline.py",
                      "def _also_missing_the_section(")
        self.assertIn("missing_sections(", seg)

    def test_it_says_something_different_when_they_diverge(self):
        """只在库里缺的时候，那句话必须换个说法 —— 否则就是撒谎。

        沙箱里给一个库里缺、而文件那边压根找不到的岗：重合数是 0，
        句子应该说「是回写那一跳没把四维带进库」。
        """
        user_or_skip()   # 没有真实数据可读时 skip（见 tests/_live.py）
        out = ap.check_scored_without_dims({
            "1": {"url": "https://not-in-any-dir/xyz", "rank_score": 60,
                  "rank_verdict": "可以考虑", "rank_breakdown": {"依据": "x"}}})
        self.assertIn("回写那一跳", out[0][2])
        # 第三种：一半一半 —— 句子要把两半分开说
        with unittest.mock.patch.object(ap, "_also_missing_the_section",
                                        lambda _urls: 1):
            half = ap.check_scored_without_dims({
                "1": self.ONE["1"],
                "2": {"url": "https://x/2", "rank_score": 61,
                      "rank_verdict": "可以考虑",
                      "rank_breakdown": {"依据": "y"}}})
        self.assertIn("其中 1 个", half[0][2])
        self.assertIn("另外 1 个", half[0][2])
        self.assertNotIn("别做两遍", out[0][2])

    def test_gate_fail_jobs_are_still_out(self):
        """硬门 FAIL 的按 04 本来就不打分，不算缺拆解。"""
        self.assertEqual(ap.check_scored_without_dims({
            "1": {"url": "https://x/1", "rank_score": 0,
                  "rank_verdict": "硬门 FAIL（学历）", "rank_breakdown": {}}}), [])


class TheyReallyDoOverlapRightNow(unittest.TestCase):
    """控制用例：这台机器上两边真的是同一批岗 —— 否则上面全是空谈。"""

    def test_the_two_sets_are_the_same(self):
        ptr = ROOT / ".active_user"
        if not ptr.is_file():
            self.skipTest("没有活动用户")
        user = ptr.read_text(encoding="utf-8").strip()
        f = ROOT / "users" / user / "job_scraper" / "seen_jobs.json"
        apps = ROOT / "users" / user / "documents" / "applications"
        if not (f.is_file() and apps.is_dir()):
            self.skipTest("没有语料")
        seen = _cli.seen_of(json.loads(f.read_text(encoding="utf-8")))
        a = {_cli.norm_url(e.get("url") or "") for e in seen.values()
             if isinstance(e, dict) and isinstance(e.get("rank_score"), int)
             and not str(e.get("rank_verdict") or "").startswith("硬门")
             and "技能与经验" not in (e.get("rank_breakdown") or {})}
        a.discard("")
        if not a:
            self.skipTest("这台机器上一个都没有")
        dirs = ap.dir_urls(user)
        b = set()
        for ev in sorted(apps.glob("*/evaluation.md")):
            gone = ap.missing_sections(
                ev.read_text(encoding="utf-8", errors="replace"))
            if gone and "评分明细" in gone:
                b.add(_cli.norm_url(dirs.get(ev.parent.name, "")))
        b.discard("")
        # 不断言完全相等 —— 那会把实测冻成契约。断言的是**报告说的和实际一致**：
        # 重合数算得对。
        self.assertEqual(ap._also_missing_the_section(a), len(a & b))


if __name__ == "__main__":
    unittest.main()
