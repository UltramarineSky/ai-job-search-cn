# -*- coding: utf-8 -*-
"""状态码漏到屏幕上，是 `AGENTS.md` 点名禁的那类；而这件事一直没人验。

`tracker.say()` 认不出的状态**原样返回**（它的 docstring 写着「宁可露出一个码，
也好过把用户的状态说成别的」—— 那个取舍是对的，但它意味着：词表漏一个，
屏幕上就裸印一个英文码）。

实测代价是有档案的：`SAY_EXTRA` 上面那段注释记着「2026-08-13 全面检查命令
逻辑时扫出来：状态机里有 4 个状态面板进不去，顺着查到这里」。四个都补上了，
**而那次检查是人扫的，扫完没留下任何机械判据** —— 下一个状态加进来时，
同一件事会重演。

这件事**此前只被验过一半**：`test_one_number_per_concept` 里有一个
`EveryStatusSaysSomethingHuman`，从同一次检查里顺出来的，但它只汇两个
源头（按钮表、终结态表）。2026-08-31 两份并到这里 —— 我第一版写这份
守卫时按 `grep "tracker.say"` 判定「全仓没有」，而那一份写的是
`import tracker as tk` 加 `tk.say(...)`，整份从搜索结果里漏掉了。
**按名字搜「有没有人验过」会漏掉换了别名的那一份** —— 这一课记在这儿。

## 判据是派生的，不维护第二份名单

状态从四个互不相干的源头汇：按钮表的目标、终结态表、`/job-outcome` 正文里
列出来的那几个、以及这台机器上真实的投递记录。任何一处新加一个状态，
这里当场红 —— 不必登记。

## 点不到的那几个要逐个说清为什么

按钮表之外的状态不是 bug（`withdrawn`、`interview_only` 都是刻意不做按钮的，
理由写在 `tracker.NEXT` 上面）。但「刻意」和「忘了」在数据上长得一样，
所以下面那张表要求每一个都写明理由 —— 和 `doctor` 那份副本登记表同一个形状。
"""
import csv
import pathlib
import re
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import _cli      # noqa: E402
import tracker   # noqa: E402

OUTCOME = (ROOT / "workflows" / "job-outcome.md").read_text(encoding="utf-8")

#: 按钮点不到、但系统里真会出现的状态：值是**为什么不做按钮**。
#: 这张表只许因为一次明确的裁定而变长。
NO_BUTTON = {
    "withdrawn": "少见，且往往连着一段要写清楚的原因",
    "interview_only": "「流程停了」和「不了了之」是两件事，分得清的只有他",
    "no_response": "`no response` 的下划线体，存量 CSV 里两种拼法都有",
    "offer_declined": "`offer declined` 的下划线体，同上",
}


def _button_targets() -> set:
    return {v for opts in tracker.NEXT.values() for v, _t in opts}


def _from_the_workflow() -> set:
    """`/job-outcome` 正文里 `- \\`xxx\\` —— 说明` 那张表列出来的状态。"""
    return {m.group(1) for m in
            re.finditer(r"^- `([a-z][a-z_ ]{3,20})`\s*——", OUTCOME, re.M)}


def _from_the_ledger() -> set:
    p = ROOT / ".active_user"
    if not p.is_file():
        return set()
    f = (ROOT / "users" / p.read_text(encoding="utf-8").strip()
         / "job_search_tracker.csv")
    if not f.is_file():
        return set()
    with f.open(encoding="utf-8-sig") as fh:
        return {(r.get("status") or "").strip()
                for r in csv.DictReader(fh)} - {""}


def _every_status() -> set:
    return (_button_targets() | set(tracker.FINAL_STATUSES)
            | _from_the_workflow() | _from_the_ledger())


class TheScanSeesTheRealThing(unittest.TestCase):
    """尺子先证明自己会亮 —— 汇不到状态时，下面那些在空集上永远绿。"""

    def test_all_four_sources_contribute(self):
        for name, got in (("按钮表", _button_targets()),
                          ("终结态表", set(tracker.FINAL_STATUSES)),
                          ("job-outcome 正文", _from_the_workflow())):
            with self.subTest(name):
                self.assertGreaterEqual(len(got), 3, f"{name} 一个都没扫到")

    def test_the_workflow_list_is_parsed(self):
        """正文那张表的写法变了要当场知道 —— 不然这一源静默变空。"""
        self.assertIn("interview_only", _from_the_workflow())
        self.assertIn("hired", _from_the_workflow())


