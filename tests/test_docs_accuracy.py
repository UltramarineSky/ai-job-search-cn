"""面向新用户的两份入口文档（README / SETUP）不得引用不存在的东西。

为什么值得一条测试盯住：这两份是新用户唯一的入口，里面的每处路径与依赖说明都会被
照着执行。本轮实测抓到过三类漂移，都不会被任何现有检查发现：

1. **引用已删功能**：SETUP 写「薪资查询工具需要 Python 3.10+」，而薪资查询工具早已
   整个删除。新用户会为一个不存在的功能去装依赖。
2. **依赖归属写错**：Python 实际是 `/job-dashboard` 要用的，文档却只说「CI 检查脚本」，
   于是想看驾驶舱的人不知道要装它。
3. **共享框架文件路径写错**：README/SETUP 里的共享文件路径若失效，新用户第一步就撞空。

按用户解析的路径（`profile/…`、`resume/main.typ` 等）**不在本检查范围**——它们在
`users/<活动用户>/` 下、`/job-setup` 之前本就不存在，SETUP 顶部已有专门说明。
"""

import ast
import re
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ENTRY_DOCS = ("README.md", "SETUP.md")

#: 共享框架文件：不按活动用户解析，必须真实存在于仓库根。
SHARED_PATHS = (
    "resume/template.typ",
    "resume/example.typ",
    "resume/README.md",
    "cover_letter/template.typ",
    "templates/README.md",
    "documents/README.md",
    "AGENTS.md",
    "CLAUDE.md",
    "SECURITY.md",
    "CONTRIBUTING.md",
)

#: 已从仓库删除的功能，文档里不得再出现（否则新用户会为不存在的东西做准备）。
REMOVED_FEATURES = (
    "salary_lookup",
    "convert_salary_excel",
    "薪资查询工具",
    "migrate_to_multiuser",
)


class EntryDocPathTests(unittest.TestCase):
    def test_shared_framework_paths_exist(self):
        """文档引用的共享框架文件必须真实存在。"""
        for rel in SHARED_PATHS:
            self.assertTrue((REPO_ROOT / rel).exists(),
                            f"{rel} 被入口文档引用但不存在于仓库")

    def test_referenced_workflow_files_exist(self):
        """入口文档里指向 workflows/ 与 tools/ 的链接必须有效。"""
        pat = re.compile(r"(workflows/[A-Za-z0-9_./-]+\.md|tools/[A-Za-z0-9_-]+\.py)")
        for doc in ENTRY_DOCS:
            text = (REPO_ROOT / doc).read_text(encoding="utf-8")
            for rel in sorted(set(pat.findall(text))):
                self.assertTrue((REPO_ROOT / rel).is_file(),
                                f"{doc} 引用了不存在的 {rel}")


