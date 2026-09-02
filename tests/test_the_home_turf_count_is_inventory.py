# -*- coding: utf-8 -*-
"""「行业对口 107 个岗」是历史统计，而紧挨着它的建议是库存指令。

那一节（「市场怎么读你的简历」）末尾写着：

    专业能力中位数 55 · 行业经验中位数 40——差距在后者，
    而它主要靠**选对岗**解决，不是靠补课。

「选对岗」要人去挑，那就得说清还有多少可挑。可 `count` 把已投的、他点掉的、
已下线的、判词出局的全算在里面 —— 它回答的是「市场里有多大一块对得上你」，
放在这一节里没错，但它不是库存。实测活动用户 2026-08-23：

    行业对口（有完整评分的 687 个里）   107
      其中已经投出去了                  22
      点掉 / 下线 / 判词出局             36
      **现在还能投的**                  49   ← 差不多是它的一半

同一族的前科就在上一次：`topReady.ready` 那个「前 20 里 0 个备好材料」的局部 0
盖住了全局 62 个备好没发的。**两个数要在同一句里说完。**

而 49 挑着投很快见底，所以这一行还得给出补货的命令 —— 补这一类的货靠改搜索词，
不是多抓一轮（面板通例：每处引导都写出命令）。
"""
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import export_web_data as X  # noqa: E402

RREAD = (ROOT / "web" / "src" / "components"
         / "ResumeRead.tsx").read_text(encoding="utf-8")
TYPES = (ROOT / "web" / "src" / "types.ts").read_text(encoding="utf-8")
SRC = (ROOT / "tools" / "export_web_data.py").read_text(encoding="utf-8")


def _seg():
    i = SRC.index("def resume_insight(")
    return SRC[i:SRC.index("\ndef ", i + 10)]


class TheProducerCountsWhatIsStillOpen(unittest.TestCase):
    def test_the_field_exists(self):
        self.assertIn('"open": still_open', _seg(), "没有「还能投的」这个数")

    #: 造 12 条最小条目（`resume_insight` 要求至少 10 条才开口）。
    #: `rank_breakdown.专业能力/业务领域` 是 `gap_split.read_pair` 认的第二种格式。
    @staticmethod
    def _seen(n=12, **over):
        out = {}
        for i in range(n):
            e = {"url": f"https://x/{i}", "status": "ranked",
                 "rank_verdict": "值得投",
                 "rank_breakdown": {"专业能力": 80, "业务领域": 70}}
            out[str(i)] = e
        for k, v in over.items():
            out["0"][k] = v
        return out

    def _open(self, seen, applied=None):
        r = X.resume_insight("u", seen, ROOT / "nowhere", applied_urls=applied)
        self.assertIsNotNone(r, "样本不够，这条测不到东西")
        return r["sweetSpot"]["open"], r["sweetSpot"]["count"]

    def test_all_open_when_nothing_is_dead(self):
        self.assertEqual(self._open(self._seen()), (12, 12))

    def test_an_applied_one_is_not_open(self):
        """**行为断言，不是查字符串。** 只查 `applied_urls` 出现过没有，
        把那个判断整条删掉照样绿 —— 变异实测漏过一次。"""
        n, c = self._open(self._seen(), applied={"//x/0"})
        self.assertEqual((n, c), (11, 12), "已投的还被算成「还能投」")

    def test_a_dead_state_is_not_open(self):
        for field, val in (("status", "expired"), ("status", "skipped"),
                           ("rank_verdict", "不建议")):
            with self.subTest(f"{field}={val}"):
                n, c = self._open(self._seen(**{field: val}))
                self.assertEqual((n, c), (11, 12), f"{val} 还被算成「还能投」")

    def test_the_verdict_test_uses_the_whitelist(self):
        """**不许在这里另写一遍「哪些判词还能投」。** 白名单正本是
        `is_sellable`（黑名单反推两天里漏进来两次，那段历史写在它自己的
        docstring 里）。"""
        seg = _seg()
        self.assertIn("is_sellable(", seg, "没用白名单正本")
        i = seg.index("still_open += 1")
        self.assertNotIn("SELLABLE_VERDICTS", seg[max(0, i - 500):i],
                         "又把词表内联了一份")

    def test_the_caller_passes_what_was_applied(self):
        """不传的话它默认空集，`open` 会把已投的也算成还能投 —— 静默偏大。"""
        i = SRC.index("insight = resume_insight(")
        seg = SRC[i:i + 400]
        self.assertIn("applied_urls=", seg, "调用点没传已投链接")
        # 传了个空集和没传一样。要求它**真的从台账行里取**。
        self.assertIn("trows", seg, "传的不是台账里那批链接")
        self.assertIn("norm_url", seg, "没剥协议 —— http/https 会对不上，栽过")

    def test_open_never_exceeds_count(self):
        data = ROOT / "web" / "public" / "data.json"
        if not data.is_file():
            self.skipTest("还没导出过面板数据")
        ss = json.loads(data.read_text(encoding="utf-8")).get(
            "resumeInsight", {}).get("sweetSpot")
        if not ss or "open" not in ss:
            self.skipTest("这份快照里没有这个字段")
        self.assertLessEqual(ss["open"], ss["count"],
                             "还能投的比总数还多，口径反了")


