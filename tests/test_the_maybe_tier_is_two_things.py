# -*- coding: utf-8 -*-
"""「可以考虑」这一档里混着两种完全不同的东西。

    读过 JD 的（80 个）：评估看完正文，结论是「先问清楚再决定投不投」
    没读 JD 的（142 个）：只看了标题和卡片字段，分是粗筛给的

后者**不是一个关于这个岗的结论**，是关于工具自己覆盖到哪儿的陈述 ——
和这个仓库反复立的那条「『没查』与『查过没有』是两件事」同一族。

数据里本来分得开：判词就是「粗筛：可以考虑」，实测 141/142 都带这个前缀。
是 `plainVerdict` 把前缀剥掉了（那本身没错，「粗筛」是内部词）。
逐行也有「没读 JD」那枚章兜着。**漏的是标题上那个数** ——
实测 2026-08-22 写着「还有 222 个『可以考虑』的」，而其中 142 个工具没看过正文。
那个数是他决定「要不要点开」时唯一读到的东西。
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "web" / "src" / "App.tsx").read_text(encoding="utf-8")
#: 折叠标题那一段（含它上面那块注释）。**不要拿 `APP.index("还没读过 JD")` 定位**
#: ——那个词先出现在 `nRestRaw` 声明处的注释里，扫到的是另一段代码。
#: 第一版就栽在这儿：两条断言都在错的区域上求值。
_LABEL = APP[APP.index("// **「可以考虑」这一档里混着两种"):][:2600]
SHORTLIST = (ROOT / "web" / "src" / "components"
             / "Shortlist.tsx").read_text(encoding="utf-8")


class TheHeaderSaysHowManyWereNeverRead(unittest.TestCase):
    def test_the_count_exists(self):
        self.assertIn("nRestRaw", APP, "标题上没有「还没读过 JD」那个数")
        self.assertIn("还没读过 JD", APP, "算了没显示")

    def test_it_uses_the_same_field_as_the_per_row_chip(self):
        """两处判据必须同源 —— 否则标题说 142、点开数出来是别的数。"""
        m = re.search(r"nRestRaw = restList\.filter\(\(j\) => ([^)]+)\)", APP)
        self.assertIsNotNone(m, "找不到 nRestRaw 的算法")
        self.assertIn("evaluated", m.group(1), "标题用的不是 `evaluated`")
        self.assertIn("!job.evaluated", SHORTLIST, "逐行那枚章不再看 evaluated 了")

    def test_it_stays_quiet_when_everything_was_read(self):
        """全读过时不该多一句废话 —— 这一族提示只在有东西可提醒时出现。"""
        self.assertLess(_LABEL.index("nRestRaw > 0"),
                        _LABEL.index("还没读过 JD"), "没有「有才说」的门槛")

    def test_the_score_range_is_still_there(self):
        """原来那半句（分数区间）不许被挤掉 —— 它回答的是另一个问题。"""
        self.assertIn("restScores", APP)
        self.assertRegex(APP, r"分 \$\{Math\.min\(\.\.\.restScores\)\}")


class TheDistinctionIsRealInTheData(unittest.TestCase):
    def test_the_coarse_prefix_is_what_carries_it(self):
        """判词里的「粗筛：」前缀是这个区分的载体：**得有人剥，且只有一个人剥。**

        这条原来钉的是「`App.tsx` 里有那个正则」—— 钉的是实现**位置**，不是行为。
        而位置恰恰是该变的那一样：2026-08-31 把 `App.tsx` 私有的 `plainV`（同一个
        正则、多一个 `.trim()`）并进 `Shortlist.tsx` 的 `plainVerdict`之后它就红了，
        而「前缀被剥掉」这件事一点没少。**守卫钉实现位置，等于把收重复定义本身判成违规。**

        那两份实现当时已经飘了：`plainV` 带 `.trim()`，`plainVerdict`不带 —— 而后者
        正被用在 `plainVerdict(j.verdict) === "可以考虑"` 这种等值比较上，更需要它。
        「整棵 web/src 只许有一份实现」由 `test_web_copy` 那条扫全树的把着，这里只管
        **吃判词的两个判断都先过它** —— 漏掉哪一个，带前缀的判词就落进错的档。
        """
        self.assertRegex(SHORTLIST, r"replace\(/\^粗筛\[：:\]", "剥前缀那一处不见了")
        self.assertNotRegex(APP, r"replace\(/\^粗筛\[：:\]",
                            "App.tsx 又自己写了一份剥法——正本在 plainVerdict")
        for name in ("canSell", "isOut"):
            with self.subTest(name):
                i = APP.index("const " + name + " = ")
                self.assertIn("plainVerdict", APP[i:i + 300],
                              name + " 没先剥「粗筛：」前缀")

    def test_the_reason_is_written_down_next_to_the_code(self):
        """这条规矩以前反复丢，注释里要说清它属于哪一族。"""
        self.assertRegex(_LABEL, r"没查|覆盖到哪",
                         "没写清这一半是「还没看过」而不是结论")


class AnEmptyAskListStillSaysSomething(unittest.TestCase):
    """这一档的定义是「先问清楚再决定投不投」，而清单空着时面板什么都不显示。

    那一块 `{(job.askBefore?.length ?? 0) > 0 && (…)}` 只在非空时渲染。空着时
    屏幕上只剩一段可复制的开场白 —— 用户分不清是「没什么可问的」还是
    「深评根本没写」。

    实测 2026-08-31：活的「可以考虑」里 56 个已备开场白，其中 **47 个（84%）**
    这一块是空的，而这 47 个**全部深评过** —— 不是「还没评到」，是评了没写。
    审计一直在报这件事（「『可以考虑』的深评没写要问什么」），但那是事后的
    一份清单；这里是他要复制那段话的时刻。

    **只对这一档提示。** `值得投` 本来就不必等答案再投（那一块自己的说明写着
    「这几条不必等答案再投」），对它们喊一句「缺清单」是一条永远为真的噪音 ——
    本仓库为这个形状删过东西。
    """

    SHEET = (ROOT / "web" / "src" / "components"
             / "JobReadout.tsx").read_text(encoding="utf-8")

    def test_the_empty_case_is_rendered(self):
        self.assertIn("(job.askBefore?.length ?? 0) === 0", self.SHEET,
                      "空清单那一支没渲染 —— 缺了和没什么可问长得一模一样")

    def test_it_is_scoped_to_this_tier(self):
        """别的档不许提示 —— 一条永远为真的提醒等于没有提醒。"""
        i = self.SHEET.index("(job.askBefore?.length ?? 0) === 0")
        seg = self.SHEET[i:i + 200]
        self.assertIn('plainVerdict(job.verdict) === "可以考虑"', seg,
                      "没限定在「可以考虑」这一档")

    def test_it_gives_the_command(self):
        """`AGENTS.md`「每一处引导都要写出该敲的命令」。"""
        i = self.SHEET.index("(job.askBefore?.length ?? 0) === 0")
        self.assertIn("/job-apply", self.SHEET[i:i + 700],
                      "说了缺，没说该敲什么")

    def test_the_non_empty_branch_survives(self):
        """控制用例：原来那一块不能被顺手改没。"""
        self.assertIn("(job.askBefore?.length ?? 0) > 0", self.SHEET)
        self.assertIn("投之前先问清这几条", self.SHEET)


if __name__ == "__main__":
    unittest.main()
