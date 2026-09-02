# -*- coding: utf-8 -*-
"""一个占 20% 权重的分，749/783 个岗没说它是按什么判的 —— 没人能纠正它。

`04-job-evaluation.md`「工作强度与公司性质」那一节把话说死了两句：

> 判完在依据里写清「本次按什么信号判的」—— 口径要能被用户看见和纠正。
>
> 无论用哪套词，**JD 不提就标记未知** —— 不要因为没提就假设是轻松的。

实测活动用户 2026-08-25：

    打过数值强度分的岗                    783
    依据里一个字没提这一维的               749（96%）
    └ 最近一批（2026-08-24，93 个）里       80（86%）

**最后那一行才是要紧的。** 这不是存量：最新一批和全库一样差 —— 也就是说
这条规则在活着的时候就没跑过。存量说明不了规则灵不灵，最近一批说得了。

## 为什么这一维尤其不能靠猜

它占 20% 权重，而那 783 个分里 82% 只落在两个值上（现算：50 和 70）——
一个二值化的默认值。这个仓库自己的尺子是「30 分 × 25% 权重 = 7.5 分，
足以翻一整档」。

更硬的一条：把这 783 个岗对回 `details/` 的 JD 正文，**抓到正文的 604 个里
579 个（96%）通篇没有任何可判的强度信号**，而它们全都拿到了一个数、
**没有一个标「未知」**—— 其中 18 个给了 85 分，那是「这家很轻松」的正面主张。

⚠️ 那次比对用的词是按**这个用户的强度形态**取的（04 三档里的「按项目/版本
推进」：加班节奏、周末制度）。换个形态的岗位那份词一个都不会出现 ——
所以那 579 是**这一次的旁证**，不是这条检查的判据。

## 判据只问一句：依据里提没提这一维

不去猜哪些词算信号。04 自己写着，写死一份词表就是把某一个行业的黑话当成
通用尺子：「换成按班次运转的岗位，JD 里一个都不会出现，于是这一维（占 20%
权重）**静默地全部标成未知**——不是没信息，是拿错了尺子」。

这里只查那一维的**名字**出没出现在依据里 —— 提了才有得纠正，这正是 04 那句
「口径要能被用户看见和纠正」的最小可查形式。
"""
import pathlib
import re
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import _cli  # noqa: E402
import audit_pipeline as ap  # noqa: E402

AUDIT = (ROOT / "tools" / "audit_pipeline.py").read_text(encoding="utf-8")
FRAME = (ROOT / "workflows" / "reference"
         / "04-job-evaluation.md").read_text(encoding="utf-8")


def flat(s: str) -> str:
    s = " ".join(re.sub(r"^\s*(?:>|#:?)\s?", "", s, flags=re.M).split())
    return re.sub(r"(?<=[一-鿿，。；：、（）「」])"
                  r" +(?=[一-鿿，。；：、（）「」])", "", s)


def body() -> str:
    """这个函数**到下一个 def 为止**，不是到 `CHECKS = [` 为止。

    切到 `CHECKS` 的话，下一个人在它后面加一条检查，这一段就把别人的函数也
    圈进来 —— 隔壁那份守卫刚这么红过一次（它切到了 `CHECKS`，而这条检查
    正好加在它后面）。
    """
    i = AUDIT.index("def check_intensity_score_has_a_basis")
    nxt = AUDIT.find("\n\n\ndef ", i)
    end = AUDIT.index("\nCHECKS = [", i)
    return AUDIT[i:min(nxt, end) if nxt > 0 else end]


def code() -> str:
    """只要**代码**那一段，不要 docstring。

    docstring 里记着一次性的实测 —— 含那份按他强度形态取的词（加班、周末……）
    和当时的百分比。那是该留的账；而「不许造词表」「不许写死百分比」判的是
    **代码**。两者混着判，会把记账当成犯规（写这条时当场撞了两次）。
    """
    b = body()
    return b.split('"""', 2)[2] if b.count('"""') >= 2 else b


class TheRuleItEnforcesIsReal(unittest.TestCase):
    def test_the_basis_sentence_is_required(self):
        self.assertRegex(
            flat(FRAME),
            r"判完在依据里写清「本次按什么信号判的」——口径要能被用户看见和纠正")

    def test_unstated_means_unknown(self):
        self.assertRegex(
            flat(FRAME),
            r"无论用哪套词，\*\*JD 不提就标记未知\*\* —— 不要因为没提就假设是轻松的")

    def test_the_word_list_warning_is_still_there(self):
        """这条检查**不**自己造词表，靠的就是这段警告。"""
        self.assertRegex(flat(FRAME), r"那是\*\*某一个行业的\s*黑话\*\*")
        self.assertRegex(flat(FRAME), r"不是没信息，是拿错了尺子")

    def test_the_dimension_is_weighted(self):
        """20% 是这一条全部的分量 —— 它要是一维小权重，猜错也就算了。"""
        self.assertIn("- 强度与公司性质：20%", FRAME)
        self.assertIn("强度与公司性质 20 / 发展与风险 25", FRAME.replace("**", ""))


