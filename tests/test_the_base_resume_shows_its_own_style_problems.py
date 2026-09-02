# -*- coding: utf-8 -*-
"""主简历里那一句空心动词进了 12 份定制版，而面板一个字不提。

自检从 2026-08-27 起在查这件事（「简历正文：有 03 说要改写的写法」），扫的是
**全部** 17 份 PDF，报出来的是「这一句在 12 份里」。而那 12 份定制版是从主简历
复制出去的 —— 实测 2026-08-31：主简历自己就带着那一句。

**这是这一页上一次编辑收益最大的那类提示**：在 `resume/main.typ` 改一次，
12 份定制版下次 `/job-cv` 重出时一起干净。而它此前只在全量自检里出现，
而全量自检他基本不跑。

面板的「你的基简历」那一块本来就是干这个的：它说「少一节」「资料里少填一项」，
都是「你手上这一份还差什么」，都配着该敲的命令。这一条并排放进去。

## 判据要拿渲染出来的字当输入

照 `.typ` 源文件扫，六成命中的是排版注释 —— 自检那条已经交过这笔学费。
所以走 `pdftotext`（实测一份 20ms）。**没装 poppler 就整条不出**：
缺依赖不是拒绝理由，但也不该拿一个查不了的结论去吓人。

## 只扫主简历这一份

定制版归 `/job-cv` 重出，而修法写在主简历上。扫全部 17 份是自检的事
（它还要数「这一句在几份里」），面板要的是「你现在该改哪一句」。
"""
import json
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tests"))

import _cli                     # noqa: E402
import export_web_data as ex    # noqa: E402
from _srcscan import code_of    # noqa: E402

SRC = (ROOT / "web" / "src" / "components"
       / "BaseResume.tsx").read_text(encoding="utf-8")
TYPES = (ROOT / "web" / "src" / "types.ts").read_text(encoding="utf-8")
AUDIT = (ROOT / "tools" / "audit_pipeline.py").read_text(encoding="utf-8")


class TheRowIsWrittenOnce(unittest.TestCase):
    """自检与面板印的是同一件事 —— 两份格式就是同一句话两种叫法。"""

    def test_both_go_through_it(self):
        self.assertIn("_cli.style_row(", AUDIT, "自检没走共用的行文")
        seg = code_of("tools/export_web_data.py", "def style_rows(")
        self.assertIn("_cli.style_row(", seg, "导出侧没走共用的行文")

    def test_it_says_the_word_the_category_and_the_line(self):
        got = _cli.style_row("空心动词", "深度参与", "· 发起「365 开源计划」")
        for must in ("深度参与", "空心动词", "365 开源计划"):
            with self.subTest(must):
                self.assertIn(must, got)

    def test_the_line_is_capped(self):
        """一句话可能很长，而这是要塞进一格的。"""
        got = _cli.style_row("空心动词", "深度参与", "啊" * 200)
        self.assertLess(len(got), 60, "没截 —— 这一格会被撑爆")

    def test_giving_the_line_is_the_point(self):
        """只给词不给句：一个词在两千字里搜不着，一句话找得到。"""
        self.assertNotEqual(_cli.style_row("空心动词", "深度参与", "某一句话"),
                            _cli.style_row("空心动词", "深度参与", "另一句话"))


class TheJudgeIsHonestAboutWhatItCanSee(unittest.TestCase):

    def test_a_missing_pdf_is_silent(self):
        """没有 PDF 不是问题，是没法查 —— 别拿查不了当结论。"""
        self.assertEqual(
            ex.base_resume_style(ROOT / "users" / "查无此人" / "x.pdf"), [])

    def test_it_reads_the_rendered_text_not_the_source(self):
        """照 .typ 扫六成是排版注释 —— 自检那条已经交过这笔学费。"""
        seg = code_of("tools/export_web_data.py", "def base_resume_style(")
        self.assertIn("pdftotext", seg)
        self.assertIn('"-enc", "UTF-8"', seg,
                      "少了 -enc UTF-8：中文 Windows 上抽出来会是一份「没有汉字」"
                      "的文本，据此下的结论是灾难性的假警报")

    def test_a_missing_poppler_does_not_break_the_export(self):
        """整个导出不能因为少一个可选工具就挂掉。"""
        seg = code_of("tools/export_web_data.py", "def base_resume_style(")
        self.assertIn("except Exception:", seg)
        self.assertIn("return []", seg)

    def test_the_same_sentence_is_not_reported_twice(self):
        """同一句在简历里出现两次是常态（正文一次、摘要一次），那是一处。

        ⚠️ 第一版查的是源码里有没有 `seen_line` 这个名字 —— 变异把判断条件
        删掉、名字留着，它照样绿。所以判据要落在**行为**上，而那要求
        `style_rows` 单独成函数（不然得先造一份 PDF 才喂得进去）。
        """
        t = "深度参与了这个项目的交付。深度参与了这个项目的交付。深度参与了另一个的交付。"
        self.assertEqual(len(ex.style_rows(t)), 2)

    def test_an_empty_text_is_not_a_finding(self):
        for empty in ("", None, "   "):
            with self.subTest(repr(empty)):
                self.assertEqual(ex.style_rows(empty), [])

    def test_a_clean_resume_says_nothing(self):
        self.assertEqual(ex.style_rows("带过五人团队，交付三个上线项目。"), [])


class ThePanelSaysItWhereTheResumeIs(unittest.TestCase):

    def test_the_type_declares_it(self):
        self.assertIn("styleWarn?: string[];", TYPES)

    def test_it_sits_with_the_other_two_material_gaps(self):
        anchor = "{(data.gateInputsMissing?.length ?? 0) > 0 && ("
        self.assertEqual(SRC.count(anchor), 1, "锚点不唯一")
        i = SRC.index(anchor)
        self.assertIn("data.styleWarn", SRC[max(0, i - 1400):i],
                      "没和「少一节 / 少填一项」并排 —— 那三条是同一类事")

    def test_it_is_conditional_not_always_on(self):
        self.assertIn("{(data.styleWarn?.length ?? 0) > 0 && (", SRC,
                      "一条永远显示的提醒等于没有提醒")

    def test_it_gives_the_command(self):
        # 锚唯一的那一处：条件式只有一个，另外两处是渲染那几行。
        anchor = "{(data.styleWarn?.length ?? 0) > 0 && ("
        self.assertEqual(SRC.count(anchor), 1, "锚点不唯一")
        i = SRC.index(anchor)
        self.assertIn("/job-resume", SRC[i:i + 700],
                      "说了有问题，没说该敲什么")


class TheSignalIsReal(unittest.TestCase):
    """有语料时验一次：这一条不是凭空加的。"""

    def _base(self):
        p = ROOT / "web" / "public" / "data.json"
        if not p.is_file():
            self.skipTest("还没导出过面板数据")
        return json.loads(p.read_text(encoding="utf-8")).get("baseResume") or {}

    def test_the_field_survives_the_export(self):
        b = self._base()
        if not b:
            self.skipTest("这份语料里没有基简历")
        if "styleWarn" not in b:
            self.skipTest("这份主简历没踩线（那很好），或者没装 poppler")
        self.assertTrue(all(isinstance(x, str) and x for x in b["styleWarn"]))

    def test_it_stays_a_short_list(self):
        """一整页警告等于没有警告 —— 真到那一步该报的是「这份简历要重写」。"""
        w = self._base().get("styleWarn") or []
        if not w:
            self.skipTest("这份主简历没踩线")
        self.assertLess(len(w), 15, f"报了 {len(w)} 句，那一格会变成一堵墙")


if __name__ == "__main__":
    unittest.main()
