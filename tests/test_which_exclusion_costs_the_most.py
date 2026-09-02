# -*- coding: utf-8 -*-
"""04 要求写清是哪一条排除，理由是要数出「每条挡掉多少」—— 而没人数过。

那一节的原话：

> **为什么单这一道门要求写清楚：它是七道里唯一他能改的。** 学历、年限、户口、
> 应届身份都不是他今天能动的；而排除项是他自己下的结论，随时可以放宽一条。
> 但要决定放宽哪一条，他得先知道**每条各挡掉了多少个岗**。

规则立了，执行也真的发生了 —— 实测活动用户 2026-08-24：426 个岗死在这道门上，
其中 **101 个写清了是哪一条**。而那句「每条各挡掉多少」**从来没被算出来过**：
面板的 `gateFailTally` 按门名分组，这道门在那儿只是一个整数。

## 分布极其集中，所以这个数很值钱

现算出来：100 条能归到他资料里的 8 条不同排除上，而**最贵的一条占了 47 个**、
前三条占 74 个。也就是说「放宽哪一条」这个问题有一个明确答案，
而他此前无从知道。

## 归到「资料里的哪一行」，不是归到那句自由文本

理由格是自由文本：同一条排除写成「英语口语」「英语流利」「英语听说」
「英语面试」的都有。照字面分组会把一条排除拆成四份，谁也看不出它最贵。
判据与 `_exclusion_anchors` 同源（二字片段、宁可漏报不可误报）。

## 那个数必须声明是下限

325 个岗只写了「明确排除」四个字，进不了这张表。不声明的话，读的人会把
「第一条挡了 47 个」当成全貌，而真实数最多能到四倍。

## 这份测试不写他的排除条款原文

那是个人数据。断言只钉**形状**（有几条、集中度、下限声明在不在），
不钉他写了什么 —— `test_no_maintainer_data_in_repo` 也盯着这一点。
## 面板那一侧（2026-08-31 并进来）

同一件事原来有两份守卫：这一份钉自检，另一份钉面板。**两份守卫会各自
长出对方没有的一条** —— CLAUDE.md 开头记的就是这个形状，而这条判据
刚从 `audit_pipeline` 搬进 `_cli` 正是为了让两个消费方共用一套算法。
所以守卫也合到一处：下面 `TheGroupingHasOneHome` 起的几个类钉的是
导出与面板那一半。
"""
import json
import pathlib
import re
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import _cli  # noqa: E402
import audit_pipeline as ap  # noqa: E402
import export_web_data as ex  # noqa: E402
sys.path.insert(0, str(ROOT / "tests"))
from _live import user_or_skip  # noqa: E402
from _srcscan import code_of  # noqa: E402

AUDIT = (ROOT / "tools" / "audit_pipeline.py").read_text(encoding="utf-8")
CLI = (ROOT / "tools" / "_cli.py").read_text(encoding="utf-8")
EX = (ROOT / "tools" / "export_web_data.py").read_text(encoding="utf-8")
APP = (ROOT / "web" / "src" / "App.tsx").read_text(encoding="utf-8")
LOAD = (ROOT / "web" / "src" / "data"
        / "load.ts").read_text(encoding="utf-8")
EVAL = (ROOT / "workflows" / "reference"
        / "04-job-evaluation.md").read_text(encoding="utf-8")
SETUP = (ROOT / "workflows" / "job-setup.md").read_text(encoding="utf-8")


def flat(s: str) -> str:
    s = " ".join(re.sub(r"^\s*(?:>|#:?)\s?", "", s, flags=re.M).split())
    return re.sub(r"(?<=[一-鿿，。；：、（）「」])"
                  r" +(?=[一-鿿，。；：、（）「」])", "", s)


def live():
    seen, details = ap.load(user_or_skip())
    return ap.check_which_exclusion_costs_the_most(seen, details)


