# -*- coding: utf-8 -*-
"""结论说的是一件事，它点名的词是另一件事。

`gap_split.verdict` 有两条分支都把人送去改搜索词，而「改哪个」由 `_off_hint`
接在后面。那一句原来**固定数「两样都差」**：

    「两样都差」占多数         → 点名倒「两样都差」的词    ← 对得上
    「选岗问题」≥「可以靠学」   → 还是点名那批词            ← 对不上

第二条的诊断逐字是「**你不缺技能，缺的是把简历投到行业经验对得上的地方**」。
该改的是那些「专业对口、行业不对」（`PICK`）产得最多的词 —— 它们正瞄着错的
行业。而「两样都差」的词只是**烂词**：改掉它们是另一件好事，和这条诊断无关。

## 两份名单在真实语料上完全不重合

实测活动用户 2026-08-27：

    两样都差： AI赋能 14/20 · AI原生 12/19 · AI工具 12/18
    选岗问题： Agent产品经理 21/30 · 企业AI应用 18/29 · AI应用产品经理 11/23

后一组是他产出最多的几个**主力词**。「改这几个」和「改 AI工具」是两条分量
完全不同的指令 —— 前者动的是这套搜索的主干。

## 措辞也跟着格子走

「跑偏」说的是两样都差。专业对口、行业不对不叫跑偏，那是**投错了地方** ——
`LABELS[PICK]` 自己写着「不缺技能，缺的是投对地方」。
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import gap_split as gs  # noqa: E402

SRC = (ROOT / "tools" / "gap_split.py").read_text(encoding="utf-8")


def _job(found_by):
    """`split` 留在元组里的形状：(专业能力, 业务域, 整条 entry)。"""
    return (85, 20, {"found_by": found_by})


def _box(**counts):
    box = {gs.HOME: [], gs.PICK: [], gs.LEARN: [], gs.OFF: []}
    for key, (word, n) in counts.items():
        box[getattr(gs, key)] = [_job(word) for _ in range(n)]
    return box


class EachBranchNamesItsOwnQuadrant(unittest.TestCase):
    def test_the_off_heavy_branch_names_off_words(self):
        v = gs.verdict(_box(OFF=("烂词", 20)))
        self.assertIn("两样都差", v, "走的不是这一支")
        self.assertIn("烂词", v)
        self.assertIn("跑偏", v)

    def test_the_pick_heavy_branch_names_pick_words(self):
        """**这是修的那一处。** 诊断是「投错了地方」，就该点名投错地方的词。"""
        box = _box(PICK=("主力词", 20), LEARN=("别的", 2), OFF=("烂词", 3))
        v = gs.verdict(box)
        self.assertIn("选岗问题", v, "走的不是这一支")
        self.assertIn("主力词", v, "点名的还是「两样都差」那批词")
        self.assertNotIn("烂词", v, "把烂词混进来了 —— 那是另一条诊断的药")

    def test_the_wording_follows_the_quadrant(self):
        """「跑偏」只属于两样都差。专业对口、行业不对不叫跑偏。"""
        pick = gs.verdict(_box(PICK=("主力词", 20), LEARN=("别的", 2)))
        self.assertIn("行业对不上", pick)
        self.assertNotIn("跑偏", pick)

    def test_the_label_it_leans_on_is_still_there(self):
        """这条判据全压在 PICK 那一格的定义上。"""
        self.assertIn("不缺技能，缺的是投对地方", gs.LABELS[gs.PICK])


class TheWordListTakesTheQuadrant(unittest.TestCase):
    def test_it_defaults_to_off(self):
        """默认不变 —— 别的调用方（如果有）按原样继续。"""
        box = _box(OFF=("烂词", 20), PICK=("主力词", 20))
        self.assertEqual([w for w, *_ in gs.off_direction_words(box)], ["烂词"])

    def test_it_counts_the_asked_for_quadrant(self):
        box = _box(OFF=("烂词", 20), PICK=("主力词", 20))
        got = gs.off_direction_words(box, key=gs.PICK)
        self.assertEqual([w for w, *_ in got], ["主力词"])

    def test_the_denominator_is_the_whole_word(self):
        """分母是这个词抓来的**全部**岗，不只是命中那一格的。"""
        box = {gs.HOME: [_job("词") for _ in range(5)], gs.LEARN: [],
               gs.PICK: [_job("词") for _ in range(15)], gs.OFF: []}
        (word, n, off), = gs.off_direction_words(box, key=gs.PICK)
        self.assertEqual((word, n, off), ("词", 20, 15))

    def test_a_word_below_the_floor_is_dropped(self):
        """门槛沿用 `query_yield.DEAD_MIN_N` —— 「抓够这么多才谈这个词」是同一个判断。"""
        from query_yield import DEAD_MIN_N
        box = _box(PICK=("小样本", DEAD_MIN_N - 1))
        self.assertEqual(gs.off_direction_words(box, key=gs.PICK), [])

    def test_it_does_not_invent_its_own_floor(self):
        seg = SRC[SRC.index("def off_direction_words("):]
        seg = seg[:seg.index("\ndef ")]
        self.assertIn("DEAD_MIN_N", seg, "自己写了一个门槛 —— 两处迟早分叉")


class AWordWithNoHitsIsNotNamed(unittest.TestCase):
    """「跑偏最多的几个词」里不许出现一次都没跑偏的词。

    这条是写上面那些用例时撞出来的**既有**问题：原来只按「抓够 floor 个」
    过滤，命中 0 的词带着 `off=0` 留在列表里。调用方取前三名 —— 真正命中的
    不足三个时，屏幕上就会出现「跑偏最多的几个词：某某（0/20 跑偏）」。

    眼下的语料里前三名都非零，所以它从没露过面。**那是语料大，不是判据对。**
    """

    def test_a_zero_hit_word_is_dropped(self):
        box = _box(OFF=("烂词", 20), PICK=("干净词", 20))
        got = [w for w, *_ in gs.off_direction_words(box)]
        self.assertEqual(got, ["烂词"], "把一次都没跑偏的词也列出来了")

    def test_nothing_hit_means_no_hint(self):
        """一个都没有时那半句要整个消失，不是印一句「最多的是：（空）」。"""
        box = _box(HOME=("干净词", 20))
        self.assertEqual(gs.off_direction_words(box), [])
        self.assertEqual(gs._off_hint(box), "")

    def test_the_conclusion_still_reads_without_it(self):
        """没有词可点名时，结论本身仍然完整 —— 那条命令还在。"""
        v = gs.verdict(_box(PICK=("词", 20), LEARN=("别的", 2)))
        self.assertIn("/job-setup --section search", v)


class TheIncidentIsOnRecord(unittest.TestCase):
    def test_the_mismatch_is_written_down(self):
        i = SRC.index("def _off_hint(")
        seg = SRC[i:SRC.index("\ndef ", i + 10)]
        self.assertIn("对不上", seg, "没写下这一句原来点错了名单")
        self.assertIn("2026-08-27", seg)

    def test_both_measured_lists_are_kept(self):
        """两份名单不重合才是这条改动的全部理由 —— 数留着，下次能复核。"""
        i = SRC.index("def _off_hint(")
        seg = SRC[i:SRC.index("\ndef ", i + 10)]
        self.assertIn("AI工具", seg)
        self.assertIn("Agent产品经理", seg)


if __name__ == "__main__":
    unittest.main()
