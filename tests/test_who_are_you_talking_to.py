# -*- coding: utf-8 -*-
"""抬头那半句写反了，第二轮就走反 —— 而它只在事后的审计清单里说。

`06-outreach-templates.md`「渠道判定」那张表：**猎头**问薪资与到岗时间要直接答，
**HR 直招**不主动展开。也就是说「在跟谁说话」这半句决定的是**下一轮怎么说话**，
不是文风。

实测活动用户 2026-08-25（243 份话术）：

    没写是猎头还是直招        110 份
    **写反了**               **28 份**
    猎头岗对着顾问说「贵司」     9 份

审计一直在报这三个数。但审计是**事后**跑的一份清单，而这几条要在他
**按下「复制开场白」那一下**才有用 —— 那时他正要把这段话粘出去。
`greeting_problems` 早就在那个位置了（「发之前删掉：…」），这一条是它旁边缺的那半。

## 判据只留一份

`_cli.addressee_problem` 是正本，审计与面板都用它。审计原来自己留着
`_WRONG_ADDRESSEE` 与 `_head_of` —— 现在改成别名。两处各写一份的下场这个仓库
反复付过学费（同一类：`greeting_hits` 当初就是两份词表、同一类数出 32 与 17）。

## 「没判过」不是「不是猎头」

`viaHeadhunter` 为 `None` 时**只查「贵司」那一条**，不报「写反了」——
库里没判过，凭什么说他写反了。
"""
import pathlib
import re
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import _cli  # noqa: E402
import audit_pipeline as ap  # noqa: E402
import build_dashboard as bd  # noqa: E402

EX = (ROOT / "tools" / "export_web_data.py").read_text(encoding="utf-8")
AUDIT = (ROOT / "tools" / "audit_pipeline.py").read_text(encoding="utf-8")
CLI = (ROOT / "tools" / "_cli.py").read_text(encoding="utf-8")
JR = (ROOT / "web" / "src" / "components"
      / "JobReadout.tsx").read_text(encoding="utf-8")
TYPES = (ROOT / "web" / "src" / "types.ts").read_text(encoding="utf-8")
CSS = (ROOT / "web" / "src" / "theme" / "cockpit.css").read_text(encoding="utf-8")
TPL = (ROOT / "workflows" / "reference"
       / "06-outreach-templates.md").read_text(encoding="utf-8")


def flat(s: str) -> str:
    s = " ".join(re.sub(r"^\s*(?:>|#:?|//:?|\*)\s?", "", s, flags=re.M).split())
    return re.sub(r"(?<=[一-鿿，。；：、（）「」])"
                  r" +(?=[一-鿿，。；：、（）「」])", "", s)


class TheJudgementLivesInOnePlace(unittest.TestCase):
    def test_the_audit_uses_the_shared_one(self):
        """两处各写一份 —— 这个仓库为它反复付过学费。"""
        self.assertIs(ap._WRONG_ADDRESSEE, _cli.WRONG_ADDRESSEE)
        self.assertIs(ap._head_of, _cli.head_of)

    def test_the_audit_no_longer_keeps_a_copy(self):
        self.assertNotIn('_WRONG_ADDRESSEE = re.compile(', AUDIT)

    def test_it_says_where_the_original_is(self):
        i = AUDIT.index("_WRONG_ADDRESSEE = _cli.WRONG_ADDRESSEE")
        self.assertIn("正本在 `_cli`", AUDIT[max(0, i - 400):i])

    def test_the_export_uses_the_shared_one_too(self):
        self.assertIn("_cli.addressee_problem(", EX)


