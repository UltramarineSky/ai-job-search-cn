# -*- coding: utf-8 -*-
"""面板的 `Job` 类型里有个 `ticker`（股票代码）—— 全仓没有任何东西产出它。

三处都齐了，只差最要紧的那一处：

    web/src/types.ts             `ticker?: string;`
    web/src/components/JobReadout.tsx  `{job.ticker && (…<code>{job.ticker}</code>…)}`
    web/src/data/sample.ts       `ticker: "0XXXX.HK"`
    tools/export_web_data.py     ——**一次都没出现**

于是那个渲染分支在真实数据上**永远走不到**，而演示数据里它是有的。
`sample.ts` 自己的说明写着这份数据是干什么用的：

> **但边界情况是真的** —— 版面撑不撑得住取决于这些形状，所以每一种都留了一条。

一个不可能出现的形状不是边界情况，是虚构。而这份演示正是**新用户第一次打开
面板**时看到的东西（`load.ts`：读不到 `data.json` 就回退到它），
同一份说明还写着「**演示数据必须自己承认自己是演示数据**」——
一个没有后端的字段，等于让演示替工具吹了一个它没有的能力。

没有把它做出来，是删掉：抓取侧没有任何渠道给股票代码（猎聘的接口没有这个字段），
而「上市没上市」这个真正有用的信号已经由 `compStage` 承担（「港股上市」「A轮」…，
2638 个岗里 1526 个有值）。

## 这一条盯的是这一类

上一条守卫（`test_the_panel_reads_keys_that_are_written`）管的是**读**：
导出方读的键，得有东西真的写它（`experience` 读成了不存在的键）。
这一条是它的镜像，管**声明**：面板类型里声明的字段，得有东西真的产出它。
两条合起来，「界面上永远空着的一栏」这一类才算堵住。

判据故意放得松（**只要求字段名在导出方里作为带引号的字符串出现过**）：
产出的写法有好几种（`"x": …` 字面量、`job["x"] = …`、`j["x"]`、`**{…}` 展开），
认死一种会把 `funnels` / `duplicates` / `dupOf` / `nextStatuses` 全误报成孤儿
（第一版就是这么误报了 4 个）。松判据仍然抓得住 `ticker` —— 它是**零次**。
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TYPES = (ROOT / "web" / "src" / "types.ts").read_text(encoding="utf-8")
EXPORT = (ROOT / "tools" / "export_web_data.py").read_text(encoding="utf-8")


def job_fields() -> list:
    """`interface Job` 的**顶层**字段名。

    **必须按深度只取顶层。** 里面有嵌套对象字面量
    （`annual: { low; high; estimated }`、`blocked?: { 环节; 需要 }`），
    整段扫会把 `low` / `estimated` / `环节` 当成顶层字段 ——
    第一版就是这么多报了 6 个。
    """
    m = re.search(r"export interface Job\s*\{", TYPES)
    assert m, "types.ts 里找不到 `export interface Job`"
    i = m.end()
    depth, k = 1, i
    while depth:
        if TYPES[k] == "{":
            depth += 1
        elif TYPES[k] == "}":
            depth -= 1
        k += 1
    out, depth = [], 0
    for line in TYPES[i:k - 1].splitlines():
        mm = re.match(r"(\w+)\??\s*:", line.strip())
        if depth == 0 and mm:
            out.append(mm.group(1))
        depth += (line.count("{") + line.count("[")
                  - line.count("}") - line.count("]"))
    return out


def orphans() -> list:
    return [f for f in job_fields()
            if not re.search(rf"""["']{re.escape(f)}["']""", EXPORT)]


class EveryDeclaredFieldHasAProducer(unittest.TestCase):
    def test_no_field_is_declared_without_one(self):
        got = orphans()
        self.assertEqual(got, [],
                         f"`Job` 里声明了导出方从不产出的字段：{got} —— "
                         f"渲染它的分支在真实数据上永远走不到")

    def test_the_scan_actually_finds_the_fields(self):
        """扫空了会让上一条永远绿。切错括号、正则写错都是这么静默失效的。"""
        fs = job_fields()
        self.assertGreaterEqual(len(fs), 30, f"只扫到 {len(fs)} 个字段，切错了")
        for f in ("title", "company", "salary", "experience", "viaHeadhunter"):
            with self.subTest(f=f):
                self.assertIn(f, fs)

    def test_it_takes_only_top_level_fields(self):
        """嵌套对象里的字段名不算 —— 它们本来就不该在导出方顶层出现。"""
        fs = job_fields()
        for f in ("low", "high", "estimated", "环节", "需要"):
            with self.subTest(f=f):
                self.assertNotIn(f, fs, f"`{f}` 是嵌套字段，被当成顶层了")

    def test_the_loose_rule_still_catches_a_real_orphan(self):
        """判据放松到「出现过就算」，得确认它没松到什么都抓不住。"""
        self.assertNotIn("ticker", job_fields(), "`ticker` 又回来了")
        self.assertNotRegex(EXPORT, r"""["']ticker["']""")

    def test_the_loose_rule_is_why_it_is_loose(self):
        """这几个字段的产出写法各不相同，认死一种就会误报它们。"""
        for f in ("funnels", "duplicates", "dupOf", "nextStatuses"):
            with self.subTest(f=f):
                self.assertIn(f, job_fields())
                self.assertRegex(EXPORT, rf"""["']{f}["']""")


class TheDeadBranchIsGone(unittest.TestCase):
    """字段删了，渲染它的分支和演示里那一条也要跟着走，否则下次照着它又加回来。"""

    def test_the_readout_no_longer_renders_it(self):
        self.assertNotIn("ticker", (ROOT / "web" / "src" / "components"
                                    / "JobReadout.tsx").read_text(
            encoding="utf-8"))

    def test_the_demo_no_longer_claims_it(self):
        self.assertNotIn("ticker", (ROOT / "web" / "src" / "data"
                                    / "sample.ts").read_text(encoding="utf-8"))

    def test_the_readout_still_shows_the_company_line(self):
        """删的是公司名后面那一段。整行别一起带走了。"""
        src = (ROOT / "web" / "src" / "components"
               / "JobReadout.tsx").read_text(encoding="utf-8")
        i = src.index('className="readout-meta"')
        seg = src[i:i + 500]
        self.assertIn("{job.company}", seg)
        self.assertIn("猎头代招", seg, "猎头/直招那一句被带掉了")
        self.assertIn("没判是猎头还是直招", seg,
                      "「没判过」那一支被带掉了 —— 它防的是把没判过的印成直招")


class TheDemoStillEarnsItsKeep(unittest.TestCase):
    """演示数据的用处是**撑版面**。删一个字段不能把它那条说明也架空。"""

    SAMPLE = (ROOT / "web" / "src" / "data" / "sample.ts")

    def test_it_still_says_the_shapes_are_real(self):
        self.assertIn("但边界情况是真的",
                      self.SAMPLE.read_text(encoding="utf-8"))

    def test_it_still_admits_it_is_a_demo(self):
        self.assertIn("演示数据必须自己承认自己是演示数据",
                      (ROOT / "web" / "src" / "data"
                       / "load.ts").read_text(encoding="utf-8"))

    def test_the_row_it_was_on_survives(self):
        """那条演示岗还在 —— 删的是它的一个字段，不是整条。"""
        self.assertIn('id: "j-solution-lead"',
                      self.SAMPLE.read_text(encoding="utf-8"))


class TheSignalItWouldHaveCarriedIsElsewhere(unittest.TestCase):
    """删之前先确认没删掉真需求：「上市没上市」由 `compStage` 承担。"""

    def test_the_scraper_stores_the_funding_stage(self):
        self.assertRegex(
            (ROOT / "workflows" / "job-scrape.md").read_text(encoding="utf-8"),
            r'"compStage"')

    def test_it_reaches_the_screen_as_words(self):
        """它不是结构化字段，但会在评估正文里出现 —— 显示层把内部词换成人话。

        **2026-08-23 起换的那个词不再是「融资阶段」。** 实测那个字段里混着三条轴
        （融资阶段 / 上市板块 / 所有权性质：民营 116、不需要融资 87、国企合资外资
        共 63），译成「融资阶段」会在屏幕上写出「融资阶段：国企」。这里只钉
        **有没有这条换词、换出来的是不是人话**，具体措辞归
        `test_comp_stage_is_not_one_axis.py` 管，两处不重复钉同一个字符串。
        """
        self.assertRegex(EXPORT, r'\("compStage", "[^"A-Za-z]+", ""\)')


if __name__ == "__main__":
    unittest.main()
