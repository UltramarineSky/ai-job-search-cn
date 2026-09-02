# -*- coding: utf-8 -*-
"""「资料和简历里都没有的词」那个分支，结构上永远渲染不出来。

面板「简历要补什么」那一栏分两档，`ResumeRead.tsx` 里写着：

    notWritten = asks.filter(a => a.inResume === false && a.inProfile)
    notHad     = asks.filter(a => a.inResume === false && a.inProfile === false)

第二档配着一段很讲究的告诫（「别直接写进简历，资料里没有就是真没有」，
出处是 `03-writing-style.md` 铁律 3）。**而它一次都没有渲染过，也不可能渲染。**

原因在词源：`asks` 的循环源是 `profile_terms(user)` —— 从 `candidate.md` 的
「技能」一节抽的词；而 `inProfile` 查的是 `profile_text(user)` —— **同一个文件的
全文**。抽出来的词必然是全文的子串，所以 `inProfile` 恒为真。
实测 2026-08-24 导出的 7 条 asks，`inProfile` 非 true 的有 0 条。

## 词源只有一个，就问不出「我不知道的词」

`profile_terms` 的说明自己写着这一半做不到：

> **不能**：市场反复要、而你不会也没写的（真缺口）。那需要中文分词才能从 JD 里
> 反向抽词，而本仓库零依赖。

那句话对**中文散文**成立，对**职位名里的英文词不成立**。`FDE`、`AIGC`、`SaaS`、
`ICU`、`IPO` 这类切出来不需要任何分词，一个正则就够 —— 而它们恰恰是国内招聘里
最要紧的一类词：**HR 在简历库里搜人，打的就是职位名。**

## 实测（活动用户 2026-08-24，107 个行业对口的岗）

    ai      68 个标题（64%）   简历里有
    agent   19 个标题（18%）   简历里有
    fde     10 个标题（ 9%）   **资料里有、简历里没有**

第三个就是这一层报出来的东西。他已经投过 4 个标题带 FDE 的岗 —— 自己知道这个词，
只是 HR 会读到的那份文件上没有。

门槛 5%（在这份语料上是 5 个标题）是量出来的：过门槛的正好这三个；紧挨着门槛
下面是 `engineer` 3、`harness` 3；再往下会带出 manager / product / pm / base /
leader —— 双语职位名里的通用填充词。**噪音一进来这一栏就会被整个忽略。**
"""
import json
import pathlib
import re
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import _cli  # noqa: E402
import export_web_data as ex  # noqa: E402

RREAD = (ROOT / "web" / "src" / "components"
         / "ResumeRead.tsx").read_text(encoding="utf-8")
TYPES = (ROOT / "web" / "src" / "types.ts").read_text(encoding="utf-8")
EXPORT = (ROOT / "tools" / "export_web_data.py").read_text(encoding="utf-8")


def flat(s: str) -> str:
    s = " ".join(re.sub(r"^\s*#:?\s?", "", s, flags=re.M).split())
    return re.sub(r"(?<=[一-鿿，。；：、（）「」])"
                  r" +(?=[一-鿿，。；：、（）「」])", "", s)


class TitleTermsNeedsNoSegmentation(unittest.TestCase):
    def test_it_picks_an_acronym_out_of_titles(self):
        sweet = [{"title": f"AI FDE 产品经理 {i}"} for i in range(20)]
        got = dict(ex.title_terms(sweet))
        self.assertEqual(got.get("fde"), 20)
        self.assertEqual(got.get("ai"), 20)

    def test_it_works_on_a_non_tech_corpus(self):
        """工具行业无关 —— 护士的 ICU、律师的 IPO 同样切得出来。"""
        sweet = [{"title": f"ICU 主管护师（{i}）"} for i in range(20)]
        self.assertIn("icu", dict(ex.title_terms(sweet)))

    def test_a_rare_word_does_not_pass(self):
        sweet = [{"title": "AI 产品经理"} for _ in range(40)]
        sweet.append({"title": "AI PM harness 岗"})
        got = dict(ex.title_terms(sweet))
        self.assertIn("ai", got)
        self.assertNotIn("harness", got, "1/41 也过了门槛 —— 这一栏会被噪音淹掉")

    def test_the_floor_scales_with_the_corpus(self):
        i = EXPORT.index("_TITLE_SHARE = ")
        self.assertIn("floor = max(3, int(len(sweet) * _TITLE_SHARE))", EXPORT,
                      "门槛写成了固定次数 —— 语料一大就全是通用词")
        del i

    def test_a_tiny_corpus_reports_nothing(self):
        """三五个岗算不出「市场在用的叫法」，宁可不说。"""
        self.assertEqual(ex.title_terms([{"title": "AI FDE"}] * 2), [])
        self.assertEqual(ex.title_terms([]), [])

    def test_it_counts_jobs_not_occurrences(self):
        """一个标题里写两遍不算两个岗。"""
        sweet = [{"title": "AI AI AI 产品经理"} for _ in range(20)]
        self.assertEqual(dict(ex.title_terms(sweet)).get("ai"), 20)

    def test_it_is_case_insensitive(self):
        sweet = ([{"title": "FDE 工程师"}] * 10) + ([{"title": "fde 专家"}] * 10)
        self.assertEqual(dict(ex.title_terms(sweet)).get("fde"), 20)

    def test_a_missing_title_does_not_crash(self):
        self.assertEqual(ex.title_terms([{}, {"title": None}]), [])


