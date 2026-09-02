# -*- coding: utf-8 -*-
"""面板那层措辞替换救不了一个被直接打开的文件 —— 71% 的深评里有框架词。

`AGENTS.md`「给用户看的措辞」管的是「**凡是给用户看的东西**」，逐条列了替换
（判词→结论、四维→评分明细、硬门→硬性条件……）。面板那一侧有兜底：
`export_web_data` 里那张替换表，注释自称「**最后一道显示层**」。

**而深评与话术是用户直接打开的文件，那一层挡不在中间。** 实测活动用户
2026-08-24（剥掉 HTML 注释 —— 那些是写给 AI 的）：

    evaluation.md   268 份里 191 份命中（71%）   判词 282 · 四维 65 · 硬门 45
    outreach.md     抬头那半 103 份（已由抬头那条检查管），正文这半 0 份

最扎眼的是前两个：**它们的正解就是输出格式里那两节的名字** ——「结论」和
「评分明细」。写的人抬头就看得见，却在正文里改口叫回框架词；有几份干脆把小节
标题写成了 `## 四维`。

## 词表只收判据明确、中文里不会误伤的那几个

`能力边界` 不收：`AGENTS.md` 那张表写的是「能力边界**缺口**」，而
「这是你写明的能力边界」在中文里读得通。`信息质量` 同理（「信息质量好」是日常话）。
`硬门` 要排掉 `硬门槛`（实测 7 处）—— 后者是中文里本来就有的词。

**误报一次这条就会被整条忽略**，本仓库为这句话付过好几次学费。

## 两条检查不许报同一批文件

话术的抬头归 `check_outreach_header_says_who_youre_talking_to`。第一版没切抬头，
于是那边报 103 份、这边报 104 份 —— 同一批文件在审计里出现两次，用户会以为有
两个问题。切掉抬头之后正文这半是 0，两条互不重叠。
"""
import pathlib
import re
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import audit_pipeline as ap  # noqa: E402

EVAL = (ROOT / "workflows" / "reference"
        / "04-job-evaluation.md").read_text(encoding="utf-8")
AGENTS = (ROOT / "AGENTS.md").read_text(encoding="utf-8")


def flat(s: str) -> str:
    s = " ".join(re.sub(r"^\s*>\s?", "", s, flags=re.M).split())
    return re.sub(r"(?<=[一-鿿，。；：、（）「」])"
                  r" +(?=[一-鿿，。；：、（）「」])", "", s)


def run(files: dict):
    """`files` 是 {文件名: 正文}，都放进同一个材料目录。"""
    old = ap.ROOT
    try:
        with tempfile.TemporaryDirectory() as t:
            r = pathlib.Path(t)
            d = r / "users" / "甲" / "documents" / "applications" / "某公司_某岗"
            d.mkdir(parents=True)
            for name, text in files.items():
                (d / name).write_text(text, encoding="utf-8")
            (r / "users" / "甲" / "profile").mkdir(parents=True)
            (r / "users" / "甲" / "profile" / "candidate.md").write_text(
                "x", encoding="utf-8")
            (r / ".active_user").write_text("甲", encoding="utf-8")
            ap.ROOT = r
            return ap.check_documents_speak_chinese_to_the_user({}, {})
    finally:
        ap.ROOT = old


def titles(files: dict):
    return [t for _l, t, _b in run(files)]


class ItCatchesTheFrameworkWords(unittest.TestCase):
    def test_the_check_is_registered(self):
        self.assertIn("话术与深评：正文里有框架词", [n for n, _f in ap.CHECKS])

    def test_it_catches_each_word(self):
        for w in ("判词", "四维", "硬门", "台账", "驾驶舱", "短名单", "读数"):
            with self.subTest(w=w):
                self.assertIn("深评正文里有框架词",
                              titles({"evaluation.md": f"## 结论\n\n{w}是这个。\n"}),
                              f"「{w}」没被认出来")

    def test_a_clean_file_reports_nothing(self):
        self.assertEqual(
            run({"evaluation.md": "## 结论\n\n值得投。\n\n## 评分明细\n\n88 分。\n"}),
            [])

    def test_it_says_what_to_write_instead(self):
        body = run({"evaluation.md": "判词：值得投\n"})[0][2]
        self.assertIn("判词→结论", body)

    def test_it_says_why_the_panel_layer_does_not_help(self):
        body = run({"evaluation.md": "判词：值得投\n"})[0][2]
        self.assertIn("用户会直接打开", body)
        self.assertIn("面板那层措辞替换救不了它", body)

    def test_it_does_not_ask_for_a_backfill(self):
        """191 份存量逐份补是没人会做的事 —— 说清盯哪儿。"""
        body = run({"evaluation.md": "判词：值得投\n"})[0][2]
        self.assertIn("存量不必逐份补，盯新跑的批次", body)

    def test_it_stays_a_warning(self):
        """没有机械修法，判 error 会让「零 error」那条测试长红。"""
        for level, _t, _b in run({"evaluation.md": "判词：值得投\n"}):
            self.assertEqual(level, "warn")


