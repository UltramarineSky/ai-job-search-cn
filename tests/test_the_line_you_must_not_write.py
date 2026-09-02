# -*- coding: utf-8 -*-
"""面板那一节的标题写着「写材料时这几处不能吹」，而「不能写成什么」从没人产出过。

`types.ts` 的 `overclaim`、面板把那句话划红的分支（`JobReadout.tsx` 的 `<s>`）、
示例数据里那两条 —— 全都在，而**真实数据里一条都没有**：实测活动用户
2026-08-25，258 个有缺口的岗、719 条缺口，`overclaim` 出现 **0 次**。

原因不是数据丢了，是 `04-job-evaluation.md` 的缺口那一节**从没要过它**
（那一节整整两行：`### 缺口` / `- ...（如实写，不美化）`）。
整条链路只在示例数据里活着 —— 那正是这个仓库自己警告过的
「虚构数据的问题不是不够真，而是它长得像真的」。

## 为什么接通而不是删掉

那一节的标题已经在承诺了。列出缺口是「我差在哪」，是自我认知；
而他下一步真的会去做的事是写简历、写开场白 —— 那一刻需要的不是
「我 Python 不够深」，是「**别写『熟练 Python』**」这句具体的禁令。
模板的 `## 明确的能力边界` 那一节已经有它的全局形态
（「逐条列出你明确不具备/不做的能力，**绝不含糊或夸大**」，底下还有一张
「绝不可写/说的表述」清单）—— 这一格是它**在这一个岗上**的形态。

删掉的话，那句标题也得跟着改小 —— 而缩的是功能，不是债。
"""
import json
import pathlib
import re
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import export_web_data as ex  # noqa: E402

SPEC = (ROOT / "workflows" / "reference"
        / "04-job-evaluation.md").read_text(encoding="utf-8")
EX = (ROOT / "tools" / "export_web_data.py").read_text(encoding="utf-8")
TYPES = (ROOT / "web" / "src" / "types.ts").read_text(encoding="utf-8")
READOUT = (ROOT / "web" / "src" / "components"
           / "JobReadout.tsx").read_text(encoding="utf-8")


def flat(s: str) -> str:
    s = " ".join(re.sub(r"^\s*(?:>|#:?)\s?", "", s, flags=re.M).split())
    return re.sub(r"(?<=[一-鿿，。；：、（）「」])"
                  r" +(?=[一-鿿，。；：、（）「」])", "", s)


def one(line: str) -> dict:
    got = ex.parse_gaps("## 缺口\n" + line + "\n")
    return got[0] if got else {}


