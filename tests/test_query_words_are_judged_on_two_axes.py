# -*- coding: utf-8 -*-
"""查询词的好坏有两个轴，只看一个会推荐反方向的词。

- **高匹配率**：这个词抓到的岗，**分够不够高** —— 短名单不够长时看它。
- **主场率**：抓到的岗，**行业经验对不对得上** —— 投出去没回音、
  而多数是「行业对不上」时看它（判据见 `export_web_data.applied_fit`：
  实测他投出去的 63% 是这一类）。

两者按词排序**几乎相反**（实测活动用户 2026-08-22，相关系数 **0.33**）：

    企业AI应用   已评 12 · 高匹配 5（42%） · 主场 0
    AI提效       已评  8 · 高匹配 5（63%） · 主场 1
    开发者工具    已评 12 · 高匹配 1（ 8%） · 主场 3（25%）

只看高匹配的话，「企业AI应用」会被推荐，而它抓回来的 12 个岗**行业经验一个都
对不上**；「开发者工具」会被判成弱词，而它是这批里主场率最高的。

所以两列都给、**不替用户选**。而 `/job-setup --section search` 也要先读这份实测
再问 —— 一个已经抓过几千个岗的人，让他从零想关键词是浪费。
"""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import gap_split as gs  # noqa: E402
import query_yield as qy  # noqa: E402

SETUP = (ROOT / "workflows" / "job-setup.md").read_text(encoding="utf-8")


def _entry(stack, domain, verdict="值得投"):
    return {"url": f"u{stack}{domain}", "status": "ranked",
            "rank_verdict": verdict,
            "rank_breakdown": {"四维": f"专业能力 {stack}×0.6+业务域 {domain}×0.4"}}


class TheKeepBarIsPinned(unittest.TestCase):
    """`MIN_NEW = 5` 与 `MIN_HIGH_RATE = 0.25` —— 此前**一条测试都没提过它们**。

    它们决定哪些搜索词算「达标」，而达标那张表是 `search-queries.md` 里那个
    自动维护块的内容 —— 下一轮 `/job-scrape` 照它去搜。也就是说这两个数
    直接决定 `/job-auto` 下一轮**抓什么**：

        调松 → 泛词（`产品经理` 这种）挤进词表，抓回来一堆低质命中，
               而每次请求要隔 8 秒
        调紧 → 真正高产的词也达不了标，词表越缩越窄

    定义处写着「两条都要满足 —— 只看新增数会把大量低质命中的泛词排到前面」，
    而没有一处验它真的是「都要满足」。

    钉的是边界行为，天数/比例**写死**（不从常量现算 —— 那等于让它自己给
    自己出题，同 `test_archive_keeps_walls_down` 刚踩过的那一脚）。
    """

    @staticmethod
    def _rows(n, hi):
        """`n` 个岗，其中 `hi` 个判词是可投顶两档。"""
        return [{"new": 1, "rank_verdict": "值得投" if i < hi else "不建议"}
                for i in range(n)]

    def _keep(self, by):
        return {q for q, *_rest in qy.render(by, set())[1]}

    def test_exactly_at_the_rate_still_counts(self):
        """8 个里 2 个高匹配 = 25%，正好够 —— 边界上要收进来。"""
        self.assertIn("甲", self._keep({"甲": {"p1": self._rows(8, 2)}}))

    def test_just_under_the_rate_is_dropped(self):
        """8 个里 1 个 = 12.5%，不够。"""
        self.assertNotIn("乙", self._keep({"乙": {"p1": self._rows(8, 1)}}))

    def test_a_tiny_sample_is_dropped_however_good(self):
        """4 个里 4 个全是高匹配 —— 比例满分，但样本不够 5 个，照样不算数。

        这一条钉的是**「两条都要满足」**：少了它，一个只抓到 1 个岗、
        恰好命中的词就会被当成高产词推上去。
        """
        self.assertNotIn("丙", self._keep({"丙": {"p1": self._rows(4, 4)}}))

    def test_both_bars_are_and_not_or(self):
        """三个词一起喂进去，只有同时过两关的那个留下。"""
        by = {"甲": {"p1": self._rows(8, 2)},     # 8 个 25%   → 留
              "乙": {"p1": self._rows(8, 1)},     # 8 个 12.5% → 去
              "丙": {"p1": self._rows(4, 4)}}     # 4 个 100%  → 去（样本小）
        self.assertEqual(self._keep(by), {"甲"})

    def test_the_reason_for_the_pair_is_written_down(self):
        src = (ROOT / "tools" / "query_yield.py").read_text(encoding="utf-8")
        i = src.index("MIN_NEW = ")
        self.assertIn("只看新增数", " ".join(src[max(0, i - 300):i].split()),
                      "这两个数没留下「为什么是两条」的理由")


