"""命令行工具的共同规矩——按 `tools/*.py` **枚举**检查，新工具自动纳入。

## 这次全面检查抓到的

把每个工具都敲了一遍 `--help`，没有一个是帮助：

- `export_web_data.py --help` **真的重跑了导出、重写了 data.json**
- `doctor.py --help`、`lint_skills.py --help` 照样干完活
- `serve.py --help` **起了 HTTP 服务器卡住不返回**（第一次跑这轮检查时整条命令
  卡死两分钟被 timeout 杀掉，就是它）

`--help` 干活只是表症。病根是这七个工具**根本不解析参数**——敲什么都当没看见。
而仓库里另外八个工具**是认 `--user` 的**，也就是说 `--user` 早就是本仓库的词汇：

    python tools/export_web_data.py --user bob

多人共用一份 clone 时，这条命令会**把 alice 的数据导成 bob 的面板并报成功**。
没有一个字提示 `--user` 被吞了。这正是本仓库反复在清的那个形状——**静默做错，
而且看起来像成功**。

## 顺手带出来的两个真 bug

**① `bundle_web.py` 会打出「标着 bob、装着 alice」的文件。**（历史记录；那个文件后来连同单文件面板一起删了，只剩 `serve.py` 一条路。） 它内联 `data.json`，
用户名却另去读 `.active_user`。中间切过用户，这两个就对不上——而打出来的 HTML
照样双击能开。改成从 `data.json` 自己的 `activeUser` 读。

**② `serve.py` 与导出器在同一进程里抢 `sys.argv`。** `_export_now()` 直接调
`ex.main()`；给导出器加上参数解析之后，`serve.py --port 29030` 会让导出器把
`--port` 当成自己的未知参数、当场 `SystemExit(2)`——症状是面板打不开，报的错
却跟端口毫无关系。修法：`main(argv)` 必须能显式传入。
"""

import ast
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"

#: 不是命令行入口的模块（没有 `if __name__ == "__main__"`）自动跳过，见 `cli_tools()`。


def cli_tools():
    out = []
    for p in sorted(TOOLS.glob("*.py")):
        if p.name.startswith("_"):
            continue
        if '__name__ == "__main__"' in p.read_text(encoding="utf-8"):
            out.append(p)
    return out


def run(path: Path, *args, timeout=60):
    return subprocess.run([sys.executable, str(path), *args], cwd=ROOT,
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=timeout)


class EveryToolAnswersHelp(unittest.TestCase):

    def test_help_exits_zero_and_does_not_hang(self):
        for p in cli_tools():
            with self.subTest(tool=p.name):
                try:
                    r = run(p, "--help", timeout=30)
                except subprocess.TimeoutExpired:
                    self.fail(f"{p.name} --help 卡住了——它在干活（起服务器/等输入），"
                              "而不是在说明用法")
                self.assertEqual(r.returncode, 0,
                                 f"{p.name} --help 退出码 {r.returncode}：{r.stderr[:200]}")
                self.assertIn("usage", r.stdout.lower(),
                              f"{p.name} --help 没打印用法，说明它压根没解析参数")

    def test_help_does_no_work(self):
        """`--help` 干活最狠的一例是导出器：它会**重写 data.json**。

        判据用输出长度：真正的帮助只有用法与参数说明；把整套流程跑完的会刷出
        进度、统计、「下一步：…」。一个数量级的差距，不会误判。
        """
        for p in cli_tools():
            with self.subTest(tool=p.name):
                r = run(p, "--help", timeout=30)
                self.assertLess(
                    len(r.stdout.splitlines()), 60,
                    f"{p.name} --help 输出 {len(r.stdout.splitlines())} 行——"
                    "它把活干了，不是在说明用法")


class EveryToolRejectsUnknownArgs(unittest.TestCase):
    """静默忽略打错的参数 = 你以为在操作 bob，其实在操作 alice。"""

    def test_unknown_flag_is_an_error(self):
        for p in cli_tools():
            with self.subTest(tool=p.name):
                try:
                    r = run(p, "--这个参数不存在", timeout=30)
                except subprocess.TimeoutExpired:
                    self.fail(f"{p.name} 收到未知参数后仍然跑起来了（还卡住了）")
                self.assertEqual(r.returncode, 2,
                                 f"{p.name} 把未知参数当没看见（rc={r.returncode}）——"
                                 "打错一个字母就会静默跑在错的数据上")


