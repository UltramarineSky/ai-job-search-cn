# -*- coding: utf-8 -*-
"""评分里三样确定性的东西，此前由执行者逐个岗手算 —— 12% 错。

`04-job-evaluation.md` 的四维里，只有三维要读 JD 之后拿主意（技能与经验、
强度与公司性质、发展与风险）。剩下的三样是**纯函数**：

    薪资与职级 = f(薪资串, 薪数, 底线, 期望区间)     —— 查一张四行的表
    综合分     = Σ 维度 × 权重 + 调整
    判词       = min(分数档, 技能与经验的天花板)

实测活动用户 2026-08-29，四维齐全、有分数的 728 个岗里：
**薪资维错 89 个（12%）、综合分错 85 个（12%）、判词错 6 个（1%）。**

一个确定性函数手算几百遍，错这些是必然的 —— 12% 不是谁马虎，是分工放错了
地方。此前三条自检都是**事后**报（`audit_pipeline`），人再手工订正；
那是烟雾报警器，不是防火。`tools/score.py` 把这三样从手里拿走。

这条守卫钉两件事：**只有一份实现**（查的一侧和算的一侧共用 `scoring`），
以及**该拿走的确实拿走了**（工作流里点名要跑）。
"""
import json
import pathlib
import sys
import inspect
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tests"))
from _live import user_or_skip  # noqa: E402
import audit_pipeline as ap  # noqa: E402
import score as sc_cli  # noqa: E402
import scoring as sc  # noqa: E402
import _cli  # noqa: E402


class OnlyOneImplementation(unittest.TestCase):
    """查的一侧和算的一侧共用同一份 —— 否则会「自检说对、写回又算成另一个数」。"""

    def test_the_auditor_reuses_the_scorer(self):
        self.assertIs(ap._DIM_WEIGHTS, sc.DIM_WEIGHTS)
        self.assertIs(ap._VERDICT_BANDS, sc.VERDICT_BANDS)
        self.assertIs(ap._VERDICT_CEILINGS, sc.VERDICT_CEILINGS)
        self.assertIs(ap._VERDICT_ORDER, sc.VERDICT_ORDER)

    def test_the_pay_table_is_not_copied(self):
        self.assertEqual((ap._PAY_TOP, ap._PAY_IN, ap._PAY_OK),
                         (sc.PAY_TOP, sc.PAY_IN, sc.PAY_OK))

    def test_the_wrappers_delegate(self):
        for s in (0, 29, 30, 44, 45, 59, 60, 74, 75, 100):
            with self.subTest(score=s):
                self.assertEqual(ap._band_of(s), sc.band_of(s))
        for k in (0, 39, 40, 59, 60, 79, 80, 100):
            with self.subTest(skill=k):
                self.assertEqual(ap._ceiling_of(k), sc.ceiling_of(k))


class TheThreeFunctionsAreRight(unittest.TestCase):
    FLOOR, EXPECT = 45.0, (72.0, 96.0)

    def test_the_pay_table_has_four_rows_and_only_four(self):
        allowed = {sc.PAY_TOP, sc.PAY_IN, sc.PAY_OK, sc.PAY_LOW}
        for lo in range(5, 200, 3):
            for m in (None, 12, 14, 15, 16):
                got = sc.pay_dim({"salary": f"{lo}-{lo*2}k", "salaryMonths": m},
                                 self.FLOOR, self.EXPECT)
                with self.subTest(salary=f"{lo}-{lo*2}k", months=m):
                    self.assertIn(got, allowed)

    def test_the_verdict_takes_the_lower_of_the_two(self):
        """技能 28、总分 60 —— 04 举过的那个例子：判词不许是「值得投」。"""
        self.assertEqual(sc.verdict_of(60, 28), "不建议")
        self.assertEqual(sc.verdict_of(60, 85), "值得投")   # 分数档才是那道低的
        self.assertEqual(sc.verdict_of(80, 85), "强匹配")

    def test_the_composite_counts_the_adjustment(self):
        dims = {"技能与经验": 70, "薪资与职级": 60,
                "强度与公司性质": 50, "发展与风险": 60}
        base = sc.composite(dims)
        self.assertEqual(sc.composite(dims, {"专业减分": -5}), base - 5)

    def test_coarse_levels_snap_down_not_up(self):
        """往低不往高 —— 假设值可以让分保守，不可以让岗虚高。"""
        self.assertEqual(sc.snap_coarse(60), 50)
        self.assertEqual(sc.snap_coarse(55), 50)
        self.assertEqual(sc.snap_coarse(35), 30)
        self.assertEqual(sc.snap_coarse(85), 85)


