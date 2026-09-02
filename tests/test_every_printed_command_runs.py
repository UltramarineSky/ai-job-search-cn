# -*- coding: utf-8 -*-
"""印给用户的每一条 `python tools/X.py --flag`，工具都得真认它。

## 为什么要有

`AGENTS.md`「每一处引导都要写出该敲的命令」把命令写进了工作流、工具输出、
面板和根目录那几份文档。**写出来的命令必须敲得动** —— 否则那句引导比不给
更坏：用户照做，撞一个 `unrecognized arguments`，然后不知道该信哪一半。

这类漂移在本仓库不是假想：
- `stale_materials.py --urls` 被删之后，它自己的 help 还写着「喂给
  `/job-apply --stale`」，而那条路早就不经过它（2026-08-30 删）；
- `job-scrape.md` 里「框架自己的 `search-queries.md` 在本技能目录下」
  指着一个**根本不存在的位置**。

散文里的互指由 `test_cross_references_resolve` 管，这一条管**可执行的**那一半。

## 这条规则原来有两份守卫，弱的那份会给错答案

`test_documented_commands_still_parse` 查的是同一件事（印出来的
`python tools/X.py --flag` 敲不敲得动），2026-08-31 并进本文件后删掉。
两份的差别不是风格，是**对错**：

| | 已删的那份 | 这一份 |
|---|---|---|
| 取旗子 | 正则扫 `add_argument("--x"` | AST 遍历 |
| 共享解析器给的 `--user` | 不认 | 认（`resolve_user(` 在源码里就算） |
| `--help` | 不认 | 认 |
| 扫哪些地方 | 4 份根文档 + workflows + `.claude` | 再加 `tools/*.py` 的输出串、`web/src`、`SETUP.md` |

实测那两处差异是真的：`export_web_data.py --user 张三` 与
`portal_budget.py -n 5` 都是合法命令，而正则那份认不出来 ——
文档里哪天真写上这两条，它会红，且理由是错的（「工具不认这个旗子」）。

**两份守卫的代价不是多跑一遍，是它们迟早给出两个答案**，而读的人
不知道该信哪一个。一件事一个住址，这个仓库反复栽在这句话上。

## 判据是派生的

不维护「有哪些命令」的名单：正则扫出所有 `python tools/X.py …`，
旗子从工具源码里静态取（`add_argument` 的字面量，外加共享解析器
`_cli.resolve_user()` 带来的 `--user`）。加一条新命令不必登记，
写错一个旗子当场红。
"""
import ast
import functools
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]

CMD = re.compile(r"python\s+tools/([A-Za-z_0-9]+\.py)((?:\s+[^\s`|>&#\n]+)*)")

#: 命令后面常跟着引号、括号、中文标点 —— 剥掉再比。
TRAIL = "".join(chr(c) for c in
                (34, 39, 65289, 41, 93, 125, 44, 59, 12290, 65292, 12289))

#: `lint_skills` 里讲规则时用的占位文件名，不是真命令。
PLACEHOLDER_TOOLS = {"x.py"}


def _flags(tool: str) -> set:
    src = (ROOT / "tools" / tool).read_text(encoding="utf-8")
    out = {"--help"}
    # 用共享解析器的工具自己不写 add_argument，但命令行确实收 `--user`。
    if "resolve_user(" in src:
        out.add("--user")
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return out
    for n in ast.walk(tree):
        if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                and n.func.attr == "add_argument"):
            for a in n.args:
                if (isinstance(a, ast.Constant) and isinstance(a.value, str)
                        and a.value.startswith("-")):
                    out.add(a.value)
    return out


