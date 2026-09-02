"""命令行工具接上管道时，两头都必须是 UTF-8——印出去的和喂进来的。

## 为什么值得一条测试

Windows 上 Python 只有 stdout 是**真终端**时才走 WriteConsoleW（Unicode 直通）。
一旦被管道接走或重定向到文件，就回落到 `locale.getpreferredencoding()`——
中文 Windows 上是 **cp936（GBK）**。

而 Git Bash、VS Code 内置终端、Windows Terminal 都按 UTF-8 解。于是用户敲

    python tools/doctor.py

看到的是一屏乱码。**这个仓库引导新人全靠终端提示**（doctor 的「下一步」只给一条，
就是靠它把人推到下一个动作），乱码等于引导整个失效。

更糟的是往 cp936 流里打一个它编不出的字符会直接 `UnicodeEncodeError` 崩掉，
而不是退化成问号——写这条测试时我自己的诊断脚本就这么崩过一次。

## 这个 bug 藏了多久，以及为什么

`tests/test_doctor.py` 给子进程设了 `PYTHONUTF8=1, PYTHONIOENCODING=utf-8`，
**把用户真实遇到的条件配置掉了**，于是一直绿。同期 `test_cli_contract` 没设、
照实撞见乱码而红——那条红的被当成「Windows 环境问题」放了很久。

**红的那条才是诚实的。** 教训：给子进程设环境变量让测试变绿之前，先问一句
「用户身上有这个变量吗」。

## 判据

`tools/*.py` 里每个有 `__main__` 的，用 `--help` 跑一遍（`_cli` 保证 --help 不干活），
stdout + stderr 必须能按 UTF-8 **严格**解码。不用 errors="replace"——那正是
当初让乱码溜过去的东西。

读的那头判据在 `PipedInputIsUtf8`：`tools/*.py` 里出现 `sys.stdin` 的都要走
`_cli`，外加一条证明 import 它确实管用。
"""

import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"


def main_entry_tools():
    """有 `__main__` 的工具 = 用户会直接敲的那些。库模块不算。"""
    for p in sorted(TOOLS.glob("*.py")):
        if p.name.startswith("_"):
            continue
        if "__main__" in p.read_text(encoding="utf-8"):
            yield p


class PipedOutputIsUtf8(unittest.TestCase):

    def test_the_scan_finds_tools(self):
        """控制用例：真扫到了工具，否则下面那条是空跑。"""
        n = len(list(main_entry_tools()))
        self.assertGreater(n, 5, f"只扫到 {n} 个命令行工具——判据多半失效了")

    def test_help_output_decodes_as_utf8(self):
        broken = []
        for p in main_entry_tools():
            r = subprocess.run([sys.executable, str(p), "--help"],
                               cwd=str(ROOT), capture_output=True, timeout=180)
            raw = (r.stdout or b"") + (r.stderr or b"")
            if not raw.strip():
                continue
            try:
                raw.decode("utf-8")
            except UnicodeDecodeError as e:
                broken.append(f"{p.name}: {e}")
        self.assertEqual(
            broken, [],
            "这些工具被管道接走时吐的不是 UTF-8：\n  " + "\n  ".join(broken)
            + "\nGit Bash / VS Code 终端里会显示成乱码。"
            "\n修法：import tools/_cli（import 即生效），"
            "或按 _cli.force_utf8_output() 内联同一段。")

    def test_the_check_can_actually_fail(self):
        """判据自检：造一个真往 cp936 里写中文的子进程，必须被认出来。

        没有这条的话，哪天 `--help` 全变成纯 ASCII，上面那条会永远绿——
        而它绿的原因是没有中文可乱，不是编码修好了。
        """
        code = ("import sys\n"
                "sys.stderr.reconfigure(encoding='gbk', errors='replace')\n"
                "print('没有叫「测试」的用户', file=sys.stderr)")
        r = subprocess.run([sys.executable, "-c", code],
                           capture_output=True, timeout=60)
        with self.assertRaises(UnicodeDecodeError,
                               msg="判据认不出 GBK 字节——上面那条测试是空跑"):
            r.stderr.decode("utf-8")


