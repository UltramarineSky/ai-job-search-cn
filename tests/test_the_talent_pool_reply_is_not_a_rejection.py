# -*- coding: utf-8 -*-
"""国内 HR 极少写「拒绝」两个字，而那套委婉说法全仓一个都没有。

全仓搜（2026-08-24，`workflows/` + `tools/`）：

    人才库    0 命中
    保持联系  0 命中
    再联系    0 命中
    婉拒      0 命中
    暂时搁置  0 命中

而 `job-gmail-sync.md` 的分类表已经很认真地把明拒的中文措辞列全了
（「很遗憾」「暂不合适」「未能进入下一轮」「另作安排」「祝您求职顺利」）——
**唯独漏了国内最常见的那一种**：

> 您的简历已进入我们人才库，后续有合适岗位会第一时间联系您。

后果是双向的：认不出来 → 那次投递一直挂在「还在等」，面板还在劝他去催；
认成拒信 → 原因那一格落到「简历没过」，而他会去重写一份没问题的简历。

## 三档，不是两档

    明拒    你不合适          → 原因是简历 / 年限 / 学历……
    软拒    这个岗没 HC 了 / 已经定了人，但你留着 → **不是简历的问题**
    岗位关了 这个岗不招了      → 别再看这家这个岗

软拒和「岗位关了」也不是一回事：前者是「招了别人，但你留着」，
后者是「这个岗没了」—— 对下一步的含义不同（大厂 HC 解冻后回捞是真事）。

## 只认，不动手

`job-gmail-sync` 自己的铁律 4：「拿不准就别提议——摆出来。」
软拒正是那一类：它对这一个岗基本终结，但记 `rejected` 还是 `no response`
得他自己定。所以这一行**不自动改状态**。
"""
import pathlib
import re
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import tracker as tk  # noqa: E402

GM = (ROOT / "workflows" / "job-gmail-sync.md").read_text(encoding="utf-8")
TRK = (ROOT / "tools" / "tracker.py").read_text(encoding="utf-8")


def flat(s: str) -> str:
    s = " ".join(re.sub(r"^\s*(?:>|#:?)\s?", "", s, flags=re.M).split())
    return re.sub(r"(?<=[一-鿿，。；：、（）「」])"
                  r" +(?=[一-鿿，。；：、（）「」])", "", s)


class TheReasonExists(unittest.TestCase):
    def test_it_is_in_the_list(self):
        self.assertIn("talent_pool", dict(tk.REASONS))

    def test_it_reads_as_plain_chinese(self):
        self.assertEqual(tk.REASON_LABEL["talent_pool"], "进了人才库/让保持联系")

    def test_it_is_not_merged_into_the_resume_bucket(self):
        """**这是它存在的全部理由。** 并进去他会重写一份没问题的简历。"""
        self.assertIn("resume", dict(tk.REASONS))
        self.assertNotEqual(tk.REASON_LABEL["talent_pool"],
                            tk.REASON_LABEL["resume"])

    def test_it_is_not_merged_into_closed_either(self):
        """「这个岗不招了」和「招了别人但你留着」对下一步的含义不同。"""
        self.assertIn("closed", dict(tk.REASONS))
        self.assertNotEqual(tk.REASON_LABEL["talent_pool"],
                            tk.REASON_LABEL["closed"])

    def test_the_catch_all_still_sits_last(self):
        """「其它」要留在最后一档 —— 它是兜底，不是并列选项。"""
        self.assertEqual(tk.REASONS[-1][0], "other")

    def test_no_reason_still_sits_first(self):
        self.assertEqual(tk.REASONS[0][0], "no_reason")

    def test_the_reason_is_recorded(self):
        i = TRK.index('("talent_pool"')
        seg = flat(TRK[max(0, i - 1300):i])
        self.assertRegex(seg, r"国内最常见的那种「不算拒绝的拒绝」")
        self.assertRegex(seg, r"为什么不并进「简历没过」")
        self.assertRegex(seg, r"也不并进「岗位关了」")
        self.assertIn("2026-08-24", seg)

    def test_the_panel_does_not_hardcode_it(self):
        """前端那份下拉来自 `tracker.REASONS` —— 加一档不该要改前端。"""
        jr = (ROOT / "web" / "src" / "components"
              / "JobReadout.tsx").read_text(encoding="utf-8")
        self.assertNotIn("talent_pool", jr)

    def test_the_server_accepts_it(self):
        """服务端按 `REASON_LABEL` 校验 —— 加进词表就自动放行，别另开白名单。"""
        srv = (ROOT / "tools" / "serve.py").read_text(encoding="utf-8")
        self.assertIn("tracker.REASON_LABEL", srv)


