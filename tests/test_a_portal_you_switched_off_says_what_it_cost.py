# -*- coding: utf-8 -*-
"""关掉一家招聘网站，面板只是把那一行变灰 —— 而变灰把「你漏了什么」压下去了。

`Portals.tsx` 开头列了这一块存在的两条理由，第一条就是：

> **某个网站根本没在抓。** 取消勾选的整家跳过，而词表算出来的「最值钱的格子」
> 可能恰恰在那几家 —— 用户不知道自己漏了什么。

而现在「关掉」在屏幕上的全部表现是：勾选框空着、行加一个 `is-off` 变灰。
**变灰的恰恰是那一行的数字** —— 也就是判断「关掉值不值」唯一的依据。

实测活动用户 2026-08-24，四家的职位描述覆盖：

    猎聘      1478/2232 = 66%   ← 关着
    BOSS         1/126 = 0.8%   ← 开着
    智联          4/86 = 5%     ← 开着
    前程无忧      0/194 = 0%     ← 开着

**他关掉的是四家里唯一打得出分的那家。** 而覆盖率决定的正是「抓回来的岗能不能
打分」（同这一行里已有的 `读不到职位详情` 那条）—— 现在抓回来的岗多半评不了，
屏幕上却只有一个灰掉的勾选框。

## 为什么比覆盖率，不比岗位数

比岗位数会把「抓得多」误当成「捞得多」—— 那正是各家 `note` 里已经在提醒的
反面（猎聘那条的原话：「量最大……但一百个岗里只有五个能投——抓得多不等于
捞得多」）。覆盖率问的是另一件事：**抓回来的东西能不能进流水线**。

## 只在真的有代价时才出

判据是「这家的覆盖比**在用的每一家都高**」。在用的里面有更高的，那关掉它就
没有这一层代价，一个字都不该多说。
"""
import json
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = (ROOT / "web" / "src" / "components"
       / "Portals.tsx").read_text(encoding="utf-8")


def flat(s: str) -> str:
    s = " ".join(re.sub(r"^\s*>\s?", "", s, flags=re.M).split())
    return re.sub(r"(?<=[一-鿿，。；：、（）「」])"
                  r" +(?=[一-鿿，。；：、（）「」])", "", s)


def block() -> str:
    i = SRC.index("**关掉的那家，要说出关掉的代价。**")
    return SRC[i:SRC.index("{/* 拿不到 JD 的渠道要单独说", i)]


class TheNoteExists(unittest.TestCase):
    def test_it_is_rendered(self):
        self.assertIn("关着的这家职位描述覆盖最高", SRC)

    def test_it_only_fires_when_switched_off(self):
        # 2026-09-02 锚点跟着代码挪：勾选框改成乐观更新之后，显示值一律走
        # `shownOn(p)`（本地覆盖优先，props 追上来退位）。判的还是同一件事，
        # 只是那个值不再直接读 props —— 见 `Portals.tsx` 的 `ovOn` 说明。
        self.assertIn("if (shownOn(p) || !p.jobs) return null;", block())

    def test_it_compares_against_the_enabled_ones(self):
        seg = block()
        self.assertIn("portals.filter((q) => shownOn(q) && q.jobs)", seg)
        self.assertIn("Math.max(", seg)

    def test_it_stays_quiet_when_there_is_no_cost(self):
        """在用的里面有覆盖更高的 —— 那关掉它不损失打分能力，别多话。"""
        self.assertIn("if (cov(p) <= bestOn) return null;", block())

    def test_the_sentence_is_not_split_across_lines(self):
        """JSX 会把换行加缩进折成一个空格，中文里那个空格看得见。

        实测就栽在这儿（`test_css_and_cjk_text` 顶红）。写成模板字符串，
        断行的诱惑就没了。"""
        self.assertIn("{`关着的这家职位描述覆盖最高（", block())

    def test_it_shows_both_numbers(self):
        """只说「最高」不够 —— 差多少才是他判断的依据。"""
        seg = block()
        self.assertIn("Math.round(cov(p) * 100)", seg)
        self.assertIn("Math.round(bestOn * 100)", seg)

    def test_it_explains_the_consequence_on_hover(self):
        seg = block()
        self.assertIn("停在「待评」", seg)
        self.assertIn("打不出分", seg)

    def test_a_zero_job_portal_is_skipped(self):
        """还没抓过的那家覆盖率是 0/0 —— 拿它比毫无意义。"""
        self.assertIn("!p.jobs", block())


