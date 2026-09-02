# -*- coding: utf-8 -*-
"""固定字符窗口截断了要查的那一段，而断言是「不许出现」—— 那是假绿。

## 这一课记过三次，前两次方向是安全的

本仓库大量用 `SRC[i:i + N]` 取源码片段做断言。窗口不够时会怎样，**取决于
断言的方向**：

    assertIn(X, 窗口)      内容挪出窗口 → 变红。吵，但它自陈。
    assertNotIn(X, 窗口)   内容挪进被截掉的那截 → **静默通过**。

前两次都栽在前一种，所以都被当场看见了：

- 2026-08-27 `test_the_padding_survives_a_job_title`：那道台阶加到第六格，
  2400 字窗口够不着了 —— 当时就改成「取整个函数」并把理由写进了注释；
- 2026-08-31 `test_the_greeting_stats_are_not_stale`：同一道台阶加到第十格，
  它**没跟上**那一课，仍用 2400 字窗口，红在一个「上一格」上。

## 而这一条查的是第二种

2026-08-31 扫全仓：`tests/` 里 184 个文件用固定窗口，其中锚点是
`def ` / `## `、且窗口短于真实段落的有 **19 处** —— 但只有 **2 处**配的是
「不许出现」型断言：

    test_the_materials_queue_goes_stale_too.py     assertNotIn("ready_note",  DR[i:i+6000])
    test_when_did_you_last_refresh_your_resume.py  assertNotIn("resume_note", DR[i:i+6000])

而 `doctor.next_step` 那时已经 8000 字 —— **最后 2000 字不在检查范围内**。
两条都改成取整个函数（改完仍然绿，说明当时没有藏着的违规），这条守卫钉住
不再长出第三处。

## 判据只认会静默出错的那一半

`assertIn` 那 17 处不动：它们窗口不够会变红，而红是看得见的。
一刀切地要求「都取整段」是另一种噪音。
"""
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]

#: `VAR[i:i + N]`。小窗口（< 300）是「就近断言」，不是想取整段。
_SLICE = re.compile(r"(\w+)\[i:i \+ (\d+)\]")
_ANCHOR = re.compile(r'i = (\w+)(?:\.\w+)?\.index\((["\'])(.+?)\2\)')
#: 会静默出错的那几种用法。
_SILENT = re.compile(r"assertNotIn|assertNotRegex|findall|\.count\(")
_MIN_WIDTH = 300


def _globals_of(text: str) -> dict:
    """测试里那些大写全局 → 它指向的仓库文件（相对路径）。"""
    out = {}
    for m in re.finditer(
            r'^([A-Z_]+) = \(?ROOT(?: / "([^"]+)")(?: / "([^"]+)")?(?: / "([^"]+)")?',
            text, re.M):
        parts = [g for g in m.groups()[1:] if g]
        out[m.group(1)] = "/".join(parts)
    return out


def offenders() -> list:
    bad = []
    for p in sorted((ROOT / "tests").glob("*.py")):
        text = p.read_text(encoding="utf-8")
        g = _globals_of(text)
        lines = text.splitlines()
        for n, ln in enumerate(lines):
            m = _SLICE.search(ln)
            if not m:
                continue
            var, width = m.group(1), int(m.group(2))
            if width < _MIN_WIDTH:
                continue
            anc = None
            for back in range(n, max(0, n - 12), -1):
                ma = _ANCHOR.search(lines[back])
                if ma:
                    anc = (ma.group(1), ma.group(3))
                    break
            if not anc or anc[0] != var:
                continue
            if not (anc[1].startswith("def ") or anc[1].startswith("## ")):
                continue
            near = "\n".join(lines[n:min(len(lines), n + 6)])
            if not _SILENT.search(near):
                continue
            rel = g.get(var)
            if not rel:
                continue
            f = ROOT / rel
            if not f.is_file():
                continue
            src = f.read_text(encoding="utf-8", errors="replace")
            try:
                i = src.index(anc[1])
            except ValueError:
                continue
            ends = [x for x in (src.find("\ndef ", i + 10),
                                src.find("\n## ", i + 10),
                                src.find("\nclass ", i + 10)) if x > 0]
            real = (min(ends) if ends else len(src)) - i
            if real > width:
                bad.append(f"{p.name}:{n + 1} {var}[i:i+{width}] "
                           f"而 {anc[1][:30]!r} 那一段有 {real} 字")
    return bad


class NoTruncatedWindowFeedsANegativeAssertion(unittest.TestCase):

    def test_none_right_now(self):
        bad = offenders()
        self.assertEqual(
            bad, [],
            "这几处的窗口截断了要查的那一段，而断言是「不许出现」——"
            "被截掉的那截里真出现了也看不见：\n  " + "\n  ".join(bad)
            + "\n改法：把窗口换成整段（找下一个 def / ## 作边界）")

    def test_the_detector_can_fire(self):
        """对照：判据真认得出那种写法。"""
        self.assertTrue(_SILENT.search('self.assertNotIn("x", DR[i:i + 6000])'))
        self.assertTrue(_SLICE.search("DR[i:i + 6000]"))
        self.assertIsNone(_SLICE.search("DR[i:i + 60]") and None)

    def test_small_windows_are_not_flagged(self):
        """就近断言不在射程内 —— 一刀切要求取整段是另一种噪音。"""
        self.assertLess(int(_SLICE.search("X[i:i + 120]").group(2)), _MIN_WIDTH)

    def test_positive_assertions_are_left_alone(self):
        """`assertIn` 窗口不够会变红，而红是看得见的。"""
        self.assertIsNone(_SILENT.search('self.assertIn("x", SRC[i:i + 400])'))


if __name__ == "__main__":
    unittest.main()
