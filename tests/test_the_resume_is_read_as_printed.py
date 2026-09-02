# -*- coding: utf-8 -*-
"""简历正文是四条对外渠道里最后一条没查的 —— 而它拖到现在不是忘了。

`_cli.STYLE_BANS` 的注释与 `audit_pipeline` 里都记着同一段：照 `.typ` 源文件扫
（2026-08-24 实测 17 份、41 处命中）——

    25 处落在 Typst 注释里 —— 全是「对齐」，说的是排版，**永远不进 PDF**
    15 处是同一句话       —— 那句被复制进 15 份定制版，按份计数会把
                            一句话报成 15 个问题
     1 处是真的

**六成是排版注释。** 当时写下的方子是：要接就得拿**渲染出来的文本**当输入，
并且**按不同的句子去重、不按文件数**。

## 照方子做完（2026-08-27）

17 份 PDF 全部抽得出文本，不同的句子里踩线的 **5 句**：「AI 深度参与」
（空心动词）那一句被复制进 12 份、另外三句各 1 份、外加一处「闭环」。
41 → 5，而且每一句都指得出该改哪儿。

## 顺带抓到一个真缺陷

同一次抽取里发现 `main-长版.pdf` 印着「1 万\\+ GitHub stars」—— 一个**可见的
反斜杠**。源头是 Typst 正文里写了 `\\+`，而同一个符号在高亮正则串里
（`\\\\+`）是对的，抄来抄去混进了正文。这类错**编译不报**、预览不细看也不
显眼，而读到它的是招聘方。当天改掉了；这条检查留着防下一次。

## 两件事在同一次抽取里报

抽 PDF 要起子进程，17 份约 0.4 秒。分成两条检查就要抽两遍 —— 而它们看的是
同一份文本。所以一个函数返回两条判词。
"""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import audit_pipeline as ap  # noqa: E402
import verify_pdf as vp  # noqa: E402

SRC = (ROOT / "tools" / "audit_pipeline.py").read_text(encoding="utf-8")
BS = chr(92)


def _run(text, files=("main.pdf",)):
    """拿一段构造的「渲染文本」跑这条检查。"""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        d = root / "users" / "u" / "resume"
        d.mkdir(parents=True)
        for name in files:
            (d / name).write_bytes(b"%PDF-1.4 fake")
        with mock.patch.object(ap, "ROOT", root), \
             mock.patch.object(ap, "_USER", ["u"]), \
             mock.patch("verify_pdf.run_tool", lambda cmd: text):
            return ap.check_resume_body_keeps_the_style_rules({}, {})


def _titles(got):
    return [t for _lvl, t, _m in got]


class TheInputIsWhatGetsPrinted(unittest.TestCase):
    """判据的全部价值在这一点上：读 PDF，不读 .typc。"""

    def test_it_shells_out_to_pdftotext_with_the_encoding_flag(self):
        i = SRC.index("def check_resume_body_keeps_the_style_rules(")
        end = SRC.find("\ndef ", i + 10)
        seg = SRC[i:end if end > 0 else len(SRC)]
        self.assertIn("pdftotext", seg)
        self.assertIn('"-enc", "UTF-8"', seg,
                      "少了 -enc UTF-8：中文 Windows 上抽出来的会是一份「没有汉字」的文本")

    def test_it_borrows_the_existing_reader(self):
        """`verify_pdf.run_tool` 早就把编码那个坑处理过了 —— 别再起一个读法。"""
        i = SRC.index("def check_resume_body_keeps_the_style_rules(")
        end = SRC.find("\ndef ", i + 10)
        self.assertIn("run_tool", SRC[i:end if end > 0 else len(SRC)])

    def test_a_missing_tool_says_it_did_not_check(self):
        """抽不出来要说「没查」，**不是「没问题」**。"""
        def boom(cmd):
            raise vp.VerificationError("没装 pdftotext", missing_tool="pdftotext")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            d = root / "users" / "u" / "resume"
            d.mkdir(parents=True)
            (d / "main.pdf").write_bytes(b"%PDF-1.4 fake")
            with mock.patch.object(ap, "ROOT", root), \
                 mock.patch.object(ap, "_USER", ["u"]), \
                 mock.patch("verify_pdf.run_tool", boom):
                got = ap.check_resume_body_keeps_the_style_rules({}, {})
        self.assertTrue(got)
        self.assertIn("没查", got[0][1])

    def test_no_pdfs_is_silent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "users" / "u").mkdir(parents=True)
            with mock.patch.object(ap, "ROOT", root), \
                 mock.patch.object(ap, "_USER", ["u"]):
                self.assertEqual(ap.check_resume_body_keeps_the_style_rules({}, {}), [])