class ItDoesNotCryWolf(unittest.TestCase):
    def test_a_html_comment_does_not_count(self):
        """注释是写给 AI 的，不是「给用户看的东西」。"""
        self.assertEqual(
            run({"evaluation.md": "## 结论\n\n<!-- 判词上限是「值得投」 -->\n值得投。\n"}),
            [])

    def test_ordinary_chinese_is_not_jargon(self):
        """「硬门槛」中文里本来就有；实测 7 处。误报一次这条就被整条忽略。"""
        self.assertEqual(
            run({"evaluation.md": "## 结论\n\n一条硬门槛都没有。\n"}), [])

    def test_the_word_list_leaves_out_the_ambiguous_ones(self):
        """`能力边界`／`信息质量` 在中文里读得通 —— 不收。"""
        words = [w for w, _p, _f in ap._DOC_JARGON]
        for w in ("能力边界", "信息质量"):
            with self.subTest(w=w):
                self.assertNotIn(w, words, f"「{w}」进了词表 —— 它会误伤")

    def test_every_word_has_a_replacement(self):
        """只说「别写」不给「写什么」，等于把问题退回给写的人。"""
        for w, _p, fix in ap._DOC_JARGON:
            with self.subTest(w=w):
                self.assertTrue(fix.strip(), f"「{w}」没给替换词")

    def test_every_word_traces_to_the_wording_table(self):
        for w, _p, _f in ap._DOC_JARGON:
            with self.subTest(w=w):
                self.assertIn(w, AGENTS,
                              f"「{w}」不在 AGENTS.md 的措辞表里，凭什么禁")


class TheTwoChecksDoNotOverlap(unittest.TestCase):
    """抬头归抬头那条检查 —— 同一批文件在审计里出现两次，用户会以为有两个问题。"""

    HEAD = "- 渠道判定：**有对话方 · 聊天框（猎头）**\n- 判词：值得投（72 分）\n"

    def test_a_jargon_only_header_is_not_reported_here(self):
        t = self.HEAD + "\n## 打招呼开场白\n\n您好，我做过 X。\n"
        self.assertEqual(titles({"outreach.md": t}), [])

    def test_jargon_in_the_greeting_body_is_reported(self):
        t = ("- 渠道判定：**有对话方 · 聊天框（猎头）**\n\n"
             "## 打招呼开场白\n\n您好，这个岗的四维分很高。\n")
        self.assertIn("话术正文里有框架词", titles({"outreach.md": t}))

    def test_the_evaluation_is_not_cut(self):
        """深评没有「抬头」这个概念，别顺手也切一刀。"""
        i = ap.__file__ and 0
        src = (ROOT / "tools" / "audit_pipeline.py").read_text(encoding="utf-8")
        j = src.index("def check_documents_speak_chinese_to_the_user")
        seg = src[j:j + 3000]
        self.assertIn('if kind == "outreach.md":', seg,
                      "切抬头没有按文件类型分 —— 深评会被切掉开头一段")
        del i

    def test_the_reason_is_written_down(self):
        src = (ROOT / "tools" / "audit_pipeline.py").read_text(encoding="utf-8")
        j = src.index("def check_documents_speak_chinese_to_the_user")
        seg = flat(src[j:j + 3000].replace("#", " "))
        self.assertRegex(seg, r"那边 103 份、这边 104 份")


class TheRuleIsAtTheWritersElbow(unittest.TestCase):
    """规则贴在写手眼前才算数 —— 这是 04 自己记过的一课。"""

    def _seg(self) -> str:
        i = EVAL.index("## 输出格式")
        return flat(EVAL[i:EVAL.index("```", i)])

    def test_the_output_format_says_it_is_user_facing(self):
        self.assertRegex(self._seg(),
                         r"\*\*这份文件是给用户看的，不是内部记录。\*\*")

    def test_it_carries_the_replacement_table(self):
        seg = self._seg()
        for pair in ("判词", "四维", "硬门 / 硬门 FAIL"):
            with self.subTest(pair=pair):
                self.assertIn(pair, seg)

    def test_it_points_out_the_irony(self):
        """正解就是同一份模板里那两节的名字 —— 不点破，下一个人还会犯。"""
        seg = self._seg()
        self.assertRegex(seg, r"它们的正解\*\*就是这份模板里那两节的名字\*\*")

    def test_it_carries_the_measurement(self):
        seg = self._seg()
        self.assertIn("2026-08-24", seg)
        self.assertRegex(seg, r"191 份命中（71%）")

    def test_it_excuses_ordinary_chinese(self):
        self.assertRegex(self._seg(), r"「硬门槛」这种日常说法\*\*不算\*\*")

    def test_it_says_the_panel_layer_is_not_enough(self):
        self.assertRegex(self._seg(), r"\*\*但那只救得了面板\*\*")

    def test_it_names_the_check(self):
        self.assertIn("话术与深评正文里有框架词", self._seg())


class TheSignalItLeansOnIsReal(unittest.TestCase):
    def test_the_real_corpus_still_trips_it(self):
        p = ROOT / ".active_user"
        if not p.is_file():
            self.skipTest("没有活动用户")
        apps = (ROOT / "users" / p.read_text(encoding="utf-8").strip()
                / "documents" / "applications")
        if not apps.is_dir():
            self.skipTest("没有语料")
        got = ap.check_documents_speak_chinese_to_the_user({}, {})
        if not got:
            self.skipTest("这份语料已经干净了 —— 那 04 那段的数要重量")
        self.assertTrue(any("深评" in t for _l, t, _b in got))

    def test_the_panel_still_has_its_own_layer(self):
        """这条检查的前提之一是「面板另有一层」—— 那一层没了要重说。"""
        src = (ROOT / "tools" / "export_web_data.py").read_text(encoding="utf-8")
        self.assertIn("最后一道显示层", src)


if __name__ == "__main__":
    unittest.main()
