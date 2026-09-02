# -*- coding: utf-8 -*-
"""「管的是所有对外文案」—— 而它只扫开场白。简历没被扫，但那是有意的。

`audit_pipeline` 里那条注释写着：`_cli.STYLE_BANS` 来自 `03` 的「AI 味清单」，
**管的是所有对外文案**。而简历、求职信同样是对外文案，还更对外 —— 它们一个字
都没被扫过。读到那句话的人会以为覆盖到了。

## 但naive 地补上去是错的

实测活动用户 2026-08-24，拿这张表扫 17 份简历源文件（主简历 2 + 定制版 15），
命中 41 处：

    25 处在 Typst 注释里   全是「对齐」——「两处列表没对齐」「共用同一条对齐轴」，
                          **永远不进 PDF**
    15 处是同一句话        那句被复制进了 15 份定制版；按文件数报，
                          一句话就成了 15 个问题
     1 处是真的

**六成是排版注释。** 一条这样的检查上线，会一直喊狼来了，然后被人整条关掉 ——
那比没有更坏。

## 所以这一轮改的是那句话，不是加检查

把「适用范围」和「检查范围」分开写清，并留下真要接时的两个前提：
输入得是**渲染出来的文本**（`verify_pdf` 已经在取），去重要按**句子**、不按文件数。
"""
import pathlib
import re
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import _cli  # noqa: E402

AUDIT = (ROOT / "tools" / "audit_pipeline.py").read_text(encoding="utf-8")


def flat(s: str) -> str:
    s = " ".join(re.sub(r"^\s*>\s?", "", s, flags=re.M).split())
    return re.sub(r"(?<=[一-鿿，。；：、（）「」])"
                  r" +(?=[一-鿿，。；：、（）「」])", "", s)


def seg() -> str:
    i = AUDIT.index("两份词表，两个出处，报的时候要分得开")
    return flat(AUDIT[i:AUDIT.index("_style = set(", i)].replace("#", " "))


class TheScopeIsStatedHonestly(unittest.TestCase):
    def test_it_separates_the_two_scopes(self):
        self.assertRegex(
            seg(), r"\*\*「所有对外文案」是那张表的适用范围，不是这里的检查范围。\*\*")

    def test_it_says_the_resume_is_not_scanned(self):
        s = seg()
        self.assertRegex(s, r"这个检查只扫开场白")
        self.assertRegex(s, r"简历、求职信同样是对外文案")

    def test_it_says_the_omission_is_deliberate(self):
        """不说「有意的」，下一个人会当成待办直接补上去。"""
        self.assertRegex(seg(), r"\*\*这是有意的\*\*，不是漏了")

    def test_the_original_two_tables_note_survives(self):
        s = seg()
        self.assertRegex(s, r"两份词表，两个出处，报的时候要分得开")
        self.assertRegex(s, r"却把用户指去一张查不到「互联网黑话」的表")


class TheMeasurementBehindItIsRecorded(unittest.TestCase):
    def test_it_carries_the_split(self):
        s = seg()
        self.assertRegex(s, r"25 处落在 Typst 注释里")
        self.assertRegex(s, r"15 处是同一句话")
        self.assertRegex(s, r"1 处是真的")

    def test_it_names_the_headline_ratio(self):
        """一个比例比三个绝对数更容易被记住，也更难被稀释。"""
        self.assertRegex(seg(), r"\*\*照着源文件扫，六成是排版注释\*\*")

    def test_it_carries_the_date(self):
        self.assertIn("2026-08-24", seg())

    def test_it_says_what_a_bad_check_costs(self):
        """「误报多一点」听起来能忍 —— 要写清它的真实下场。"""
        self.assertRegex(seg(), r"一直喊狼来了，然后被人整条关掉")


class ItLeavesTheTwoPreconditionsForDoingItRight(unittest.TestCase):
    def test_it_names_the_right_input(self):
        s = seg()
        self.assertRegex(s, r"输入得是 \*\*渲染出来的文本\*\*|\*\*渲染出来的文本\*\*")
        self.assertIn("verify_pdf", s)

    def test_it_remembers_the_encoding_flag(self):
        """那个参数漏了，中文简历抽出来就是「没有汉字」——同一天栽过。"""
        self.assertIn("-enc UTF-8", seg())

    def test_it_says_to_dedupe_by_sentence(self):
        self.assertRegex(seg(), r"按「不同的句子」去重、不按文件数")


