# -*- coding: utf-8 -*-
"""斜杠只在「不把 `/` 留给自己内置指令」的那几家保留。

`AGENTS.md`「每一处引导都要写出该敲的命令」要求**按当前工具调整命令形式**。
2026-09-29 / 09-30 逐家实测，五家吃斜杠、一家拦：

- **Claude Code** —— 技能进它的斜杠表（二进制里的 `skillToolCommands`）。
- **Qoder** —— harness 自己的口径：技能可按 `/<名>` 请求。
- **agy** —— 用户 2026-09-28 当场在 `/` 面板测过 `/job-scrape` 能匹配。
- **Qwen Code** —— 0.24.7 起把每个技能注册成 `/<技能名>`，并且开始扫
  `.agents/skills/`（`PROJECT_SKILL_DIRS = [".qwen", ".agents"]`）。
  ⚠️ 本机先前装的是 0.14.0，那一版两件事都不成立 —— 据旧版下的结论被新版打回。
- **MiMo Code** —— `command/index.ts` 把每个技能以 `source: "skill"` 塞进命令表，
  `skill/index.ts` 的注释写着「用户手敲斜杠照样能用」。
- **Codex CLI —— 拦。** 二进制 `codex.exe` 0.159.0 里就印着
  `Unrecognized command '/-'. Type "/" for a list of supported commands.`
  （出处 `tui\\src\\bottom_pane\\chat_composer\\inline_input.rs`）。它注入给模型的
  是 `<skills_instructions>`，技能不注册成斜杠项。

**Gemini CLI 原来在这一档，2026-09-30 整档删掉**：那家已停（个人版登录通道被关，
`reasonCode: UNSUPPORTED_CLIENT` / `tierId: free-tier`），后继是 Antigravity CLI。
留着它只是让一个装不上的工具白占一格，还会把 `GEMINI_CLI` 当成活信号去认。

**这一档最早只钉着 `claude` 一家，其余全在「去斜杠」里**，理由是「斜杠会被客户端
当成内置指令拦掉」——那句话只对 Codex 成立，剩下几家是被它白扣了斜杠这一层形式。
Codex 没有可用的探测信号（`CODEX` 那个变量不存在），自动探测落 `generic`，
所以 `no-slash` 那一档现在兜的是**「没实测过的工具」**，含 Codex。
裸形式各家都敲得动（触发词接得住），留着敲不动的斜杠才是每条引导都作废。

这份文件管**渲染层那张表**，以及面板那头的抄件。`_cli.py` 与 `doctor.py` 两份
`detect_code_tool` 副本的一致性已经由 `tests/test_code_tool_detection.py` 钉住，
这里不抄第二遍。
"""
import ast
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import doctor  # noqa: E402

#: 渲染层的两档名单，喂给下面第一条用例（逐档验斜杠去没去掉）。
#: **枚举「探测能返回哪些值」不靠这份手抄** —— 那条断言从源码里数，见
#: `_auto_detect_returns()`。
NO_SLASH = ("generic",)
SLASH = ("antigravity", "claude", "mimo", "qoder", "qwen")

#: 面板那头自己存了一份斜杠档名单（`CodeToolContext.tsx`）。它是 Python 那张表的
#: **抄件**，跨语言，import 不到，只能按文本对拍 —— 原来没有这一条，所以
#: `isNoSlash = tool !== "claude"` 在四家都已实测吃斜杠之后照样全绿。
TS_CTX = ROOT / "web" / "src" / "context" / "CodeToolContext.tsx"
_TS_LIST = r'const %s[^=]*=\s*\[([^\]]*)\]'
_TS_WORD = re.compile(r'"([a-z][a-z_]*)"')


def ts_names(const_name: str) -> set:
    """面板那份名单里的工具名，从 TS 源码里数出来。"""
    src = TS_CTX.read_text(encoding="utf-8")
    m = re.search(_TS_LIST % const_name, src)
    assert m, f"CodeToolContext.tsx 里找不到 const {const_name} —— 改名了就把这条一起改"
    return set(_TS_WORD.findall(m.group(1)))


def auto_detect_returns(src_name: str) -> set:
    """`detect_code_tool()` 自动探测能返回的全部字面量，从源码里数出来。

    只取字符串字面量的 `return`，所以手工覆盖那一支
    （`return override.strip().lower()`）天然不在集合里 —— 它对取值没有约束，
    任意名字都落到 `command_syntax()` 的默认档，那是设计（`doctor.py` 的
    `COMMAND_SYNTAX` 注释与 `test_an_unknown_tool_falls_into_the_no_slash_group`）。
    """
    tree = ast.parse((ROOT / "tools" / src_name).read_text(encoding="utf-8"))
    fn = next(n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef) and n.name == "detect_code_tool")
    return {n.value.value for n in ast.walk(fn)
            if isinstance(n, ast.Return)
            and isinstance(n.value, ast.Constant)
            and isinstance(n.value.value, str)}