class TheEntriesAreSplitPerLine(unittest.TestCase):
    def test_it_reads_the_same_sections_as_the_anchor_side(self):
        """两个函数读同几节，只是切法不同 —— 各读各的就会对不上。"""
        i = CLI.index("def exclusion_entries(")
        body = CLI[i:CLI.index("def bigrams(", i)]
        self.assertIn("EXCLUSION_SECTIONS", body)

    def test_it_says_why_it_cannot_reuse_the_anchor_bag(self):
        i = CLI.index("def exclusion_entries(")
        seg = flat(CLI[i:CLI.index("def bigrams(", i)])
        self.assertRegex(seg, r"要\*\*分得出是哪一条\*\*")

    def test_a_missing_profile_is_not_an_error(self):
        i = CLI.index("def exclusion_entries(")
        self.assertIn("if not p.is_file():", CLI[i:i + 900])

    def test_it_finds_real_entries(self):
        """现算 —— 只看条数，不看他写了什么。"""
        ents = ap._exclusion_entries(user_or_skip())
        if not ents:
            self.skipTest("这位用户还没填排除条款")
        self.assertGreater(len(ents), 3)

    def test_only_bullet_lines_count_as_entries(self):
        """**一条排除是一个列表项**，不是那几节里的每一行。

        把散文段落也收进来的话，「归到哪一条」会归到一句说明上，
        而那句说明他删不掉、也不是一条排除（变异实测：条数从 24 涨上去）。
        """
        user = user_or_skip()
        f = ROOT / "users" / user / "profile" / "candidate.md"
        if not f.is_file():
            self.skipTest("这位用户还没有资料")
        want, on = 0, False
        for ln in f.read_text(encoding="utf-8").splitlines():
            if ln.lstrip().startswith("#"):
                on = any(x in ln for x in ap._EXCLUSION_SECTIONS)
                continue
            t = ln.strip()
            if on and t.startswith(("-", "*", "·")) and len(t) > 6:
                want += 1
        self.assertEqual(len(ap._exclusion_entries(user)), want,
                         "收进来的不只是列表项")


