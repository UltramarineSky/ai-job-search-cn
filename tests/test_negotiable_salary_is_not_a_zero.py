# -*- coding: utf-8 -*-
"""「薪资面议这一维不打分」写在框架里，而没有任何东西验它。

`04-job-evaluation.md` 规定得很死：

> **薪资面议**：`salary` 为「薪资面议」时，这一维**不打分**，标记为「信息缺失」
> ——面议本身是个信号，意味着薪资弹性大或不愿公开。

同一份文档还算过这笔账：薪资维不计入、权重重分配 → 总分 **76**；照打 → **63**。

**规则写了，没有东西验它。** 实测活动用户 2026-08-23：平台明写「面议」的 21 个岗里，
**2 个**仍然写了薪资维分数 —— 一个 58、一个 **0**。

## 0 比「随便给个数」更坏

0 的意思是「薪资很差」，而真相是「不知道」。那一个的总分被压到 45、
判词落到「不建议」—— 一个可能不错的岗，因为对方没公开薪资而出局。
按规则重算是 50（+13）。

那个 58 更隐蔽：它自己的评估里写着
「薪资维按**信息缺失折算中性值**」—— 而「折算一个中性值」既不是打分、
也不是不打分，是执行者发明的第三条路（这个说法在框架和所有工作流里查无出处，
268 份深评里 4 份用了它）。中性值仍占 25% 权重，会把总分往它自己身上拉。

## 判据第一版太宽，报错了一个

第一版直接用 `_cli.salary_unstated`（「串里一个数字都没有」），它把 `None`
也算进去，于是报出 4 个。其中一个的列表薪资是**空**的，而深评读过 JD 正文、
里面明写着「25-35k·15薪」—— 打 46 分完全正确。
**空 ≠ 面议**：空只说明列表页没抓到。收窄成「非空、且不含数字」之后，
命中恰好是那 2 个真违规，零误报。

## 判据提成了具名函数

「串里一个阿拉伯数字都没有」这条判据原来在 `export_web_data` 里内联了两处
（`annual_of` 与 `salary_months_unknown` 的开头守卫），字面完全一样。
审计要用它就是第三处 —— 所以提成 `_cli.salary_unstated`，三处共用一份。
**不枚举写法**：平台的说法五花八门（面议 / 薪资面议 / 另议 / 详谈），枚举必漏。
"""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tests"))
from _srcscan import strip_comments  # noqa: E402
import _cli  # noqa: E402
import audit_pipeline as A  # noqa: E402

AUDIT = (ROOT / "tools" / "audit_pipeline.py").read_text(encoding="utf-8")
EX = (ROOT / "tools" / "export_web_data.py").read_text(encoding="utf-8")
EVAL = (ROOT / "workflows" / "reference"
        / "04-job-evaluation.md").read_text(encoding="utf-8")


class TheJudgeIsNamedAndShared(unittest.TestCase):
    def test_it_exists(self):
        self.assertTrue(hasattr(_cli, "salary_unstated"))

    def test_it_catches_every_wording(self):
        for s in ("面议", "薪资面议", "另议", "详谈", "", "   ", None):
            with self.subTest(s=s):
                self.assertTrue(_cli.salary_unstated(s), f"{s!r} 应算「给不出数」")

    def test_anything_with_a_digit_is_stated(self):
        for s in ("20-35k·14薪", "3千及以下", "面议 8k 起", "120-200元/天"):
            with self.subTest(s=s):
                self.assertFalse(_cli.salary_unstated(s))

    def test_it_does_not_enumerate_wordings(self):
        """枚举「面议」这类词必漏 —— 判据只能是「有没有数字」。"""
        i = _cli.__file__
        src = strip_comments(Path(i).read_text(encoding="utf-8"))
        j = src.index("def salary_unstated(")
        body = src[j:src.index("\ndef ", j + 10)]
        self.assertNotIn("面议", body, "判据里枚举了写法")
        self.assertIn(r'\d', body)

    def test_the_two_old_sites_now_call_it(self):
        """原来内联两处、字面完全一样 —— 不改的话这就是第三份。"""
        self.assertEqual(EX.count("_cli.salary_unstated(t)"), 2)
        self.assertNotIn('if not t or not re.search(r"\\d", t):', EX,
                         "还留着内联的那一份")

    def test_the_reason_is_recorded(self):
        src = Path(_cli.__file__).read_text(encoding="utf-8")
        i = src.index("def salary_unstated(")
        seg = " ".join(src[i:src.index("\ndef ", i + 10)].split())
        self.assertRegex(seg, r"21 个面议岗里 19 个照做了")
        self.assertRegex(seg, r"面议不计入 → 总分 76；照打 → 63")
        self.assertIn("2026-08-23", seg)