class TheMailTableRecognisesIt(unittest.TestCase):
    def _row(self) -> str:
        return next(l for l in GM.splitlines() if l.startswith("| **软拒**"))

    def test_the_row_exists(self):
        self.assertTrue(self._row())

    def test_it_lists_the_actual_wording(self):
        """只写「软拒」两个字，执行者认不出任何一封真邮件。"""
        r = self._row()
        for w in ("人才库", "保持联系", "暂时搁置"):
            with self.subTest(w=w):
                self.assertIn(w, r)

    def test_it_covers_the_english_too(self):
        """这张表本来就是中英双列 —— 投外企时那套说法也一样。

        这两句英文让 `test_workflow_prose_is_chinese` 的 `RUN_BUDGET` 从 1
        调到了 3 —— **那份预算写着「只许改小」，这是它第一次往上调**，
        理由记在那边（同一张表、同一列、同一类匹配串；散文一个字没多）。
        """
        self.assertIn("keep your resume on file", self._row())

    def test_raising_that_ratchet_was_written_down(self):
        """往上调一个「只许改小」的预算，理由必须留在被调的那一处。"""
        t = (ROOT / "tests"
             / "test_workflow_prose_is_chinese.py").read_text(encoding="utf-8")
        i = t.index('"job-gmail-sync.md": 3,')
        seg = flat(t[max(0, i - 1400):i])
        self.assertRegex(seg, r"这是这份预算第一次往上调")
        self.assertRegex(seg, r"只对「同一张表里同类的匹配串」成立")
        self.assertRegex(seg, r"散文一个字都没多")

    def test_it_does_not_auto_change_the_status(self):
        """铁律 4：拿不准就别提议 —— 摆出来。"""
        r = self._row()
        self.assertIn("不自动改", r)
        self.assertIn("信号打架，要你自己判断", r)

    def test_it_names_the_reason_to_record(self):
        r = self._row()
        self.assertIn("talent_pool", r)

    def test_the_bucket_it_points_at_exists(self):
        """指一个不存在的小节，这一行就落空了。"""
        self.assertIn("### 信号打架，要你自己判断", GM)

    def test_the_hard_rejection_row_is_untouched(self):
        """这一行是加的，明拒那一行一个字不许动。"""
        r = next(l for l in GM.splitlines() if l.startswith("| 拒信 |"))
        for w in ("很遗憾", "暂不合适", "未能进入下一轮", "祝您求职顺利"):
            with self.subTest(w=w):
                self.assertIn(w, r)
        self.assertIn("`rejected`", r)


class TheDifferenceIsSpelledOut(unittest.TestCase):
    def _seg(self) -> str:
        i = GM.index("> ⚠️ **软拒不是拒信的同义词")
        return flat(GM[i:GM.index("**信号短语中文在前。**", i)])

    def test_it_says_what_happens_if_unrecognised(self):
        s = self._seg()
        self.assertRegex(s, r"一直挂在「还在等」里")
        self.assertRegex(s, r"面板还在劝他去催")

    def test_it_says_what_happens_if_called_a_rejection(self):
        """这半句才是「为什么不能直接当拒信」的答案。"""
        s = self._seg()
        self.assertRegex(s, r"重写一份没问题的简历")
        self.assertRegex(s, r"照着错的诊断动刀")

    def test_it_contrasts_the_two_on_three_axes(self):
        s = self._seg()
        for w in ("说的是什么", "原因那一格", "下一步"):
            with self.subTest(w=w):
                self.assertIn(w, s)

    def test_it_says_the_soft_one_is_worth_revisiting(self):
        """这是它和明拒在**行动**上唯一的区别。"""
        self.assertRegex(self._seg(), r"隔一阵值得回来看")

    def test_it_carries_the_zero_hit_measurement(self):
        s = self._seg()
        self.assertIn("2026-08-24", s)
        self.assertRegex(s, r"一个都没有")

    def test_it_defers_to_the_commands_own_rule(self):
        """不新立规矩 —— 这一类本来就归铁律 4 管。"""
        self.assertRegex(self._seg(), r"拿不准就别提议——摆出来")

    def test_that_rule_still_exists(self):
        self.assertRegex(flat(GM), r"\*\*拿不准就别提议——摆出来。\*\*")


class TheSignalItLeansOnIsReal(unittest.TestCase):
    """现算：这套说法此前真的一处都没有，而现在只在该有的地方有。"""

    def test_it_was_absent_everywhere_else(self):
        hits = []
        for base in ("workflows", "tools"):
            for f in sorted((ROOT / base).rglob("*")):
                if f.suffix not in (".md", ".py") or "__pycache__" in str(f):
                    continue
                if f.name in ("job-gmail-sync.md", "tracker.py"):
                    continue
                if "人才库" in f.read_text(encoding="utf-8", errors="replace"):
                    hits.append(f.name)
        self.assertEqual(hits, [], f"这几处也讲了人才库，判据可能已经分叉：{hits}")

    def test_his_tracker_has_no_such_record_yet(self):
        """他 0 回音，所以一条都不该有。哪天有了，这条会红 —— 那是好事。"""
        import csv
        p = ROOT / ".active_user"
        if not p.is_file():
            self.skipTest("没有活动用户")
        f = (ROOT / "users" / p.read_text(encoding="utf-8").strip()
             / "job_search_tracker.csv")
        if not f.is_file():
            self.skipTest("还没有投递记录")
        rows = list(csv.DictReader(f.open(encoding="utf-8-sig")))
        n = sum(1 for r in rows if "talent_pool" in str(r.get("notes") or ""))
        if n:
            self.skipTest(f"已经记了 {n} 条 —— 那套判据开始生效了")
        self.assertEqual(n, 0)


if __name__ == "__main__":
    unittest.main()
