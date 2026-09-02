# -*- coding: utf-8 -*-
"""审计报了两个「趋势」，两个都是从不能算趋势的材料里算出来的。

## 一、拿规则生效前的产出，算这条规则的执行率

`check_maybe_tier_has_questions` 报的是：

> 最近 30 份里就缺 22 份（73%）——**不是存量遗留，新出的更差**。

而「投前必问」这一节是 **2026-08-22** 才补进 `04-job-evaluation.md` 的输出格式的
（那份文档自己写着）。实测 2026-08-23：268 份深评里最新的一份写于 **08-19**，
「可以考虑」那一档最新的是 **08-17** —— **规则之后一份都还没产出**。

那句话把**存量**说成了**规则不灵**。读的人会去重写一条还没被执行过的规则，
而正确的动作只是「跑一批新的再看」。

## 二、把批次差异读成时间趋势

`check_evaluation_sections` 原来按**文件 mtime** 排，报「新出的已经好多了（13%）」。
改成按深评自己写的评估日期排，同一份数据立刻翻成「新出的更差（90%）」——
**两个方向都下过因果断语，而两个都不是真的**。按日期摊开才看得出形状：

    08-10  26 份全缺      08-11  79 份全写了
    08-13  16 份全缺      08-12  77 份只缺 1
    08-17  40 份全缺      08-19   3 份全写了

缺的 86 份就是这几批加起来。**是整批漏，不是慢慢漂** —— 一个 30 份的窗口跨在
批次边界上，落哪边就报哪边的数，方向纯属抽签。这个形状也换了该做的事：
不是逐份补小节，是去看那几次运行当时怎么跑的。

两条一起指向同一件事：**一个数字要能支撑一句因果话，得先问它是从什么材料上算的。**
"""
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tests"))
import audit_pipeline as AP  # noqa: E402
from _srcscan import strip_comments  # noqa: E402

EVAL_DOC = (ROOT / "workflows" / "reference"
            / "04-job-evaluation.md").read_text(encoding="utf-8")


def _eval(date, verdict, sections=(), *, ask=False):
    """造一份深评。小节名走 `EVAL_SECTIONS` 的正名，判词走结论那一行。"""
    body = [f"# 职位评估：某公司 - 某岗位", "",
            f"- 评估日期：{date}（构造）", ""]
    for s in sections:
        body += [f"## {s}", "略", ""]
    if ask:
        body += ["## 投前必问", "- 问一句", ""]
    body += ["## 结论", f"**{verdict}**", ""]
    return "\n".join(body)


def _mk(root, files):
    apps = root / "users" / "u" / "documents" / "applications"
    for i, text in enumerate(files):
        d = apps / f"c{i:03d}_岗"
        d.mkdir(parents=True)
        (d / "evaluation.md").write_text(text, encoding="utf-8")


def _run(fn, root):
    old_root, old_pick = AP.ROOT, AP._cli.pick_user
    try:
        AP.ROOT = root
        AP._cli.pick_user = lambda *a, **k: "u"
        return fn({}, {})
    finally:
        AP.ROOT, AP._cli.pick_user = old_root, old_pick


SRC = (ROOT / "tools" / "audit_pipeline.py").read_text(encoding="utf-8")


