# -*- coding: utf-8 -*-
"""测试用 `X.index("锚")` 切一段来验，而锚在目标文件里不止一处时，它验的是别人的文字。

这一族**不会红**，所以最贵。实测 2026-08-23 抓到一个已经空转的：

    tests/test_the_inbound_half_is_covered.py
        seg = RESUME[RESUME.index("2.6"):]

`job-resume.md` 里第一个「2.6」是第 19 行的**前向引用**（「见下面 2.6」），
于是切出来的是**从第 19 行到文件末尾**。把 2.6 节内的「没查」「必须改」
全删掉，那两条断言照样全绿 —— 那两个词在文件别处各有 2 处和 4 处。
（整节删掉时红的是**另外**几条对着整份文档的断言，这三条一直空转。）

同一天在别处栽过三次会红的版本：`className="mat-gap"` 有两个横幅在用、
`你的简历` 在文件里出现三次、`要读 JD 才能评` 撞上解释它的那句注释。
会红的那三次修起来只花几分钟；**不会红的这一次躲了不知道多久**。

## 这条检查怎么判

扫每个测试文件里 `VAR = (ROOT / "…").read_text(...)` 的绑定，再看
`VAR.index("锚")` 的锚在那个文件里出现几次。多于一次就要么改唯一，
要么进下面的名单并写明理由 —— **名单里每一条都是「就是要第一处」**。
"""
import re
import unittest
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
from _srcscan import strip_comments  # noqa: E402

#: 故意要「第一处」的用法。键是 `(测试文件, 锚)`，值是理由 ——
#: 写不出理由的就不该进这张表，而该去把锚改唯一。
FIRST_ON_PURPOSE = {
    ("test_the_spine_is_three_commands.py", "/job-auto"):
        "它比的就是先后：/job-auto 必须比 /job-rank 先出现在 README 里",
    # 这两条测的是**两块渲染之间的距离**（「在跟谁说话」那条要挨着
    # 「发之前删掉」那条 —— 分开放用户会以为是两回事）。两个名字各出现两次
    # （条件里一次、渲染里一次），而第一处正好是那一块的起点，正是要比的东西。
    ("test_who_are_you_talking_to.py", "m.greetingWarn"):
        "比的是两块渲染的距离，第一处就是那一块的起点",
    ("test_who_are_you_talking_to.py", "m.addresseeWarn"):
        "同上 —— 两个锚都要取各自那一块的起点",
}

_BIND = re.compile(r'^(\w+)\s*=\s*\(?ROOT\s*/\s*(.+?)\)?\.read_text', re.M | re.S)
_USE = re.compile(r'\b(\w+)\.index\(\s*([\'"])(.+?)\2\s*\)')


def _occurrences(text: str, anchor: str) -> int:
    """出现次数。**标识符样的锚要看右边界** —— 否则 `rread-bn` 会被
    `rread-bnote` 撞出一个假的第二处（第一版就误报了这一条）。"""
    if re.fullmatch(r"[\w-]+", anchor):
        return len(re.findall(re.escape(anchor) + r"(?![\w-])", text))
    return text.count(anchor)


def _scan():
    out = []
    for f in sorted((ROOT / "tests").glob("test_*.py")):
        # **先剥注释与 docstring。** 讲这个坑的文件里必然会**引用**出问题的
        # 那行写法（本文件的 docstring 里就逐字抄着 `RESUME.index("2.6")`）——
        # 连注释一起扫，扫描器就会指着一段解释文字说「这里有 bug」。
        # 这个扫描器自己第一版就栽在它要防的坑上。
        src = strip_comments(f.read_text(encoding="utf-8"))
        targets = {}
        for m in _BIND.finditer(src):
            parts = re.findall(r'[\'"]([^\'"]+)[\'"]', m.group(2))
            p = ROOT.joinpath(*parts)
            if p.is_file():
                targets[m.group(1)] = p
        if not targets:
            continue
        for m in _USE.finditer(src):
            var, raw = m.group(1), m.group(3)
            if var not in targets or len(raw) < 3:
                continue
            try:
                anchor = raw.encode().decode("unicode_escape")
            except Exception:
                anchor = raw
            n = _occurrences(targets[var].read_text(encoding="utf-8"), anchor)
            if n > 1:
                out.append((f.name, targets[var].name, n, anchor))
    return out


class EveryAnchorPointsAtOnePlace(unittest.TestCase):
    def test_no_ambiguous_anchor(self):
        bad = [x for x in _scan()
               if (x[0], x[3]) not in FIRST_ON_PURPOSE]
        self.assertEqual(
            [], sorted({f"{a} → {b} 里「{d}」出现 {c} 次" for a, b, c, d in bad}),
            "这些锚点在目标文件里不止一处，`index()` 取的是第一处 —— "
            "断言可能落在别人的文字上，而且**不会红**。"
            "改成唯一的锚（小节标题、独有的 className、渲染点旁的常量名），"
            "或者进 `FIRST_ON_PURPOSE` 并写明为什么就是要第一处。")

    def test_the_allow_list_has_no_dead_entries(self):
        """名单里的条目如果已经不再多处命中，就该删掉 ——
        留着会让下一个人以为那里仍有取舍。"""
        live = {(a, d) for a, _b, _c, d in _scan()}
        dead = [k for k in FIRST_ON_PURPOSE if k not in live]
        self.assertEqual(dead, [], f"这些豁免已经用不上了，删掉：{dead}")

    def test_every_exemption_states_a_reason(self):
        for k, why in FIRST_ON_PURPOSE.items():
            with self.subTest(k=k):
                self.assertGreater(len(why), 8, f"{k} 的理由太短，等于没写")


class TheScannerActuallyWorks(unittest.TestCase):
    """扫不到东西的扫描等于没有。这几条盯着它别退化成空跑。"""

    def test_it_finds_the_bindings(self):
        n = sum(1 for f in (ROOT / "tests").glob("test_*.py")
                if _BIND.search(f.read_text(encoding="utf-8")))
        self.assertGreater(n, 20, f"只认出 {n} 个测试文件在读源码 —— 写法变了？")

    def test_it_counts_a_repeated_anchor(self):
        # 标识符样的锚要看右边界，所以用有边界的样本 ——
        # `aXbXc` 里两个 X 右边都是词字符，按规则本就是 0（第一版写错了）。
        self.assertEqual(_occurrences('"foo" x "foo" y', "foo"), 2)

    def test_a_prefix_is_not_a_second_hit(self):
        """`rread-bn` 不该被 `rread-bnote` 撞出第二处 —— 第一版就误报了。"""
        self.assertEqual(_occurrences('"rread-bn" "rread-bnote"', "rread-bn"), 1)

    def test_a_phrase_anchor_is_counted_literally(self):
        """整句锚不做边界处理 —— 中文里没有词边界。"""
        self.assertEqual(_occurrences("见下面 2.6。\n### 2.6 在线简历", "2.6"), 2)

    def test_the_known_case_would_have_been_caught(self):
        """回归：那条空转的写法（锚「2.6」）必须被这个扫描判为多处。"""
        t = (ROOT / "workflows" / "job-resume.md").read_text(encoding="utf-8")
        self.assertGreater(_occurrences(t, "2.6"), 1)
        self.assertEqual(_occurrences(t, "### 2.6 在线简历"), 1,
                         "改用的那个锚也不唯一了")


if __name__ == "__main__":
    unittest.main()
