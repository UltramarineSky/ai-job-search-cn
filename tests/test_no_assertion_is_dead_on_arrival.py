# -*- coding: utf-8 -*-
"""断言不许「写了却永远不会失败」—— 判据自己失效的最后一种形状。

## 这个病犯过

`tests/test_followups.py` 里曾经写着：

    self.assertIn("two", t.lower() + "两次")

作者想让中英两款都通过，可**往尾巴上拼一个中文串并不会让 `"two"` 命中**——
这条断言只可能靠 `t` 里的英文通过，中文那一款从没被验过。
2026-08-20 把 `job-outcome.md` 翻成中文，它当场露馅（现在改成了
`assertTrue("两次" in t or "two" in t.lower(), …)`）。

这类断言比没有断言更坏：它占着一个名字、进着计数、永远是绿的。
和本仓库反复在治的「空 glob 恒绿」「判据只 `read_text` 不执行」是同一族。

## 判据

只报**结构上就能断定**的五种，不做语义推断——宁可漏报，不要制造噪音：

1. 两个参数完全相同（`assertEqual(x, x)`）
2. `assertTrue` / `assertFalse` 括着一个字面常量
3. `assertIn(针, … + 含针的常量)` —— 干草堆里自带答案
4. `assertIn(纯拉丁的针, … + 纯中日韩的常量)` —— 拼上去那截不可能命中（就是上面那个真 bug）
5. `assertGreaterEqual(len(x), 0)` —— 恒真
6. **跳过条件和断言判的是同一件事** —— `if X not in Y: skipTest(...)` 之后再
   `assertIn(X, Y)`：不成立就跳过，成立才断言，两条路都不会红

第 6 种是 2026-08-25 加的，起因是同一天写的两条守卫自己犯了它：一条写着
「消息里没有那句话就 skip」、下一条断言那句话在 —— 于是把整段从消息里删掉，
测试变成 **skip 而不是红**。**用「它在不在」决定「要不要验它在不在」。**

扫一遍存量，另有四处同型（境外学历那条、门名那条、两条渠道开关的），
其中两条也是同一天写的。这类特别容易写出来，因为它读起来很合理：
「这个信号哪天没了，这条就该跳过」——**那句话本身没错，错在跳过之后又去断言
它在**。该断言的是**别的东西**：那个信号真的驱动了它该驱动的行为。

**本文件的例子都写在字符串里**，`ast.parse` 只会把它们看成字面量、不是调用，
所以这条判据扫自己也不会误报——不需要把自己排除在外
（`test_no_maintainer_data_in_repo` 那种「排除自己」正是它后来出事的原因）。
"""

import ast
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
TESTS = ROOT / "tests"

SAME_ARG = {"assertEqual", "assertIs", "assertIn", "assertNotIn",
            "assertGreaterEqual", "assertLessEqual", "assertCountEqual",
            "assertSetEqual", "assertListEqual", "assertDictEqual"}


def _const(node):
    try:
        return ast.literal_eval(node)
    except Exception:                                  # noqa: BLE001
        return None


def _flatten_add(node):
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return _flatten_add(node.left) + _flatten_add(node.right)
    return [node]


#: `skipTest` 的守卫条件 → 它等价于哪一条断言。
#:
#: 只认**结构完全相同**的（`ast.dump` 一致），不做语义推断 —— 同本文件那句
#: 「宁可漏报，不要制造噪音」。所以
#: `if not shutil.which("node"): skip` 配 `assertIn("node", argv[0].lower())`
#: 不会误报：守卫判的是「这台机器有没有 node」，断言判的是「选出来的是不是它」，
#: 两件事。
#: **不分极性。** `if X not in Y: skip` 配 `assertIn(X, Y)` 是恒绿；反过来
#: 配 `assertNotIn(X, Y)` 是**恒红** —— 跳过条件把「不在」那一路挡掉了，
#: 剩下的每一次都必失败。两种都是死测试，都该报。
_SKIP_MIRROR = {"In", "NotIn"}


def _skip_guards(fn: ast.FunctionDef) -> list:
    """这个测试方法里，所有「命中就 skipTest」的守卫条件。"""
    out = []
    for node in ast.walk(fn):
        if not isinstance(node, ast.If):
            continue
        if any(isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute)
               and c.func.attr == "skipTest" for c in ast.walk(node)):
            out.append(node.test)
    return out