class TheWatermarkSentenceHasOneHome(unittest.TestCase):
    """「最近一批是 X（N 个）—— 存量不必逐个补……」写了三遍。

    `batch_note` 自己的说明开头就写着「手写两遍就会有第三遍写不出来。这里做成
    一个函数」—— 那句话写下之后，**同一个形状又长了三份**：薪资维那条、总分
    那条（连前面两行 `latest` / `recent` 的记账都一字不差）、读了 JD 没落库那条。

    它和 `batch_note` 说的不是一回事：那个要**分母**（那天判过这道门的全部），
    报「最近一批里犯了几成」；这个只有**分子**，报的是水位线「最近一次是哪天、
    那天几个」。所以不是把它并进 `batch_note`，是给它自己一个家。
    """

    def test_nobody_hand_writes_it_again(self):
        n = SRC.count("最近一批是 {")
        self.assertEqual(
            n, 1,
            f"这句话在源码里出现了 {n} 次 —— 只许 `watermark_note` 自己那一处")

    def test_it_reports_the_latest_day_and_its_count(self):
        got = AP.watermark_note(["2026-08-20", "2026-08-26",
                                 "2026-08-26", "2026-08-19"])
        self.assertIn("最近一批是 2026-08-26（2 个）", got)
        self.assertIn("盯的是这个数会不会再涨", got)

    def test_no_dates_means_no_sentence(self):
        """一个日期都没有就闭嘴 —— 「没查」和「查过没有」是两件事。"""
        self.assertEqual(AP.watermark_note([]), "")
        self.assertEqual(AP.watermark_note(["", "", None]), "")

    def test_a_missing_date_does_not_become_the_latest_batch(self):
        """**这是收进来时顺手修掉的那个坑。**

        「读了 JD 没落库」那条原来把缺日期的记成 `"?"` 再 `sorted(...)[-1]`，
        而 `?`（0x3F）排在数字之后 —— 只要有一条没写 `rank_date`，
        「最近一批」就会印成 `?`。"""
        got = AP.watermark_note(["2026-08-26", "", "2026-08-20"])
        self.assertIn("2026-08-26", got)
        self.assertNotIn("?", got)

    def test_a_caller_really_prints_it(self):
        """调用点真的把那句话印出去了 —— 喂构造数据，读返回的报文。

        这条替掉的是一条钉源码的（见下面那段说明）。**变异实测证明替得对**：
        把调用点改成 `tail = ""`（绕过助手），钉源码那条照样绿，这条当场红。"""
        seen = {}
        for i in range(3):
            seen[f"k{i}"] = {
                "url": f"https://x/{i}", "title": f"岗{i}", "company": "c",
                "rank_date": "2026-08-30", "rank_score": 80,
                "rank_breakdown": {"技能与经验": 50, "薪资与职级": 50,
                                   "强度与公司性质": 50, "发展与风险": 50},
            }
        rows = AP.check_score_reconciles(seen, {})
        self.assertEqual(len(rows), 1, "构造数据没触发这条检查")
        self.assertIn("最近一批是 2026-08-30（3 个）", rows[0][2],
                      "调用点绕过了助手 —— 那句话没印出去")

    #: 这里原来还有一条 `test_the_three_callers_go_through_it`：
    #: 在三个调用点的源码片段里查 `watermark_note(`。
    #: **本仓库自己那条棘轮把它拦下了**（`test_a_guard_pins_behaviour_not_a_line`：
    #: 钉在某一行代码上的断言不许再涨）—— 拦得对，它钉的是「那一行长什么样」。
    #:
    #: 上面那条 `test_nobody_hand_writes_it_again` 覆盖了真正要防的事：
    #: 谁再手写一份，这句话在源码里就出现两次，当场红。


class TheRuleDateIsPinnedToItsSource(unittest.TestCase):
    def test_the_constant_exists(self):
        self.assertTrue(re.fullmatch(r"\d{4}-\d{2}-\d{2}", AP._ASK_RULE_SINCE))

    def test_it_matches_what_the_document_says(self):
        """常量和正本各写各的，两边就会飘。04 自己写着这一节哪天进的输出格式。"""
        self.assertIn(f"这一节是 {AP._ASK_RULE_SINCE} 补进输出格式的", EVAL_DOC,
                      "04 里那句话和 _ASK_RULE_SINCE 对不上了")