class TheTablesThemselvesAreIntact(unittest.TestCase):
    def test_the_style_list_still_covers_the_document(self):
        """**类名从 `03` 那一节读出来，不在这里写死一份。**

        这条原来叫「三类」并列着那三个名字。2026-08-31 实测：`03` 列的是
        **四类**，「求职套话」整类没有检查器 —— 而当时**三条测试**各自钉着
        「就是这三类」，把一个错答案抄了三份。抄件互相印证，看起来像被守住了。

        判据改成派生：文档有几类，就该盖住几类。重合的两个词
        （`贵司平台` / `深受吸引`）住在 `GREETING_BANS`，所以按**两张表的并集**
        判，且按包含判（表里可以只存前缀）。出处与实测见
        `test_the_ai_flavour_list_is_actually_checked`。
        """
        import re

        ws = (ROOT / "workflows" / "reference"
              / "03-writing-style.md").read_text(encoding="utf-8")
        i = ws.index("## 中文文案的 AI 味清单")
        body = ws[i:ws.index("**注意：中文里的破折号", i)]
        cats = set(re.findall(r"^- [*][*]([^*]+)[*][*][：:]", body, re.M))
        self.assertGreaterEqual(len(cats), 4,
                                f"从 03 只解析出 {len(cats)} 类，抽取式坏了")
        both = ({w for v in _cli.STYLE_BANS.values() for w in v}
                | {w for v in _cli.GREETING_BANS.values() for w in v})
        for item in re.split(r"^(?=- [*][*])", body, flags=re.M):
            m = re.match(r"- [*][*]([^*]+)[*][*][：:](.+)",
                         " ".join(item.split()), re.S)
            if not m or m.group(1) in _cli.STYLE_BANS:
                continue
            words = re.sub(r"（[^）]*）", "", re.split("——", m.group(2))[0])
            un = [w.strip() for w in re.split(r"[、,/]", words)
                  if w.strip() and not any(x in w for x in both)]
            with self.subTest(m.group(1)):
                self.assertEqual(
                    un, [],
                    f"03 的「{m.group(1)}」这一类，这几个词两张表都不查：{un}")

    def test_the_greeting_check_still_uses_both_tables(self):
        hits = _cli.greeting_hits("您好，我做过赋能抓手。期望 40k。")
        cats = {c for c, _ in hits}
        self.assertIn("互联网黑话", cats)
        self.assertIn("先谈钱", cats)

    def test_the_report_still_names_the_right_source_doc(self):
        # 锚在 `where` 的**赋值**上，不锚它第一个字面量 —— 2026-08-24 接进
        # 第三个出处时那串括号改了写法，这条当场 ValueError（不是 fail）。
        i = AUDIT.index('where = "，以及 ".join(')
        self.assertIn("03-writing-style.md 的「AI 味清单」", AUDIT[i:i + 400])


class TheSignalItLeansOnIsReal(unittest.TestCase):
    """有语料时验一次：注释里那批误报真的占多数。"""

    def _sources(self):
        p = ROOT / ".active_user"
        if not p.is_file():
            self.skipTest("没有活动用户")
        u = p.read_text(encoding="utf-8").strip()
        root = ROOT / "users" / u
        files = [root / "resume" / "main.typ"]
        files += sorted((root / "documents" / "applications").glob("*/resume.typ"))
        files = [f for f in files if f.is_file()]
        if len(files) < 3:
            self.skipTest("简历源文件太少")
        return files

    def test_comment_hits_outnumber_content_hits(self):
        words = [w for ws in _cli.STYLE_BANS.values() for w in ws]
        body = note = 0
        for f in self._sources():
            for ln in f.read_text(encoding="utf-8", errors="replace").splitlines():
                head, _, tail = ln.partition("//")
                body += sum(1 for w in words if w in head)
                note += sum(1 for w in words if w in tail)
        if body + note == 0:
            self.skipTest("这份语料里一个都没命中 —— 那这条注释的依据要重量")
        self.assertGreater(note, body,
                           f"注释里 {note} 处、正文里 {body} 处 —— "
                           f"「六成是排版注释」不再成立，重新量一次")

    def test_the_content_hits_are_one_repeated_sentence(self):
        """按文件数报会把一句话说成 N 个问题 —— 这条守着那个论断。"""
        words = [w for ws in _cli.STYLE_BANS.values() for w in ws]
        lines = set()
        for f in self._sources():
            for ln in f.read_text(encoding="utf-8", errors="replace").splitlines():
                head = ln.partition("//")[0]
                if any(w in head for w in words):
                    lines.add(" ".join(head.split()))
        if not lines:
            self.skipTest("正文里没有命中")
        self.assertLess(len(lines), len(self._sources()),
                        f"{len(lines)} 种不同的句子，跨 {len(self._sources())} 份文件 —— "
                        f"不再是「同一句被复制」，那句话要改")