class TheCheckAsksOnlyOneThing(unittest.TestCase):
    def test_it_is_registered(self):
        self.assertIn(ap.check_intensity_score_has_a_basis,
                      [fn for _n, fn in ap.CHECKS])

    def test_it_only_looks_for_the_dimension_name(self):
        """造一份词表就是重犯 04 点名的那个错。"""
        self.assertIn("_INTENSITY_KEYS", body())
        for w in ("加班", "大小周", "996", "双休", "排班", "夜班"):
            with self.subTest(w=w):
                self.assertNotIn(w, code(), f"代码里出现了「{w}」—— 那就是一份词表")

    def test_it_says_why_it_refuses_a_word_list(self):
        b = flat(body())
        self.assertRegex(b, r"\*\*不去猜哪些词算信号。\*\*")
        self.assertRegex(b, r"写死一份词表就是把某一个行业的黑话\s*当成通用尺子")

    def test_it_only_counts_numeric_scores(self):
        """硬门 FAIL 的岗四维全是「不适用」—— 那不是漏写依据。"""
        self.assertIn("isinstance(b[k], (int, float))", body())

    def test_a_scored_job_without_the_word_is_caught(self):
        got = ap.check_intensity_score_has_a_basis(
            {"a": {"rank_breakdown": {"强度与公司性质": 70, "依据": "技能对口"}}}, {})
        self.assertEqual(len(got), 1)
        self.assertIn("1/1", got[0][2])

    def test_a_scored_job_that_names_it_is_clean(self):
        got = ap.check_intensity_score_has_a_basis(
            {"a": {"rank_breakdown": {"强度与公司性质": 70,
                                      "依据": "强度：JD 未提作息，按未知处理"}}}, {})
        self.assertEqual(got, [])

    def test_a_gate_fail_job_is_not_counted(self):
        """「不适用」不是数，不进这个分母。"""
        got = ap.check_intensity_score_has_a_basis(
            {"a": {"rank_breakdown": {"强度与公司性质": "不适用", "依据": "硬门 FAIL"}}}, {})
        self.assertEqual(got, [])


class TheNumbersAreComputedNotHardcoded(unittest.TestCase):
    def test_the_concentration_is_live(self):
        """写死一个百分比就等着它过期。"""
        self.assertIn("vals.most_common(2)", code())
        self.assertNotIn("83%", code())
        self.assertNotIn("82%", code())

    def test_it_says_why_it_is_live(self):
        self.assertRegex(flat(body()), r"\*\*现算\*\*，不写死一个数")

    def test_the_concentration_line_disappears_when_meaningless(self):
        """只有两三个取值时，「82% 落在两个值上」是句废话。"""
        self.assertIn("if len(vals) > 2 else", body())

    def test_the_latest_batch_is_reported(self):
        """存量说明不了规则灵不灵 —— 这个仓库的既有写法。"""
        b = flat(body())
        self.assertRegex(b, r"这个数才说得了规则灵不灵，全库那个只会随产量涨")

    def test_the_sibling_that_set_that_pattern_still_says_it(self):
        i = AUDIT.index("def check_documents_speak_chinese_to_the_user")
        self.assertRegex(flat(AUDIT[i:i + 4000]), r"最近一批")


class TheFixSplitsByHowItWasScored(unittest.TestCase):
    """`--all` 改不到深评 —— 这个仓库刚为同一件事付过学费。"""

    def test_it_splits(self):
        b = body()
        self.assertIn("miss_coarse", b)
        self.assertIn("miss_deep", b)
        self.assertIn('e.get("evaluated")', b)

    def test_the_coarse_half_gets_all(self):
        self.assertRegex(flat(body()), r"粗筛的 \{len\(miss_coarse\)\} 个跑 /job-rank --all")

    def test_the_deep_half_gets_apply(self):
        b = flat(body())
        self.assertRegex(b, r"深评过的 \{len\(miss_deep\)\} 个逐个跑 /job-apply <职位链接>")
        self.assertRegex(b, r"--all 改不到深评")

    def test_that_lesson_is_still_recorded_elsewhere(self):
        """引的是同一份文件里那条已经修好的 —— 它没了这里就成了孤证。"""
        self.assertRegex(flat(AUDIT), r"逐个重跑 /job-apply <职位链接> 改这几份深评")

    def test_an_empty_half_is_not_printed(self):
        """一半为空时不该印「深评过的 0 个」。"""
        self.assertIn("if miss_coarse:", body())
        self.assertIn("if miss_deep:", body())