class TheTallyAnswersTheQuestion(unittest.TestCase):
    def test_the_check_is_registered(self):
        self.assertIn(ap.check_which_exclusion_costs_the_most,
                      [fn for _, fn in ap.CHECKS])

    def test_it_reports_something(self):
        got = live()
        if not got:
            self.skipTest("样本不够，或还没有这一类的岗")
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0][0], "warn")

    def test_it_names_the_most_expensive_ones(self):
        got = live()
        if not got:
            self.skipTest("没有触发")
        self.assertIn("最贵的三条", got[0][2])
        self.assertRegex(got[0][2], r"挡掉 \d+ 个")

    def test_it_says_how_many_entries_they_spread_over(self):
        """只报前三条会让人以为一共就三条。"""
        got = live()
        if not got:
            self.skipTest("没有触发")
        self.assertRegex(got[0][2], r"归到你资料里 \d+ 条不同的排除上")

    def test_the_buckets_are_profile_entries_not_free_text(self):
        """**这条钉的是归组方式，不是措辞。**

        照理由那句自由文本分组，同一条排除会拆成「英语口语」「英语流利」
        「英语听说」「英语面试」四份 —— 桶数会涨到资料里根本没有那么多条。
        所以上界就是他资料里真有的条数（变异实测：换成按字面分组，
        桶数从 8 跳到 51）。
        """
        got = live()
        if not got:
            self.skipTest("没有触发")
        n = int(re.search(r"归到你资料里 (\d+) 条", got[0][2]).group(1))
        ents = ap._exclusion_entries(user_or_skip())
        self.assertLessEqual(
            n, len(ents),
            f"报出 {n} 个桶，而资料里只有 {len(ents)} 条排除 —— "
            f"多半是照自由文本分的组，一条排除被拆成了好几份")

    def test_it_declares_the_floor(self):
        """**这是这条最要紧的半句。** 325 个进不了表，读的人会把它当全貌。

        **「有没有未标注的」自己算，别看消息里有没有那句话。** 第一版是
        「消息里没提到就跳过」—— 那等于把「已经全写清了」和「那句话被删了」
        当成同一件事，删掉整段照样绿（变异实测）。
        """
        got = live()
        if not got:
            self.skipTest("没有触发")
        seen, _d = ap.load(user_or_skip())
        blank = sum(
            1 for e in seen.values()
            if "FAIL" in str(e.get("rank_verdict") or "")
            and ap._gate_of_verdict(e.get("rank_verdict")) == "候选人明确排除"
            and not ap._exclusion_reason(e))
        if not blank:
            self.skipTest("这批已经全写清了 —— 好事，去把这一节的数更新掉")
        m = got[0][2]
        self.assertIn(str(blank), m, "没报出有多少个进不了这张表")
        self.assertIn("是下限，不是全貌", m)

    def test_the_floor_line_stays_a_caveat_and_nothing_more(self):
        """那一句**只声明口径**，不再把规则讲一遍。

        它原来还引着「04 那一节明写着写不出是哪一条就不该判 FAIL」。
        同一个数字、同一条规则挂在两处各讲一遍，两处迟早分叉 ——
        2026-08-25 它连同处置办法一起搬去了
        `check_an_exclusion_fail_must_name_the_rule`（那里才有该敲的命令）。
        这里留下的只是一句「上面那几个数是下限」。
        """
        got = live()
        if not got or "只写了「明确排除」" not in got[0][2]:
            self.skipTest("没有未标注的")
        self.assertIn("是下限，不是全貌", got[0][2])
        self.assertNotIn("不该判 FAIL", got[0][2],
                         "规则在这儿又讲了一遍")
        # 事实搬到哪儿了，就在哪儿引出处 —— 别让它两头都没有。
        seen, det = ap.load(user_or_skip())
        other = ap.check_an_exclusion_fail_must_name_the_rule(seen, det)
        self.assertTrue(other, "那条新的没报 —— 于是这个数两头都没人解释")
        self.assertIn("04-job-evaluation.md", other[0][2])

    def test_it_says_why_this_gate_and_not_the_others(self):
        """七道门里唯一他能改的 —— 不说这句，这条读起来只是又一条统计。"""
        got = live()
        if not got:
            self.skipTest("没有触发")
        self.assertIn("唯一你今天就能改的", got[0][2])

    def test_it_carries_both_commands(self):
        """改一条排除之后不重评，名单不会变 —— 两条命令缺一不可。"""
        got = live()
        if not got:
            self.skipTest("没有触发")
        self.assertIn("/job-setup --section exclusions", got[0][2])
        self.assertIn("/job-rank --all", got[0][2])

    def test_the_section_name_it_gives_is_real(self):
        """指一个不存在的 `--section`，用户敲下去只会得到一句「没这个」。"""
        self.assertRegex(SETUP, r"\|\s*`exclusions`\s*\|")

    def test_no_markdown_reaches_the_terminal(self):
        """他的资料原文是 markdown，直接拼进来会连着星号一起显示。"""
        got = live()
        if not got:
            self.skipTest("没有触发")
        self.assertNotIn("**", got[0][2])

    def test_a_tiny_sample_says_nothing(self):
        i = AUDIT.index("def check_which_exclusion_costs_the_most(")
        self.assertIn("if len(fails) < 20:", AUDIT[i:i + 4000])

    def test_the_reason_is_recorded(self):
        i = AUDIT.index("def check_which_exclusion_costs_the_most(")
        seg = flat(AUDIT[i:AUDIT.index("    user = _cli.pick_user", i)])
        self.assertRegex(seg, r"04 说该数的那张表，此前没有任何一处在数")
        self.assertRegex(seg, r"照字面分组会把一条排除拆成四份")
        self.assertRegex(seg, r"那个数是下限，必须说出来")
        self.assertIn("2026-08-24", seg)


