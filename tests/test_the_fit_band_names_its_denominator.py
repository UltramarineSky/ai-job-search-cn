# -*- coding: utf-8 -*-
"""「投出去的 78 个里」—— 投出去的是 85 个。

「投的地方对不对」那一栏把四格摊开，产出的是这一页最有分量的一句结论：

    49 个是「你的专业能力够、但这个岗要的行业经验你没做过」
    —— 不是简历写得不好，是投的地方不对。

**分母是这句结论的全部依据**，而它只数「评分拆得出两笔分」的岗
（`gap_split.read_pair`；早期评估用的是旧口径，拆不出来）。实测 2026-08-23：

    投出去的            85   ·  拆得出分的  78
    还能投的            231  ·  拆得出分的  227

差得不多，结论也不变 —— 但两个数都写成了「投出去的 78 个」「还没投的 227 个」，
**把子集说成了全体**。而 231 这个数这一页别处刚印过（「行业对口…现在还能投的
是 49」那一行的同一批），读的人对不上就只能怀疑其中一个坏了。

这一族在本仓库反复出现，判据一律是：**一个数旁边要说清它数的是哪一批**。
"""
import json
import re
import unittest
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
from _srcscan import strip_comments  # noqa: E402
SRC = (ROOT / "web" / "src" / "components"
       / "OutcomeStats.tsx").read_text(encoding="utf-8")


#: **先剥注释再扫。** 这一段的注释里逐字引着那句结论（「不是简历写得不好，
#: 是投的地方不对」—— 它就是在解释那句话为什么要保）。连注释一起扫，
#: 把渲染里的结论删掉照样绿：变异实测漏过一次。这个坑本仓库栽过八次以上。
CODE = strip_comments(SRC)


def _band(src=None):
    t = src if src is not None else SRC
    i = t.index("投的地方对不对")
    return t[i:i + 3000]


class BothHalvesSayWhatTheyCount(unittest.TestCase):
    def test_the_applied_half_names_it(self):
        self.assertIn("评分拆得出来的那些", _band(),
                      "「投出去的 N 个」没说清是哪一批")

    def test_the_open_half_names_it(self):
        self.assertIn("同样只算拆得出分的", _band(),
                      "「还没投的 N 个」没说清是哪一批")

    def test_the_applied_half_says_how_many_fell_out(self):
        """只说「拆得出来的那些」还不够：差几个要说出来，
        否则读者拿它和「投了 85 个」对不上时还是没答案。"""
        seg = _band()
        self.assertRegex(seg, r"s\.total - s\.appliedFit\.total")
        self.assertRegex(seg, r"拆不出、没算")

    def test_it_stays_quiet_when_nothing_fell_out(self):
        """全部拆得出来时不该多一句「另有 0 个拆不出」。"""
        seg = _band()
        self.assertRegex(seg, r"s\.total > s\.appliedFit\.total\s*\n?\s*\?",
                         "没有「有才说」的门槛")

    def test_the_conclusion_itself_is_untouched(self):
        """**只加分母的说明，不动结论。** 那句话是这一栏存在的理由。"""
        seg = _band(CODE)
        self.assertIn("不是简历写得不好，是投的地方不对", seg)
        self.assertIn("真正对得上的只有", seg)

    def test_the_restock_command_survives(self):
        self.assertIn("/job-setup --section search", _band())


class TheNumbersReallyDifferOnRealData(unittest.TestCase):
    """如果 78==85、227==231，那这次改动就是在解释一个不存在的差异。"""

    def _snap(self):
        p = ROOT / "web" / "public" / "data.json"
        if not p.is_file():
            self.skipTest("还没导出面板数据")
        return json.loads(p.read_text(encoding="utf-8"))

    def test_the_scored_subset_is_smaller(self):
        o = self._snap().get("outcomeStats") or {}
        fit = o.get("appliedFit")
        if not fit:
            self.skipTest("这份快照里没有四格")
        self.assertLessEqual(fit["total"], o["total"])
        self.assertLess(fit["total"], o["total"],
                        "全都拆得出分 —— 这次的说明就没有对象了（可以删）")

    def test_the_open_subset_is_smaller_than_the_sellable_list(self):
        snap = self._snap()
        fit = ((snap.get("outcomeStats") or {}).get("appliedFit") or {}).get("open")
        if not fit:
            self.skipTest("这份快照里没有还没投的四格")

        # **判词词表不许在这里内联一份** —— 正本在 `_cli.VERDICTS`，
        # 切片即子集（`test_shared_vocab_single_source` 盯着，刚被它拦下一次）。
        sys.path.insert(0, str(ROOT / "tools"))
        import _cli

        def plain(j):
            return (j.get("verdict") or "").replace("粗筛：", "").strip()

        sellable = sum(1 for j in snap["jobs"]
                       if not j.get("dupOf") and not j.get("applied")
                       and not j.get("skipped") and not j.get("expired")
                       and plain(j) in _cli.VERDICTS[:3])
        self.assertLessEqual(fit["total"], sellable)
        self.assertLess(fit["total"], sellable,
                        "两个数一样大 —— 那就不该额外解释")

    def test_the_quadrants_sum_to_the_stated_total(self):
        """四格加起来必须等于那个分母，否则「拆得出分的那些」这句话是假的。"""
        for key in ("appliedFit",):
            fit = (self._snap().get("outcomeStats") or {}).get(key)
            if not fit:
                self.skipTest("没有四格")
            for label, box in (("已投", fit), ("未投", fit.get("open") or {})):
                if not box:
                    continue
                with self.subTest(which=label):
                    n = sum(box[k] for k in ("home", "pick", "learn", "off"))
                    self.assertEqual(n, box["total"], f"{label}：四格 {n} ≠ {box['total']}")


class TheTwoDefinitionsStayDistinct(unittest.TestCase):
    """「行业对口 49」和「主场 11」不是同一件事 —— 一个只看行业一维，
    一个两维都要。这一页为此专门改过名，别又被人合并。"""

    def test_the_resume_panel_still_calls_it_by_the_one_axis(self):
        rr = (ROOT / "web" / "src" / "components"
              / "ResumeRead.tsx").read_text(encoding="utf-8")
        self.assertIn("行业对口的岗", rr)
        self.assertRegex(rr, r"只有\*\*行业经验 ≥60\*\* 一维|专业能力那一维压根没看")

    def test_the_fit_band_needs_both_axes(self):
        src = (ROOT / "tools" / "gap_split.py").read_text(encoding="utf-8")
        i = src.index("def quadrant(")
        seg = src[i:i + 300]
        self.assertIn("stack >= STACK_OK", seg)
        self.assertIn("domain >= DOMAIN_OK", seg)


if __name__ == "__main__":
    unittest.main()
