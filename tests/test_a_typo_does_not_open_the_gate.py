# -*- coding: utf-8 -*-
"""渠道名打错一个字，风控闸门就放行。

`portal_budget.py --check <渠道>` 是抓取前那道闸门：退出码 1 = 这条停着别动，
0 = 可以抓。而 `lane_of` 对认不出的名字一律退回 `"browser"`，于是 `check()`
把它当成一条从没动过的通道 —— 没冷却、没间隔。

实测 2026-09-01（猎聘 CLI 正封着 112 小时）：

    --check liepin-search    停手：… 已经封了 112 小时     退出码 1
    --check lieping-search   可以：lieping-search 今天已发 0 次，还没动过   退出码 0
    --check LIEPIN-SEARCH    可以：…                       退出码 0
    --check 查无此渠道        可以：…                       退出码 0

**多一个字母就把硬停变成放行**，而这道闸门护的是用户自己的账号：照它抓下去，
限流会升级成账号风控（`job-scrape.md` 那段实测：限流 → 账号标记异常（要短信
验证）→ IP 被拦截）。

名字给错在这条命令上**有先例**：`job-scrape.md` 记着执行者敲过 `--round liepin`。
那次是往「当成整家没戏」的方向错（少抓），这次是往**放行**的方向错（乱抓）——
后者更贵。

## 退出码为什么是 2

1 是「这条通道停着，别动」，执行者照它跳过这一条继续跑别的；名字打错要的是
**停下改命令**。两件事共用一个码，等于把「你打错了」说成「这条今天不跑」。
"""
import os
import pathlib
import subprocess
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import portal_budget as pb  # noqa: E402


#: 这份测试自己的用户 —— **绝不碰活动用户的账本**。
#:
#: ⚠️ 第一版没有它：`run("--block", …)` / `run("--clear", …)` 不带 `--user`，
#: 走的就是活动用户那份 `portal_budget.json`。平时被那道拦截挡下所以看不出来，
#: 而**变异实测把拦截去掉的那一刻它就真写了**：2026-09-01 06:59，活动用户的
#: 账本里多出一个叫 `lieping-search` 的假渠道（带 actions 和 block_log）。
#:
#: 一条为「别让错字放行」立的守卫，自己把错字写进了用户的数据。
#: 拿真账本当夹具，代价就是这个。
PROBE_USER = "探针用户_渠道名"


def setUpModule():
    (ROOT / "users" / PROBE_USER / "job_scraper").mkdir(parents=True,
                                                        exist_ok=True)


def tearDownModule():
    import shutil
    shutil.rmtree(ROOT / "users" / PROBE_USER, ignore_errors=True)


def run(*args):
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "portal_budget.py"),
                        *args, "--user", PROBE_USER],
                       cwd=ROOT, capture_output=True, text=True,
                       encoding="utf-8", errors="replace",
                       env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
    return r.returncode, (r.stdout or "") + (r.stderr or "")


class AnUnknownNameIsRefused(unittest.TestCase):

    #: 都不是真名：差一个字母的、大小写不同的、整个瞎编的。
    TYPOS = ("lieping-search", "LIEPIN-SEARCH", "查无此渠道", "liepin_search")

    def test_the_judge_itself_knows_the_real_ones(self):
        """**先证明它认得真名。** 全判不认识的话，下面几条永远绿。"""
        for good in ("liepin-search", "liepin-browser", "boss-browser",
                     "zhaopin-browser", "51job-browser", "BOSS", "猎聘"):
            with self.subTest(good=good):
                self.assertTrue(pb.known_channel(good), f"{good} 是真名")

    def test_a_typo_is_not_a_channel(self):
        for bad in self.TYPOS:
            with self.subTest(bad=bad):
                self.assertFalse(pb.known_channel(bad))

    def test_an_empty_name_is_not_a_channel(self):
        self.assertFalse(pb.known_channel(""))
        self.assertFalse(pb.known_channel("   "))

    def test_check_does_not_wave_a_typo_through(self):
        """这就是那一下：多一个字母，硬停变成放行。"""
        code, out = run("--check", "lieping-search")
        self.assertNotEqual(code, 0, f"打错名字还放行了：{out[:120]}")
        self.assertNotIn("可以：", out, "它还给这个不存在的渠道报了「可以」")

    def test_it_is_told_apart_from_a_real_block(self):
        """码 2 ≠ 码 1：一个是「你打错了」，一个是「这条停着」。"""
        typo, _ = run("--check", "lieping-search")
        self.assertEqual(typo, 2)
        # 真名那条此刻是停是通取决于数据，但**一定不是 2**。
        real, _ = run("--check", "liepin-search")
        self.assertIn(real, (0, 1), "真渠道被当成名字打错了")

    def test_it_says_which_names_are_real(self):
        """光说「不认识」不够 —— 他得知道该敲什么（`AGENTS.md` 那条）。"""
        _code, out = run("--check", "查无此渠道")
        self.assertIn("liepin-search", out)
        self.assertIn("--round", out, "没告诉他怎么拿到这一轮该跑的那几条")

    def test_the_writing_flags_refuse_it_too(self):
        """`--block` / `--clear` / `--note` 打错名字更贵：

        `--block` 会给一条不存在的通道记冷却，而真出事的那条照旧开着；
        `--clear` 会说「解开了」，而真封着的那条还封着。两种都是静默的。
        """
        for flag in ("--block", "--clear", "--note"):
            with self.subTest(flag=flag):
                code, out = run(flag, "lieping-search")
                self.assertEqual(code, 2, f"{flag} 收下了一个不存在的渠道")
                self.assertIn("什么也没做", out)


