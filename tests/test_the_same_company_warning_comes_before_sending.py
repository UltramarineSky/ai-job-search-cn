# -*- coding: utf-8 -*-
"""「这家你投了几个岗」这条提醒，只在**投完之后**才说。

`followups.py` 把道理写全了，而且写得很好：

> 催进度是**按人**发的：同一家公司投了 5 个岗，发 5 条各问各的，
> 对面看到的是同一个人在同一个 ATS 里刷屏。
>
> 国内投递里同一家既被猎头报备、自己又直投过，用人方那边会撞成重复候选人，
> 谁来推、推荐费算谁的都要掰扯，处理不好两条都卡住。

**但它长在 `/job-outcome followup` 里** —— 那是投出去之后、等了十天才跑的东西。
避撞单的意义恰恰在于**别让它发生**。

实测活动用户 2026-08-23：备好没投的 75 个里有 **7 个**落在已投过的公司 ——
最重的那家发完会是 **6 个**、第二重的 **4 个**。而同一块面板正在劝他
「手上那 62 份备好的别等」。照做就是往一家公司里再塞一个。

## 公司身份必须走 `cluster_key`

裸比公司名会把脱敏串当成一家：猎聘给猎头岗打的「某知名公司」库里出现 158 次，
那是 158 家不同的用人方。裸比的结果是详情里印一句
「这家你已经投过 4 个岗」，而那四个岗是四家公司。
`followups.cluster_key` 就是为这件事写的，直接用它，不另写一份。

## 为什么放详情、不放列表

实测有 92 个岗带着这个数。列表上挂 92 枚标记是噪音；
详情是他真正在决定投不投的地方。

## 这份文件守哪一半

守的是**这条提醒存不存在、算在什么时候、公司怎么归并**。

那句话本身的措辞（「短期内」到底多短、日期印不印出来、窗口外该说什么）
2026-08-24 单独拆出去了 —— 见
`tests/test_the_same_company_warning_has_no_clock.py`。拆的原因：那一版的
计数器**没有任何时间维度**，却印着一句带时间状语的话，而这份文件里没有
一条断言能看出这件事。两份文件守同一个字段的两件事，别互相抄。
"""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import followups as fu  # noqa: E402

EXPORT = (ROOT / "tools" / "export_web_data.py").read_text(encoding="utf-8")
JR = (ROOT / "web" / "src" / "components"
      / "JobReadout.tsx").read_text(encoding="utf-8")
TYPES = (ROOT / "web" / "src" / "types.ts").read_text(encoding="utf-8")
FU = (ROOT / "tools" / "followups.py").read_text(encoding="utf-8")


def counter_block() -> str:
    """从注释开头到写字段那一行为止。

    **按内容切，不按固定长度。** 第一版写 `funnels_of(j)` 之后 +200 字，
    刚好没盖到 `if n:` 那两行 —— 断言当场落空。"""
    i = EXPORT.index("**这家你已经投过几个了。**")
    return EXPORT[i:EXPORT.index('j["sameCompanyWarn"] = _note', i) + 45]


class TheCountIsComputedBeforeSending(unittest.TestCase):
    def test_the_field_is_produced(self):
        self.assertIn('j["sameCompanyWarn"] = _note', EXPORT,
                      "还是只有投完之后那条路会说这件事")

    def test_it_reuses_the_clustering_helper(self):
        """**不许裸比公司名。** 脱敏串会把 158 家印成一家。

        **两处都要走它**：算分母的那个 Counter，和逐岗回查那一次。
        只验「出现过」的话，把 Counter 那处换成裸比照样绿（变异实测）——
        而分母裸比正是「某知名公司 158 次」那个错法。"""
        self.assertIn("from followups import cluster_key", EXPORT)
        self.assertEqual(
            EXPORT.count('cluster_key(j.get("company") or "")'), 2,
            "两处（分母的 Counter、逐岗回查）必须都走 cluster_key")

    def test_it_never_writes_a_second_matcher(self):
        """自己重写一份归并逻辑是这个仓库最贵的错法之一。"""
        block = counter_block()
        self.assertNotIn("is_anonymous_employer", block,
                         "在这儿又拆了一遍脱敏判定 —— 用 cluster_key")

    def test_only_unsent_jobs_carry_it(self):
        """已投的岗自己就是分子，给它带这个数会让人以为要重复处理。"""
        block = counter_block()
        self.assertIn('if not j.get("applied"):', block)

    def test_zero_is_omitted(self):
        """0 不是信息。缺字段直接不出现，是这一页一贯的做法。"""
        self.assertRegex(" ".join(counter_block().split()),
                         r"if _note:\s*j\[\"sameCompanyWarn\"\] = _note")

    def test_it_runs_after_the_tracker_is_joined(self):
        """算在回接之前的话，分母永远是 0。

        **比的是代码的位置，不是注释的位置。** 第一版拿那句注释的下标去比 ——
        把 `_sent_at` 那行整个挪到回接之前、注释留在原地，断言照样绿
        （变异实测）。"""
        self.assertLess(EXPORT.index('primary["applied"] = j["applied"]'),
                        EXPORT.index("_sent_at: dict[str, list[str]]"))

    def test_the_reason_is_recorded_with_numbers(self):
        seg = " ".join(counter_block().split())
        self.assertRegex(seg, r"最重的那家发完会是 \*\*6 个\*\*")
        self.assertIn("2026-08-23", seg, "实测数没带日期")
        self.assertRegex(seg, r"那是\*\*投完之后\*\*才跑的")

    def test_it_names_both_costs(self):
        """广撒网和撞单不是一回事，少说一个就少了一半理由。"""
        seg = " ".join(counter_block().split())
        self.assertIn("广撒网", seg)
        self.assertRegex(seg, r"撞成重复候选人")