def _mirrors(guard, call) -> bool:
    """守卫和这条断言判的是不是同一个表达式（极性不论，见 `_SKIP_MIRROR`）。"""
    name = call.func.attr
    args = call.args
    # `if X: skip` / `if not X: skip`  ↔  assertTrue(X) / assertFalse(X)
    if name in ("assertTrue", "assertFalse") and len(args) >= 1:
        if isinstance(guard, ast.UnaryOp) and isinstance(guard.op, ast.Not):
            guard = guard.operand
        return ast.dump(guard) == ast.dump(args[0])
    # `if X in Y: skip` / `if X not in Y: skip`  ↔  assertIn / assertNotIn
    if (isinstance(guard, ast.Compare) and len(guard.ops) == 1
            and name in ("assertIn", "assertNotIn") and len(args) >= 2
            and type(guard.ops[0]).__name__ in _SKIP_MIRROR):
        # **干草堆也要比。** 只比针的话，`if 'a' not in t: skip` 会把
        # `assertIn('a', other)` 一起报了 —— 那是两个不同的问题。
        return (ast.dump(guard.left) == ast.dump(args[0])
                and ast.dump(guard.comparators[0]) == ast.dump(args[1]))
    return False


def skip_mirrors_assertion(source: str) -> list[tuple[int, str, str]]:
    """跳过条件和断言判的是同一件事 —— 两条路都不会红。"""
    out = []
    for fn in ast.walk(ast.parse(source)):
        # 不挑 `test_` 开头：`_skip_guards` 本来就只在同一个函数体内配对，
        # 辅助函数里出现同型一样是死代码。
        if not isinstance(fn, ast.FunctionDef):
            continue
        guards = _skip_guards(fn)
        if not guards:
            continue
        for call in ast.walk(fn):
            if not (isinstance(call, ast.Call)
                    and isinstance(call.func, ast.Attribute)
                    and call.func.attr.startswith("assert")):
                continue
            if any(_mirrors(g, call) for g in guards):
                out.append((call.lineno, call.func.attr,
                            "上面那个 skipTest 判的就是这件事 —— "
                            "不成立就跳过、成立才断言，两条路都不会红"))
    return out


def dead_assertions(source: str) -> list[tuple[int, str, str]]:
    """返回 (行号, 断言名, 为什么它永远不会失败)。"""
    out = []
    for n in ast.walk(ast.parse(source)):
        if not (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)):
            continue
        name = n.func.attr
        if not name.startswith("assert") or not n.args:
            continue
        a0 = n.args[0]
        a1 = n.args[1] if len(n.args) > 1 else None

        if a1 is not None and name in SAME_ARG and ast.dump(a0) == ast.dump(a1):
            out.append((n.lineno, name, "两个参数完全相同，恒真"))
            continue

        if name in ("assertTrue", "assertFalse"):
            v = _const(a0)
            if v is not None and not isinstance(a0, (ast.Name, ast.Call)):
                want = name == "assertTrue"
                out.append((n.lineno, name,
                            f"参数是常量 {v!r} —— {'恒真' if bool(v) == want else '恒假'}"))
                continue

        if name == "assertIn" and a1 is not None:
            needle = _const(a0)
            parts = _flatten_add(a1)
            if isinstance(needle, str) and len(parts) > 1:
                lits = [_const(p) for p in parts]
                if any(isinstance(v, str) and needle in v for v in lits):
                    out.append((n.lineno, name,
                                f"干草堆里拼进了含 {needle!r} 的常量 —— 恒真"))
                    continue
                if needle.isascii() and needle.strip():
                    bad = next((v for v in lits
                                if isinstance(v, str) and v.strip()
                                and not any(ch.isascii() for ch in v)), None)
                    if bad is not None:
                        out.append((n.lineno, name,
                                    f"针 {needle!r} 是纯拉丁，却往干草堆里拼了纯中文的 "
                                    f"{bad!r} —— 那一截不可能命中，等于白拼"))
                        continue

        if (name == "assertGreaterEqual" and a1 is not None and _const(a1) == 0
                and isinstance(a0, ast.Call)
                and getattr(a0.func, "id", "") == "len"):
            out.append((n.lineno, name, "len(...) >= 0 恒真"))
    return out


def all_problems(source: str) -> list[tuple[int, str, str]]:
    """两条判据的**唯一**入口 —— 加了新形状却没挂进来，这里就漏了。"""
    return dead_assertions(source) + skip_mirrors_assertion(source)


class NoAssertionIsDeadOnArrival(unittest.TestCase):

    def test_the_suite_has_none(self):
        bad = []
        for f in sorted(TESTS.glob("test_*.py")):
            src = f.read_text(encoding="utf-8")
            for line, name, why in all_problems(src):
                bad.append(f"{f.name}:{line} {name} —— {why}")
        self.assertEqual(
            bad, [],
            "这些断言永远不会失败 —— 比没有断言更坏，它占着名字、进着计数、"
            "永远是绿的：\n  " + "\n  ".join(bad))

    def test_the_scan_actually_reaches_the_tests(self):
        """对照用例：真的扫到文件了 —— 否则上面那条恒绿，正是它在治的病。"""
        found = list(TESTS.glob("test_*.py"))
        self.assertGreaterEqual(
            len(found), 100,
            f"只扫到 {len(found)} 份测试 —— 判据大概是够不到文件了")