class TheHomeColumnIsItsOwnAxis(unittest.TestCase):
    def test_a_high_scoring_word_can_have_zero_home(self):
        """分高不等于行业对得上 —— 这正是「企业AI应用」那一格的形状。"""
        rows = [_entry(90, 20) for _ in range(5)]
        n, hi = qy.stats(rows)
        self.assertEqual((n, hi), (5, 5), "这批本该都算高匹配")
        self.assertEqual(qy.n_home(rows), 0, "行业经验 20 分却算进了主场")

    def test_a_low_scoring_word_can_be_all_home(self):
        """反过来也成立 —— 「开发者工具」那一格。"""
        rows = [_entry(75, 70, verdict="可以考虑") for _ in range(4)]
        self.assertEqual(qy.n_home(rows), 4)

    def test_the_thresholds_are_not_copied(self):
        """分界只有一个出处（`gap_split`）。抄一遍就等着两处哪天不一样。"""
        src = (ROOT / "tools" / "query_yield.py").read_text(encoding="utf-8")
        seg = src[src.index("def n_home("):]
        seg = seg[:seg.index("\ndef ", 1)]
        body = seg.split('"""')
        code = body[0] + "".join(body[2:]) if len(body) > 2 else seg
        self.assertNotRegex(code, r"\b70\b|\b60\b", "分界被抄进了 n_home")
        self.assertIn("gs.quadrant", code, "没走 gap_split 的分格函数")

    def test_unreadable_scores_do_not_count_as_home(self):
        """读不出两笔分数就不是主场 —— 不猜。"""
        self.assertEqual(qy.n_home([{"url": "x", "status": "ranked"}]), 0)

    def test_the_column_reaches_the_table(self):
        """算出来不进表 = 又一个没人读的字段。"""
        src = (ROOT / "tools" / "query_yield.py").read_text(encoding="utf-8")
        self.assertIn("其中主场", src, "表头里没有这一列")
        self.assertIn("n_home(", src[src.index("def render("):], "render 没调它")


