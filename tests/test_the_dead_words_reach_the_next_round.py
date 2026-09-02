# -*- coding: utf-8 -*-
"""「该停一停的词」只 print 到终端 —— 而下一轮读的是文件。

`query_yield` 算了两件事：

    该停一停的词        抓够 15 个、可投一个都没出
    下一轮最值钱的格子   达标的词 × 还没跑过的平台

两件都 `print()` 到终端，**都不进写回的那个块**。而下一轮真正被读的是
`profile/search-queries.md` —— `job-scrape.md` Step 1b 写着「把
`profile/search-queries.md` 里的查询词，翻成这个渠道认的参数形式」。
终端那份输出只活在跑它的那一次会话里。

## 代价是可量的

实测活动用户 2026-08-24：**12 个词抓够 15 个而可投一个都没出，合计白抓 267 个岗**
—— 按每次请求隔 8 秒算，约等于一个平台连抓 40 分钟。

**更要命的是那句反向指路。** 块里写着「`—` 表示这个词在这个平台还没跑过 ——
那通常是下一轮最值钱的格子」。它是对整张表说的，而那 12 个死词各自还空着两三格：
照着读，**最没用的词反而成了最值钱的格子**。真正过滤好的那份交叉清单
（只列达标的词）同样只在终端里。

## 这是本仓库反复出现的那一族

算了没显示、存了没人读。`_home_caveat` 栽过同一课（「全仓库只有测试在调」），
`resume_insight.asks` 的 `notHad` 分支栽过同一课（结构上渲染不出来）。
"""
import pathlib
import re
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import query_yield as qy  # noqa: E402

SRC = (ROOT / "tools" / "query_yield.py").read_text(encoding="utf-8")


def flat(s: str) -> str:
    s = " ".join(re.sub(r"^\s*#\s?", "", s, flags=re.M).split())
    return re.sub(r"(?<=[一-鿿，。；：、（）「」])"
                  r" +(?=[一-鿿，。；：、（）「」])", "", s)


def block(**kw) -> str:
    by = {"好词": {"猎聘": [{"fit": "high"}] * 10},
          "死词": {"猎聘": [{"fit": "low"}] * 20}}
    kw.setdefault("dead", [("死词", 20, 0)])
    kw.setdefault("gaps", [("好词", "BOSS")])
    kw.setdefault("rate", 0.04)
    return qy.build_block(by, "2026-08-24", 0, frozenset(), "上海", **kw)


class TheDeadWordsLandOnDisk(unittest.TestCase):
    def test_the_block_names_them(self):
        b = block()
        self.assertIn("该停一停的词", b)
        self.assertIn("「死词」抓了 20 个，可投 0", b)

    def test_it_says_what_they_cost(self):
        """「12 个词没产出」是个统计；「约等于 N 小时的抓取时间」才是代价。

        换算基准 2026-08-26 从日上限改成间隔 —— 那天固定额度删了，
        稀缺的不再是次数而是时间。代价这件事没变，量纲变了。"""
        b = block(dead=[("死词", 240, 0)])
        self.assertIn("合计白抓 240 个岗", b)
        self.assertRegex(b, r"约等于 \d+ 小时的抓取时间")

    def test_it_cancels_the_dash_advice_for_them(self):
        """块顶那句「`—` 是最值钱的格子」对死词不成立 —— 不写这句，
        读的人会照着去把最没用的词铺到别的平台上。"""
        b = block()
        self.assertIn("对这几个词不成立", b)
        self.assertIn("还没在那儿浪费过", b)

    def test_the_top_of_the_block_points_down_to_it(self):
        b = block()
        i = b.index("`—` 表示")
        self.assertIn("先看下面「该停一停」那一节", b[i:i + 200])

    def test_the_pointer_disappears_with_the_section(self):
        """一句「先看下面那一节」而下面没有那一节，比不写更坏 —— 读的人
        会以为自己漏看了，或者以为块被截断了。**这条是写这批守卫时当场
        抓到的**：第一版那半句是无条件写死的。"""
        b = block(dead=[])
        self.assertNotIn("先看下面", b)
        self.assertIn("别把它当成「跑了没产出」。", b)

    def test_it_is_not_a_verdict(self):
        """停不停是他的判断 —— 工具给数，不替他决定。"""
        b = block()
        self.assertIn("这不是判决", b)
        self.assertIn("停不停你定", b)
        self.assertIn("全库平均命中率只有 4%", b)

    def test_nothing_is_written_when_there_are_none(self):
        b = block(dead=[])
        self.assertNotIn("该停一停", b)

    def test_only_the_first_ten_are_listed(self):
        b = block(dead=[(f"词{i}", 20, 0) for i in range(30)])
        self.assertEqual(b.count("可投 0"), 10, "列了几十行，那一节没人会读")
        self.assertIn("共 30 个", b)