class TheDeadBranchIsNowReachable(unittest.TestCase):
    """这才是这次改动的正事：让那个分支**有可能**渲染。"""

    def test_the_panel_branch_still_exists(self):
        self.assertIn("a.inResume === false && a.inProfile === false", RREAD)
        self.assertIn("别直接写进简历", RREAD)

    def test_a_title_term_can_be_absent_from_the_profile(self):
        """构造一遍：市场标题里有、而资料和简历里都没有的词，要走得到那一档。"""
        rows = []
        for term, n in ex.title_terms([{"title": "AI FDE 岗"}] * 20):
            rows.append({"term": term, "n": n, "of": 20, "where": "标题",
                         "inResume": "fde" in "我会 ai",
                         "inProfile": "fde" in "我会 ai"})
        hard = [r for r in rows if r["inResume"] is False
                and r["inProfile"] is False]
        self.assertTrue(hard, "标题词也进不了那一档，那个分支还是死的")
        self.assertIn("fde", [r["term"] for r in hard])

    def test_the_export_really_adds_the_second_source(self):
        i = EXPORT.index("_have = {a[\"term\"].lower() for a in asks}")
        seg = EXPORT[i:i + 700]
        self.assertIn("for term, n in title_terms(sweet):", seg)
        self.assertIn('"where": "标题"', seg)

    def test_it_does_not_double_count_a_term_from_both_sources(self):
        i = EXPORT.index("for term, n in title_terms(sweet):")
        self.assertIn("if term in _have:", EXPORT[i:i + 200],
                      "同一个词会在列表里出现两次")

    def test_the_body_rows_are_tagged_too(self):
        """只给新的那批打标，旧的那批 `where` 缺失，界面就得处处判 undefined。"""
        self.assertIn('a["where"] = "正文"', EXPORT)


class TheTwoSourcesReadDifferently(unittest.TestCase):
    def test_the_panel_says_which_is_which(self):
        self.assertIn("function askNote(", RREAD)
        self.assertIn("HR 搜人打的是这个词", RREAD)
        self.assertIn("个行业对口的岗要", RREAD)

    def test_the_reason_is_written_down(self):
        i = RREAD.index("function askNote(")
        seg = flat(RREAD[max(0, i - 700):i])
        self.assertRegex(seg, r"\*\*两个词源说的不是同一件事\*\*")
        self.assertRegex(seg, r"后者是「被搜到」那条路上的事")

    def test_the_type_carries_it(self):
        self.assertIn('where?: "正文" | "标题";', TYPES)

    def test_the_type_says_why_two_sources_exist(self):
        i = TYPES.index('where?: "正文" | "标题";')
        seg = flat(TYPES[max(0, i - 700):i])
        self.assertRegex(seg, r"`inProfile` 恒为真")