class TheEvalDateComesFromTheFileNotTheFilesystem(unittest.TestCase):
    def test_it_reads_the_header(self):
        self.assertEqual(AP._eval_date(_eval("2026-08-17", "可以考虑")),
                         "2026-08-17")

    def test_it_returns_empty_when_absent(self):
        self.assertEqual(AP._eval_date("# 没有抬头日期"), "")

    def test_it_does_not_take_just_any_date(self):
        """正文里到处是日期（JD 发布日、他的在职区间）。只认抬头那一行。"""
        t = "# 职位评估\n\n发布于 2020-01-01。\n\n- 评估日期：2026-08-17\n"
        self.assertEqual(AP._eval_date(t), "2026-08-17")

    def test_no_check_sorts_by_mtime(self):
        """mtime 会被重新归档、批量改权限、同步工具推到今天 ——
        那时候「最近 30 份」就是随机 30 份，而报告仍会照它下断语。"""
        code = strip_comments((ROOT / "tools" / "audit_pipeline.py")
                              .read_text(encoding="utf-8"))
        self.assertNotIn("st_mtime", code, "又有检查按文件时间排序了")


class TheAskBeforeCheckRefusesToJudgeARuleItCannotSee(unittest.TestCase):
    def test_it_says_so_when_everything_predates_the_rule(self):
        before = AP._ASK_RULE_SINCE.replace("-22", "-17")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _mk(root, [_eval(before, "可以考虑") for _ in range(20)])
            out = _run(AP.check_maybe_tier_has_questions, root)
        msg = out[0][2]
        self.assertIn("全部产于规则之前", msg)
        self.assertIn(AP._ASK_RULE_SINCE, msg, "没说清规则是哪天生效的")
        self.assertIn(before, msg, "没说清最新一份是哪天写的")

    def test_it_does_not_blame_the_rule_on_pre_rule_data(self):
        """这才是真正要防的那句话。"""
        before = AP._ASK_RULE_SINCE.replace("-22", "-17")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _mk(root, [_eval(before, "可以考虑") for _ in range(40)])
            msg = _run(AP.check_maybe_tier_has_questions, root)[0][2]
        self.assertNotIn("新出的更差", msg)
        self.assertNotIn("不是存量遗留", msg)

    def test_it_tells_the_reader_what_to_do_instead(self):
        before = AP._ASK_RULE_SINCE.replace("-22", "-17")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _mk(root, [_eval(before, "可以考虑") for _ in range(20)])
            msg = _run(AP.check_maybe_tier_has_questions, root)[0][2]
        self.assertIn("跑一批新的", msg)

    def test_the_denominator_is_the_post_rule_batch(self):
        """有了生效后的样本才谈执行率 —— 而且分母只能是那一批，
        否则存量会把当下的问题稀释掉。"""
        before = AP._ASK_RULE_SINCE.replace("-22", "-17")
        after = AP._ASK_RULE_SINCE.replace("-22", "-25")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _mk(root, [_eval(before, "可以考虑") for _ in range(50)]
                + [_eval(after, "可以考虑") for _ in range(8)]
                + [_eval(after, "可以考虑", ask=True) for _ in range(4)])
            msg = _run(AP.check_maybe_tier_has_questions, root)[0][2]
        self.assertIn("规则生效后的 12 份里仍缺 8 份", msg)
        self.assertIn("67%", msg, "百分比按生效后那批算，不是全量")
        self.assertIn("不是存量", msg)

    def test_it_says_when_the_post_rule_batch_is_clean(self):
        """全写了也要说 —— 否则读者以为那 61 份存量是当下的问题。"""
        before = AP._ASK_RULE_SINCE.replace("-22", "-17")
        after = AP._ASK_RULE_SINCE.replace("-22", "-25")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _mk(root, [_eval(before, "可以考虑") for _ in range(30)]
                + [_eval(after, "可以考虑", ask=True) for _ in range(10)])
            msg = _run(AP.check_maybe_tier_has_questions, root)[0][2]
        self.assertIn("缺的都是存量", msg)

    def test_a_thin_clean_sample_does_not_get_the_reassurance_either(self):
        """**两个方向同一个下限。** 悲观那句要 10 份才敢说，宽慰那句原来
        一份就说 —— 于是「缺的都是存量」结构上只可能往好的方向出现：
        同样是 6 份，全写了就下定论，有没写的反而什么都不说。
        """
        before = AP._ASK_RULE_SINCE.replace("-22", "-17")
        after = AP._ASK_RULE_SINCE.replace("-22", "-25")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _mk(root, [_eval(before, "可以考虑") for _ in range(30)]
                + [_eval(after, "可以考虑", ask=True) for _ in range(6)])
            msg = _run(AP.check_maybe_tier_has_questions, root)[0][2]
        self.assertNotIn("缺的都是存量", msg)
        self.assertIn("还不够看趋势", msg, "样本不够就该直说不够，不是沉默")

    def test_a_thin_post_rule_sample_does_not_get_a_verdict(self):
        """生效后只有三五份，报个规模可以，**不许下「更差」这种断语**。"""
        before = AP._ASK_RULE_SINCE.replace("-22", "-17")
        after = AP._ASK_RULE_SINCE.replace("-22", "-25")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _mk(root, [_eval(before, "可以考虑") for _ in range(30)]
                + [_eval(after, "可以考虑") for _ in range(3)])
            msg = _run(AP.check_maybe_tier_has_questions, root)[0][2]
        self.assertIn("还不够看趋势", msg)
        self.assertNotIn("新出的更差", msg)

    def test_the_tier_filter_survives(self):
        """只查「可以考虑」—— 别的档没有这个要求，一并查就是假阳性。"""
        after = AP._ASK_RULE_SINCE.replace("-22", "-25")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _mk(root, [_eval(after, "值得投") for _ in range(20)])
            self.assertEqual(_run(AP.check_maybe_tier_has_questions, root), [])