class PerUserToolsAcceptUser(unittest.TestCase):
    """碰每用户数据的工具必须认 `--user`，语义一致：只影响这一次，不改 `.active_user`。"""

    #: 豁免 `--user` 的工具，每条都写清为什么。写成白名单而不是黑名单——
    #: 新工具默认被要求支持 `--user`，要豁免得显式加进来并给出理由。
    NO_USER_DATA = {
        # 开发侧检查工具，不读任何人的资料
        "lint_skills.py": "检查 skill/命令 stub 与 workflows 的接线",
        "security_guards.py": "检查权限白名单与 gitignore 规则",
        # 下面两个碰用户数据，但「按用户切换」对它们没有意义
        "verify_pdf.py": "按位置参数收 PDF 路径，路径里已经带着是谁的了",
        "template_usage.py": "本来就是**跨所有用户**扫共享模板占用，限定一个人就没用了",
    }

    #: 不退出 2、而是**照常跑完并把下一步告诉你**的那几个。
    #:
    #: `doctor` 的整个存在理由就是「环境半坏时仍能跑」——
    #: `AGENTS.md` 明写着「`.active_user` 指向的目录不存在 → 引导 `/job-user`」。
    #: 对它来说 `SystemExit(2)` 才是错的：那正是它要替用户拆解的那种失败。
    #: 它自己那一支由 `test_doctor` 钉着（「--user 指定的「X」不存在。下一步：」）。
    REPORTS_INSTEAD = {"doctor.py"}

    @staticmethod
    def _reads_active_user(src: str):
        """有没有去读 `.active_user` 的内容——即 `<某个根> / ".active_user"`。"""
        return [ast.unparse(n) for n in ast.walk(ast.parse(src))
                if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Div)
                and isinstance(n.right, ast.Constant)
                and n.right.value == ".active_user"]

    def test_whitelist_entries_really_touch_no_user_data(self):
        """白名单不能随手加：豁免的前提要能验。

        第一版的判据是「源码里出现字符串 `.active_user`」，于是把
        `security_guards.py` 误判了——它那个 `.active_user` 是**gitignore
        规则表里的一条**，检查这个文件有没有被忽略，从头到尾没读过它的内容。
        """
        for name in self.NO_USER_DATA:
            if name in ("verify_pdf.py", "template_usage.py"):
                continue          # 这两个本来就碰用户数据，豁免理由不是「不碰」
            with self.subTest(tool=name):
                self.assertEqual(
                    self._reads_active_user((TOOLS / name).read_text(encoding="utf-8")),
                    [],
                    f"{name} 会去读 .active_user 的内容，却在开发侧工具的豁免里")

    def test_the_whitelist_check_can_actually_fail(self):
        """反查判据本身有效——否则上一条是在检查一个永远为真的条件。"""
        self.assertTrue(
            self._reads_active_user((TOOLS / "serve.py").read_text(encoding="utf-8")),
            "判据连 serve.py 读 .active_user 都认不出来，白名单检查是空的")

    def test_per_user_tools_declare_user_flag(self):
        for p in cli_tools():
            if p.name in self.NO_USER_DATA:
                continue
            with self.subTest(tool=p.name):
                r = run(p, "--help", timeout=30)
                self.assertIn("--user", r.stdout,
                              f"{p.name} 碰的是每用户数据却不认 --user；"
                              "仓库里另外八个工具都认，肌肉记忆会直接把它喂进来")

    def test_unknown_user_is_refused_not_silently_emptied(self):
        """给一个不存在的用户，**每一个**认 `--user` 的工具都必须报错退出。

        继续跑下去会读不到任何数据 → 当成「这个人还没开始」→ 导出一份空面板，
        而空面板和「真的还没开始」长得一模一样。

        ## 这条原来只测 `export_web_data` 一个

        规则要求全部，验只验了一个。实测 2026-08-30 跑遍全部工具：
        **5 个没照做** —— `trim_opening`（rc=0，照常往下跑，印出
        「（用户：查无此人_测试）」然后报 0 份，正是上面那句「静默当成还没开始」）、
        `stale_materials` / `outreach_header` / `score` / `name_the_exclusion`
        （rc=1，抛 Traceback）。

        根因是一个位置写反的 `or`：

            对：  _cli.pick_user(args.user or "", root=ROOT)
            错：  a.user or _cli.pick_user("", root=ROOT)

        后者在**给了 `--user` 时根本不调 `pick_user`** —— 那个名字从不被校验。
        五处同错，因为这一行是抄过去的。
        """
        for path in cli_tools():
            if path.name in set(self.NO_USER_DATA) | self.REPORTS_INSTEAD:
                continue
            with self.subTest(tool=path.name):
                r = run(path, "--user", "查无此人_测试", timeout=90)
                self.assertEqual(
                    r.returncode, 2,
                    f"{path.name} 没拒绝一个不存在的用户"
                    f"（rc={r.returncode}）：{(r.stdout + r.stderr)[-200:]}")
                self.assertIn("没有叫", r.stderr + r.stdout)

    def test_the_explicit_user_goes_through_the_resolver(self):
        """判据只有一份（`pick_user`），给了名字也要走它。

        只扫源码：上面那条真跑一遍，这条把**写法**钉死 —— 那五处是抄出来的，
        再抄一次同样看不出来。
        """
        bad = []
        for path in cli_tools():
            if path.name in self.NO_USER_DATA:
                continue
            src = path.read_text(encoding="utf-8")
            if "pick_user" not in src:
                continue
            for var in ("a.user", "args.user"):
                if var + " or _cli.pick_user(" in src:
                    bad.append(path.name + "（" + var + " or pick_user(...)）")
        self.assertEqual(
            bad, [],
            "这几处给了 --user 就绕过 pick_user，名字不会被校验："
            + "、".join(bad)
            + "。写法：把那个变量放进 pick_user 的第一个参数里，"
              "别拿它去短路掉 pick_user")

    def test_user_flag_does_not_move_the_pointer(self):
        """`--user` 是「这一次看谁」，不是「切换到谁」。改了指针会让人切走而不自知。"""
        ptr = ROOT / ".active_user"
        if not ptr.is_file():
            self.skipTest("没有活动用户")
        before = ptr.read_text(encoding="utf-8")
        others = [d.name for d in (ROOT / "users").glob("*")
                  if d.is_dir() and d.name != before.strip()]
        if not others:
            self.skipTest("只有一个用户，测不出来")
        run(TOOLS / "doctor.py", "--user", others[0], timeout=60)
        self.assertEqual(ptr.read_text(encoding="utf-8"), before,
                         "看了一眼别人的进度，.active_user 就被改掉了")


