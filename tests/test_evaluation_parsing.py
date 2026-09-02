"""evaluation.md 的解析：标题怎么写都得认，认不出来也不许说成「都通过了」。

## 为什么每条都值得钉住

**标题不能靠字面词认。** 硬门表原来靠 `"硬门" in 标题` 定位。可 `apply.md` 从没规定
过标题写法，AGENTS.md 还明令「硬门」是内部词、不许出现在给用户看的东西里——于是 AI
越守措辞规则，写出的「## 第一步：硬性门槛」越是解析不出来。实测五份真实评估里，唯一
一份用了规范措辞的那份，整张硬门表被丢弃。

**后果比「少一块内容」严重得多。** 硬门为空时，页面那句会走 else 分支印出「这些条件
都核对过了，没有要问的」——把**没解析到**说成**全部通过**。用户据此以为学历、外包、
地点都验过了。所以除了放宽解析，`GateGrid` 那边还得有空数组守卫（见 test_web_copy）。

**内部词不能原样上屏。** `/job-rank` 写的「依据」是框架词写的内部记录，却原样进了短名单
行的悬浮提示：实测约 70 个岗的提示里带着「硬门 FAIL」「框架硬门表」。

**但换词要带守卫。** 真实开场白里写过「智能座舱行业经验是硬门槛，还是 Agent 产品能力
也在考虑范围？」——那是地道中文。裸 `replace("硬门", …)` 会把它改成「硬性条件槛」。
"""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import export_web_data as ex  # noqa: E402

GATE_ROWS = """
| 门槛 | JD 原文 / 判据 | 判定 |
|---|---|---|
| 学历与院校 | JD 写「学历不限」 | PASS |
| 工作年限 | JD 写「经验不限」 | PASS |
"""


class GateTableSurvivesAnyHeading(unittest.TestCase):
    """AI 按措辞规则写标题时，解析器必须照样认得。"""

    HEADINGS = [
        "## 硬门检查",                 # 老写法（框架词）
        "## 硬门（一票否决）",
        "## 第一步：硬性门槛",          # 实测踩雷的那个
        "## 硬性条件",                 # AGENTS.md 推荐的说法
        "## 第 1 步 · 准入门槛核对",
    ]

    # 一律走 `ex.parse_gates` —— 导出器用的就是它。
    # 测试自己重新调 `parse_table` 并指定放宽后的参数是**假绿**：那样改坏导出器
    # 那边的调用，测试照样通过。实测漏过一次（把标题匹配退回只认「硬门」，全绿）。

    def test_every_reasonable_heading_parses(self):
        for h in self.HEADINGS:
            with self.subTest(heading=h):
                gates = ex.parse_gates(h + "\n" + GATE_ROWS)
                self.assertEqual(len(gates), 2, f"「{h}」下的硬性条件表没解析出来")
                self.assertEqual(gates[0]["name"], "学历与院校")

    def test_unknown_heading_still_found_by_column_names(self):
        """标题完全不着调时，靠表头特征兜底 —— 表还是那张表。"""
        gates = ex.parse_gates("## 这个岗能不能投\n" + GATE_ROWS)
        self.assertEqual(len(gates), 2, "兜底没生效")
        self.assertEqual(gates[0]["name"], "学历与院校",
                         "兜底把表头当成数据行了（_rows_from 的起始行传错）")

    def test_column_synonyms_are_accepted(self):
        """同一张表，表头可能写「硬门」也可能写「门槛」——OR 组必须都认。"""
        alt = GATE_ROWS.replace("| 门槛 |", "| 硬门 |").replace("| 判定 |", "| 结论 |")
        gates = ex.parse_gates("## 随便什么标题\n" + alt)
        self.assertEqual(len(gates), 2, "同义列名没认出来")

    def test_no_table_returns_empty_not_garbage(self):
        """真没有表就得返回空，不能瞎认一张别的表充数。"""
        self.assertEqual(ex.parse_gates("## 硬性条件\n\n这个岗我还没核对。\n"), [])

    def test_gate_names_are_translated(self):
        """解析成功后条件名直接上屏，内部词不能带过去。"""
        t = GATE_ROWS.replace("| 学历与院校 |", "| 英语（你的自带硬门） |")
        self.assertEqual(ex.parse_gates("## 硬性条件\n" + t)[0]["name"],
                         "英语（你的自带硬性条件）")


