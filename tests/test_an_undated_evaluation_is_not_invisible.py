# -*- coding: utf-8 -*-
"""没写「评估日期」的深评，不许对按日期的分析和写盘闸门隐形。

## 规则在，没人验

`04-job-evaluation.md` 的输出格式里有 `- 评估日期：YYYY-MM-DD`，旁边整整
一段说它为什么要紧：

> 「评估日期」那一行不是装饰，是所有按批次看趋势的分析唯一的依据……
> 审计每一条报的都是全库累计数，而那个数只会随产量涨。改完一条规则之后，
> 能回答「它生效了没有」的只有「最近一批还犯不犯」—— 而那要按日期分组才看
> 得出来。日期丢了，新加的规则就再也验不了。

那段话还记着一次事故：3 份写了日期却没带 `- `，**当天新出的深评对每一个
按日期分析的检查全部隐形**。

**而验它的一处也没有**（2026-08-30 通读时发现）。

## 它还会漏掉写盘那道闸门

`--sections` 按日期挑「这一批」。判不出日期时**不能当成「不是这一批」** ——
那样它永远挑不出来。实测全库 1 份没有这一行，而那 1 份缺了**四节**
（结论、优势、建议、投前必问）：此前它对每一道网都是隐形的。
"""
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tests"))
from _srcscan import code_of  # noqa: E402
import audit_pipeline as ap  # noqa: E402

EVAL04 = (ROOT / "workflows" / "reference"
          / "04-job-evaluation.md").read_text(encoding="utf-8")
LF = chr(10)


class TheRequirementIsStillWrittenDown(unittest.TestCase):

    def test_the_format_asks_for_it(self):
        self.assertIn("- 评估日期：YYYY-MM-DD", EVAL04)

    def test_the_reason_is_written_next_to_it(self):
        """判据没了，下面几条就只是一条口味规则。"""
        self.assertIn("不是装饰", EVAL04)
        self.assertIn("新加的规则就再也验不了", EVAL04)


class TheGateDoesNotSkipUndatedFiles(unittest.TestCase):

    def test_no_date_still_counts_as_this_batch(self):
        """判不出日期 ≠ 不是这一批。当成后者，它就永远逃得掉。"""
        seg = code_of("tools/audit_pipeline.py", "def _sections_cli(")
        self.assertIn('want | {""}', seg,
                      "没日期的又被排除在「这一批」之外了")

    def test_the_gate_says_it_included_them(self):
        seg = code_of("tools/audit_pipeline.py", "def _sections_cli(")
        self.assertIn("外加没写日期的", seg, "纳入了却不说，读的人会以为漏了")


class TheAuditReportsThem(unittest.TestCase):

    def test_an_undated_evaluation_is_reported(self):
        head = LF.join(["# 岗 深评", "", "- 职位链接：https://x/1.html",
                        "", "## 结论", "值得投（70）"])
        import tempfile
        import unittest.mock
        with tempfile.TemporaryDirectory() as d:
            tmp = pathlib.Path(d)
            ev = tmp / "users" / "u" / "documents" / "applications" / "一个岗"
            ev.mkdir(parents=True)
            (ev / "evaluation.md").write_text(head, encoding="utf-8")
            with unittest.mock.patch.object(ap, "ROOT", tmp), \
                    unittest.mock.patch.object(ap, "_USER", ["u"]), \
                    unittest.mock.patch.object(ap._cli, "pick_user",
                                               lambda *a, **k: "u"):
                out = ap.check_evaluations_are_dated({}, {})
        self.assertTrue(out, "抬头没有评估日期，一个字都没报")
        self.assertIn("评估日期", out[0][1])

    def test_a_dated_one_is_clean(self):
        head = LF.join(["# 岗 深评", "", "- 评估日期：2026-08-30",
                        "", "## 结论", "值得投（70）"])
        import tempfile
        import unittest.mock
        with tempfile.TemporaryDirectory() as d:
            tmp = pathlib.Path(d)
            ev = tmp / "users" / "u" / "documents" / "applications" / "一个岗"
            ev.mkdir(parents=True)
            (ev / "evaluation.md").write_text(head, encoding="utf-8")
            with unittest.mock.patch.object(ap, "ROOT", tmp), \
                    unittest.mock.patch.object(ap, "_USER", ["u"]), \
                    unittest.mock.patch.object(ap._cli, "pick_user",
                                               lambda *a, **k: "u"):
                self.assertEqual(ap.check_evaluations_are_dated({}, {}), [])

    def test_the_prefixless_form_is_still_accepted(self):
        """事故那次是 3 份漏了 `- `。正则宽进，别把合法写法报成缺失。"""
        self.assertTrue(ap._eval_date("评估日期：2026-08-30"))
        self.assertTrue(ap._eval_date("- 评估日期: 2026-08-30"))
        self.assertTrue(ap._eval_date("* 评估日期：2026-08-30"))


