"""`05-cv-templates.md` 里的用法示例，必须真的能用当前模板编译出来。

## 文档会悄悄落后于实现

这份文件是 `/job-apply` **起草简历前必读**的那一份（`apply.md` 5b：「动手前先读取
`05-cv-templates.md`：裁剪优先级、页预算、七段顺序都写在那里」）。它写错了，
每一次定制简历都跟着错。

实测抓到过一次，而且是**改实现没改文档**：

    - **`·` 开头的行是普通文本**，不是 Typst 列表语法。这样写是刻意的：
      中文简历的项目符号用 `·` 比 `-` 更常见，且避免 Typst 列表的默认缩进。

模板早就改成了原生列表 —— `set list(marker: text(fill: 淡)[·])`，`entry` 内部
是 `list(..要点)`。**看起来是 `·`，写的时候是 `-`。** 文档教的是相反的写法。

差别在**续行**（实测两种写法各编译一次比对过）：原生列表的第二行悬挂缩进、
对齐在正文下方；手写「`· 文字`」的第二行顶格，和 `·` 对齐——一条要点只要超过
一行，扫读时就会被当成新的一条。而简历上超过一行的要点是常态。

## 判据

把文档里那段 ```typst 示例原样抽出来，配上当前的 `resume/template.typ` 编译一次。
**这条不是在检查措辞，是在检查文档还成不成立**——签名改了、导出的函数改了、
参数名改了，示例当场编译失败。

没装 typst 就跳过（本仓库对它是软依赖，见 `AGENTS.md` 能力对照表）。
"""

import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOC = ROOT / "workflows" / "reference" / "05-cv-templates.md"
TEMPLATE = ROOT / "resume" / "template.typ"


def typst_available() -> bool:
    return shutil.which("typst") is not None


def doc_example() -> str:
    m = re.search(r"```typst\n(.*?)```", DOC.read_text(encoding="utf-8"), re.S)
    return m.group(1) if m else ""


class TheDocumentedUsageStillWorks(unittest.TestCase):

    def test_there_is_an_example(self):
        """控制用例：文档里真有那段示例，否则下面那条是空跑。"""
        ex = doc_example()
        self.assertIn("resume.with", ex,
                      "05-cv-templates.md 里找不到 ```typst 用法示例了")

    def test_the_template_exists(self):
        self.assertTrue(TEMPLATE.is_file(), f"{TEMPLATE} 不在")

    def test_the_example_compiles_against_the_current_template(self):
        if not typst_available():
            self.skipTest("本机没装 typst（软依赖）")
        with tempfile.TemporaryDirectory() as d:
            dd = Path(d)
            shutil.copy(TEMPLATE, dd / "template.typ")
            (dd / "main.typ").write_text(doc_example(), encoding="utf-8")
            r = subprocess.run(
                ["typst", "compile", str(dd / "main.typ"), str(dd / "out.pdf")],
                capture_output=True, text=True, encoding="utf-8", errors="replace")
            self.assertEqual(
                r.returncode, 0,
                "05-cv-templates.md 的用法示例编译不过当前的 resume/template.typ：\n"
                + (r.stderr or "")[:1200]
                + "\n\n这份文件是 /job-apply 起草简历前必读的那一份——它对不上实现，"
                "\n每一次定制简历都跟着错。")
            self.assertTrue((dd / "out.pdf").is_file(), "编译报成功却没有产出 PDF")

    def test_the_doc_does_not_teach_the_old_bullet_syntax(self):
        """模板改用原生列表之后，别再教「`·` 开头是普通文本」。

        这条单独钉，因为它**编译得过**——手写 `· 文字` 是合法 Typst，
        只是续行不悬挂缩进。编译检查抓不到它，只有明写规则才拦得住。
        """
        uses_native_list = "set list(" in TEMPLATE.read_text(encoding="utf-8")
        if not uses_native_list:
            self.skipTest("模板不再用原生列表了，这条规则要重新讨论")
        # ⚠️ 只看**指令行**，不看引用块。
        #
        # 第一版扫全文，当场自己撞自己：修正说明里必须引用旧写法当反例
        # （「本条原来写的是相反的说法——『`·` 开头的行是普通文本』——那是模板
        # 改用原生 list 之前的事」），断言把这段解释判成了违规。
        # 「断言撞上解释自己的文字」是这个仓库反复出现的形状，解法一律是把判据
        # 收到结构上：这里是「引用块（`>` 开头）里的话不算指令」。
        lines = [l for l in DOC.read_text(encoding="utf-8").splitlines()
                 if not l.lstrip().startswith(">")]
        text = "\n".join(lines)
        for stale in ("`·` 开头的行是普通文本", "避免 Typst 列表的默认缩进"):
            with self.subTest(stale=stale):
                self.assertNotIn(
                    stale, text,
                    f"文档还在教旧写法（「{stale}」），而模板用的是原生列表——"
                    "\n手写 `· 文字` 的续行会顶格，超过一行的要点会被扫读成两条。")


if __name__ == "__main__":
    unittest.main()