class TheMeasurementIsRecorded(unittest.TestCase):
    def _seg(self) -> str:
        i = EXPORT.index("def title_terms(")
        return flat(EXPORT[i - 900:EXPORT.index("    if not sweet:", i)])

    def test_it_says_what_the_old_docstring_got_wrong(self):
        seg = self._seg()
        self.assertRegex(seg, r"那句话对\*\*中文散文\*\*成立，对\*\*职位名里的英文词不成立\*\*")

    def test_it_names_the_dead_branch(self):
        seg = self._seg()
        self.assertRegex(seg, r"`inProfile` \*\*恒为真\*\*")
        self.assertRegex(seg, r"在结构上永远不会渲染")

    def test_it_carries_the_three_rows(self):
        seg = self._seg()
        for row in (r"ai\s+68 个标题（64%）", r"agent\s+19 个标题（18%）",
                    r"fde\s+10 个标题（ ?9%）"):
            with self.subTest(row=row):
                self.assertRegex(seg, row)

    def test_the_threshold_shows_what_is_just_below_it(self):
        """只写「5% 是量出来的」等于没写 —— 要给出门槛下面那几个长什么样。"""
        seg = self._seg()
        self.assertRegex(seg, r"`engineer` 3、`harness` 3")
        self.assertRegex(seg, r"通用填充词")

    def test_it_admits_the_limit(self):
        seg = self._seg()
        self.assertRegex(seg, r"只切英文")
        self.assertRegex(seg, r"仍然归 `/job-upskill`")

    def test_it_carries_the_date(self):
        self.assertIn("2026-08-24", self._seg())


class TheSignalItLeansOnIsReal(unittest.TestCase):
    def _sweet(self):
        p = ROOT / ".active_user"
        if not p.is_file():
            self.skipTest("没有活动用户")
        u = p.read_text(encoding="utf-8").strip()
        f = ROOT / "users" / u / "job_scraper" / "seen_jobs.json"
        if not f.is_file():
            self.skipTest("没有职位库")
        seen = _cli.seen_of(json.loads(f.read_text(encoding="utf-8")))
        sweet = [e for e in seen.values()
                 if (ex._read_pair(e) or (0, 0))[1] >= ex.SWEET_SPOT_DOMAIN]
        if len(sweet) < 30:
            self.skipTest("行业对口的岗太少")
        return sweet

    def test_the_threshold_keeps_the_list_short(self):
        """这一栏的价值全在「短」。长了就没人看。"""
        got = ex.title_terms(self._sweet())
        self.assertLessEqual(len(got), 8,
                             f"过门槛的有 {len(got)} 个 —— 门槛该重新量了："
                             f"{[t for t, _ in got]}")

    def test_it_finds_at_least_one_term_the_resume_lacks(self):
        p = ROOT / ".active_user"
        u = p.read_text(encoding="utf-8").strip() if p.is_file() else ""
        cv = ROOT / "users" / u / "resume" / "main.typ"
        if not cv.is_file():
            self.skipTest("读不到主简历")
        rt = ex._norm(cv.read_text(encoding="utf-8", errors="replace"))
        got = ex.title_terms(self._sweet())
        if not got:
            self.skipTest("这份语料里没有过门槛的词")
        miss = [t for t, _n in got if ex._norm(t) not in rt]
        if not miss:
            self.skipTest("市场在用的叫法简历里都有了 —— 那这一栏这轮没话说，正常")
        # 跳过条件只保证「现算出来简历缺这几个词」。该断言的是**导出的那份也
        # 这么认** —— 两处 `_norm` 走岔了，面板上就会把缺的说成有，
        # 而那一栏的全部意义就是告诉他缺什么。（判据见 `test_no_assertion_is_dead_on_arrival.py` 第 6 种）
        d = ROOT / "web" / "public" / "data.json"
        if not d.is_file():
            self.skipTest("还没导出过面板数据")
        blob = json.loads(d.read_text(encoding="utf-8"))
        rows = {a.get("term"): a for a
                in (((blob.get("resumeInsight") or {}).get("sweetSpot") or {})
                    .get("asks") or [])
                if a.get("where") == "标题"}
        for term in miss:
            if term not in rows:
                continue          # 导出是快照，语料变过就可能还没有这一行
            with self.subTest(term=term):
                self.assertIs(
                    rows[term].get("inResume"), False,
                    f"现算说简历里没有「{term}」，面板上却写着有")


class TheOlderRulesSurvive(unittest.TestCase):
    def test_profile_terms_still_reads_the_users_own_words(self):
        """不许退回硬编码词表 —— 那是把一个人的样本当成所有人的规则。"""
        self.assertIn("从**候选人自己的资料**里抽技能词", EXPORT)
        self.assertIn(r'r"^#{1,6}\s*技能\s*$', EXPORT)

    def test_the_never_invent_rule_is_still_on_screen(self):
        self.assertIn("资料里没有就是真没有", RREAD)

    def test_the_null_means_not_compared_rule_survives(self):
        self.assertIn("None if rt is None else needle in rt", EXPORT)
        self.assertIn("None if pt is None else needle in pt", EXPORT)


if __name__ == "__main__":
    unittest.main()
