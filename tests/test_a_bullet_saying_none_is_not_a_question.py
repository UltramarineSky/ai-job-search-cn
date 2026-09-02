# -*- coding: utf-8 -*-
"""「投前必问」里有 74 条写着「无」，而它们各自占满了所在岗位的整节。

那一档的定义就是「先问清楚关键信息再决定投不投」（`04-job-evaluation.md`）。
面板上 170 个岗的「下一步」写着「这一档要先问清楚再决定投不投」——
展开之后，其中一批看到的是一条写着**「无」**的待问事项。

实测活动用户 2026-08-24：

    「投前必问」条目总数            363
    其中字面是「无」的              **74**（20%）
    整节只有占位、等于什么也没说的岗  **74 / 176**（42%）
    └ 其中判词是「可以考虑」的        **39**

## 写「无」比空着更糟

空着这一节整个不渲染，用户知道没有；写「无」在界面上长得和一条真问题
一模一样，他得读完才发现什么也没说。

## 两头都要修

    导出层   `parse_ask_before` 把「无 / 暂无 / 不适用 / N/A」这类占位滤掉
    审计层   「有标题、写着一条『无』」和「没有这一节」算同一件事

审计那边**不另定「什么算空」** —— 借导出那一侧的正本，否则两份迟早分叉。

## 顺带撞出一个早就存在的矛盾

审计那条把缺失率从 61/130 推到 **100/130（77%）**，当场从「留意」升成「要修」
（它带着一条 ≥50% 的升级）。而同一份文件里
`check_greeting_keeps_the_five_rules` 的「为什么判留意而不是要修」
**逐字点了这条的名**：

> 本仓库的「要修」都配一个机械修法……同族的
> `check_company_claims_have_a_source`、`check_maybe_tier_has_questions`
> 也都是这一级。

两处一直对立，只是 46% 卡在门槛下面没人撞见。这条检查**依然没有 `--apply`**
（改法是重写那份评估），所以解的是矛盾，不是把数字调回门槛以下 ——
判据是 `test_the_backlog_does_not_hide_the_trend` 写下的那句
「一个永远红的审计会被当噪音略过。报出来让人看见，不劫持构建。」
"""
import json
import pathlib
import re
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tests"))
from _live import user_or_skip  # noqa: E402
import audit_pipeline as ap  # noqa: E402
import export_web_data as ex  # noqa: E402

EX = (ROOT / "tools" / "export_web_data.py").read_text(encoding="utf-8")
AUDIT = (ROOT / "tools" / "audit_pipeline.py").read_text(encoding="utf-8")


def flat(s: str) -> str:
    s = " ".join(re.sub(r"^\s*(?:>|#:?)\s?", "", s, flags=re.M).split())
    return re.sub(r"(?<=[一-鿿，。；：、（）「」])"
                  r" +(?=[一-鿿，。；：、（）「」])", "", s)


SEC = "## 投前必问\n"


class ThePlaceholderNeverReachesThePanel(unittest.TestCase):
    def test_a_bare_none_is_dropped(self):
        self.assertEqual(ex.parse_ask_before(SEC + "- 无\n"), [])

    def test_its_common_variants_too(self):
        for w in ("无。", "没有", "暂无", "不适用", "待定", "N/A", "n/a", "—", "-"):
            with self.subTest(w=w):
                self.assertEqual(ex.parse_ask_before(SEC + f"- {w}\n"), [],
                                 f"「{w}」没被当成占位")

    def test_a_real_question_survives(self):
        got = ex.parse_ask_before(SEC + "- 这个岗现在还在招吗？\n")
        self.assertEqual(got, ["这个岗现在还在招吗？"])

    def test_a_question_without_a_mark_survives(self):
        """「研发节奏是怎样的，有没有大小周」是问题，只是没写问号。"""
        got = ex.parse_ask_before(SEC + "- 研发节奏是怎样的，有没有大小周\n")
        self.assertEqual(len(got), 1)

    def test_a_word_starting_with_none_is_not_a_placeholder(self):
        """**判据钉整条，不是「以无开头」。** 「无编制的岗要问清转编通道」
        是一条真问题，滤掉它就把这条检查变成了新的缺陷。"""
        got = ex.parse_ask_before(SEC + "- 无编制的岗要问清有没有转编通道\n")
        self.assertEqual(len(got), 1, f"把一条真问题当占位滤掉了：{got}")

    def test_the_mixed_case_keeps_the_real_ones(self):
        got = ex.parse_ask_before(SEC + "- 无\n- 薪资几薪？\n- 暂无\n")
        self.assertEqual(got, ["薪资几薪？"])

    def test_the_reason_is_recorded(self):
        i = EX.index("_ASK_EMPTY = re.compile(")
        seg = flat(EX[max(0, i - 1100):i])
        self.assertRegex(seg, r"它不是内容，是占位")
        self.assertRegex(seg, r"写「无」比空着更糟")
        self.assertRegex(seg, r"74 条是字面的「无」")
        self.assertIn("2026-08-24", seg)

    def test_it_names_the_tier_that_is_defined_by_this_section(self):
        i = EX.index("_ASK_EMPTY = re.compile(")
        seg = flat(EX[max(0, i - 1100):i])
        self.assertRegex(seg, r"39 个判词是「可以考虑」")