class RealEvaluationsAllParse(unittest.TestCase):
    """控制测试：盘上真实的评估文件，硬门表一份都不许丢。

    这是唯一能发现「解析器和 AI 的写法各走各的」的测试——合成样例永远长成
    解析器认识的样子。
    """

    def test_every_real_evaluation_yields_gates(self):
        ptr = ROOT / ".active_user"
        if not ptr.is_file():
            self.skipTest("没有活动用户")
        base = ROOT / "users" / ptr.read_text(encoding="utf-8").strip()
        apps = base / "documents" / "applications"
        if not apps.is_dir():
            self.skipTest("还没有投递材料")
        checked = 0
        for ev in sorted(apps.glob("*/evaluation.md")):
            t = ev.read_text(encoding="utf-8", errors="replace")
            if "|" not in t:
                continue                      # 没有任何表格的评估，跳过
            checked += 1
            with self.subTest(app=ev.parent.name):
                self.assertTrue(ex.parse_gates(t),
                                f"{ev.parent.name} 的硬性条件表没解析出来 —— "
                                "面板会把它显示成「都核对过了」")
        if not checked:
            self.skipTest("没有带表格的评估文件")


class InternalWordsDoNotReachTheScreen(unittest.TestCase):

    def test_framework_words_are_translated(self):
        for src, want in [
            ("原判「硬门 FAIL (学历院校)」", "不满足硬性条件"),
            ("框架硬门表里没有此条", "硬性条件表"),
            ("## 信息质量提示", "待核实的信息"),
            ("进了短名单", "可以投的岗位"),
            ("记入台账", "投递记录"),
        ]:
            with self.subTest(src=src):
                self.assertIn(want, ex.plain(src))
                self.assertNotIn("硬门 FAIL", ex.plain(src))

    def test_longer_terms_win_over_shorter(self):
        """先换「硬门」的话，屏幕上会剩一个孤零零的英文 FAIL。"""
        self.assertNotIn("FAIL", ex.plain("硬门 FAIL (英语)"))

    def test_natural_chinese_is_not_mangled(self):
        """「硬门槛」「信息质量差」是地道中文，不是框架词 —— 一个字都不许动。

        前者出自真实开场白（要发给雇主的文案）。裸子串替换会把它改成
        「硬性条件槛」，而那句话是用户要复制去发的。
        """
        for s in ["智能座舱行业经验是硬门槛，还是产品能力也在考虑范围？",
                  "JD 信息质量差，像是两个岗拼在一起"]:
            with self.subTest(s=s):
                self.assertEqual(ex.plain(s), s)


