"""猎聘 CLI 必须能在 **Node** 上直接跑，不强制用户装 Bun。

为什么这条重要：Claude Code 本身走 `npm install -g` 安装，**所以每个用户必然已经有
Node**。CLI 的 `src/` 零 runtime 依赖，只要避开「需要生成代码」的 TS 特性，
`node src/cli.ts` 就能直接跑（Node 22.18+ 默认剥离类型），Bun 就从「必装」降为「可选」。

Node 的类型剥离**只做擦除、不做转换**，所以这几类 TS 特性会让它直接抛错：

- **构造器参数属性**（`constructor(readonly code: string)`）—— 曾经就是这个卡住的
- `enum`（非 `const enum` 也不行）、`namespace`、装饰器

而 Bun 全都支持，所以一旦有人改回去，**Bun 侧测试全绿、typecheck 全绿，只有 Node 用户会崩**
—— 静默退化成「必须装 Bun」。这条测试就是拦这个。

相对 import 必须写 `.ts` 后缀（tsconfig 已开 `allowImportingTsExtensions`，且本 CLI
从不编译、永远从源码跑）：Node 不会把 `.js` 映射回 `.ts`，写 `.js` 会 ERR_MODULE_NOT_FOUND。
"""

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

#: 覆盖**所有** portal CLI，不只 liepin —— `/job-add-portal` 生成的新 CLI 也要守同一套约束
#: （契约写在 workflows/job-add-portal.md 的「portal-skill 契约」里）。
SRC_DIRS = sorted(REPO_ROOT.glob(".agents/skills/*/cli/src"))


def _ts_files():
    return [p for d in SRC_DIRS for p in sorted(d.rglob("*.ts"))]


class NodeStrippableTests(unittest.TestCase):
    def test_at_least_one_portal_cli_present(self):
        self.assertTrue(SRC_DIRS, "找不到任何 portal CLI 的 src/ —— glob 根写错了或目录搬了")
        self.assertTrue(_ts_files(), "portal CLI 的 src/ 下没有 .ts 文件")

    def test_no_constructor_parameter_properties(self):
        """构造器参数属性需要生成代码，Node 剥离不了。"""
        pat = re.compile(
            r"constructor\s*\([^)]*\b(readonly|private|public|protected)\b", re.S)
        for p in _ts_files():
            text = p.read_text(encoding="utf-8")
            self.assertIsNone(
                pat.search(text),
                f"{p.relative_to(REPO_ROOT)} 用了构造器参数属性 —— Node 的类型剥离只做擦除、"
                f"不做转换，`node src/cli.ts` 会直接抛错。改成显式声明字段 + 构造器里赋值。",
            )

    def test_no_enum_namespace_or_decorators(self):
        """enum / namespace / 装饰器同样需要生成代码。"""
        checks = (
            (re.compile(r"^\s*(export\s+)?(const\s+)?enum\s+", re.M), "enum"),
            (re.compile(r"^\s*(export\s+)?namespace\s+", re.M), "namespace"),
            (re.compile(r"^\s*@\w+", re.M), "装饰器"),
        )
        for p in _ts_files():
            text = p.read_text(encoding="utf-8")
            for pat, name in checks:
                self.assertIsNone(
                    pat.search(text),
                    f"{p.relative_to(REPO_ROOT)} 用了 {name} —— Node 的类型剥离不支持，"
                    f"会让 CLI 只能在 Bun 上跑。",
                )

    def test_relative_imports_use_ts_extension(self):
        """Node 不会把 `.js` 映射回 `.ts`，写 `.js` 会 ERR_MODULE_NOT_FOUND。"""
        bad = re.compile(r'from\s+"((?:\./|\.\./)[^"]*\.js)"')
        for p in _ts_files():
            text = p.read_text(encoding="utf-8")
            hits = bad.findall(text)
            self.assertFalse(
                hits,
                f"{p.relative_to(REPO_ROOT)} 的相对 import 还写着 .js：{hits}。"
                f"本 CLI 永不编译、只从源码跑，import 要写 .ts",
            )

    def test_relative_imports_actually_resolve(self):
        """控制用例：`.ts` import 指向的文件必须真实存在。"""
        pat = re.compile(r'from\s+"((?:\./|\.\./)[^"]+)"')
        for p in _ts_files():
            for spec in pat.findall(p.read_text(encoding="utf-8")):
                target = (p.parent / spec).resolve()
                self.assertTrue(
                    target.is_file(),
                    f"{p.relative_to(REPO_ROOT)} 引用的 {spec} 解析不到文件（{target}）",
                )