class ItRefusesTheOnesItMustNotTouch(unittest.TestCase):
    def test_deep_evaluations_are_left_alone(self):
        """深评正本在 `evaluation.md` —— 库里单边改会被 writeback 顶回去，
        还会留下「硬门 FAIL 配判词值得投」的混合状态（2026-08-28 撞过）。"""
        self.assertFalse(sc.is_triage({"来源": "深评（读过 JD 正文）"}))
        self.assertTrue(sc.is_triage({"来源": "粗筛（读过 JD 正文）"}))
        self.assertTrue(sc.is_triage({"来源": "预筛（未抓 JD）"}))

    def test_scoreless_entries_are_left_alone(self):
        """**这才是当初露出来的那一头。** `rank_score=None` 是有意的：
        硬门 FAIL / 预筛结案 / 已下线。按四维重算等于把排除掉的岗复活 ——
        2026-08-29 试运行时两个这样的岗被算成「跳过 → 强匹配」。"""
        for e in ({"rank_score": None, "rank_verdict": "已下线"},
                  {"rank_score": None, "rank_verdict": "硬门 FAIL (学历与院校)"},
                  {"rank_score": 60, "rank_verdict": "不满足硬性条件"}):
            with self.subTest(entry=e):
                self.assertTrue(sc.is_scoreless(e))
        self.assertFalse(sc.is_scoreless({"rank_score": 60,
                                          "rank_verdict": "粗筛：值得投"}))


class TheWorkflowsCallIt(unittest.TestCase):
    """拿走了就要在流程里点名 —— 不写进去，下一轮还是靠人记得。"""

    def test_job_rank_runs_it_in_step_zero(self):
        t = (ROOT / "workflows" / "job-rank.md").read_text(encoding="utf-8")
        self.assertIn("tools/score.py --apply", t)

    def test_job_auto_points_at_the_per_batch_list(self):
        """auto 只指路，不抄命令 —— 抄一份就等着它分叉。

        2026-08-30 前这里断言 `score.py --apply` 出现在 auto 那一节里；
        当天两处各加了两条新命令，而 auto 那句「Step 0 那几条」还停在旧的
        四条上，同一个文件里「那几条」指四条、下面又「再加一条」加了两条。
        清单收归 `job-rank.md` Step 0 之后，这里改成钉「指对了没有」——
        「谁跑它」的守卫在 `test_perishable_evidence_is_checked_per_batch`。
        """
        t = (ROOT / "workflows" / "job-auto.md").read_text(encoding="utf-8")
        i = t.index("每批都要跑的机械步骤")
        seg = t[i:i + 400]
        self.assertIn("job-rank.md", seg)
        self.assertIn("score.py", seg)
        self.assertIn("每批都要跑", seg)

    def test_the_framework_says_the_tool_owns_them(self):
        t = (ROOT / "workflows" / "reference"
             / "04-job-evaluation.md").read_text(encoding="utf-8")
        i = t.index("#### 打分口径：比的是「够不够」")
        seg = t[i:i + 1200]
        self.assertIn("不用你手算", seg)
        self.assertIn("score.py", seg)
        self.assertRegex(seg, r"12%")     # 那个错误率是这条改动的全部理由


