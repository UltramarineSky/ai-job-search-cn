# -*- coding: utf-8 -*-
"""盖住正文的浮层必须有出口：Esc 关、点外面关。

这一页栽过两次，第二次是我：

  ① 用户弹层（`App.tsx` 的 `userPanel`）—— `position:absolute; z-index:20`，
     展开时盖住正文，而出口只有来时那个按钮。修的时候留了整段注释。
  ② 「不想看什么」（`HidePrefs`）—— 2026-08-13 我加的，**一模一样的错**：
     实测截图里它正好盖住表头和前两行，Esc 没反应、点外面没反应。
     `App.tsx` 里那段注释就在上面，我没看见。

所以这条守卫盯的是**所有浮层**，不是某一个：新加一个盖正文的面板，
复制现有组件就自带出口。
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "web" / "src"

#: 会盖住正文的浮层（组件文件 → 它的容器 class）。加新的就往这里加。
OVERLAYS = [
    ("components/HidePrefs.tsx", "hide-body"),
]


class OverlaysHaveAnExit(unittest.TestCase):

    def test_each_overlay_closes_on_escape_and_outside_click(self):
        for f, cls in OVERLAYS:
            src = (SRC / f).read_text(encoding="utf-8")
            with self.subTest(file=f):
                self.assertIn('"Escape"', src, f"{f}：Esc 关不掉")
                self.assertIn("mousedown", src, f"{f}：点外面关不掉")
                self.assertIn("removeEventListener", src,
                              f"{f}：监听没摘，关掉之后还在吃全局事件")

    def test_the_outside_click_ignores_the_trigger(self):
        """点在触发按钮上不能也走「关」——那会变成「关了又开」，看着像没反应。"""
        src = (SRC / "components/HidePrefs.tsx").read_text(encoding="utf-8")
        self.assertIn("contains(e.target", src)

    def test_overlays_are_actually_positioned(self):
        """这条守卫只对**真的浮起来**的东西有意义。它要是变成普通块元素了，
        名单该更新——不然守着一个不存在的问题。"""
        css = (ROOT / "web" / "src" / "theme" / "cockpit.css").read_text(encoding="utf-8")
        for _, cls in OVERLAYS:
            with self.subTest(cls=cls):
                # 同一个 class 在文件里可能有多条规则（媒体查询里还有一条），
                # 而媒体查询那条排在前面——只看第一处会漏判。任一处浮起来就算。
                blocks = re.findall(rf"\.{cls}\s*\{{([^{{}}]*)\}}", css)
                self.assertTrue(blocks, f".{cls} 的样式找不到了")
                self.assertTrue(any("position: absolute" in b for b in blocks),
                                f".{cls} 不再是浮层了——这条守卫该更新名单")
