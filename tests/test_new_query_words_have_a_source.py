# -*- coding: utf-8 -*-
"""「改搜索词」是三处引导指向的杠杆，而**新词从哪来**没人说。

面板现在有三处把人送去 `/job-setup --section search`：行业对口那批见底、
英语挡路那一栏、投后四格那句「不是简历写得不好，是投的地方不对」。
重跑那一节的人多半正是因为「投了没回音、多数是行业对不上」才来的。

那一节确实先读实测（`query_yield`）—— 但**那张表只能给现有的词打分**：
哪个词该停、哪个词值得往新平台扩。它给不出一个新词。

而原料一直在：`resume_insight.sweetSpot.industries` —— **他行业经验够得上的
那批岗，实际落在哪些行业**。实测活动用户 2026-08-23，107 个行业对口的岗里：

    互联网 23 · 计算机软件 19 · IT服务 11 · 未标 10 · 电子商务 8 · 人工智能 7

而「行业/领域关键词」那一问取的是**他自己说的**（从 `candidate.md` 读）。
两者不是一回事：他说的是想去的，实测说的是够得着的。

**这条规矩仍然行业无关**：那几个行业名是从他自己的语料里数出来的
（每个岗的 `compIndustry`，只数行业经验 ≥60 的那批），换个人跑出来就是另一组词。
同本节开头「不要举例」那条的理由 —— 写死一份行业清单才是预设。
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SETUP = (ROOT / "workflows" / "job-setup.md").read_text(encoding="utf-8")


def _group2() -> str:
    i = SETUP.index("#### 第 2 组：目标岗位与关键词")
    m = re.search(r"^#### ", SETUP[i + 10:], re.M)
    return SETUP[i:i + 10 + m.start()] if m else SETUP[i:]


class TheRerunKnowsWhereNewWordsComeFrom(unittest.TestCase):
    def test_it_names_the_source(self):
        self.assertIn("sweetSpot.industries", _group2(),
                      "重跑那一节仍然只会给现有的词打分")

    def test_it_says_why_the_yield_table_is_not_enough(self):
        """不说清「那张表给不出新词」，读者会以为读完表就够了。"""
        self.assertRegex(_group2(), r"只能给现有的词打分|给不出新词")

    def test_it_stays_industry_agnostic(self):
        """行业名是从他自己的语料里数出来的 —— 这一句必须在，
        否则下一个人会把它读成「工具内置了一份行业清单」。"""
        seg = _group2()
        self.assertRegex(seg, r"从他自己的语料里数出来|换个人跑出来就是另一组词")
        self.assertIn("compIndustry", seg, "没说清那几个行业名是哪个字段来的")

    def test_it_warns_against_using_the_industry_name_alone(self):
        """平台搜索框认的是岗位名。单搜一个行业名会返回一堆不相干的岗。"""
        seg = _group2()
        # **两半都要。** 告诫（别单搜）和正确用法（和岗位名组合）缺一不可 ——
        # 写成 `告诫|用法` 的话删掉告诫照样绿，变异实测漏过一次。
        self.assertIn("别直接拿行业名当查询词", seg, "没有那句告诫")
        self.assertIn("和主岗位名组合", seg, "没给正确用法")
        self.assertIn("PRIORITY_2_CATEGORY_NAME", seg, "没接到已有的组合写法上")

    def test_it_asks_instead_of_deciding(self):
        """同这一节既有的规矩：只报事实，改不改由他定。"""
        seg = _group2()
        i = seg.index("sweetSpot.industries")
        self.assertRegex(seg[i:i + 900], r"问哪几个值得|要不要挑")

    def test_it_skips_when_the_corpus_is_thin(self):
        """三五个样本的分布指不出方向 —— 同 `resume_insight` 自己的门槛。"""
        self.assertRegex(_group2(), r"评估语料不足 10 份|这一段跳过")

    def test_the_yield_table_half_survives(self):
        """原来那半（哪个词该停）答的是另一个问题，不许被挤掉。"""
        seg = _group2()
        self.assertIn("query_yield.py", seg)
        self.assertRegex(seg, r"该停一停的词")


class TheTwoAnswersAreDistinguished(unittest.TestCase):
    """「他自己说的领域词」和「市场量出来的行业」不是一回事。"""

    def test_the_question_says_which_wins_on_a_rerun(self):
        seg = _group2()
        i = seg.index("**问：行业/领域关键词**")
        self.assertRegex(seg[i:i + 900], r"以实测为准",
                         "两个来源冲突时没说听谁的")

    def test_it_says_what_each_one_means(self):
        seg = _group2()
        i = seg.index("**问：行业/领域关键词**")
        self.assertRegex(seg[i:i + 900], r"他想去的.*够得着的|想去的|够得着的")

    def test_the_no_examples_rule_survives(self):
        """「这里不要举例」那条是防「让不在其中的人以为工具不是给他用的」——
        新加的那段引用的是**他自己的**数据，不构成举例，但那条规矩要还在。"""
        self.assertIn("**这里不要举例。**", _group2())


class TheFieldReallyExists(unittest.TestCase):
    """文档让读的字段必须真在快照里 —— 指一个不存在的字段等于没写。"""

    def test_the_exporter_produces_it(self):
        src = (ROOT / "tools" / "export_web_data.py").read_text(encoding="utf-8")
        i = src.index("def resume_insight(")
        seg = src[i:src.index("\ndef ", i + 10)]
        self.assertIn('"industries"', seg)
        self.assertIn("compIndustry", seg)

    def test_it_only_counts_the_home_turf_ones(self):
        """整库的行业分布没有意义 —— 要的是「他够得上的那批」在哪些行业。"""
        src = (ROOT / "tools" / "export_web_data.py").read_text(encoding="utf-8")
        i = src.index('"industries"')
        self.assertIn("sweet", src[max(0, i - 300):i + 200],
                      "行业分布不是按行业对口那批算的")

    def test_a_real_snapshot_carries_it(self):
        import json
        p = ROOT / "web" / "public" / "data.json"
        if not p.is_file():
            self.skipTest("还没导出面板数据")
        ss = (json.loads(p.read_text(encoding="utf-8"))
              .get("resumeInsight") or {}).get("sweetSpot")
        if not ss:
            self.skipTest("这份快照里没有市场反馈")
        self.assertTrue(ss.get("industries"), "行业分布是空的")
        self.assertTrue(all({"name", "n"} <= set(x) for x in ss["industries"]))


if __name__ == "__main__":
    unittest.main()
