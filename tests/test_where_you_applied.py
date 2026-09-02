# -*- coding: utf-8 -*-
"""「投了这么多没回音」还有一种解释：**投的地方不对**。

面板的诊断链原来只讲**怎么到达**——一半没到用人方手里（猎头代招）、
三个网站都是 0、换一种到达方式（内推）。缺的是**投给了谁**这一层。

实测活动用户 2026-08-22，投出去的 78 份可回读评估：

    主场（能力够 + 行业对口）        17
    选岗问题（能力够、行业对不上）    49   ← 63%
    可以靠学                          5
    两样都差                          7

对「85 个 0 回音」来说这是最直接的一条解释，而且给的动作最具体：
**下一批往那 17 个所在的方向投**。此前它只活在 `gap_split.py --applied` 里，
由 `/job-upskill` 调用 —— 而那条命令他一次都没跑过。

判据与分界一律走 `gap_split`（`STACK_OK` / `DOMAIN_OK`），**连数字都不抄**：
它们取自框架各维自身的分档，而 2026-08-23 专业能力那条已经从 70 改成 60。
"""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import export_web_data as X  # noqa: E402
import gap_split as gs  # noqa: E402

PANEL = (ROOT / "web" / "src" / "components"
         / "OutcomeStats.tsx").read_text(encoding="utf-8")


def _applied_fit_code() -> str:
    """四格那套算法的**代码**部分，剥掉 docstring。

    两件事要注意，各栽过一次：

    1. 下面两条查的是「有没有抄」，而 docstring 里恰恰要解释「为什么不抄」——
       连着注释一起扫，等于禁止把理由写下来。
    2. 分格那几行搬进了 `_fit_of`（还没投的那批要走同一份），所以
       **两个函数一起扫** —— 只盯一个的话，代码一搬这条检查就静默失效。
    """
    src = (ROOT / "tools" / "export_web_data.py").read_text(encoding="utf-8")
    out = []
    for name in ("def applied_fit(", "def _fit_of("):
        seg = src[src.index(name):]
        seg = seg[:seg.index("\ndef ", 1)]
        body = seg.split('"""')
        out.append(body[0] + "".join(body[2:]) if len(body) > 2 else seg)
    return "\n".join(out)


def _job(url, applied=True):
    return {"url": url, "applied": {"status": "applied"} if applied else None}


def _entry(url, stack, domain):
    return {"url": url, "status": "ranked",
            "rank_breakdown": {"四维": f"专业能力 {stack}×0.6+业务域 {domain}×0.4"}}


class TheSplitComesFromGapSplit(unittest.TestCase):
    def test_the_thresholds_are_not_copied(self):
        """分界只有一个出处。抄一遍就等着两处哪天不一样。"""
        seg = _applied_fit_code()
        self.assertNotRegex(seg, r"\b70\b|\b60\b", "分界被抄进了 applied_fit")
        self.assertIn("gs.quadrant", seg, "没走 gap_split 的分格函数")

    def test_it_reads_the_raw_entry_not_the_exported_note(self):
        """导出侧那条 note 已被 `strip_weights` 剥掉 `×0.6`，拿它去配必然全落空。"""
        seg = _applied_fit_code()
        self.assertIn("gs.read_pair", seg, "没用 gap_split 的原式解析")
        self.assertNotIn("dimensions", seg, "又去读导出后的 dimensions 了")


class OnlyTheAppliedBatchCounts(unittest.TestCase):
    def test_jobs_never_applied_to_are_excluded(self):
        """全库那份会被宽泛抓取的噪音淹掉（实测 593 份里「两样都差」占 372）。"""
        jobs = [_job("a"), _job("b", applied=False)]
        seen = {"1": _entry("a", 80, 80), "2": _entry("b", 10, 10)}
        seen.update({str(i): _entry(f"x{i}", 80, 80) for i in range(3, 15)})
        jobs += [_job(f"x{i}") for i in range(3, 15)]
        out = X.applied_fit(jobs, seen)
        self.assertEqual(out["off"], 0, "把没投过的岗也算进来了")

    def test_a_tiny_sample_says_nothing(self):
        """10 份以下说不出话来 —— 报一个 3/5 的比例只会误导。"""
        jobs = [_job(f"u{i}") for i in range(4)]
        seen = {str(i): _entry(f"u{i}", 80, 30) for i in range(4)}
        self.assertIsNone(X.applied_fit(jobs, seen))

    def test_unreadable_scores_are_skipped_not_guessed(self):
        jobs = [_job(f"u{i}") for i in range(12)]
        seen = {str(i): {"url": f"u{i}", "status": "ranked"} for i in range(12)}
        self.assertIsNone(X.applied_fit(jobs, seen), "读不出分数却给了结论")

    def test_the_quadrants_match_gap_split(self):
        """同一批数据，两边必须分出同一个格 —— 否则面板和命令行各说各的。"""
        jobs = [_job(f"u{i}") for i in range(12)]
        seen = {str(i): _entry(f"u{i}", 80, 30) for i in range(12)}
        out = X.applied_fit(jobs, seen)
        self.assertEqual(out["pick"], 12)
        self.assertEqual(gs.quadrant(80, 30), gs.PICK)


