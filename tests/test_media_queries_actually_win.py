# -*- coding: utf-8 -*-
"""媒体查询里的规则，要盖得住外面那条同形的。

## 媒体查询不提升特异性——这份文件里已经栽了三次

`@media (max-width: 720px) { .cmdbook-row { grid-template-columns: 1fr } }`
读起来像是「窄屏堆成一列」，但外面还有一条
`.cmdbook-row { grid-template-columns: 12em 1fr }`，**特异性完全一样**，
而且写在文件更靠后的地方。同特异性下后写的赢，于是断点里那条一行都不生效。

实测（2026-08-18，Playwright 量 `getComputedStyle`）三处：

| 断点里写的 | 外面那条在 | 实际结果 |
|---|---|---|
| `.cmdbook-row { grid-template-columns: 1fr }` | 约 1000 行 | 390px 上量到 `180px 100px`，说明列只有 100px、每行四五个字 |
| `.cmdbook-ex { grid-column: 1 }` | 约 1010 行 | 一直停在第 2 列 |
| `.shortlist .ant-table-content > table { min-width: 0 }` | 约 1210 行 | 表格照旧 576px 宽，横滚没消失 |

前两条是**写下来之后一次都没工作过**——而它们上面的注释（「命令表在更窄处才需要
堆叠」）读起来完全像是已经在管事了。这类失效不会报错、不会崩，只会让人以为
响应式已经做过了。

## 判据

对每个 `@media` 块里的选择器，找文件中**块外**是否有字面完全相同的选择器。
有的话，块内那条必须**特异性更高**（通常是多挂一层祖先类），否则报。

只比字面相同的选择器：`.a .b` 和 `.b` 谁盖谁要看上下文，那种不在这条守卫的
射程里；而字面相同这一种是纯粹的失效，没有任何「其实我想要外面那条」的解释。
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CSS = ROOT / "web" / "src" / "theme" / "cockpit.css"


def _strip_comments(t: str) -> str:
    """注释挖空，但**保留换行数**——否则报出来的行号对不上原文。

    第一版直接删掉整段注释，于是 `.hide-body` 被报在 L634，而那一行是
    `.rread-bn`；这份 CSS 的注释很长（本仓库要求写清原委），错位有四百多行。
    报错要能直接跳过去看，不然守卫等于只说了「某处有问题」。
    """
    return re.sub(r"/\*.*?\*/",
                  lambda m: "\n" * m.group(0).count("\n"), t, flags=re.S)


def _media_spans(t: str):
    """每个 `@media {...}` 的 (内容起, 内容止) 偏移。"""
    out = []
    for m in re.finditer(r"@media", t):
        i = t.index("{", m.start())
        depth, j = 0, i
        while j < len(t):
            if t[j] == "{":
                depth += 1
            elif t[j] == "}":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        out.append((i + 1, j))
    return out


def _props(body: str):
    """一条规则里声明了哪些属性名。用来判断两条规则是否真的会打架。"""
    return {d.split(":", 1)[0].strip().lower()
            for d in body.split(";") if ":" in d}


def _rules(chunk: str, offset: int = 0):
    """(选择器串, 属性名集合, 在原文里的偏移)。只认 `选择器 { ... }` 这一层。"""
    out = []
    for m in re.finditer(r"([^{}@]+)\{([^{}]*)\}", chunk):
        sel = " ".join(m.group(1).split())
        if sel and not sel.startswith("@"):
            out.append((sel, _props(m.group(2)), offset + m.start()))
    return out


def specificity(sel: str):
    """(id, class/attr/pseudo-class, element) —— 够用的近似，不处理 :is()/:not() 内部。"""
    s = re.sub(r"::[a-z-]+", " ", sel)                       # 伪元素算元素
    ids = len(re.findall(r"#[\w-]+", s))
    cls = len(re.findall(r"\.[\w-]+|\[[^\]]+\]|:[\w-]+(?:\([^)]*\))?", s))
    els = len(re.findall(r"(?:^|[\s>+~])([a-z][\w-]*)", s))
    return (ids, cls, els)


class MediaQueryRulesOutrankTheirBaseRule(unittest.TestCase):

    def test_no_media_rule_is_shadowed_by_an_identical_selector(self):
        t = _strip_comments(CSS.read_text(encoding="utf-8"))
        spans = _media_spans(t)
        self.assertTrue(spans, "一个 @media 都没有？这条守卫失去依据")

        in_rules = []
        for a, b in spans:
            in_rules.extend(_rules(t[a:b], a))

        # 块外的规则：把所有 @media 块整段挖掉再扫
        outside_src, prev = [], 0
        for a, b in spans:
            start = t.rfind("@media", 0, a)
            outside_src.append((t[prev:start], prev))
            prev = b + 1
        outside_src.append((t[prev:], prev))
        out_rules = {}
        for chunk, off in outside_src:
            for sel, props, o in _rules(chunk, off):
                out_rules.setdefault(sel, []).append((props, o))

        bad = []
        for sel, props, off in in_rules:
            for one in [s.strip() for s in sel.split(",")]:
                for out_props, o in out_rules.get(one, []):
                    # 只有**块外那条写在后面**、且两边设了同一个属性，才是真遮蔽。
                    # 不比属性的话，`.cmdbook-bare` 一处设 `overflow-wrap`、
                    # 另一处设 `grid-column` 也会被报——那种误报的代价不是多看一眼，
                    # 是逼着下一个人给根本不需要的规则乱加 `.cockpit`，
                    # 把这份文件的选择器整体推高一层，真正的遮蔽反而更难看出来。
                    clash = props & out_props
                    if o > off and clash:
                        bad.append(
                            f"L{t[:off].count(chr(10)) + 1} 断点里的 `{one}` "
                            f"被 L{t[:o].count(chr(10)) + 1} 同形的那条盖掉"
                            f"（都设了 {'、'.join(sorted(clash))}）")

        self.assertEqual(
            bad, [],
            "\n  " + "\n  ".join(bad)
            + "\n\n媒体查询**不提升特异性**：块外字面相同、又写在后面的那条会赢，"
              "\n断点里这条一行都不生效——不报错、不崩，只让人以为响应式做过了。"
              "\n改法：给断点里的选择器多挂一层祖先（本仓库用 `.cockpit`），"
              "\n不要靠把断点搬到基础规则后面（那会让 @media 散落，"
              "\n`test_css_and_cjk_text.BreakpointsStayTogether` 会拦）。")

    def test_it_would_catch_a_shadowed_rule(self):
        """控制用例：造一段确实被盖掉的 CSS，判据必须认出来。"""
        fake = "@media (max-width: 620px) { .x { color: red } }\n.x { color: blue }\n"
        a, b = _media_spans(fake)[0]
        sel, props, off = _rules(fake[a:b], a)[0]
        self.assertEqual((sel, props), (".x", {"color"}))
        _, out_props, out_off = _rules(fake[b + 1:], b + 1)[0]
        self.assertGreater(out_off, off, "控制样例里块外那条没排在后面，样例本身不成立")
        self.assertTrue(props & out_props, "两条设的是同一个属性，才构成遮蔽")

    def test_different_properties_are_not_a_clash(self):
        """控制用例：同一个选择器设不同属性，不算遮蔽——误报会逼人乱加祖先类。"""
        fake = ("@media (max-width: 620px) { .y { overflow-wrap: anywhere } }\n"
                ".y { grid-column: 2 }\n")
        a, b = _media_spans(fake)[0]
        _, props, _ = _rules(fake[a:b], a)[0]
        _, out_props, _ = _rules(fake[b + 1:], b + 1)[0]
        self.assertFalse(props & out_props,
                         "判据把两条互不相干的声明当成打架了")

    def test_specificity_counts_an_extra_class(self):
        """控制用例：多挂一层类确实算更高——判据的修法得真管用。"""
        self.assertGreater(specificity(".cockpit .cmdbook-row"),
                           specificity(".cmdbook-row"))
        self.assertGreater(specificity(".cockpit .shortlist .ant-table-content > table"),
                           specificity(".shortlist .ant-table-content > table"))


if __name__ == "__main__":
    unittest.main()
