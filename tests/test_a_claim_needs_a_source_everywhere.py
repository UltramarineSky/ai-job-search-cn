# -*- coding: utf-8 -*-
"""开场白说了公司的事却没记出处 —— 审计报了两周，面板一个字都没印。

`03-writing-style.md` 铁律 1 是「绝不编造」。审计从 2026-08-26 起在查这件事
（「话术：说了公司的事就要有出处」），而**那是事后的一份清单**：用户按
「复制开场白」把这段字发给用人方的时候，屏幕上什么都没有。同一块屏幕上，
文风问题印着「发之前删掉：…」、抬头问题印着「发之前先看一眼：…」，
只有「这句话你从哪看来的」是哑的。

实测 2026-08-31：面板上 280 段开场白里 **20 段**踩了这条，而它们旁边就摆着
复制按钮和 `mailto:` 链接。

## 为什么这条守卫要盯「只有一个家」

判据原来私有在 `audit_pipeline`（`_COMPANY_CLAIM` / `_fact_items`），而那个
模块**反过来 import `export_web_data`** —— 导出侧想共用只能再抄一份。抄完
两处就会各自长出自己的范围：这个仓库反复栽在这个形状上（同一件事几个住址，
而检查只去了一个）。所以正本搬进 `_cli`，两个消费方都调它。

## 范围窄不是偷懒，是量出来的

第一版查的是「那一节空不空」，报 228/236 —— 大部分是假阳性。现算
（2026-08-31）：280 段里真对公司下断言的只有 24 段（8%），其中 20 段没记
出处；另外那 92% 讲的全是他自己的经历，出处是 `profile/candidate.md`，
那一节空着是对的。下面 `TheJudgementStaysNarrow` 钉的就是这个「多数岗不该报」。

（这里写「280 段」不写「280 份开场白」是有意的：那个说法是**分母的正规写法**，
`test_the_greeting_stats_are_not_stale` 会逐处核对它和当下语料对不对得上，
而这份守卫不该多背一个会过期的数。）
"""
import json
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))

import _cli  # noqa: E402

AUDIT = (TOOLS / "audit_pipeline.py").read_text(encoding="utf-8")
EX = (TOOLS / "export_web_data.py").read_text(encoding="utf-8")
DASH = (TOOLS / "build_dashboard.py").read_text(encoding="utf-8")
TYPES = (ROOT / "web" / "src" / "types.ts").read_text(encoding="utf-8")
SHEET = (ROOT / "web" / "src" / "components"
         / "JobReadout.tsx").read_text(encoding="utf-8")


class OnlyOneHomeForTheJudgement(unittest.TestCase):
    """两个消费方，一份判据。抄一份就等着它们分叉。"""

    def _tools_containing(self, needle: str) -> list:
        return sorted(p.name for p in TOOLS.glob("*.py")
                      if needle in p.read_text(encoding="utf-8"))

    def test_the_claim_pattern_is_written_once(self):
        """「什么算对公司下断言」只许有一处定义。"""
        self.assertEqual(
            self._tools_containing("贵司|你们|咱们"), ["_cli.py"],
            "认主张的那串正则不止一份 —— 两处各改各的，审计和面板就会不一致")

    def test_the_source_section_is_parsed_once(self):
        """「出处记在哪一节」也只许有一处定义。"""
        self.assertEqual(
            self._tools_containing('"公司事实" in ln'), ["_cli.py"],
            "找出处那一节的代码不止一份")

    def test_both_consumers_go_through_the_judge(self):
        """审计与面板导出都调正本，不各判各的。"""
        for src, who in ((AUDIT, "审计"), (EX, "面板导出")):
            with self.subTest(who):
                self.assertIn("_cli.claim_without_source(", src,
                              f"{who}没走正本")

    def test_the_audit_does_not_restate_the_range(self):
        """量出来的那几个数只许有一处 —— 两份就会一半新一半旧。"""
        self.assertNotIn("228/236", AUDIT,
                         "审计又抄了一份范围说明，正本在 `_cli`")


