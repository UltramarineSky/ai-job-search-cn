# -*- coding: utf-8 -*-
"""`pdftotext` 不带 `-enc UTF-8`，中文简历抽出来就是一份「没有汉字」的文本。

`verify_pdf.run_tool` 的注释早就点过这个名：

> 必须显式指定 utf-8：`text=True` 默认按**本地**编码解码，而下面明确用
> `pdftotext -enc UTF-8` 要的就是 UTF-8。在中文 Windows（cp936）上，
> "张三" 会被解成三个完全不同的字……

**但那条知识住在函数内部，从外面调 `pdftotext` 的人看不到。** 2026-08-24
实测：为了核活动用户的简历，两次直接调 `pdftotext`（一次在 shell 里、一次在
Python 里），两次都漏了这个参数，两次都得到「汉字占比 0%」—— 而那两份 PDF
实际上有 716 和 1255 个汉字、0 个替换符。**差一点据此报出「他 19 份简历的
中文全都抽不出来、85 次投递发的等于白纸」这种灾难性的假警报。**

假警报的方向也值得说：它不是「漏报一个真问题」，是**凭空造一个不存在的
事故**，而且是最吓人的那种。看到这个结论的人第一反应会是重做全部简历。

## 所以这条扫两处

- **代码**：`tools/` 里每一次真的调 `pdftotext`，都要带 `-enc UTF-8`。
  实测补了一处：`verify_pdf` 数页数的退路（`pdfinfo` 缺席时数换页符）原来
  没带 —— 效果上无害（换页符在哪种编码下都是同一个字节），但同一个文件里
  两处写法不一致，迟早被抄走一份。
- **文档**：凡是让人**照着敲**的 `pdftotext` 命令行，都要带。工作流那几处
  本来就带着；漏的是 `AGENTS.md` 的能力对照表 —— 而那张表正是工具中立的
  执行者学「该跑什么」的权威入口。
"""
import pathlib
import re
import subprocess
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]

#: shell 写法：`pdftotext` 后面跟着一个 `-` 开头的参数，或一个 `.pdf` 路径。
#: **不能只看「pdftotext 后面有非空白」**：散文里的「pdftotext / Bun 不装也能用」
#: 会被当成调用（第一版实测 16 个误报，全是这种）。
_SHELL = re.compile(r"pdftotext(?:\s+-\S+|\s+\S*\.pdf)")
#: Python 列表写法：`run_tool(["pdftotext", …])`。**必须是列表的第一个元素** ——
#: 只认「引号包着的 pdftotext 后面跟逗号」会把 `{"key": "pdftotext", …}` 这种
#: 字典项也算进来（实测 `doctor.py` 就有一条，是环境自检的显示名，不是调用）。
_PYLIST = re.compile(r"\[\s*[\"']pdftotext[\"']\s*,")


def tracked(*suffixes) -> list:
    out = subprocess.run(["git", "ls-files"], capture_output=True, text=True,
                         cwd=str(ROOT)).stdout.split()
    return [ROOT / r for r in out if r.endswith(suffixes)
            and (ROOT / r).is_file()]


def invocations(paths) -> list:
    """[(相对路径, 行号, 这一行, 命令窗口)] —— 窗口含后两行，命令会续行。"""
    hits = []
    for p in paths:
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
        for i, ln in enumerate(lines):
            if _SHELL.search(ln) or _PYLIST.search(ln):
                hits.append((p.relative_to(ROOT).as_posix(), i + 1,
                             " ".join(ln.split()),
                             " ".join(" ".join(lines[i:i + 3]).split())))
    return hits


def missing_enc(hits) -> list:
    return [(f, n, ln) for f, n, ln, win in hits
            if not ("-enc" in win and "UTF-8" in win)]


class TheScannerActuallyFindsThings(unittest.TestCase):
    """控制用例：扫不到就是空跑，说出来，别假绿。"""

    def test_it_finds_the_known_invocations(self):
        hits = invocations(tracked(".py", ".md"))
        self.assertGreater(len(hits), 5,
                           "几乎没扫到 pdftotext 调用 —— 多半是写法变了，"
                           "回去看 `_SHELL` / `_PYLIST`")

    def test_it_does_not_flag_prose(self):
        """「pdftotext / Bun 不装完全能用」是散文，不是调用。"""
        hit = invocations([ROOT / "tools" / "doctor.py"])
        self.assertEqual(
            [h for h in hit if "shutil.which" in h[2]], [],
            "把 `shutil.which(\"pdftotext\")` 当成了调用")