class TheAdviceChecksWhetherItIsExecutable(unittest.TestCase):
    """「往主场方向投」得先问一句：手上挑得出来吗。

    实测 2026-08-22：还没投的 227 个可投岗里主场只有 11 个（分数 54-59，
    一个都没进「值得投」）。那句建议真正的意思是**去改搜索词多抓这类**，
    不是「从现有名单里挑」—— 一个是今晚能做的事，一个是明天才有的结果。
    """

    def test_the_open_batch_is_split_too(self):
        jobs = ([_job(f"a{i}") for i in range(12)]
                + [{"url": f"o{i}", "verdict": "可以考虑"} for i in range(12)])
        seen = {f"a{i}": _entry(f"a{i}", 80, 30) for i in range(12)}
        seen.update({f"o{i}": _entry(f"o{i}", 80, 80) for i in range(12)})
        out = X.applied_fit(jobs, seen)
        self.assertIsNotNone(out.get("open"), "没有给还没投的那批分格")
        self.assertEqual(out["open"]["home"], 12)

    def test_applied_jobs_are_not_in_the_open_batch(self):
        """投过的岗不算「手上还有的」——重复计数会把「不够挑」说成「够挑」。"""
        jobs = [dict(_job(f"a{i}"), verdict="可以考虑") for i in range(12)]
        seen = {f"a{i}": _entry(f"a{i}", 80, 80) for i in range(12)}
        self.assertIsNone(X.applied_fit(jobs, seen).get("open"),
                          "投过的岗被算进了还没投的那批")

    def test_the_panel_switches_advice_on_whether_there_is_anything_to_pick(self):
        i = PANEL.index("投的地方对不对")
        seg = PANEL[i:i + 2600]
        self.assertIn("open.home * 10 < s.appliedFit.open.total", seg,
                      "没有「手上够不够挑」这道判断")
        self.assertIn("--section search", seg, "不够挑时没给出改搜索词的命令")
        self.assertIn("/job-scrape", seg, "改完搜索词之后那一步没说")


class ThePanelSaysWhatToDoAboutIt(unittest.TestCase):
    def test_the_band_only_shows_when_it_is_the_majority(self):
        """少数几个跨行业投递是正常试探，不值得单开一行。"""
        self.assertIn("appliedFit.pick * 2 > s.appliedFit.total", PANEL,
                      "没有过半才说的门槛")

    def test_it_names_the_action_and_the_command(self):
        #: **切到那一段结束，别按字符数切。** 这一块后来加了几段长注释
        #: （给两个分母各写了口径），固定 1400 字符当场把要验的命令挤出窗口。
        i = PANEL.index("投的地方对不对")
        j = PANEL.find("投在哪个网站", i)
        seg = PANEL[i:j if j > 0 else i + 4000]
        self.assertRegex(seg, r"下一批先发它们|想多抓这类",
                         "没给出下一步该做什么")
        self.assertIn("/job-upskill --applied", seg, "没给出看明细的命令")

    def test_it_does_not_blame_the_resume(self):
        """这一条的要点就是「不是简历的问题」——说反了就把人送去改简历。"""
        i = PANEL.index("投的地方对不对")
        seg = PANEL[i:i + 1400]
        self.assertRegex(seg, r"不是简历写得不好|不是简历不行",
                         "没说清这一条和简历无关")

    def test_the_command_form_exists(self):
        up = (ROOT / "workflows" / "job-upskill.md").read_text(encoding="utf-8")
        self.assertRegex(up, r"`/job-upskill --applied`",
                         "面板印的敲法在 job-upskill 里查无此形")


if __name__ == "__main__":
    unittest.main()