class TheHeaderIsParsed(unittest.TestCase):
    def test_it_cuts_at_the_first_section(self):
        self.assertEqual(_cli.head_of("抬头\n\n## 渠道 1\n正文"), "抬头\n")

    def test_no_section_means_all_of_it(self):
        self.assertEqual(_cli.head_of("只有抬头"), "只有抬头")

    def test_it_reads_both_kinds(self):
        self.assertEqual(_cli.addressee_said("对方是猎头顾问"), "猎头")
        self.assertEqual(_cli.addressee_said("企业直招"), "直招")
        self.assertEqual(_cli.addressee_said("非猎头"), "直招")
        self.assertEqual(_cli.addressee_said("什么都没写"), "")

    def test_the_parser_exposes_it(self):
        """面板拿不到原文，只拿得到解析结果 —— 抬头要跟着出来。"""
        got = bd.parse_outreach("- 对方是：猎头\n\n## 渠道 1：打招呼开场白\n\n你好")
        self.assertIn("猎头", got["head"])
        self.assertNotIn("你好", got["head"])


class TheProblemIsNamedInPlainChinese(unittest.TestCase):
    def test_a_wrong_kind_is_reported(self):
        got = _cli.addressee_problem("企业直招", "您好", True)
        self.assertIn("抬头写着「直招」", got)
        self.assertIn("库里是猎头", got)

    def test_it_says_what_goes_wrong(self):
        """只说「写反了」不够 —— 要说清后果，否则他不知道该不该管。"""
        self.assertIn("第二轮就走反了", _cli.addressee_problem("直招", "您好", True))

    def test_a_missing_kind_is_reported_with_the_answer(self):
        """既然库里知道答案，就顺手告诉他 —— 别让他再去查一次。"""
        got = _cli.addressee_problem("（什么都没写）", "您好", False)
        self.assertIn("抬头没说在跟谁说话", got)
        self.assertIn("直招", got)

    def test_a_correct_header_is_silent(self):
        self.assertEqual(_cli.addressee_problem("猎头代招", "您好", True), "")
        self.assertEqual(_cli.addressee_problem("企业直招", "您好", False), "")

    def test_guisi_to_a_consultant_is_reported(self):
        got = _cli.addressee_problem("猎头", "贵司在做的事我很感兴趣", True)
        self.assertIn("贵司", got)
        self.assertIn("能不能推", got)

    def test_guisi_to_a_direct_employer_is_fine(self):
        """对用人方说「贵司」没问题 —— 误报一次这条就会被整条忽略。"""
        self.assertEqual(
            _cli.addressee_problem("企业直招", "贵司在做的事我很感兴趣", False), "")

    def test_unknown_only_checks_the_guisi_half(self):
        """**没判过不是「不是猎头」。** 库里没判过，凭什么说他写反了。

        变异实测：把 `is not None` 换成 `True` 时，`None` 会被当成「直招」——
        上面那两个用例都还绿（一个抬头也写「直招」不冲突，一个只查前半句）。
        所以下面两条专门钉住那个分岔：抬头写「猎头」而库里没判过时，
        **不许报「写反了」**；抬头什么都没写时，**不许替它编一个档**。
        """
        self.assertEqual(_cli.addressee_problem("企业直招", "贵司如何", None), "")
        # ① 抬头写「猎头」+ 库里没判过 —— 把 None 当「直招」就会在这儿报错话
        got = _cli.addressee_problem("猎头代招", "您好", None)
        self.assertEqual(got, "", f"库里没判过却说他写反了：{got}")
        # ② 抬头什么都没写 —— 只能说「没说」，不许补一个「这个岗是 X」
        got = _cli.addressee_problem("（空）", "您好", None)
        self.assertIn("抬头没说在跟谁说话", got)
        self.assertNotIn("这个岗是", got, f"没判过却替它编了一个档：{got}")

    def test_both_problems_are_reported_together(self):
        got = _cli.addressee_problem("企业直招", "贵司很好", True)
        self.assertIn("第二轮就走反了", got)
        self.assertIn("贵司", got)

    def test_no_markdown_reaches_the_user(self):
        got = _cli.addressee_problem("企业直招", "贵司很好", True)
        self.assertNotIn("**", got)

    def test_no_framework_jargon(self):
        """这句话直接上屏 —— 内部词不许搬到台面上（`AGENTS.md`）。"""
        got = _cli.addressee_problem("企业直招", "贵司很好", True)
        for w in ("判词", "四维", "硬门", "台账", "短名单"):
            with self.subTest(w=w):
                self.assertNotIn(w, got)


