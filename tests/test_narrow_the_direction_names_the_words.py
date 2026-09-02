# -*- coding: utf-8 -*-
"""「建议先收窄 /job-scrape 的方向」—— 收窄哪个词？一个字都没说。

`gap_split` 的两条结论都把人送去改搜索词：

    「两样都差」占多数   → 建议先收窄 /job-scrape 的方向
    「选岗问题」≥「可以靠学」 → 先调 profile/search-queries.md 更划算

而判据一直在手边：每条岗身上带着 `found_by`（哪个词搜到的），`split`
又把整条 entry 留在了元组里。按它一统计，分离得非常干净 ——
实测 2026-08-23（活动用户，607 份语料、374 个「两样都差」）：

    AI工具         共 17   两样都差 16 (94%)   主场 0
    AI原生         共 15   两样都差 14 (93%)   主场 0
    AI赋能         共 25   两样都差 22 (88%)   主场 0
    …
    Agent产品经理  共 26   两样都差  3 (12%)   主场 5

**和 `query_yield` 的「该停一停的词」不是同一件事。** 那边问「这个词出过
可投的岗吗」（高匹配 0），这边问「这个词抓来的岗在不在他赛道上」。一个词可以
大量产出「选岗问题」（专业对口、行业不对）—— 不可投，但也不算跑偏。
实测两张单子 12 个 vs 8 个词，**只有 `AI工具` 重合**。

顺带一条既有规矩：第二句原来只给了文件名 `profile/search-queries.md`。
`AGENTS.md`「面板每处引导都要写出命令」—— 用户不知道拿那个文件怎么办。
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tests"))
import gap_split as G  # noqa: E402
import query_yield as Q  # noqa: E402
from _srcscan import strip_comments  # noqa: E402

UPSKILL = (ROOT / "workflows" / "job-upskill.md").read_text(encoding="utf-8")


def _e(skill, dom, found_by=None):
    """形状同 `test_gap_split.E` —— `read_pair` 认的是 `四维` 那个键。"""
    e = {"status": "ranked", "title": "岗", "company": "某公司",
         "rank_breakdown": {"四维": f"专业能力{skill}×0.6+业务域{dom}×0.4"}}
    if found_by:
        e["found_by"] = found_by
    return e


def _box(**spec):
    """`{格: [(词, 个数)…]}` → `split` 出来的四格。"""
    seen, i = {}, 0
    pairs = {"home": (90, 80), "pick": (90, 30), "learn": (50, 80),
             "off": (50, 30)}
    for kind, items in spec.items():
        for word, n in items:
            for _ in range(n):
                i += 1
                seen[f"k{i}"] = _e(*pairs[kind], found_by=word)
    return G.split(seen)


class TheWordsAreNamed(unittest.TestCase):
    def test_a_word_that_only_produces_off_direction_jobs_is_listed(self):
        box = _box(off=[("甲词", 20)], home=[("乙词", 20)])
        got = dict((w, off) for w, _n, off in G.off_direction_words(box))
        self.assertEqual(got.get("甲词"), 20)
        # **2026-08-27：从「列出来、写 0」改成「根本不列」。**
        # 调用方取前三名 —— 真正命中的不足三个时，屏幕上会出现
        # 「跑偏最多的几个词：乙词（0/20 跑偏）」。眼下语料里前三名都非零，
        # 所以它从没露过面；那是语料大，不是判据对。
        self.assertIsNone(got.get("乙词"), "一次都没跑偏的词还被列出来")

    def test_a_thin_word_is_not_listed(self):
        """三五个岗的比例说明不了什么。门槛沿用 `query_yield.DEAD_MIN_N`。"""
        box = _box(off=[("甲词", Q.DEAD_MIN_N - 1)])
        self.assertEqual(G.off_direction_words(box), [])
        box2 = _box(off=[("甲词", Q.DEAD_MIN_N)])
        self.assertEqual([w for w, *_ in G.off_direction_words(box2)], ["甲词"])

    def test_the_floor_is_not_a_second_constant(self):
        """同一个判断（抓够多少个才谈这个词）不许两处各定各的。"""
        code = strip_comments((ROOT / "tools" / "gap_split.py")
                              .read_text(encoding="utf-8"))
        self.assertIn("DEAD_MIN_N", code, "自己又定了一个最小样本量")

    def test_pages_fold_back_into_the_word(self):
        """`AI赋能 p6` 是翻页。不并的话一个词拆成七八行，全都够不着门槛
        —— `query_yield` 那边踩过一次。"""
        n = Q.DEAD_MIN_N
        box = _box(off=[("甲词", n // 2 + 1), ("甲词 p2", n // 2 + 1)])
        self.assertEqual([w for w, *_ in G.off_direction_words(box)], ["甲词"])

    def test_jobs_without_a_source_are_skipped(self):
        """`found_by` 是后加的字段，早期抓的补不上 —— 不许把它们算成某个词。"""
        box = _box(off=[(None, 40)])
        self.assertEqual(G.off_direction_words(box), [])

    def test_it_sorts_by_how_many_went_off(self):
        """按跑偏个数排，不按比例：比例高但样本刚过线的排不到前面。"""
        box = _box(off=[("多的", 30), ("少的", 16)],
                   home=[("多的", 20)])
        self.assertEqual([w for w, *_ in G.off_direction_words(box)][:2],
                         ["多的", "少的"])


class BothVerdictsCarryThem(unittest.TestCase):
    def test_the_off_heavy_verdict_names_words(self):
        v = G.verdict(_box(off=[("甲词", 40)], home=[("乙词", 5)]))
        self.assertIn("跑偏最多的几个词", v)
        self.assertIn("甲词", v)

    def test_the_pick_heavy_verdict_names_words(self):
        v = G.verdict(_box(pick=[("甲词", 20)], learn=[("乙词", 6)],
                           home=[("丙词", 5)], off=[("甲词", 16)]))
        self.assertIn("先别急着开学习清单", v)
        # **2026-08-27：这一条原来钉着一个 bug。**
        # 这一支的诊断是「你不缺技能，缺的是投对地方」，而它当时点名的是
        # 「两样都差」那批词 —— 两份名单在真实语料上完全不重合。
        # 判据见 `test_the_hint_follows_its_diagnosis.py`。
        self.assertIn("行业对不上最多的几个词", v)

    def test_both_give_a_command_not_a_file_path(self):
        """`AGENTS.md`「面板每处引导都要写出命令」—— 原来第二句只给了文件名。"""
        for v in (G.verdict(_box(off=[("甲词", 40)], home=[("乙词", 5)])),
                  G.verdict(_box(pick=[("甲词", 20)], learn=[("乙词", 6)]))):
            with self.subTest(v=v[:20]):
                self.assertIn("/job-setup --section search", v)

    def test_it_does_not_decide_for_him(self):
        """同 `query_yield` 那句「数给你，停不停你定」。"""
        v = G.verdict(_box(off=[("甲词", 40)], home=[("乙词", 5)]))
        self.assertIn("停不停你定", v)
        for word in ("删掉", "必须停", "去掉这几个"):
            with self.subTest(word=word):
                self.assertNotIn(word, v)

    def test_no_words_no_tail(self):
        """`found_by` 全空时（早期语料）不许吊一个空尾巴。"""
        seen = {f"k{i}": _e(50, 30) for i in range(40)}
        v = G.verdict(G.split(seen))
        self.assertNotIn("跑偏最多的几个词", v)
        self.assertNotIn("：。", v)

    def test_the_other_two_verdicts_are_untouched(self):
        """「照常出学习计划」和「没有明显缺口格」不该长出这条尾巴 ——
        那两条根本不是让人去改搜索词的。"""
        learn = G.verdict(_box(learn=[("甲词", 20)], pick=[("乙词", 3)],
                               home=[("丙词", 4)], off=[("丁词", 5)]))
        self.assertIn("照常出学习计划", learn)
        self.assertNotIn("跑偏最多的几个词", learn)
        home = G.verdict(_box(home=[("甲词", 20)]))
        self.assertIn("没有明显的缺口格", home)
        self.assertNotIn("跑偏最多的几个词", home)


class ItIsADifferentQuestionFromTheStopList(unittest.TestCase):
    """两张单子答的不是一回事，合并或互相引用都会把判据搅浑。"""

    def test_a_word_full_of_pick_jobs_is_not_off_direction(self):
        """「选岗问题」= 专业对口、行业不对。不可投，但没跑偏。
        `query_yield` 会把它列进「该停一停」（高匹配 0），这里不该列。"""
        box = _box(pick=[("甲词", 30)])
        got = dict((w, off) for w, _n, off in G.off_direction_words(box))
        # 「不列出来」比「列出来写 0」更强地表达同一件事。
        self.assertIsNone(got.get("甲词"), "选岗问题的词被当成跑偏报了")
        # 换成问 PICK，它就该出现 —— 这才说明两个问题是分开的。
        pick = dict((w, off) for w, _n, off in
                    G.off_direction_words(box, key=G.PICK))
        self.assertEqual(pick.get("甲词"), 30)

    def test_the_difference_is_written_down(self):
        """**要那句分工本身，不是附近出现过「query_yield」这几个字。**
        第一版就是后者：变异只删掉那句断言，两个锚点在下一行照样在，绿。"""
        src = (ROOT / "tools" / "gap_split.py").read_text(encoding="utf-8")
        i = src.index("def off_direction_words(")
        # **先把折行压平。** 中文散文在源码里是折着写的，一个句子中间会带
        # 换行加缩进，按原样匹配必然落空 —— 而那不是文档的问题，是断言的问题。
        seg = " ".join(src[i:i + 2200].split())
        self.assertIn("不是同一件事", seg, "没说清和停用清单的分工")
        self.assertIn("那边问「这个词 出过可投的岗吗」", seg, "没说那边问什么")
        self.assertIn("这边问「这个词抓来的岗在不在他赛道上」", seg, "没说这边问什么")
        self.assertIn("只有 `AI工具` 重合", seg, "没留下实测的量")

    def test_the_stop_list_still_exists(self):
        """这条分工的另一半。它没了，上面那段解释就成了无主之谈。"""
        src = (ROOT / "tools" / "query_yield.py").read_text(encoding="utf-8")
        self.assertIn("该停一停的词", src)


class TheWorkflowTellsTheExecutorToReadThemOut(unittest.TestCase):
    """算了不念等于没算 —— 这个仓库反复出现的那一族。"""

    def test_it_says_to_read_the_words_out(self):
        """**要那句祈使，不是「跑偏最多的几个词」这几个字出现过。**
        第一版验的是后者，而它在解释段里也有一份 —— 删掉指令照样绿。"""
        self.assertIn("把 `gap_split` 报的那几个词一并念给他", UPSKILL,
                      "没让执行者把那几个词说出来")
        self.assertIn("off_direction_words", UPSKILL, "没说清判据在哪")
        self.assertRegex(UPSKILL, r"「先调搜索词」不说改哪个词，等于把活推回给他自己猜")

    def test_it_gives_the_command(self):
        i = UPSKILL.index("「选岗问题」那格 ≥「可以靠学」那格")
        self.assertIn("/job-setup --section search", UPSKILL[i:i + 1200])

    def test_rescraping_before_narrowing_is_called_out(self):
        """词没换，重抓一遍只会抓回同一批 —— 原来那条先让人去 /job-scrape。"""
        self.assertRegex(UPSKILL, r"词没换，重抓一遍只会抓回同一批")

    def test_it_still_says_this_is_a_hint_not_a_block(self):
        """原有的规矩：用户说「还是要学习计划」就照常出。"""
        self.assertIn("这是提示，不是拦截", UPSKILL)


if __name__ == "__main__":
    unittest.main()