class ThePanelSaysBothInOneBreath(unittest.TestCase):
    def test_the_line_exists(self):
        self.assertIn("rread-open", RREAD, "没有「还能投的 N 个」那一行")

    def test_it_prints_both_numbers(self):
        i = RREAD.index("rread-open")
        seg = RREAD[i:i + 900]
        self.assertIn("ss.count", seg, "只说还能投的，没说总数")
        self.assertIn("ss.open", seg, "没印还能投的那个数")

    def test_it_says_where_the_rest_went(self):
        """不解释的话，107 和 49 同框看着就是矛盾的。"""
        i = RREAD.index("rread-open")
        self.assertRegex(RREAD[i:i + 900], r"投过了|点掉|已下线",
                         "没说清差额去哪了")

    def test_it_gives_the_restock_command(self):
        i = RREAD.index("rread-open")
        seg = RREAD[i:i + 900]
        self.assertIn("/job-setup --section search", seg, "没给补货的命令")
        # 那条敲法必须真的存在（面板印的命令在别处查无此名，栽过一次）。
        setup = (ROOT / "workflows" / "job-setup.md").read_text(encoding="utf-8")
        self.assertIn("--section search", setup, "面板印的敲法在工作流里查无此名")

    def test_it_says_scraping_more_is_not_the_lever(self):
        """多抓一轮抓回来的还是同一批行业的岗 —— 杠杆是搜索词。"""
        i = RREAD.index("rread-open")
        self.assertRegex(RREAD[i:i + 900], r"改搜索词.{0,10}比|不是多抓")

    def test_the_field_is_optional_in_the_type(self):
        """旧快照没有它。写成必填，换个旧 data.json 整块就崩。"""
        i = TYPES.index("sweetSpot: {")
        self.assertRegex(TYPES[i:i + 1400], r"open\?: number",
                         "`open` 不是可选字段")

    def test_the_render_is_guarded(self):
        i = RREAD.index("rread-open")
        self.assertIn('typeof ss.open === "number"', RREAD[max(0, i - 300):i],
                      "旧快照上会渲染出 undefined")


class TheWarningOnlyLightsWhenItIsThin(unittest.TestCase):
    """库存还剩大半时不该点亮警示色 —— 那会让每一次打开都像在报警。"""

    def test_the_threshold_is_relative(self):
        i = RREAD.index("rread-open")
        self.assertRegex(RREAD[i:i + 400], r"ss\.open < ss\.count / 2",
                         "没有「少了才点亮」的判据")

    def test_the_style_hangs_off_that_flag(self):
        css = (ROOT / "web" / "src" / "theme"
               / "cockpit.css").read_text(encoding="utf-8")
        self.assertIn(".rread-open[data-thin]", css, "标记了却没有对应样式")
        # 「这一块的变量都定义了没」归 `test_css_and_cjk_text.EveryCssVarIsDefined`
        # 全库扫（2026-08-31 把五份按块扫的抄件一起删了）—— 抄件用的是正本
        # 已经修掉的写法：`(?m)^\s*--x\s*:` 一行里只认得第一个变量。


if __name__ == "__main__":
    unittest.main()