class TheAuditSeesThroughIt(unittest.TestCase):
    #: 判据 2026-08-30 从 `check_maybe_tier_has_questions` 搬进了
    #: `ask_before_missing` —— 写盘时那道闸门（`--sections`）要用同一份。
    #: 下面两条跟着指过去：**钉的是判据只有一份，不是它住在哪个函数里。**
    ANCHOR = "ok = any(a in heads for a in _ASK_HEADS)"

    def test_it_requires_content_not_just_a_heading(self):
        i = AUDIT.index(self.ANCHOR)
        self.assertIn("_ex.parse_ask_before(text)", AUDIT[i:i + 120])

    def test_it_borrows_the_exporter_judgement(self):
        """在这儿另定「什么算空」就是第二份 —— 两份迟早分叉。"""
        i = AUDIT.index(self.ANCHOR)
        seg = flat(AUDIT[max(0, i - 900):i])
        self.assertRegex(seg, r"不在这儿另写一份|「什么算空」走")
        self.assertNotIn("_ASK_EMPTY", AUDIT)

    def test_only_one_place_computes_it(self):
        """全库只许有一处算这件事。"""
        self.assertEqual(AUDIT.count(self.ANCHOR), 1,
                         "「什么算有内容」又长出第二份实现了")

    def test_a_heading_with_only_a_placeholder_counts_as_missing(self):
        """现算：把一份「标题在、只写了无」的评估喂进去，它得算缺。"""
        self.assertEqual(ex.parse_ask_before("## 投前必问\n- 无\n"), [])

    def test_the_reason_is_in_the_docstring(self):
        i = AUDIT.index("def check_maybe_tier_has_questions")
        seg = flat(AUDIT[i:i + 3000])
        self.assertRegex(seg, r"「有标题、写着一条『无』」和「没有这一节」是同一件事")
        self.assertRegex(seg, r"74 个整节只有一条「无」的岗")


class TheContradictionIsResolvedNotDodged(unittest.TestCase):
    """把数字调回门槛以下也能让测试变绿 —— 那是躲，不是修。"""

    def test_this_check_is_always_a_warning(self):
        i = AUDIT.index('"「可以考虑」的深评没写要问什么"')
        head = AUDIT[max(0, i - 200):i]
        self.assertIn('return [("warn"', head)
        self.assertNotIn('else "error"', head)

    def test_the_sibling_that_already_said_so_still_says_it(self):
        """这一条整个建立在那句话上 —— 它没了，改判据就没依据了。"""
        i = AUDIT.index("def check_greeting_keeps_the_five_rules")
        seg = flat(AUDIT[i:i + 2600])
        self.assertRegex(seg, r"本仓库的「要修」都配一个机械修法")
        self.assertIn("check_maybe_tier_has_questions", seg)

    def test_the_resolution_is_explained(self):
        i = AUDIT.index("# **这条一律判「留意」，不按缺失率升 error。**")
        seg = flat(AUDIT[i:i + 1400])
        self.assertRegex(seg, r"两处一直对立，只是缺失率 46% 卡在门槛下面")
        self.assertRegex(seg, r"依然没有机械修法")
        self.assertRegex(seg, r"解的是那个矛盾，不是把数字调回门槛以下")

    def test_the_audit_has_no_errors(self):
        """现算：整套审计仍然零 error（那是 `test_pipeline_audit_stays_clean`
        钉的，这里只是确认这一轮没把它推红）。"""
        import _cli
        seen, details = ap.load(user_or_skip())
        bad = [(t, m[:60]) for fn in [f for _n, f in ap.CHECKS]
               for lvl, t, m in fn(seen, details) if lvl == "error"]
        self.assertEqual(bad, [], f"有 error：{bad}")


