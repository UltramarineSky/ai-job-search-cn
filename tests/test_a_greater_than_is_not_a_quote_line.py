# -*- coding: utf-8 -*-
"""开场白剥尾巴那条正则，会把最后一行里任意位置的尖括号到行尾一起删掉。

`_strip_wordcount` 第 ③ 步要剥的是「最后**一整行**是引用」——自检备注长那样：

    > 字数校验：**192 字**（去空白字符计），≤200 ✓

而它写成了 `\\n?\\s*>[^\\n]*$`。那个 `?` 让换行变成可选，于是它匹配的其实是
「最后一行里**任意位置**的尖括号到行尾」：

    你好，我是A。转化率 3% > 行业均值 1.8%。
        ↓
    你好，我是A。转化率 3%

**而这段字是直接粘进聊天框发给 HR 的。** 断句会原样发出去，没有任何地方会提示。

实测活动用户 2026-08-23：245 个要发出去的小节（开场白 + 网申自评）里只有 1 个
含尖括号，位置也没踩到 —— **今天 0 例**。守它是因为开场白是大模型现写的自由
文本，「A > B」这种比较写法在产品岗话术里随时会出现，而失败是静默的。

## 另一半：规定的模板，要能被读它的解析器读出来

这条缝本会话已经出过两个 bug（`parse_quality` 要一个规格里不存在的粗体标题、
`parse_gaps` 不认写手真的在用的表格形状）。根因是**产出物没有 schema 正本**：
形状只活在两处 —— 写它的工作流散文、读它的解析器正则，而没有任何测试
把前者喂给后者。这里补上。
"""
import pathlib
import re
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import build_dashboard as bd  # noqa: E402
import export_web_data as ex  # noqa: E402

BD = (ROOT / "tools" / "build_dashboard.py").read_text(encoding="utf-8")


def flat(s: str) -> str:
    s = " ".join(re.sub(r"^\s*>\s?", "", s, flags=re.M).split())
    return re.sub(r"(?<=[一-鿿，。；：、（）「」])"
                  r" +(?=[一-鿿，。；：、（）「」])", "", s)


def fenced(path: str, anchor: str) -> str:
    """`workflows/…` 里以 `anchor` 开头的那个围栏块的正文。"""
    t = (ROOT / path).read_text(encoding="utf-8")
    i = t.index(anchor)
    return t[i:t.index("\n```", i)]


class AMidSentenceBracketSurvives(unittest.TestCase):
    def test_a_comparison_is_not_a_quote(self):
        s = "你好，我是A。转化率 3% > 行业均值 1.8%。"
        self.assertEqual(bd._strip_wordcount(s), s)

    def test_nothing_is_lost_after_the_bracket(self):
        """要害是**后半句还在**，不是「结果非空」。"""
        out = bd._strip_wordcount("你好。我把 A > B 讲清楚了。")
        self.assertIn("讲清楚了", out)

    def test_a_trailing_bracket_survives(self):
        self.assertEqual(bd._strip_wordcount("abc>"), "abc>")

    def test_it_is_not_only_about_the_last_line(self):
        """中间那行有尖括号，同样不许动。"""
        s = "第一行 A > B\n第二行收尾。"
        self.assertEqual(bd._strip_wordcount(s), s)


class TheRealTailsAreStillStripped(unittest.TestCase):
    """剥不掉的话，自检备注会跟着粘进聊天框 —— 那是这条正则本来的活。"""

    def test_a_wordcount_quote_line_goes(self):
        out = bd._strip_wordcount(
            "你好，我是A。\n> 字数校验：**192 字**（去空白字符计），≤200 ✓")
        self.assertEqual(out, "你好，我是A。")

    def test_several_quote_lines_go(self):
        out = bd._strip_wordcount(
            "你好。\n\n> 字数校验：192 字\n> 渠道：猎聘")
        self.assertEqual(out, "你好。")

    def test_a_blank_line_between_does_not_save_it(self):
        out = bd._strip_wordcount("你好。\n\n\n> 自检：渠道判定 猎头")
        self.assertEqual(out, "你好。")

    def test_the_paren_wordcount_still_goes(self):
        self.assertEqual(bd._strip_wordcount("你好。\n（字数：199）"), "你好。")

    def test_a_rule_line_still_goes(self):
        self.assertEqual(bd._strip_wordcount("你好。\n---"), "你好。")

    def test_a_quote_line_in_the_middle_survives(self):
        """docstring 明写「只从**尾部**剥，不动正文中间」——引 JD 原话就长这样。

        变异实测：把结尾锚 `$` 去掉之后，`re.sub` 会把**每一处**引用行都删掉，
        而当时整份测试照样全绿。缺的就是这一条。
        """
        s = "\n".join(["你好，我是A。",
                       "> JD 原话：「要求 5 年经验」",
                       "这一条我对得上。"])
        self.assertEqual(bd._strip_wordcount(s), s)

    def test_only_the_last_one_goes_when_both_exist(self):
        """中间一条留、尾部一条剥 —— 两件事要同时成立才说明锚点对。"""
        out = bd._strip_wordcount("\n".join(
            ["你好。", "> JD 原话：「五年经验」", "我对得上。",
             "> 字数校验：99 字"]))
        self.assertIn("JD 原话", out)
        self.assertNotIn("字数校验", out)

    def test_a_leading_html_comment_still_goes(self):
        self.assertEqual(
            bd._strip_wordcount("<!-- 给写文件的人看的 -->\n你好。"), "你好。")


