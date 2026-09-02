# -*- coding: utf-8 -*-
"""写盘那道闸门对着一个动不了的岗，永远红着。

`/job-auto` 每批写完盘先跑 `audit_pipeline.py --sections`，
`job-auto.md` 对非零的要求是明确的：

> **非零就当场补齐，补完重跑到零再往下走** —— 别刷快照、别开下一批。

## 它兑不了现

没写「评估日期」的深评**一律纳入「这一批」**（否则它永远逃得掉，
判据见 `_sections_cli` 里那段注释）。而实测 2026-09-01：全库唯一一份
没有那一行的深评产于 2026-08-10，用的还是旧口径（五维打分 / 硬门检查），
缺 结论、优势、建议 三节 —— 它对应的岗**用户早就标了不投**。

于是这一份每一轮都被捞进来，闸门**永远非零**，而那句「补完重跑到零」
永远做不到：补个日期是假账，整份重跑是给一个不投的岗重开页面。

**一道兑不了现的闸门，执行者只会学会绕过它** —— 连同它本来拦得住的
那几十份一起。这个仓库为「许一个兑现不了的诺」交过好几次学费。

## 判据不是新发明的

`--actionable` 那一档早就按 `NO_LIVE` 滤过一遍行（`run()` 里那句
「一行有活、一行没有」），这道闸门从来没学会它 —— 同一件事两个住址，
而检查只去了一个。

**「判不了」不算动不了。** `sendable_state` 五格里的「对不上职位库」
要留在红的那一边：`live_tail` 为这一脚交过学费（并进「已经出局」，
数被压小了还看不见）。
"""
import contextlib
import io
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import audit_pipeline as ap  # noqa: E402

LF = chr(10)
#: 缺「建议」一节，其余写齐 —— 闸门该报的那种。
LACKING = LF.join("## " + k for k in ap.EVAL_SECTIONS if k != "建议")
WHOLE = LF.join("## " + k for k in ap.EVAL_SECTIONS)


def _run(files, where, paths=()):
    """临时根下摆几份深评，跑一次闸门 → `(退出码, 打印出来的话)`。

    `files` = {目录名: 正文}，`where` = {目录名: `sendable_state` 那五格之一}。
    """
    with tempfile.TemporaryDirectory() as d:
        tmp = pathlib.Path(d)
        apps = tmp / "users" / "u" / "documents" / "applications"
        for name, text in files.items():
            (apps / name).mkdir(parents=True)
            (apps / name / "evaluation.md").write_text(text, encoding="utf-8")
        urls = {n: f"https://x/{n}" for n in files}
        buf = io.StringIO()
        with mock.patch.object(ap, "ROOT", tmp), \
                mock.patch.object(ap._cli, "pick_user", lambda *a, **k: "u"), \
                mock.patch.object(ap, "load", lambda u: ({}, {})), \
                mock.patch.object(ap, "dir_urls", lambda u: urls), \
                mock.patch.object(
                    ap._cli, "sendable_state",
                    lambda u, s: (lambda url: where.get(
                        url.rsplit("/", 1)[-1], "还能发"))), \
                contextlib.redirect_stdout(buf):
            code = ap._sections_cli([str(apps / p) for p in paths])
        return code, buf.getvalue()


class ItStillBitesOnWhatThisRunCanFix(unittest.TestCase):

    def test_a_live_job_still_fails_the_gate(self):
        """这才是闸门的正事 —— 放过它就等于把闸门整个撤了。"""
        code, out = _run({"甲": LACKING}, {"甲": "还能发"})
        self.assertEqual(code, 1)
        self.assertIn("缺 建议：甲", out)

    def test_an_unknown_job_still_fails_the_gate(self):
        """**「判不了」不算「动不了」。**

        `live_tail` 为这一脚交过学费：把「对不上职位库」并进「已经出局」，
        数被压小了，而且压得看不见。两个方向都要留住那个「不知道」。
        """
        code, out = _run({"甲": LACKING}, {"甲": "对不上职位库"})
        self.assertEqual(code, 1, "判不了还能不能发的，被当成不用管了")
        self.assertIn("缺 建议：甲", out)

    def test_all_sections_written_is_still_green(self):
        code, out = _run({"甲": WHOLE}, {"甲": "还能发"})
        self.assertEqual(code, 0)


