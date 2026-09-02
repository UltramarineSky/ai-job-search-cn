# -*- coding: utf-8 -*-
"""面板上印的命令是给人复制去跑的 —— 它得真的做那件事。

## 这一条从哪来

2026-08-31 把 `archive.py --revive` 也纳进 `--apply` 的试运行约定（在那之前
它敲一次就当场搬 1074 个岗，而同一个工具的 help 写着「不加就是试运行」）。
当天改了工具、改了 `job-rank.md`，**漏了面板**：

    另有 N 个老岗位收进了存档……改了硬性条件想重新评它们时先跑
    <Cmd>python tools/archive.py --revive</Cmd>

那是一个可点击复制的命令块，而它现在只会印一句「会拉回 N 个岗」，
什么也不做。用户照做、看不到变化，第一反应是面板骗了他。

第 63 轮那条 `test_every_printed_command_runs` 没拦住它：`--revive` 这面旗子
**存在**，所以那条放行了。它验的是「敲得动」，不是「敲了会做那件事」。

## 判据只管面板，不管工作流

工作流里那 20 来条不带 `--apply` 的命令绝大多数是正当的 ——
文档会成对展示「先试运行、确认无误再加 `--apply`」，那是给执行者读的散文。
**面板没有这个余地**：一个命令块，点一下复制，没有上下文能补。

（实测：拿同一条判据扫 `workflows/` 得 21 条，逐条看几乎全是那种成对展示 ——
所以那一侧不设这道闸门，噪音比病症大。）
"""
import ast
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
CMD = re.compile(r"python\s+tools/([A-Za-z_0-9]+\.py)((?:\s+[^\s`<|>&#{}\n]+)*)")


def _declares_apply(tool: str) -> bool:
    f = ROOT / "tools" / tool
    if not f.is_file():
        return False
    try:
        tree = ast.parse(f.read_text(encoding="utf-8"))
    except SyntaxError:
        return False
    return any(
        isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
        and n.func.attr == "add_argument"
        and any(isinstance(a, ast.Constant) and a.value == "--apply"
                for a in n.args)
        for n in ast.walk(tree))


def panel_commands():
    """`(文件, 行号, 整条命令, 工具名, 带没带 --apply)`。"""
    src = ROOT / "web" / "src"
    if not src.is_dir():
        return
    for p in sorted(src.rglob("*.ts*")):
        if "sample" in p.name:          # 演示数据不是印给用户的引导
            continue
        for i, ln in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            for m in CMD.finditer(ln):
                yield (p.name, i, m.group(0), m.group(1),
                       "--apply" in (m.group(2) or ""))


class EveryPanelCommandDoesTheThing(unittest.TestCase):

    def test_a_write_tool_is_invoked_with_apply(self):
        bad = [f"{f}:{i} {cmd}" for f, i, cmd, tool, ap in panel_commands()
               if _declares_apply(tool) and not ap]
        self.assertEqual(
            bad, [],
            "面板上这几条命令的工具默认是试运行 —— 用户复制去跑，"
            "看到的是「会怎样」而不是做完了：\n  " + "\n  ".join(bad)
            + "\n面板没有「先预览再加旗子」的余地，一个命令块就是一次动作")

    def test_the_scan_sees_the_panel(self):
        """控制用例：真扫到了命令，否则上面那条永远绿。"""
        got = list(panel_commands())
        self.assertGreaterEqual(len(got), 8, f"只扫到 {len(got)} 条")

    def test_it_knows_which_tools_are_dry_by_default(self):
        self.assertTrue(_declares_apply("archive.py"))
        self.assertFalse(_declares_apply("serve.py"))
        self.assertFalse(_declares_apply("doctor.py"))


if __name__ == "__main__":
    unittest.main()