class QualityNotesAreParsedNotSilentlyEmpty(unittest.TestCase):
    """`parse_quality` —— 五个 `parse_*` 里**唯一没有测试的那个**。

    2026-08-21 量行覆盖率发现的：`parse_dimensions` / `parse_gates` / `parse_gaps` /
    `parse_table` 都在本文件里钉着，只有它整段没人跑过、也没有任何测试提到它的名字。

    它产出的是面板上「待核实的信息」。它的实现里记着两条用代价换来的行为，
    而**两条都是一改就静默失效**——解析不到只会少一块内容，页面不会报错：

    1. **标题宽进。** 「信息质量」和「硬门」一样是 AGENTS.md 禁止上屏的内部词，
       AI 守规则写成「待核实的信息」——只认字面词的解析器一条都读不到。
       这与本文件开头那段「硬门表因为守措辞规则反而解析不出来」是同一个坑。
    2. **折行接回去之后要再过一次 `plain()`。** 拼接用一个空格（英文折行需要它），
       中文折行不需要，拼完屏幕上就是「没有公司名， 本轮无法独立核实」——
       标点后凭空多一个空格，实测 21 条这样的。
    """

    BODY = "\n".join([
        "## 待核实的信息",
        "",
        "- **公司未公开**：这个岗由猎头代招，**没有公司名**，",
        "  本轮无法独立核实。",
        "- **薪资口径不明**：JD 只写 `面议`。",
        "",
        "## 下一节",
        "- **不该被读到的**：属于别的小节。",
    ])

    def test_every_reasonable_heading_parses(self):
        """标题宽进：内部词和人话都要认。写死一种，另一种就静默变空。"""
        for h in ("## 信息质量", "## 待核实的信息", "## 真伪信号",
                  "## 存疑之处", "## 要核实的几件事"):
            with self.subTest(heading=h):
                got = ex.parse_quality(h + "\n- **甲**：乙\n")
                self.assertEqual([i["title"] for i in got], ["甲"],
                                 f"标题写成「{h}」就读不到了")

    def test_unrelated_heading_yields_empty(self):
        self.assertEqual(ex.parse_quality("## 评分明细\n- **甲**：乙\n"), [])

    def test_it_stops_at_the_next_section(self):
        titles = [i["title"] for i in ex.parse_quality(self.BODY)]
        self.assertEqual(titles, ["公司未公开", "薪资口径不明"],
                         "越过 `##` 读到了下一节的内容")

    def test_wrapped_lines_are_joined_without_a_stray_space(self):
        """中文折行拼回去之后，标点后面不许多出一个空格。"""
        got = ex.parse_quality(self.BODY)
        detail = got[0]["detail"]
        self.assertIn("本轮无法独立核实", detail, f"折行那半句丢了：{detail!r}")
        self.assertNotIn("， ", detail,
                         f"中文标点后凭空多了一个空格（没过 plain()）：{detail!r}")

    def test_markdown_marks_do_not_reach_the_screen(self):
        """`**` 与反引号是给文件看的，不是给屏幕看的。"""
        got = ex.parse_quality(self.BODY)
        blob = "".join(i["title"] + i["detail"] for i in got)
        for mark in ("**", "`"):
            with self.subTest(mark=mark):
                self.assertNotIn(mark, blob, f"标记漏到屏幕上了：{blob!r}")


class GapsAreParsedNotSilentlyEmpty(unittest.TestCase):
    """「缺口」小节必须被解析——这个字段原来**根本没有解析器**。

    job 初始化成 `"gaps": []` 之后全文件再无第二处写入，于是深评明明写了
    缺口，面板却对每个岗都渲染「这个岗没有（对不上的地方）」——把「上游丢了
    数据」说成「核对过没问题」，与 GateStamp 注释点名的「解析为空说成核对通过」
    同一类，是整页最危险的错误形状。实测 39 份评估里 37 份有缺口节、
    共 117 条，页面上一条都没显示过。
    """

    DOC = ("# 甲公司 — 岗A\n\n"
           "## 缺口（如实写，不美化）\n\n"
           "- 「2 个企业级项目」——你的作品是面向公众的开源产品\n"
           "- **石化行业域完全陌生**\n"
           "- 任职要求：英语流利——你明确排除英语面试\n\n"
           "## 有哪些信息没核实上（不计分）\n\n- 无\n")

    def test_the_real_shape_parses(self):
        got = ex.parse_gaps(self.DOC)
        self.assertEqual(len(got), 3, f"三条 bullet 只解析出 {got}")
        self.assertEqual(got[0]["claim"], "「2 个企业级项目」")
        self.assertEqual(got[0]["detail"], "你的作品是面向公众的开源产品")

    def test_bold_markers_are_stripped(self):
        got = ex.parse_gaps(self.DOC)
        self.assertNotIn("**", got[1]["claim"], "markdown 粗体不该原样上屏")

    def test_kind_is_only_taken_when_written(self):
        """真实数据多是平铺 bullet——`kind` 不编造，写了才有。"""
        got = ex.parse_gaps(self.DOC)
        self.assertEqual(got[0]["kind"], "")
        self.assertEqual(got[2]["kind"], "任职要求")
        self.assertEqual(got[2]["claim"], "英语流利")

    def test_section_boundary_is_respected(self):
        """下一个 `##` 就停——「待核实」那节的「无」不是缺口。"""
        got = ex.parse_gaps(self.DOC)
        self.assertTrue(all("无" != g["claim"] for g in got))

    def test_no_section_means_no_items(self):
        self.assertEqual(ex.parse_gaps("# 岗\n\n## 优势\n- 强\n"), [])

    def test_the_export_actually_calls_it(self):
        """有解析器但没人调，页面照旧全空——钉住 main() 里那行赋值。"""
        src = (ROOT / "tools" / "export_web_data.py").read_text(encoding="utf-8")
        self.assertIn('job["gaps"] = parse_gaps(', src,
                      "main() 没把 parse_gaps 的结果放进 job——字段又回到永远为空")