class TheSectionsCheckReportsBatchesNotATrend(unittest.TestCase):
    SEC = ("评分明细", "优势", "缺口", "职位真伪信号", "建议", "结论")

    def _corpus(self, root):
        """两批全缺、两批全写 —— 实测那个形状的最小复制。"""
        full = [_eval("2026-08-11", "值得投", self.SEC) for _ in range(9)]
        full += [_eval("2026-08-19", "值得投", self.SEC) for _ in range(7)]
        thin = [_eval("2026-08-10", "值得投", ("评分明细", "结论")) for _ in range(8)]
        thin += [_eval("2026-08-17", "值得投", ("评分明细", "结论")) for _ in range(6)]
        _mk(root, full + thin)

    def test_it_counts_the_batches(self):
        """报的是**形状**：几批全缺、几批全写齐，各多少份。

        ⚠️ **2026-08-30 起不再逐批列日期。** 那串枚举是为了立住「整批漏，
        不是慢慢漂」这个判断，而**那个问题已经答完了**：整批漏，且几乎只缺
        「建议」那一节（实测表进了 04 的「建议」那一节）。结论立住之后，
        原始数据留在收尾里就成了噪音 —— 它把「你现在动得了什么」那句推到了
        400 字开外，而这一档的全部价值就在那一句。一行从 472 字降到 321 字。

        「全缺」读起来像「每一节都没有」，实际是「每份都缺了至少一节」
        —— 措辞 2026-08-23 改过，那半句照旧钉着。
        """
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._corpus(root)
            msg = _run(AP.check_evaluation_sections, root)[0][2]
        self.assertIn("是整批漏，不是慢慢漂", msg)
        self.assertIn("2 批（共 14 份）每份都缺了至少一节", msg)
        self.assertIn("另有 2 批（共 16 份）全写齐", msg)

    def test_it_no_longer_lists_every_date(self):
        """列日期就是把原始数据摆进收尾 —— 结论已经有了，数据该退场。"""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._corpus(root)
            msg = _run(AP.check_evaluation_sections, root)[0][2]
        for d in ("2026-08-10", "2026-08-17", "2026-08-19"):
            with self.subTest(d=d):
                self.assertNotIn(f"{d} 那批", msg)

    def test_it_still_says_whether_the_latest_batch_did_it(self):
        """收尾真正要的是「最近一批还犯不犯」—— 走共用的 `batch_note`。

        这条检查手写的那串枚举正是 `batch_note` 的设计来源
        （它的 docstring 里逐字引着），而它自己一直没用上那个函数。
        """
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._corpus(root)
            msg = _run(AP.check_evaluation_sections, root)[0][2]
        # 08-19 只有 7 份，`batch_note` 的 `min_size` 是 8 —— 太小的批次
        # 说不出任何东西，它按设计跳过，落到 08-11 那 9 份上。
        self.assertIn("最近一批（2026-08-11，9 份）里 0 份", msg)

    def test_it_never_calls_a_direction(self):
        """这条检查报过两个相反的方向，两个都是抽签抽出来的。"""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._corpus(root)
            msg = _run(AP.check_evaluation_sections, root)[0][2]
        for phrase in ("新出的更差", "新出的已经好多了", "最近 30 份"):
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, msg)

    def test_it_redirects_the_fix(self):
        """批次形状换了该做的事：不是逐份补。

        原来这句是「该查的是那几次跑法，不是逐份补」。2026-08-30 那几次跑法
        **查过了** —— 答案（几乎只缺「建议」）就写在同一句里，再让人去查一遍
        是把已经做完的事又派回去。现在指的是结论所在的那一节。
        """
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._corpus(root)
            msg = _run(AP.check_evaluation_sections, root)[0][2]
        self.assertIn("几乎只缺「建议」那一节", msg)
        self.assertIn("04 的「建议」那一节", msg)

    def test_a_tiny_day_is_not_a_batch(self):
        """两三份说明不了「整批」—— 实测 08-14 就只有 2 份。"""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _mk(root, [_eval("2026-08-11", "值得投", self.SEC) for _ in range(9)]
                + [_eval("2026-08-14", "值得投", ("结论",)) for _ in range(2)])
            msg = _run(AP.check_evaluation_sections, root)[0][2]
        self.assertNotIn("2026-08-14", msg, "2 份被当成了一个批次")

    def test_it_says_so_when_there_is_no_batch_split(self):
        """缺口真的均匀散着时，不许硬凑一句批次话。"""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _mk(root, [_eval("2026-08-11", "值得投",
                             self.SEC if i % 2 else ("结论",)) for i in range(20)])
            msg = _run(AP.check_evaluation_sections, root)[0][2]
        self.assertIn("没有整批全缺", msg)
        self.assertNotIn("是整批漏", msg)

    def test_the_gate_fail_exclusion_survives(self):
        """硬门 FAIL 的深评按 04 本来就该到此为止，不进分母 ——
        把它们算进来，缺小节的比例会凭空翻倍。验行为，不验源码里有没有那个变量名。"""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            ok = [_eval("2026-08-11", "值得投", self.SEC) for _ in range(9)]
            bad = [_eval("2026-08-17", "值得投", ("结论",)) for _ in range(6)]
            fail = [_eval("2026-08-17", "不建议", ("结论",)).replace(
                "## 结论", "不满足硬性条件\n\n## 结论") for _ in range(11)]
            _mk(root, ok + bad + fail)
            msg = _run(AP.check_evaluation_sections, root)[0][2]
        self.assertIn("该写全的 15 份深评里", msg, "硬门 FAIL 的进了分母")
        self.assertIn("另有 11 份硬门 FAIL 的没算", msg)
        # 那一批实际有 17 份（6 份缺小节 + 11 份硬门 FAIL）。批次计数只该
        # 数 6 —— 数成 17 就是把「本来就该短」的文件算成了漏写。
        self.assertIn("1 批（共 6 份）每份都缺了至少一节", msg,
                      "批次计数把硬门 FAIL 的也数了进去")