class NoArgvCrosstalkBetweenTools(unittest.TestCase):
    """serve.py 调导出器时，钉住的用户必须显式传下去。

    > **2026-08-13 更新**：serve 的导出从同进程 `ex.main([...])` 改成了**子进程**
    > （长驻服务会用启动那一刻的旧模块，把新字段覆盖回旧格式——见
    > `tests/test_export_runs_the_code_on_disk.py`）。`main(argv=...)` 的契约仍然
    > 要留着：它是导出器可被程序化调用的保证，测试与别的调用方都依赖它。
    """

    def test_export_main_takes_explicit_argv(self):
        sys.path.insert(0, str(TOOLS))
        import export_web_data as ex
        import inspect
        self.assertIn("argv", inspect.signature(ex.main).parameters,
                      "export_web_data.main() 不收 argv，只能去读 sys.argv——"
                      "程序化调用时外层的参数会被它当成自己的未知参数直接崩掉")

    def test_serve_passes_the_pinned_user_down(self):
        """验的是**规则**（用户被传下去了），不是某一种写法。

        这条原来断言源码里有 `ex.main(["--user", active_user()])` 这一行字面量。
        规则没变、实现从同进程换成子进程，它就红了——**绑死实现的守卫，
        会在一次正当重构里报假警，而在真出问题时未必说得清哪里错了**。
        改成调一次 `_export_now`、看用户到底有没有被传下去。
        """
        from unittest import mock
        sys.path.insert(0, str(TOOLS))
        import serve
        fake = mock.Mock(returncode=0, stdout="", stderr="")
        with mock.patch.object(serve.subprocess, "run", return_value=fake) as run, \
             mock.patch.object(serve, "active_user", return_value="张三"):
            serve._export_now()
        argv = [str(a) for a in run.call_args[0][0]]
        self.assertIn("--user", argv,
                      "自动重导没把钉住的用户传下去——页面会标着 bob、装着 alice")
        self.assertEqual(argv[argv.index("--user") + 1], "张三",
                         "传了 --user 但不是当前活动用户")



