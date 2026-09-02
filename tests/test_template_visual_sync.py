"""简历与求职信两份共享模板的视觉令牌必须逐字一致。

## 为什么值得一条测试

这两份文档几乎总是一起发出去（投递邮件里一封信 + 一份简历）。观感不一致——
灰阶差一档、字重差一级、页边距差 2mm——会让整包材料显得是随手拼的。

而它们是**两个独立文件**，没有 import 关系：`users/<用户>/…/main.typ` 要求自包含
（见 AGENTS.md），跨目录 import 会破坏那条约束。代价就是令牌被复制了两份，
**改一边忘另一边是必然会发生的事**——这条测试就是拿来兜住它的。

## 判据

`#let <名> = <值>` 形式的设计令牌，两份模板里同名的必须字面量相同。
只盯**视觉身份**类令牌，不盯排版参数：正文字号、行距、首行缩进本来就该不同
（信是用来读的，简历是用来扫的），那些差异是刻意的。
"""

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

RESUME_TPL = "resume/template.typ"
LETTER_TPL = "cover_letter/template.typ"

#: 必须两边一致的标量令牌（灰阶与字重）。这些构成「同一套材料」的视觉身份。
SHARED_SCALARS = ("墨", "次", "淡", "常规", "加重", "衬线粗")

#: 必须两边一致的字体回退链。
SHARED_CHAINS = ("中文字体", "中文衬线")

#: 页边距也要一致——两份文档叠在一起时页面几何不同会很显眼。
MARGIN_RE = re.compile(r"margin:\s*\(x:\s*([\d.]+cm),\s*y:\s*([\d.]+cm)\)")


def _scalars(text: str) -> dict:
    """抽 `#let 名 = 值`（单行、非元组）的字面量，值按去掉行尾注释后的原文比较。

    名字用 `[^\\s=(]+` 而不是 `\\S+`：后者会把 `#let section(标题) = {` 里的
    `section(标题)` 一并吞掉。值不能用 `[^\\n(]+` 排除括号——`rgb("#111111")`
    本身就带括号，那样写会一个令牌都抽不到（而且是**静默**抽不到，全部比较恒绿）。
    """
    out = {}
    for m in re.finditer(r"^#let\s+([^\s=(]+)\s*=\s*(.+)$", text, re.M):
        名 = m.group(1)
        值 = m.group(2).split("//")[0].strip()
        if 值.startswith("("):      # 元组（字体链）走 _chains，不在这里比
            continue
        out[名] = 值
    return out


def _chains(text: str) -> dict:
    """抽 `#let 名 = ( "a", "b", … )` 形式的字体链。"""
    out = {}
    for m in re.finditer(r"#let\s+(\S+)\s*=\s*\((.*?)\)", text, re.S):
        fonts = re.findall(r'"([^"]+)"', m.group(2))
        if fonts:
            out[m.group(1)] = fonts
    return out


class SharedTemplatesLookLikeOneFamily(unittest.TestCase):

    def setUp(self):
        self.resume = (REPO_ROOT / RESUME_TPL).read_text(encoding="utf-8")
        self.letter = (REPO_ROOT / LETTER_TPL).read_text(encoding="utf-8")

    def test_the_scan_finds_the_tokens(self):
        """控制用例：判据真的抽到了东西，否则下面几条全是空跑。"""
        for name, text in (("简历", self.resume), ("求职信", self.letter)):
            got = _scalars(text)
            missing = [t for t in SHARED_SCALARS if t not in got]
            self.assertEqual(
                missing, [],
                f"{name}模板里抽不到这些令牌：{missing}。"
                f"要么模板改了写法、要么判据失效——不要直接放宽判据，先看模板。")

    def test_gray_scale_and_weights_match(self):
        r, l = _scalars(self.resume), _scalars(self.letter)
        bad = [f"{t}: 简历={r.get(t)!r} 求职信={l.get(t)!r}"
               for t in SHARED_SCALARS if r.get(t) != l.get(t)]
        self.assertEqual(
            bad, [],
            "两份共享模板的视觉令牌不一致：\n  " + "\n  ".join(bad)
            + f"\n它们几乎总是一起发出去，观感不一致会显得材料是拼的。"
            f"\n（{RESUME_TPL} 与 {LETTER_TPL}）")

    def test_font_chains_match(self):
        r, l = _chains(self.resume), _chains(self.letter)
        bad = [f"{c}: 简历={r.get(c)} 求职信={l.get(c)}"
               for c in SHARED_CHAINS if r.get(c) != l.get(c)]
        self.assertEqual(bad, [], "两份共享模板的字体回退链不一致：\n  " + "\n  ".join(bad))

    def test_page_margins_match(self):
        rm = MARGIN_RE.search(self.resume)
        lm = MARGIN_RE.search(self.letter)
        self.assertIsNotNone(rm, f"{RESUME_TPL}: 抽不到页边距，判据可能失效")
        self.assertIsNotNone(lm, f"{LETTER_TPL}: 抽不到页边距，判据可能失效")
        self.assertEqual(
            rm.groups(), lm.groups(),
            f"页边距不一致：简历 {rm.groups()}、求职信 {lm.groups()}。"
            f"两份文档叠在一起时页面几何不同会很显眼。")

    def test_the_comparison_can_actually_fail(self):
        """判据自检：喂两份不同的令牌，必须认出来。"""
        a = _scalars('#let 墨 = rgb("#111111")\n')
        b = _scalars('#let 墨 = rgb("#000000")\n')
        self.assertNotEqual(a.get("墨"), b.get("墨"), "认不出不同的令牌值")
        c = _scalars('#let 墨 = rgb("#111111")   // 行尾注释不该影响比较\n')
        self.assertEqual(a.get("墨"), c.get("墨"), "行尾注释干扰了比较")


if __name__ == "__main__":
    unittest.main()
