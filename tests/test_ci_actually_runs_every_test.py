"""CI 跑的是 `unittest discover`——写成 pytest 风格的判据它一条都收不到。

2026-08-20 实测抓到的：`tests/test_portal_budget_stops_the_whole_site.py`
整份是模块级 `def test_*()` 加 `@pytest.mark.parametrize`，13 条判据
（守的是「撞风控停整家」，关系到用户账号被封）在两种环境里各有一种坏法：

| 环境 | 后果 |
|---|---|
| 维护者本机（装了 pytest） | `unittest` 收到 0 条，**安静地不跑**——本机 pytest 跑是绿的，看不出来 |
| CI（`python-tests` job 不装 pytest） | 模块级 `import pytest` 直接 ImportError，`FAILED (errors=1)` |

实测数：pytest 收 1767 条，`unittest discover` 只跑 1754 条，差的正是那 13 条；
在没装 pytest 的干净 clone 上跑，原版是 `Ran 1749 ... FAILED (errors=1)`。

**「判据存在但从不执行」跟这个仓库一直在治的「空 glob 恒绿」是同一个形状**，
而且更难看见：那个至少还在同一个进程里，这个连收集都没发生。

判据用 AST 而不是文本扫描——本文件自己要写下 `import pytest` 这几个字
（就在这段说明里），文本扫描会把自己扫红。
"""

from __future__ import annotations

import ast
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
TESTS = ROOT / "tests"


def offences(source: str) -> list[str]:
    """返回这份测试源码里「CI 跑不到 / 会让 CI 炸」的地方。"""
    found = []
    tree = ast.parse(source)
    for node in tree.body:                      # 只看模块级
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name.startswith("test"):
                found.append(
                    f"第 {node.lineno} 行 `def {node.name}()` 是模块级函数——"
                    "unittest discover 只收 TestCase 的方法，这条不会被执行")
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.name == "pytest" or a.name.startswith("pytest."):
                    found.append(f"第 {node.lineno} 行 import pytest —— "
                                 "CI 的 python-tests job 不装它，整个模块会 ImportError")
        elif isinstance(node, ast.ImportFrom) and (node.module or "").split(".")[0] == "pytest":
            found.append(f"第 {node.lineno} 行 from pytest import … —— 同上")
    return found


class EveryTestFileIsRunnableByUnittest(unittest.TestCase):
    def test_no_test_file_is_invisible_to_ci(self):
        bad = {}
        for p in sorted(TESTS.glob("test_*.py")):
            hits = offences(p.read_text(encoding="utf-8"))
            if hits:
                bad[p.name] = hits
        self.assertEqual(
            bad, {},
            "这些判据在 CI 上不会被执行（或会让 CI 直接炸）：\n" +
            "\n".join(f"  {f}: {'; '.join(h)}" for f, h in bad.items()) +
            "\n改法：套进 `class X(unittest.TestCase)`，参数化改用 `self.subTest`。")

    def test_the_scan_actually_reaches_the_tests(self):
        """对照用例：扫描真的够到了文件——否则上面那条是恒绿的。

        这正是本文件在治的病的元层：判据够不到东西时，
        「没有问题」和「没有检查」长得一模一样。
        """
        found = list(TESTS.glob("test_*.py"))
        self.assertGreaterEqual(
            len(found), 100,
            f"只扫到 {len(found)} 份测试 —— 判据大概是够不到文件了，"
            "而不是仓库真的只剩这么几份")


class TheDetectorCanActuallyGoRed(unittest.TestCase):
    """变异用例：证明上面那条不是摆设。不落盘，只喂源码字符串。"""

    def test_module_level_test_function_is_caught(self):
        hits = offences("def test_something():\n    assert True\n")
        self.assertTrue(hits and "模块级函数" in hits[0], hits)

    def test_import_pytest_is_caught(self):
        self.assertTrue(offences("import pytest\n"))
        self.assertTrue(offences("from pytest import raises\n"))

    def test_a_normal_testcase_is_clean(self):
        self.assertEqual(offences(
            "import unittest\n"
            "class T(unittest.TestCase):\n"
            "    def test_x(self):\n"
            "        self.assertTrue(True)\n"), [])

    def test_a_nested_helper_named_test_is_not_flagged(self):
        """只管模块级：TestCase 里的方法、函数里的内嵌函数都不算。"""
        self.assertEqual(offences(
            "import unittest\n"
            "class T(unittest.TestCase):\n"
            "    def test_x(self):\n"
            "        def test_inner():\n"
            "            pass\n"
            "        test_inner()\n"), [])


if __name__ == "__main__":
    unittest.main()