class TheMessageIsFitForTheTerminal(unittest.TestCase):
    def test_no_markdown(self):
        i = body().index('return [("warn"')
        self.assertNotIn("**", body()[i:])

    def test_it_is_a_warning(self):
        b = body()
        self.assertIn('return [("warn", "强度那一维给了分，却没说按什么判的"', b)
        self.assertNotIn('"error"', b)

    def test_it_quotes_the_rule_verbatim(self):
        b = body()
        self.assertIn("判完在依据里写清『本次按什么信号判的』", b)
        self.assertIn("JD 不提就标记未知", b)


class TheSignalItLeansOnIsReal(unittest.TestCase):
    """现算：这条真的在响，而且最近一批真的没变好。"""

    def _got(self):
        p = ROOT / ".active_user"
        if not p.is_file():
            self.skipTest("没有活动用户")
        seen, details = ap.load(_cli.pick_user("", root=ROOT))
        return seen, ap.check_intensity_score_has_a_basis(seen, details)

    def test_it_fires_today(self):
        """**修完之后这条会 skip。** 那时把上面的实测数更新掉，别删了它。"""
        _seen, got = self._got()
        if not got:
            self.skipTest("都写上依据了 —— 好事")
        self.assertEqual(got[0][0], "warn")

    def test_the_denominator_is_not_tiny(self):
        """**支点。** 只有十几个打过分时，这一节说不出话来。"""
        seen, got = self._got()
        if not got:
            self.skipTest("都写上依据了")
        n = int(re.search(r"\d+/(\d+) 个", got[0][2]).group(1))
        self.assertGreater(n, 100, f"只有 {n} 个打过强度分 —— 这一节的论点要重看")

    def test_the_docstring_agrees_with_the_latest_batch(self):
        """**说明里那句判断，要和最近一批的实况对得上。**

        原来这一条写的是「最近一批必须一样差，好转了就要改说明」——
        它把一个**会变的事实**钉成了不变量。2026-08-25 最近一批变成 0/3
        （那天的深评逐份写了依据），这条当场红了，而红的原因是**事情变好了**。

        好转本身不该让测试红。该红的是**说明没跟着改**。所以判据换成对账：
        消息里报的最近一批比例，和说明里那句话说的是不是同一件事。
        """
        _seen, got = self._got()
        if not got:
            self.skipTest("都写上依据了")
        m = re.search(r"最近一批（(20[\d-]+)，(\d+) 个）里 (\d+) 个", got[0][2])
        if not m:
            self.skipTest("读不出最近一批")
        tot, bad = int(m.group(2)), int(m.group(3))
        doc = flat(ap.check_intensity_score_has_a_basis.__doc__ or "")
        if bad > tot * 0.5:
            self.assertIn("和全库一样差", doc,
                          f"最近一批 {bad}/{tot} 仍然一样差，而说明里已经不这么说了")
        else:
            self.assertIn("翻过来了", doc,
                          f"最近一批 {bad}/{tot} —— 好转了，而说明里还写着一样差")

    def test_the_small_sample_is_flagged_as_one(self):
        """3/3 只够说「不再一样差」，不够宣布规则站住了 —— 那句话要写出来。"""
        doc = flat(ap.check_intensity_score_has_a_basis.__doc__ or "")
        if "翻过来了" not in doc:
            self.skipTest("最近一批还没好转")
        self.assertIn("不足以宣布规则站住了", doc)

    def test_the_check_and_a_hand_count_agree(self):
        """独立数一遍对账 —— 匹配器断掉时它会静默地什么都不报。"""
        seen, got = self._got()
        if not got:
            self.skipTest("都写上依据了")
        mine = 0
        for e in seen.values():
            if not isinstance(e, dict):
                continue
            b = e.get("rank_breakdown") or {}
            if not isinstance(b, dict):
                continue
            k = next((k for k in b if "强度" in str(k)), None)
            if k and isinstance(b[k], (int, float)):
                mine += 1
        n = int(re.search(r"\d+/(\d+) 个", got[0][2]).group(1))
        self.assertEqual(n, mine, "报出来的分母和独立数的对不上")

    def test_the_whole_audit_still_has_no_errors(self):
        seen, _got = self._got()
        user = _cli.pick_user("", root=ROOT)
        ap._USER[:] = [user]
        _s, details = ap.load(user)
        bad = [(k, m[:50]) for _n, fn in ap.CHECKS
               for lvl, k, m in fn(seen, details) if lvl == "error"]
        self.assertEqual(bad, [], f"有 error：{bad}")


if __name__ == "__main__":
    unittest.main()
