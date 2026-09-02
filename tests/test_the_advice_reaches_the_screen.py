# -*- coding: utf-8 -*-
"""评估里「建议」那一节要有人读 —— 而且它说「不投」时，页面不许再催你去投。

## 为什么

`04-job-evaluation.md` 的输出格式里，「建议」是**每份深评都要写**的一节，
写的是读完这个岗之后的人话结论。而在 2026-09-02 之前，**它没有任何消费方**：
`data.json` 里从来没有这个字段，于是屏幕上只剩判词那一半。

判词和建议**可以合法地不一致** —— 判词是打分器给的档，建议是读完之后的结论：

    判词「可以考虑」 ＋ 建议「不投。同一个岗有薪资更高的挂法，投那一条」

问题从来不在它们不一致，在于**只有一半能到眼前**。实测（2026-09-02，活动用户
的真实产出）：**50 份深评的「建议」以「不投」开头**，其中 **13 个**的逐岗
「下一步」正印着「材料就绪，还没投——复制开场白、开职位链接自己投出去」。
`AGENTS.md` 管这个形状叫「同一份文档一边发出邀请，一边把门关上」。

## 这条和 `is_out_verdict` 那条是同一形状

`job_next_step` 里已经有一条「判词出局的岗不催去投，哪怕材料已经做好了」，
它的注释记着一模一样的事故（判词后来降档，页面照旧催投）。这一条是同一形状
再深一层：**判词没出局，但读完这个岗的人说了别投。**

## 判据钉行为，不钉措辞

三件事：**导出带得出这个字段**、**说「不投」时不给催投的下一步**、
**两处「什么算不投」的词表相等**。至于那句话怎么写、CSS 什么颜色，不钉。
"""

import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tests"))
import build_dashboard as bd  # noqa: E402

EVAL = """# 职位评估

### 结论：可以考虑

**综合得分：54/100**

### 建议

{advice}

### 待核实的信息

- 无
"""


class TheAdviceIsParsed(unittest.TestCase):

    def test_it_comes_out_of_the_evaluation(self):
        r = bd.parse_evaluation(EVAL.format(advice="不投。域是零。"))
        self.assertEqual(r["verdict"], "可以考虑")
        self.assertIn("不投", r["advice"])

    def test_no_advice_section_is_not_a_crash(self):
        r = bd.parse_evaluation("### 结论：可以考虑\n\n**综合得分：54/100**\n")
        self.assertEqual(r.get("advice"), "")


class ItStopsTheNagWhenItSaysNo(unittest.TestCase):
    """材料备好、判词没出局 —— 唯一拦得住的就是这一节。"""

    def _job(self, advice):
        return {"company": "某公司", "url": "https://x/1", "verdict": "可以考虑",
                "score": 54, "materials": {"greeting": "..."}, "advice": advice}

    def test_it_still_nags_when_the_advice_says_go(self):
        """控制组：没有这一节、或它没说别投时，照旧催去投。

        少了它，上面那条可以靠「谁都不催」蒙混过去。
        """
        for advice in ("", "投。这个岗值得，尽快发。"):
            with self.subTest(advice=advice):
                step = bd.job_next_step(self._job(advice))
                self.assertIn("复制开场白", step["text"])

    def test_it_does_not_nag_when_the_advice_says_no(self):
        for advice in ("不投。域是零。", "不建议投。定级偏低。",
                       "**不投**。同一个岗有更好的挂法。"):
            with self.subTest(advice=advice):
                step = bd.job_next_step(self._job(advice))
                self.assertNotIn("复制开场白", step["text"],
                                 "评估说别投，页面还在催他去投")

    def test_the_guidance_names_which_branch_does_what(self):
        """一条引导只给一个动作 —— 真有分支就写清哪种情况做哪件事。

        `AGENTS.md`「每一处引导都要写出该敲的命令」第 3 条。
        我自己第一版就犯了：文案让他「点『不投这个岗』」，命令块给的却是
        `/job-apply` —— 一条引导里两个动作，用户得先做一次选择，
        而那正是引导本该替他省掉的那一步。

        判据钉**两个分支都点了名**，不钉措辞。
        """
        step = bd.job_next_step(self._job("不投。域是零。"))
        self.assertIn("不投这个岗", step["text"], "没说同意的话该做什么")
        self.assertRegex(step["text"], r"(不对|不同意|不认同)",
                         "没说不同意的话该做什么 —— 而命令块给的正是那一支")
        self.assertTrue(step["command"].startswith("/job-apply"),
                        "命令和「重跑一遍」那一支对不上")

    def test_only_the_opening_counts(self):
        """「建议」里顺口提到「不投」的句子太多了，按包含判会误伤一片。"""
        step = bd.job_next_step(self._job(
            "可以投，先问清楚定级；若不投也不可惜。"))
        self.assertIn("复制开场白", step["text"])

    def test_both_job_shapes_are_read(self):
        """两条调用路手上的 job 形状不一样，只认一种就是「本机通、面板没生效」。

        实测 2026-09-02：第一版只读嵌套那种，导出之后 13 个岗照旧催投，
        而 `advice` 明明已经在 `data.json` 里了。
        """
        flat = self._job("不投。域是零。")
        nested = {**self._job(""), "evaluation": {"advice": "不投。域是零。"}}
        for name, job in (("平铺", flat), ("嵌套", nested)):
            with self.subTest(shape=name):
                self.assertNotIn("复制开场白", bd.job_next_step(job)["text"])


class TheExporterCarriesIt(unittest.TestCase):

    def test_the_field_is_exported(self):
        src = (ROOT / "tools" / "export_web_data.py").read_text(encoding="utf-8")
        self.assertIn('job["advice"]', src,
                      "导出里没有这个字段 —— 屏幕上就只剩判词那一半")

    def test_the_panel_declares_it(self):
        ts = (ROOT / "web" / "src" / "types.ts").read_text(encoding="utf-8")
        self.assertIn("advice?: string;", ts)

    def test_the_two_word_lists_agree(self):
        """判「什么算不投」的词表有两份（Python 一份、TSX 一份），必须相等。

        分叉的样子：后端不催了，前端不描红 —— 或者反过来。
        """
        tsx = (ROOT / "web" / "src" / "components" / "JobReadout.tsx"
               ).read_text(encoding="utf-8")
        m = re.search(r"ADVISES_AGAINST\s*=\s*/\^[^/]*?\((.+?)\)/", tsx)
        self.assertIsNotNone(m, "前端那份词表找不到了")
        self.assertEqual(set(m.group(1).split("|")), set(bd._AGAINST),
                         "两处「什么算不投」的词表分叉了")


class ItHoldsOnTheRealData(unittest.TestCase):
    """现算：这台机器上的真实快照里，没有一个「说别投却还在催投」的岗。"""

    def test_no_job_is_both_told_no_and_nagged(self):
        p = ROOT / "web" / "public" / "data.json"
        if not p.is_file():
            self.skipTest("还没导出过面板数据")
        jobs = json.loads(p.read_text(encoding="utf-8")).get("jobs") or []
        against = [j for j in jobs
                   if bd._advises_against(j)]
        if not against:
            self.skipTest("这份数据里没有说「别投」的建议 —— 没什么可验的")
        bad = [j.get("title") for j in against
               if "复制开场白" in ((j.get("nextStep") or {}).get("text") or "")]
        self.assertEqual(
            bad, [], f"这几个岗的评估说别投，页面还在催他去投：{bad}")


if __name__ == "__main__":
    unittest.main()