class ItDoesNotBlockOnWhatNobodyCanFix(unittest.TestCase):

    def test_a_job_he_marked_skipped_does_not_hold_the_gate_red(self):
        code, out = _run({"甲": LACKING}, {"甲": "你标了不投"})
        self.assertEqual(code, 0, "闸门被一个不投的岗永远拖红着")
        self.assertIn("不计入这道闸门", out)

    def test_it_still_names_them(self):
        """不计入不等于不说 —— 不说就成了另一种隐形。"""
        _code, out = _run({"甲": LACKING}, {"甲": "已经投出去了"})
        self.assertIn("甲", out)
        self.assertIn(ap._cli.NO_LIVE, out)

    def test_one_live_one_moot_still_fails(self):
        """混着来的时候，红的那个说了算。"""
        code, out = _run({"甲": LACKING, "乙": LACKING},
                         {"甲": "还能发", "乙": "岗位已下线"})
        self.assertEqual(code, 1)
        self.assertIn("缺 建议：甲", out)
        self.assertNotIn("缺 建议：乙", out)
        self.assertIn("不计入这道闸门", out)

    def test_the_count_it_reports_leaves_the_moot_ones_out(self):
        """报「N 份都写全了」时，那个 N 不能把动不了的算进去 —— 那是虚报。"""
        _code, out = _run({"甲": WHOLE, "乙": LACKING},
                          {"甲": "还能发", "乙": "你标了不投"})
        self.assertIn("该管的 1 份都写全了", out)


class AMissingJobStoreDoesNotStopIt(unittest.TestCase):
    """`load` 缺文件时是直接 `SystemExit` 的 —— 闸门不能倒在这一下。

    它给的是「没有 …/seen_jobs.json —— 先跑 /job-scrape」，对这道闸门
    答非所问：闸门查的是刚写下的那批文件，和抓没抓过岗没关系。

    实测（2026-09-01）：接上 `sendable_state` 的当天，全量测试里
    一条建临时根跑闸门的用例当场炸了 `SystemExit` —— 而临时根里本来
    就不会有职位库。真实场景同形：新用户、换了活动用户、路径坏了。

    **读不出来就一律算「判不了」，留在红的那一边** —— 宁可多拦，
    绝不因为读不到库而放过谁。
    """

    def _run_without_store(self, text):
        with tempfile.TemporaryDirectory() as d:
            tmp = pathlib.Path(d)
            ev = tmp / "users" / "u" / "documents" / "applications" / "甲"
            ev.mkdir(parents=True)
            (ev / "evaluation.md").write_text(text, encoding="utf-8")
            buf = io.StringIO()
            with mock.patch.object(ap, "ROOT", tmp),                     mock.patch.object(ap._cli, "pick_user",
                                      lambda *a, **k: "u"),                     contextlib.redirect_stdout(buf):
                code = ap._sections_cli([])
            return code, buf.getvalue()

    def test_it_still_reports_the_gap(self):
        code, out = self._run_without_store(LACKING)
        self.assertEqual(code, 1, "职位库读不出来，闸门就整个不拦了")
        self.assertIn("缺 建议：甲", out)

    def test_it_does_not_die(self):
        """倒在这儿的话，那一批的缺口一条都印不出来。"""
        code, _out = self._run_without_store(WHOLE)
        self.assertEqual(code, 0)


class GivingPathsMeansCheckThose(unittest.TestCase):

    def test_an_explicit_path_is_checked_whatever_its_state(self):
        """点名要查的那几份，不替调用方判该不该管。"""
        code, out = _run({"甲": LACKING}, {"甲": "你标了不投"}, paths=("甲",))
        self.assertEqual(code, 1)
        self.assertIn("缺 建议：甲", out)


if __name__ == "__main__":
    unittest.main()