class TheLabelsAreCleanedTheSharedWay(unittest.TestCase):
    def test_it_reuses_the_panel_stripper(self):
        """另写一份剥标记的逻辑，两处迟早分叉 —— 这仓库反复付过学费。"""
        i = EX.index("def short_rule(")
        self.assertIn("plain(t)", EX[i:i + 600])
        self.assertIn("_ex.short_rule(", AUDIT,
                      "终端那份不再走面板那个缩写器了")

    def test_it_does_not_cut_mid_phrase(self):
        i = EX.index("def short_rule(")
        self.assertIn('"，。；、（("', EX[i:i + 900])

    def test_the_truncation_incident_is_recorded(self):
        seg = flat(EX[EX.index("def short_rule("):][:900])
        self.assertRegex(seg, r"截断不能按字数硬切")


class TheRuleItServesIsStillWritten(unittest.TestCase):
    """这一整条建立在 04 那句话上。它没了，这条就成了我们自己发明的统计。"""

    def test_the_rule_still_demands_a_citation(self):
        self.assertRegex(
            flat(EVAL), r"命中时必须写清是哪一条排除，不能只写「明确排除」四个字")

    def test_the_rule_still_gives_this_reason(self):
        self.assertRegex(flat(EVAL), r"他得先知道\*\*每条各挡掉了多少个岗\*\*")

    def test_the_rule_still_says_it_is_the_only_adjustable_one(self):
        self.assertRegex(flat(EVAL), r"它是七道里唯一他能改的")


class TheSignalItLeansOnIsReal(unittest.TestCase):
    """现算：那 101 条真的归得上，而且分布真的集中。"""

    def _tally(self):
        user = user_or_skip()
        ents = ap._exclusion_entries(user)
        if not ents:
            self.skipTest("还没填排除条款")
        seen, _d = ap.load(user)
        fails = [e for e in seen.values()
                 if "FAIL" in str(e.get("rank_verdict") or "")
                 and ap._gate_of_verdict(e.get("rank_verdict")) == "候选人明确排除"]
        if len(fails) < 20:
            self.skipTest("样本太小")
        keyed = [(x, ap._bigrams(x)) for x in ents]
        import collections
        t, blank, orphan = collections.Counter(), 0, 0
        for e in fails:
            r = ap._exclusion_reason(e)
            if not r:
                blank += 1
                continue
            rb = ap._bigrams(r)
            best, k = None, 0
            for txt, bag in keyed:
                n = len(rb & bag)
                if n > k:
                    best, k = txt, n
            if best:
                t[best] += 1
            else:
                orphan += 1
        return t, blank, orphan, len(fails)

    def test_almost_every_citation_traces_to_an_entry(self):
        """归不上的多了，说明要么他改了资料、要么打分器在编 —— 两种都该看一眼。"""
        t, _blank, orphan, _n = self._tally()
        cited = sum(t.values()) + orphan
        if cited < 20:
            self.skipTest("写清了理由的太少")
        self.assertLessEqual(
            orphan, cited * 0.1,
            f"{orphan}/{cited} 条理由在资料里对不上任何一条排除 —— "
            f"要么资料改过了，要么打分器在引一条不存在的规则"
            f"（04「引资料里没有的规则 = 编造」）")

    def test_the_distribution_is_concentrated_enough_to_act_on(self):
        """**这是这条检查值不值得存在的判据。** 平均分布的话它给不出行动。"""
        t, _b, _o, _n = self._tally()
        if sum(t.values()) < 20:
            self.skipTest("样本太小")
        top = t.most_common(1)[0][1]
        self.assertGreater(
            top, sum(t.values()) * 0.2,
            f"最贵那条只占 {top}/{sum(t.values())} —— 分布太平，"
            f"「放宽哪一条」这个问题没有明确答案了，这条检查该重新裁定")

    def test_the_uncited_pile_is_still_the_majority(self):
        """它缩下去是好事 —— 那时这一节引的 325 就该更新。"""
        t, blank, orphan, n = self._tally()
        if not blank:
            self.skipTest("全都写清了 —— 好事，去把这一节的数更新掉")
        self.assertGreater(blank, 0)
        self.assertEqual(blank + sum(t.values()) + orphan, n)