class PipedInputIsUtf8(unittest.TestCase):
    """读的那头是同一个坑，而且更隐蔽：**它不报错。**

    发布前实测（2026-09-03）：`python tools/check_outreach.py --stdin` 喂一段
    中文开场白，子进程 `sys.stdin.encoding` 是 **gbk**，UTF-8 字节被按 GBK 解成
    一串乱码 —— 于是一条禁语都命不中，闸门印出 `✓` 并以退出码 0 放行。
    输出那头至少会显示成乱码让人看见；输入这头**看起来完全正常**。

    两个消费方都在要害上：话术闸门（`check_outreach --stdin`）和
    「把猎头发来的那整段职位描述粘进来」（`jd_store --save -`）。

    判据分两层：**机制**（`_cli` 一 import 就把 stdin 也定到 UTF-8）
    和**覆盖**（读 stdin 的工具都走了 `_cli`）。少了后一层，
    新加一个不 import `_cli` 的工具照样会静默坏掉。
    """

    #: 喂进去必须原样回来。挑的字都在 GBK 里也有 —— 乱码不是因为字冷僻，
    #: 是因为按错表解了。
    SAMPLE = "您好，这件事是我这三年一直在做的事。"

    def stdin_readers(self):
        for p in sorted(TOOLS.glob("*.py")):
            # `_cli.py` 自己就是修法所在，别把它算成一个消费方。
            if p.name.startswith("_"):
                continue
            if "sys.stdin" in p.read_text(encoding="utf-8"):
                yield p

    def test_the_scan_finds_stdin_readers(self):
        """控制用例：真有工具在读 stdin，否则下面两条是空跑。"""
        found = [p.name for p in self.stdin_readers()]
        self.assertTrue(found, "一个读 stdin 的工具都没扫到——判据多半失效了")

    def test_importing_cli_fixes_stdin(self):
        code = ("import sys, pathlib\n"
                "sys.path.insert(0, str(pathlib.Path('tools').resolve()))\n"
                "import _cli  # noqa: F401\n"
                "sys.stdout.buffer.write(sys.stdin.read().encode('utf-8'))")
        r = subprocess.run([sys.executable, "-c", code], cwd=str(ROOT),
                           input=self.SAMPLE.encode("utf-8"),
                           capture_output=True, timeout=60)
        self.assertEqual(
            r.stdout.decode("utf-8"), self.SAMPLE,
            "import _cli 之后 stdin 仍不是 UTF-8——"
            "管道里喂进来的中文会变成乱码，而且不报错。"
            f"\nstderr: {r.stderr.decode('utf-8', 'replace')}")

    def test_every_stdin_reader_goes_through_cli(self):
        missing = [p.name for p in self.stdin_readers()
                   if not re.search(r"^import _cli\b", p.read_text(encoding="utf-8"),
                                    re.M)]
        self.assertEqual(
            missing, [],
            "这些工具读 stdin 却没 import _cli：\n  " + "\n  ".join(missing)
            + "\n中文 Windows 上喂进去的 UTF-8 会被按 cp936 解成乱码，且不报错。")

    def test_the_check_can_actually_fail(self):
        """判据自检：不 import `_cli` 的同一段代码必须解不出原文。

        没有这条的话，哪天 Python 自己把默认改成 UTF-8（或 CI 全跑在 Linux 上），
        上面那条会永远绿——而它绿的原因是环境本来就对，不是这个仓库修好了。
        """
        code = "import sys; sys.stdout.buffer.write(sys.stdin.read().encode('utf-8'))"
        r = subprocess.run([sys.executable, "-c", code], cwd=str(ROOT),
                           input=self.SAMPLE.encode("utf-8"),
                           capture_output=True, timeout=60)
        if r.stdout.decode("utf-8", "replace") == self.SAMPLE:
            self.skipTest("这个环境的默认 stdin 本来就是 UTF-8（非中文 Windows）"
                          "——上面那条测的是机制，仍然有效，但这里没有对照组")


if __name__ == "__main__":
    unittest.main()
