# -*- coding: utf-8 -*-
"""`03-writing-style.md` 有一张写着「出现即改写」的词表 —— 而没有任何东西在验它。

`06-outreach-templates.md` 的五条铁律有机械检查器（`_cli.greeting_problems`，
面板复制按钮旁印提示、审计全库汇总）。`03` 的「中文文案的 AI 味清单」同样是
一张**逐词列出来**的表，标题就写着「出现即改写」，却一条都没进检查器 ——
`_cli` 里只有 `06` 那张表里的「套话开头」四个词。

实测活动用户 2026-08-23，**只看可粘贴的那段开场白**（不含给用户自己看的注解行）：
236 份里 **17 份（7%）**命中 —— 赋能 6、闭环 5、打法 4、优秀的 1、对齐 1。

## 先量对了再做

第一版扫的是整个 `outreach.md`，得到 23 份 —— 而那里面多数命中在**注解行**
（「对方回话后再对齐」这类给用户看的话，不是发给 HR 的）和**岗位名**里
（有个岗标题本身就叫「…有 AI 赋能案例…」）。`03` 管的是**对外文案**，
注解不算。换成消费方真正用的那段（`build_dashboard` 解析出的 `greeting`）
才是 17 份。**判不准的扫描器比没有更坏** —— 这个仓库为此删过一个。

## 两份词表不合并

`GREETING_BANS` 的出处是 `06` 渠道 1 那张表、**只管渠道 1**；
`STYLE_BANS` 的出处是 `03`、管**所有对外文案**。合成一份之后就说不清
某个词是从哪条规则来的 —— 那正是 `GREETING_BANS` 自己的注释记着的分叉事故
（同一件事一边报 32 份、一边报 17 份）。

## 覆盖不全要说出来

`03` 同样约束邮件、网申自评、求职信和简历正文。2026-08-27 之前**机械检查只有
开场白这一处**；那天邮件 / 网申自评 / 求职信 / 内推请托接上了 `style_hits`、
简历正文接上了渲染文本那条路，四条渠道现在都有检查器。

**但那句自陈仍然要在**：它说的是「还没查到的地方要自己说出来」，
而不是某一天还差几处。下面钉的是那句判词（「这是覆盖不全，不是豁免」）
加上它当下点名的那一处，不是钉「只有开场白」这个实情。
"""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import _cli  # noqa: E402

WS = (ROOT / "workflows" / "reference"
      / "03-writing-style.md").read_text(encoding="utf-8")
CLI = (ROOT / "tools" / "_cli.py").read_text(encoding="utf-8")
AUDIT = (ROOT / "tools" / "audit_pipeline.py").read_text(encoding="utf-8")


def ai_flavour_words() -> set:
    """`03` 那一节里逐词列出来的黑话 / 空心动词 / 万能形容词。"""
    i = WS.index("## 中文文案的 AI 味清单")
    seg = WS[i:WS.index("**注意：中文里的破折号", i)]
    # **先把续行接回去。** 三行里有两行是折行的（`顶层设计、生态位` 在下一行、
    # `否则删掉` 在下一行）—— 只读第一行会漏掉每张表的最后一两个词，
    # 而「表里多出来的词」那条断言就会把它们当成凭空发明的（第一版实测漏了 4 个）。
    items = re.split(r"^(?=- \*\*)", seg, flags=re.M)
    out = set()
    for item in items:
        # **类名从文档派生，不许写死。** 第一版这里是
        # `(互联网黑话|空心动词|万能形容词)` —— 那是**拿要验证的答案去过滤
        # 输入**：文档那一侧先被裁成代码已有的三类，第四类根本进不了
        # `doc` 集合，于是「文档里有、表里没有」永远是空集。
        #
        # 实测代价（2026-08-31）：`03` 这一节列的是**四类**，
        # 「求职套话」那一类整类没有检查器，而下面那条守卫一直绿着。
        # 同一课本文件的 `_cap_bands` 记过一次（「第一版写成只保留
        # 80/60/40」），换个地方又犯了一遍。
        m = re.match(r"- \*\*([^*]+)\*\*[：:](.+)",
                     " ".join(item.split()), re.S)
        if not m:
            continue
        # `——` 后面是解释，不是词；括注同理。
        body = re.split(r"——", m.group(2))[0]
        body = re.sub(r"（[^）]*）", "", body)
        # `/` 也是分隔符：文档里写「我深信/我坚信」是两个词。
        out |= {w.strip() for w in re.split(r"[、,/]", body) if w.strip()}
    return out


