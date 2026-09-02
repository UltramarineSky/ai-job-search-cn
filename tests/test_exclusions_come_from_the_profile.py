# -*- coding: utf-8 -*-
"""「候选人明确排除」这道门只认资料里明写过的条款。

七道硬门里，其余六道的判据在 JD 那边（学历、年限、户口、应届、外包、执业资格）。
这一道不一样：**判据全在用户自己的资料里**。所以它有一条别的门没有的约束 ——
资料里没有的条款，不许拿来当门。

实测活动用户 2026-08-22，415 个「明确排除」FAIL 里，理由那一格写着
**事业部经营管理 / 人力资源 / 企业信息化 / 四大 / 日语** —— 这五个词在他整份
资料里一次都没出现过。那不是排除，是评估在用一票否决表达「我觉得这岗不合适」，
代价是**分数抹零、岗位从此不再出现**。

而这份资料里已经记了两次同类事故，**两次都是用户自己发现的**：英语那条原来只写
「无法口语沟通」，执行时被当成「凡沾英语一律排除」；专业清单「2026-08-14 上午曾
按硬门写在这里，同日本人放宽为减分」。**一个只有用户自己能发现的错误，
就是一个迟早不会被发现的错误。**
"""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import audit_pipeline as A  # noqa: E402

RANK = (ROOT / "workflows" / "job-rank.md").read_text(encoding="utf-8")

PROFILE = """### 明确排除
- 外包、驻场、劳务派遣
- 大小周

#### 明确的能力边界（硬缺口）
- **不写代码**，不具备独立编码能力
- **英语只限书面**：口语不行
"""


class TheRuleIsWrittenDown(unittest.TestCase):
    def test_a_gate_needs_a_clause_in_the_profile(self):
        self.assertRegex(RANK, r"资料里没有的条款，不许拿来当门",
                         "job-rank 里没写「资料里没有的条款不许当门」")

    def test_the_alternative_is_a_deduction_not_a_gate(self):
        """JD 有要求、资料里没有 → 扣分或问用户，不是杀掉。"""
        self.assertRegex(RANK, r"不是硬门.*扣分|按业务域/技能维\*\*扣分\*\*",
                         "没说清「不是硬门时该怎么办」")


class TheAuditCatchesIt(unittest.TestCase):
    @staticmethod
    def _run(rows, profile=PROFILE):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            prof = root / "users" / "张三" / "profile"
            prof.mkdir(parents=True)
            (prof / "candidate.md").write_text(profile, encoding="utf-8")
            saved = A.ROOT, list(A._USER)
            try:
                A.ROOT, A._USER[:] = root, ["张三"]
                return A.check_exclusions_trace_to_the_profile(
                    {str(i): r for i, r in enumerate(rows)}, {})
            finally:
                A.ROOT, A._USER[:] = saved[0], saved[1]

    @staticmethod
    def _fail(reason=""):
        v = f"硬门 FAIL (明确排除（{reason}）)" if reason else "硬门 FAIL (明确排除)"
        return {"rank_verdict": v, "title": "某岗"}

    def test_a_reason_with_no_clause_is_an_error(self):
        out = self._run([self._fail("日语")])
        self.assertTrue(any(l == "error" for l, _, _ in out), f"没报：{out}")
        self.assertIn("日语", out[-1][2])

    def test_a_reason_that_traces_is_fine(self):
        """措辞不必逐字照抄——「英语口语」对上「口语不行」就算有出处。"""
        out = self._run([self._fail("英语口语")])
        self.assertFalse(any(l == "error" for l, _, _ in out), f"误报了：{out}")

    def test_each_half_of_a_compound_reason_is_checked(self):
        """「独立编码 + 日语」：前半有出处、后半没有，要报后半。

        整串比对会把这条整个放过去 —— 那正是最容易漏的形状。
        """
        out = self._run([self._fail("独立编码 + 日语")])
        self.assertTrue(any("日语" in d for _, _, d in out), f"复合理由没拆开查：{out}")

    def test_the_nested_parens_are_parsed(self):
        """存的是两层括号 `(明确排除（日语）)`。配错的话所有理由都读成空。"""
        self.assertEqual(A._exclusion_reason(self._fail("日语")), "日语")
        self.assertEqual(A._exclusion_reason(self._fail()), "")

    def test_blank_reasons_are_reported_by_the_other_check(self):
        """**这一半 2026-08-25 搬家了。**

        这个函数按它自己的名字只管「理由在资料里找不找得到出处」；
        「压根没写理由」归 `check_an_exclusion_fail_must_name_the_rule` ——
        那里才有规格原句、能动的那批、以及该敲的命令。
        搬家前同一个数字挂在三处，而三处的说法已经不一样了。

        这条留着不删：它钉的是**这件事仍然有人报**，只是不在这儿。
        """
        rows = [self._fail(), self._fail(), self._fail("英语口语")]
        out = self._run(rows)
        self.assertFalse(any("没说是哪一条" in k for _, k, _ in out),
                         f"副报告又回来了：{out}")
        other = A.check_an_exclusion_fail_must_name_the_rule(
            {str(i): r for i, r in enumerate(rows)}, {})
        self.assertTrue(any("没说是哪一条" in k for _, k, _ in other),
                        f"搬过去之后两头都没人报：{other}")

    def test_an_unreadable_profile_says_it_did_not_check(self):
        out = self._run([self._fail("日语")], profile="（空）")
        self.assertTrue(any("没查" in k + d for _, k, d in out),
                        f"读不出资料却没说没查：{out}")

    def test_it_is_registered(self):
        self.assertTrue(
            any(getattr(fn, "__name__", "") == "check_exclusions_trace_to_the_profile"
                for _, fn in A.CHECKS), "新检查没进 CHECKS")


if __name__ == "__main__":
    unittest.main()
