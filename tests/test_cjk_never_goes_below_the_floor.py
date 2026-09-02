# -*- coding: utf-8 -*-
"""屏幕上的**汉字**不许小于 12px。

## 为什么

`web/src/theme/tokens.ts` 顶上第 3 条自己写着：

> **中文优先的字号下限**。中文字形在同等 px 下比拉丁更吃尺寸，
> 所以 fontSize 基线抬到 14.5、fontSizeSM 抬到 13——低于 13 的中文在深底上读不清。

而这条规矩**一次都没被检查过**。2026-08-22 拿浏览器逐个元素量了一遍，
当场扫出九处带汉字却压在 11 / 11.5px 的样式：

    .deep-chip「读过 JD」      .mat-chip「材料就绪」    .sent-chip「已投」
    .rec-chip「推荐先投」       .co-chip「这家投过」      .funnel-chip「另有 N 个已投出去」
    .cmdbook-bare-k「不填参数」（一屏 20 处）           .portal-jd「职位描述存了 66%」
    .portal-halt / .portal-label-blocked「被拦住了」

最后两个尤其说明问题：它们所在那次改动的注释写着「收起来时这是**唯一看得见的
信号**」——而它同时是整页最小的中文。**规矩写在文档里，没写成判据，就是这个下场。**

## 判据怎么定

拉丁与纯数字不受这条限制（`.rail-step` 的序号、`.mono-label`、版本号都是 11px，
那是有意的层级）。所以只挑**真的会显示汉字**的类：在 `.tsx` 里找到这个类名，
看它所在那段 JSX 里有没有中文字面量。

宁可漏报不可误报：够不着的（动态拼的字符串、从数据来的文案）这条测不到，
它守的是「有人在样式表里写下一个小于 12px 的字号，而那个类的模板里明摆着有汉字」。
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CSS = ROOT / "web" / "src" / "theme" / "cockpit.css"
TSX = sorted((ROOT / "web" / "src").rglob("*.tsx"))

#: 中文最小字号。与 `.kicker` 齐平——它是自家中文小标签里最小的那个。
FLOOR = 12.0

CJK = re.compile(r"[一-鿿]")
#: `.foo, .bar em { … font-size: 11px … }`
RULE = re.compile(r"([^{}]+)\{([^{}]*)\}", re.S)
SIZE = re.compile(r"font-size:\s*([\d.]+)px")


def small_classes() -> dict:
    """`{类名: 字号}`，只收小于下限的。"""
    css = CSS.read_text(encoding="utf-8")
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)      # 注释里的例子不算
    out = {}
    for sel, body in RULE.findall(css):
        m = SIZE.search(body)
        if not m or float(m.group(1)) >= FLOOR:
            continue
        for cls in re.findall(r"\.([a-zA-Z][\w-]*)", sel):
            out[cls] = min(float(m.group(1)), out.get(cls, 99))
    return out


def classes_that_show_chinese() -> dict:
    """`{类名: 例子}` —— 模板里这个类所在的那段 JSX 出现过中文字面量。"""
    out = {}
    for f in TSX:
        src = f.read_text(encoding="utf-8")
        src = re.sub(r"\{/\*.*?\*/\}", "", src, flags=re.S)   # JSX 注释不是屏幕上的字
        for m in re.finditer(r'className=(?:"([^"]+)"|\{"([^"]+)"|\{`([^`]+)`)', src):
            names = (m.group(1) or m.group(2) or m.group(3) or "")
            # **只看这个元素自己的直接文本**：从属性区结束的 `>` 起，到下一个 `<`。
            #
            # 原来取的是 className 之后 220 个字符 —— 那会串到隔壁元素上去，
            # 当场误报了 `.mono-label`：它自己只装数字（`{hiddenCount}`），
            # 而窗口里扫到了紧挨着的那个「万」。而代码里明写着「中文不能进
            # .mono-label」，误报一个守得好好的类，比漏报还坏。
            tail = src[m.end():m.end() + 400]
            gt = tail.find(">")
            seg = tail[gt + 1:tail.find("<", gt)] if gt >= 0 else ""
            hit = CJK.search(seg)
            if not hit:
                continue
            for cls in re.findall(r"[a-zA-Z][\w-]*", names):
                out.setdefault(cls, seg[max(0, hit.start() - 8):hit.start() + 14].strip())
    return out


class ChineseStaysReadable(unittest.TestCase):

    def test_there_is_something_to_check(self):
        """自检：两边都抽得出东西，否则下面那条对着空气跑。"""
        self.assertGreater(len(small_classes()), 3, "CSS 里一条小字号都没抽到")
        self.assertGreater(len(classes_that_show_chinese()), 20, "模板里一个带中文的类都没抽到")

    def test_no_chinese_is_set_below_the_floor(self):
        small, cn = small_classes(), classes_that_show_chinese()
        bad = [f"{c}：{small[c]}px　「{cn[c]}」" for c in sorted(small) if c in cn]
        self.assertEqual(
            bad, [],
            f"这些类的字号低于 {FLOOR}px，而它们在模板里显示中文——"
            "tokens.ts 自己写着「低于 13 的中文在深底上读不清」：\n  "
            + "\n  ".join(bad)
            + "\n拉丁和纯数字不受此限（序号、版本号等 11px 是有意的层级）；"
            "\n真要小于它，就把那段文案换成数字或拉丁。")


if __name__ == "__main__":
    unittest.main()
