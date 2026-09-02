# -*- coding: utf-8 -*-
"""「明确排除」判死一个岗，却说不出是哪一条 —— 规格说这就不该判 FAIL。

`04-job-evaluation.md`「明确排除」那一节：

    写不出是哪一条 → **那就不该判 FAIL**。说不清命中了哪条排除，本身就说明
    判据不牢。

规则立着，实测活动用户 2026-08-25：这道门判死 400 个，其中 **299 个的判词就是
光秃秃一句** `硬门 FAIL (候选人明确排除)` / `硬门 FAIL (明确排除)`。

## 这个数一直有人算，只是挂错了地方

`check_which_exclusion_costs_the_most` 末尾那个括号里就是它。但它在那儿的身份是
**统计口径的免责声明**（「上面那几个数是下限」）—— 读的人接收到的是「这张表数不
准」，不是「这几百个岗判错了」。同一个数字，换个位置就换了意思。

同族前科两次：`check_referral_note_is_missing` 的「这个数说的是存量」、
`check_greeting_keeps_the_five_rules` 的「99 份踩线里只有 11 份还发得出去」。
"""
from __future__ import annotations

import importlib
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
ap = importlib.import_module("audit_pipeline")

CHECK = ap.check_an_exclusion_fail_must_name_the_rule


def job(url: str, verdict: str, title: str = "某岗") -> dict:
    return {"url": url, "title": title, "rank_verdict": verdict, "status": "ranked"}


class ABareExclusionFailIsAFinding(unittest.TestCase):

    def test_the_bare_form_is_caught(self):
        seen = {"a": job("u1", "硬门 FAIL (候选人明确排除)")}
        got = CHECK(seen, {})
        self.assertEqual(len(got), 1)
        self.assertIn("1 个岗", got[0][2])

    def test_the_short_bare_form_too(self):
        """实测两种写法都在库里：带「候选人」三个字的 173 个，不带的 126 个。"""
        seen = {"a": job("u1", "硬门 FAIL (明确排除)")}
        self.assertEqual(len(CHECK(seen, {})), 1)

    def test_a_named_one_is_not_a_finding(self):
        seen = {"a": job("u1", "硬门 FAIL (候选人明确排除（跨城搬迁）)")}
        self.assertEqual(CHECK(seen, {}), [])

    def test_other_gates_are_not_this_check_s_business(self):
        """别的门不归这条管 —— 它们没有「说清是哪一条」这个要求。"""
        for v in ("硬门 FAIL (学历院校)", "硬门 FAIL (工作年限)",
                  "硬门 FAIL (外包/驻场/派遣)"):
            with self.subTest(v=v):
                self.assertEqual(CHECK({"a": job("u1", v)}, {}), [])

    def test_a_gateless_fail_is_not_this_check_s_business(self):
        """**光秃秃一句 `硬门 FAIL`、连门名都没有的**，不归这条管。

        变异检验逮到：拿掉「只看这道门」那个筛子时，上面那几条别的门照样绿 ——
        因为 `_exclusion_reason` 从 `(学历院校)` 里取得出「学历院校」，
        不算 bare。真正碰得到那个筛子的是**一个括号都没有**的判词。
        那种归 `check_gate_is_one_of_the_seven`（门名没按七道写）。
        """
        self.assertEqual(CHECK({"a": job("u1", "硬门 FAIL")}, {}), [])

    def test_a_flag_is_not_a_fail(self):
        """**FLAG 不是 FAIL。** 标出来让人投前问一句，岗还在名单上。"""
        self.assertEqual(
            CHECK({"a": job("u1", "硬门 FLAG (候选人明确排除)")}, {}), [])

    def test_the_fail_filter_is_currently_redundant_and_why_it_stays(self):
        """诚实记一笔：判定里那个 `"FAIL" in ...` 现在**杀不掉**。

        拿掉它是一个**等价变异**：`_gate_of_verdict` 只认 FAIL 判词，
        FLAG 在它那儿就返回空串，门名那一层已经把它挡下了。
        **不为了凑一个“变红”去编一条断言** —— 这里钉的是它依赖的前提：
        那个解析器不认 FLAG。哪天它跟着放宽了，这条会红，
        那正是该回头看一眼那个筛子的时候。
        """
        self.assertEqual(ap._gate_of_verdict("硬门 FLAG (候选人明确排除)"), "",
                         "门名解析器开始认 FLAG 了 —— 回头看 `check_an_exclusion_fail_"
                         "must_name_the_rule` 里那个 FAIL 筛子还冗不冗余")
        self.assertEqual(ap._gate_of_verdict("硬门 FAIL (候选人明确排除)"),
                         "候选人明确排除")

    def test_a_pass_is_not_a_finding(self):
        self.assertEqual(CHECK({"a": job("u1", "粗筛：可以考虑")}, {}), [])

    def test_nothing_bare_means_no_message(self):
        seen = {"a": job("u1", "硬门 FAIL (明确排除（英语口语）)"),
                "b": job("u2", "硬门 FAIL (学历院校)")}
        self.assertEqual(CHECK(seen, {}), [])

    # ---------- 能动的那批要认得出来 ----------

    def test_it_splits_out_the_ones_with_a_jd(self):
        """**总数印出来了，能动的那批也要认得出来。**

        这个仓库栽过两次同族的（存量 vs 新增、99 份踩线里只有 11 份还发得出去）。
        有 JD 正文的重判时点得出名，只有标题的那批是另一种处置。
        """
        seen = {"a": job("u1", "硬门 FAIL (明确排除)"),
                "b": job("u2", "硬门 FAIL (明确排除)")}
        got = CHECK(seen, {"u1": {"description": "正文在这儿"}})
        self.assertIn("1 个有 JD 正文", got[0][2])
        self.assertIn("另 1 个", got[0][2])

    def test_the_details_key_is_the_raw_url(self):
        """**`details` 的键是原样 URL，不是规范化过的。**

        用 `norm_url` 去取一个都取不到，而取不到不会报错 —— 只会印出一个
        「0 个有 JD 正文」，看起来像一条结论。第一版正是这么错的（实测当场）。
        """
        url = "https://www.liepin.com/a/1.shtml?utm=x"
        seen = {"a": job(url, "硬门 FAIL (明确排除)")}
        got = CHECK(seen, {url: {"description": "正文"}})
        self.assertIn("1 个有 JD 正文", got[0][2],
                      "键取错了 —— 有正文的那批被算成 0")

    # ---------- 消息本身 ----------

    def test_it_quotes_the_rule_and_where_it_lives(self):
        got = CHECK({"a": job("u1", "硬门 FAIL (明确排除)")}, {})
        self.assertIn("04-job-evaluation.md", got[0][2])
        self.assertIn("不该判 FAIL", got[0][2])

    def test_it_says_why_this_gate_is_special(self):
        """「唯一你今天就能改的」是这条为什么贵的全部理由 —— 少了它就只是个数。"""
        got = CHECK({"a": job("u1", "硬门 FAIL (明确排除)")}, {})
        self.assertIn("唯一你今天就能改的", got[0][2])

    def test_it_gives_exactly_one_command(self):
        got = CHECK({"a": job("u1", "硬门 FAIL (明确排除)")}, {})
        title, msg = got[0][1], got[0][2]
        self.assertEqual((title + msg).count("/job-"), 1)
        self.assertIn("/job-rank --all", msg)

    def test_it_is_registered(self):
        names = [n for n, _ in ap.CHECKS]
        self.assertIn("硬门：判了排除却没说是哪一条", names)