def ai_flavour_categories() -> dict:
    """`03` 那一节的 `类名 -> {词}`。类名从文档读，不写死。"""
    i = WS.index("## 中文文案的 AI 味清单")
    seg = WS[i:WS.index("**注意：中文里的破折号", i)]
    out = {}
    for item in re.split(r"^(?=- \*\*)", seg, flags=re.M):
        m = re.match(r"- \*\*([^*]+)\*\*[：:](.+)",
                     " ".join(item.split()), re.S)
        if not m:
            continue
        body = re.sub(r"（[^）]*）", "", re.split(r"——", m.group(2))[0])
        out[m.group(1)] = {w.strip() for w in re.split(r"[、,/]", body)
                           if w.strip()}
    return out


def _all_banned_words() -> set:
    """两张表的并集 —— `03` 的词允许落在其中任意一张。"""
    return ({w for ws in _cli.STYLE_BANS.values() for w in ws}
            | {w for ws in _cli.GREETING_BANS.values() for w in ws})


def _covered(doc_word: str, table: set) -> bool:
    """表里存的可以是文档那个词的前缀（`贵司平台` 盖住 `贵司平台好`）。"""
    return any(w in doc_word for w in table)


class TheListIsMechanicallyChecked(unittest.TestCase):
    def test_the_constant_exists(self):
        self.assertTrue(hasattr(_cli, "STYLE_BANS"),
                        "`03` 的「AI 味清单」仍然没有机械检查")

    def test_every_category_in_the_document_is_covered(self):
        """**类名也从文档派生。** 这条原来叫「三类」并写死那三个名字 ——
        名字里就把答案说出来了，文档加一类它不会红。

        `求职套话` 那一类里有两个词（`贵司平台` / `深受吸引`）住在
        `GREETING_BANS.套话开头`，那是 `06` 那张表的地盘，两张表不合并
        （理由见 `TheTwoTablesStaySeparate`）。所以这里认「类名在
        `STYLE_BANS` 里」**或**「文档那一类的词全被两张表合起来盖住」。
        """
        cats = ai_flavour_categories()
        self.assertGreaterEqual(len(cats), 4,
                                f"从文档里只解析出 {len(cats)} 类")
        both = _all_banned_words()
        for cat, words in sorted(cats.items()):
            with self.subTest(cat):
                if cat in _cli.STYLE_BANS:
                    continue
                un = sorted(w for w in words if not _covered(w, both))
                self.assertEqual(
                    un, [],
                    f"「{cat}」这一类既不在 STYLE_BANS 里，"
                    f"这几个词也没被任何一张表盖住：{un}")

    def test_every_word_in_the_document_is_in_the_table(self):
        """**词表就是判据。** 漏一个词，那个词就永远不会被报出来。"""
        doc = ai_flavour_words()
        self.assertGreaterEqual(len(doc), 15, f"从文档里只解析出 {len(doc)} 个词")
        # **比的是两张表的并集。** `03` 那一节里的 `贵司平台好` /
        # `深受吸引` 住在 `GREETING_BANS`（`06` 的地盘），只比
        # `STYLE_BANS` 会把它们报成漏掉的。
        both = _all_banned_words()
        missing = sorted(w for w in doc if not _covered(w, both))
        self.assertEqual(missing, [], f"文档里有、两张表都没有：{missing}")

    def test_the_table_invents_nothing(self):
        """反过来也要成立 —— 表里多出来的词在文档里查无出处。"""
        doc = ai_flavour_words()
        table = {w for ws in _cli.STYLE_BANS.values() for w in ws}
        # 表里存的可以是文档那个词的**前缀**（`贵司平台` ⊂ `贵司平台好`），
        # 所以反向也按包含判，不按相等判。
        extra = sorted(w for w in table
                       if not any(w in d for d in doc))
        self.assertEqual(extra, [], f"表里有、文档里没有：{extra}")

    def test_the_checker_reports_them(self):
        probs = _cli.greeting_problems(
            "您好，从场景定义到评测闭环都是我做的，这套打法我完整跑过。")
        self.assertIn("「闭环」是互联网黑话", probs)
        self.assertIn("「打法」是互联网黑话", probs)

    def test_a_clean_greeting_stays_clean(self):
        """误报一次，整条检查就会被忽略。"""
        self.assertEqual(
            _cli.greeting_problems(
                "您好，做过 N 万用户的产品。想问下这个岗的分析对象是什么？"), [])

    def test_the_five_rules_still_fire(self):
        """新加的不能把原来那五类挤掉。"""
        probs = _cli.greeting_problems("您好，看到贵司在招，我目前离职随时到岗。")
        self.assertTrue(any("开场铺垫" in p for p in probs))
        self.assertTrue(any("抢答到岗时间" in p for p in probs))