class TheCapabilityTableIsTheOnlySourceForDegradation(unittest.TestCase):
    """「缺这项能力怎么办」在 `AGENTS.md` 里只许有一张表写。

    AGENTS.md 自称「仓库规则的唯一权威来源」。同一条规则在这份文件里排进第二张表，
    结果不是冗余而是分叉——2026-08-18 当场造了一次：新加的「换个工具，哪些命令
    还能用」把「能力对照表」的降级列整列抄了过去，两处立刻各说各的（Gmail 那格
    正本写「全流程跳过并说明原因」，抄件写成「Step 0 就停」）。

    ## 判据只挡「抄进另一张表」，不挡「引用」

    第一版写的是「每个短语全文只许出现一次」，当场被两件事否掉：

    1. **同一张表里就会重复**——Gmail 与 Notion 两行的降级写法本来就一样；
    2. **讲这条规则的句子要引用它**——正如上面那段说明。

    这两类都不是分叉源。真正的分叉源是**另起一张表把降级列抄过去**，所以判据锚在
    表格行上：能力对照表之外，任何以 `|` 开头的行都不许带这些短语。散文里提、
    引号里引，随便。
    """

    #: 取自能力对照表「无此能力时的降级」列，每条都足够独特，不会在正常行文里撞上
    PHRASES = [
        "全流程跳过并说明原因",
        "`site:` 域名限定搜索兜底",
        "交付 .typ 源文件并说明编译方法",
        "两轮都不省略",
        "请用户粘贴页面文本",
    ]

    def _table_span(self, text: str):
        """能力对照表的起止字符位置（从小节标题到下一个 `##` 标题）。"""
        start = text.index("## 能力对照表")
        nxt = text.find("\n## ", start + 1)
        return start, (nxt if nxt != -1 else len(text))

    def test_no_other_table_restates_the_degradation(self):
        text = (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")
        lo, hi = self._table_span(text)
        bad = []
        for i, line in enumerate(text.splitlines(), 1):
            if not line.lstrip().startswith("|"):
                continue                      # 散文与引用不算
            off = text.index(line) if text.count(line) == 1 else None
            if off is not None and lo <= off < hi:
                continue                      # 就在能力对照表里，正当
            for ph in self.PHRASES:
                if ph in line:
                    bad.append(f"AGENTS.md:{i} 又排了一遍降级写法：「{ph}」")
        self.assertEqual(
            bad, [],
            "\n  ".join([""] + bad)
            + "\n降级写法只归「能力对照表」那一张；别的表要提就指过去，别复述。")

    def test_the_phrases_are_actually_in_the_table(self):
        """控制用例：短语若从能力对照表里消失，上面那条就在验一个不存在的规则。"""
        text = (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")
        lo, hi = self._table_span(text)
        table = text[lo:hi]
        missing = [ph for ph in self.PHRASES if ph not in table]
        self.assertEqual(missing, [],
                         f"这些短语已不在能力对照表里，判据失去依据：{missing}")


class RemovedFeatureTests(unittest.TestCase):
    def test_no_stale_references_to_removed_features(self):
        """已删功能不得在入口文档里复活。"""
        for doc in ENTRY_DOCS:
            text = (REPO_ROOT / doc).read_text(encoding="utf-8")
            for token in REMOVED_FEATURES:
                self.assertNotIn(token, text,
                                 f"{doc} 仍在提已删除的 {token}——新用户会为不存在的功能做准备")

    def test_removed_features_really_are_gone(self):
        """控制用例：确认这些功能确实已删（否则上面那条禁令本身就是错的）。"""
        for name in ("tools/salary_lookup.py", "tools/convert_salary_excel.py",
                     "tools/migrate_to_multiuser.py", "salary_lookup.py"):
            self.assertFalse((REPO_ROOT / name).exists(),
                             f"{name} 仍存在，REMOVED_FEATURES 名单需要更正")


class TheFrontendBuildPrerequisiteIsStatedEverywhere(unittest.TestCase):
    """`/job-dashboard` 现在要先构建一次前端 —— 三处必须都说到。

    这是「两套面板合并成一套」引入的**新前置条件**：总览页的界面是 React 写的，
    第一次出总览页之前要跑一次 `npm install && npm run build`。以前不需要
    （那时有个纯 Python 脚本直接吐 HTML）。

    一个新前置只写在一处的下场：用户跑了才撞错，而撞错的地方往往不解释怎么办。
    所以四处都要有，且说的是同一条命令：

    1. **README 的依赖表** —— 新用户照着它决定装什么，clone 之前就在读
    2. **自检** —— `doctor.py` 提前告诉他还差这一项
    3. **安装说明** —— SETUP.md 的 Python 一节
    4. **报错** —— 真撞上时工具自己也要说（`serve.py`）

    第 1 处是**实测新用户全程时补的**：前三处都写了，唯独那张「想用什么 / 需要装
    什么」的表还写着 `/job-dashboard` 只要 `+ Python 3.10+`。那是 GitHub 落地页上的
    表，新用户照它备齐环境，然后在第一次出总览页时撞上一条没预告的构建。

    `serve.py` 那一处是**逐条读终端文案时补的**：它只写了 `npm run build`，
    **漏掉 `npm install`**。第一次用的人根本没装过依赖，照做只会撞一个「vite 找不到」
    的错——而那条错不会告诉他还差一步。所以下面钉的是**完整那条**，不是只钉
    `npm run build`：漏掉前半截和整句都没写，对新用户是一样的结果。
    """

    #: 钉完整那条。只钉 `npm run build` 的话，`serve.py` 漏掉 `npm install` 照样绿。
    BUILD_CMD = "npm install && npm run build"

    def test_the_readme_dependency_table_says_it(self):
        text = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        rows = [ln for ln in text.splitlines()
                if ln.lstrip().startswith("|") and "/job-dashboard" in ln]
        self.assertTrue(rows, "README 的依赖表里找不到 /job-dashboard 那一行")
        self.assertTrue(
            any(self.BUILD_CMD in r for r in rows),
            "README 的依赖表把 /job-dashboard 说成只要 Python，漏了那次一次性构建："
            f"{rows}")

    def test_doctor_probes_it(self):
        sys.path.insert(0, str(REPO_ROOT / "tools"))
        import doctor
        item = next((e for e in doctor.probe_env() if e["key"] == "web_build"), None)
        self.assertIsNotNone(
            item, "自检不查前端构建 —— 用户会在跑 /job-dashboard 时才撞错")
        self.assertIn(self.BUILD_CMD, item["fix"], "查了却不说怎么构建")
        self.assertIn("dashboard", item["unlocks"], "没说这一项挡住的是什么")

    def test_setup_doc_says_it(self):
        text = (REPO_ROOT / "SETUP.md").read_text(encoding="utf-8")
        m = re.search(r"### Python\n(.{0,900})", text, re.S)
        self.assertIsNotNone(m, "SETUP.md 缺少 ### Python 一节")
        self.assertIn(self.BUILD_CMD, m.group(1),
                      "SETUP.md 没说总览页还要构建一次前端")

    def test_every_place_that_asks_you_to_build_says_the_whole_command(self):
        """**凡是叫人跑 `npm run build` 的地方，都得带上 `npm install`。**

        这条原来锚在一句话上（「web/dist 不存在」），于是只护得住那一句。逐条读
        终端文案时又抓到两处漏掉 `npm install` 的，都在别的语境里：

        - `export_web_data.py` 导出完给的「下一步：…」
        - `serve.py` 在**浏览器里**显示的那张「页面还没构建」——最显眼的一处

        锚在措辞上就只能护住那个措辞；换个说法写一遍，缺陷就原样复活。所以改成扫
        **所有会给用户看的字符串**，判据是那条命令自己：出现 `npm run build`，
        就必须出现 `npm install`。

        模块 docstring 不算——那是给读代码的人看的，不是给用户的。
        """
        bad = []
        for p in sorted((REPO_ROOT / "tools").glob("*.py")):
            try:
                tree = ast.parse(p.read_text(encoding="utf-8"))
            except SyntaxError:
                continue
            # docstring 按**节点**排除，不按文本比：`ast.get_docstring()` 返回的是
            # 清理过（去缩进、去首尾空白）的文本，跟原始 Constant 的值对不上，
            # 拿它比等于没排除——第一版就是这么让模块 docstring 漏进来的。
            docs = {id(n.body[0].value)
                    for n in ast.walk(tree)
                    if isinstance(n, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef,
                                      ast.ClassDef))
                    and n.body and isinstance(n.body[0], ast.Expr)
                    and isinstance(n.body[0].value, ast.Constant)
                    and isinstance(n.body[0].value.value, str)}
            for node in ast.walk(tree):
                if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
                    continue
                v = node.value
                if "npm run build" not in v or id(node) in docs:
                    continue
                if "npm install" not in v:
                    bad.append(f"{p.name}:{node.lineno}  {' '.join(v.split())[:70]}")
        self.assertEqual(
            sorted(set(bad)), [],
            "这些地方叫人跑构建，却漏了 npm install：\n  " + "\n  ".join(sorted(set(bad)))
            + "\n第一次用的人没装过依赖，只说 npm run build 会让他撞第二个错，"
              "而那条错不会告诉他还差一步")


class DependencyAttributionTests(unittest.TestCase):
    """依赖要说清是给哪个命令用的，否则用户不知道该不该装。"""

    def test_python_is_attributed_to_dashboard(self):
        """Python 的真实用途是 /job-dashboard（外加仓库自带检查脚本），不能只写 CI。"""
        text = (REPO_ROOT / "SETUP.md").read_text(encoding="utf-8")
        m = re.search(r"### Python\n(.{0,300})", text, re.S)
        self.assertIsNotNone(m, "SETUP.md 缺少 ### Python 一节")
        self.assertIn("dashboard", m.group(1),
                      "SETUP.md 的 Python 一节没说明它是 /job-dashboard 需要的")

    def test_dashboard_really_needs_python(self):
        """控制用例：/job-dashboard 确实调用 Python 脚本。

        **不点名具体是哪个脚本。** 原来断言的是 `tools/build_dashboard.py`，
        而这条要验的是「Python 这个依赖归 /job-dashboard 用」——实测换过两次脚本
        （build_dashboard → bundle_web → serve）它就红了，可上一条（SETUP.md 要说明
        Python 归谁用）一个字没变。
        """
        text = (REPO_ROOT / "workflows/job-dashboard.md").read_text(encoding="utf-8")
        self.assertRegex(text, r"python tools/\w+\.py",
                         "/job-dashboard 不再跑任何 Python 脚本了？"
                         "那 SETUP.md 把 Python 归给 /job-dashboard 就成了假话"
                         "（这句是转述，不是引用 —— 引用要照抄原话，"
                         "判据见 test_cross_references_resolve）")


class StubsAndWorkflowsAgreeOnWhatTheCommandIs(unittest.TestCase):
    """`.claude/commands/<名>.md` 是薄壳，标题必须和 `workflows/<名>.md` 一模一样。

    壳是**用户在命令列表里看到的那一行**，正文是 AI 真正执行的东西。两处说的不是
    同一件事时，用户按描述挑了一个命令，拿到的是另一件事。

    实测抓到一处：`/job-dashboard` 改产单文件之后，正文标题改了、壳还写着「本地静态
    单页」。16 个壳对 18 个工作流，靠人对是对不完的。
    """

    def test_titles_match(self):
        bad = []
        for stub in sorted((REPO_ROOT / ".claude" / "commands").glob("*.md")):
            wf = REPO_ROOT / "workflows" / stub.name
            if not wf.is_file():
                continue
            a = stub.read_text(encoding="utf-8").splitlines()[0].strip()
            b = wf.read_text(encoding="utf-8").splitlines()[0].strip()
            if a != b:
                bad.append(f"{stub.name}\n      壳：{a}\n      正文：{b}")
        self.assertEqual(bad, [],
                         "命令壳与工作流正文的标题对不上——"
                         "用户在列表里读到的和实际执行的不是一件事：\n  "
                         + "\n  ".join(bad))

    def test_every_stub_has_a_workflow(self):
        """壳指向不存在的正文 = 敲了就撞空。"""
        missing = [p.name for p in (REPO_ROOT / ".claude" / "commands").glob("*.md")
                   if not (REPO_ROOT / "workflows" / p.name).is_file()]
        self.assertEqual(missing, [], f"这些命令壳没有对应的工作流：{missing}")


if __name__ == "__main__":
    unittest.main()