class AFlagWithoutHelpIsAGuess(unittest.TestCase):
    """`--help` 里没写的东西，用户只能猜 —— 最该说清的是「默认不写盘」。

    本仓库每个会写盘的工具都**默认试运行**，加 `--apply` 才真写。这是敲裸命令
    之前最要紧的一件事（`AGENTS.md` 那张索引表第四列「不给参数时」讲的也是它）。

    实测 2026-08-31：12 个带 `--apply` 的工具里，**4 个的整份 `--help` 从头到尾
    没提过这件事**——

        score.py --help
          --apply        真的写盘
          --user USER                  ← 连说明都没有

    「真的写盘」只说了加上它会怎样，没说不加会怎样。而在这个仓库里裸跑恰恰是
    **安全且推荐**的第一步。同样那 4 个（外加 `stale_materials`）的 `--user`
    是一行光杆，而另外 11 个工具**一字不差**地各写了一遍「活动用户，默认读
    .active_user」——11 份抄件加 5 处缺失，正是该有一个常量的形状
    （`_cli.HELP_USER` / `_cli.help_apply`）。

    ## 判据落在「说没说」，不是「怎么写」

    `--apply` 那一行的措辞**带信息**，不该统一掉：`fetch_details` 写「真的发
    请求」、`prescreen` 写「真的写回 seen_jobs.json」。而 `applied_jds` 把这件事
    写在别处（「不给就只报覆盖」），`audit_pipeline` 也是（「默认只报要动几个」）
    —— 两句都说清了，只是不在那一行。所以判据是**整份 `--help` 里有没有说**。

    ## 为什么真跑 `--help`，不静态扫

    第一版静态扫 AST 里的字面量。收拢成 `help=_cli.help_apply()` 之后，那几个
    文件里**再没有「试运行」这个字面**，静态扫当场把已经修好的工具报成没修
    —— 判据钉在实现形态上，收重复时它会把收拢本身判成违规。
    真跑一遍读的是用户读到的那份，本文件本来就有 `run()` 与 `cli_tools()`。
    """

    #: 说清「默认不写」的几种写法。判据认意思，不认某一版遣词。
    SAYS_DRY = ("试运行", "不给就", "默认只报")

    _CACHE: dict = {}

    def _help(self, path):
        """每个工具只跑一次 `--help`，同一份输出给下面几条用。"""
        if path.name not in self._CACHE:
            r = run(path, "--help", timeout=30)
            self._CACHE[path.name] = (r.stdout or "") + (r.stderr or "")
        return self._CACHE[path.name]

    def test_the_instrument_lights_up(self):
        """先证明它会亮：真有那么多工具带这两个开关。"""
        n_apply = sum(1 for p in cli_tools() if "--apply" in self._help(p))
        n_user = sum(1 for p in cli_tools() if "--user" in self._help(p))
        self.assertGreaterEqual(n_apply, 10, f"只看见 {n_apply} 个 --apply，扫描断了")
        self.assertGreaterEqual(n_user, 15, f"只看见 {n_user} 个 --user，扫描断了")

    def test_every_apply_tool_says_the_default_is_a_dry_run(self):
        bad = [p.name for p in cli_tools()
               if "--apply" in self._help(p)
               and not any(k in self._help(p) for k in self.SAYS_DRY)]
        self.assertEqual(
            bad, [],
            "这些工具的 --help 里没有一处说「不加 --apply 就是试运行」，"
            "用户读完不知道裸跑会不会写盘：" + repr(bad))

    def test_every_user_flag_has_help(self):
        """`--user USER` 后面空着，等于让用户猜不给它会怎样。"""
        bad = []
        for p in cli_tools():
            for ln in self._help(p).splitlines():
                t = ln.strip()
                if t.startswith("--user") and len(t.split()) < 3:
                    bad.append(p.name)
                    break
        self.assertEqual(bad, [], "这些工具的 --user 是一行光杆：" + repr(bad))


class OneHomeForTheTwoHelpSentences(unittest.TestCase):
    """两句约定各只有一份出处 —— 上一条查「说没说」，这一条查「抄没抄」。"""

    def test_the_user_help_is_not_copied(self):
        raw = '"活动用户，默认读 .active_user"'
        homes = {f.name for f in TOOLS.glob("*.py")
                 if raw in f.read_text(encoding="utf-8")}
        self.assertEqual(
            homes, {"_cli.py"},
            "`--user` 的说明又被抄了一份，正本是 `_cli.HELP_USER`：" + repr(sorted(homes)))

    def test_the_convention_half_is_not_copied(self):
        """「不加就是试运行」这半句同理。`what` 那半带信息，随工具变。"""
        raw = '"真的写盘。不加就是试运行"'
        homes = {f.name for f in TOOLS.glob("*.py")
                 if raw in f.read_text(encoding="utf-8")}
        self.assertEqual(
            homes, set(),
            "整句被写死了，正本是 `_cli.help_apply()`：" + repr(sorted(homes)))

    def test_the_three_with_their_own_wording_keep_it(self):
        """`doctor` / `serve` 的说明多一句「不会改 .active_user」—— 那是它们
        **独有的保证**（看别人的进度不该改我现在是谁），不是抄件，
        收拢时不许把它一起抹掉。"""
        for name in ("doctor.py", "serve.py"):
            with self.subTest(name):
                t = (TOOLS / name).read_text(encoding="utf-8")
                self.assertIn("不改", t.replace("不会改", "不改"),
                              name + " 的 --user 不再声明它不动 .active_user")