class TheTwoTablesStaySeparate(unittest.TestCase):
    """出处不同、适用范围不同 —— 合并就说不清某个词是哪条规则来的。"""

    def test_they_are_two_constants(self):
        self.assertIsNot(_cli.STYLE_BANS, _cli.GREETING_BANS)

    def test_neither_absorbs_the_other(self):
        """**别只验「不是同一个对象」。** `STYLE_BANS = {**GREETING_BANS, ...}`
        是两个对象，却把两份判据揉成了一份 —— 那正是要防的事。"""
        for cat in _cli.GREETING_BANS:
            with self.subTest(cat=cat):
                self.assertNotIn(cat, _cli.STYLE_BANS,
                                 f"`{cat}` 同时在两份表里 —— 合并了")

    def test_no_word_is_in_both(self):
        a = {w for ws in _cli.GREETING_BANS.values() for w in ws}
        b = {w for ws in _cli.STYLE_BANS.values() for w in ws}
        self.assertEqual(sorted(a & b), [],
                         "同一个词进了两份表 —— 会被报两次，也说不清判据在哪")

    def test_the_provenance_is_written_down(self):
        i = CLI.index("STYLE_BANS = {")
        seg = " ".join(CLI[max(0, i - 1500):i].split())
        self.assertRegex(seg, r"和上面那份不是同一份，别合并")
        # **要那句「正本是 03」，不是文件名出现过。** 窗口开头那行标题里就带着
        # 文件名，光验文件名的话，把「这一份的正本是 03」删掉照样绿（变异实测）。
        self.assertRegex(seg, r"这一份的正本是 `03`")
        self.assertRegex(seg, r"`GREETING_BANS` 抄的是 `06`")

    def test_the_shared_words_are_explained_away(self):
        """两张表在「套话」上重合了两个词，注释要把**重合到什么程度**说清。

        这条原来的说明是「`03` 的求职套话和 `06` 的套话开头**是同一批词**，
        不重复搬」，钉的是 `_cli` 里那句「没有搬过来」。
        **那个前提是错的：8 个词里只重合 2 个**（`贵司平台` / `深受吸引`），
        另外六个两张表都没有，于是整整一类「出现即改写」的词没有检查器。

        判据跟着改成钉**现在的事实**：重合的那两个留在 `GREETING_BANS`
        （不重复登记，否则开场白上报两遍），其余六个补进 `STYLE_BANS`，
        注释要说清这个分工。
        """
        flat = " ".join(CLI.split())
        self.assertRegex(flat, r"8 个词里 只重合 2 个|只重合 2 个",
                         "注释没说清重合到什么程度")
        self.assertIn("求职套话", _cli.STYLE_BANS,
                      "那六个没被任何一张表收")
        for w in ("贵司平台", "深受吸引"):
            with self.subTest(w):
                self.assertNotIn(
                    w, _cli.STYLE_BANS["求职套话"],
                    f"`{w}` 同时进了两张表 —— 开场白会报两遍")

    def test_the_measured_number_is_recorded(self):
        i = CLI.index("STYLE_BANS = {")
        seg = " ".join(CLI[max(0, i - 1500):i].split())
        # **日期要挨着那个数。** 上面 `GREETING_BANS` 的注释里也有一个
        # 2026-08-23（记的是词表分叉那件事）—— 全窗口找日期的话，
        # 把这里的日期删掉照样绿（变异实测）。
        self.assertRegex(
            seg, r"实测活动用户 2026-08-23：236 份可粘贴开场白里 \*\*17 份（7%）\*\*命中")

    def test_the_coverage_gap_is_stated(self):
        """只查了四条渠道里的一条。不说出来就成了沉默的截断。"""
        i = CLI.index("STYLE_BANS = {")
        seg = " ".join(CLI[max(0, i - 1500):i].split())
        # 同 `test_a_partial_check_says_so` 那一条：钉不变量，别钉某天的实情。
        # 2026-08-27 起四条渠道里三条接上了 `style_hits`，只剩简历正文。
        self.assertRegex(seg, r"这是覆盖不全，不是豁免")
        self.assertRegex(seg, r"简历正文仍然没有机械查")
        self.assertRegex(seg, r"这是覆盖不全，不是豁免")