class TheNextCellsLandOnDisk(unittest.TestCase):
    def test_the_block_lists_them(self):
        b = block()
        self.assertIn("下一轮最值钱的格子", b)
        self.assertIn("- 好词 × BOSS", b)

    def test_it_says_the_list_is_filtered(self):
        """整张表里的 `—` 和这份清单不是一回事 —— 后者只含达标的词。"""
        self.assertIn("只列达标的词", block())

    def test_a_long_list_is_cut_and_says_so(self):
        b = block(gaps=[(f"词{i}", "BOSS") for i in range(20)])
        self.assertIn("（还有 8 个没列）", b)

    def test_nothing_is_written_when_there_are_none(self):
        self.assertNotIn("最值钱的格子（", block(gaps=[]))


class AHomeTurfHitIsSaidOutLoud(unittest.TestCase):
    """「可投 0」不是这个词的全部事实。

    这个工具的立场写在它自己的输出里：「这不是判决……数给你，停不停你定」。
    而它**已经算出来**的另一列 —— 主场（专业能力与行业经验都对上）——
    此前只进表格，不进停用清单。`n_home` 的文档写着两个比率的相关系数
    只有 0.33，「投出去没回音、而回音里多数是行业对不上时看主场」。

    实测活动用户 2026-08-27：13 个待停的词里 **1 个**出过主场岗
    （`AI工具`，47 抓里 1 个）。只报「可投 0」，用户会把它和另外 12 个
    一起停掉 —— 而那一个是两维都对上的。

    **判据没变**：停用仍然只看「可投一个都没出」。变的是报告多给一个事实。
    """

    def test_the_terminal_line_says_it(self):
        """**走真的那份格式化。** 第一版在测试里把 print 那行抄了一遍，
        于是变异「0 个也印」照样绿 —— 它在测它自己。"""
        self.assertEqual(qy.home_note(1), "  其中 1 个是主场")
        self.assertEqual(qy.home_note(0), "", "0 个也印出来就是纯噪音")

    def test_both_consumers_share_one_criterion(self):
        """措辞可以不同，「0 个不印」这条判据只能有一份。"""
        self.assertEqual(qy.home_note(0, long=True), "")
        self.assertIn("专业能力与行业经验都对上", qy.home_note(2, long=True))
        src = (ROOT / "tools" / "query_yield.py").read_text(encoding="utf-8")
        i = src.index("def home_note(")
        end = src.find(chr(10) + "def ", i + 10)
        outside = src[:i] + src[end if end > 0 else len(src):]
        self.assertNotIn("个是主场", outside,
                         "这句话在 home_note 之外又写了一遍 —— 两处迟早分叉")

    def test_the_written_back_block_says_it_too(self):
        """写回盘那份才是下一轮真正被读的（`build_block` 那段注释）。"""
        b = block(dead=[("AI工具", 47, 1)])
        self.assertIn("其中 1 个是主场", b)
        self.assertIn("专业能力与行业经验都对上", b, "没解释主场是什么意思")

    def test_zero_home_stays_quiet_in_the_block(self):
        b = block(dead=[("数字员工", 39, 0)])
        self.assertIn("数字员工", b)
        self.assertNotIn("是主场", b)

    def test_the_stop_rule_itself_did_not_change(self):
        """有主场但可投 0 的词**仍然**要进清单 —— 多给一个事实，不是改判据。"""
        by = {"词": {"猎聘": [{"rank_verdict": "不建议",
                             "rank_breakdown": {"四维": "专业能力85×0.6+业务域80×0.4"}}
                            for _ in range(qy.DEAD_MIN_N)]}}
        got = qy.dead_ends(by)
        self.assertEqual(len(got), 1, "有主场就不报了？判据被改了")
        self.assertGreater(got[0][2], 0, "主场没数出来")