class TheGroupingHasOneHome(unittest.TestCase):
    """自由文本分组只许有一套算法 —— 两套就是两个数。"""

    def test_both_consumers_call_it(self):
        for src, who in ((AUDIT, "自检"),
                         ((ROOT / "tools" / "export_web_data.py")
                          .read_text(encoding="utf-8"), "面板导出")):
            with self.subTest(who):
                self.assertIn("_cli.exclusion_tally(", src, f"{who}没走正本")

    def test_the_audit_keeps_no_private_copy(self):
        """搬完要真搬走 —— 留一份就等着它们分叉。"""
        seg = code_of("tools/audit_pipeline.py",
                      "def check_which_exclusion_costs_the_most(")
        for gone in ("collections.Counter()", "len(rb & bag)"):
            with self.subTest(gone):
                self.assertNotIn(gone, seg, "循环还留在审计里")

    def test_the_label_is_cut_the_same_way(self):
        """同一条排除在终端和面板上要是同一个叫法。"""
        self.assertIn("_ex.short_rule(", AUDIT, "终端那份自己切了一套")


class TheJudgementIsWhatItClaims(unittest.TestCase):

    ENTRIES = ["跨城市搬迁：不接受离开上海的岗位",
               "口语不行。要求英语面试、口语沟通的岗位不投",
               "职能是营销 / 市场 / 销售 / 渠道 / BD 的不投"]

    def test_the_same_rule_written_four_ways_lands_on_one_row(self):
        """自由文本写法多，照字面分组会把一条拆成四份。"""
        tally, blank, orphan = _cli.exclusion_tally(
            self.ENTRIES, ["英语口语", "英语面试", "口语沟通", "英语听说"])
        self.assertEqual(len(tally), 1, f"一条排除被拆成了 {len(tally)} 份")
        self.assertEqual(next(iter(tally.values())), 4)
        self.assertEqual((blank, orphan), (0, 0))

    def test_a_blank_reason_is_counted_apart(self):
        """没写是哪一条的要单独数 —— 混进去就把「下限」说成了「全貌」。"""
        _t, blank, _o = _cli.exclusion_tally(self.ENTRIES, ["", "   ", "英语面试"])
        self.assertEqual(blank, 2)

    def test_a_reason_that_matches_nothing_is_not_forced_in(self):
        """宁可漏报不可误报 —— 硬塞给最像的那条会凭空给它加价。"""
        _t, _b, orphan = _cli.exclusion_tally(self.ENTRIES, ["量子计算"])
        self.assertEqual(orphan, 1)

    def test_the_reason_is_the_inner_parenthesis(self):
        """`gate_in_verdict` 给的是整段内层文本，不是「哪一条排除」。

        实测 315 条上两者一条都不相等 —— 导出侧要是复用了前者，
        315 个岗会全归到同一条上，那一格就永远只有一行。
        """
        v = "硬门 FAIL (候选人明确排除（行业背景硬要求）)"
        self.assertEqual(_cli.exclusion_reason(v), "行业背景硬要求")
        self.assertNotEqual(_cli.exclusion_reason(v),
                            _cli.gate_in_verdict(v)[1])
        self.assertEqual(_cli.exclusion_reason("硬门 FAIL (候选人明确排除)"), "")