if __name__ == "__main__":
    unittest.main()


class ScoreLineVariants(unittest.TestCase):
    """综合得分那一行的各种合法写法都要读得出来。

    专门守 2026-08-17 撞出的那个洞：`candidate.md` 的专业减分裁定会让评估写成
    `综合得分：72 − 5（专业减分）= 67/100`，而原来的邻近预算（`综合` 之后 12 字内）
    刚好挡掉带标签的那种——**同一条规则，写清楚的版本读不出来、写简略的读得出来**。
    读不出来不报错，只是把深评分静默丢掉、面板继续显示粗筛分。
    """

    CASES = [
        ("**综合得分：64/100**", "64"),                       # 模板规定的写法
        ("**综合得分：约 62/100 —— 值得投**", "62"),          # 夹「约」
        ("**综合 = 55×0.30 + 40×0.25 = 62 → 「值得投」**", "62"),   # 纯算式、无 /100
        ("**综合得分：78 − 5 = 73/100**", "73"),              # 减分、不带标签
        ("**综合得分：72 − 5（专业减分）= 67/100**", "67"),   # 减分、带标签（原来读不出）
        ("**综合得分：68 - 5（专业减分）= 63/100**", "63"),   # 同上，半角减号
        ("**综合得分：63/100**（四维加权 68，已扣专业减分 5）", "63"),  # 结论在前、算式在后
        ("综合 82/100", "82"),
        ("**综合得分：100/100**", "100"),                     # 三位数不被截成 10
    ]

    def test_all_variants_parse(self):
        import build_dashboard as bd
        for line, want in self.CASES:
            with self.subTest(line=line):
                r = bd.parse_evaluation(line + "\n\n## 结论：值得投\n")
                self.assertEqual(
                    r["score"], want,
                    f"这行读不出分数或读错了：{line}——深评分会被静默丢弃")

    def test_digit_boundary_not_sliced(self):
        """`67/100` 不许被切成 `7/100`。

        按行取**最后一个** `NN/100` 时，贪婪回溯会先试最靠右的起点。
        少一个前置数字边界，67 分就读成 7 分——分数只会向下错，比读不出来更隐蔽。
        """
        import build_dashboard as bd
        r = bd.parse_evaluation("**综合得分：72 − 5 = 67/100**\n\n## 结论：值得投\n")
        self.assertEqual(r["score"], "67")


