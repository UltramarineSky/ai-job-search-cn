"""共享 Typst 模板的中文字体回退链必须覆盖 Windows / macOS / Linux 三平台。

为什么值得一条测试盯住：**字体缺失是静默失败**。typst 在中文字体一个都没装时
只打印 `warning: unknown font family`、**exit 0**、照样产出 PDF，而且 PDF 文本层
完整可提取 —— 于是 `/job-apply` 的 ATS 文本层校验也会通过。用户拿到的是一份渲染成
豆腐块、却过了全部自动检查的简历。

此前两份模板的回退链是 `("Noto Sans SC", "Microsoft YaHei", "SimHei", "DengXian")`，
后三个全是 Windows 字体，注释却写着「回退到系统自带中文字体」。macOS 用户按
SETUP.md 走（`brew install typst`，而 README 把 Noto 写成「推荐」）就会四个全落空。
"""

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

#: 每个平台至少要有一个字体族在回退链里。族名按 typst `typst fonts` 的叫法。
PLATFORM_FONTS = {
    "Windows": ("Microsoft YaHei", "SimHei", "DengXian", "SimSun"),
    "macOS": ("PingFang SC", "Hiragino Sans GB", "STHeiti", "Songti SC", "STSong"),
    "Linux": ("Noto Sans CJK SC", "Noto Serif CJK SC", "WenQuanYi Zen Hei",
              "Source Han Sans SC", "Source Han Serif SC"),
}

#: 跨平台首选：开源、可免费商用，三平台手动安装后都能用。必须排在回退链最前。
PREFERRED_FIRST = "Noto Sans SC"

SHARED_TEMPLATES = ("resume/template.typ", "cover_letter/template.typ")


def _font_lists(text: str) -> dict:
    """抽出 `#let <名> = ( … )` 形式的字体元组，返回 {变量名: [字体族, …]}。"""
    out = {}
    for m in re.finditer(r"#let\s+(\S+)\s*=\s*\((.*?)\)", text, re.S):
        name, body = m.group(1), m.group(2)
        fonts = re.findall(r'"([^"]+)"', body)
        if fonts:
            out[name] = fonts
    return out


class SharedTemplateFontTests(unittest.TestCase):
    def test_shared_templates_exist(self):
        for rel in SHARED_TEMPLATES:
            self.assertTrue((REPO_ROOT / rel).is_file(), f"{rel} 不存在")

    def test_sans_chain_covers_all_three_platforms(self):
        for rel in SHARED_TEMPLATES:
            text = (REPO_ROOT / rel).read_text(encoding="utf-8")
            lists = _font_lists(text)
            self.assertIn("中文字体", lists, f"{rel}: 找不到 `中文字体` 回退链")
            chain = lists["中文字体"]
            for platform, candidates in PLATFORM_FONTS.items():
                self.assertTrue(
                    any(c in chain for c in candidates),
                    f"{rel} 的 `中文字体` 回退链没有任何 {platform} 字体。"
                    f"字体全缺时 typst 只 warning、exit 0、文本层仍可提取，"
                    f"ATS 校验也会通过 —— 用户会静默拿到豆腐块简历。"
                    f"当前链：{chain}",
                )

    def test_serif_chain_covers_all_three_platforms(self):
        for rel in SHARED_TEMPLATES:
            text = (REPO_ROOT / rel).read_text(encoding="utf-8")
            lists = _font_lists(text)
            self.assertIn("中文衬线", lists, f"{rel}: 找不到 `中文衬线` 回退链")
            chain = lists["中文衬线"]
            for platform, candidates in PLATFORM_FONTS.items():
                self.assertTrue(
                    any(c in chain for c in candidates),
                    f"{rel} 的 `中文衬线` 回退链没有任何 {platform} 字体。当前链：{chain}",
                )

    def test_open_font_comes_first(self):
        """开源字体排第一，保证三平台渲染一致（其余都是各平台私有字体）。"""
        for rel in SHARED_TEMPLATES:
            chain = _font_lists((REPO_ROOT / rel).read_text(encoding="utf-8"))["中文字体"]
            self.assertEqual(chain[0], PREFERRED_FIRST,
                             f"{rel}: 回退链首位应是 {PREFERRED_FIRST}，实际是 {chain[0]}")


if __name__ == "__main__":
    unittest.main()
