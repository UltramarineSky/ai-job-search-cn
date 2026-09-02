"""两份围栏解析不许走样。

`tools/lint_skills.py::_strip_code` 与 `tests/md.strip_code` 是同一套 CommonMark 围栏
规则的两份实现。**留两份不是偷懒，是被逼的**：`lint_skills.py` 会被单独拷进临时目录
跑（`CopyableToolsStayStandalone`），不许 import 仓库里的任何模块。

重复本身不是问题，**无人察觉的分叉才是**。所以这里拿同一批刁钻输入喂两边，
输出必须逐字节一致。谁改了其中一份，这条当场红。

刁钻的地方都是有来历的：`lint_skills` 的 docstring 记着它有两版栽在「把反引号数量为
奇数当成未闭合」上——一个 ```` 包裹、内含单行 ``` 的合法片段正好数出奇数个。
"""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(ROOT / "tools"))

import md  # noqa: E402
import lint_skills  # noqa: E402

CASES = {
    "普通 bash 块": "前\n```bash\ncmd --x\n```\n后\n",
    "裸围栏": "前\n```\ncmd --x\n```\n后\n",
    "四反引号包着三反引号": "前\n````bash\n```\ninner\n```\n````\n后\n",
    "未闭合": "前\n```bash\ncmd\n没有闭合\n",
    "缩进围栏": "前\n  ```bash\n  cmd\n  ```\n后\n",
    "闭合行带杂物（不算闭合）": "前\n```bash\ncmd\n``` 注释\n还在块里\n```\n后\n",
    "行内代码": "有 `a` 与 `b` 两段\n",
    "空文本": "",
    "只有围栏": "```\n```\n",
    "info 带空格": "```bash title=x\ncmd\n```\n",
}


class TheTwoImplementationsAgree(unittest.TestCase):

    def test_strip_code_matches_byte_for_byte(self):
        for name, text in CASES.items():
            with self.subTest(case=name):
                self.assertEqual(
                    md.strip_code(text), lint_skills._strip_code(text),
                    f"两份围栏解析在「{name}」上分叉了 —— "
                    "它们是同一套规则的两份实现，只因 lint_skills 必须独立自足才留两份")

    def test_it_agrees_on_the_real_docs(self):
        """合成用例之外，拿仓库里真实的 markdown 再对一遍。"""
        docs = [ROOT / "README.md", ROOT / "SETUP.md", ROOT / "AGENTS.md",
                ROOT / "resume" / "README.md", ROOT / "documents" / "README.md"]
        for d in docs:
            if not d.is_file():
                continue
            with self.subTest(doc=d.name):
                t = d.read_text(encoding="utf-8")
                self.assertEqual(md.strip_code(t), lint_skills._strip_code(t),
                                 f"两份解析在 {d.name} 上给出了不同结果")

    def test_the_cases_actually_exercise_fences(self):
        """控制用例：这批输入里确实有围栏，否则上面两条是在比两个恒等的空串。"""
        stripped = sum(1 for t in CASES.values() if md.strip_code(t) != t.rstrip("\n"))
        self.assertGreater(stripped, 4, "这批用例几乎没触发围栏剥离，比对没意义")


class FencedLinesSeesEveryBlock(unittest.TestCase):
    """`fenced_lines` 必须给出**所有**围栏块，不按 info string 挑。"""

    def test_untagged_fences_are_included(self):
        text = "```\ncmd --bare\n```\n"
        got = [l for _, l, _ in md.fenced_lines(text)]
        self.assertEqual(got, ["cmd --bare"],
                         "裸围栏被跳过了 —— 那正是上一版守卫漏掉 7 个复制粘贴块的原因")

    def test_the_info_string_is_reported_not_used_as_a_filter(self):
        text = "```bash\na\n```\n```\nb\n```\n"
        got = [(l, info) for _, l, info in md.fenced_lines(text)]
        self.assertEqual(got, [("a", "bash"), ("b", "")],
                         "info string 应该原样报出来给调用方，而不是拿来筛掉块")

    def test_nested_longer_fence(self):
        text = "````bash\n```\ninner\n```\n````\n"
        got = [l for _, l, _ in md.fenced_lines(text)]
        self.assertEqual(got, ["```", "inner", "```"],
                         "四反引号块里的内层三反引号被当成闭合了")

    def test_line_numbers_are_one_based_and_real(self):
        text = "前\n```bash\ncmd\n```\n"
        got = [(n, l) for n, l, _ in md.fenced_lines(text)]
        self.assertEqual(got, [(3, "cmd")], "行号对不上原文")


if __name__ == "__main__":
    unittest.main()
