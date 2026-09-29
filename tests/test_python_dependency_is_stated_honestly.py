"""哪些命令要用 Python，依赖表里得说全。

## 表里说「只有总览页要」，实际有一串命令在调 Python

`README.md` 与 `SETUP.md` 的依赖表原来都把 Python 归成「要看总览页就装」。
实测 `workflows/` 里 `python tools/…` 的调用：

| 命令 | 调的是什么 | 缺了会怎样 |
|---|---|---|
| `/job-rank` | `prescreen.py`、`jd_store.py` | 不做预筛淘汰（队列排不空）、每轮重抓 JD |
| `/job-scrape` | `jd_store.py` | 抓到的 JD 正文不入库，下轮重抓 |
| `/job-outcome` | `followups.py` | 「该催哪几个」只能手算——而该文件明写「**用工具算，不要手算**」，并列了三种静默错法 |
| `/job-upskill` | `gap_split.py` | 专业能力/业务域四格分不出来 |
| `/job-dashboard` | `serve.py` | 整条命令跑不了 |
| `/job-setup` | `query_yield.py`、`gap_split.py` | `--section search` 复跑「改搜索词」那节没有词级战绩可看，改词只能凭感觉 |

**而且没有任何工作流写过 no-Python 的降级路径**（`AGENTS.md` 只说了「没有 Python
时跳过自检」，那讲的是 `doctor.py`）。用户照 README 跳过 Python，走到 `/job-rank`
Step 1.7 时会撞上一句「跑 `python tools/prescreen.py`」。

这条不是要求把 Python 变成必装——`/job-apply` 一行 Python 都不调；`/job-setup`
也只在 `--section search` 复跑「改搜索词」那一节时用 Python 读每个词抓过的真实
战绩（`query_yield.py`）与跑偏情况（`gap_split.py`），没有它这一节照问，词只能
用户自己想（`workflows/job-setup.md`：「再让他从零想关键词是浪费」）。是要求
**表里别少说**：少说的代价是用户在流程中途才发现，而那时他已经投入了。

## 判据

凡是 `workflows/<名>.md` 里出现 `python tools/…` 的命令，命令名都要出现在
README 与 SETUP 的「Python」那一行里。**只认那一行自己**：行本身整行都算，
表下注解里只有**自己提到 Python 的句子**才算。曾经是整个注解区域都算、名字
出现在哪儿都算，于是一句与 Python 毫不相干的话（「Claude Code 是唯一开箱就有
`/job-setup` 的」）替 `/job-setup` 交了差，而那一行其实从没提过它——2026-09
删掉那句旧话（`1203f41`）才让这个空转暴露出来。
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
    """依赖表里提到 Python 3.10+ 的那一行，**外加表下注解里自己提到 Python 的句子**。

    ## 为什么不能只看那一格

    这条守卫要的是「用户在依赖表这一眼里就知道跳过 Python 会少哪几条命令」，
    而不是「那些字必须挤在同一个单元格里」。README 那一格一度长到 **293 字符**
    ——12 条命令塞进一个格子，渲染出来把标签列挤到折行，谁也不会读完。
    拆成「格子里给摘要 + 表下面一行 `<sub>` 列全」之后信息一个没少、离得也没远，
    只是不在同一行了。

    ## 但注解整片都算，等于没守卫

    取值范围曾经是「那一行 + 表格结束到下一个空行为止的连续注解行」，命令名
    出现在区域内任何地方都算数。结果 SETUP 那边靠一句和 Python 毫不相干的话
    （「Claude Code 是唯一开箱就有 `/job-setup` 的」）替 `/job-setup` 交了差，
    而那一行其实从没提过它——那句话被删掉（`1203f41`）之后这条检查才头一回
    真的报红。README 同理：`<sub>` 第一句「主线那一行的命令：…`/job-setup`…」
    提得到它，但那说的是 Node 主线，不是 Python。

    所以现在：行本身整行都算（那一行通篇讲的就是 Python）；注解按「。」切句，
    只有句子自己提到 Python 才算这一行的账。表若日后改写，宁可红也不要空转：
    真漏的名字必须报出来，合法的改法（注解句里保住「Python」字样，或名字回到
    行本身）红一次就修好了。按行切句，跨行的句子两边都不算——同样是朝红的方向。
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
        # 注解按句过滤：只有句子自己提到 Python，句里的命令名才算这一行的账。
        out.extend(s for s in lines[j].split("。") if "ython" in s)
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
        """名字只认「Python 那一行自己」——表下注解里与 Python 无关的句子不算
        （见 `python_row` 的出处：一句旧话替 `/job-setup` 空转过）。"""
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

    def test_python_stays_optional_for_the_core_two(self):
        """反向：`/job-apply` 一个 Python 工具都不调；`/job-setup` 只在
        `--section search` 复跑那节读词级战绩，第一次填资料没有它也走得完。
        再多一环，「强烈建议」就得改口「必装」。

        这条以前拿裸的 `setup` / `apply` 去比 `job-` 开头的命令名——那个集合里
        永远没有这两个字，等于没判任何东西。换成真名才照见现实：`/job-setup`
        确实调了 `query_yield.py` 与 `gap_split.py`（`workflows/job-setup.md`
        「重跑这一节时（`--section search`），先看实测产出再问」），所以这里
        锁的是**它调用的集合**，不是「它不碰 Python」。集合变了就重新核口径。
        """
        cmds = commands_needing_python()
        with self.subTest(cmd="job-apply"):
            self.assertNotIn(
                "job-apply", cmds,
                "`/job-apply` 现在也要 Python 了——那 Python 就是必装项，"
                "两份文档的表都要改口径，不能再写「强烈建议」")

        def calls(name: str) -> set:
            text = (ROOT / "workflows" / f"{name}.md").read_text(encoding="utf-8")
            return set(CALL.findall(text))

        with self.subTest(cmd="job-setup"):
            self.assertEqual(
                calls("job-setup"),
                {"python tools/query_yield.py", "python tools/gap_split.py"},
                "`/job-setup` 用到的 Python 工具不止「改搜索词」复跑那两个了——"
                "第一次填资料若也开始离不开 Python，两份文档就不能再把它写在"
                "「强烈建议」那一档，得改成必装")
        with self.subTest(cmd="job-apply calls"):
            self.assertEqual(
                calls("job-apply"), set(),
                "`/job-apply` 正文里出现了 `python tools/…` 的调用")


if __name__ == "__main__":
    unittest.main()
