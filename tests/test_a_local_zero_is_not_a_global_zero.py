# -*- coding: utf-8 -*-
"""「分最高的 20 个里，只有 0 个备好了材料」——这是这一页关于材料的唯一一句话。

它数的是**局部**（`sellable` 按分排的前 20），而用户读到的是全局：
「我手上什么都没有，得先去补材料」。实测活动用户 2026-08-23，同一时刻：

    前 20 个里备好的        0
    全表备好、还没发出去的  62   （58 个「可以考虑」· 4 个「值得投」）

那 62 份不是积压 —— 中位放了 3 天、最久 6 天，是**随时能发的存货**。
而发出去是整条流水线里唯一要人做的那一步
（`AGENTS.md`「只有一处要人：投出去那一下」）。

**一个局部的 0 盖住一个全局的 62，指的方向正好反了**：它让人去补材料
（花的是机器的工时），而该做的是先把手上这批发掉（花的是他自己的）。
这一族在本仓库反复出现：同一个数在两处是两个意思，而屏幕上只印一个。

顺带钉住排版：这一行断在 `</b>` 之后。JSX 里两个汉字之间的换行会折成一个空格，
第一版断在「随时能发——」后面，屏幕上就是「随时能发—— 它们」。
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "web" / "src" / "App.tsx").read_text(encoding="utf-8")
CSS = (ROOT / "web" / "src" / "theme" / "cockpit.css").read_text(encoding="utf-8")


class TheCountExists(unittest.TestCase):
    def test_it_is_computed(self):
        self.assertIn("readyToSend", APP, "没有「备好没发」这个数")

    def test_it_excludes_what_was_already_sent(self):
        """已投的岗材料也在，但它不是「随时能发」。"""
        m = re.search(r"readyToSend = useMemo\(\s*\(\) =>\s*([^,]+),", APP)
        self.assertIsNotNone(m, "找不到它的算法")
        self.assertIn("!applied(j)", m.group(1), "把已投的也算进去了")
        self.assertIn("j.materials", m.group(1))

    def test_it_counts_the_whole_sellable_list(self):
        """**不能只数前 20** —— 那就又变成同一个局部数了。"""
        m = re.search(r"readyToSend = useMemo\(\s*\(\) =>\s*([^,]+),", APP)
        self.assertIn("sellable", m.group(1))
        self.assertNotIn("slice(0, TOP_N)", m.group(1), "又只看了前 20")


class ItIsSaidInTheSameBreath(unittest.TestCase):
    """两个数必须在同一个框里说完 —— 分开说等于没说。"""

    def _band(self):
        #: **不要拿 `className="mat-gap"` 定位** —— 那个类名有两个横幅在用
        #: （另一个是「有 N 个岗卡住了，等你一句话」），而它排在前面。
        #: 锚在这一块独有的渲染条件 `materialsThin` 上，切到 `</div>` 为止；
        #: 也别按字符数切：这一块后来又加了几段长注释（「把这个数变成入口」），
        #: 固定窗口当场把要验的那句话挤到外面，断言在半截文本上求值。
        i = APP.index("{materialsThin && (")
        return APP[i:APP.index("\n            </div>", i)]

    def test_the_note_sits_inside_the_gap_band(self):
        self.assertIn("mat-gap-have", self._band(),
                      "「已经备好的」那句不在缺口那条横幅里")

    def test_it_only_shows_when_there_is_something(self):
        """一个都没有时不该多一句「你有 0 个」。"""
        self.assertIn("readyToSend > 0", self._band(), "没有「有才说」的门槛")

    def test_it_says_what_to_do_first(self):
        """只报数是个观察。要说出先做哪件。"""
        self.assertRegex(self._band(), r"先把这批发掉|先发",
                         "没说清补货和发货哪个在前")

    def test_it_explains_why_they_are_not_in_the_top_n(self):
        """不解释的话，两个数看着就是矛盾的：0 和 62 同框。"""
        self.assertRegex(self._band(), r"没进前|可以考虑",
                         "没说清这 62 个为什么不在上面那 20 里")

    def test_the_original_half_is_still_there(self):
        """**不许把缺口那句挤掉** —— 它回答的是另一个问题
        （分最高的那批备得怎么样），两句各有各的用。"""
        b = self._band()
        self.assertIn("topReady.ready", b)
        self.assertIn("/job-apply --top", b)


class TheLineBreaksWhereItIsSafe(unittest.TestCase):
    def test_the_break_is_at_a_tag_boundary(self):
        """JSX 把两个汉字之间的换行折成一个空格。断在标签边界后面才不留空格。"""
        i = APP.index('className="mat-gap-have"')
        seg = APP[i:APP.index("</span>", i)]
        # 标签是哪一个不重要（`</b>` 后来变成了 `</button>`），要保的是
        # 「文本之间的换行落在标签或表达式边界上」。
        self.assertRegex(seg, r"</(b|button)>\s*\n\s*\{",
                         "换行没落在标签边界上")
        # **先剥注释。** 那几段中文注释里全是汉字换行，扫它等于禁止写注释。
        code = re.sub(r"\{/\*.*?\*/\}", " ", seg, flags=re.S)
        self.assertNotRegex(code, r"[一-鿿]\s*\n\s*[一-鿿]",
                            "两个汉字之间断了行，屏幕上会多一个空格")


class TheColourSaysItIsGoodNews(unittest.TestCase):
    def test_it_does_not_reuse_the_warning_colour(self):
        """同一个黄框里两种含义的黄，读起来两条都是警告。
        而这一条报的是存货，不是缺口。"""
        i = CSS.index(".mat-gap-have b")
        self.assertIn("--data", CSS[i:i + 120], "沿用了告警色")
        self.assertNotIn("--caution", CSS[i:i + 120])

    # 「这一块用到的 CSS 变量都定义了没」**不在这儿查** ——
    # `test_css_and_cjk_text.EveryCssVarIsDefined` 全库扫一遍，
    # 整份样式表里没有未定义的变量，这一块自然也没有。
    #
    # 这里原来抄了一份按块扫的，而且抄的是**正本已经修掉的那个写法**：
    # 用 `(?m)^\s*--x\s*:` 找定义，一行里写多个变量时只认得第一个
    # （`--ink:#17212b; --ink2:…; --ink3:…;` 会把后两个判成没定义，
    # 实测一次误报 13 个）。抄件不会跟着正本一起被修 —— 2026-08-31 删。


if __name__ == "__main__":
    unittest.main()