if __name__ == "__main__":
    unittest.main()


class ArgvIsNeverStolen(unittest.TestCase):
    """`main(argv=None)` 必须表示「没有参数」，不能表示「去读 sys.argv」。

    这条是接上 `--user` 的过程中**自己踩出来的**，一次踩了两回：

    - `serve.py --port 29030` → 导出器在同进程里被调用，把 `--port` 当成自己的
      未知参数 `SystemExit(2)`。症状是面板打不开，报的错跟端口毫无关系。
    - `pytest tests/ -q` → 直接调 `doctor.main()` 的那条测试吃到了 pytest 自己的
      命令行，报 `unrecognized arguments: tests/ -q`。

    默认值反过来设（None = 空）之后，两类都不可能再发生：库调用永远拿不到别人的
    argv，真正的入口在 `__main__` 里显式传。
    """

    ENTRY_TOOLS = ["export_web_data.py", "doctor.py", "serve.py"]

    def test_main_default_is_empty_not_sys_argv(self):
        for name in self.ENTRY_TOOLS:
            with self.subTest(tool=name):
                src = (TOOLS / name).read_text(encoding="utf-8")
                # 去掉注释再查——解释「当初为什么错」的注释里正好引用了这个写法
                code = "\n".join(ln for ln in src.splitlines()
                                 if not ln.strip().startswith("#"))
                self.assertNotIn("sys.argv[1:] if argv is None", code,
                                 f"{name} 的 main() 默认去偷 sys.argv")

    def test_entry_point_passes_argv_explicitly(self):
        for name in self.ENTRY_TOOLS:
            with self.subTest(tool=name):
                src = (TOOLS / name).read_text(encoding="utf-8")
                self.assertIn("main(sys.argv[1:])", src,
                              f"{name} 的 __main__ 没显式传 argv，命令行参数会被吞掉")

    def test_library_call_with_no_args_works_under_pytest(self):
        """这条测试**自己就在 pytest 下跑**，所以它是真验：`sys.argv` 此刻
        正是 pytest 的命令行。默认值要是错的，下面这句会当场炸。"""
        sys.path.insert(0, str(TOOLS))
        import doctor
        import io
        import contextlib
        with contextlib.redirect_stdout(io.StringIO()):
            rc = doctor.main()
        self.assertEqual(rc, 0)


class CopyableToolsStayStandalone(unittest.TestCase):
    """被测试**单独拷进临时目录**跑的脚本，不能 import 本仓库的任何模块。

    接 `--user` 时给它们加了 `import _cli`，当场 114 个测试变红——拷过去的只有
    脚本自己，`_cli.py` 不在，`ImportError` 让脚本输出空字符串，而断言看到的是
    「没打印预期的错误信息」，跟真正的原因隔着好几层。
    """

    #: 谁被单独拷走：从测试代码里**扫出来**，不手写清单——手写的会跟测试脱节。
    @staticmethod
    def copied_alone():
        import re as _re
        names = set()
        for t in (ROOT / "tests").glob("*.py"):
            for m in _re.finditer(r'shutil\.copy\(\s*(\w+)', t.read_text(encoding="utf-8")):
                src = t.read_text(encoding="utf-8")
                for mm in _re.finditer(
                        rf'{m.group(1)}\s*=\s*REPO_ROOT\s*/\s*"tools"\s*/\s*"([\w.]+)"', src):
                    names.add(mm.group(1))
        return names

    def test_scan_found_something(self):
        self.assertTrue(self.copied_alone(),
                        "扫不到任何被单独拷贝的脚本——判据失效，下一条检查是空的")

    def test_no_intra_repo_imports(self):
        local = {p.stem for p in TOOLS.glob("*.py")}
        for name in sorted(self.copied_alone()):
            with self.subTest(tool=name):
                tree = ast.parse((TOOLS / name).read_text(encoding="utf-8"))
                bad = []
                for n in ast.walk(tree):
                    if isinstance(n, ast.Import):
                        bad += [a.name for a in n.names if a.name in local]
                    elif isinstance(n, ast.ImportFrom) and n.module in local:
                        bad.append(n.module)
                self.assertEqual(bad, [],
                                 f"{name} 会被单独拷进临时目录跑，不能 import {bad}")