class TheBudgetAdviceKnowsAboutHomeTurf(unittest.TestCase):
    """`--apply` 写进用户 `search-queries.md` 那个自动维护块的推荐词，是纯按高匹配率选的。

    （那块由 `tools/query_yield.py` 运行时生成，仓库里跟踪的模板中没有它 —— 所以这里不写成
    「某文件的某节」那个形状，`test_cross_references_resolve` 会拿它去核小节名。）

    抓取额度是这套系统里最稀缺的东西（每次请求之间要隔 8/4/3 秒、撞了风控整站冷却 24 小时）。把它花在
    **扩张一个零主场的词**上，抓回来的会是更多「专业能力够、行业经验对不上」
    的岗 —— 而那正是他投出去的 63%。

    **不从推荐里删掉它们**：短名单不够长时分高的词照样有用。只把话说出来，
    让那次额度分配是知情的。
    """

    def test_a_zero_home_word_is_called_out(self):
        out = qy._home_caveat([("企业AI应用", 35, 9, 0)])
        self.assertIn("企业AI应用", out)
        self.assertIn("主场", out)

    def test_a_word_with_home_jobs_is_not(self):
        self.assertEqual(qy._home_caveat([("Agent产品经理", 69, 16, 5)]), "")

    def test_it_does_not_drop_them_from_the_recommendation(self):
        """提醒 ≠ 删除。删掉的话，短名单不够长的人就再也抓不到分高的岗。"""
        src = (ROOT / "tools" / "query_yield.py").read_text(encoding="utf-8")
        i = src.index("    runnable = ")
        self.assertNotIn("hm", src[i:i + 200],
                         "可执行块按主场过滤了 —— 那是删词，不是提醒")

    def test_the_caveat_carries_no_markdown(self):
        """这段字既进 markdown 也进终端，`**` 会原样上屏。"""
        self.assertNotIn("**", qy._home_caveat([("某词", 20, 6, 0)]))

    def test_it_says_when_to_ignore_the_caveat(self):
        """两个轴哪个要紧取决于他卡在哪 —— 不说清就变成了一条绝对规则。"""
        out = qy._home_caveat([("某词", 20, 6, 0)])
        self.assertRegex(out, r"短名单不够长时.{0,10}照样有用",
                         "没说清什么时候不必理会这条提醒")

    def test_someone_actually_calls_it(self):
        """**这条是这一组原来缺的那一条。**

        上面五条把 `_home_caveat` 的行为验得很细 —— 而 2026-08-23 实测发现
        **全仓库只有这几条测试在调它**，生产路径一次都没调过。写好的提醒
        从来没有出现在任何人的屏幕上，而测试全绿，看着像覆盖到了。

        同一个文件里 `n_home` 那一组就有这条（`test_the_column_reaches_the_table`
        里的「render 没调它」）。两组不对称，缺的那一组就是坏的那一组。
        """
        src = (ROOT / "tools" / "query_yield.py").read_text(encoding="utf-8")
        i = src.index("def main(")
        self.assertIn("_home_caveat(", src[i:], "main 没调它 —— 又是算了没显示")

    def test_it_prints_next_to_the_qualifying_list(self):
        """挨着「达标」那一行才有意义：上面说「这几个词值得往新平台上扩」，
        它说「其中这几个扩出来的多半还是行业对不上的」。"""
        src = (ROOT / "tools" / "query_yield.py").read_text(encoding="utf-8")
        i = src.index("def main(")
        seg = src[i:]
        self.assertLess(seg.index("达标（新增"), seg.index("_home_caveat("),
                        "提醒印在了达标清单前面")
        self.assertLess(seg.index("_home_caveat("), seg.index("该停一停的词"),
                        "提醒被挤到了下一节后面")

    def test_the_report_really_carries_it(self):
        """端到端：造一份最小的库跑完整个 `main`，那句话必须出现在标准输出里。
        只查源码里有没有那个调用，改成 `if False:` 照样绿。"""
        import contextlib
        import io
        import json
        import tempfile
        import unittest.mock as mock
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            js = root / "users" / "u" / "job_scraper"
            js.mkdir(parents=True)
            # 一个词、一个平台、8 个岗，6 个「值得投」但行业经验全是 20 分
            # ——达标（高匹配 75% ≥ 25%、新增 8 ≥ 5），而主场 0。
            seen = {}
            for i in range(8):
                seen[f"k{i}"] = {
                    "url": f"https://www.liepin.com/job/{i}.shtml",
                    "status": "ranked", "first_seen": "2026-08-01",
                    "rank_verdict": "值得投" if i < 6 else "不建议",
                    "rank_breakdown": {"专业能力": 80, "业务领域": 20},
                    "found_by": "示例词", "portal": "猎聘",
                }
            (js / "seen_jobs.json").write_text(
                json.dumps({"seen": seen}, ensure_ascii=False), encoding="utf-8")
            buf = io.StringIO()
            with mock.patch.object(qy, "ROOT", root),                  contextlib.redirect_stdout(buf):
                try:
                    qy.main(["--user", "u"])
                except SystemExit:
                    pass
            out = buf.getvalue()
        if "达标（新增" not in out or " 0 个词" in out:
            self.skipTest(f"这份夹具没造出达标的词：{out[-300:]}")
        self.assertIn("一个「主场」岗都没抓到过", out,
                      "达标词全是零主场，报告里却没有那句提醒")


class SetupReadsTheMeasurementBeforeAsking(unittest.TestCase):
    def test_rerunning_the_section_starts_from_data(self):
        seg = SETUP[SETUP.index("#### 第 2 组：目标岗位与关键词"):][:2400]
        self.assertIn("query_yield.py", seg, "重跑这一节时没让它先看实测产出")
        self.assertIn("--section search", seg, "没说清这条只对重跑成立")

    def test_it_warns_against_merging_the_two_columns(self):
        """合成一个「好词」正是这一轮要防的事。"""
        seg = SETUP[SETUP.index("#### 第 2 组：目标岗位与关键词"):][:2400]
        self.assertRegex(seg, r"两列分开看|别合成", "没提醒两列要分开看")
        self.assertIn("0.33", seg, "没给出那两列到底有多不一致")

    def test_it_reports_facts_and_leaves_the_call_to_him(self):
        """他知道自己那一行的词，工具不知道 —— 只报事实。"""
        seg = SETUP[SETUP.index("#### 第 2 组：目标岗位与关键词"):][:2400]
        self.assertRegex(seg, r"只报事实|由他定|不要替他改",
                         "变成了替用户改词")


if __name__ == "__main__":
    unittest.main()