class TheAllQuoteBodyIsStillRescued(unittest.TestCase):
    """②-在-③-之前那条不变量：整段引用要被剥成正文，不能被一行行吃光。"""

    def test_it_becomes_plain_text(self):
        self.assertEqual(
            bd._strip_wordcount("> 整段都是引用的开场白\n> 第二行"),
            "整段都是引用的开场白\n第二行")

    def test_it_does_not_come_back_empty(self):
        self.assertTrue(bd._strip_wordcount("> 只有一行，整段是引用").strip())

    def test_the_ordering_reason_is_still_recorded(self):
        seg = flat(BD[BD.index("def _strip_wordcount("):][:2600]
                   .replace("#", " "))
        self.assertRegex(seg, r"③ 必须在 ② 之后")
        self.assertRegex(seg, r"一行一行 把正文全吃光|一行一行把正文全吃光")


class TheReasonIsRecorded(unittest.TestCase):
    def _seg(self) -> str:
        i = BD.index("尾部引用行（自检备注）")
        return flat(BD[max(0, i - 1400):i].replace("#", " "))

    def test_it_says_the_newline_is_mandatory(self):
        self.assertRegex(self._seg(), r"\*\*换行不是可选的。\*\*")

    def test_it_shows_the_damage(self):
        seg = self._seg()
        self.assertRegex(seg, r"会被削成 `转化率 3%`，一句话从中间断掉")
        self.assertRegex(seg, r"\*\*直接粘进聊天框发给 HR 的\*\*")

    def test_it_admits_there_is_no_live_case(self):
        seg = self._seg()
        self.assertRegex(seg, r"245 个要发出去的小节里只有 1 个含尖括号")
        self.assertIn("2026-08-23", seg)

    def test_it_says_why_dropping_the_quantifier_is_safe(self):
        """「那整段引用怎么办」是审这段改动时第一个会问的问题。"""
        self.assertRegex(self._seg(), r"在上面第 ② 步已经处理过")

    def test_it_points_at_this_test(self):
        self.assertIn("test_a_greater_than_is_not_a_quote_line.py", self._seg())