class FreshnessAlsoMeansItIsTheRightPersons(unittest.TestCase):
    """派生数据要验的是**两件事**：够不够新，以及**是不是这个人的**。

    只验时效会漏掉最刺眼的一种：盘上那份是别人的。冒烟实测——

        python tools/serve.py --user 李四 --port 29031
        → 端出的是**另一个用户**的一整份职位数据

    因为那份 `data.json` 比李四的上游文件新，`refresh_if_stale()` 判定「不过期」
    直接端出去。时间对、人不对，页面上没有任何异常提示。

    与 `bundle_web.py` 那个「标着 bob、装着 alice」是同一个病：**只验时效不验归属**。
    """

    def test_the_decision_itself(self):
        """真的把判定函数跑一遍，四种情形逐个验——不是「看源码里有没有那句」。"""
        import importlib
        import json
        import tempfile
        sys.path.insert(0, str(TOOLS))
        serve = importlib.import_module("serve")

        with tempfile.TemporaryDirectory() as td:
            d = Path(td) / "data.json"
            d.write_text(json.dumps({"activeUser": "甲", "jobs": []}, ensure_ascii=False),
                         encoding="utf-8")
            old = d.stat().st_mtime - 100      # 上游比它旧 = 够新鲜
            new = d.stat().st_mtime + 100      # 上游比它新 = 过期

            self.assertFalse(serve.needs_reexport(d, "甲", old),
                             "同一个人 + 上游更旧，不该重导")
            self.assertTrue(serve.needs_reexport(d, "乙", old),
                            "**这就是那个 bug**：数据是甲的、时间还很新，"
                            "于是原样端给了乙")
            self.assertTrue(serve.needs_reexport(d, "甲", new),
                            "同一个人但上游更新了，要重导")
            self.assertTrue(serve.needs_reexport(Path(td) / "没有这个文件.json", "甲", old),
                            "文件都不在，必须重导")

    def test_broken_json_reexports_instead_of_serving_it(self):
        """半截 JSON 读不出归属——那种情况下**当成要重导**，不能当成「是这个人的」。"""
        import importlib
        import tempfile
        sys.path.insert(0, str(TOOLS))
        serve = importlib.import_module("serve")
        with tempfile.TemporaryDirectory() as td:
            d = Path(td) / "data.json"
            d.write_text('{"activeUser": "甲", "jobs": [', encoding="utf-8")
            self.assertTrue(serve.needs_reexport(d, "甲", d.stat().st_mtime - 100))