class TheAuditChecksIt(unittest.TestCase):
    def test_the_check_exists(self):
        self.assertTrue(hasattr(A, "check_negotiable_salary_is_not_scored"))

    def test_it_is_registered(self):
        self.assertIn('("薪资：面议不该打分", check_negotiable_salary_is_not_scored)',
                      AUDIT)

    def test_it_fires_on_a_scored_negotiable_job(self):
        seen = {"a": {"title": "岗", "salary": "面议",
                      "rank_breakdown": {"薪资与职级": 0}, "rank_score": 45}}
        out = A.check_negotiable_salary_is_not_scored(seen, {})
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0][0], "warn")

    def test_an_empty_salary_is_not_reported(self):
        """**空 ≠ 面议。** 空只说明列表没抓到，而深评读过 JD ——
        实测有一个岗列表为空、评估里明写着「25-35k·15薪」，打 46 分完全正确。
        第一版把 `None` 也算进去，就把这种合法情形报成了违规。"""
        for s in (None, "", "   "):
            with self.subTest(salary=s):
                seen = {"a": {"title": "岗", "salary": s,
                              "rank_breakdown": {"薪资与职级": 46}}}
                self.assertEqual(
                    A.check_negotiable_salary_is_not_scored(seen, {}), [],
                    "薪资串为空被当成了面议")

    def test_other_negotiable_wordings_still_fire(self):
        """窄不等于只认「面议」两个字 —— 平台的说法五花八门。"""
        for s in ("另议", "详谈", "薪资面议", "薪资详谈"):
            with self.subTest(salary=s):
                seen = {"a": {"title": "岗", "salary": s,
                              "rank_breakdown": {"薪资与职级": 50}}}
                self.assertEqual(
                    len(A.check_negotiable_salary_is_not_scored(seen, {})), 1)

    def test_the_narrowing_is_explained(self):
        """判据收窄的理由要留下 —— 否则下一版会「顺手」把空串加回去。"""
        i = AUDIT.index("def check_negotiable_salary_is_not_scored(")
        seg = " ".join(AUDIT[i:AUDIT.index("\n    hit = []", i)].split())
        self.assertRegex(seg, r"空 ≠ 面议")
        self.assertRegex(seg, r"判不准的扫描器比没有更坏")

    def test_it_stays_quiet_when_the_rule_is_followed(self):
        """面议且没打分 —— 那是对的，不该报。"""
        seen = {"a": {"title": "岗", "salary": "面议",
                      "rank_breakdown": {"薪资与职级": None}},
                "b": {"title": "岗2", "salary": "薪资面议",
                      "rank_breakdown": {"依据": "薪资面议，这一项不计入"}}}
        self.assertEqual(A.check_negotiable_salary_is_not_scored(seen, {}), [])

    def test_a_real_salary_with_a_score_is_fine(self):
        seen = {"a": {"title": "岗", "salary": "20-35k·14薪",
                      "rank_breakdown": {"薪资与职级": 60}}}
        self.assertEqual(A.check_negotiable_salary_is_not_scored(seen, {}), [])

    def test_zero_is_called_out_separately(self):
        """0 和「随便给个数」不是一回事 —— 0 会实打实把总分压下去。"""
        seen = {"a": {"title": "岗", "salary": "面议",
                      "rank_breakdown": {"薪资与职级": 0}}}
        msg = A.check_negotiable_salary_is_not_scored(seen, {})[0][2]
        self.assertIn("0 的意思是「薪资很差」", msg)

    def test_zero_is_not_mentioned_when_there_is_none(self):
        seen = {"a": {"title": "岗", "salary": "面议",
                      "rank_breakdown": {"薪资与职级": 58}}}
        msg = A.check_negotiable_salary_is_not_scored(seen, {})[0][2]
        self.assertNotIn("给的是 0", msg)

    def test_the_message_cites_the_framework_arithmetic(self):
        seen = {"a": {"title": "岗", "salary": "面议",
                      "rank_breakdown": {"薪资与职级": 0}}}
        msg = A.check_negotiable_salary_is_not_scored(seen, {})[0][2]
        self.assertIn("04-job-evaluation.md", msg)
        self.assertIn("面议不计入 76 分，照打 63", msg)

    def test_the_message_says_the_platform_wrote_it(self):
        """「给不出数」和「平台明写着不是数字」是两回事 —— 后者才是判据。
        报成前者，读的人会以为空薪资也算。"""
        seen = {"a": {"title": "岗", "salary": "面议",
                      "rank_breakdown": {"薪资与职级": 0}}}
        msg = A.check_negotiable_salary_is_not_scored(seen, {})[0][2]
        self.assertIn("平台明写着不是数字", msg)

    def test_the_message_says_what_to_do(self):
        seen = {"a": {"title": "岗", "salary": "面议",
                      "rank_breakdown": {"薪资与职级": 0}}}
        msg = A.check_negotiable_salary_is_not_scored(seen, {})[0][2]
        self.assertIn("/job-rank --all", msg)

    def test_no_markdown_reaches_the_terminal(self):
        """审计输出印在终端上 —— `**` 会连星号一起显示。"""
        seen = {"a": {"title": "岗", "salary": "面议",
                      "rank_breakdown": {"薪资与职级": 0}}}
        title, msg = A.check_negotiable_salary_is_not_scored(seen, {})[0][1:]
        for s in (title, msg):
            with self.subTest(s=s[:20]):
                self.assertNotIn("**", s)

    def test_it_uses_the_shared_judge(self):
        i = AUDIT.index("def check_negotiable_salary_is_not_scored(")
        body = AUDIT[i:AUDIT.index("\ndef ", i + 10)]
        self.assertIn("_cli.salary_unstated(", body)
        self.assertNotIn("面议\"", body, "又在这里枚举写法了")