class ARerunIsAlsoThisBatch(unittest.TestCase):
    """`/job-apply --stale` 重写的那一批，这道闸门原来一份都看不见。

    重跑完留的是 `重跑日期：YYYY-MM-DD`（`job-apply.md`：那是它出队的唯一
    判据），而 `评估日期` 原样不动 —— 只按后者挑「这一批」的话，
    **整批逃过这道闸门**。而它恰恰是同一个写手在同一次运行里写的，
    正是「一次跑里要么每份都写、要么每份都不写」那条由来说的那种批。

    ## 只放宽闸门，不动 `_eval_date`

    批次趋势问的是「08-17 那次跑法怎么样」。把重跑件挪到今天，
    会把那个问题答坏 —— 两个问题，两个日期。
    """

    def _run(self, body: str) -> str:
        import contextlib
        import io
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            d = (root / "users" / "_t_rr" / "documents" / "applications"
                 / "甲_岗")
            d.mkdir(parents=True)
            (d / "evaluation.md").write_text(body, encoding="utf-8")
            old_root, old_user = ap.ROOT, list(ap._USER)
            try:
                ap.ROOT = root
                ap._USER[:] = ["_t_rr"]
                (root / ".active_user").write_text("_t_rr", encoding="utf-8")
                buf = io.StringIO()
                with contextlib.redirect_stdout(buf):
                    ap._sections_cli([])
                return buf.getvalue()
            finally:
                ap.ROOT = old_root
                ap._USER[:] = old_user

    def _today(self) -> str:
        import datetime as dt
        return dt.date.today().isoformat()

    def test_a_rerun_today_is_picked_up(self):
        out = self._run(f"- 评估日期：2026-01-02\n- 重跑日期：{self._today()}\n"
                        "## 结论：值得投\n")
        self.assertIn("查", out)
        self.assertIn("1 份", out, "今天重跑的那一份没进这一批")

    def test_an_old_one_that_was_not_rerun_stays_out(self):
        """存量不该被拉进来 —— 这道闸门的全部价值是「这一批」。"""
        out = self._run("- 评估日期：2026-01-02\n## 结论：值得投\n")
        self.assertIn("还没写过深评", out, "三个月前的存量被拉进来了")

    def test_the_gate_says_it_included_them(self):
        seg = code_of("tools/audit_pipeline.py", "def _sections_cli(")
        self.assertIn("重跑过的", seg, "纳入了却不说，读的人会以为漏了")

    def test_the_two_dates_stay_apart(self):
        """`_eval_date` 不许跟着认「重跑日期」—— 那会把批次趋势答坏。"""
        self.assertEqual(ap._eval_date("- 重跑日期：2026-08-31"), "")
        self.assertEqual(ap._rerun_date("- 重跑日期：2026-08-31"), "2026-08-31")
        self.assertEqual(ap._rerun_date("- 评估日期：2026-08-31"), "")

    def test_it_reads_the_same_shape_as_the_queue(self):
        """出队那一侧（`stale_materials`）认哪几种写法，这边就得认哪几种。"""
        import stale_materials as sm
        for form in ("- 重跑日期：2026-08-31", "重跑日期: 2026-08-31",
                     "* 重跑日期：2026-08-31"):
            with self.subTest(form):
                self.assertTrue(sm._REREAD.search(form))
                self.assertTrue(ap._rerun_date(form))


if __name__ == "__main__":
    unittest.main()