class ZeroRuntimeDepTests(unittest.TestCase):
    def test_the_start_script_uses_node(self):
        """`package.json` 的 `start` 也要走 node —— 新 portal 会照抄这份文件。

        2026-08-21 通读 `/job-add-portal` 时抓到：这份参考技能的
        `"start": "bun run src/cli.ts"`，而同一份工作流明写
        「**运行时：node 与 bun 都要能跑，且 node 是默认路径**」，
        Step 3 又要求新技能「照抄它的架构」—— **这一处会被复制进每个新技能**。

        本文件其余判据管的是 `src/` 里的 TS 语法与依赖，**没有一条看
        `package.json` 的脚本**。`test` 用 bun 是对的（测试写的是 `bun:test`），
        只有 `start` 该跟着默认运行时走。
        """
        import json as _json

        for pkg in (REPO_ROOT / ".agents" / "skills").glob("*/cli/package.json"):
            scripts = (_json.loads(pkg.read_text(encoding="utf-8"))
                       .get("scripts") or {})
            start = scripts.get("start", "")
            if not start:
                continue
            with self.subTest(skill=pkg.parent.parent.name):
                self.assertNotIn(
                    "bun", start,
                    f"{pkg.parent.parent.name} 的 start 脚本走 bun（{start!r}）—— "
                    "而 node 才是文档说的默认路径，新 portal 会照抄这一行")

    def test_no_runtime_dependencies(self):
        """零 runtime 依赖是「Node 直接跑」的前提——有依赖就得先 install。"""
        import json
        for d in SRC_DIRS:
            pkg_path = d.parent / "package.json"
            self.assertTrue(pkg_path.is_file(), f"{pkg_path} 不存在")
            pkg = json.loads(pkg_path.read_text(encoding="utf-8"))
            self.assertEqual(
                pkg.get("dependencies", {}), {},
                f"{pkg_path.relative_to(REPO_ROOT)} 出现了 runtime 依赖，"
                f"Node 用户就得先跑 install 了")

    def test_src_uses_no_bun_globals(self):
        """src/ 不得用 Bun 专有 API（tests/ 用 bun:test 无妨，那只影响开发）。"""
        for p in _ts_files():
            text = p.read_text(encoding="utf-8")
            self.assertNotIn("Bun.", text,
                             f"{p.relative_to(REPO_ROOT)} 用了 Bun 专有 API，Node 跑不了")
            self.assertNotIn('from "bun', text,
                             f"{p.relative_to(REPO_ROOT)} 从 bun: 导入，Node 跑不了")


class EveryPortalSkillPermitsNode(unittest.TestCase):
    """技能的工具权限清单里必须同时允许 node 和 bun。

    上面那几条守的是 **CLI 源码**能不能在 Node 上跑。可就算源码没问题，
    技能的权限清单只写了 `Bash(bun run …)` 的话，Node 用户照样跑不了——
    而报错长得像权限问题，不像「你少装了个东西」。

    实测 `workflows/job-add-portal.md` 就是这么教的：它让生成器只写 bun 那一条，
    而同一份文件上一节刚宣布「**node 是默认路径**，用户不必额外装 Bun」，
    范例 `liepin-search` 的权限行也是两条都有。**照它生成的每一个新平台技能，
    在文档自己宣布的默认运行时上都跑不起来。**

    这里同时钉住两头：现有技能的权限行，以及 `add-portal.md` 教人怎么写的那一段。
    """

    SKILLS = sorted(REPO_ROOT.glob(".agents/skills/*/SKILL.md"))
    ADD_PORTAL = REPO_ROOT / "workflows" / "job-add-portal.md"

    def test_there_is_a_skill_to_check(self):
        """控制用例：真扫到了技能。"""
        self.assertTrue(self.SKILLS, "`.agents/skills/*/SKILL.md` 一个都没找到")

    def test_each_skill_allows_both_runtimes(self):
        bad = []
        for p in self.SKILLS:
            head = p.read_text(encoding="utf-8").split("---")[1] if "---" in p.read_text(encoding="utf-8") else ""
            if "cli.ts" not in head:
                continue          # 不是 portal CLI 技能，没有这条约束
            for runtime in ("Bash(node ", "Bash(bun run "):
                if runtime not in head:
                    bad.append(f"{p.parent.name}: 权限清单里没有 `{runtime}…`")
        self.assertEqual(
            bad, [],
            "这些技能的权限清单少了一个运行时：" + chr(10) + "  " + (chr(10) + "  ").join(bad)
            + chr(10) + "node 是默认路径（用户装 AI 工具时就有），bun 是可选加速；"
            + chr(10) + "只允许其中一个，另一边的用户会撞上一个看着像权限问题的报错。")

    def test_add_portal_teaches_both(self):
        """生成器的说明里两条命令模式都要出现，否则新技能一生成就是坏的。

        断言的是**规则**不是某一种写法：两个运行时各有一条、且都用前缀形式。
        这条原来把 `Bash(node …cli.ts *)` 整串钉死，于是 2026-08-18 把空格版
        改成正确的 `:*` 前缀形式时它红了——**正当的修复被守卫拦下**，
        正是 `CONTRIBUTING.md` 那张失效表里的「断言绑死一种写法而非规则」。
        """
        t = self.ADD_PORTAL.read_text(encoding="utf-8")
        for runtime in ("node", "bun run"):
            with self.subTest(runtime=runtime):
                pat = re.compile(
                    r"Bash\(" + runtime.replace(" ", r"\s+")
                    + r"\s+\.agents/skills/<name>/cli/src/cli\.ts(\S*)\)")
                m = pat.search(t)
                self.assertIsNotNone(
                    m, f"add-portal.md 没教生成 `{runtime}` 那条——"
                       "少哪条，新技能就在哪个运行时上跑不了。")
                self.assertEqual(
                    m.group(1), ":*",
                    f"`{runtime}` 那条不是前缀形式（`:*`）。空格加星是精确匹配，"
                    "真实调用后面还跟着 search -q … -l …，永远匹配不上。")


if __name__ == "__main__":
    unittest.main()