class EveryCodeInvocationDeclaresIt(unittest.TestCase):
    def test_tools_are_clean(self):
        bad = missing_enc(invocations(tracked(".py")))
        bad = [b for b in bad if b[0].startswith("tools/")]
        self.assertEqual(bad, [],
                         f"这些地方调 pdftotext 没带 `-enc UTF-8`：{bad}")

    def test_the_page_count_fallback_carries_it(self):
        """实测补的就是这一处。"""
        src = (ROOT / "tools" / "verify_pdf.py").read_text(encoding="utf-8")
        i = src.index('.count("\\f")')
        self.assertIn('"-enc", "UTF-8"', src[max(0, i - 300):i])

    def test_the_text_extraction_still_carries_it(self):
        src = (ROOT / "tools" / "verify_pdf.py").read_text(encoding="utf-8")
        self.assertIn('["pdftotext", "-layout", "-enc", "UTF-8"', src)

    def test_run_tool_still_decodes_as_utf8(self):
        """两端要一致：命令按 UTF-8 输出，解码也按 UTF-8。少一边就白搭。"""
        src = (ROOT / "tools" / "verify_pdf.py").read_text(encoding="utf-8")
        i = src.index("def run_tool(")
        seg = src[i:src.index("\ndef ", i + 10)]
        self.assertIn('encoding="utf-8"', seg)
        self.assertIn("cp936", seg, "那条 cp936 的教训被删掉了")


class EveryDocumentedCommandDeclaresIt(unittest.TestCase):
    """文档里的命令是给人照着敲的 —— 敲下去的那一版必须是对的。"""

    def test_docs_are_clean(self):
        bad = missing_enc(invocations(tracked(".md")))
        self.assertEqual(bad, [],
                         f"这些文档里的 pdftotext 命令没带 `-enc UTF-8`：{bad}")

    def test_the_capability_table_names_the_flag(self):
        """工具中立的执行者只读这张表 —— 表里漏了，它就会敲一条错的。"""
        doc = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        i = doc.index("| PDF 编译与文本层校验 |")
        row = doc[i:doc.index("\n", i)]
        self.assertIn("pdftotext -layout -enc UTF-8", row)

    def test_the_capability_table_says_it_is_not_optional(self):
        doc = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        i = doc.index("| PDF 编译与文本层校验 |")
        row = doc[i:doc.index("\n", i)]
        self.assertIn("不是可选的", row)
        self.assertIn("cp936", row)

    def test_the_capability_table_says_what_goes_wrong(self):
        """只说「要带」，下一个人还是会觉得可有可无。"""
        doc = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        i = doc.index("| PDF 编译与文本层校验 |")
        row = doc[i:doc.index("\n", i)]
        self.assertIn("没有汉字", row)
        self.assertIn("假警报", row)

    def test_the_workflows_that_already_had_it_still_do(self):
        for rel, n in (("workflows/job-apply.md", 2),
                       ("workflows/job-resume.md", 1)):
            with self.subTest(rel=rel):
                txt = (ROOT / rel).read_text(encoding="utf-8")
                self.assertGreaterEqual(
                    txt.count("pdftotext -layout -enc UTF-8"), n)


class TheSignalItLeansOnIsReal(unittest.TestCase):
    """有 pdftotext 和真简历时验一次：带不带那个参数，结论确实相反。"""

    def _one_pdf(self):
        import shutil
        if not shutil.which("pdftotext"):
            self.skipTest("没装 pdftotext")
        p = ROOT / ".active_user"
        if not p.is_file():
            self.skipTest("没有活动用户")
        u = p.read_text(encoding="utf-8").strip()
        pdfs = sorted((ROOT / "users" / u / "resume").glob("*.pdf"))
        if not pdfs:
            self.skipTest("没有简历 PDF")
        return pdfs[0]

    @staticmethod
    def _cjk(text) -> int:
        return sum(1 for ch in text if "一" <= ch <= "鿿")

    def test_with_the_flag_the_chinese_is_there(self):
        import sys
        sys.path.insert(0, str(ROOT / "tools"))
        import verify_pdf as v
        txt = v.run_tool(["pdftotext", "-layout", "-enc", "UTF-8",
                          str(self._one_pdf()), "-"])
        self.assertGreater(self._cjk(txt), 100,
                           "带了参数还是抽不出汉字 —— 那不是编码问题，"
                           "是这份 PDF 真有毛病，去查字体嵌入")

    def test_the_ratio_clears_the_floor_by_a_lot(self):
        """离门槛太近的话，这条守卫就成了随机数。"""
        import sys
        sys.path.insert(0, str(ROOT / "tools"))
        import verify_pdf as v
        txt = v.run_tool(["pdftotext", "-layout", "-enc", "UTF-8",
                          str(self._one_pdf()), "-"])
        self.assertGreater(v.cjk_ratio(v.normalize_text(txt)),
                           v.CJK_FLOOR * 2)


if __name__ == "__main__":
    unittest.main()