class TheTailIsParsedOffTheDetail(unittest.TestCase):

    def test_the_plain_form(self):
        g = one("- 「要求 5 年 Python」——我写过脚本，不是工程化开发"
                "（别写成：「熟练 Python」）")
        self.assertEqual(g["overclaim"], "熟练 Python")
        self.assertEqual(g["detail"], "我写过脚本，不是工程化开发")

    def test_the_wordings_a_human_actually_types(self):
        """**跑偏的是写手，不是解析器**（同 `parse_gaps` 那句）。"""
        for line, want in (
                ("- 「A」——B（不能写成「精通 PyTorch」）", "精通 PyTorch"),
                ("- 「A」——B（不要写成：熟练管理）", "熟练管理"),
                ("- 「A」——B(别写成:\"deep learning\")", "deep learning"),
                ("- 「A」——B （别写成：「x」） ", "x")):
            with self.subTest(line=line):
                self.assertEqual(one(line).get("overclaim"), want)

    def test_a_gap_without_the_tail_is_untouched(self):
        g = one("- 「英语口语」——读写可以，口语不行")
        self.assertNotIn("overclaim", g)
        self.assertEqual(g["detail"], "读写可以，口语不行")

    def test_an_empty_tail_is_not_a_finding(self):
        """只剩标点的「不能写成」印到屏幕上比不印更糟 —— 认不出就整句别动。"""
        for line in ("- 「A」——B（别写成：）", "- 「A」——B（别写成：「」）"):
            with self.subTest(line=line):
                g = one(line)
                self.assertNotIn("overclaim", g)
                self.assertIn("别写成", g["detail"],
                              "没认出来就别把它从 detail 里剥掉 —— 那是丢数据")

    def test_the_explanation_after_the_quote_goes_back_to_detail(self):
        """引号里那句才是「不能写成」的原话，后面那段解释是**能**写的实情。

        捕获是懒惰的，可收尾要求一个右括号 —— 引号后面还跟着解释时，
        那个 `」` 连同整段解释一起被卷进 `overclaim`。屏幕上就出现
        `有合规相关项目经验」；你做过的是…`：一个开不了口的引号，
        而且把实情划红成了「不能写成」。2026-08-31 在导出的真实快照里逮到。

        ⚠️ 用例里别写内部词：`parse_gaps` 出来的字要过 `plain()`，
        第一版按真实数据写了「这几个业务域」，被译成「这几个行业经验」，
        断言当场落空 —— 报的是这条守卫，错的是用例。
        """
        g = one("- 「有合规经验」——这几样你一个都沾不上"
                "（别写成：「有合规相关项目经验」；你做过的是产品与交付，"
                "不是合规业务本身）")
        self.assertEqual(g["overclaim"], "有合规相关项目经验")
        self.assertEqual(g["overclaim"].count("「"), g["overclaim"].count("」"),
                         "引号配不上对 —— 那句话断在半截")
        self.assertIn("你做过的是产品与交付", g["detail"],
                      "解释被吞了 —— 配平不许靠丢字")
        self.assertIn("这几样你一个都沾不上", g["detail"])

    def test_only_the_tail_is_taken(self):
        """括号在句子中间的不算 —— 那是正文的一部分。"""
        g = one("- 「A」——B（别写成：「x」）还有一句")
        self.assertNotIn("overclaim", g)

    def test_the_trailing_comma_goes_with_it(self):
        g = one("- 「A」——只调过 API，（别写成：「精通」）")
        self.assertEqual(g["detail"], "只调过 API")

    def test_the_table_shape_is_parsed_too(self):
        """**两种形状同一个判据。** 只给 bullet 剥的话，写成表格的那 52 份拿不到。"""
        got = ex.parse_gaps(
            "## 缺口\n| 缺口 | 严重程度 | 怎么讲 |\n|---|---|---|\n"
            "| 「带过团队」 | 中 | 带过 3 人（别写成：「熟练管理」） |\n")
        self.assertEqual(got[0]["overclaim"], "熟练管理")
        self.assertEqual(got[0]["detail"], "带过 3 人")
        self.assertEqual(got[0]["kind"], "中", "顺带别把严重程度弄丢了")

    def test_the_judge_has_one_home(self):
        """两支都调同一个函数，不许各写一份正则。"""
        self.assertEqual(EX.count("_overclaim_of("), 3,
                         "定义一次 + 两支各调一次 —— 多出来的那次多半是抄的")

    def test_the_reason_is_recorded(self):
        doc = flat(ex._overclaim_of.__doc__ or "")
        self.assertIn("面板把它划红单独排", doc)
        self.assertIn("2026-08-25", doc)