class TheLabelDoesNotStopHalfWay(unittest.TestCase):
    """这几个字上面板，断在半截是这个仓库有名字的一类。"""

    #: 真实数据里那一条。**上限给 22 是为了让切点正好落在引号里** ——
    #: 按字数硬切时它会切成 `…仍在「明确`，一个开不了口的引号。
    #: 不挑这个位置的话，硬切与按标点切出来的字一样，断言就是空的。
    LONG = "行业背景硬要求那条**不在放宽范围**，仍在「明确排除」里，别放宽"

    def test_a_long_rule_is_cut_at_a_punctuation(self):
        got = ex.short_rule(self.LONG, 22)
        self.assertTrue(got.endswith("…"))
        for a, b in (("「", "」"), ("（", "）")):
            self.assertEqual(got.count(a), got.count(b), f"断在半截：{got}")

    def test_a_hard_cut_really_would_break_it(self):
        """判据自检：这个用例得真能分出两种切法，否则上面那条什么都没验。"""
        naive = ex.plain(self.LONG).strip()[:22]
        self.assertNotEqual(naive.count("「"), naive.count("」"),
                            "硬切在这个位置并不会断 —— 换一个上限或换一句话")

    def test_a_short_rule_is_left_alone(self):
        self.assertEqual(ex.short_rule("不接受跨城市搬迁"), "不接受跨城市搬迁")

    def test_markdown_never_reaches_the_label(self):
        self.assertNotIn("**", ex.short_rule("**不接受**跨城市搬迁"))


class ThePanelSaysWhichOne(unittest.TestCase):

    def test_the_field_is_declared_and_whitelisted(self):
        """`normalize` 是手写白名单 —— 漏掉一个字段那块界面就永远不出现。"""
        self.assertIn("topExclusions?: { rule: string; n: number }[];", LOAD)
        self.assertIn("topExclusions: d.topExclusions,", LOAD)

    def test_it_sits_next_to_the_total_it_refines(self):
        anchor = 'x.gate === "你资料里写明不要的"'
        self.assertEqual(APP.count(anchor), 1, "锚点不唯一")
        i = APP.index(anchor)
        self.assertIn("snap.topExclusions", APP[i:i + 1600],
                      "细分没挨着那个总数 —— 分开摆就是两块互不相干的数")

    def test_it_is_conditional_not_always_on(self):
        self.assertIn("(snap.topExclusions ?? []).length > 0 && (", APP,
                      "样本不够时那一格该整个不出现")

    def test_it_says_both_commands_and_which_order(self):
        """改完不重评，屏幕上的分数还是老的 —— 两条命令要一起给。"""
        # 锚唯一的那一处：条件式只有一个，`.map` 那行是第二处。
        anchor = "(snap.topExclusions ?? []).length > 0 && ("
        self.assertEqual(APP.count(anchor), 1, "锚点不唯一")
        i = APP.index(anchor)
        seg = APP[i:i + 1200]
        self.assertIn("/job-setup --section exclusions", seg)
        self.assertIn("/job-rank --all", seg)
        self.assertLess(seg.index("/job-setup --section exclusions"),
                        seg.index("/job-rank --all"), "顺序反了")


class TheSignalIsReal(unittest.TestCase):
    """有语料时验一次：这一格不是凭空加的，而且它真能分出高下。"""

    def _snap(self):
        p = ROOT / "web" / "public" / "data.json"
        if not p.is_file():
            self.skipTest("还没导出过面板数据")
        return json.loads(p.read_text(encoding="utf-8"))

    def test_the_top_rule_is_meaningfully_worse_than_the_rest(self):
        top = self._snap().get("topExclusions") or []
        if len(top) < 2:
            self.skipTest("这份语料里排不出高下")
        self.assertGreater(
            top[0]["n"], top[1]["n"],
            "第一条并不比第二条贵 —— 那这一格帮不了他决定动哪一条")

    def test_it_never_out_counts_the_total_it_refines(self):
        d = self._snap()
        top = d.get("topExclusions") or []
        if not top:
            self.skipTest("这份语料里没有这一格")
        tot = next((x["n"] for x in (d.get("gateFailTally") or [])
                    if x["gate"] == "你资料里写明不要的"), 0)
        self.assertLessEqual(
            sum(x["n"] for x in top), tot,
            "细分加起来比它上面那个总数还大 —— 相邻两行、同一件事、两个数")

if __name__ == "__main__":
    unittest.main()
