# -*- coding: utf-8 -*-
"""样式表里不留死 class。

死 CSS 的害处不是几行字节，是**误导**：下一个人看到 `.triage-chip` 会以为
界面上有这么个标记，照着它的配色去做新东西，或者花时间找它在哪渲染。

2026-08-13 扫出一个：`.triage-chip`（「粗筛」标记的样式）。那个标记早就撤了
——改成只标少数派「读过 JD」，因为 84 行里 80 行是粗筛，标它等于满屏噪音。
样式留了下来，还被另一处注释当成同族点名。

## 2026-08-22：这份判据自己曾经**结构性地不可能失败**

逃生口原来写成 `re.search(rf"[\\w.]{c}|{c}\\(", css)`，本意是排掉注释里
被粗正则捞进来的函数名。可 `[\\w.]` 里的那个点，正好匹配这个 class
**自己那条规则的选择器**（`.deep-chip` 里的 `.`）——于是**每一个** class
都命中逃生口，`dead` 恒为空。

旁边还坐着一条名叫「变异内建」的控制用例，而它在测试里**自己重写了一遍**
`re.findall`，从没调用过真判据——所以真判据坏成这样，它照样绿。
两个一起绿着，放过了两个真死的类（`deep-chip`、`stamp-row`）。

现在：判据收进 `_dead()` 一处，控制用例调的就是它。
**变异测试必须调用被测的那段代码，否则它证明的只是自己。**
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CSS = ROOT / "web" / "src" / "theme" / "cockpit.css"

#: 不参与检查的前缀：antd 自己的、CSS-in-JS 生成的、伪类/伪元素关键字。
SKIP = re.compile(r"^(ant-|css-|hover|focus|active|first|last|nth|not|is|where|has)")

#: 由模板串拼出来的 class（`ob-${b.k}`），静态搜不到，逐个豁免并写明来源。
DYNAMIC = {
    "ob-约面或更远": "OutcomeStats.tsx 的 `ob-${b.k}`，k 来自后端 buckets",
    "ob-被拒": "OutcomeStats.tsx 的 `ob-${b.k}`，k 来自后端 buckets",
}


class NoDeadCss(unittest.TestCase):

    @staticmethod
    def _dead(css: str, src: str) -> list:
        """`css` 里定义了、而 `src` 里没人用的 class。**判据只有这一份。**

        **注释先剥掉。** 这份 CSS 的注释里满是散文写的点号名字
        （`document.styleSheets`、互相引用的 `.rail-guide`），它们不是选择器，
        留着只会制造假阳性——而正是为了压掉那些假阳性，才有了当初那个
        把整条判据废掉的逃生口。剥注释是治因，逃生口是治果。
        """
        css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
        dead = []
        for c in sorted(set(re.findall(r"\.([a-z][\w-]{2,})", css))):
            if SKIP.match(c) or c in DYNAMIC or c in src:
                continue
            # `color-mix(` 这类函数名会被上面那个粗正则捞进来，排掉。
            # **不要再加 `[\w.]` 那一支**——它会匹配到 class 自己的选择器。
            if re.search(rf"{re.escape(c)}\(", css):
                continue
            dead.append(c)
        return dead

    def test_the_detector_can_fail(self):
        """变异内建：塞一个查无此处的 class，**走真正那条判据**，必须被抓到。"""
        fake = CSS.read_text(encoding="utf-8") + "\n.zzz-not-used { color: red; }\n"
        self.assertIn(
            "zzz-not-used", self._dead(fake, ""),
            "塞了一个明摆着没人用的 class，判据没报——它抓不到任何东西")

    def test_every_class_is_used(self):
        src = "\n".join(p.read_text(encoding="utf-8")
                        for p in (ROOT / "web" / "src").rglob("*.ts*"))
        dead = self._dead(CSS.read_text(encoding="utf-8"), src)
        self.assertEqual(dead, [],
                         "这些 class 没人用——留着会让下一个人以为界面上有它：\n  "
                         + "\n  ".join(dead))

    def test_dynamic_exemptions_are_justified(self):
        for c, why in DYNAMIC.items():
            with self.subTest(cls=c):
                self.assertGreater(len(why), 10, f"{c} 的豁免理由太短")


if __name__ == "__main__":
    unittest.main()
