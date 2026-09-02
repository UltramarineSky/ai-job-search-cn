# -*- coding: utf-8 -*-
"""规则是对的，判据太字面 —— 中间插个副词就漏。

2026-08-25 用户读了一份刚生成的开场白，当场指出这句：

    你们说的可审核、可恢复、可复用的任务树，正是我这两年一直在想的事。

「这类根本不符合中文习惯」。而 `_cli.greeting_hits` 说它干净。

规则本来就在 `03-writing-style.md`「句式：中文不这么说」那一节，还带着硬证据：
「…，是我…的事」在 **1486 份真人 JD 里 0 次**、在我们的产出里 13 次 ——
「不是风格偏好，是口音」。**漏的是判据，不是规则**：

    翻译腔（动作当主语）  要求 `，\\s*是我`      → 「，**正**是我…」多一个字就断了
    翻译腔（自我认证）    要求「正是我」紧跟「做的」 → 中间插「这两年一直在想」就断了

放宽之后拿同一份参照语料复量：**1497 份真人 JD 上放宽前后都是 0 命中**。
判据的正当性从来不是「读着像」，是「真人写作里出现几次」—— 放宽不能动摇那个 0。

## 这一族还有一个更该抓的动词

原来只认「做的」。而「正是我一直在**想**的事」比「在做的」更虚：
对面在筛人，**想过不算做过**。新判据把「想」一并收了。
"""
import json
import pathlib
import re
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import _cli  # noqa: E402

STYLE = (ROOT / "workflows" / "reference"
         / "03-writing-style.md").read_text(encoding="utf-8")


def cats(s: str) -> set:
    return {c for c, _w in _cli.greeting_hits(s)}


class TheSentenceThatSlippedThroughIsCaught(unittest.TestCase):

    def test_the_exact_sentence(self):
        """就是用户挑出来的那一句。"""
        got = cats("你们说的可审核、可恢复、可复用的任务树，正是我这两年一直在想的事。")
        self.assertTrue(got, "用户一眼看出不对，判据说干净 —— 那是判据的问题")
        self.assertIn("翻译腔（自我认证）", got)

    def test_an_adverb_before_shi_wo(self):
        """「，正是我…的事」「，就是我…的事」—— 多一个副词不该断掉判据。"""
        for adv in ("正", "就", "恰", "才"):
            with self.subTest(adv=adv):
                self.assertIn("翻译腔（动作当主语）",
                              cats(f"把接口定清楚，{adv}是我天天在干的事"))

    def test_no_adverb_still_caught(self):
        """放宽不许把原来抓得到的放跑。"""
        self.assertIn("翻译腔（动作当主语）", cats("把 X 定清楚，是我天天在干的事"))
        self.assertIn("翻译腔（自我认证）", cats("这正是我在做的"))

    def test_an_adverbial_in_the_middle(self):
        for mid in ("", "一直", "这两年一直", "从去年开始"):
            with self.subTest(mid=mid):
                self.assertIn("翻译腔（自我认证）", cats(f"正是我{mid}在做的事"))

    def test_thinking_counts_too(self):
        """**想过不算做过。** 「在想的」比「在做的」更虚，更该抓。"""
        self.assertIn("翻译腔（自我认证）", cats("正是我一直在想的事"))

    def test_the_rewritten_greeting_is_clean(self):
        """改法要能通过 —— 否则这条规则等于禁止表达这个意思。"""
        ok = "任务树要能审、能恢复、能复用——我做自己的工具时就照这个思路走"
        self.assertEqual(cats(ok), set())

    def test_plain_chinese_is_never_flagged(self):
        """真人 JD 那种写法（动词打头）一个都不许报。"""
        for s in ("负责 Agent 的推理调度与资源管理",
                  "主导大模型项目落地的关键技术工作",
                  "我天天在用这两个工具",
                  "这两个工具我天天在用"):
            with self.subTest(s=s):
                self.assertEqual(cats(s), set())


class TheWideningDidNotCostPrecision(unittest.TestCase):
    """判据的正当性是「真人写作里出现 0 次」—— 放宽不能动摇那个 0。"""

    def _jds(self):
        p = ROOT / ".active_user"
        if not p.is_file():
            self.skipTest("没有活动用户")
        det = (ROOT / "users" / p.read_text(encoding="utf-8").strip()
               / "job_scraper" / "details")
        if not det.is_dir():
            self.skipTest("没有 JD 语料")
        out = []
        for f in det.glob("*.json"):
            try:
                d = json.loads(f.read_text(encoding="utf-8"))
            except (ValueError, OSError):
                continue
            if (d.get("description") or "").strip():
                out.append(d["description"])
        if len(out) < 500:
            self.skipTest(f"JD 语料只有 {len(out)} 份，验不出误报率")
        return out

    def test_the_two_patterns_never_fire_on_real_jds(self):
        """**这是整条规则的地基。** 真人写作里开始命中，就说明判据抓错了东西。"""
        jds = self._jds()
        for name in ("翻译腔（动作当主语）", "翻译腔（自我认证）"):
            with self.subTest(name=name):
                rx = re.compile(_cli.STYLE_PATTERNS[name])
                hit = [t for t in jds if rx.search(t)]
                self.assertEqual(
                    len(hit), 0,
                    f"「{name}」在 {len(jds)} 份真人 JD 上命中了 {len(hit)} 份 —— "
                    f"放宽过头了。例：{(hit[0][:60] if hit else '')}")

    def test_the_corpus_is_big_enough_to_mean_something(self):
        """对照用例：语料真的读到了 —— 否则上一条恒绿。"""
        self.assertGreater(len(self._jds()), 500)


class TheRuleItLeansOnIsStillThere(unittest.TestCase):

    def test_the_style_section_exists(self):
        self.assertIn("## 句式：中文不这么说", STYLE)

    def test_it_still_carries_the_zero_evidence(self):
        """「1486 份真人 JD 里 0 份」是这一族的全部正当性。"""
        i = STYLE.index("## 句式：中文不这么说")
        seg = STYLE[i:i + 2600]
        self.assertIn("1486 份真人 JD", seg)
        self.assertIn("不是风格偏好，是口音", seg)

    def test_the_three_rules_are_still_listed(self):
        i = STYLE.index("## 句式：中文不这么说")
        seg = STYLE[i:i + 3200]
        for k in ("是我天天在干的事", "这正是我在做的"):
            with self.subTest(k=k):
                self.assertIn(k, seg)

    def test_the_widening_is_recorded_where_the_pattern_lives(self):
        """为什么放宽、放宽到哪 —— 写在正则旁边，不写在别处。"""
        src = (ROOT / "tools" / "_cli.py").read_text(encoding="utf-8")
        i = src.index("STYLE_PATTERNS = {")
        seg = src[i:i + 2600]
        self.assertIn("多一个「正」字就断了", seg)
        self.assertIn("想过不算做过", seg)
        self.assertIn("1497 份真人 JD", seg)


if __name__ == "__main__":
    unittest.main()
