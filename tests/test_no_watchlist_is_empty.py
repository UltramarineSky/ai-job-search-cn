"""测试里的词表不许是空的——空词表 = 那条检查静默失效。

## 为什么需要一条元测试

这个仓库有大量「不许出现 X」式的检查，判据都是一份词表：禁用词、内部词、行业词、
个人标识符、被禁的路径写法……它们的失效方式**完全一样**：

    for w in WATCHLIST:          # 词表空了
        if w in text:            # 循环一次都不跑
            bad.append(...)
    assertEqual(bad, [])         # 恒绿

两轮代码审查各抓到一次这个形状（`PER_USER_IN_CMD = ()` 全绿、`ACTED_ON = ()` 全绿），
而扫下来这样的词表有二十多份。**给每一份都补一条「非空」断言是重复劳动，而且新加的
词表还是会漏。** 判据放在这里，覆盖所有现有和将来的。

## 判据

模块级或类级的**大写常量**，值是全字符串的元组/列表/集合——那就是一份词表。
非空即可，不判内容：内容对不对是各自测试的事，这里只拦「整份没了」。

正则常量、路径常量、`SKIP_*` 这类「例外名单」不在此列（例外名单空着是合法状态：
表示没有例外）。
"""

import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TESTS = ROOT / "tests"

#: 空着是合法状态的常量——它们表达「例外/豁免」，没有例外就该是空的。
#: 判据是名字前缀，不是逐个点名：点名的清单自己也会漂移。
ALLOW_EMPTY_PREFIX = ("SKIP", "ALLOW", "EXEMPT", "IGNORE", "EXCLUDE", "OPTIONAL")


def string_watchlists(path: Path):
    """产出 `(常量名, 行号, 元素个数)`：模块级与类级的全字符串词表。"""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:
        return
    scopes = [tree] + [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
    for scope in scopes:
        for node in scope.body:
            if not isinstance(node, ast.Assign):
                continue
            for t in node.targets:
                if not (isinstance(t, ast.Name) and t.id.isupper() and len(t.id) > 2):
                    continue
                if t.id.startswith(ALLOW_EMPTY_PREFIX):
                    continue
                v = node.value
                if not isinstance(v, (ast.Tuple, ast.List, ast.Set)):
                    continue
                if not all(isinstance(e, ast.Constant) and isinstance(e.value, str)
                           for e in v.elts):
                    continue
                yield t.id, node.lineno, len(v.elts)


class NoWatchlistIsEmpty(unittest.TestCase):

    def test_the_scan_finds_watchlists(self):
        """控制用例：真扫到了词表，否则下面那条是空跑。

        这条自己就是它要防的那个形状的活标本——没有它，`string_watchlists`
        哪天认不出任何东西，下面那条照样绿。
        """
        found = [(f.name, n) for f in sorted(TESTS.glob("test_*.py"))
                 for n, _, _ in string_watchlists(f)]
        self.assertGreater(
            len(found), 15,
            f"只扫到 {len(found)} 份词表——判据多半失效了，而不是仓库里真的这么少")

    def test_no_string_watchlist_is_empty(self):
        bad = []
        for f in sorted(TESTS.glob("test_*.py")):
            for name, ln, size in string_watchlists(f):
                if size == 0:
                    bad.append(f"{f.name}:{ln}  {name}")
        self.assertEqual(
            bad, [],
            "这些词表是空的，靠它们判断的检查全都恒绿：\n  " + "\n  ".join(bad)
            + "\n空词表不会让任何测试变红——这正是它危险的地方")

    def test_the_emptiness_check_can_actually_fail(self):
        """判据自检：喂它一份空词表，必须认出来。"""
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "test_probe.py"
            # 名字要长于两个字符——判据本身有这条过滤（`ID`、`OK` 这种短名
            # 多半不是词表）。第一版探针用了 `OK`，红的是探针不是判据。
            p.write_text("BANNED = ()\nKEPT = ('x',)\n", encoding="utf-8")
            got = {n: size for n, _, size in string_watchlists(p)}
        self.assertEqual(got.get("BANNED"), 0, "认不出空词表")
        self.assertEqual(got.get("KEPT"), 1, "把非空的也当成空的了")

    def test_exception_lists_are_allowed_to_be_empty(self):
        """`SKIP_*` 这类表达「例外」的常量空着是合法的，不该被拦。"""
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "test_probe.py"
            p.write_text("SKIP_SUFFIX = ()\nBANNED = ()\n", encoding="utf-8")
            names = {n for n, _, _ in string_watchlists(p)}
        self.assertNotIn("SKIP_SUFFIX", names, "例外名单被当成了词表")
        self.assertIn("BANNED", names, "真正的词表被漏掉了")


if __name__ == "__main__":
    unittest.main()