class CommandSyntaxFollowsTheTool(unittest.TestCase):

    def test_only_the_unverified_group_strips_the_slash(self):
        text = "跑 /job-auto 然后 /job-outcome <公司>"
        for tool in NO_SLASH:
            out = doctor.adapt_commands(text, tool)
            self.assertNotIn("/job-", out, f"{tool} 那一档还留着斜杠：{out}")
        for tool in SLASH:
            self.assertEqual(doctor.adapt_commands(text, tool), text,
                             f"{tool} 实测吃斜杠，被剥掉就是白退回裸形式")

    def test_codex_manual_override_strips_the_slash(self):
        """Codex 拦斜杠是实测的，但它没有探测信号 → 只能手工指定，走默认档。

        这一条是那张表**没有** `codex` 那一格的理由：`detect_code_tool()` 自动探测
        永远不返回它，加一格会让 `test_the_syntax_table_names_every_tool` 变红，
        而行为靠默认值就已经对。真给 `codex` 单开一格的那天，把这条改成钉格子。
        """
        self.assertNotIn("/job-", doctor.adapt_commands("/job-auto", "codex"))
        self.assertEqual(doctor.command_syntax("codex"), "no-slash")

    def test_an_unknown_tool_falls_into_the_no_slash_group(self):
        """没探测出来的工具按去斜杠处理 —— 留斜杠会让所有引导都敲不动。"""
        self.assertNotIn("/job-", doctor.adapt_commands("/job-auto", "某个没见过的工具"))
        self.assertEqual(doctor.command_syntax("某个没见过的工具"), "no-slash")

    def test_the_discontinued_tool_has_no_cell(self):
        """Gemini CLI 已停 → 整档删掉，别再给它留格子，也别再认它的信号。

        `GEMINI_CLI` 是**真信号**（不像 `CLAUDE_CODE` / `CODEX` 那批从来不存在），
        所以「假信号不许触发」那组断言天然盖不住它 —— 得单钉这一条。留着不会报错，
        只会给一个装不上的工具印出名字，而那句名字正是用户唯一能据以判断
        「探测对不对」的线索。
        """
        self.assertNotIn("gemini", doctor.COMMAND_SYNTAX)
        for src in ("_cli.py", "doctor.py"):
            with self.subTest(src=src):
                self.assertNotIn("gemini", auto_detect_returns(src))

    def test_the_syntax_table_names_every_tool(self):
        """`COMMAND_SYNTAX` 覆盖 `detect_code_tool` 自动探测能返回的每一个值。

        **值从源码里数，不比手抄名单。** 原来这一条比的是本文件顶上那两个元组
        （NO_SLASH + SLASH）—— 同一份文件里的手抄名单，`detect_code_tool()` 一次都没
        调用过，于是给探测加第六档（`return "trae"`）它照样全绿，而 `doctor.py` 那行
        注释写的正是「逐条对拍」。**注释比着代码，代码比着空气。**
        现在加一档而没在 `COMMAND_SYNTAX` 里给它一格 → 红；两族副本（`_cli.py` 与
        `doctor.py`）数出来的集合不等 → 也红（判得一样那部分另有正本：
        `tests/test_code_tool_detection.py`，这里只比取值集合，不抄它的行为用例）。
        """
        for src in ("_cli.py", "doctor.py"):
            with self.subTest(src=src):
                self.assertEqual(auto_detect_returns(src), set(doctor.COMMAND_SYNTAX),
                                 f"{src} 的 detect_code_tool 返回值与 "
                                 f"COMMAND_SYNTAX 的格子对不上")
        self.assertEqual(set(NO_SLASH) | set(SLASH), set(doctor.COMMAND_SYNTAX),
                         "上面那两档名单与 COMMAND_SYNTAX 分了家 —— 第一条用例就只"
                         "覆盖了一半的档位")
        self.assertTrue(all(v in ("slash", "no-slash")
                            for v in doctor.COMMAND_SYNTAX.values()))


class ThePanelCarriesTheSameTable(unittest.TestCase):
    """`web/src/context/CodeToolContext.tsx` 是那张表的**跨语言抄件**，得对着正本量。

    面板原来自己写了一遍 `tool !== "claude"`（还有 `CommandBook.tsx` 的
    `tool === "claude" ? ... : ...`）。2026-09-29 把四家翻成吃斜杠之后，那两处
    **一行代码都不用改就全绿** —— 面板继续给 Gemini / Qoder / agy 免斜杠，
    而 Python 那头说该给斜杠。抄件与正本分叉从来不会自己喊，所以这里钉住：
    名单相等 + 不许再出现按单家公司硬编码的判断。
    """

    def test_the_known_tool_list_matches_the_table(self):
        self.assertEqual(ts_names("KNOWN_TOOLS"), set(doctor.COMMAND_SYNTAX),
                         "面板认识的工具与 COMMAND_SYNTAX 的格子对不上 —— "
                         "探测加一档，面板那头会把它的快照归到 generic 上")

    def test_the_slash_list_matches_the_table(self):
        slash = {k for k, v in doctor.COMMAND_SYNTAX.items() if v == "slash"}
        self.assertEqual(ts_names("SLASH_TOOLS"), slash,
                         "面板的斜杠档名单与 COMMAND_SYNTAX 的 slash 格对不上")

    def test_nobody_re_derives_the_answer_from_one_vendor_name(self):
        src = TS_CTX.read_text(encoding="utf-8")
        self.assertNotIn('!== "claude"', src,
                         "又退回去按 claude 一家硬编码了 —— 读 SLASH_TOOLS")
        cmdbook = (ROOT / "web" / "src" / "components" / "CommandBook.tsx") \
            .read_text(encoding="utf-8")
        self.assertNotIn('=== "claude"', cmdbook,
                         "开关那一头也别再点名 claude，形式问题问 context")


if __name__ == "__main__":
    unittest.main()