class TheReasonIsRecorded(unittest.TestCase):
    def test_it_names_the_purpose_it_serves(self):
        seg = flat(block())
        self.assertRegex(seg, r"用户不知道 自己漏了什么|用户不知道自己漏了什么")

    def test_it_says_why_greying_out_is_the_problem(self):
        """「变灰」听起来无害 —— 要说清它压掉的正是判断依据。"""
        self.assertRegex(flat(block()), r"变灰恰恰把「漏了什么」那部分信息压下去了")

    def test_it_says_why_coverage_and_not_job_count(self):
        seg = flat(block())
        self.assertRegex(seg, r"比岗位数会把「抓得多」误当成「捞得多」")

    def test_it_carries_the_measurement(self):
        seg = flat(block())
        self.assertRegex(seg, r"关着的那家覆盖 66%，而在用的三家是 0\.8% / 5% / 0%")
        self.assertIn("2026-08-24", seg)


class TheSurroundingRowIsIntact(unittest.TestCase):
    """这一行原有的几件事都不能被这次插入挤掉。"""

    def test_the_jd_coverage_line_survives(self):
        self.assertIn("职位描述存了 {Math.round((p.withJd / p.jobs) * 100)}%", SRC)

    def test_the_no_detail_warning_survives(self):
        self.assertIn("读不到职位详情", SRC)

    def test_the_blocked_marker_survives(self):
        self.assertIn("is-blocked", SRC)

    def test_the_switch_is_still_the_only_switch(self):
        seg = SRC[SRC.index("export function Portals("):]
        self.assertIn("checked={shownOn(p)}", seg)
        self.assertIn("onChange={() => void toggle(p)}", seg)

    def test_the_two_purposes_are_still_documented(self):
        head = flat(SRC[:SRC.index("export function Portals(")])
        self.assertRegex(head, r"某个网站根本没在抓")
        self.assertRegex(head, r"某个网站抓得到岗、却打不出分")


class TheSignalItLeansOnIsReal(unittest.TestCase):
    """有导出时验一次：真的存在「关着的那家覆盖最高」这个局面。"""

    def _portals(self):
        p = ROOT / "web" / "public" / "data.json"
        if not p.is_file():
            self.skipTest("还没导出过")
        ps = json.loads(p.read_text(encoding="utf-8")).get("portals") or []
        if len(ps) < 2:
            self.skipTest("平台太少，比不出来")
        return ps

    @staticmethod
    def _cov(q):
        return (q.get("withJd") or 0) / (q.get("jobs") or 1)

    def test_coverage_really_differs_across_portals(self):
        """四家覆盖都一样的话，这条规则永远不出现，也就白写了。"""
        ps = [q for q in self._portals() if q.get("jobs")]
        covs = {round(self._cov(q), 2) for q in ps}
        self.assertGreater(len(covs), 1,
                           "各家职位描述覆盖没有差别 —— 这条判据失去意义")

    def test_the_note_would_fire_on_this_corpus(self):
        """真出现了就该出现。这条哪天不成立了，说明他把那家打开了 —— 好事，
        但那时这条守卫要改成「不再需要」，别让它悄悄空跑。"""
        ps = self._portals()
        off = [q for q in ps if not q.get("enabled") and q.get("jobs")]
        if not off:
            self.skipTest("四家都开着 —— 没有可比的局面")
        best_on = max([self._cov(q) for q in ps
                       if q.get("enabled") and q.get("jobs")], default=0)
        self.assertTrue(any(self._cov(q) > best_on for q in off),
                        f"关着的那几家覆盖都不比在用的高 —— 这条不会出现，"
                        f"实测记录（关着 66% vs 在用最高 5%）已经过期")


if __name__ == "__main__":
    unittest.main()
