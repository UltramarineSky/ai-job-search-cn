# -*- coding: utf-8 -*-
"""说「JD 没要求 X」，那就得先有那份 JD。

2026-08-30 用浏览器补一个 77 分岗的 JD 时当场撞见：它的硬性条件表里写着

    候选人明确排除 | PASS | 国际化产品但书面英语可用；JD 未要求口语工作语言

而 JD 补进来之后，任职要求第 9 条原文是「英文能力良好，能**支持海外客户沟通**、
全球市场调研和跨区域协作」，平台语言栏还写着「英语、普通话」。
**那句断言是在没有 JD 的情况下写的**，而它恰好放行了一道本该亮黄灯的门。

## 否定断言为什么特别危险

肯定句写错了，读者对着 JD 一眼能看出来；**否定句写错了看不出来** ——
「JD 未要求学历」和「我没查过学历」在纸面上长得一模一样，而前者会让七道门里的
一道直接 PASS。这是本仓库反复记的那一类：**「没查」和「查过没有」是两件事**。

实测：84 份深评里 267 条这样的断言，而那些岗的 JD 正文库里一份都没有；
另有 197 份有 JD 撑着（583 条同类断言），那些不算 —— **有据可查的占多数，
所以这条不是在骂写手，是在指出那 84 份缺的是证据不是态度。**
"""
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tests"))
from _live import user_or_skip  # noqa: E402
import audit_pipeline as ap  # noqa: E402

NAME = "JD：说「没要求 X」而 JD 不在库里"


class ThePatternCatchesTheRealSpellings(unittest.TestCase):
    HIT = ("JD 未要求口语工作语言", "JD 未设学历门槛", "JD 没提年限",
           "JD 未写年限下限", "JD 未列专业清单", "JD 不限专业")

    MISS = ("JD 要求硕士及以上", "JD 写着「5 年以上」", "他没读过 JD",
            "任职要求段未展示")

    def test_it_catches_the_negative_forms(self):
        for s in self.HIT:
            with self.subTest(s=s):
                self.assertTrue(ap._NEGATIVE_CLAIM.search(s), s)

    def test_it_leaves_positive_claims_alone(self):
        """肯定句不进这条 —— 它们错了读者对着 JD 看得出来。"""
        for s in self.MISS:
            with self.subTest(s=s):
                self.assertFalse(ap._NEGATIVE_CLAIM.search(s), s)


class TheCheckIsRegisteredAndHonest(unittest.TestCase):
    def test_it_is_registered(self):
        self.assertIn(NAME, [n for n, _fn in ap.CHECKS])

    def test_it_says_why_negatives_are_worse(self):
        doc = ap.check_a_negative_claim_needs_the_jd.__doc__ or ""
        self.assertIn("否定句", doc)
        self.assertIn("没查", doc)

    def test_the_fix_is_not_deleting_the_sentence(self):
        """删掉那句话只会让门变成「没判」—— 修法是把 JD 补回来。"""
        doc = ap.check_a_negative_claim_needs_the_jd.__doc__ or ""
        self.assertIn("删了", doc)
        self.assertIn("补回来", doc)

    def test_it_reports_the_ones_that_are_fine_too(self):
        """有 JD 撑着的那批要一起报 —— 不然这条读起来像在指控所有人。"""
        seen, details = ap.load(user_or_skip())
        ap._USER[:] = [user_or_skip()]
        out = ap.check_a_negative_claim_needs_the_jd(seen, details)
        if not out:
            self.skipTest("这一档已经清空了 —— 好事")
        self.assertIn("那些不算", out[0][2])
        self.assertNotIn("**", out[0][2])


if __name__ == "__main__":
    unittest.main()
