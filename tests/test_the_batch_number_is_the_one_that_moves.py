# -*- coding: utf-8 -*-
"""审计每条报的都是全库累计数，而那个数只会随产量涨 —— 改好了也降不下来。

「191/269 份命中框架词」这种数，分母里绝大多数是规则收紧**之前**产的。
所以改完一条规则之后，它**回答不了「这条规则生效了没有」**。

唯一回答得了的是**最近一批还犯不犯**。这不是新想法 —— `audit_pipeline` 里
已经有两条检查在散文里手写过同一件事：

    深评缺小节：「是整批漏，不是慢慢漂：2026-08-10 那批 26 份每份都缺了至少一节
                ……而 2026-08-11 的 79 份全写齐了。该查的是那几次跑法。」
    可以考虑：  「这个数说的是存量，说明不了规则灵不灵，跑一批新的才有得比」

手写两遍就会有第三遍写不出来。这一轮把它做成 `batch_note()`。

## 但它先卡在一个更基础的地方：日期读不到

`_EVAL_DATE` 按 `^-\\s*评估日期：` 解析，而 **`04` 的输出格式里根本没有这一行**。
266/270 对得上，只是因为早期批次碰巧都带了 `- `。

实测 2026-08-24：**3 份写了日期却没带列表符，其中两份是当天照 04 的格式写的** ——
于是当天新出的深评对每一个按日期分析的检查全部隐形。

这是这个仓库点过名的那一类：**检查在、规则不在**。两头都修了：
解析器放宽（`- ` 可有可无），`04` 的输出格式补上那一行并写明它为什么要紧。

## 太小的批次不报

实测这个库里 2026-08-14 只有 2 份、08-19 只有 3 份。「最近一批 2/2 都犯」
在统计上说不出任何东西，读起来却像个结论 —— 宁可不说。
"""
import pathlib
import re
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import audit_pipeline as ap  # noqa: E402

AUDIT = (ROOT / "tools" / "audit_pipeline.py").read_text(encoding="utf-8")
EVAL = (ROOT / "workflows" / "reference"
        / "04-job-evaluation.md").read_text(encoding="utf-8")


def flat(s: str) -> str:
    s = " ".join(re.sub(r"^\s*(?:>|#:?)\s?", "", s, flags=re.M).split())
    return re.sub(r"(?<=[一-鿿，。；：、（）「」])"
                  r" +(?=[一-鿿，。；：、（）「」])", "", s)


class TheDateParsesEitherWay(unittest.TestCase):
    def test_with_the_bullet(self):
        self.assertEqual(ap._eval_date("- 评估日期：2026-08-17"), "2026-08-17")

    def test_without_the_bullet(self):
        """两份当天照 04 格式写的深评就是这么掉出去的。"""
        self.assertEqual(ap._eval_date("评估日期：2026-08-24"), "2026-08-24")

    def test_full_width_colon_and_star(self):
        self.assertEqual(ap._eval_date("* 评估日期: 2026-08-01"), "2026-08-01")

    def test_it_still_needs_the_label(self):
        """放宽的是列表符，不是「随便哪个日期都算」。"""
        self.assertEqual(ap._eval_date("生成日期：2026-08-17"), "")
        self.assertEqual(ap._eval_date("2026-08-17"), "")

    def test_the_widening_is_recorded(self):
        i = AUDIT.index("_EVAL_DATE = re.compile(")
        seg = flat(AUDIT[max(0, i - 1200):i])
        self.assertRegex(seg, r"列表符是可选的")
        self.assertRegex(seg, r"两份是当天照 04 的格式写的")
        self.assertIn("2026-08-24", seg)