class TheAuditNamesBothSources(unittest.TestCase):
    """报出 7 个类别却说「那五类、判据见 06」，是把人指去一张查不到的表。"""

    def _msg(self) -> str:
        """**从构造 `where` 那几行起切**，不是从 `return` 起 ——
        判据指向哪一份表是在 `return` **上面**算好的，从 `return` 切会漏掉
        （第一版实测两条断言当场落空）。"""
        i = AUDIT.index("_style = set(_cli.STYLE_BANS)")
        return AUDIT[i:AUDIT.index("修：重写那一句", i) + 200]

    def test_the_title_no_longer_says_five(self):
        self.assertNotIn("开场白踩了渠道 1 的铁律", AUDIT)
        self.assertIn('"开场白有不该出现的写法"', AUDIT)

    def test_the_registry_entry_matches(self):
        """标题在两处出现（检查函数、检查表）—— 改一处就对不上了。"""
        self.assertIn('("话术：开场白有不该出现的写法", '
                      'check_greeting_keeps_the_five_rules)', AUDIT)

    def test_it_cites_the_second_source_only_when_hit(self):
        """没踩到 `03` 那几类时不该硬提第二份表。"""
        seg = self._msg()
        self.assertIn("if hit_style else", seg)
        self.assertIn("03-writing-style.md 的「AI 味清单」", seg)

    def test_it_still_cites_the_first_source(self):
        self.assertIn("06-outreach-templates.md 渠道 1 那张表", self._msg())

    def test_the_reason_is_recorded(self):
        seg = " ".join(AUDIT[AUDIT.index("**两份词表，两个出处"):
                             AUDIT.index("_style = set(")].split())
        self.assertRegex(seg, r"它当场就成了错话")

    def test_the_existing_advice_survives(self):
        """**这条原来守的是一句已经被推翻的话。**

        它守的是「这些是已经写好、等着发出去的文件，不是待办」。那句话后来被
        实测推翻并删掉了：踩线的那批里四分之三**已经投出去或已下线**，
        「等着发出去」对它们是错的（来历记在 `check_greeting_keeps_the_five_rules`
        的说明里）。守卫却还在原地守那句错话 —— 于是删对了反而变红。

        **一句话被撤，守它的断言要跟着改成守替代它的那句**，而不是留在那儿
        逼下一个人把错话粘回去。下面守的是替代品：分档那一格，加上两条真正
        给出「怎么改」的建议。
        """
        seg = self._msg()
        self.assertNotIn("等着发出去的文件，不是待办", seg,
                         "这句话 2026-08-25 已撤（四分之三的文件已投出/已下线）")
        self.assertIn("还发得出去的只有", seg, "总数之外要给出能动的那一格")
        self.assertIn("第一行是会话列表里唯一看得见的那行", seg)
        self.assertIn("2026-08-17 裁定两边都不写", seg)
        self.assertIn("2026-08-17 裁定两边都不写", seg)


class TheDocumentSideIsIntact(unittest.TestCase):
    def test_the_section_still_exists(self):
        self.assertIn("## 中文文案的 AI 味清单（出现即改写）", WS)

    def test_the_dash_exemption_survives(self):
        """中文破折号不禁用 —— 这条不许被这次改动带进词表。"""
        self.assertIn("中文里的破折号（——）是正常标点，不禁用", WS)
        table = {w for ws in _cli.STYLE_BANS.values() for w in ws}
        self.assertNotIn("——", table)

    def test_the_scope_line_still_covers_all_copy(self):
        self.assertIn("本文件规定所有对外文案", WS)


if __name__ == "__main__":
    unittest.main()