class TheRealChannelsStillWork(unittest.TestCase):
    """反向支点：别为了挡住错字把对的也挡了。"""

    def test_every_name_the_round_prints_is_accepted(self):
        """`--round` 印出来的名字，执行者会原样拿去 `--check` —— 必须认。"""
        code, out = run("--round")
        self.assertEqual(code, 0, out[:200])
        names = [ln.split()[1] for ln in out.splitlines()
                 if ln.strip().startswith(("✓", "✗"))]
        self.assertGreaterEqual(len(names), 4, f"只解析出 {names}")
        for n in names:
            with self.subTest(n=n):
                self.assertTrue(pb.known_channel(n),
                                f"--round 印了 {n}，而 --check 不认它")

    def test_the_table_in_the_workflow_uses_real_names(self):
        """`job-scrape.md` 那张表第 4 列是「`--check` 用的名字」—— 逐个验。"""
        md = (ROOT / "workflows" / "job-scrape.md").read_text(encoding="utf-8")
        i = md.index("`--check` 用的名字")
        rows = [ln for ln in md[i:i + 1200].splitlines()
                if ln.startswith("|") and "`" in ln]
        got = []
        for ln in rows:
            cells = [c.strip().strip("`*") for c in ln.split("|")]
            if len(cells) > 4 and cells[4]:
                got.append(cells[4])
        self.assertGreaterEqual(len(got), 4, f"只解析出 {got}")
        for n in got:
            with self.subTest(n=n):
                self.assertTrue(pb.known_channel(n),
                                f"表里写着用 {n}，而 --check 不认它")


class BothWaysToUnblockAgree(unittest.TestCase):
    """解封有两个入口：命令行 `--clear` 和面板上那个按钮。名字认不认得，
    两边得是同一条判据。

    2026-09-01 给命令行加上「认不出的名字退出码 2」之后，面板那条还留着老行为：
    `clear()` 对认不出的名字返回 `was=False`，于是它回一句
    「XX 的浏览器现在没有被封，不用解」—— 把「查无此渠道」说成「没封」，
    而用户刚过完短信验证的那条还封着，他会以为自己点错了按钮。

    **同一件事两个入口，那道不对称是加固命令行时自己造出来的。**
    """

    def _panel(self, name):
        """面板那条也按到探针用户上 —— 它内部走 `active_user()`，改不了参数。"""
        import unittest.mock as _m
        import serve
        with _m.patch.object(serve, "active_user", lambda: PROBE_USER):
            return serve.apply_unblock(name)

    def test_the_panel_refuses_an_unknown_name(self):
        import serve
        for bad in ("查无此渠道", "lieping-search", ""):
            with self.subTest(bad=bad):
                got = serve.apply_unblock(bad)
                self.assertFalse(got.get("ok"))
                self.assertIn("没有叫", got.get("error", ""))

    def test_it_does_not_call_it_unblocked(self):
        """「没有这条渠道」和「这条没被封」是两回事，别说成一回事。"""
        got = self._panel("查无此渠道")
        self.assertNotIn("没有被封", got.get("error", ""))

    def test_both_entry_points_ask_the_same_judge(self):
        """判据只有一份 —— 两边对同一批名字要给同一个答案。

        钉行为，不钉 `serve.py` 里那一行长什么样（第一版钉的是源码里
        `known_channel(name)`，被 `test_a_guard_pins_behaviour_not_a_line`
        拦下）：同一组名字，命令行认不认、面板认不认，逐个对上。
        """
        # ⚠️ **空串不在这张单子上。** 命令行那边 `--check ""` 是假值，
        # 等同于「这面旗子没给」—— 它印整张额度表，那是另一个意思，
        # 不是「这个名字不认识」。面板那边永远带着一个 name 字段，空的
        # 就是请求坏了。两边此处本来就不是同一件事（第一版把它算进去，
        # 红的是我的前提不是代码）。
        for name in ("liepin-search", "liepin-browser", "BOSS", "猎聘",
                     "lieping-search", "查无此渠道", "liepin_search"):
            with self.subTest(name=name):
                cli_ok = run("--check", name)[0] != 2
                panel_ok = "没有叫" not in (
                    self._panel(name).get("error") or "")
                self.assertEqual(cli_ok, panel_ok,
                                 f"「{name}」命令行认={cli_ok}、面板认={panel_ok}")


if __name__ == "__main__":
    unittest.main()