class TheSpecNowAsksForIt(unittest.TestCase):
    def test_the_skeleton_has_the_line(self):
        """**光放宽解析器不够** —— 规格里没有，下一个人照样各写各的。"""
        i = EVAL.index("## 职位评估：[公司] - [岗位]")
        self.assertIn("- 评估日期：YYYY-MM-DD", EVAL[i:i + 300])

    def test_it_says_why_the_line_matters(self):
        i = EVAL.index("「评估日期」那一行不是装饰")
        seg = flat(EVAL[i:i + 1200])
        self.assertRegex(seg, r"所有按批次看趋势的分析唯一的依据")
        self.assertRegex(seg, r"全库累计数")
        self.assertRegex(seg, r"只会随产量涨")

    def test_it_records_the_incident(self):
        i = EVAL.index("「评估日期」那一行不是装饰")
        seg = flat(EVAL[i:i + 1200])
        self.assertIn("2026-08-24", seg)
        self.assertRegex(seg, r"两份是当天照这份格式写的")

    def test_it_warns_against_leaning_on_the_parser(self):
        i = EVAL.index("「评估日期」那一行不是装饰")
        seg = flat(EVAL[i:i + 1200])
        self.assertRegex(seg, r"靠解析器兜底就等于把格式交给下一个人各写各的")


class TheBatchNoteSaysTheRightThing(unittest.TestCase):
    def test_it_reports_the_latest_big_enough_batch(self):
        rows = [("2026-08-11", False)] * 80 + [("2026-08-17", True)] * 40
        got = ap.batch_note(rows)
        self.assertIn("2026-08-17", got)
        self.assertIn("40 份）里 40 份", got)

    def test_a_tiny_batch_is_skipped(self):
        """「最近一批 2/2 都犯」读起来像结论，统计上什么也不是。"""
        rows = [("2026-08-11", False)] * 80 + [("2026-08-19", True)] * 3
        got = ap.batch_note(rows)
        self.assertIn("2026-08-11", got, "跳过小批次之后要退回上一批，不是放弃")

    def test_no_batch_is_big_enough_says_nothing(self):
        self.assertEqual(ap.batch_note([("2026-08-19", True)] * 3), "")

    def test_undated_rows_are_ignored(self):
        """没日期的不该被凑成一批 —— 那批的「日期」是空串，报出来是假的。"""
        self.assertEqual(ap.batch_note([("", True)] * 40), "")

    def test_a_clean_batch_reports_zero(self):
        """**改好了要看得出来。** 这才是这个函数存在的理由。"""
        rows = [("2026-08-11", True)] * 80 + [("2026-08-25", False)] * 20
        got = ap.batch_note(rows)
        self.assertIn("2026-08-25", got)
        self.assertIn("20 份）里 0 份", got)

    def test_it_says_why_this_number_and_not_the_other(self):
        got = ap.batch_note([("2026-08-17", True)] * 40)
        self.assertIn("全库那个数只会随产量涨", got)

    def test_no_markdown_reaches_the_terminal(self):
        self.assertNotIn("**", ap.batch_note([("2026-08-17", True)] * 40))

    def test_the_threshold_is_adjustable(self):
        self.assertTrue(ap.batch_note([("2026-08-19", True)] * 3, min_size=3))

    def test_the_reason_is_recorded(self):
        i = AUDIT.index("def batch_note(")
        seg = flat(AUDIT[i:AUDIT.index("def _eval_date(", i)])
        self.assertRegex(seg, r"唯一能回答「它生效了没有」的是「最近一批还犯不犯」")
        self.assertRegex(seg, r"手写两遍就会有第三遍写不出来")
        self.assertRegex(seg, r"太小的批次不报")