class VerdictIsNotPolluted(unittest.TestCase):
    """判词天花板的核对句里几乎总有「强匹配」字样——不能把解释文字当判词。

    原来兜底按档位表顺序扫全文（强匹配排第一），一份结论明写「值得投」、
    但天花板句提到「天花板强匹配，不压」的评估，面板显示成「强匹配」。
    这种误报只会**向上**，比不显示更糟。整体走查（护理模拟用户）当场撞出。
    """

    BODY = ("# 某医院 — 某岗\n\n## 四维打分\n\n"
            "| 维度 | 权重 | 分 | 依据 |\n|---|---|---|---|\n"
            "| 技能与经验 | 30% | 93 | x |\n\n"
            "综合 = 93×0.30 + 55×0.20 + 70×0.30 + 70×0.20 = 74 → **值得投**"
            "（判词天花板：技能 93 ≥80 → 天花板强匹配，不压）\n")

    def test_arrow_anchored_verdict_wins_over_ceiling_note(self):
        import build_dashboard as bd
        r = bd.parse_evaluation(self.BODY)
        self.assertEqual(r["verdict"], "值得投",
                         "把天花板解释里的「强匹配」当成了判词——档位向上误报")

    def test_bold_conclusion_line_still_works(self):
        import build_dashboard as bd
        r = bd.parse_evaluation("综合 82/100\n\n**结论：强匹配（82/100）**\n\n"
                                "判词天花板核对：……值得投……\n")
        self.assertEqual(r["verdict"], "强匹配")

    def test_plain_text_fallback_takes_earliest_position(self):
        import build_dashboard as bd
        r = bd.parse_evaluation("综合 55/100\n本岗判为可以考虑。"
                                "（对照：强匹配的标准是……）\n")
        self.assertEqual(r["verdict"], "可以考虑",
                         "兜底该按文中位置取最早的档位，不按档位优先级")

    def test_intermediate_conclusion_line_does_not_win(self):
        """真实评估里硬门小节也有「**结论：硬门全部通过…**」——它在文中先出现。

        只取第一个锚点会把这句中间结论当判词端上屏（还带内部词「硬门」）。
        整体走查还原数据时当场撞出：一个 82 分的岗，判词变成了那句话。
        """
        import build_dashboard as bd
        r = bd.parse_evaluation(
            "## 第一步：硬性门槛\n\n| 门槛 | 依据 | 判定 |\n|---|---|---|\n"
            "| 学历 | 不限 | PASS |\n\n**结论：硬门全部通过，可以进入打分。**\n\n"
            "## 综合\n\n综合 82/100\n\n**结论：强匹配（82/100）**\n")
        self.assertEqual(r["verdict"], "强匹配",
                         "把硬门小节的中间结论当成了判词")