class TheJudgementStaysNarrow(unittest.TestCase):
    """报得太宽等于没报（第一版 228/236 就是这么废掉的）。"""

    CLAIM = ("贵司去年融资之后铺的这条线，正是我这三年在做的事情，"
             "所以很想聊聊具体怎么落地，看看能不能帮上忙。")
    OWN = ("我做过十年数据科学，带过五人团队，交付过三个上线项目，"
           "指标口径和取数链路都是自己搭的，想投这个岗位试一下。")

    def test_a_claim_with_no_source_is_reported(self):
        self.assertTrue(_cli.claim_without_source(self.CLAIM, []))

    def test_a_recorded_source_clears_it(self):
        self.assertEqual(
            _cli.claim_without_source(self.CLAIM, ["- 官网 2026 年新闻"]), "")

    def test_talking_about_himself_is_not_a_claim(self):
        """89% 是这一类：出处是他自己的资料，那一节空着是对的。"""
        self.assertEqual(_cli.claim_without_source(self.OWN, []), "")

    def test_too_short_to_judge(self):
        """还没成句的那几段判不出主张，别拿它当问题报。"""
        self.assertEqual(
            _cli.claim_without_source("贵司融资，想聊聊，谢谢。", []), "")

    def test_the_skeleton_placeholder_is_not_a_source(self):
        """模板留下的 `<…>` 是个坑，不是查过的事实 —— 它不该消掉警告。"""
        skeleton = "# 本次使用的公司事实\n- <这里写你从哪看来的>\n"
        self.assertEqual(_cli.fact_items(skeleton), [])
        real = "# 本次使用的公司事实\n- 官网 2026 年新闻\n"
        self.assertEqual(len(_cli.fact_items(real)), 1)

    def test_the_next_section_is_not_swallowed(self):
        """只收这一节的条目，下一节的不算。"""
        two = ("# 本次使用的公司事实\n- 官网新闻\n\n"
               "# 下一节\n- 这条不属于出处\n")
        self.assertEqual(_cli.fact_items(two), ["- 官网新闻"])


class TheParserHandsOverTheSource(unittest.TestCase):
    """导出侧拿到的是 `parse_outreach` 的产物，不是原文 —— 出处得跟着过来。"""

    def test_parse_outreach_carries_the_facts(self):
        got = __import__("build_dashboard").parse_outreach(
            "# 打招呼开场白\n你好。\n\n# 本次使用的公司事实\n- 官网新闻\n")
        self.assertEqual(got.get("facts"), ["- 官网新闻"])

    def test_the_reason_is_recorded_next_to_it(self):
        """不写下来，下一个人会把它当成没人用的字段删掉。"""
        i = DASH.index('"facts": _cli.fact_items(text)')
        self.assertIn("claim_without_source", " ".join(DASH[i - 400:i].split()))


class ThePanelSaysItWhereTheCopyButtonIs(unittest.TestCase):

    def test_the_type_declares_it(self):
        self.assertIn("factWarn?: string;", TYPES, "没声明，面板读不到")

    def test_the_exporter_writes_what_the_judge_returned(self):
        """钉数据流向，不钉变量名：判据的返回值要落进那个字段。"""
        i = EX.index('mats["factWarn"]')
        self.assertIn("_cli.claim_without_source(",
                      EX[max(0, i - 400):i],
                      "这个字段的值不是判据算出来的")

    def test_it_sits_with_the_other_two_greeting_warnings(self):
        # 锚代码构造、且先验唯一 —— 显示串在自己写的注释里会再出现一次，
        # 这个仓库栽过。
        anchor = "{m.addresseeWarn && ("
        self.assertEqual(SHEET.count(anchor), 1, "锚点不唯一")
        i = SHEET.index(anchor)
        # **找的是整个条件式，不是那个名字。** 光找 `m.factWarn` 时，把字段
        # 改名成 `m.factWarnX` 这条照样绿 —— 旧名是新名的前缀。
        # 同一个子串陷阱这个会话里已经栽过一次（`resumeStale`）。
        self.assertIn("{m.factWarn && (", SHEET[i:i + 2000],
                      "提示没挨着开场白那三条，用户在别处看不到")

    def test_it_is_conditional_not_always_on(self):
        """一条永远显示的提醒等于没有提醒。"""
        self.assertIn("{m.factWarn && (", SHEET)

    def test_it_gives_the_command_to_fix_it(self):
        """`AGENTS.md`「每一处引导都要写出该敲的命令」。"""
        i = SHEET.index("{m.factWarn && (")
        self.assertIn("/job-apply", SHEET[i:i + 600],
                      "只说有问题，没说该敲什么")


class TheSignalIsReal(unittest.TestCase):
    """有语料时验一次：既不是零，也不是全中。"""

    def _mats(self):
        p = ROOT / "web" / "public" / "data.json"
        if not p.is_file():
            self.skipTest("还没导出过面板数据")
        return [(j.get("materials") or {})
                for j in json.loads(p.read_text(encoding="utf-8"))["jobs"]]

    def test_it_reports_a_minority_not_everything(self):
        greets = [m for m in self._mats() if m.get("greeting")]
        if not greets:
            self.skipTest("这份语料里没有开场白")
        bad = [m for m in greets if m.get("factWarn")]
        self.assertLess(
            len(bad), len(greets) // 2,
            f"{len(bad)}/{len(greets)} 被判成没出处 —— 报得过宽，"
            "第一版（228/236）就是这么废掉的")


if __name__ == "__main__":
    unittest.main()
