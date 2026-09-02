# -*- coding: utf-8 -*-
"""五档判词在 TS 里又写了一份，而跨语言那道缝没人钉。

正本是 `_cli.VERDICTS`。`test_shared_vocab_single_source` 专门拦「又抄了一份」
—— 它这个会话里抓过我两次 —— **可它只扫 `tools/*.py` 与 `tests/*.py`**。
`web/src/theme/tokens.ts` 里那一行整整齐齐地躺着：

    export type Verdict = "强匹配" | "值得投" | "可以考虑" | "不建议" | "跳过";
    export const verdictColor: Record<Verdict, string> = { 强匹配: …, … };

`import` 跨不过语言边界，抄一份是**必须的**；没人钉住两边相等才是问题
（`test_every_job_lands_somewhere` 的原话：「两份词表跨语言，import 不过去，
只能靠守卫钉」—— 那条钉的是硬门前缀，判词这一份漏了）。

## 已经钉住的只有前三档

`test_one_number_per_concept` 把 `App.tsx` 的 `SELLABLE` 钉到
`export_web_data.SELLABLE_VERDICTS`。那是「能不能进可投名单」的白名单，
只有三档。**后两档（`不建议` / `跳过`）和整个 union 的成员资格没人管**：

- Python 改名一档 → TS 的 union 与 `verdictColor` 都不会红（数据是
  `string`，类型检查看不见），那一档的判词章掉色或落回默认。
- Python 新增一档 → `verdictColor` 缺一格，`Record` 的类型完整性也保证不了
  （新档在 TS 那边根本不存在）。

## 判据钉的是集合与顺序

顺序也要一致：`_cli.VERDICTS` 是**从好到差**排好的，面板别处按它切片
（`VERDICTS[:3]` 就是可投那三档）。两边顺序不同时，切片的语义就断了。
"""
import pathlib
import re
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import _cli  # noqa: E402

TOKENS = (ROOT / "web" / "src" / "theme"
          / "tokens.ts").read_text(encoding="utf-8")


def _union() -> list:
    m = re.search(r"export type Verdict\s*=\s*([^;]+);", TOKENS)
    if not m:
        return []
    return re.findall(r'"([^"]+)"', m.group(1))


def _tone_keys() -> list:
    m = re.search(r"export const verdictColor: Record<Verdict, string> = \{"
                  r"([\s\S]*?)\};", TOKENS)
    if not m:
        return []
    return re.findall(r"^\s*([^\s:]+)\s*:", m.group(1), re.M)


class TheRulerWouldLightUp(unittest.TestCase):
    """两个抽取器都要真取到东西 —— 取空了下面全是在比两个空表。"""

    def test_the_union_is_parsed(self):
        self.assertEqual(len(_union()), 5, f"union 解析成了 {_union()}")

    def test_the_tone_map_is_parsed(self):
        self.assertEqual(len(_tone_keys()), 5, f"色表解析成了 {_tone_keys()}")

    def test_the_source_has_five(self):
        self.assertEqual(len(_cli.VERDICTS), 5)


class TheTwoSidesAgree(unittest.TestCase):

    def test_the_union_matches_the_source(self):
        self.assertEqual(
            _union(), list(_cli.VERDICTS),
            "`tokens.ts` 的 Verdict 和 `_cli.VERDICTS` 对不上 —— "
            "改名的那一档在面板上会掉色，新增的那一档 TS 里根本不存在")

    def test_the_tone_map_covers_every_band(self):
        self.assertEqual(
            sorted(_tone_keys()), sorted(_cli.VERDICTS),
            "每一档都要有语义色 —— 缺一格那一档的判词章会落回默认色，"
            "而颜色正是这一页读判词的第一眼")

    def test_the_order_is_the_same(self):
        """顺序不是装饰：面板别处按它切片（`VERDICTS[:3]` = 可投那三档）。"""
        self.assertEqual(_union()[0], _cli.VERDICTS[0], "最好的那一档不一样")
        self.assertEqual(_union()[-1], _cli.VERDICTS[-1], "最差的那一档不一样")

    def test_the_first_three_are_the_sellable_ones(self):
        """跟 `App.tsx` 的 `SELLABLE` 是同一批 —— 那一份由
        `test_one_number_per_concept` 钉着，这里只确认两处说的是同一件事。"""
        app = (ROOT / "web" / "src" / "App.tsx").read_text(encoding="utf-8")
        m = re.search(r"const SELLABLE = \[(.+?)\];", app, re.S)
        self.assertIsNotNone(m, "App.tsx 里的 SELLABLE 找不到了")
        self.assertEqual(re.findall(r'"([^"]+)"', m.group(1)),
                         list(_cli.VERDICTS[:3]))


class TheGapThisCameFrom(unittest.TestCase):
    """立这条守卫的理由：那条「又抄了一份」的检查够不着 web/src。"""

    def test_the_dup_scan_still_only_reads_python(self):
        src = (ROOT / "tests"
               / "test_shared_vocab_single_source.py").read_text(encoding="utf-8")
        self.assertNotIn('"web"', src,
                         "那条检查已经扫到 web/src 了 —— 这一份可以合并进去")
        self.assertIn('(ROOT / "tools").glob("*.py")', src)


if __name__ == "__main__":
    unittest.main()
