"""文档给 CLI 调用示例时，不能只给 `bun run`——Node 才是默认路径。

## 同一个坑，两份文档、七处

仓库反复声明 Node 是默认运行时、Bun 只在改 CLI 代码时才需要：

- `SETUP.md` 的小节标题就是「**职位搜索 CLI 的运行时：Node 就够，不用装 Bun**」，
  依赖表里 Bun 标着「⑦ 只有改 CLI 代码才需要」
- `workflows/job-add-portal.md`：「**node 是默认路径**……强制 Bun 等于凭空多加一个必装依赖」
- `.agents/skills/liepin-search/SKILL.md` 的权限行与全部用法示例都用 `node`

可实际给出的命令是另一回事。实测七处：

| 在哪 | 写的是什么 | 后果 |
|---|---|---|
| `SETUP.md` 第 3 节 | `bun install`，还说「不装也能直接 `bun run` 起来」 | Node-only 用户照做，撞 `bun: command not found` |
| `SETUP.md` 常见问题 | 「确认装了 Bun」 | 排障第一步就把人引向一个不需要的依赖 |
| `add-portal.md` 生成的技能权限 | 只写 `Bash(bun run …)` | **每个新平台技能在默认运行时上都跑不起来**，报错还长得像权限问题 |
| `add-portal.md` Step 4 / Step 6 / 设计原则 | 验证与「试试看」命令全用 `bun`；设计原则写「只装了 `bun` 的新克隆」 | 与同一文件的运行时一节直接冲突 |

**声明和示例分开维护，就会漂。** 判据落在示例上——那才是用户真去敲的东西。

## 判据

一份文档只要出现 `bun run …cli.ts` 形式的调用，就必须也出现 `node …cli.ts`。
反过来不要求：只给 `node` 是对的（Bun 是可选加速）。
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

NODE_CALL = re.compile(r"node [^\n]*cli\.ts")
BUN_CALL = re.compile(r"bun run [^\n]*cli\.ts")


def docs():
    yield from ROOT.glob("*.md")
    yield from (ROOT / "workflows").rglob("*.md")
    yield from (ROOT / ".agents").rglob("*.md")


class NodeIsAlwaysOfferedAlongsideBun(unittest.TestCase):

    def test_the_scan_finds_cli_docs(self):
        """控制用例：真扫到了给 CLI 调用示例的文档。"""
        found = [p.name for p in docs()
                 if NODE_CALL.search(p.read_text(encoding="utf-8"))]
        self.assertGreaterEqual(
            len(found), 3,
            f"只有 {found} 给出了 node 调用示例——判据大概失效了")

    def test_the_default_runtime_is_still_node(self):
        """控制用例：仓库确实还把 Node 当默认，否则本测试拦的是不存在的规则。"""
        setup = (ROOT / "SETUP.md").read_text(encoding="utf-8")
        self.assertIn(
            "Node 就够，不用装 Bun", setup,
            "SETUP.md 里「Node 就够，不用装 Bun」不见了——默认运行时改了吗？"
            "改了就把本测试一起改。")

    def test_the_cli_help_does_not_send_people_to_bun(self):
        """CLI 自己打印的用法也不许只给 `bun run` —— 那是判据原来够不到的地方。

        ## 判据的边界停在了 markdown，而用户读的是 --help

        2026-08-21 通读 `job-apply.md` 时核对那条 `node …cli.ts detail` 的调用，
        顺手跑了一次 `node src/cli.ts --help`：**它用 node 跑通了，然后打印出
        「用法：bun run src/cli.ts …」**。源码里 `bun run` 出现 6 次、`node` 0 次。

        这条规则本来就有判据（`test_no_doc_offers_only_bun`），但它只扫 markdown。
        而**帮助文本是用户卡住那一刻真正会读的东西**——比任何一份文档都近。
        「一条规则声明了、另一头没落点」在这个仓库是常客，这次的另一头是 `.ts`。
        """
        cli = ROOT / ".agents" / "skills" / "liepin-search" / "cli" / "src" / "cli.ts"
        if not cli.is_file():
            self.skipTest("liepin-search CLI 不在，跳过")
        t = cli.read_text(encoding="utf-8")
        self.assertNotIn(
            "bun run src/cli.ts", t,
            "CLI 的用法/示例里还写着 `bun run src/cli.ts` —— 用户拿 node 跑通了它，"
            "它却告诉用户去装 bun。Node 是默认路径（SETUP.md「Node 就够，不用装 Bun」）。")
        self.assertIn(
            "node src/cli.ts", t,
            "CLI 的帮助文本里一条 `node src/cli.ts` 示例都没有了 —— 这条判据失去了依据")

    def test_no_doc_offers_only_bun(self):
        bad = []
        for p in docs():
            text = p.read_text(encoding="utf-8")
            if BUN_CALL.search(text) and not NODE_CALL.search(text):
                bad.append(p.relative_to(ROOT).as_posix())
        self.assertEqual(
            bad, [],
            "这些文档只给了 `bun run …cli.ts`，没给 `node …cli.ts`：\n  "
            + "\n  ".join(bad)
            + "\nNode 是默认路径（`SETUP.md`「Node 就够，不用装 Bun」）；"
            "\n只给 bun 的示例会把用户引向一个他不需要装的依赖，"
            "\n而报错（`bun: command not found`、或权限不匹配）都不像「你少装了个东西」。")


if __name__ == "__main__":
    unittest.main()