class FreshCloneNeverShowsATraceback(unittest.TestCase):
    """一份全新 clone 上（`.active_user` 还没有、`users/` 是空的），
    任何工具都不许抛 Python 栈回溯。

    ## 为什么这条要紧

    这是新人看到的第一屏。而**敲错顺序是常态**——他不知道要先 `/job-setup`，随手试了
    `python tools/prescreen.py`，得到的是：

        FileNotFoundError: [Errno 2] No such file or directory: '…/.active_user'

    实测四个工具都这样：`prescreen` / `followups` / `gap_split` / `fetch_details`，
    每个都是同一行 `(ROOT / ".active_user").read_text(...)` 不判存在。
    `doctor.py` 顶上那条约束说的正是这件事：「任何失败都会让新用户在第一步就撞墙
    ——而这正是它要消除的体验」。而那条约束只管住了 doctor 自己。

    ## 判据

    在临时目录里搭一个**最小的假仓库**（有 AGENTS.md / workflows/ / tools/，
    没有 `.active_user`、`users/` 为空），逐个跑，看有没有 `Traceback`。
    """

    @staticmethod
    def _fake_repo(td: Path) -> Path:
        import shutil
        root = td / "repo"
        (root / "workflows").mkdir(parents=True)
        (root / "users").mkdir()
        (root / "AGENTS.md").write_text("# x\n", encoding="utf-8")
        shutil.copytree(TOOLS, root / "tools")
        return root

    def test_no_tool_crashes_with_a_traceback(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            root = self._fake_repo(Path(td))
            for p in cli_tools():
                with self.subTest(tool=p.name):
                    try:
                        r = subprocess.run(
                            [sys.executable, str(root / "tools" / p.name)],
                            cwd=root, capture_output=True, text=True,
                            encoding="utf-8", errors="replace", timeout=40)
                    except subprocess.TimeoutExpired:
                        # skipTest 抛 SkipTest 被 subTest 捕获，循环照常继续——
                        # 后面不需要（也到不了）return
                        self.skipTest(f"{p.name} 会长跑（起服务/抓网页），这条不适用")
                    out = (r.stdout or "") + (r.stderr or "")
                    self.assertNotIn(
                        "Traceback (most recent call last)", out,
                        f"{p.name} 在全新 clone 上抛了栈回溯，新人第一次就撞墙：\n"
                        + out[-400:])

    def test_the_message_points_at_the_next_command(self):
        """光不崩不够——还要说清下一步敲什么。"""
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            root = self._fake_repo(Path(td))
            for name in ("prescreen.py", "followups.py", "gap_split.py",
                         "fetch_details.py", "export_web_data.py"):
                with self.subTest(tool=name):
                    r = subprocess.run(
                        [sys.executable, str(root / "tools" / name)], cwd=root,
                        capture_output=True, text=True, encoding="utf-8",
                        errors="replace", timeout=40)
                    out = (r.stdout or "") + (r.stderr or "")
                    self.assertIn("/job-setup", out,
                                  f"{name} 没告诉新人下一步敲什么：{out[:200]}")

    def test_pick_user_routes_each_failure_to_the_right_command(self):
        """`pick_user` 的三条失败分支**真跑一遍** —— 上面那条只读源码。

        ## 为什么补

        上面 `test_one_implementation_of_user_resolution` 保证「解析只有一份」，
        但它 `read_text` 完就断言，**那一份从没被执行过**。
        2026-08-21 量 `tools/` 的行覆盖率：`pick_user` 的三条错误分支里
        「`.active_user` 指向的目录不存在」那一支**整套测试一次都没跑到**，
        另外两支只在子进程测试里被间接碰到。

        这一支恰恰是 `AGENTS.md` 专门立过规矩的那个：**指针坏了要引导
        `/job-user`，不是 `/job-setup`**——「那是指针坏了，`/job-setup` 修不了它」
        （它只会再建一个新用户，原来那份数据仍然找不到）。
        `doctor.py` 那一份有判据钉着（`test_doctor` 里那条），
        而**十来个 CLI 工具共用的这一份没有**。同一条规则只贴在一个写手身上。

        ## 判据

        四种情形各跑一次：没有指针 / 指针指向不存在的用户 / `--user` 指了个
        不存在的名字 / 一切正常。看的是**退出码**与**那句话把人指向哪条命令**。
        """
        import tempfile

        sys.path.insert(0, str(TOOLS))
        import _cli

        def run(root, explicit=""):
            """调一次，返回 (退出码, 印出来的话)。"""
            import contextlib
            import io as _io
            err = _io.StringIO()
            try:
                with contextlib.redirect_stderr(err):
                    return 0, _cli.pick_user(explicit, root=root), err.getvalue()
            except SystemExit as exc:
                return int(exc.code or 0), None, err.getvalue()

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)

            code, _, msg = run(root)
            self.assertEqual(code, 1, f"没有 .active_user 却不是 1：{msg!r}")
            self.assertIn("/job-setup", msg, "第一次用的人没被指向建档")
            self.assertIn("/job-user", msg, "已经有用户的人没被指向切换")

            (root / ".active_user").write_text("查无此人", encoding="utf-8")
            code, _, msg = run(root)
            self.assertEqual(code, 1, f"指针坏了却不是 1：{msg!r}")
            self.assertIn("/job-user", msg,
                          f"指针坏了没指向 /job-user：{msg!r}")
            self.assertNotIn(
                "/job-setup", msg,
                "指针坏了却把人指去 /job-setup —— 那修不了指针，"
                f"只会再建一个新用户，原来那份数据仍然找不到：{msg!r}")

            (root / "users" / "张三").mkdir(parents=True)
            (root / ".active_user").write_text("张三", encoding="utf-8")
            code, got, msg = run(root)
            self.assertEqual((code, got), (0, "张三"), msg)

            code, _, msg = run(root, explicit="李四")
            self.assertEqual(code, 2, f"--user 指了个不存在的名字却不是 2：{msg!r}")
            self.assertIn("张三", msg, "没把现有用户列出来，用户无从改对")

    def test_the_command_it_points_at_can_actually_catch_them(self):
        """**把人指过去，那条命令得接得住。**

        上面那条钉的是「指针坏了要说 `/job-user`」—— 十来个工具都照做了。
        而 2026-09-02 通读 `job-user.md` 发现：**它没有这一支。**
        「解析用户输入」只认两种状态（`users/` 为空、`.active_user` 未设），
        而「指着一个不存在的目录」两种都不是。

        于是这是一个闭环：工具印「跑 `/job-user` 看看有哪些用户」，
        用户照着敲过来，**这份文档没有一句话告诉执行者该怎么办** ——
        而 `AGENTS.md`「会话开始」那一节点名的正是这件事
        （「那是指针坏了，`/job-setup` 修不了」）。

        规则立在总纲、判据钉在工具，唯独**接活的那条命令**没写。
        本仓库反复出现的形状：一条规则只贴在一个写手身上。

        判的是「有没有这一支」，不是抄词：三样都要在 —— 认得出这个状态、
        说清指针坏了、给得出下一步。
        """
        t = (ROOT / "workflows" / "job-user.md").read_text(encoding="utf-8")
        body = "\n".join(l for l in t.splitlines()
                         if not l.lstrip().startswith(">"))
        i = body.index("## 解析用户输入")
        seg = body[i:body.index("\n## ", i + 5)]
        self.assertRegex(
            seg, r"`users/<它>/` *不存在|指向的目录不存在|指着一个不存在的目录",
            "/job-user 认不出「指针坏了」这个状态 —— 而全仓的工具都把人指过来")
        self.assertIn("指针坏了", seg, "没说清这是指针的问题")
        self.assertRegex(
            seg, r"doctor\.py|/job-setup|/job-user <",
            "认出来了却没给下一步，用户还是不知道该敲什么")

    def test_the_panel_says_the_same_thing(self):
        """**面板那条路走同一组用例。**

        上面那条把三种情形验得很细 —— 而它只管 `pick_user`。`serve.py` 另写了
        一份 `active_user()`，把「一个用户都没有」和「指针坏了」合成一句、
        `/job-setup` 排在最前面，**同一条规则在同一个仓库里被违反了，而没有
        任何测试看得见** —— 因为守卫钉的是那一个函数，不是那件事。

        这里不再拷一份判据（拷件必飘），只钉**两条路给的是同一句话**：
        上面那条验的每一个字，就自动也是面板上的字。而面板恰恰是他读到它的
        地方 —— 浏览器里那个 409 和 `serve.py` 启动时的 stderr 印的都是它。
        """
        import tempfile
        import unittest.mock

        sys.path.insert(0, str(TOOLS))
        import _cli
        import serve

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            with unittest.mock.patch.object(serve, "ROOT", root), \
                    unittest.mock.patch.object(serve, "_PINNED_USER", ""):
                for stage in ("没有指针", "指针坏了", "一切正常"):
                    if stage == "指针坏了":
                        (root / ".active_user").write_text(
                            "查无此人", encoding="utf-8")
                    elif stage == "一切正常":
                        (root / "users" / "张三").mkdir(parents=True)
                        (root / ".active_user").write_text(
                            "张三", encoding="utf-8")
                    want_user, want_msg = _cli.read_active_user(root)
                    with self.subTest(stage):
                        try:
                            got = serve.active_user()
                        except serve.NoActiveUser as exc:
                            self.assertEqual(
                                str(exc), want_msg,
                                "面板说的和命令行说的不是同一句")
                        else:
                            self.assertEqual((got, want_msg),
                                             (want_user, ""))

    def test_one_implementation_of_user_resolution(self):
        """措辞与退出码只有一份。两处各写一套必然飘，而用户看到的正是那句措辞。

        **判据是派生的，不是一张名单。** 这里原来点着四个工具的名字
        （prescreen / followups / gap_split / fetch_details），2026-08-31 实测那四个
        **早就全干净了** —— 这条守卫在盯四扇没人走的门。而名单外的 `serve.py`正
        自己读一遍指针，把两种故障合成一句「还没有你的资料 —— 先跑 /job-setup建档；
        已经建过就跑 /job-user 切过去」。**手写名单只盖得住已经想到的那几个。**

        `doctor.py` 那一份是钉住的、不是漏网的：它顶上那条契约要求不 import 任何
        仓库模块（新用户第一步撞见的不该是 ImportError），所以它必须自带一份。
        """
        import re

        reads = set()
        for f in sorted(TOOLS.glob("*.py")):
            code = "\n".join(
                ln for ln in f.read_text(encoding="utf-8").splitlines()
                if not ln.strip().startswith("#"))
            for m in re.finditer(r'"\.active_user"', code):
                if "read_text" in code[m.end():m.end() + 200]:
                    reads.add(f.name)
                    break
        self.assertEqual(
            reads, {"_cli.py", "doctor.py"},
            "读 .active_user 的不止正本与钉住的那份副本：" + repr(sorted(reads)))
        src = (TOOLS / "_cli.py").read_text(encoding="utf-8")
        self.assertEqual(src.count('ptr = base / ".active_user"'), 1,
                         "`.active_user` 的解析写了不止一份")
