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

**这两条判据的实现现在住在 `tools/_entries.py`（`commands_in()` 与 `covered()`），
本文件 import 它，不再自己抄一份。**原来这里是 `RUNNERS`、`_FENCE`、
`_commands_in()`、`_covered()` 四样副本（2026-08-18 那两次事故催生的判据，
Task 2 把它们搬进派生器，2026-09-29 删掉这一份）—— 同一个「什么算一条要跑的命令」
写两处，改一处忘一处，而忘的那一处正是缺口藏身的地方
（`AGENTS.md`「一条规则只贴在一个写手身上，另外两个照样会犯」）。

留在本文件的是另外两半，它们不是副本：`_ALLOWED` / `_allowed_bash` 读的是**壳**
（派生器只管生成，不管回读），`_inline_commands` / `INLINE_EXEMPT` / `FENCE_EXEMPT`
问的是**正文里那句算不算运行时步骤** —— 生成器刻意不问这个问题（它只认代码块），
所以判据在派生器里没有、也不该有对应实现。

## 围栏必须贴 bash 标签（2026-09-29 Task 3 评审后新增）

上面这套「围栏 + 正文」双路提取有个共同盲区：**裸 ``` 围栏**。围栏提取只认
`_entries._FENCE` 那几种标签（bash / sh / shell / console），而正文提取先把所有
围栏整段剥掉——藏在没贴标签的围栏里的命令，**两头都看不见**。实测代价：`job-auto.md` 收尾段
九条 `python tools/*.py`（writeback / archive / export_web_data / check_outreach…）
藏在裸围栏里，生成的壳一条都没批，招牌命令每一步都要用户手点授权；而当时的
缺口清单数出 13 条，正是因为同一类缺口对判据不可见。所以这里加一条守卫：
`test_no_unlabelled_fence_hides_a_runner_command`。修法是**给围栏贴标签**，
不是给壳补权限——贴上 `bash`，派生自然就批到了。
"""

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import _entries  # noqa: E402  （判据只有一份：commands_in / covered / derives_nothing / fence_blocks / _one_command）

#: 读**壳**的判据（不是派生权限的判据），所以留在本文件。
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
    # 下面两条同形状：那一句讲的是**用户走的另一条路**（总览页上点按钮），
    # 不是这条命令自己要跑的一步。给它们补权限等于替「面板」这条路与本命令绑定，
    # 而面板那条路由 `/job-dashboard`（正文围栏里就写着 serve.py）负责。
    ("job-rank", "python tools/serve.py"):
        "「先确认用户是不是在走这条路。总览页正常跑法是 python tools/serve.py」——"
        "那是**指路**：服务已开着时点「不投」直接写回，根本不进这条命令",
    ("job-outcome", "python tools/serve.py"):
        "「用 python tools/serve.py 打开总览页时…点一下就行，不用回来跑这条命令」——"
        "同上，那一段的存在理由就是把用户**从这条命令上引开**",
}

#: 围栏里**真跑**、而派生器**刻意不映射**的那几条（`_entries._rule_for` 返回 None）。
#:
#: **这不是逃生口**：一条命令能进这张表的前提是派生器自己也拒绝为它生成规则
#: （下面 `test_the_fence_exemptions_stay_narrow` 逐条这么验）。所以「把授权放宽
#: 到能派生、好让豁免消失」那种反向操作在这里走不通——能派生的命令永远被
#: `test_every_runnable_command_is_permitted` 逼着补权限。
#:
#: 为什么需要一个 INLINE_EXEMPT 之外的表：inline 那张管的是「这句到底是步骤吗」，
#: 而这里的是**步骤**，只是它的窄权限不存在。
FENCE_EXEMPT = {
    ("job-html-report", "python -c"):
        "`--open` 那一步用 `python -c \"…webbrowser.open…\"` 把刚写出的报表打开。"
        "`Bash(python -c:*)` 授权的是**任意内联代码**，而 `Bash(python:*)` 等于没有闸门"
        "（`tests/test_entries_derivation.py::test_no_wide_bash_rule_is_derived` 就钉着"
        "派生器不许产出 `python -c`）。仓库里也没有第二个脚本能打开任意路径 —— "
        "`tools/` 里唯一用 webbrowser 的是 `serve.py`，而它起的是总览页服务。"
        "**所以这条缺口是设计**：工作流正文自己写着「没有执行权限就开口要；"
        "真的要不到，再退回告诉他路径」。撤掉豁免的正确做法是给仓库加一个"
        "`tools/` 下的确定性入口，不是给它加权限。",

    ("job-add-portal", "node .agents/skills/<name>/cli/src/cli.ts"):
        "这一条与其余几条不是一类：它不是**漏批**，是**批不了**。工作流里那句是"
        "模板（`<name>` 要被换成新渠道的目录名，见 `job-add-portal.md` 自己写的"
        "`Bash(node .agents/skills/<name>/cli/src/cli.ts:*)` 那一步），渠道还没落地"
        "时盘上根本没有这条路径，`derives_nothing()` 因此认它派生不出规则。"
        "已装着的渠道由 `_entries.PORTAL_BASH` 逐条批**具体**前缀，那些是真覆盖得住的。"
        "\n\n原来这一格是靠通配规则 `Bash(node .agents/skills/*/cli/src/cli.ts:*)` "
        "过检的，而 2026-09-29 实测证明那条通配在 Claude 里什么都不放行（前缀按字面比，"
        "中间的 `*` 就是星号）——**它盖住这条模板只是因为 `covered()` 比真实客户端宽**，"
        "不是因为它批到了什么。撤掉豁免的正确做法不是把通配写回来（那边有专门的测试拦"
        "：`test_bash_permissions_use_the_prefix_form.py::test_no_mid_pattern_wildcard`），"
        "而是新渠道建好后把它的具体前缀补进 `PORTAL_BASH`。",
}


def _inline_commands(workflow: Path) -> set:
    """正文里（剥掉代码块之后）出现的 `python tools/X.py`。"""
    t = re.sub(r"```[\s\S]*?```", "", workflow.read_text(encoding="utf-8"))
    return {f"python tools/{x}.py"
            for x in re.findall(r"python\s+tools/([a-z_]+)\.py", t)}


def _hidden_runner_commands(text: str) -> list:
    """裸围栏（``` 后不写语言标签）里藏着的 RUNNERS 命令。

    判据全部借自派生器本尊——`_entries.fence_blocks`（外层围栏配对）、
    `_entries._one_command`（一行算不算命令，与 `commands_in` 同一个）——
    **「哪些标签的围栏算命令块」这一个判断，本文件已经不再自己写一份**
    （原来那份模块级 `_FENCE` 与逐行判据 `_commands_in()` 已删，改读
    `_entries.commands_in`）。
    ⚠️ 这句话的范围要说准：`_inline_commands()` 里那个**整段剥掉围栏**的
    `re.sub` **还在**，但它不是这里的副本 —— 它剥的是**全部**围栏
    （不分标签、不做外层配对），为的是「围栏之外正文里提到的命令」那半边判据，
    与「哪段算命令块」是两个问题。
    只查**没贴标签**的：`json` / `python` / `markdown` 那些是明确声明过的
    「非命令块」，命令藏在里面不算盲区。
    """
    out = []
    for label, body in _entries.fence_blocks(text):
        if label:
            continue
        for line in body.splitlines():
            cmd = _entries._one_command(line)
            if cmd:
                out.append(cmd)
    return out


def _skills():
    """两族壳都要查。

    `.claude/skills/` 与 `.agents/skills/` 逐字相同（生成器保证），但**这条测试查的
    不是「两份一致」而是「壳的权限够不够它那份工作流用」**——只查一族的话，
    将来有人手改另一族，工作流照跑、权限不够，用户看到的是一串失败的命令。
    """
    out = []
    for fam in _entries.SHELL_FAMILIES:
        out += sorted((ROOT / fam / "skills").glob("*/SKILL.md"))
    return out


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


def _allowed_bash(skill: Path) -> list:
    m = _ALLOWED.search(skill.read_text(encoding="utf-8"))
    return re.findall(r"Bash\(([^)]*)\)", m.group(1)) if m else []


class SkillPermissionsCoverItsWorkflow(unittest.TestCase):

    def test_the_scan_finds_the_skills(self):
        found = _skills()
        self.assertGreaterEqual(
            len(found), 44,
            f"只扫到 {len(found)} 份壳 —— 大概是 glob 打空了，而不是仓库真的只剩这么几份。"
            "（22 × 两族 = 44，另加 .agents/skills/liepin-search）")

    def test_every_runnable_command_is_permitted(self):
        bad = []
        for sk in _skills():
            wf = _target_workflow(sk)
            if wf is None:
                continue                      # 纯咨询壳，没有要执行的正文
            name = sk.parent.name
            rules = _allowed_bash(sk)
            for cmd in sorted(_entries.commands_in(wf.read_text(encoding="utf-8"))):
                if _entries.covered(cmd, rules):
                    continue
                if (name, cmd) in FENCE_EXEMPT and _entries.derives_nothing(cmd):
                    continue                  # 派生器也不认它 —— 见那张表的说明
                bad.append(f"{sk.relative_to(ROOT).as_posix()}: "
                           f"工作流要跑 `{cmd}`，"
                           f"但 allowed-tools 里没有对应的 Bash 规则")
        self.assertEqual(
            bad, [], "\n  " + "\n  ".join(bad)
            + "\n技能跑起来时手里只有 allowed-tools 列出的工具；缺一条，"
              "工作流里那一步就得让用户逐次手批，或者干脆跑不了。")

    def test_the_fence_exemptions_stay_narrow(self):
        """FENCE_EXEMPT 只能装「派生器自己也拒绝映射」的那几条，而且要还活着。

        没有这条，那张表就跟所有豁免表一样慢慢烂成一个逃生口：先随手加一条把红的
        测试压绿，下一个人在下面那条上照抄一次 —— 于是缺口被登记成规矩。
        两条判据都要在：命令还在那份围栏里（豁免没有对着幽灵），
        以及 `derives_nothing` 仍说不派生（**有人给派生器开了宽规则，
        这条就先红** —— 那正是该撤豁免的那一刻，不是该留着的）。
        """
        ghost, too_wide = [], []
        for (name, cmd), _why in FENCE_EXEMPT.items():
            wf = ROOT / "workflows" / f"{name}.md"
            self.assertTrue(wf.is_file(), f"{name}: 豁免指着一份不存在的工作流")
            if cmd not in _entries.commands_in(wf.read_text(encoding="utf-8")):
                ghost.append(f"{name}: {cmd}")
            if not _entries.derives_nothing(cmd):
                too_wide.append(f"{name}: {cmd}")
        self.assertEqual(ghost, [], f"这几条豁免指着的命令已经不在围栏里了：{ghost}")
        self.assertEqual(
            too_wide, [],
            f"派生器现在能为这几条生成规则了，豁免该撤、权限该补：{too_wide}")

    def test_the_fence_exemption_table_is_not_empty_by_accident(self):
        """对照用例：这张表真在豁免一条**会被上面那条抓到**的缺口。

        做法是把它临时清空再跑一次同样的判定 —— 有缺口时列表必须非空。
        否则「表里的都被 derives_nothing 放行」可能只是因为根本没有缺口。
        """
        if not FENCE_EXEMPT:
            self.skipTest("没有围栏豁免，这条对照不适用")
        # 用集合而不是列表：两族壳字节相同，同一条缺口会在 `.claude` 与
        # `.agents` 各出现一次 —— 那是**同一条**豁免盖住的同一个洞，不是两个洞。
        holes = set()
        for sk in _skills():
            wf = _target_workflow(sk)
            if wf is None:
                continue
            name = sk.parent.name
            rules = _allowed_bash(sk)
            for cmd in _entries.commands_in(wf.read_text(encoding="utf-8")):
                if (not _entries.covered(cmd, rules)
                        and (name, cmd) in FENCE_EXEMPT):
                    holes.add(f"{name}: {cmd}")
        self.assertEqual(sorted(holes), sorted(f"{n}: {c}" for (n, c) in FENCE_EXEMPT),
                         "表里记的和实际缺口不一致 —— 要么多登了，要么那条已被别的方式覆盖")

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
            fenced = _entries.commands_in(wf.read_text(encoding="utf-8"))
            for cmd in sorted(_inline_commands(wf)):
                if cmd in fenced or _entries.covered(cmd, rules):
                    continue
                if (name, cmd) in INLINE_EXEMPT:
                    continue
                bad.append(f"{sk.relative_to(ROOT).as_posix()}: "
                           f"正文里写着 `{cmd}`，而 allowed-tools 没给 "
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
        """纯咨询壳不申请执行权限 —— 权限窄是它的边界，不是漏了。

        `job-application-assistant` 是「聊到求职就自动接管」的：一句「看看这个岗」
        就把控制权交给它。这样的壳手里不该攥着编译、写盘、起子代理。
        真要出材料那一步它把人交给 `/job-apply`——那是**另一个壳**，权限由它自己
        那份工作流正文派生，与本壳无关。

        判据：本壳的 `allowed-tools` 里不出现 Bash 与 Agent。给它开 typst 既没必要，
        也会让人以为这个壳自己会编译 PDF。

        （原来这条给的理由是「`/job-apply` 那条命令**没有 allowed-tools 限制**」，
        而那句在 stub 删掉之后不成立：`/job-apply` 今天是一个生成壳，自己带着
        由它那份工作流正文派生的 `allowed-tools`。同一个旧理由**还写在路由壳的
        正文里**（两族 `skills/job-application-assistant/SKILL.md` 都有一句
        「那两条命令的 stub 没有 frontmatter，不受本壳的权限限制」）——
        那是壳的正文，改它要两族一起改，不是这条测试的范围；
        谁只改了一边，`tests/test_shell_families_are_byte_identical.py`
        的 `test_the_handwritten_router_matches_too` 当场红。）
        """
        for fam in _entries.SHELL_FAMILIES:
            p = ROOT / fam / "skills" / "job-application-assistant" / "SKILL.md"
            # **不跳过**：两族里这份壳都是本仓库自带、已入库的，不像
            # `.agents/skills/` 下的渠道技能那样可插拔。它不在就是出事了。
            self.assertTrue(p.is_file(),
                            f"{fam}: 咨询壳的壳文件不在了 —— 它是自带技能，不该缺")
            lines = [ln for ln in p.read_text(encoding="utf-8").splitlines()
                     if ln.startswith("allowed-tools:")]
            self.assertEqual(len(lines), 1,
                             f"{fam}: 咨询壳的 allowed-tools 行不是恰好一行，"
                             "下面那两条判据会对着不存在或重复的行放行")
            line = lines[0]
            self.assertNotIn("Bash(", line, f"{fam}: 咨询壳申请执行权限了")
            self.assertNotIn("Agent", line, f"{fam}: 咨询壳申请起子代理了")
            self.assertIsNone(_target_workflow(p),
                              f"{fam}: 咨询壳被当成了执行壳——判据认错了「执行」那一句")

    def test_the_check_would_actually_catch_something(self):
        """控制用例：判据对一条明显缺失的权限必须报（判据本尊在 `_entries.covered`）。"""
        self.assertFalse(_entries.covered("python tools/gap_split.py",
                                          ["Bash(node --version)"]),
                         "判据把一条没被允许的命令当成允许了")
        self.assertTrue(_entries.covered("python tools/gap_split.py",
                                         ["python tools/gap_split.py:*"]))
        self.assertTrue(
            _entries.covered("node .agents/skills/liepin-search/cli/src/cli.ts",
                             ["node .agents/skills/*/cli/src/cli.ts:*"]),
            "带通配的路径规则没认出来")

    def test_no_unlabelled_fence_hides_a_runner_command(self):
        """裸围栏里不许藏着要跑的命令 —— 那是派生与正文两条提取路的共同盲区。

        修法只有一个：**给围栏贴 `bash` 标签**，贴上派生就自然批到
        （job-rank 的 writeback / archive / export_web_data 就是这么被批的）。
        别给壳补 `extra_tools` 绕过去：留着一个看不见的围栏，下一个往里加的
        命令照样没人看见（2026-09-29 job-auto 事故的原样）。
        装散文、JSON、控制台回声、文件清单的围栏**不是**命令块——扫到命中时
        先读那段再动手，别见标签就贴。
        """
        bad = []
        bare_seen = 0
        for wf in sorted((ROOT / "workflows").rglob("*.md")):
            text = wf.read_text(encoding="utf-8")
            bare_seen += sum(1 for label, _ in _entries.fence_blocks(text) if not label)
            for cmd in sorted(set(_hidden_runner_commands(text))):
                bad.append(f"workflows/{wf.name}: 未贴标签的围栏里藏着 `{cmd}`"
                           " —— 它是要跑的命令就给围栏贴 bash，不是就移出围栏")
        self.assertGreaterEqual(
            len(list((ROOT / "workflows").rglob("*.md"))), 20,
            "workflows/ 扫空了，这条守卫在空集上恒绿")
        self.assertGreaterEqual(
            bare_seen, 30,
            f"全仓库只扫到 {bare_seen} 段裸围栏 —— 配对大概是坏了（实测 2026-09-29 是 57）")
        self.assertEqual(bad, [], "\n  " + "\n  ".join(bad))

    def test_the_unlabelled_fence_guard_can_fire(self):
        """对照用例：判据必须真抓得到那条盲区的命令 —— 否则上面恒绿。

        三个形状一起验：裸围栏里的命令要抓到；```bash 里的同一命令**不算**
        （派生看得见它，不是盲区）；裸围栏里的散文（`while 真:` 那类伪代码）
        不报——不然任何一份写流程图的文档都红。
        变异验证（2026-09-29 提交前实跑）：把 `job-auto.md` 的 bash 标签撕掉
        恢复成裸 ```，这条守卫的实体判据当场报出 9 条；贴回后归零。
        """
        text = ("散文\n\n```\npython tools/writeback.py --apply\n```\n\n"
                "```bash\npython tools/writeback.py --apply\n```\n\n"
                "```\nwhile 真:\n    1. 跑 /job-rank\n```\n")
        self.assertEqual(_hidden_runner_commands(text), ["python tools/writeback.py"],
                         "裸围栏里的命令没抓到，或把 bash 围栏/散文也误报了")


if __name__ == "__main__":
    unittest.main()
