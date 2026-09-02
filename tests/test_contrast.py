"""配色的对比度：注释里写了数字，就得有人验。

`tokens.ts` 的调色板每一行都带着一个承诺——`lit` 写「≈15:1」、`faint` 写
「≈4.9:1，AA 下限」。这些数**从来没有东西验过**。改色时把某个灰调暗一档，
注释照旧写着 4.9，谁也不会发现——而那正是「再暗就读不清」的那条线。

## 按最亮的那层底算

舱内有三层面：`bay`（舱底）、`panel`（面板）、`panelRaised`（抬起/hover）。
同一个前景色在越亮的底上对比度越低，所以承诺只能按**最亮的那层**给，
这样在哪一层都成立。实测注释里的三个数正是这么算出来的。

## 焦点环是非文字元素，门槛 3:1

WCAG 1.4.11 管的是「非文字内容」——焦点环、图标、边框。antd 所有
`:focus-visible` 都取 `colorPrimaryBorder` 这一个令牌，而暗色算法会把它从
`colorPrimary` 推导成 `#204B47`：实测 1.76:1，画在深底上基本看不见，
键盘操作时不知道自己在哪。所以那个令牌必须显式给定并过 3:1。
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOKENS = ROOT / "web" / "src" / "theme" / "tokens.ts"

#: 三层面色，按亮度排序后取最亮的那层当基准
SURFACES = ["bay", "panel", "panelRaised"]

#: 正文色的 AA 门槛（WCAG 1.4.3，正常字号）
AA_TEXT = 4.5
#: 非文字元素的门槛（WCAG 1.4.11）——焦点环走这条
AA_NON_TEXT = 3.0


def relative_luminance(hex_color: str) -> float:
    """WCAG 2.x 的相对亮度。"""
    h = hex_color.lstrip("#")
    parts = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
           for c in parts]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contrast(a: str, b: str) -> float:
    hi, lo = sorted((relative_luminance(a), relative_luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def palette() -> dict:
    """`tokens.ts` 的 `palette` → `{名: #hex}`。"""
    src = TOKENS.read_text(encoding="utf-8")
    body = re.search(r"export const palette\s*=\s*\{(.*?)\n\}", src, re.S)
    assert body, "tokens.ts 里找不到 palette —— 调色板改名或搬走了"
    return {m.group(1): m.group(2)
            for m in re.finditer(r"(\w+)\s*:\s*\"(#[0-9A-Fa-f]{6})\"",
                                 body.group(1))}


def documented_claims() -> dict:
    """调色板注释里承诺的比值 → `{名: 数}`。写了 `≈7.5:1` 就按 7.5 验。"""
    src = TOKENS.read_text(encoding="utf-8")
    body = re.search(r"export const palette\s*=\s*\{(.*?)\n\}", src, re.S)
    return {m.group(1): float(m.group(2))
            for m in re.finditer(
                r"(\w+)\s*:\s*\"#[0-9A-Fa-f]{6}\"\s*,\s*//[^\n]*?≈\s*([\d.]+)\s*:\s*1",
                body.group(1))}


def lightest_surface(pal: dict) -> str:
    return max((s for s in SURFACES if s in pal),
               key=lambda s: relative_luminance(pal[s]))


class DocumentedRatiosAreTrue(unittest.TestCase):
    """注释里写的比值必须是真的——**注释本身就是断言**。"""

    def test_the_palette_documents_at_least_the_three_text_colors(self):
        """承诺没了，这条检查就成了无源之水。"""
        claims = documented_claims()
        for name in ("lit", "dim", "faint"):
            self.assertIn(name, claims,
                          f"{name} 的注释里不再写对比度了——那这条就没东西可验")

    def test_every_documented_ratio_holds_on_the_lightest_surface(self):
        pal, claims = palette(), documented_claims()
        base = lightest_surface(pal)
        bad = []
        for name, promised in claims.items():
            got = contrast(pal[name], pal[base])
            # ±0.6 的余量：注释写的是约数，但不能差到换一个档位
            if abs(got - promised) > 0.6:
                bad.append(f"{name}({pal[name]}) 对 {base}({pal[base]}) "
                           f"实测 {got:.2f}:1，注释写 ≈{promised}:1")
        self.assertEqual(bad, [],
                         "调色板的注释和实际色值对不上了：\n" + "\n".join(bad))

    def test_text_colors_clear_the_aa_floor_everywhere(self):
        """三层底都要过，所以按最亮那层算——在哪一层都成立才叫承诺。"""
        pal = palette()
        base = lightest_surface(pal)
        bad = [f"{n} 只有 {contrast(pal[n], pal[base]):.2f}:1"
               for n in ("lit", "dim", "faint", "data", "caution", "lock")
               if n in pal and contrast(pal[n], pal[base]) < AA_TEXT]
        self.assertEqual(bad, [],
                         f"这些字色在最亮的底（{base}）上读不清，AA 要 {AA_TEXT}:1：\n"
                         + "\n".join(bad))


class TheFocusRingIsVisible(unittest.TestCase):
    """antd 的焦点环走 `colorPrimaryBorder`，暗色算法推出来的值太暗。

    我们自己做的元素（`.rail-cell` / 表格行 / `.shelf-restore`）在 cockpit.css
    里用 `var(--data)` 画环，实测 8.6:1；antd 那半边不接管就是 1.76:1。
    只写一半，键盘用户在半个界面里看不见自己在哪。
    """

    def test_the_token_is_set_explicitly(self):
        src = TOKENS.read_text(encoding="utf-8")
        self.assertRegex(
            src, r"colorPrimaryBorder\s*:",
            "没有显式给 colorPrimaryBorder —— antd 暗色算法会把它推成 #204B47，"
            "对面板底只有 1.76:1，焦点环等于没有")

    def test_the_focus_ring_clears_the_non_text_floor(self):
        pal = palette()
        src = TOKENS.read_text(encoding="utf-8")
        m = re.search(r"colorPrimaryBorder\s*:\s*(?:palette\.(\w+)|\"(#[0-9A-Fa-f]{6})\")",
                      src)
        self.assertIsNotNone(m, "colorPrimaryBorder 的取值读不出来")
        color = pal[m.group(1)] if m.group(1) else m.group(2)
        base = lightest_surface(pal)
        got = contrast(color, pal[base])
        self.assertGreaterEqual(
            got, AA_NON_TEXT,
            f"焦点环 {color} 对最亮的底 {base}({pal[base]}) 只有 {got:.2f}:1，"
            f"WCAG 1.4.11 要 {AA_NON_TEXT}:1")


class TheDetectorCanActuallyFail(unittest.TestCase):
    """判据自检——走的是**同一个** `contrast`，不另抄一份算式。"""

    def test_known_pairs(self):
        # WCAG 规范里的两个端点：黑白 21:1、同色 1:1
        self.assertAlmostEqual(contrast("#FFFFFF", "#000000"), 21.0, places=2)
        self.assertAlmostEqual(contrast("#151C25", "#151C25"), 1.0, places=2)
        # antd 推导出来的那个焦点环色，就是这条规则要拦的
        self.assertLess(contrast("#204B47", "#1C2530"), AA_NON_TEXT)

    def test_the_claim_parser_reads_the_comment(self):
        claims = documented_claims()
        self.assertGreaterEqual(len(claims), 3,
                                f"注释里的比值只解析出 {len(claims)} 条")


if __name__ == "__main__":
    unittest.main()