class EveryStatusCanBeSaid(unittest.TestCase):

    def test_no_status_prints_as_a_bare_code(self):
        """`AGENTS.md`「未解释的英文码」：屏幕上不许出现 `interview_only`。"""
        bad = sorted(s for s in _every_status() if tracker.say(s) == s)
        self.assertEqual(
            bad, [],
            "这几个状态 say() 认不出来，会原样裸印到面板与报告上："
            + repr(bad) + "，补进 tracker.SAY_EXTRA")

    def test_what_it_says_is_actually_chinese(self):
        """「认得出」不等于「说成了人话」—— 映射到另一个英文码也算认得出。"""
        for s in sorted(_every_status()):
            with self.subTest(s):
                self.assertRegex(tracker.say(s), r"[一-鿿]",
                                 f"{s} 说出来还是没有一个汉字")

    def test_an_unset_status_is_not_an_error(self):
        self.assertEqual(tracker.say(""), "还没投")
        self.assertEqual(tracker.say(None), "还没投")

    def test_an_unknown_status_is_returned_as_is(self):
        """**认不出就原样返回，那是刻意的**（`say()` 自己的 docstring：
        「宁可露出一个码，也好过把用户的状态说成别的」）。

        这条同时是上面那条的判据自检：`say()` 若改成「认不出就说『未知』」，
        上面那条永远绿，而屏幕上从此看不出词表漏了谁。
        """
        self.assertEqual(tracker.say("随便编一个"), "随便编一个")

    def test_both_spellings_are_covered(self):
        """两种拼法都收是对的（不能丢用户的历史数据），收了就得都能显示。

        2026-08-13 那次就是从这儿裂开的：`FINAL_STATUSES` 两种都收，
        而 `say()` 只认空格版 —— 一条下划线体的记录在面板上裸印英文码。
        """
        for a, b in (("no response", "no_response"),
                     ("offer declined", "offer_declined")):
            with self.subTest(a):
                self.assertIn(a, tracker.FINAL_STATUSES)
                self.assertIn(b, tracker.FINAL_STATUSES)
                self.assertEqual(tracker.say(a), tracker.say(b))


class TheButtonlessOnesAreAccountedFor(unittest.TestCase):
    """「刻意不做按钮」和「忘了做」在数据上长得一样，所以要逐个写明。"""

    def test_no_unregistered_buttonless_status(self):
        gone = sorted(_every_status() - _button_targets() - set(NO_BUTTON))
        self.assertEqual(
            gone, [],
            "这几个状态按钮点不到，也没人说清为什么：" + repr(gone)
            + "。要么进 tracker.NEXT，要么进这份表并写明理由")

    def test_the_table_is_not_stale(self):
        """登记了却已经不存在的，说明表该清了。"""
        stale = sorted(set(NO_BUTTON) - _every_status())
        self.assertEqual(stale, [], f"这几个状态已经没有了：{stale}")

    def test_the_reason_is_written_next_to_the_table(self):
        """理由的正本在 `tracker.NEXT` 上面那段，不在这份表里。"""
        src = (ROOT / "tools" / "tracker.py").read_text(encoding="utf-8")
        i = src.index("NEXT: dict[str, list[tuple[str, str]]] = {")
        seg = " ".join(src[max(0, i - 2200):i].split())
        for name in ("withdrawn", "interview_only"):
            with self.subTest(name):
                self.assertIn(name, seg, f"{name} 为什么没有按钮，代码里没写")


class TheLabelTableStaysWhatItClaims(unittest.TestCase):
    """`LABEL` 被 `html-report.md` 钉为「按钮上的字」—— 塞别的进去它就说谎了。"""

    def test_label_is_exactly_the_buttons(self):
        self.assertEqual(set(tracker.LABEL), _button_targets())

    def test_say_extra_does_not_overlap_label(self):
        """两张表都能答同一个状态时，改一张就会有一处不跟着变。"""
        self.assertEqual(set(tracker.SAY_EXTRA) & set(tracker.LABEL), set())


if __name__ == "__main__":
    unittest.main()
