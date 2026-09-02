# -*- coding: utf-8 -*-
"""「这一页的服务还在用旧代码跑」那份监视名单，自己漏了三个文件。

`serve.py` 记下启动那一刻各文件的 mtime，之后每次 `/data.json` 比一遍，
变了就在页面上挂一条提醒。名单原来是**手写**的 8 个文件。

实测 2026-08-24：从 `serve.py` 顺着 import 走一遍，这个进程实际会加载
**11 个**仓库模块 —— 漏掉 `doctor` / `query_yield` / `archive`。三个都进了
`sys.modules`，改了不重启就是旧代码，而这份名单存在的理由正是拦这件事。

**它漏的恰恰是自己那段注释点名的那一类。** 名单上面写着：

> 顶层 import 和函数内 import 在这件事上没有区别，都要看住。

而 `export_web_data` 就是在函数里 `import doctor` 的。

## 手写的名单会漂，而且是静默地漂

`followups` / `gap_split` 2026-08-21 也是手工补进来的 —— **补一次漂一次**。
所以改成从 import 图现推（只用 `ast`，零依赖）。手写那份留作**兜底下限**：
真解析不出来时不能反而少看住几个。
"""
import ast
import pathlib
import re
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import serve  # noqa: E402

SRC = (ROOT / "tools" / "serve.py").read_text(encoding="utf-8")


def flat(s: str) -> str:
    s = " ".join(re.sub(r"^\s*#:?\s?", "", s, flags=re.M).split())
    return re.sub(r"(?<=[一-鿿，。；：、（）「」])"
                  r" +(?=[一-鿿，。；：、（）「」])", "", s)


def reachable() -> set:
    """这个测试自己独立走一遍 import 图 —— 不调被测的那个函数。

    调它就成了「拿实现验实现」：实现漏了，测试跟着漏。
    """
    here = ROOT / "tools"
    names = {p.stem for p in here.glob("*.py")}
    seen: set = set()

    def walk(n: str) -> None:
        if n in seen:
            return
        seen.add(n)
        f = here / (n + ".py")
        if not f.is_file():
            return
        for node in ast.walk(ast.parse(f.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                for a in node.names:
                    if a.name in names:
                        walk(a.name)
            elif isinstance(node, ast.ImportFrom) and node.module in names:
                walk(node.module)

    walk("serve")
    return {n + ".py" for n in seen}


class EveryLoadedModuleIsWatched(unittest.TestCase):
    def test_nothing_reachable_is_missing(self):
        missing = sorted(reachable() - set(serve._CODE_FILES))
        self.assertEqual(
            missing, [],
            f"这几个模块这个进程会加载，改了不重启就是旧代码，"
            f"而监视名单里没有：{missing}")

    def test_the_three_that_were_missing_are_in(self):
        """2026-08-24 漏的就是这三个 —— 单独钉一条，回归时报得具体。"""
        for f in ("doctor.py", "query_yield.py", "archive.py"):
            with self.subTest(f=f):
                self.assertIn(f, serve._CODE_FILES)

    def test_the_hand_written_floor_is_still_covered(self):
        """兜底下限一个都不能少 —— 现推失败时它是唯一剩下的东西。"""
        for f in serve._CODE_FLOOR:
            with self.subTest(f=f):
                self.assertIn(f, serve._CODE_FILES)

    def test_it_watches_more_than_the_floor(self):
        self.assertGreater(len(serve._CODE_FILES), len(serve._CODE_FLOOR),
                           "现推没生效 —— 名单退回手写那 8 个了")

    def test_it_only_watches_repo_modules(self):
        """标准库与第三方改不动，也不归我们管；列进来只会误报。"""
        for f in serve._CODE_FILES:
            with self.subTest(f=f):
                self.assertTrue((ROOT / "tools" / f).is_file(),
                                f"{f} 不在 tools/ 下")


class TheDerivationIsRobust(unittest.TestCase):
    def test_it_is_derived_not_hand_listed(self):
        self.assertIn("_CODE_FILES = _loaded_modules()", SRC,
                      "又改回手写名单了 —— 补一次漂一次")

    def test_a_broken_file_falls_back_instead_of_shrinking(self):
        """解析不出来时宁可少报一个改动，不可少看住一个文件。"""
        i = SRC.index("def _loaded_modules(")
        seg = SRC[i:SRC.index("_CODE_FILES = _loaded_modules()", i)]
        self.assertIn("except (SyntaxError, OSError):", seg)
        self.assertIn("_CODE_FLOOR", seg, "兜底下限没并进去")

    def test_a_cycle_does_not_hang_it(self):
        """`a import b; b import a` —— 走过的不再走。"""
        i = SRC.index("def _loaded_modules(")
        seg = SRC[i:SRC.index("_CODE_FILES = _loaded_modules()", i)]
        self.assertIn("if name in seen:", seg)

    def test_it_needs_no_third_party(self):
        i = SRC.index("def _loaded_modules(")
        self.assertIn("import ast", SRC[i:i + 400])


class TheReasonIsRecorded(unittest.TestCase):
    def _seg(self) -> str:
        i = SRC.index("**这份名单不再手写。**")
        return flat(SRC[i:SRC.index("_CODE_FLOOR = (", i)])

    def test_it_names_the_three_it_missed(self):
        seg = self._seg()
        for m in ("doctor", "query_yield", "archive"):
            with self.subTest(m=m):
                self.assertIn(m, seg)

    def test_it_points_at_its_own_rule(self):
        """名单漏的正是它自己那句话点名的那一类。"""
        seg = self._seg()
        self.assertRegex(seg, r"顶层 import 和函数内 import 在这件事上没有区别")
        self.assertRegex(seg, r"而它自己漏了")

    def test_it_names_the_earlier_drift(self):
        self.assertRegex(self._seg(), r"补一次漂一次")

    def test_it_carries_the_date(self):
        self.assertIn("2026-08-24", self._seg())


class TheWarningItselfIsIntact(unittest.TestCase):
    def test_it_still_warns_once_per_file(self):
        self.assertIn("_STALE_WARNED", SRC)

    def test_the_page_still_gets_the_flag(self):
        self.assertIn('d["staleCode"] = sorted(changed)', SRC)

    def test_the_page_does_not_print_file_names(self):
        """用户对着 `_cli.py` 什么也做不了 —— 文件名留在终端那份告警里。

        `serve.py` 本身不算：那是**要他敲的命令**，不是「改过的文件」。
        所以先把那条命令摘掉再看还有没有别的 `.py`。
        """
        app = (ROOT / "web" / "src" / "App.tsx").read_text(encoding="utf-8")
        i = app.index("这一页的服务还在用旧代码跑")
        seg = app[i:i + 300].replace("python tools/serve.py", "")
        self.assertNotIn(".py", seg,
                         "又把改过的文件名列到页面上了 —— 用户对着它做不了什么")
        self.assertIn("python tools/serve.py", app[i:i + 300])


if __name__ == "__main__":
    unittest.main()
