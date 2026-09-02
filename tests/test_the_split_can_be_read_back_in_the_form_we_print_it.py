# -*- coding: utf-8 -*-
"""那条正则读不回自己的输出。

`gap_split.FORMULA` 有两个用途：**回读**那两个分（`read_pair`）、
**从屏幕上剥掉算式**（`export_web_data.strip_weights`）。而剥的方式是把
`专业能力88×0.6+业务域25×0.4` **改写成** `专业能力 88 · 行业经验 25` ——
那正是 `AGENTS.md` 措辞表规定的、给用户看的写法。

于是照规矩写的深评（`| 技能与经验 | 67 | 专业能力 75 · 行业经验 55 |`）
这条正则**读不出来**：它认得算式，认不得自己印出去的那一版。

上一轮为同一件事放宽过一次，只加了词（`行业经验`）、没动分隔符 —— 半个修法。
实测代价 2026-08-27：一轮 `/job-auto` 出了 6 份深评，**6 份的 `四维` 全部
静默停在粗筛旧值**（例：库里 `70×0.6+55×0.4`，深评写的是 75/55）。
`writeback` 那句「两笔拆解不同即分叉」照跑，只是永远解析不出新值，于是
`test_skill_composition_is_computed` 报「算式算出 64 却写 61」——
报的是**旧**拆解对**新**合成分，看着像评估算错了，其实是没读进去。
"""
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import export_web_data as ex  # noqa: E402
import gap_split as gs  # noqa: E402


class ItReadsBothWaysOfWritingThePair(unittest.TestCase):
    CASES = [
        # 剥之前的算式形态（存量与新写的都有）
        ("专业能力88×0.6+业务域25×0.4", (88, 25)),
        ("专业 72×0.6+行业经验 70×0.4", (72, 70)),
        ("技术栈75×0.6+业务领域45×0.4", (75, 45)),
        ("专业能力80×0.6+业务域65", (80, 65)),   # 尾巴 ×0.4 可省，存量里有
        # 剥之后、也就是 AGENTS.md 规定的显示形态
        ("专业能力 75 · 行业经验 55", (75, 55)),
        ("技术栈 71 · 行业经验 70", (71, 70)),
        ("专业能力 80 · 行业经验 20 · 另有加分 +4", (80, 20)),
    ]

    def test_every_form_parses(self):
        for text, want in self.CASES:
            with self.subTest(text=text):
                m = gs.FORMULA.search(text)
                self.assertTrue(m, "读不出来")
                self.assertEqual((int(m.group(1)), int(m.group(2))), want)

    def test_it_reads_back_exactly_what_strip_weights_prints(self):
        """**这才是当初露出来的那一头。** 输出必须是自己的合法输入。"""
        for text, want in self.CASES:
            shown = ex.strip_weights(text)
            with self.subTest(printed=shown):
                m = gs.FORMULA.search(shown)
                self.assertTrue(m, f"剥完变成 {shown!r}，自己读不回来了")
                self.assertEqual((int(m.group(1)), int(m.group(2))), want)

    def test_stripping_twice_changes_nothing(self):
        for text, _ in self.CASES:
            once = ex.strip_weights(text)
            self.assertEqual(ex.strip_weights(once), once, f"{text!r} 剥两次不一样")

    def test_the_formula_still_never_reaches_the_screen(self):
        """放宽是为了多认一种，不是为了让算式活下来。"""
        for text, _ in self.CASES:
            shown = ex.strip_weights(text)
            for w in ("×0.6", "x0.6", "×0.4", "业务域"):
                self.assertNotIn(w, shown, f"{w} 漏到屏幕上了：{shown!r}")


class ItStillRefusesWhatIsNotAPair(unittest.TestCase):
    """放宽分隔符不等于见两个数就认。"""

    def test_a_bare_pair_of_numbers_is_not_enough(self):
        for text in ("75 · 55", "这个岗 30-60k，团队 85 人",
                     "专业能力 75 · 薪资与职级 55", "行业经验 55 · 专业能力 75"):
            with self.subTest(text=text):
                self.assertIsNone(gs.FORMULA.search(text))

    def test_read_pair_returns_none_rather_than_guessing(self):
        self.assertIsNone(gs.read_pair({"rank_breakdown": {"四维": "说不清"}}))


class TheReasonIsWrittenNextToIt(unittest.TestCase):
    def test_the_comment_records_the_half_fix(self):
        src = (ROOT / "tools" / "gap_split.py").read_text(encoding="utf-8")
        seg = src[max(0, src.index("FORMULA = re.compile(") - 1400):
                  src.index("FORMULA = re.compile(")]
        self.assertIn("2026-08-27", seg, "实测数没带日期")
        self.assertIn("分隔符", seg, "没写清上一轮只放宽了词、没放宽分隔符")


if __name__ == "__main__":
    unittest.main()
