# -*- coding: utf-8 -*-
"""「分最高的 20 个」这条提示，说的必须是它真正数的那批。

原话是「**前 20 个可以投的岗**里，只有 0 个备好了材料」，而同一屏上：

    段头写着「可以投的岗位 **9**」
    这条提示数的是 `sellable` 按分排的前 20（含「可以考虑」那一档，实测 231 个）

**同一句话两个集合，同一屏上。** 和「主场」那次是同一类撞词。

那个 0 本身也误导：分数把两种深度混着排 —— 粗筛分只看标题和卡片，深评分读过
JD 正文。实测 2026-08-22 这前 20 名里 **14 个是粗筛**（最高那个 72 分连 JD 都没读），
而深评过的「值得投」最高才 66。于是「有材料的 0 个」看着像名单全空，
可同一屏的短名单上明明有 4 行挂着「材料就绪」。

不改排序（那是另一件事），但要说清这个 0 是怎么来的 ——
也正好解释了为什么该跑 `--top 20`：那条命令干的就是把这批猜测变成读过 JD 的评估。
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "web" / "src" / "App.tsx").read_text(encoding="utf-8")
#: 两种注释都剥 —— 注释里要引用旧文案说明为什么改（已栽过四次）。
_CODE = re.sub(r"\{/\*[\s\S]*?\*/\}|/\*[\s\S]*?\*/|^\s*//.*$", "", APP, flags=re.M)


def _banner() -> str:
    """渲染那一段。**别锚 `topReady.size` 的第一处** —— 那是声明区，
    离屏幕上那句话几百行远。这类定位错误已经犯过三次，每次都是断言在错的区域
    上求值、看着像功能没做。"""
    i = _CODE.index("分最高的 {topReady.size}")
    return _CODE[max(0, i - 200):i + 500]


class TheBannerNamesItsOwnPopulation(unittest.TestCase):
    def test_it_does_not_reuse_the_section_heading_words(self):
        """段头叫「可以投的岗位」，这条数的是另一批 —— 不许共用那句话。"""
        self.assertNotIn("个可以投的岗里", _CODE,
                         "又把两个不同的集合叫成同一个名字了")

    def test_it_says_it_is_the_top_scored(self):
        self.assertIn("分最高的", _banner(), "没说清它按什么挑的这 20 个")


class TheZeroIsExplained(unittest.TestCase):
    def test_the_coarse_count_is_computed(self):
        """判据 2026-08-26 收紧：`!evaluated` → `!evaluated && !jdRead`。

        粗筛也会读完整 JD（判词来源写着「粗筛（读过 JD 正文）」），它只是没做
        公司调研与双角色审稿。只看 `evaluated` 的话，这句「其中 N 个还没读过 JD」
        会把读过的那批也算进去 —— 实测当天没深评的 1429 个里 946 个其实读过。
        """
        self.assertIn("raw: top.filter((j) => !j.evaluated && !j.jdRead).length", _CODE,
                      "没数这前 20 里有几个是**真没读过 JD**的")

    def test_it_is_shown_only_when_there_are_any(self):
        """全是深评时不该多一句废话。"""
        self.assertIn("topReady.raw > 0", _banner(), "没有「有才说」的门槛")

    def test_it_says_where_the_score_came_from(self):
        """只说「没读过 JD」不够 —— 要说清那个分是粗筛给的，否则 0 还是没解释。"""
        self.assertRegex(_banner(), r"分是粗筛给的|粗筛给的",
                         "没说清那个分的来路")

    def test_the_ready_count_still_leads(self):
        """这条提示的主语仍是「有几个备好了材料」，粗筛那句是补充，别喧宾夺主。"""
        b = _banner()
        self.assertLess(b.index("topReady.ready"), b.index("topReady.raw"))

    def test_the_same_field_as_the_per_row_chip(self):
        """「没读过 JD」在逐行章和这里必须同源，不然两个数对不上。"""
        sl = (ROOT / "web" / "src" / "components"
              / "Shortlist.tsx").read_text(encoding="utf-8")
        self.assertIn("!job.evaluated", sl, "逐行那枚章不再看 evaluated 了")
        self.assertIn("!j.evaluated", _CODE, "这条提示用的不是同一个字段")


if __name__ == "__main__":
    unittest.main()