class TheWarningReachesTheCopyButton(unittest.TestCase):
    """审计事后报一份清单，而**他要用这段话的时刻**在面板上。

    开场白早就查在那一下了（`greetingWarn` → 「发之前删掉：…」）。而紧挨着的
    邮件正文与网申自评**一个字的提示都没有** —— 直到 2026-08-31。

    实测那天：面板上 10 段网申自评里 **5 段**踩了 `03` 的铁律
    （互联网黑话「闭环」1、翻译腔 4），10 段邮件正文 0 段。也就是说
    **一半的网申自评可以被原样复制粘进表单，没有任何提示**。

    ## 判据不串味

    `06` 渠道 1 那五类禁区（开场铺垫、先谈钱、抢答到岗时间…）**只管开场白** ——
    那段 ⚠️ 明说的：「渠道 2（邮件）、3（网申自评）、4（求职信）不受此限」。
    所以这几段走的是 `style_problems`（只含 `03` 那两张表），不是
    `greeting_problems`。**两条方向都要钉**：03 的要报，06 的不许报。
    """

    def test_the_judge_only_carries_the_03_rules(self):
        got = _cli.style_problems("您好，看到这个岗，期望薪资 40k，随时到岗。")
        self.assertEqual(got, [],
                         "06 那五类禁区串进了邮件/网申的判据 —— "
                         "那几段本来就允许谈条件")

    def test_the_judge_does_catch_the_03_rules(self):
        got = _cli.style_problems("把实践沉淀成方法论沉淀，形成闭环。")
        self.assertTrue(got, "03 的词表在这条路上没生效")
        self.assertIn("互联网黑话", " ".join(got))

    def test_the_greeting_judge_still_carries_both(self):
        """控制用例：开场白那条不能被顺手改窄。"""
        got = _cli.greeting_problems("您好，看到这个岗，期望薪资 40k。")
        self.assertTrue(any("开场铺垫" in x for x in got), got)

    def test_the_wording_has_one_home(self):
        """两条路的措辞与截断只有一份（`_as_problems`）—— 否则同一块屏幕上两种说法。"""
        src = (ROOT / "tools" / "_cli.py").read_text(encoding="utf-8")
        self.assertEqual(src.count('f"「{w}」是{cat}"'), 1,
                         "「「X」是Y」这句措辞不止一份实现")
        self.assertEqual(src.count("条同类的，一并看一遍"), 1,
                         "截断提示不止一份实现")

    def test_the_export_emits_both_warnings(self):
        """**钉调用与赋值，不是钉名字出现过。**

        第一版只断言 `"style_problems" in ex_src` —— 把那行调用整个换成
        `_sp = []`，它照样绿：那个词还在**注释里**。变异当场照出来。
        """
        ex_src = (ROOT / "tools" / "export_web_data.py").read_text(encoding="utf-8")
        self.assertIn("_cli.style_problems(mats[_k])", ex_src,
                      "导出器没真去算这两段的警告")
        self.assertIn('mats[_k + "Warn"] = _sp', ex_src,
                      "算了但没写进 payload")
        for k in ("emailBody", "wangshen"):
            with self.subTest(k):
                self.assertIn('"' + k + '"', ex_src)

    def test_the_panel_renders_them_next_to_their_own_section(self):
        """**各自摆在自己那一段旁边**，不是堆在开场白那儿。"""
        sl = (ROOT / "web" / "src" / "components"
              / "JobReadout.tsx").read_text(encoding="utf-8")
        # **锚点要唯一。** 第一版用 `{m.emailBody}`，而它第一次出现是在复制按钮
        # 那一行（`<CopyIcon text={m.emailBody} …>`），窗口够不到下面的渲染段 ——
        # `index()` 取第一处，断言落在别处。用带 className 的整句当锚。
        for field, anchor in (
                ("emailBodyWarn", '<p className="greeting">{m.emailBody}</p>'),
                ("wangshenWarn", '<p className="greeting">{m.wangshen}</p>')):
            with self.subTest(field):
                # **钉渲染条件，不是钉字段名出现过。** 把条件换成
                # `{false && (` 时字段名还在里面，第一版照样绿。
                self.assertIn(f"(m.{field}?.length ?? 0) > 0", sl,
                              f"面板没按 {field} 的长度决定显不显示")
                self.assertEqual(sl.count(anchor), 1,
                                 f"锚点 {anchor} 不唯一，断言会落在别处")
                i = sl.index(anchor)
                self.assertIn(field, sl[i:i + 600],
                              f"{field} 没挨着它自己那一段")

    def test_the_type_declares_them(self):
        t = (ROOT / "web" / "src" / "types.ts").read_text(encoding="utf-8")
        for k in ("emailBodyWarn?: string[];", "wangshenWarn?: string[];"):
            with self.subTest(k):
                self.assertIn(k, t)


if __name__ == "__main__":
    unittest.main()
