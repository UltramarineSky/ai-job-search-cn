# -*- coding: utf-8 -*-
"""技能的 `allowed-tools` 必须覆盖它那份工作流真要跑的命令。

## 实测抓到的

`.claude/skills/*/SKILL.md` 是薄壳，正文都在 `workflows/<名>.md`。壳上那行
`allowed-tools` 决定技能跑起来时手里有哪些工具——而它是**手写**的，工作流里加一条
命令不会自动反映过来。2026-08-18 扫出两处，都是同一个形状：

| 技能 | 工作流要跑 | `allowed-tools` 里有 |
|---|---|---|
| `job-scrape` | `python tools/{doctor,query_yield,jd_store,export_web_data}.py` | 只有 node / bun 那四条 |
| `job-upskill` | `python tools/gap_split.py` | **一条 Bash 都没有** |

`job-upskill` 那条尤其说明问题：它的工作流写着「**用工具分，别手数**——四格是机械
的，手数容易错」，然后把唯一能分的那个工具挡在了权限外面。

已有的两条检查都够不着这件事：`test_bash_permissions_use_the_prefix_form` 只看
**写法**对不对（冒号前缀而非空格），`lint_skills` 只看 Bash 规则里的路径**存不存在**。
两条都是「你写下的那几条合不合规」，没有一条问「你该写的都写了吗」。

## 判据

从工作流的 ```bash 代码块里取要跑的命令——**只认代码块**。正文里
「Claude Code 本身走 `npm install -g` 安装」是在说明**别人**怎么装，不是让执行者跑
`npm`；按行文抓会把它算成缺失，那种误报会逼着下一个人给技能开一个根本不需要的
`npm` 权限。

只比到「解释器 + 第一个参数」这一层（`python tools/gap_split.py`）。再细就等于把
每个参数组合都钉死，工作流换个 flag 就红。
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

#: 要在 shell 里跑的解释器。`git` 不在内——工作流里没有，写进来只会招误报。
RUNNERS = ("python", "python3", "node", "bun", "npm", "npx",
           "typst", "pdftotext", "pdftoppm")

_FENCE = re.compile(r"```(?:bash|sh|shell|console)\n(.*?)```", re.S)
_ALLOWED = re.compile(r"^allowed-tools:(.*)$", re.M)

#: 正文（不在代码块里）出现的 `python tools/X.py`：要么被 `allowed-tools`
#: 覆盖，要么在这张表里写明「那不是跑起来要执行的步骤」。
#:
#: **为什么不能只看代码块。** 上面那段说明的理由是对的（正文里「别人怎么装」
#: 那类不该算），但它把另一半也挡在了外面：真正的运行时步骤有时就写在正文里。
#: 实测 2026-08-31 `job-scrape.md` 有一条 ——
#: 「`--no-rank` …这条路要**自己收尾**：跑一次 `python tools/export_web_data.py`
#: 刷新面板」。它恰好被授权了，所以没出事；而这条检查看不见它。
#:
#: 判不了意图就别装作判得了：这张表逼人每次看一眼，不替他决定。
INLINE_EXEMPT = {
    ("job-scrape", "python tools/audit_pipeline.py"):
        "「下次改这一步之前，先跑…」—— 给改工作流的人看的，不是运行时的步骤",
}


def _inline_commands(workflow: Path) -> set:
    """正文里（剥掉代码块之后）出现的 `python tools/X.py`。"""
    t = re.sub(r"```[\s\S]*?```", "", workflow.read_text(encoding="utf-8"))
    return {f"python tools/{x}.py"
            for x in re.findall(r"python\s+tools/([a-z_]+)\.py", t)}


def _skills():
    return sorted(ROOT.glob(".claude/skills/*/SKILL.md"))


def _target_workflow(skill: Path):
    """壳指向的那份工作流。

    认「读取并严格执行 `workflows/<名>.md`」这一句，**不是全文第一个
    `workflows/…` 链接**：`job-application-assistant` 的正文里列着五份参考资料，
    还有一句「实际投递走 `workflows/job-apply.md`」——那是给用户指路，不是它自己
    要执行的东西。按第一个链接取会把 `job-apply.md` 算成它的正文，然后要求这个
    纯咨询壳去申请 typst 与 pdftotext 权限（实测第一版就是这么误报的）。
    """
    text = skill.read_text(encoding="utf-8")
    m = re.search(r"(?:读取并严格执行|执行)\s*`workflows/([\w-]+\.md)`", text)
    if not m:
        return None
    p = ROOT / "workflows" / m.group(1)
    return p if p.is_file() else None


def _commands_in(workflow: Path) -> set:
    """工作流的 ```bash 块里，每条命令的「解释器 + 第一个参数」。"""
    out = set()
    for block in _FENCE.findall(workflow.read_text(encoding="utf-8")):
        for line in block.splitlines():
            line = line.strip().lstrip("$ ").strip()
            # 行尾注释不算命令的一部分
            line = line.split("#")[0].strip()
            parts = line.split()
            if len(parts) >= 2 and parts[0] in RUNNERS:
                out.add(f"{parts[0]} {parts[1]}")
            elif len(parts) == 1 and parts[0] in RUNNERS:
                out.add(parts[0])
    return out


def _allowed_bash(skill: Path) -> list:
    m = _ALLOWED.search(skill.read_text(encoding="utf-8"))
    return re.findall(r"Bash\(([^)]*)\)", m.group(1)) if m else []


def _covered(cmd: str, rules: list) -> bool:
    """某条命令是否被任一规则允许。

    规则是前缀形式 `<前缀>:*`，也可能是精确形式（`node --version`）。
    两种都按「命令以规则的前缀开头」判——精确形式恰好是前缀的退化情形。
    """
    for r in rules:
        prefix = r[:-2] if r.endswith(":*") else r
        # 通配的路径段（`.agents/skills/*/cli/...`）按正则比
        if "*" in prefix:
            pat = "^" + ".*".join(re.escape(x) for x in prefix.split("*"))
            if re.match(pat, cmd):
                return True
        elif cmd.startswith(prefix):
            return True
    return False


class SkillPermissionsCoverItsWorkflow(unittest.TestCase):

    def test_the_scan_finds_the_skills(self):
        """控制用例：一个技能都没扫到时下面那条是空跑。"""
        self.assertGreaterEqual(len(_skills()), 3, "技能目录扫空了，判据失去依据")

    def test_every_runnable_command_is_permitted(self):
        bad = []
        for sk in _skills():
            wf = _target_workflow(sk)
            if wf is None:
                continue                      # 纯咨询壳，没有要执行的正文
            rules = _allowed_bash(sk)
            for cmd in sorted(_commands_in(wf)):
                if not _covered(cmd, rules):
                    bad.append(f"{sk.parent.name}: 工作流要跑 `{cmd}`，"
                               f"但 allowed-tools 里没有对应的 Bash 规则")
        self.assertEqual(
            bad, [], "\n  " + "\n  ".join(bad)
            + "\n技能跑起来时手里只有 allowed-tools 列出的工具；缺一条，"
              "工作流里那一步就得让用户逐次手批，或者干脆跑不了。")

    def test_inline_commands_are_granted_or_exempt(self):
        """写在正文里的运行时步骤，代码块那条判据看不见。

        判不了「这句是给谁看的」，所以不猜：要么权限已经给了，要么有人
        在 `INLINE_EXEMPT` 里写明为什么不算步骤。
        """
        bad = []
        for sk in _skills():
            wf = _target_workflow(sk)
            if wf is None:
                continue
            name = sk.parent.name
            rules = _allowed_bash(sk)
            fenced = _commands_in(wf)
            for cmd in sorted(_inline_commands(wf)):
                if cmd in fenced or _covered(cmd, rules):
                    continue
                if (name, cmd) in INLINE_EXEMPT:
                    continue
                bad.append(f"{name}: 正文里写着 `{cmd}`，而 allowed-tools 没给 "
                           f"—— 是运行时的步骤就补权限，不是就进 INLINE_EXEMPT")
        self.assertEqual(bad, [], "\n  " + "\n  ".join(bad))

    def test_the_inline_scan_sees_something(self):
        """控制用例：正文里一条都扫不到时，上面那条是空跑。

        实测 2026-08-31 `job-scrape.md` 正文里有两条（`export_web_data`
        与 `audit_pipeline`），一条被授权、一条在豁免表里。
        """
        got = set()
        for sk in _skills():
            wf = _target_workflow(sk)
            if wf is not None:
                got |= _inline_commands(wf)
        self.assertGreaterEqual(len(got), 2, f"正文里只扫到 {got}")

    def test_the_exemptions_are_still_real(self):
        """豁免指着一条正文里已经没有的命令时，这张表该清了。"""
        stale = []
        for (name, cmd), _why in INLINE_EXEMPT.items():
            wf = ROOT / "workflows" / f"{name}.md"
            if not wf.is_file() or cmd not in _inline_commands(wf):
                stale.append(f"{name}: {cmd}")
        self.assertEqual(stale, [], f"这几条豁免已经没有对应的正文了：{stale}")

    def test_a_consulting_shell_is_not_asked_for_permissions(self):
        """纯咨询壳（正文里只有参考资料、没有「执行 workflows/x.md」）应当被跳过。

        `job-application-assistant` 就是这一种：它给建议，真要投递时把人交给
        `/job-apply`（那条命令没有 allowed-tools 限制）。要求它申请 typst 权限
        既没必要，也会让人以为这个壳自己会编译 PDF。
        """
        shell = ROOT / ".claude" / "skills" / "job-application-assistant" / "SKILL.md"
        # **不跳过**：`.claude/skills/` 下这三个壳是本仓库自带的、已跟踪的，
        # 不像 `.agents/skills/` 下的渠道技能那样可插拔。它不在就是出事了。
        self.assertTrue(shell.is_file(),
                        "job-application-assistant 的壳不在了 —— 它是自带技能，不该缺")
        self.assertIsNone(_target_workflow(shell),
                          "咨询壳被当成了执行壳——判据认错了「执行」那一句")

    def test_the_check_would_actually_catch_something(self):
        """控制用例：判据对一条明显缺失的权限必须报。"""
        self.assertFalse(_covered("python tools/gap_split.py",
                                  ["Bash(node --version)"]),
                         "判据把一条没被允许的命令当成允许了")
        self.assertTrue(_covered("python tools/gap_split.py",
                                 ["python tools/gap_split.py:*"]))
        self.assertTrue(_covered("node .agents/skills/liepin-search/cli/src/cli.ts",
                                 ["node .agents/skills/*/cli/src/cli.ts:*"]),
                        "带通配的路径规则没认出来")


if __name__ == "__main__":
    unittest.main()