class ItIsIdempotent(unittest.TestCase):
    """跑第二遍必须是 0 改动 —— 否则它自己就是一个漂移源。"""

    def test_a_settled_store_needs_no_change(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = pathlib.Path(tmp.name)
        d = root / "users" / "u" / "job_scraper"
        d.mkdir(parents=True)
        dims = {"技能与经验": 70, "薪资与职级": 55,
                "强度与公司性质": 50, "发展与风险": 70}
        entry = {"title": "某岗", "url": "https://x.com/1",
                 "salary": "40-70K", "salaryMonths": 16,
                 "rank_score": sc.composite(dims),
                 "rank_verdict": "粗筛：" + sc.verdict_of(sc.composite(dims), 70),
                 "rank_breakdown": dict(dims, **{"来源": "粗筛（读过 JD 正文）"})}
        (d / "seen_jobs.json").write_text(
            json.dumps({"seen": {"k": entry}}, ensure_ascii=False), encoding="utf-8")
        old_root = sc_cli.ROOT
        try:
            sc_cli.ROOT = root
            rows, _ = sc_cli.plan("u")
        finally:
            sc_cli.ROOT = old_root
        self.assertEqual(rows, [], "一条已经算好的记录还被要求再改")


class EveryGateNameInTheVerdictIsChecked(unittest.TestCase):
    """一条判词挂两道门时，第二道此前没人看。

    `_cli.gate_in_verdict`（单数）只取第一道 —— 那是对的，它服务于
    「有几个岗被这道门挡住」，拆开会让计数大于岗数。但**校名**那一侧
    漏看第二道就等于放过它。

    实测 2026-08-29：判词里点了门名的 747 个岗里，门名不在七道里的 29 个；
    而按「只看第一道」查只报得出 7 个 —— 差的 22 个都是
    `硬门 FAIL (工作年限 + 行业背景硬要求)` 这种第一道合法、第二道不合法的写法。
    """
    def test_a_composite_verdict_exposes_the_second_gate(self):
        """**这才是当初露出来的那一头。**"""
        known, off = _cli.gates_in_verdict("硬门 FAIL (工作年限 + 行业背景硬要求)")
        self.assertEqual(known, ["工作年限"])
        self.assertEqual(off, ["行业背景硬要求"])

    def test_the_singular_helper_still_counts_by_the_first_gate(self):
        """单数那个不许跟着改 —— 它答的是另一个问题。"""
        gate, _inner = _cli.gate_in_verdict("硬门 FAIL (工作年限 + 行业背景硬要求)")
        self.assertEqual(gate, "工作年限")

    def test_a_reason_in_nested_brackets_is_not_a_gate_name(self):
        """`明确排除（英语口语）` 点的门是「明确排除」，括注是理由。"""
        known, off = _cli.gates_in_verdict("硬门 FAIL (明确排除（英语口语）)")
        self.assertEqual(off, [])
        self.assertEqual(known, ["明确排除"])

    def test_full_width_brackets_parse(self):
        """深评写全角、粗筛写半角 —— 只认半角会整批漏掉（实测 25 个岗）。"""
        known, off = _cli.gates_in_verdict("不满足硬性条件（学历）")
        self.assertEqual((known, off), (["学历"], []))

    def test_a_non_gate_verdict_yields_nothing(self):
        for v in ("值得投", "粗筛：可以考虑", "已下线", ""):
            with self.subTest(verdict=v):
                self.assertEqual(_cli.gates_in_verdict(v), ([], []))

    def test_the_audit_uses_the_plural_one(self):
        src = ap.check_gate_is_one_of_the_seven.__code__.co_names
        self.assertIn("gates_in_verdict", src)


class DeepModeNeverWritesOneSideAlone(unittest.TestCase):
    """`--deep` 改深评的薪资维时，必须连 `evaluation.md` 一起改。

    ## 这条守卫补的是什么

    深评的分与判词，正本在 `evaluation.md`；只改库那一边，`writeback --apply`
    会把旧数顶回来，中间那段时间面板上是另一个数
    （`job-auto.md`「存档是事实源，工具不单边篡改」）。原来 `score.py` 靠**整块跳过深评**来守这条 —— 代价是
    89 个查表结果要用户逐个敲 `/job-apply`。

    `--deep` 把跳过换成「连文件一起改」。**换的过程中当场破过一次这条不变量**
    （2026-08-29）：判据写成了「有没有找到文件」，找不到就只写库。而
    「按链接找不到」不等于「没有存档」—— 同一个岗在猎聘挂了两处
    （`/a/…449` 与 `/a/…451`，相邻的号），评估目录的「职位链接」写的是前者，
    后者那条也在库里、也是深评。于是 18 条只写了库那一边，其中一条当场被
    `test_deep_eval_writeback` 抓到「文件 73 ≠ 库 74」。

    **判据得是「能不能连文件一起改」，不是「有没有文件」。**
    """

    def test_no_row_lacks_its_document(self):
        user = user_or_skip()
        rows, _skip = sc_cli.plan(user, deep=True)
        naked = [(r["entry"].get("title") or "")[:24] for r in rows if not r.get("doc")]
        self.assertEqual(naked, [], "深评模式产出了没有评估文件的行 —— "
                                    "写下去就是只改库那一边")

    def test_the_shallow_mode_still_refuses_documented_ones(self):
        """粗筛那一侧的老规矩不变：有评估文件的一律不碰。"""
        src = inspect.getsource(sc_cli.plan)
        self.assertIn("有深评文件", src)
        self.assertIn("深评但没找到评估文件", src)


class ThePayNoteAgreesWithThePayDim(unittest.TestCase):
    """那一维的分和它的说明必须出自同一次折算。

    分和说明分头算就会出现「写着 55、解释的却是另一个数」，而那句话要显示在
    总览页和评估文件里 —— 自检「薪资维和它自己的薪资串对不上」盯的就是这个。
    """

    CASES = [("30-60k", 15), ("30-50k", None), ("65-85k", None),
             ("20-40k", 14), ("35-40k·15薪", 15), ("面议", None), ("", None)]

    def test_both_are_none_or_both_are_not(self):
        for s, m in self.CASES:
            with self.subTest(salary=s, months=m):
                e = {"salary": s, "salaryMonths": m}
                d = sc.pay_dim(e, 45.0, (72.0, 96.0))
                n = sc.pay_note(e, 45.0, (72.0, 96.0))
                self.assertEqual(d is None, n is None)

    def test_the_note_never_says_the_months_twice(self):
        """薪资串自己带了薪数时别再拼一遍 —— 实测出过「35-40k·15薪×15薪」。"""
        n = sc.pay_note({"salary": "35-40k·15薪", "salaryMonths": 15},
                             45.0, (72.0, 96.0))
        self.assertEqual(n.count("薪 ="), 1)
        self.assertNotIn("薪×", n.split("=")[0].replace("·15薪×15薪", "×"))
        self.assertIn("35-40k×15薪", n)

    def test_the_note_carries_no_markdown_bold(self):
        """这段字会进纯文本节点 —— 星号会原样显示（AGENTS.md 末尾那条）。"""
        for s, m in self.CASES:
            n = sc.pay_note({"salary": s, "salaryMonths": m},
                                 45.0, (72.0, 96.0))
            with self.subTest(salary=s):
                self.assertNotIn("**", n or "")

if __name__ == "__main__":
    unittest.main()

class TheSkipCounterNamesWhatItSkipped(unittest.TestCase):
    """终端那行「跳过：粗筛 371、…」里的名字得对得上被跳过的那批。

    不加 `--deep` 时这一趟算的是粗筛，跳过去的是**深评**；加了 `--deep` 反过来。
    原来两个名字写反了：实测 2026-09-03 一轮粗筛落盘后印「跳过：粗筛 371」，
    而那 371 个全是深评 —— 读的人会以为自己刚写的粗筛一条没算着。
    """

    def _root(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = pathlib.Path(tmp.name)
        d = root / "users" / "u" / "job_scraper"
        d.mkdir(parents=True)
        dims = {"技能与经验": 70, "薪资与职级": 55,
                "强度与公司性质": 50, "发展与风险": 70}
        def entry(src):
            return {"title": "某岗", "url": "https://x.com/" + src, "salary": "40-70K",
                    "salaryMonths": 16, "rank_score": sc.composite(dims),
                    "rank_verdict": "粗筛：值得投" if src.startswith("粗筛") else "值得投",
                    "rank_breakdown": dict(dims, **{"来源": src})}
        (d / "seen_jobs.json").write_text(json.dumps(
            {"seen": {"a": entry("粗筛（读过 JD 正文）"), "b": entry("深评")}},
            ensure_ascii=False), encoding="utf-8")
        return root

    def _plan(self, deep):
        # 只测跳过计数的命名，不牵扯 candidate.md：把底线/期望直接钉住。
        old_root, old_bounds = sc_cli.ROOT, sc_cli._bounds
        try:
            sc_cli.ROOT = self._root()
            sc_cli._bounds = lambda user: (45.0, (72.0, 96.0))
            return sc_cli.plan("u", deep=deep)[1]
        finally:
            sc_cli.ROOT, sc_cli._bounds = old_root, old_bounds

    def test_without_deep_the_skipped_ones_are_the_deep_ones(self):
        skip = self._plan(deep=False)
        self.assertEqual(skip["深评"], 1, skip)
        self.assertEqual(skip["粗筛"], 0, skip)

    def test_with_deep_the_skipped_ones_are_the_triage_ones(self):
        skip = self._plan(deep=True)
        self.assertEqual(skip["粗筛"], 1, skip)
        self.assertEqual(skip["深评"], 0, skip)