class AGateFailIsNeverReadAsABand(unittest.TestCase):
    """硬性条件没过的评估，不许被读成五档里的任何一档。

    它的结论标题是「### 结论：不满足硬性条件」——**不含任何档位词**，
    于是锚点全被过滤掉，退回扫「结论」段正文。而翻案类评估的结论段几乎必然
    写着一句「上一轮给了 63「值得投」」来解释为什么改判——那句就成了判词。

    实测：某大型游戏公司 AI FDE，存档明写「结论：不满足硬性条件」（8 年年限门槛
    差 4.7 年），面板却显示「值得投」并把它排进「可以投的岗位」。
    **误报只会向上**——让用户去投一个硬性条件根本不满足的岗，比不显示危险得多。

    还有一层：`writeback` 自己有一份 `is_gate_fail` 判得对，于是它说「库与存档一致」，
    而 export 逐次催「跑 writeback 补账」。两个工具对同一份存档给出不同结论，
    用户夹在中间死循环。判据因此收敛到 `build_dashboard` 一处。
    """

    REVERSAL = (
        "# 某公司 — AI FDE\n\n"
        "### 硬性条件检查\n\n"
        "| 门槛 | 结果 | 依据 |\n|---|---|---|\n"
        "| 工作年限 | FAIL | 要 8 年，你 3 年 4 个月 |\n\n"
        "**综合得分：不打分（硬性条件没过）**\n\n"
        "### 结论：不满足硬性条件\n\n"
        "**这一条是重跑时翻的案。** 上一轮给了 63「值得投」并出了开场白，"
        "那是漏读了任职要求第 1 条的年限门槛。\n")

    def test_the_old_verdict_quoted_in_prose_is_not_the_verdict(self):
        import build_dashboard as bd
        v = bd.parse_evaluation(self.REVERSAL)["verdict"]
        self.assertNotIn(v, bd.VERDICTS,
                         f"硬性条件没过的评估被读成了「{v}」——"
                         "结论段里那句解释用的旧判词被当成了判词")
        self.assertTrue(v.startswith("硬门 FAIL"),
                        f"判词应是硬门 FAIL 形态，实际是「{v}」")

    def test_a_gate_fail_without_any_band_word_still_parses(self):
        """结论段里一个档位词都没有时也不能返回空——空判词下游会当成「已评分」。"""
        import build_dashboard as bd
        v = bd.parse_evaluation(
            "**综合得分：不打分（硬性条件没过）**\n\n"
            "### 结论：不满足硬性条件\n\n学历要求硕士，你是本科。\n")["verdict"]
        self.assertTrue(v.startswith("硬门 FAIL"), v)

    def test_the_two_tools_share_one_predicate(self):
        """判据只此一份。两份必然飘——这条 bug 就是飘出来的。"""
        import build_dashboard as bd
        import writeback as wb
        self.assertIs(wb.is_gate_fail, bd.is_gate_fail,
                      "writeback 又自己写了一份 is_gate_fail")

    def test_a_normal_evaluation_is_untouched(self):
        """别把正常评估也误判成硬门 FAIL——控制检查的另一半。"""
        import build_dashboard as bd
        r = bd.parse_evaluation(
            "综合 74/100\n\n**结论：值得投（74/100）**\n\n"
            "硬性条件全部通过。\n")
        self.assertEqual(r["verdict"], "值得投")
        self.assertEqual(r["score"], "74")

    def test_the_panel_keeps_the_gate_name_from_the_store(self):
        """存档只给得出「硬门 FAIL」四个字，门名要从库里补，否则面板不说是哪条没过。"""
        import build_dashboard as bd
        app = {"evaluation": bd.parse_evaluation(self.REVERSAL)}
        entry = {"rank_verdict": "硬门 FAIL (工作年限)", "rank_score": None}
        _, verdict, evaluated = bd.resolve_score(entry, app)
        self.assertEqual(verdict, "硬门 FAIL (工作年限)",
                         "门名丢了——面板只会说「不满足硬性条件」，不说是哪一条")
        self.assertTrue(evaluated)


class ArchiveLinksSurviveLabelVariants(unittest.TestCase):
    """投递目录靠 posting.md 里的链接行接回职位——标签写法不能只认一种。

    实测 6 份真实归档里 3 份不是「原始链接：」（半角冒号的、只写「链接：」的），
    全靠 outreach.md 的「职位链接：」行侥幸兜底；少写那一行，材料与硬性条件
    整个从面板消失，且无声。整体走查（护理模拟用户）当场撞出。
    """

    def _find(self, posting_text):
        import tempfile
        import build_dashboard as bd
        with tempfile.TemporaryDirectory() as td:
            d = Path(td) / "某公司_某岗"
            d.mkdir()
            (d / "posting.md").write_text(posting_text, encoding="utf-8")
            apps = bd.find_applications(Path(td))
        return apps[0]["url"] if apps else ""

    def test_label_variants_and_both_colons(self):
        for line in ["原始链接：https://x/1", "原始链接: https://x/1",
                     "链接：https://x/1", "- 职位链接: https://x/1"]:
            with self.subTest(line=line):
                self.assertEqual(self._find(f"# 快照\n\n- {line}\n\n## 正文\n…"),
                                 "https://x/1", f"「{line}」没解析出链接")

    def test_headerless_url_falls_back(self):
        """标签完全没写时，退到文件头部第一个链接。"""
        self.assertEqual(self._find("# 快照\n\nhttps://x/2\n\n## 正文\n…"),
                         "https://x/2")

    def test_body_urls_are_not_grabbed(self):
        """正文里雇主写的链接（第 13 行以后）不作兜底——那不是职位链接。"""
        body = "# 快照\n\n没有链接行\n" + "\n" * 12 + "https://employer.example/apply\n"
        self.assertEqual(self._find(body), "")