class TheSpecNowAsksForIt(unittest.TestCase):

    def _seg(self) -> str:
        i = SPEC.index("### 缺口")
        return SPEC[i:SPEC.index("### 职位真伪信号", i)]

    def _bullet(self) -> str:
        """这一节里**执行者照着写的那一行** —— 不含上面那段 `<!-- -->` 说明。

        第一版直接在整节里搜 `（别写成：「xxx」）`，而**说明块里也举了这个例子**：
        把正文那行的尾巴整个删掉，测试照样绿（2026-08-25 变异检验逮到）。
        注释满足断言，是这个仓库反复踩的形状。
        """
        seg = self._seg()
        i = seg.rindex("-->") + 3 if "-->" in seg else 0
        return seg[i:].lstrip()

    def test_the_line_format_shows_the_tail(self):
        self.assertIn("（别写成：「xxx」）", self._bullet(),
                      "正文那一行没给格式 —— 说明块里举过例子不算，"
                      "执行者照着写的是正文那一行")

    def test_the_comment_is_not_what_satisfies_it(self):
        """对照用例：切出来的那截真的不含说明块。"""
        self.assertNotIn("<!--", self._bullet())
        first = next(l for l in self._bullet().splitlines() if l.strip())
        self.assertTrue(first.startswith("- "),
                        f"切歪了 —— 切出来的第一行该是那条 bullet，实际是：{first[:40]}")

    def test_it_says_why_that_bracket_is_the_point(self):
        seg = flat(self._seg())
        self.assertIn("那个括号是这一节唯一的落地动作", seg)
        self.assertIn("别写『熟练 Python』", seg)

    def test_it_forbids_filling_the_format_for_its_own_sake(self):
        """**写不出来就不写。** 不然会冒出一批他根本不会写的假禁令。"""
        seg = flat(self._seg())
        self.assertIn("写不出来就不写这个括号", seg)
        self.assertIn("别为了填格式编一句他根本不会写的话", seg)

    def test_it_names_the_profile_rule_it_grounds(self):
        seg = flat(self._seg())
        self.assertIn("绝不含糊或夸大", seg)
        self.assertIn("绝不可写/说的表述", seg)

    def test_that_profile_rule_really_exists(self):
        """引的是模板里的原话 —— 它没了这两句就成了无源之谈。

        第一版引成了「绝不可在材料中含糊或夸大」，那是**活动用户自己**那份
        资料里的措辞（gitignore 的），模板里根本没有。引一份看不见的文件，
        换个用户就落空了。
        """
        tpl = (ROOT / "profile.example" / "candidate.md").read_text(encoding="utf-8")
        self.assertIn("绝不含糊或夸大", tpl)
        self.assertIn("**绝不可写/说的表述：**", tpl)
        self.assertIn("## 明确的能力边界", tpl)

    def test_it_records_that_the_chain_was_dead(self):
        seg = flat(self._seg())
        self.assertIn("258 个有缺口的岗里", seg)
        self.assertIn("只在示例数据里活着", seg)

    def test_the_bullet_line_still_says_the_old_rule(self):
        """「如实写，不美化」是这一节的本分，别被新格式挤掉。"""
        self.assertIn("如实写，不美化", self._seg())


class ThePanelEndOfTheChainIsIntact(unittest.TestCase):
    """这一头本来就在 —— 这次只是终于有东西喂给它了。别在补上游时碰坏它。"""

    def test_the_type_field_exists(self):
        self.assertIn("overclaim?: string;", TYPES)

    def test_the_section_heading_promises_it(self):
        self.assertIn("写材料时这几处不能吹", READOUT)

    def test_the_struck_through_branch_exists(self):
        i = READOUT.index("g.overclaim &&")
        seg = READOUT[i:i + 200]
        self.assertIn("不能写成", seg)
        self.assertIn("<s>", seg)

    def test_it_renders_nothing_when_there_is_none(self):
        """没这一格时不许渲染出「，不能写成「」」这种残句。"""
        self.assertIn("{g.overclaim && (", READOUT)


class TheSignalItLeansOnIsReal(unittest.TestCase):
    """现算：链路能通了 —— 拿真实评估跑一遍解析器。"""

    def _evals(self):
        p = ROOT / ".active_user"
        if not p.is_file():
            self.skipTest("没有活动用户")
        apps = (ROOT / "users" / p.read_text(encoding="utf-8").strip()
                / "documents" / "applications")
        if not apps.is_dir():
            self.skipTest("还没有深评")
        got = sorted(apps.glob("*/evaluation.md"))
        if len(got) < 20:
            self.skipTest(f"深评只有 {len(got)} 份")
        return got

    def test_the_parser_still_reads_the_existing_gaps(self):
        """**别为了加一格把原来的读坏了。** 存量一条都不许少。"""
        n = sum(len(ex.parse_gaps(f.read_text(encoding="utf-8", errors="replace")))
                for f in self._evals())
        self.assertGreater(n, 300, f"只解析出 {n} 条缺口 —— 存量被弄丢了")

    def test_no_existing_gap_accidentally_grew_the_field(self):
        """存量里没有人写过那个括号，所以这一格现在应该还是空的。

        哪天不空了，说明新跑的深评照着新格式写了 —— **那时这条会红**，
        而那正是该来更新这一节实测数的时候。
        """
        got = [g for f in self._evals()
               for g in ex.parse_gaps(f.read_text(encoding="utf-8", errors="replace"))
               if g.get("overclaim")]
        if got:
            self.skipTest(f"已经有 {len(got)} 条写了 —— 好事，实测数该更新了")
        self.assertEqual(got, [])


if __name__ == "__main__":
    unittest.main()