class EveryPrescribedTemplateParses(unittest.TestCase):
    """写手规定的形状，读它的解析器必须认得 —— 这条缝出过两个 bug。

    只钉「读得出来」，不钉字段取值：具体语义各有各的测试，这里是那张
    「写手 ↔ 读者」的连线本身。
    """

    def test_the_evaluation_template_parses(self):
        t = fenced("workflows/reference/04-job-evaluation.md",
                   "## 职位评估：[公司] - [岗位]")
        for name, fn in (("硬性条件", ex.parse_gates),
                         ("评分明细", ex.parse_dimensions),
                         ("职位真伪信号", ex.parse_quality),
                         ("缺口", ex.parse_gaps)):
            with self.subTest(name=name):
                self.assertTrue(fn(t), f"模板里的「{name}」解析器读不出来")

    def test_the_evaluation_template_yields_a_verdict(self):
        t = fenced("workflows/reference/04-job-evaluation.md",
                   "## 职位评估：[公司] - [岗位]")
        self.assertTrue(bd.parse_evaluation(t).get("verdict", "") is not None)

    def test_the_outreach_template_parses(self):
        t = fenced("workflows/reference/06-outreach-templates.md",
                   "# <公司> - <岗位> 投递话术")
        got = bd.parse_outreach(t)
        for k in ("url", "greeting", "email_subject", "email_body", "wangshen"):
            with self.subTest(k=k):
                self.assertTrue(got[k].strip(), f"模板里的 `{k}` 解析成空了")

    def test_the_outreach_template_keeps_the_placeholder_intact(self):
        """`<正文>` 的尾括号被吃掉，正是这次修的那个 bug 的最小复现。"""
        got = bd.parse_outreach(
            fenced("workflows/reference/06-outreach-templates.md",
                   "# <公司> - <岗位> 投递话术"))
        self.assertEqual(got["greeting"], "<正文>")
        self.assertEqual(got["wangshen"], "<正文>")

    def test_the_interview_log_template_parses(self):
        t = fenced("workflows/job-interview.md", "## 第 N 轮 · YYYY-MM-DD")
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d) / "interview_log.md"
            p.write_text(t, encoding="utf-8")
            got = bd.parse_interview_log(p)
        self.assertEqual(len(got), 1)
        self.assertTrue(got[0]["qa"], "问答一条都没读出来")
        self.assertTrue(got[0]["scene"].strip())

    def test_a_real_interview_heading_fills_all_three_fields(self):
        """模板里 `第 N 轮 · YYYY-MM-DD` 是占位符，轮次与日期留空是**规定的**
        「宽进不猜」。换成真抬头就必须三个字段都到位 —— 否则那条宽进
        会掩盖一个真的解析错位。"""
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d) / "interview_log.md"
            p.write_text("## 第 3 轮 · 2026-08-20 · 专业面\n\n"
                         "- 场景：用人经理，40 分钟\n\n"
                         "### Q1 说说你做过的最难的项目\n\n"
                         "**答**：某个项目。\n\n**反馈**：够具体。\n",
                         encoding="utf-8")
            got = bd.parse_interview_log(p)
        self.assertEqual((got[0]["round"], got[0]["date"], got[0]["stage"]),
                         ("3", "2026-08-20", "专业面"))

    def test_the_anchors_still_exist(self):
        """锚点没了，上面几条会静默变成「没测」。"""
        for path, anchor in (
                ("workflows/reference/04-job-evaluation.md",
                 "## 职位评估：[公司] - [岗位]"),
                ("workflows/reference/06-outreach-templates.md",
                 "# <公司> - <岗位> 投递话术"),
                ("workflows/job-interview.md", "## 第 N 轮 · YYYY-MM-DD")):
            with self.subTest(path=path):
                self.assertIn(anchor,
                              (ROOT / path).read_text(encoding="utf-8"))


class TheSignalItLeansOnIsReal(unittest.TestCase):
    """有语料时验一次：改动没有动到任何一份真开场白。"""

    def _sections(self):
        p = ROOT / ".active_user"
        if not p.is_file():
            self.skipTest("没有活动用户")
        u = p.read_text(encoding="utf-8").strip()
        d = ROOT / "users" / u / "documents" / "applications"
        if not d.is_dir():
            self.skipTest("没有投递归档")
        out = []
        for f in d.glob("*/outreach.md"):
            t = f.read_text(encoding="utf-8", errors="replace")
            for sec in ("打招呼开场白", "网申自评"):
                raw = bd._section(t, sec)
                if raw.strip():
                    out.append(raw)
        if len(out) < 50:
            self.skipTest("小节太少，说明不了")
        return out

    def test_every_section_still_yields_text(self):
        empty = [s for s in self._sections() if not bd._strip_wordcount(s).strip()]
        self.assertEqual(empty, [], f"{len(empty)} 个小节被剥成空了")

    def test_no_metadata_survives_into_what_gets_sent(self):
        """反向那一半：自检备注留在正文里，会跟着粘给 HR。"""
        leak = [s for s in self._sections()
                if re.search(r"字数校验|≤ ?200 ✓|附件命名|收件人自己填",
                             bd._strip_wordcount(s))]
        self.assertEqual(leak[:2], [], f"{len(leak)} 个小节里还留着自检备注")

    def test_no_stray_quote_prefix_survives(self):
        bad = [s for s in self._sections()
               if re.search(r"(?m)^\s*>", bd._strip_wordcount(s))]
        self.assertEqual(bad[:2], [], f"{len(bad)} 个小节还带着行首引用标记")


if __name__ == "__main__":
    unittest.main()
