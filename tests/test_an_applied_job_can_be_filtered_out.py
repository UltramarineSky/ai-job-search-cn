# -*- coding: utf-8 -*-
"""「材料就绪」点开有 244 个，其中 83 个已经投出去了 —— 而没有开关能把它们滤掉。

「不想看什么」原来只有一条与「投过」有关的开关：**投过的公司，它别的岗也不显示**。
它藏的是「这家公司的**别的**岗」，藏不掉「**这一个**岗我已经发过了」。

默认视图（可以投的岗位）本来就不列已投的，所以这件事在首屏看不出来。
点开流水线格子之后才咬人 —— 实测活动用户 2026-08-26：

    材料就绪   244 个，其中已投 83 个（34%）
    可投档     133 个，其中已投 62 个

用户点进去要找的是「还没发的那批」，得先用眼睛把三分之一滤掉。

## 仍然默认关

已投的行上有状态按钮（约面了 / 挂了 / 没下文），藏掉就没地方点了。
要不要藏是他的选择，不是默认 —— 同「投过的公司」那条的判据。
"""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HID = (ROOT / "web" / "src" / "data" / "hidden.ts").read_text(encoding="utf-8")
UI = (ROOT / "web" / "src" / "components" / "HidePrefs.tsx").read_text(encoding="utf-8")


class TheSwitchExists(unittest.TestCase):
    def test_the_pref_has_the_field(self):
        # `re.M` 是必需的：assertRegex 默认不开多行，`^` 只匹配整串开头。
        self.assertTrue(re.search(r"^\s*applied: boolean;", HID, re.M),
                        "HiddenPrefs 里没有这个开关")

    def test_it_defaults_to_off(self):
        i = HID.index("export const EMPTY")
        self.assertIn("applied: false", HID[i:i + 200], "默认不是关的")

    def test_it_survives_a_reload(self):
        """存量结构少一个键不该让整份偏好失效 —— 逐字段兜底那一段要带上它。"""
        i = HID.index("export function loadHidden")
        self.assertIn("applied: Boolean(d?.applied)", HID[i:i + 900],
                      "读回来的时候没兜底，老用户刷新就丢")

    def test_it_is_compiled_for_the_hot_path(self):
        i = HID.index("export function compile")
        self.assertIn("applied: p.applied", HID[i:i + 400], "没进 compile，判定时读不到")

    def test_it_actually_hides(self):
        i = HID.index("export function isHidden")
        seg = HID[i:i + 700]
        self.assertIn("p.applied && job.applied", seg, "开关开着也不藏")


class TheTwoAppliedSwitchesAreDistinct(unittest.TestCase):
    """两条都叫「投过」，藏的不是一个东西 —— 面板上必须分得开。"""

    def test_both_are_offered(self):
        self.assertIn("已经投过的岗不显示", UI)
        self.assertIn("投过的公司，它别的岗也不显示", UI)

    def test_each_says_what_it_hides(self):
        self.assertRegex(UI, r"「可以投的岗位」本来就不列已投的",
                         "没说清这个开关到底在哪几张表上生效")
        self.assertRegex(UI, r"只藏这家公司的其它岗",
                         "另一条的说明丢了，两条就分不开了")

    def test_the_company_switch_still_keeps_the_applied_row(self):
        """按公司藏时，**那个投过的岗本身**照常显示 —— 不然找不到自己投了什么。"""
        i = HID.index("export function isHidden")
        self.assertIn("p.appliedCompanies && !job.applied", HID[i:i + 700],
                      "按公司藏把已投的那一行也藏了")


class ClearAllClearsEverything(unittest.TestCase):
    """**「全部清掉」不许再抄一份空值。**

    它原来就地写了 `{ appliedCompanies: false, companies: [], ... }`，
    于是加一个开关就有两处要同步。2026-08-26 加这条时 `tsc` 当场报少一个字段 ——
    要是哪天类型没管住，症状是「全部清掉」清不干净，而屏幕上没有任何提示。
    """

    def test_it_spreads_empty(self):
        self.assertIn("onChange({ ...EMPTY })", UI, "又把空值抄了一份")
        self.assertIn("EMPTY", UI.split(chr(10))[1], "没从 hidden.ts 引 EMPTY")

    def test_the_button_shows_when_this_switch_is_on(self):
        """只开了这一条时也得能清 —— 否则用户关不掉它。"""
        i = UI.index("const any =")
        self.assertIn("prefs.applied", UI[i:i + 200], "`any` 没算上这条开关")


if __name__ == "__main__":
    unittest.main()
