import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.verify_pdf import (VerificationError, count_pages, parse_page_count,
                              run_tool, verify_pdf)


class CountPagesFallbackTests(unittest.TestCase):
    """`--pages` 不能因为 pdfinfo 缺席而误报。

    poppler 的 Windows 发行版常只带 pdftotext 不带 pdfinfo——2026-08-12 实测：
    10 份刚编译好的一页简历全被 `--pages 1` 判失败，肉眼再数才发现错误其实是
    「工具没装」不是「页数超标」。页数校验必须能退回 pdftotext 的换页符计数
    （它在**每一页**末尾输出一个 \\f，含最后一页），而文本层校验本来就依赖它。
    """

    @patch("tools.verify_pdf.run_tool")
    def test_falls_back_to_pdftotext_when_pdfinfo_is_missing(self, mock_run_tool):
        def fake(cmd):
            if cmd[0] == "pdfinfo":
                # **靠 `missing_tool` 这个字段，不靠错误文案。**
                # 原来这里造的是英文串，而 `count_pages` 也按串匹配 ——
                # 2026-08-23 把文案翻成中文时兜底当场就断了
                # （只有 pdftotext 没有 pdfinfo 的机器上 `--pages` 永远报错）。
                raise VerificationError(
                    "没装 pdfinfo（poppler 的一部分）—— 装上 poppler-utils 再跑",
                    missing_tool="pdfinfo")
            return "第一页的文字\f"
        mock_run_tool.side_effect = fake
        self.assertEqual(count_pages(Path("example.pdf")), 1)

    @patch("tools.verify_pdf.run_tool")
    def test_pdfinfo_failures_other_than_missing_still_raise(self, mock_run_tool):
        """pdfinfo 在但读不动文件 → 照常报错；换条路把坏文件放过去才是真事故。"""
        mock_run_tool.side_effect = VerificationError(
            "pdfinfo could not read the PDF: invalid PDF")
        with self.assertRaisesRegex(VerificationError, "invalid PDF"):
            count_pages(Path("example.pdf"))

    @patch("tools.verify_pdf.run_tool")
    def test_no_page_breaks_is_an_error_not_a_pass(self, mock_run_tool):
        """pdftotext 一个换页符都没给 → 报「数不出页数」，不许把 0 当成任何页数。"""
        def fake(cmd):
            if cmd[0] == "pdfinfo":
                raise VerificationError("没装 pdfinfo", missing_tool="pdfinfo")
            return ""
        mock_run_tool.side_effect = fake
        with self.assertRaisesRegex(VerificationError, "数不出页数"):
            count_pages(Path("example.pdf"))


class ParsePageCountTests(unittest.TestCase):
    def test_parses_pdfinfo_page_count(self):
        self.assertEqual(parse_page_count("Title: Example\nPages:          2\n"), 2)

    def test_rejects_output_without_page_count(self):
        with self.assertRaisesRegex(VerificationError, "输出里没有页数"):
            parse_page_count("Title: Example\n")


class VerifyPdfTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.pdf = Path(self.temp_dir.name) / "example.pdf"
        self.pdf.touch()

    def tearDown(self):
        self.temp_dir.cleanup()

    @patch("tools.verify_pdf.run_tool")
    def test_accepts_expected_pages_and_text(self, mock_run_tool):
        mock_run_tool.side_effect = [
            "Pages:          2\n",
            "Professional\nExperience   [your.email@example.com]\n",
        ]

        verify_pdf(
            self.pdf,
            expected_pages=2,
            min_chars=20,
            required_text=("Professional Experience", "[your.email@example.com]"),
        )

    @patch("tools.verify_pdf.run_tool")
    def test_rejects_wrong_page_count(self, mock_run_tool):
        mock_run_tool.return_value = "Pages:          3\n"

        with self.assertRaisesRegex(VerificationError, "页数应该是 2，实际 3"):
            verify_pdf(self.pdf, expected_pages=2)

    @patch("tools.verify_pdf.run_tool")
    def test_rejects_too_little_extractable_text(self, mock_run_tool):
        mock_run_tool.return_value = "short"

        with self.assertRaisesRegex(VerificationError, "至少要 20 个"):
            verify_pdf(self.pdf, min_chars=20)

    @patch("tools.verify_pdf.run_tool")
    def test_rejects_missing_required_text(self, mock_run_tool):
        mock_run_tool.return_value = "Readable text, but not the expected section."

        with self.assertRaisesRegex(VerificationError, "Professional Experience"):
            verify_pdf(self.pdf, required_text=("Professional Experience",))

    def test_rejects_missing_pdf(self):
        with self.assertRaisesRegex(VerificationError, "找不到这个 PDF"):
            verify_pdf(Path(self.temp_dir.name) / "missing.pdf")


class RunToolTests(unittest.TestCase):
    @patch("tools.verify_pdf.subprocess.run", side_effect=FileNotFoundError)
    def test_reports_missing_poppler_command(self, _mock_run):
        with self.assertRaisesRegex(VerificationError, "装上 poppler-utils"):
            run_tool(["pdftotext", "example.pdf", "-"])

    @patch("tools.verify_pdf.subprocess.run")
    def test_reports_unreadable_pdf(self, mock_run):
        mock_run.side_effect = subprocess.CalledProcessError(
            1, ["pdfinfo", "example.pdf"], stderr="invalid PDF"
        )

        with self.assertRaisesRegex(VerificationError, "invalid PDF"):
            run_tool(["pdfinfo", "example.pdf"])


if __name__ == "__main__":
    unittest.main()


class RunToolDecodingTests(unittest.TestCase):
    """run_tool 必须按 UTF-8 解码，而不是本地编码。

    verify_pdf 明确用 `pdftotext -enc UTF-8` 取文本，若解码时回落到本地编码，
    中文 Windows（cp936）上「张三」会被解成三个完全不同的字：--contains 在一份
    文字确实存在的 PDF 上报 missing、--min-chars 也数错。既有用例全部 mock 掉了
    run_tool，所以从来没有走过真实解码这条路。
    """

    def test_invalid_bytes_still_return_a_string(self):
        """无效字节不得让解码在 subprocess 读取线程里抛错。

        严格解码时那个异常没人接：run_tool 直接返回 None，下游 normalize_text(None)
        再 AttributeError，而用户看到的是一段裸 traceback。
        """
        import sys
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as td:
            emitter = Path(td) / "emit.py"
            emitter.write_text(
                "import sys\n"
                "sys.stdout.buffer.write(bytes([0x54, 0x69, 0x74, 0x6c, 0x65, 0xff]))\n",
                encoding="utf-8")
            out = run_tool([sys.executable, str(emitter)])
        self.assertIsInstance(out, str)
        self.assertTrue(out.startswith("Title"))

    def test_utf8_output_is_decoded_as_utf8(self):
        import sys
        out = run_tool([sys.executable, "-c",
                        'import sys; sys.stdout.buffer.write("张三 李四".encode("utf-8"))'])
        self.assertEqual(out, "张三 李四")