class ItReachesThePanel(unittest.TestCase):
    def test_the_export_sets_the_field(self):
        self.assertIn('mats["addresseeWarn"] = _who', EX)

    def test_it_is_computed_next_to_the_greeting_check(self):
        """两条要在同一个地方说 —— 分开放，他会以为是两回事。"""
        a = EX.index('mats["greetingWarn"] = probs')
        b = EX.index('mats["addresseeWarn"] = _who')
        self.assertLess(abs(a - b), 900)

    def test_it_uses_the_parsed_header_not_the_raw_file(self):
        i = EX.index("_cli.addressee_problem(")
        self.assertIn('o.get("head")', EX[i:i + 200])

    def test_the_panel_renders_it(self):
        self.assertIn("{m.addresseeWarn && (", JR)

    def test_it_sits_by_the_copy_button(self):
        """判据与 `greetingWarn` 同一个位置 —— 那才是他要用这段话的时刻。"""
        a = JR.index("m.greetingWarn")
        b = JR.index("m.addresseeWarn")
        self.assertLess(abs(a - b), 1600)

    def test_the_two_warnings_look_different(self):
        """一个是「这段字里有该删的」，一个是「你可能对错了人」—— 两件事。"""
        self.assertIn(".addressee-warn {", CSS)
        self.assertIn("addressee-warn", JR)

    def test_the_type_says_what_it_decides(self):
        i = TYPES.index("addresseeWarn?: string;")
        seg = flat(TYPES[max(0, i - 700):i])
        self.assertRegex(seg, r"第二轮怎么说话")

    def test_the_reason_is_recorded_once(self):
        i = CLI.index("def addressee_problem(")
        seg = flat(CLI[i:CLI.index("def greeting_problems(", i)])
        self.assertRegex(seg, r"写反了\*\*\s*\*\*28 份\*\*|写反了.{0,6}28 份")
        self.assertRegex(seg, r"审计.{0,20}事后")
        self.assertIn("2026-08-25", seg)


class TheRuleItGuardsIsStillWritten(unittest.TestCase):
    def test_the_template_still_says_the_consultant_is_not_the_employer(self):
        """这一整条建立在它上面 —— 它没了，这条就成了我们自己发明的说法。"""
        self.assertRegex(flat(TPL), r"对面是顾问不是用人方")

    def test_the_template_still_splits_the_second_round(self):
        seg = flat(TPL)
        self.assertRegex(seg, r"猎头|顾问")
        self.assertRegex(seg, r"期望薪资|到岗时间")


class TheSignalItLeansOnIsReal(unittest.TestCase):
    """现算一遍：这批话术里真的有写反的。"""

    def _live(self):
        p = ROOT / "web" / "public" / "data.json"
        if not p.is_file():
            self.skipTest("还没导出过面板数据")
        import json
        d = json.loads(p.read_text(encoding="utf-8"))
        mats = [(j.get("company"), (j.get("materials") or {}))
                for j in d["jobs"] if j.get("materials")]
        if len(mats) < 20:
            self.skipTest("话术太少，比不出来")
        return mats

    def test_some_are_still_wrong(self):
        """一份都不报时这条链子就是空跑 —— 那时该确认是真修好了，还是判据坏了。"""
        mats = self._live()
        n = sum(1 for _, m in mats if m.get("addresseeWarn"))
        self.assertGreater(
            n, 0, "一份都没报 —— 要么真的都写对了（好事，去更新这一节的数），"
                  "要么 `addresseeWarn` 那条链子断了")

    def test_the_wrong_kind_half_actually_fires(self):
        """「没写」容易命中，「写反了」才是这条真正要抓的 —— 单独钉一次。"""
        mats = self._live()
        n = sum(1 for _, m in mats if "第二轮就走反了" in (m.get("addresseeWarn") or ""))
        if not n:
            self.skipTest("这批里没有写反的 —— 好事")
        self.assertGreater(n, 0)


if __name__ == "__main__":
    unittest.main()
