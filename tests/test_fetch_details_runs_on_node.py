# -*- coding: utf-8 -*-
"""`fetch_details.py` 得能在只有 Node 的机器上跑。

全仓的口径是一致的：**node 是默认运行时，bun 是可选**——
`tools/doctor.py` 把 Bun 标成「可选 · 日常使用不需要」，`security_guards.py` 的注释
写着 node 是「默认路径」，`helpers.ts` 里那条「显式声明 + 显式赋值」的约束存在的
理由就是「让用户不必额外装 Bun」，SKILL.md 的每条用法示例也都是 `node …/cli.ts`。

唯独这个工具写死了 bun：`find_bun()` 找不到就 `SystemExit`。于是一台只有 Node 的
机器上，自检说「一切就绪、Bun 不需要」，`/job-rank` 走到抓详情这一步却直接死掉，
报的还是「装了才能跑」——用户刚被告知不用装。

两条命令形状不同（`node <file>` vs `bun run <file>`），所以不能只换可执行文件名。
"""
import shutil
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import fetch_details as fd  # noqa: E402


class NodeIsEnough(unittest.TestCase):

    def test_it_does_not_hard_require_bun(self):
        src = (ROOT / "tools" / "fetch_details.py").read_text(encoding="utf-8")
        self.assertNotIn("找不到 bun —— 装了才能跑", src,
                         "缺 bun 仍然是硬退出，而自检说 Bun 可选")

    def test_a_runtime_is_found_on_this_machine(self):
        """本机至少有 node 或 bun，就该找得到一个可用运行时。"""
        if not (shutil.which("node") or shutil.which("bun")):
            self.skipTest("本机 node/bun 都没有")
        argv = fd.find_runtime()
        self.assertTrue(argv, "两个运行时都在，却没找出可用的")
        self.assertIsInstance(argv, list, "返回的该是 argv 前缀，不是一个可执行名——"
                                          "node 与 bun 的命令形状不同")

    def test_node_is_preferred(self):
        if not shutil.which("node"):
            self.skipTest("本机没有 node")
        argv = fd.find_runtime()
        self.assertIn("node", argv[0].lower(),
                      f"有 node 却没优先用它：{argv}")
        self.assertNotIn("run", argv,
                         "`node` 不吃 `run` 子命令——那是 bun 的形状")

    def test_the_command_shape_matches_the_runtime(self):
        """bun 要 `bun run <file>`，node 是 `node <file>`。形状拼错就是 127。"""
        for exe, tail in (("/x/bun", ["run"]), ("/x/node", [])):
            with self.subTest(exe=exe):
                self.assertEqual(fd.runtime_argv(exe), [exe] + tail)

    def test_missing_both_says_what_to_install(self):
        """两个都没有时才报错，且要说清装哪个——不能只提 bun。"""
        src = (ROOT / "tools" / "fetch_details.py").read_text(encoding="utf-8")
        i = src.find("def find_runtime")
        self.assertGreater(i, -1, "没有 find_runtime")
        seg = src[i:i + 1400]
        self.assertIn("node", seg.lower())
        self.assertIn("bun", seg.lower())


if __name__ == "__main__":
    unittest.main()