class TheComputationHasOneImplementation(unittest.TestCase):
    """算法从 main 里抽出来了 —— 别在两处各算一遍。"""

    def test_dead_ends_is_a_function(self):
        by = {"死词": {"猎聘": [{"fit": "low"}] * 20},
              "好词": {"猎聘": [{"fit": "high"}] * 20}}
        self.assertEqual(qy.dead_ends(by), [("死词", 20, 0)])

    def test_it_merges_paged_variants(self):
        """「研发效能 p6」这类翻页要并回主词，否则每行都不够门槛、永远报不出来。"""
        by = {"词": {"猎聘": [{"fit": "low"}] * 8},
              "词 p2": {"猎聘": [{"fit": "low"}] * 8}}
        self.assertEqual(qy.dead_ends(by), [("词", 16, 0)])

    def test_one_hit_saves_a_word(self):
        by = {"词": {"猎聘": [{"fit": "low"}] * 19 + [{"fit": "high"}]}}
        self.assertEqual(qy.dead_ends(by), [], "有一个可投的还被判死")

    def test_below_the_floor_is_not_dead_yet(self):
        by = {"词": {"猎聘": [{"fit": "low"}] * (qy.DEAD_MIN_N - 1)}}
        self.assertEqual(qy.dead_ends(by), [])

    def test_hit_rate_is_a_function(self):
        by = {"a": {"猎聘": [{"fit": "high"}] + [{"fit": "low"}] * 9}}
        self.assertAlmostEqual(qy.hit_rate(by), 0.1, places=6)

    def test_hit_rate_survives_an_empty_library(self):
        self.assertEqual(qy.hit_rate({}), 0.0)

    def test_main_uses_the_functions(self):
        i = SRC.index("def main(")
        seg = SRC[i:]
        self.assertIn("dead = dead_ends(by)", seg)
        self.assertIn("rate = hit_rate(by)", seg)
        self.assertNotIn("if n >= DEAD_MIN_N and hi == 0", seg,
                         "main 里又自己算了一遍 —— 两处早晚分叉")

    def test_main_passes_them_through(self):
        i = SRC.index("write_back(target, build_block(")
        self.assertIn("dead=dead, gaps=gaps, rate=rate", SRC[i:i + 500],
                      "算出来了却没传给写回那一份")


class TheReasonIsRecorded(unittest.TestCase):
    def _seg(self) -> str:
        i = SRC.index("「别再跑什么」和「下一轮跑哪一格」也要落盘")
        return flat(SRC[i:i + 1200])

    def test_it_says_where_the_next_round_actually_reads_from(self):
        seg = self._seg()
        self.assertRegex(seg, r"\*\*这两段原来只 print 到终端。\*\*")
        self.assertIn("job-scrape.md", seg)
        self.assertRegex(seg, r"只活在跑它的那一次会话里")

    def test_it_carries_the_measurement(self):
        seg = self._seg()
        self.assertIn("2026-08-24", seg)
        self.assertRegex(seg, r"12 个词抓够 15 个而可投一个都没出")
        self.assertRegex(seg, r"合计白抓 267 个岗")
        self.assertRegex(seg, r"约等于 \d+ 分钟的抓取时间")

    def test_it_names_the_backwards_advice(self):
        """光说「没落盘」不够 —— 落盘的那半句还在指反方向。"""
        seg = self._seg()
        self.assertRegex(seg, r"最没用的词反而成了最值钱的格子")

    def test_it_names_the_family(self):
        self.assertRegex(self._seg(), r"算了没显示、存了没人读")


class TheBlockItselfIsStillIntact(unittest.TestCase):
    def test_the_priority_runnable_block_survives(self):
        b = block()
        self.assertIn("下一轮优先跑", b)
        self.assertIn('-q "好词" -l "上海"', b)

    def test_the_hand_maintained_part_is_still_declared_off_limits(self):
        self.assertIn("要长期固定某个词，写到上面的「优先级」分类里", block())

    def test_the_markers_survive(self):
        b = block()
        self.assertTrue(b.startswith(qy.BEGIN))
        self.assertTrue(b.rstrip().endswith(qy.END))

    def test_no_city_means_no_location_flag(self):
        """写死一个城市的代价实测过 —— 取不到就不给 `-l`。"""
        by = {"好词": {"猎聘": [{"fit": "high"}] * 10}}
        b = qy.build_block(by, "2026-08-24", 0, frozenset(), "")
        self.assertNotIn(" -l ", b)

    def test_it_still_runs_without_the_new_arguments(self):
        """老调用方（测试、别的脚本）不传 dead/gaps 也不能炸。"""
        by = {"好词": {"猎聘": [{"fit": "high"}] * 10}}
        b = qy.build_block(by, "2026-08-24", 0)
        self.assertIn("下一轮优先跑", b)
        self.assertNotIn("该停一停", b)


class TheScrapeWorkflowReadsThisFile(unittest.TestCase):
    """这条改动的前提：下一轮确实从这个文件取词。前提没了就要重想。"""

    def test_the_workflow_says_so(self):
        doc = (ROOT / "workflows" / "job-scrape.md").read_text(encoding="utf-8")
        self.assertIn("`profile/search-queries.md` 里的查询词", doc)


if __name__ == "__main__":
    unittest.main()