class TheSignalItLeansOnIsReal(unittest.TestCase):
    """现算：那批「无」真的在库里，而且真的集中在这一档。"""

    def _evals(self):
        p = ROOT / ".active_user"
        if not p.is_file():
            self.skipTest("没有活动用户")
        apps = (ROOT / "users" / p.read_text(encoding="utf-8").strip()
                / "documents" / "applications")
        if not apps.is_dir():
            self.skipTest("还没有深评")
        out = [f.read_text(encoding="utf-8", errors="replace")
               for f in apps.glob("*/evaluation.md")]
        if len(out) < 50:
            self.skipTest("深评太少")
        return out

    def test_the_raw_files_really_carry_the_placeholder(self):
        """**修好之后这条会 skip。** 那时把这一节的实测数更新掉，别删了它。"""
        n = sum(1 for t in self._evals()
                if re.search(r"^\s*[-*]\s*无\s*[。．.]?\s*$", t, re.M))
        if not n:
            self.skipTest("已经没有写「无」的了 —— 好事")
        self.assertGreater(n, 0)

    def test_the_panel_no_longer_shows_any(self):
        """导出那一层滤掉了 —— 盘上那份快照里一条都不该有。"""
        p = ROOT / "web" / "public" / "data.json"
        if not p.is_file():
            self.skipTest("还没导出过面板数据")
        d = json.loads(p.read_text(encoding="utf-8"))
        bad = [q for j in d["jobs"] for q in (j.get("askBefore") or [])
               if q.strip() in ("无", "无。", "暂无", "没有", "不适用")]
        self.assertEqual(bad, [], f"面板上还有 {len(bad)} 条占位")

    def test_dropping_them_really_moved_the_number(self):
        """这一滤是**真的滤掉了东西**，不是「本来就没有」。

        ## 原来钉的是一个冻在活数据上的字面数

        原文：`assertLess(n, 176)` —— 176 是写这条那天**过滤前**的实测值
        （「从 176 掉到 102，那 74 个此前是假的『有』」）。
        它把一个当天的快照当成了永久上限，而库天天在长。

        实测代价（2026-09-02 发布前）：库里现在 **221** 个岗带这一节，
        判据当场变红，印的却是「还是 221 个 —— **占位没被滤掉？**」。
        过滤器好好的，红的是那个数。**一个数冻在活数据上，冻的那一刻就开始过期。**

        ## 改成两边现算

        原始评估里还有多少条写着「无」（有 → 过滤器有活干），
        面板上还剩多少条（必须是 0）。两个数都现取，库长多大都成立。
        上下两条各自只看一边，这一条看的是**它们的差**——那才是「真的滤掉了」。
        """
        raw = sum(1 for t in self._evals()
                  if re.search(r"^\s*[-*]\s*无\s*[。．.]?\s*$", t, re.M))
        if not raw:
            self.skipTest("原始评估里已经没有写「无」的了 —— 没什么可滤的")
        p = ROOT / "web" / "public" / "data.json"
        if not p.is_file():
            self.skipTest("还没导出过面板数据")
        d = json.loads(p.read_text(encoding="utf-8"))
        left = sum(1 for j in d["jobs"] for q in (j.get("askBefore") or [])
                   if q.strip() in ("无", "无。", "暂无", "没有", "不适用"))
        self.assertEqual(
            left, 0,
            f"原始评估里有 {raw} 条占位，面板上还剩 {left} 条 —— 这一滤没生效")


if __name__ == "__main__":
    unittest.main()
