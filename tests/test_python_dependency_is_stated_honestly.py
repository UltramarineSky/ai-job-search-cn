"""哪些命令要用 Python，依赖表里得说全。

## 表里说「只有总览页要」，实际有五条命令在调 Python

`README.md` 与 `SETUP.md` 的依赖表原来都把 Python 归成「要看总览页就装」。
实测 `workflows/` 里 `python tools/…` 的调用：

| 命令 | 调的是什么 | 缺了会怎样 |
|---|---|---|
| `/job-rank` | `prescreen.py`、`jd_store.py` | 不做预筛淘汰（队列排不空）、每轮重抓 JD |
| `/job-scrape` | `jd_store.py` | 抓到的 JD 正文不入库，下轮重抓 |
| `/job-outcome` | `followups.py` | 「该催哪几个」只能手算——而该文件明写「**用工具算，不要手算**」，并列了三种静默错法 |
| `/job-upskill` | `gap_split.py` | 专业能力/业务域四格分不出来 |
| `/job-dashboard` | `serve.py` | 整条命令跑不了 |

**而且没有任何工作流写过 no-Python 的降级路径**（`AGENTS.md` 只说了「没有 Python
时跳过自检」，那讲的是 `doctor.py`）。用户照 README 跳过 Python，走到 `/job-rank`
Step 1.7 时会撞上一句「跑 `python tools/prescreen.py`」。

这条不是要求把 Python 变成必装——核心的 `/job-setup` 与 `/job-apply` 确实不用它。
是要求**表里别少说**：少说的代价是用户在流程中途才发现，而那时他已经投入了。

## 判据

凡是 `workflows/<名>.md` 里出现 `python tools/…` 的命令，命令名都要出现在
README 与 SETUP 的「Python」那一行里。
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

CALL = re.compile(r"python tools/[a-z_]+\.py")


def commands_needing_python() -> set:
    """哪些工作流会调 Python 工具。**现扫，不写死清单。**"""
    out = set()
    for p in (ROOT / "workflows").glob("*.md"):
        if CALL.search(p.read_text(encoding="utf-8")):
            out.add(p.stem)
    return out


def python_row(doc: Path) -> str:
    """依赖表里提到 Python 3.10+ 的那一行，**外加紧跟这张表的注解行**。

    ## 为什么不能只看那一格

    这条守卫要的是「用户在依赖表这一眼里就知道跳过 Python 会少哪几条命令」，
    而不是「那些字必须挤在同一个单元格里」。README 那一格一度长到 **293 字符**
    ——12 条命令塞进一个格子，渲染出来把标签列挤到折行，谁也不会读完。
    拆成「格子里给摘要 + 表下面一行 `<sub>` 列全」之后信息一个没少、离得也没远，
    只是不在同一行了。

    所以取值范围＝那一行 + 表格结束后的连续注解行（空行即止）。
    再往后就不算了：隔着一段正文的提及不构成「表里说清楚了」。
    """
    lines = doc.read_text(encoding="utf-8").splitlines()
    hit = next((i for i, l in enumerate(lines)
                if l.lstrip().startswith("|") and "Python 3.10" in l), None)
    if hit is None:
        return ""
    out = [lines[hit]]
    # 走到表尾
    j = hit + 1
    while j < len(lines) and lines[j].lstrip().startswith("|"):
        j += 1
    # 表和注解之间**允许一个空行**：markdown 里表格后面本来就要空一行，不放过它
    # 的话这个函数永远停在表尾，等于没加宽——实测第一版就是这样，README 那边
    # 十条命令一条都没认出来。
    if j < len(lines) and not lines[j].strip():
        j += 1
    while j < len(lines) and lines[j].strip():
        out.append(lines[j])
        j += 1
    return "\n".join(out)


class ThePythonRowNamesEveryCommandThatUsesIt(unittest.TestCase):

    DOCS = ("README.md", "SETUP.md")

    def test_the_scan_finds_callers(self):
        """控制用例：真扫到了调 Python 的工作流。"""
        cmds = commands_needing_python()
        self.assertGreaterEqual(
            len(cmds), 4,
            f"只扫到 {sorted(cmds)} 在调 python tools/——判据大概失效了")

    def test_each_doc_has_a_python_row(self):
        """控制用例：两份文档都有那一行，否则下面那条比对的是空串。"""
        for name in self.DOCS:
            with self.subTest(doc=name):
                self.assertTrue(
                    python_row(ROOT / name),
                    f"{name} 的依赖表里找不到 Python 3.10+ 那一行了")

    def test_every_caller_is_named_in_the_row(self):
        cmds = commands_needing_python()
        bad = []
        for name in self.DOCS:
            row = python_row(ROOT / name)
            if not row:
                continue
            for c in sorted(cmds):
                if f"/{c}" not in row:
                    bad.append(f"{name}: 没提 `/{c}`")
        self.assertEqual(
            bad, [],
            "这些命令会调 Python 工具，依赖表却没说：\n  " + "\n  ".join(bad)
            + "\n用户照表跳过 Python，走到流程中途才撞上「跑 `python tools/…`」——"
            "\n而那时他已经投入了。少说不等于没有。"
            + f"\n实际在调的：{sorted(cmds)}")

    def test_setup_and_apply_stay_python_free(self):
        """反向：核心两条确实不用 Python，否则「强烈建议」就该改成「必装」。"""
        for c in ("setup", "apply"):
            with self.subTest(cmd=c):
                self.assertNotIn(
                    c, commands_needing_python(),
                    f"`/{c}` 现在也要 Python 了——那 Python 就是必装项，"
                    "两份文档的表都要改口径，不能再写「强烈建议」")


if __name__ == "__main__":
    unittest.main()