class ItHasRealConsumers(unittest.TestCase):
    """只有一个消费方的辅助函数就是过度设计 —— 本仓库已经手写过两遍。"""

    def test_at_least_two_checks_use_it(self):
        n = AUDIT.count("batch_note(rows)")
        self.assertGreaterEqual(n, 2, f"只有 {n} 处在用它")

    def test_the_jargon_check_uses_it(self):
        i = AUDIT.index('f"{label}正文里有框架词"')
        self.assertIn("batch_note(rows)", AUDIT[i:i + 800])

    def test_the_missing_gates_check_uses_it(self):
        i = AUDIT.index('"深评漏判硬性条件"')
        self.assertIn("batch_note(rows)", AUDIT[i:i + 700])

    def test_the_denominator_is_kept(self):
        """**每份都要记一笔，不管有没有命中** —— 只记命中的，分母就丢了。"""
        i = AUDIT.index("rows.append((_eval_date(_dated_text(f)), bool(words)))")
        seg = AUDIT[max(0, i - 400):i]
        self.assertIn("不管有没有命中", seg)
        # 记录那一行必须在 `continue` **之前**
        self.assertLess(i, AUDIT.index("if not words:\n                continue"))

    def test_outreach_borrows_the_date_from_its_evaluation(self):
        """话术文件自己没有「评估日期」那一行 —— 同一次跑产的两个文件，日期是同一个。

        **验行为，不验 docstring。** 第一版只查了那段说明里有没有
        「evaluation.md」这个词，于是把借日期那两行整个删掉，测试照样全绿
        （变异实测）—— 而那正是话术那一侧唯一的日期来源。
        """
        import tempfile
        nl = chr(10)
        with tempfile.TemporaryDirectory() as t:
            d = pathlib.Path(t) / "甲_某岗"
            d.mkdir()
            (d / "evaluation.md").write_text("- 评估日期：2026-08-17" + nl,
                                             encoding="utf-8")
            (d / "outreach.md").write_text("# 话术" + nl + "没有日期这一行" + nl,
                                           encoding="utf-8")
            self.assertEqual(ap._eval_date(ap._dated_text(d / "outreach.md")),
                             "2026-08-17")
            # 深评自己那份读自己
            self.assertEqual(ap._eval_date(ap._dated_text(d / "evaluation.md")),
                             "2026-08-17")
            # 旁边没有深评时不猜
            lone = pathlib.Path(t) / "乙_某岗"
            lone.mkdir()
            (lone / "outreach.md").write_text("# 话术" + nl, encoding="utf-8")
            self.assertEqual(ap._dated_text(lone / "outreach.md"), "")

    def test_the_borrowing_is_explained(self):
        i = AUDIT.index("def _dated_text(")
        seg = flat(AUDIT[i:AUDIT.index("def batch_note(", i)])
        self.assertRegex(seg, r"话术文件自己没有「评估日期」那一行")


class TheSignalItLeansOnIsReal(unittest.TestCase):
    """现算：这个库里真的分得出批次，而且最近一批真的够大。"""

    def _dates(self):
        p = ROOT / ".active_user"
        if not p.is_file():
            self.skipTest("没有活动用户")
        apps = (ROOT / "users" / p.read_text(encoding="utf-8").strip()
                / "documents" / "applications")
        if not apps.is_dir():
            self.skipTest("还没有深评")
        got = [ap._eval_date(f.read_text(encoding="utf-8", errors="replace"))
               for f in apps.glob("*/evaluation.md")]
        if len(got) < 50:
            self.skipTest("深评太少，分不出批次")
        return got

    def test_almost_every_evaluation_has_a_date(self):
        """日期丢一份，按批次的分析就少看一份 —— 而新出的那几份恰恰最要紧。"""
        got = self._dates()
        blank = sum(1 for d in got if not d)
        self.assertLessEqual(
            blank, len(got) * 0.02,
            f"{blank}/{len(got)} 份读不到评估日期 —— 按批次的分析在少看它们")

    def test_there_is_a_batch_big_enough_to_talk_about(self):
        got = self._dates()
        import collections
        c = collections.Counter(d for d in got if d)
        self.assertTrue(any(v >= 8 for v in c.values()),
                        f"没有一批够 8 份 —— batch_note 会一直沉默：{c.most_common(3)}")


if __name__ == "__main__":
    unittest.main()