class TheBackfillTableAndTheAuditAgree(unittest.TestCase):
    """「一次补完 `/job-apply 全部`」对其中一部分是做不到的。

    `job-apply.md` 第 0 步那张补漏表列了三样能只补一节的东西，而只有
    「建议」住在 `evaluation.md`（「内推请托」在话术里，「投前必问」有它自己
    那条检查）。**其余几节缺了只能整份重跑** —— 那张表的 ⚠️ 写得很直白：
    「「职位真伪信号」缺了只能整份重跑（事后补一个「无」等于谎报查过一次）」。

    而「深评缺小节」原来把两种混在一个数里，收尾那句「一次补完」于是对后者
    许了一个做不到的诺。实测 2026-08-31：还能动的 55 份里 44 份只缺「建议」，
    另外 11 份缺的是补不了的那几节。

    这正是 `test_the_command_covers_what_the_sentence_names` 立起来的那条规矩
    （「命令选的那批，包不包含句子指的那批」）—— 它管的是档位那一半，
    这一半是「补得了 vs 补不了」，当时没人管。
    """

    SEC = TheSectionsCheckReportsBatchesNotATrend.SEC

    def test_it_is_a_subset_of_the_six(self):
        self.assertTrue(set(AP.BACKFILLABLE_SECTIONS) <= set(AP.EVAL_SECTIONS),
                        "补得了的那几节得先是六节之一")

    def test_it_matches_the_backfill_table(self):
        """正本是那张表 —— 表里属于 `evaluation.md` 的行就是这几节。"""
        apply_md = (ROOT / "workflows" / "job-apply.md").read_text(
            encoding="utf-8")
        i = apply_md.index("该有而可能没有的，现在是两节")
        table = apply_md[i:apply_md.index("「投前必问」和「建议」", i)]
        # 表里第一列写的就是「名（住在哪）」——`建议（`evaluation.md` 里）`。
        named = {c.split("（")[0].strip()
                 for ln in table.splitlines() if ln.strip().startswith("|")
                 for c in [ln.strip().strip("|").split("|")[0]]
                 if "evaluation.md" in c}
        self.assertTrue(named, "补漏表解析成空了 —— 那下面就是在比两个空集")
        self.assertEqual(
            named - {"投前必问"},                # 它有自己那条检查，不进六节
            set(AP.BACKFILLABLE_SECTIONS),
            "补漏表和 BACKFILLABLE_SECTIONS 对不上 —— "
            "「一次补完」会对补不了的那几份许一个做不到的诺")

    def test_the_two_kinds_get_different_commands(self):
        """只缺「建议」的补一节；缺别的的整份重跑 —— 两句话，两条命令。"""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            only_adv = [_eval("2026-08-11", "值得投",
                              tuple(x for x in self.SEC if x != "建议"))]
            needs_rerun = [_eval("2026-08-11", "值得投",
                                 tuple(x for x in self.SEC
                                       if x not in ("建议", "职位真伪信号")))]
            _mk(root, only_adv * 6 + needs_rerun * 6)
            msg = _run(AP.check_evaluation_sections, root)[0][2]
        self.assertIn("另有", msg)
        self.assertIn("只能整份重跑", msg)

    def test_it_says_nothing_extra_when_they_are_all_backfillable(self):
        """全都只缺「建议」时不该多那半句 —— 一条永远为真的提示是噪音。"""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            only_adv = _eval("2026-08-11", "值得投",
                             tuple(x for x in self.SEC if x != "建议"))
            _mk(root, [only_adv] * 8)
            msg = _run(AP.check_evaluation_sections, root)[0][2]
        self.assertNotIn("只能整份重跑", msg)


if __name__ == "__main__":
    unittest.main()