class TheRuleReallySaysThat(unittest.TestCase):
    """**现拿规格原文来对。** 引一条不存在的规则，这个仓库栽过一次
    （「规则真、出处假」，`AGENTS.md` 记着）。"""

    def test_the_spec_line_exists(self):
        t = (ROOT / "workflows" / "reference" / "04-job-evaluation.md").read_text(
            encoding="utf-8")
        self.assertRegex(t, r"写不出是哪一条[^\n]{0,6}→[^\n]{0,10}那就不该判 FAIL")

    def test_the_spec_says_why_this_gate_is_the_changeable_one(self):
        t = (ROOT / "workflows" / "reference" / "04-job-evaluation.md").read_text(
            encoding="utf-8")
        self.assertRegex(t, r"七道里唯一他能改的")


class TheOldPlaceNoLongerExplainsIt(unittest.TestCase):
    """同一个数字不许在两处各讲一遍规则 —— 两处迟早分叉。"""

    def test_the_tally_only_states_the_caveat(self):
        src = (ROOT / "tools" / "audit_pipeline.py").read_text(encoding="utf-8")
        i = src.index("def check_which_exclusion_costs_the_most(")
        body = src[i:src.index("\ndef ", i + 10)]
        code = "\n".join(l for l in body.splitlines()
                         if not l.lstrip().startswith("#"))
        self.assertIn("是下限，不是全貌", code, "口径声明还是要留着")
        self.assertNotIn("不该判 FAIL", code,
                         "规则在这儿又讲了一遍 —— 它归「判了排除却没说是哪一条」那条")


if __name__ == "__main__":
    unittest.main()
