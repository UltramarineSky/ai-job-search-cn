# -*- coding: utf-8 -*-
"""「展开看那一行」不是引导 —— 他得先去找，而找到的多半什么都没有。

`AGENTS.md`「每一处引导都要写出该敲的命令」把判据说死了：

> 指一个文件名（「去改 `search-queries.md`」）或指一件事（「重新评一遍」）
> 都不够：**用户不知道该敲什么。**
> 判据是「读完这句他能不能直接动手」。

而「指一个**地方**」比指文件名更远一层。2026-08-31 一天之内在三处逮到同一个
形状，三处都是同一句话的不同出口：

    自检收尾    「照下面那几条各自的链接一个一个跑」   下面只印了 2 条，要跑的有 10 个
    终端自检    「其余的展开看那一行会说怎么补」       56 个里 47 个那一行是空的
    面板下一步  「展开看每个岗的疑问」                 同上，同一批岗

第三处最说明问题：`doctor` 那一侧 2026-08-30 就为这件事分了两枚章
（它的注释写着「指一份不存在的东西，比不提更坏 —— 他会去找，找不到，
然后连带不信这一整句」），**而同一句话在面板那一侧原样留着**。
一条规则贴在一个出口上，另外两个照样会犯。

## 判据只看会印出去的字

注释与 docstring 里讲这条规则本身要能引用它（这份文件自己就在引），
所以只扫**字符串字面量**，且剥掉 docstring。

## 词表是量出来的，不是想出来的

只收上面三处真实出现过的说法，加上它们最直接的近邻。宁可漏，不可误报 ——
一条报错的守卫会被人整条关掉。
"""
import ast
import pathlib
import re
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]

#: 「指一个地方」的说法。只收实测出现过的与它们的近邻。
POINTING = re.compile(
    r"展开看|看那一行|照下面那|各自的链接|去面板上?看|到总览页上?看|自己找一下")

#: 句子里有这些，就说明它给了能敲的东西。
ACTIONABLE = re.compile(r"/job-[a-z]+|python tools/|typst |pdftotext")


def _printed_strings(path: pathlib.Path):
    """`(行号, 串)` —— 只要字面量，docstring 不算。"""
    src = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return
    docs = set()
    for n in ast.walk(tree):
        if isinstance(n, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef,
                          ast.ClassDef)):
            d = ast.get_docstring(n, clean=False)
            if d:
                docs.add(d)
    for n in ast.walk(tree):
        if (isinstance(n, ast.Constant) and isinstance(n.value, str)
                and n.value not in docs and len(n.value) >= 8):
            yield n.lineno, n.value


def _offenders():
    out = []
    for f in sorted((ROOT / "tools").glob("*.py")):
        for lineno, s in _printed_strings(f):
            if POINTING.search(s) and not ACTIONABLE.search(s):
                out.append(f"{f.name}:{lineno}  {s.strip()[:60]}")
    for f in sorted((ROOT / "web" / "src").rglob("*.ts*")):
        for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            t = line.strip()
            if t.startswith(("//", "*", "/*")):
                continue
            if POINTING.search(t) and not ACTIONABLE.search(t):
                out.append(f"{f.name}:{i}  {t[:60]}")
    return out


class TheRulerWouldLightUp(unittest.TestCase):
    """判据自检 —— 扫不到东西时下面那条在空集上永远绿。"""

    def test_it_reads_a_healthy_number_of_strings(self):
        n = sum(1 for _f in (ROOT / "tools").glob("*.py")
                for _ in _printed_strings(_f))
        self.assertGreater(n, 500, f"只扫到 {n} 个字面量，抽取器多半坏了")

    def test_docstrings_are_out_of_scope(self):
        """讲规则要能引用规则本身 —— 这份文件的开头就在引。"""
        src = ROOT / "tools" / "build_dashboard.py"
        got = {s for _ln, s in _printed_strings(src)}
        self.assertFalse([s for s in got if s.startswith("「材料备好还没投」")],
                         "docstring 混进来了")

    def test_it_would_catch_the_three_it_came_from(self):
        for s in ("其余的展开看那一行会说怎么补",
                  "先问清楚关键信息再决定，展开看每个岗的疑问",
                  "改不了它们 —— 照下面那几条各自的链接一个一个跑"):
            with self.subTest(s[:16]):
                self.assertTrue(POINTING.search(s), "词表认不出它了")
                self.assertFalse(ACTIONABLE.search(s))

    def test_a_sentence_with_a_command_passes(self):
        s = "其余 47 个没写；一次补完：/job-apply 可以考虑"
        self.assertTrue(POINTING.search(s) is None or ACTIONABLE.search(s))


class NoGuidanceStopsAtAPlace(unittest.TestCase):

    def test_nothing_points_without_saying_what_to_type(self):
        bad = _offenders()
        self.assertEqual(
            bad, [],
            "这几处把人指到一个地方，却没说该敲什么："
            "\n  " + "\n  ".join(bad)
            + "\n判据见 `AGENTS.md`「每一处引导都要写出该敲的命令」。")


class TheThreeFixesAreStillInPlace(unittest.TestCase):
    """三处的修法各不相同，逐处钉住 —— 词表挡的是下一次，这里钉的是这三次。"""

    def test_the_terminal_one_gives_the_batch_command(self):
        src = (ROOT / "tools" / "doctor.py").read_text(encoding="utf-8")
        self.assertIn("一次补完：/job-apply 可以考虑", src)

    def test_the_panel_one_gives_it_too(self):
        import importlib
        sys.path.insert(0, str(ROOT / "tools"))
        bd = importlib.import_module("build_dashboard")
        got = bd._ready_text(56, 0, 0, 9)
        self.assertIn("47 个没写要问什么", got)
        self.assertIn("/job-apply 可以考虑", got)

    def test_the_panel_one_stays_quiet_when_they_all_have_questions(self):
        """全都写了的时候不该多这半句 —— 那是一条永远为真的噪音。"""
        import importlib
        sys.path.insert(0, str(ROOT / "tools"))
        bd = importlib.import_module("build_dashboard")
        self.assertNotIn("/job-apply", bd._ready_text(56, 0, 0, 56))
        self.assertNotIn("/job-apply", bd._ready_text(56, 0, 0, None))

    def test_the_audit_one_prints_every_link(self):
        import importlib
        sys.path.insert(0, str(ROOT / "tools"))
        ap = importlib.import_module("audit_pipeline")
        links = [f"https://x.com/{i}" for i in range(5)]
        got = ap.rewrite_commands(links)
        self.assertEqual(len([g for g in got if "/job-apply" in g]), 5)


if __name__ == "__main__":
    unittest.main()