class TheInventedMiddlePathIsNamed(unittest.TestCase):
    """规则正着说「不打分」不够 —— 执行者发明了第三条听起来很合规的路。"""

    def _seg(self) -> str:
        i = EVAL.index("「折算一个中性值」不算「不打分」")
        return EVAL[i:EVAL.index("## ", i)]

    def test_the_wrong_form_is_named(self):
        self.assertIn("「折算一个中性值」不算「不打分」——那是第三条路，别走。",
                      EVAL, "框架仍然只正着说「不打分」")

    def test_it_says_the_phrase_is_invented(self):
        seg = " ".join(self._seg().split())
        self.assertRegex(seg, r"在本框架和所有工作流里查无出处")
        self.assertRegex(seg, r"听起来很像在守规矩")

    def test_the_phrase_really_is_absent_elsewhere(self):
        """这条断言是上面那句的事实基础 —— 哪天真写进别处，这一段要重写。"""
        for f in sorted((ROOT / "workflows").rglob("*.md")):
            with self.subTest(f=f.name):
                body = f.read_text(encoding="utf-8")
                if f.name == "04-job-evaluation.md":
                    body = body.replace(self._seg(), "")
                self.assertNotIn("折算中性值", body)

    def test_it_explains_why_neutral_is_not_neutral(self):
        seg = " ".join(self._seg().split())
        self.assertRegex(seg, r"仍然占 25% 权重，会把总分\*\*往它自己身上拉\*\*")
        self.assertRegex(seg, r"只有碰巧等于其余三项时它才无害")

    def test_it_carries_the_recomputed_costs(self):
        seg = " ".join(self._seg().split())
        self.assertRegex(seg, r"38 → 50（\+13")
        self.assertRegex(seg, r"64 → 70（\+6）")
        self.assertIn("2026-08-23", seg)

    def test_it_gives_the_right_output_shape(self):
        """只说「别那样」不够，要说清那一格该写什么。"""
        seg = " ".join(self._seg().split())
        self.assertRegex(seg, r"薪资那一格写「信息缺失」，不写数字")

    def test_it_points_at_the_checker(self):
        self.assertIn("「薪资：面议不该打分」", self._seg())

    def test_it_carves_out_the_empty_case(self):
        seg = " ".join(self._seg().split())
        self.assertRegex(seg, r"`salary` 为空是另一回事")
        self.assertRegex(seg, r"只有平台\*\*明写\*\*「面议 / 另议 / 详谈」时")

    def test_the_carve_out_gives_its_evidence(self):
        """例外不给实例就会被当成含糊其辞删掉 —— 那一个岗是这条例外的全部依据。"""
        seg = " ".join(self._seg().split())
        self.assertRegex(seg, r"深评读过 JD 正文")
        self.assertRegex(seg, r"评估里明写着「25-35k·15薪」")


class TheFrameworkRuleItEnforcesIsIntact(unittest.TestCase):
    def test_the_rule_still_says_do_not_score(self):
        self.assertRegex(
            "".join(EVAL.split()),
            r"\*\*薪资面议\*\*：`salary`为「薪资面议」时，这一维\*\*不打分\*\*")

    def test_the_arithmetic_it_cites_is_still_there(self):
        self.assertRegex(" ".join(EVAL.split()),
                         r"面议）→ 信息缺失、权重重分配 → 总分 76")

    def test_the_display_rule_survives(self):
        """权重是内部参数 —— 别把「权重重分配」照抄到用户看的说明栏里。"""
        self.assertRegex(" ".join(EVAL.split()),
                         r"写进「说明」栏时别照抄这句")


if __name__ == "__main__":
    unittest.main()