class TheReadoutSaysItWhereHeDecides(unittest.TestCase):
    """句子 2026-08-24 搬去 Python 拼了（`same_company_note`），这里只剩
    「渲不渲染、渲在哪」。措辞本身归 `..._has_no_clock.py`。"""

    def _seg(self) -> str:
        i = JR.index("**这家你已经投过几个了。**")
        return JR[i:i + 2000]

    def test_the_line_exists(self):
        self.assertIn("{job.sameCompanyWarn}", JR)

    def test_it_is_rendered_as_a_warning(self):
        self.assertIn('className="readout-facts warn"', self._seg())

    def test_the_two_costs_are_still_said_somewhere(self):
        """广撒网和撞单不是一回事。句子换了个地方拼，两条都不许丢。"""
        import export_web_data as _ex
        got = _ex.same_company_note(5, 3)
        self.assertIn("在刷屏", got)
        self.assertIn("撞成重复候选人", got)

    def test_it_says_what_to_actually_do(self):
        """「有风险」不是行动。要说清投之前该做哪一件事。"""
        import export_web_data as _ex
        self.assertIn("先确认他没把你报备到同一家",
                      _ex.same_company_note(5, 3))

    def test_it_hides_at_zero(self):
        self.assertIn("{job.sameCompanyWarn && (", self._seg())

    def test_it_says_why_not_on_the_list(self):
        """不写理由，下一版会「顺手」把它挪到列表上，然后 92 行全是标记。"""
        seg = " ".join(self._seg().split())
        self.assertRegex(seg, r"列表上挂 92 枚标记是噪音")

    def test_the_type_declares_it(self):
        self.assertIn("sameCompanyWarn?: string;", TYPES)
        i = TYPES.index("sameCompanyWarn?: string;")
        self.assertIn("cluster_key", TYPES[max(0, i - 900):i],
                      "类型里没说清公司身份是怎么归的")


class TheHelperItLeansOnStillBehaves(unittest.TestCase):
    """整条改动建立在 `cluster_key` 上。它变了，上面全部要重看。"""

    def test_a_real_company_clusters(self):
        self.assertEqual(fu.cluster_key("甲科技"), "甲科技")

    def test_an_anonymised_string_does_not(self):
        for s in ("某知名公司", "某上海互联网公司"):
            with self.subTest(s=s):
                self.assertEqual(fu.cluster_key(s), "",
                                 f"「{s}」被当成了一家公司")

    def test_empty_does_not(self):
        self.assertEqual(fu.cluster_key("  "), "")

    def test_the_docstring_still_explains_why(self):
        i = FU.index("def cluster_key(")
        seg = FU[i:i + 900]
        self.assertIn("脱敏串归不了，返回空串", seg)
        self.assertRegex(" ".join(seg.split()), r"158 次")


class TheAfterTheFactWarningIsUntouched(unittest.TestCase):
    """投前这条是**补**的，不是替。投完之后那条一个字都不能少。"""

    def test_followups_still_groups_by_company(self):
        self.assertRegex(" ".join(FU.split()),
                         r"这家你\{where\}投了 \{size\[k\]\} 个岗")

    def test_followups_still_warns_about_cross_channel(self):
        self.assertIn("用人方那边可能撞成重复候选人", FU)

    def test_followups_still_keeps_the_channel_in_the_key(self):
        """猎聘和 BOSS 是两个 app，一条消息发不到两边。"""
        self.assertIn('return (c, ch, 0) if c else ("", "", i + 1)', FU)


if __name__ == "__main__":
    unittest.main()
