# -*- coding: utf-8 -*-
"""断言失败时，不许把 `users/` 底下整份文件印进测试报告。

## 为什么这条值得单独有

`unittest` 的 `assertIn` / `assertRegex` 失败时会把**两个操作数都印出来**。
拿整份 `candidate.md` 当 haystack，一次失败就是把姓名、薪资区间、
「明确的能力边界」那八条全倒进报告 —— **而测试报告会被贴进对话、CI 日志、issue**。

2026-08-30 自己造过一次（`test_the_iron_rules_hold_on_real_output` 的第一版
写成 `assertRegex(candidate.md 全文, ...)`，而那条断言当场就是红的，
于是资料真的被印了出来）。改法只有一步：**先算成布尔再断言**。

    found = any(re.match(r"#{2,4}\\s*明确的能力边界", ln) for ln in t.splitlines())
    self.assertTrue(found, "…")

## 判据只认最窄的那一种

只认「断言的操作数是一个**直接**读 `users/` 底下文件的 `read_text()` 调用，
或一个由那种调用赋值的变量」。放宽一点就会把 1000 多处断言仓库自己源文件的
测试全报出来 —— 那些印出来无害（内容本来就在版本库里）。
"""
import ast
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]

#: 会把两个操作数都印进报告的断言。
DUMPING = {"assertIn", "assertNotIn", "assertEqual", "assertNotEqual",
           "assertRegex", "assertNotRegex"}


def _text(node, lines) -> str:
    lo = node.lineno - 1
    hi = node.end_lineno or node.lineno
    return "\n".join(lines[lo:hi])


def _reads_personal(txt: str) -> bool:
    """这段源码是不是在读 `users/` 底下的文件。"""
    if "read_text" not in txt:
        return False
    return ('"users"' in txt or "'users'" in txt or "users /" in txt
            or "udir" in txt)


def _reads_personal_path(txt: str) -> bool:
    """这段源码是不是在拼一个**真实**用户目录下的路径（不一定当场读）。

    ⚠️ **必须从 `ROOT` 起。** 沙箱测试里满是 `tmp / "users" / "试用" / …` ——
    那是构造出来的数据，印出来无害；只认 `users` 两个字会把它们全报出来
    （实测误报 8 处）。`udir` 是 `doctor` 那几条测试里真实用户目录的惯用名。
    """
    if "udir" in txt:
        return True
    if not ("ROOT" in txt or "root=" in txt):
        return False
    return '"users"' in txt or "'users'" in txt or "users /" in txt


def _is_read_call(node) -> bool:
    """**直接**就是一个 `….read_text(…)` 调用 —— 不是「表达式里含有」。

    ⚠️ 这一条收紧过两次，两次都是自己的误报逼的：
    推导式 `[u for u in xs if "…" not in (…).read_text()]` 的**结果**是一串
    用户名，印出来无害；而按「源码里出现 read_text」判会把它报成 dump 整份文件。
    """
    return (isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "read_text")