class ItCountsSentencesNotFiles(unittest.TestCase):
    """这是方子里的第二条，也是 41 → 5 的那一半。"""

    LINE = "· 把 AI 深度参与下的交付流程标准化。\n"

    def test_one_sentence_in_many_files_is_one_finding(self):
        got = _run(self.LINE, files=("main.pdf", "a.pdf", "b.pdf", "c.pdf"))
        msg = next(m for _l, t, m in got if "改写" in t)
        self.assertIn("1 句", msg, f"按文件数报了：{msg}")
        self.assertIn("4 份里", msg, "没说这一句摊在几份上 —— 那是改一次能修几份")

    def test_two_different_sentences_are_two(self):
        got = _run("· 把 AI 深度参与下的流程标准化。\n· 把链路闭环掉。\n")
        msg = next(m for _l, t, m in got if "改写" in t)
        self.assertIn("2 句", msg)

    def test_a_clean_resume_says_nothing(self):
        self.assertEqual(_run("· 一年做了 40 个开源项目，累计 1 万+ stars。\n"), [])


class AStrayBackslashIsCaught(unittest.TestCase):
    """编译不报、预览不显眼，而读到它的是招聘方。"""

    def test_it_fires(self):
        got = _run("· 已交付 1 万" + BS + "+ GitHub stars。\n")
        self.assertIn("简历正文：反斜杠印到纸上了", _titles(got))

    def test_it_quotes_the_surroundings(self):
        msg = next(m for _l, t, m in _run("· 已交付 1 万" + BS + "+ GitHub stars。\n")
                   if "反斜杠" in t)
        self.assertIn(BS, msg, "报了却不给上下文 —— 用户不知道去源文件里找哪一行")
        self.assertIn("main.pdf", msg, "没说是哪一份")

    def test_a_clean_resume_has_none(self):
        self.assertNotIn("简历正文：反斜杠印到纸上了",
                         _titles(_run("· 累计 1 万+ GitHub stars。\n")))

    def test_it_is_reported_even_when_the_style_is_clean(self):
        """两件事互不依赖：文风干净的简历照样可能印着转义符。"""
        got = _run("· 累计 1 万" + BS + "+ GitHub stars。\n")
        self.assertEqual(_titles(got), ["简历正文：反斜杠印到纸上了"])

    def test_both_come_from_one_extraction(self):
        """抽 PDF 要起子进程。分成两条检查就要抽两遍，而看的是同一份文本。"""
        got = _run("· 把链路闭环掉。\n· 已交付 1 万" + BS + "+ stars。\n")
        self.assertEqual(len(got), 2, f"两件事没有一起报出来：{_titles(got)}")


class ItIsRegistered(unittest.TestCase):
    def test_the_check_is_in_the_list(self):
        uses = [ln for ln in SRC.splitlines()
                if "check_resume_body_keeps_the_style_rules" in ln
                and not ln.lstrip().startswith("def ")]
        self.assertTrue(uses, "写了检查却没挂进清单")
        self.assertTrue(any("(" in ln and "," in ln for ln in uses), uses)

    def test_the_reason_it_waited_is_on_record(self):
        i = SRC.index("def check_resume_body_keeps_the_style_rules(")
        end = SRC.find("\ndef ", i + 10)
        seg = SRC[i:end if end > 0 else len(SRC)]
        self.assertIn("41", seg, "没记下照源文件扫是多少处")
        self.assertIn("25", seg, "没记下其中多少处是排版注释")
        self.assertIn("按不同的句子去重", seg)


if __name__ == "__main__":
    unittest.main()