def _sources():
    yield from sorted((ROOT / "workflows").rglob("*.md"))
    # 技能壳与命令 stub —— 已删的那份守卫扫这里，合并时一并接过来。
    yield from sorted((ROOT / ".claude").rglob("*.md"))
    yield from sorted((ROOT / "tools").glob("*.py"))
    if (ROOT / "web" / "src").is_dir():
        yield from sorted((ROOT / "web" / "src").rglob("*.ts*"))
    for name in ("AGENTS.md", "README.md", "SETUP.md", "CONTRIBUTING.md",
                 "CLAUDE.md"):
        f = ROOT / name
        if f.is_file():
            yield f


@functools.lru_cache(maxsize=1)
def scan():
    """`(工具不存在的, 旗子不存在的, 对上的个数)`。"""
    no_tool, no_flag, ok = [], [], 0
    cache = {}
    for p in _sources():
        for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            for m in CMD.finditer(line):
                tool, rest = m.group(1), m.group(2) or ""
                if tool in PLACEHOLDER_TOOLS:
                    continue
                if not (ROOT / "tools" / tool).is_file():
                    no_tool.append(f"{p.name}:{i} {tool}")
                    continue
                known = cache.setdefault(tool, _flags(tool))
                for tok in rest.split():
                    if not tok.startswith("--"):
                        continue
                    name = tok.split("=")[0].rstrip(TRAIL)
                    # 文档里的占位（`--user <名字>`）和被中文标点粘住的，跳过
                    if "<" in name or "（" in name or "，" in name:
                        continue
                    if name in known:
                        ok += 1
                    else:
                        no_flag.append(f"{p.name}:{i} {tool} {name}")
    return no_tool, no_flag, ok


class EveryCommandIsRunnable(unittest.TestCase):

    def test_the_tools_exist(self):
        no_tool, _f, _n = scan()
        self.assertEqual(no_tool, [],
                         "印出来的命令指着不存在的工具：\n  "
                         + "\n  ".join(no_tool))

    def test_the_flags_exist(self):
        _t, no_flag, _n = scan()
        self.assertEqual(no_flag, [],
                         "印出来的命令带着工具不认的旗子（用户照敲会撞 "
                         "unrecognized arguments）：\n  " + "\n  ".join(no_flag))

    def test_it_actually_looked_at_something(self):
        """判据是派生的 —— 扫不到东西时它会假绿。"""
        _t, _f, n = scan()
        self.assertGreater(n, 100, f"只对上了 {n} 个旗子，扫描多半没跑起来")

    def test_the_shared_parser_counts(self):
        """`--user` 由 `_cli.resolve_user()` 给，工具自己不写 add_argument。

        漏掉这一层会把十几条正确的命令报成错的（第一版就是这样）。
        """
        self.assertIn("--user", _flags("export_web_data.py"))
        self.assertIn("--help", _flags("doctor.py"))


class HistoricalRecordsAreOutOfScope(unittest.TestCase):
    """计划与报告是当时的记录，里面的工具早就跑完删了 ——
    改它们等于篡改档案。（从已删的那份守卫接过来。）
    """

    HIST = ("docs/superpowers", ".superpowers")

    def test_the_scan_does_not_reach_into_plans(self):
        seen = {p for p in _sources()}
        for d in self.HIST:
            base = (ROOT / d).resolve()
            inside = [p for p in seen
                      if base in p.resolve().parents]
            self.assertEqual(inside, [],
                             f"扫到 {d} 里去了 —— 那底下的命令是档案")

    def test_those_places_really_do_contain_stale_commands(self):
        """它们要是其实干净的，上面那条豁免就没有存在的理由。"""
        stale = 0
        for d in self.HIST:
            base = ROOT / d
            if not base.is_dir():
                continue
            for f in base.rglob("*.md"):
                txt = f.read_text(encoding="utf-8", errors="replace")
                for m in CMD.finditer(txt):
                    if not (ROOT / "tools" / m.group(1)).is_file():
                        stale += 1
        if not stale:
            self.skipTest("历史文档里已经没有失效命令了 —— 豁免可以撤了")


if __name__ == "__main__":
    unittest.main()