class TheDetectorCanActuallyFire(unittest.TestCase):
    """六条规则各喂一个已知的坏例子，都必须报出来。

    例子写在字符串里交给 `ast.parse`，不是真的写成断言——否则本文件自己就红了。
    """

    def _one(self, body: str) -> str:
        src = "import unittest\nclass T(unittest.TestCase):\n    def test_x(self):\n" \
              "        t = 'x'\n        " + body + "\n"
        got = all_problems(src)
        self.assertTrue(got, f"这条坏断言没被抓到：{body}")
        return got[0][2]

    def test_identical_args(self):
        self.assertIn("完全相同", self._one("self.assertEqual(t, t)"))

    def test_constant_truthy(self):
        self.assertIn("常量", self._one("self.assertTrue('非空字面量')"))

    def test_haystack_contains_the_needle(self):
        self.assertIn("恒真", self._one("self.assertIn('a', t + 'abc')"))

    def test_latin_needle_with_cjk_tail(self):
        """就是 2026-08-20 那个真 bug 的形状。"""
        self.assertIn("不可能命中",
                      self._one("self.assertIn('two', t.lower() + '两次')"))

    def test_len_ge_zero(self):
        self.assertIn("恒真", self._one("self.assertGreaterEqual(len(t), 0)"))

    def test_a_skip_guarding_its_own_assertion(self):
        """第 6 种：跳过条件和断言判的是同一件事。"""
        for body, why in (
                ("if 'a' not in t:\n            self.skipTest('x')\n"
                 "        self.assertIn('a', t)", "in"),
                ("if not got:\n            self.skipTest('x')\n"
                 "        self.assertTrue(got)", "not"),
                ("if got:\n            self.skipTest('x')\n"
                 "        self.assertFalse(got)", "truthy")):
            with self.subTest(why=why):
                src = ("import unittest\nclass T(unittest.TestCase):\n"
                       "    def test_x(self):\n        t = 'x'\n"
                       "        got = []\n        " + body + "\n")
                self.assertTrue(all_problems(src),
                                f"这个恒绿的形状没被抓到：{why}")

    def test_a_skip_on_availability_is_not_flagged(self):
        """反向：**跳过条件本身不是罪**。

        真正合法的那一类长得很像 —— 都是「拿不到就跳过」。分界是
        **跳过判的和断言判的是不是同一个表达式**：`which("node")` 判的是
        这台机器有没有它，`argv[0]` 判的是选出来的是不是它，两件事。
        这两个例子取自仓库里真实存在的两条测试，判据把它们放过才算对。
        """
        for body, why in (
                ("if not which('node'):\n            self.skipTest('x')\n"
                 "        self.assertIn('node', argv[0].lower())", "另一个表达式"),
                ("if 'open' not in ss:\n            self.skipTest('x')\n"
                 "        self.assertLessEqual(ss['open'], ss['count'])", "另一种判法"),
                ("if not got:\n            self.skipTest('x')\n"
                 "        self.assertEqual(len(got), 3)", "断的是别的性质"),
                ("if 'a' not in t:\n            self.skipTest('x')\n"
                 "        self.assertIn('a', ss)", "同一个针，换了干草堆")):
            with self.subTest(why=why):
                src = ("import unittest\nclass T(unittest.TestCase):\n"
                       "    def test_x(self):\n        got, ss = [], {}\n"
                       "        which = argv = None\n        " + body + "\n")
                self.assertEqual(all_problems(src), [],
                                 f"误报了：{why}")

    def test_a_healthy_assertion_is_not_flagged(self):
        """反向：正常断言一个都不许误报。"""
        # ⚠️ 别把 `assertIn('a', t + '两次')` 当成健康例子——第一版就是这么写的，
        # 判据当场把它抓了，**而判据是对的**：那截中文同样帮不到一个纯拉丁的针，
        # 跟 2026-08-20 那个真 bug 完全同型。错的是例子，不是判据。
        for ok in ("self.assertEqual(t, 'x')",
                   "self.assertTrue('两次' in t or 'two' in t.lower())",
                   "self.assertIn('a', t + other)",
                   "self.assertIn('两次', t + other)",
                   "self.assertGreaterEqual(len(t), 3)",
                   "self.assertTrue(t)"):
            with self.subTest(line=ok):
                src = ("import unittest\nclass T(unittest.TestCase):\n"
                       "    def test_x(self):\n        t = 'x'\n"
                       "        other = 'y'\n        " + ok + "\n")
                self.assertEqual(all_problems(src), [], f"误报了：{ok}")


if __name__ == "__main__":
    unittest.main()
