# -*- coding: utf-8 -*-
"""读「这台机器上的真实数据」的判据，没有真实数据时该 skip，不该红。

## 为什么要它

干净 clone —— 别人 clone 下来的样子，也是 CI `python-tests` job 的样子 ——
里面**没有** `users/`、没有 `.active_user`。那不是坏了，那是**还没跑
`/job-setup` 的正常状态**。

而 `_cli.pick_user()` 在那种状态下 `SystemExit(1)`。**那是它对用户的正确行为**
（CLI 就该说清「先跑 `/job-setup`」再退出，不该抛个栈回溯），所以要改的不是它，
是不加判断就调它的那些判据。

`SystemExit` 继承 `BaseException` 而不是 `Exception`，`except Exception` 接不住 ——
这个仓库在 `serve.py` 上为同一件事栽过一次（写入端点以「连接被关」的形式失败）。

## 实测代价（2026-09-02，发布前的干净 clone 实测）

**30 个文件、85 条红**，其中 60 条是这一个 `SystemExit`。本机全绿，
只有**别人**会红 —— 而「别人」的第一个就是首次 CI。

上一次跑这一遍是 2026-08-21（`Ran 1823, OK`）。此后套件从 1823 长到 7309，
新加的判据都写在一台永远有活动用户的机器上，没人再跑过那一遍。
**这就是「本机全绿证明不了别人拿到的东西能用」的样子。**

## 用法

    from _live import user_or_skip
    user = user_or_skip()

**不用传 `self`。** 它直接抛 `unittest.SkipTest`，而 `test.skipTest()` 抛的也是
同一个东西 —— 少一个参数，模块级的辅助函数（`def live():` 这种，作用域里没有
`self`）就能用同一种写法，不必为它另开一支。

抛的是异常，所以它下面的代码不会跑，不必再写 if。
"""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools"))


def active_user_name():
    """`.active_user` 里那个名字；没有就返回 None。**不碰 `pick_user`。**

    有些判据只想知道「这台机器上有没有人」，不需要走 CLI 那条会退出的路。
    """
    p = ROOT / ".active_user"
    if not p.is_file():
        return None
    name = p.read_text(encoding="utf-8").strip()
    return name or None


#: skip 时说的那句话。**只有一份** —— 三十来处判据引它，各写各的迟早分叉，
#: 而分叉的下场是有人看到「没有活动用户」、有人看到别的，谁也不知道是同一件事。
NO_USER = "没有活动用户 —— 干净 clone / CI 上是常态，不是故障"


def user_or_skip(test=None):
    """活动用户名；拿不到就 skip 掉这条判据。

    `pick_user` 除了「没有活动用户」还会为别的原因退出（比如名字指向的目录
    不存在）。**一律 skip，不区分** —— 这个辅助只服务一件事：
    「这台机器上没有真实数据可读」。真要区分退出原因，那是另一条判据的事。

    `test` 收下但不用，只为让 `user_or_skip(self)` 这种写法也读得通。
    """
    import _cli
    try:
        return _cli.pick_user("", root=ROOT)
    except SystemExit:
        raise unittest.SkipTest(NO_USER) from None


def user_root_or_skip(test=None):
    """`users/<活动用户>/`；没有活动用户或目录不在就 skip。"""
    name = active_user_name()
    if not name:
        raise unittest.SkipTest(NO_USER)
    root = ROOT / "users" / name
    if not root.is_dir():
        raise unittest.SkipTest(f"`.active_user` 指向 {name!r}，而那个目录不在")
    return root


def live_store_or_skip(test=None):
    """(user, seen, details) —— 活动用户的职位库。没有就 skip。

    包住 `audit_pipeline.load()`：它内部自己去 `pick_user`，所以在没有活动
    用户时同样 `SystemExit`，而调用方看到的只是「load 炸了」。
    """
    import audit_pipeline as ap
    user = user_or_skip()
    try:
        seen, details = ap.load(user)
    except SystemExit:
        raise unittest.SkipTest("读不到这个用户的职位库") from None
    return user, seen, details


#: 面板快照。**它不按用户分** —— 谁跑 `export_web_data` 都写这一份。
PANEL_SNAPSHOT = ROOT / "web" / "public" / "data.json"


def keep_panel_snapshot():
    """真跑一次工具之前调它，返回「跑完还原」的那个函数。

        _restore = keep_panel_snapshot()      # setUpModule
        _restore()                            # tearDownModule

    ## 为什么要有它

    `export_web_data` 不管传哪个 `--user` 都写同一份 `web/public/data.json`。
    拿探针用户跑一遍，那份快照就变成「1 个岗、`isRealData: true`」——
    后面所有读真实快照的判据集体失真。

    **两种机器要分开处理，而这正是原来漏掉的那一半：**

    - 本机原来**有**快照 → 跑完写回去。原来两个模块都做对了这一半。
    - 干净 clone 原来**没有** → 跑完要**删掉**。原来两个模块都漏了这一半，
      于是探针那份假快照留在盘上。一次跑不出问题（写它的模块按字母序在
      `o`/`t`，读的那些在前面，当轮已跑完），代价在**第二次跑**：
      同一个 clone 再跑一遍，那几条读到的是探针数据而不是「没有快照 → skip」。

    实测 2026-09-03：同一份干净 clone，第一遍 `Ran 7340, OK (skipped=406)`，
    第二遍 `FAILED (failures=8, errors=12)`。先只修了
    `test_one_bad_row_does_not_crash_everything` 那一份，第二遍变成
    `failures=6, errors=12` —— **另一份（`test_the_file_he_saved_in_excel`）
    照样漏**。所以收在这里，不在两个模块里各写一遍。

    `web/public/` 是 gitignore 的，所以「本来没有」和「留下一个假的」
    在 `git status` 里长得一模一样，只有再跑一遍才看得见。
    """
    saved = PANEL_SNAPSHOT.read_bytes() if PANEL_SNAPSHOT.is_file() else None

    def restore():
        if saved is None:
            PANEL_SNAPSHOT.unlink(missing_ok=True)
        else:
            PANEL_SNAPSHOT.write_bytes(saved)

    return restore


class LiveDataTestCase(unittest.TestCase):
    """要读真实数据的判据可以继承它，`self.user` 自动就绪或整类 skip。"""

    @classmethod
    def setUpClass(cls):
        name = active_user_name()
        if not name or not (ROOT / "users" / name).is_dir():
            raise unittest.SkipTest(
                "没有活动用户 —— 干净 clone / CI 上是常态，不是故障")
        cls.user = name