def offenders() -> list:
    bad = []
    for p in sorted((ROOT / "tests").glob("*.py")):
        src = p.read_text(encoding="utf-8")
        lines = src.splitlines()
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        # **按函数分域收集。** 变量名会跨函数重用：同一个 `t` 在这个函数里读的是
        # `workflows/job-interview.md`，在另一个里读的是 `candidate.md` ——
        # 全文件收集会把前者也报出来（实测误报 2 处）。
        # **模块那一档只看顶层语句。** 第一版写 `[tree] + [函数们]`，而
        # `ast.walk(tree)` 会把每个函数体也走一遍 —— 想修的跨函数泄漏原样还在
        # （实测误报 14 处：读 `workflows/*.md` 的 `t` 被同文件另一个函数里
        # 读个人资料的 `t` 带脏了）。
        funcs = [n for n in ast.walk(tree)
                 if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        top = ast.Module(body=[n for n in tree.body
                               if not isinstance(n, (ast.FunctionDef,
                                                     ast.AsyncFunctionDef,
                                                     ast.ClassDef))],
                         type_ignores=[])
        for scope in [top] + funcs:
            # **路径常常先落在一个变量里。** 变异实测（2026-08-30）：把
            # `test_the_iron_rules_hold_on_real_output` 改回坏写法
            #（`p = ROOT / "users" / … ; t = p.read_text(); assertIn(…, t)`），
            # 第一版检测器一声不吭 —— 因为 `t = p.read_text()` 那一行里
            # 根本没有 `users` 两个字。所以要先认出「p 是个人数据的路径」。
            paths = set()
            for n in ast.walk(scope):
                if (isinstance(n, ast.Assign) and len(n.targets) == 1
                        and isinstance(n.targets[0], ast.Name)
                        and _reads_personal_path(_text(n, lines))):
                    paths.add(n.targets[0].id)
            personal = set()
            for n in ast.walk(scope):
                if not (isinstance(n, ast.Assign) and len(n.targets) == 1
                        and isinstance(n.targets[0], ast.Name)
                        and _is_read_call(n.value)):
                    continue
                on_var = (isinstance(n.value.func.value, ast.Name)
                          and n.value.func.value.id in paths)
                if on_var or _reads_personal(_text(n, lines)):
                    personal.add(n.targets[0].id)
            for n in ast.walk(scope):
                if not (isinstance(n, ast.Call)
                        and isinstance(n.func, ast.Attribute)
                        and n.func.attr in DUMPING):
                    continue
                for a in n.args[:2]:
                    direct = _is_read_call(a) and _reads_personal(_text(a, lines))
                    byname = isinstance(a, ast.Name) and a.id in personal
                    if direct or byname:
                        hit = f"{p.name}:{n.lineno} {n.func.attr}"
                        if hit not in bad:
                            bad.append(hit)
                        break
    return bad


class NoAssertionDumpsPersonalData(unittest.TestCase):
    def test_none_right_now(self):
        bad = offenders()
        self.assertEqual(
            bad, [],
            "这几处断言失败时会把 users/ 底下整份文件印进报告（姓名、薪资、"
            "能力边界都在里面），而报告会被贴进对话与 CI 日志。"
            "改法：先算成布尔再 assertTrue：\n  " + "\n  ".join(bad))

    def test_the_detector_can_fire(self):
        """对照：坏写法真抓得出来。"""
        lines = ['self.assertIn("x", (ROOT / "users" / u / "profile" /',
                 '                    "candidate.md").read_text(encoding="utf-8"))']
        txt = "\n".join(lines)
        self.assertTrue(_reads_personal(txt))

    def test_it_does_not_flag_repo_files(self):
        """断言仓库自己的源文件是无害的 —— 那 1000 多处不许被卷进来。"""
        txt = '(ROOT / "workflows" / "job-auto.md").read_text(encoding="utf-8")'
        self.assertFalse(_reads_personal(txt))

    def test_a_comprehension_over_a_read_is_not_a_dump(self):
        """推导式的结果是一串用户名，印出来无害 —— 别把它报成 dump 整份文件。"""
        node = ast.parse("[u for u in xs if 'x' in (p / 'users').read_text()]",
                         mode="eval").body
        self.assertFalse(_is_read_call(node))

    def test_a_direct_read_is_still_caught(self):
        node = ast.parse("(ROOT / 'users' / u).read_text()", mode="eval").body
        self.assertTrue(_is_read_call(node))

    def test_a_path_held_in_a_variable_is_caught(self):
        """**变异实测逼出来的这一条。** 路径先落在变量里时，
        读它那一行的源码里根本没有 `users` 两个字。"""
        self.assertTrue(_reads_personal_path(
            'p = ROOT / "users" / user / "profile" / "candidate.md"'))
        self.assertFalse(_reads_personal_path(
            'p = ROOT / "workflows" / "job-auto.md"'))

    def test_a_sandbox_path_is_not_personal(self):
        """沙箱里的 `tmp / "users" / "试用"` 是构造数据，印出来无害。"""
        self.assertFalse(_reads_personal_path(
            'csv = tmp / "users" / "试用" / "job_search_tracker.csv"'))


if __name__ == "__main__":
    unittest.main()
