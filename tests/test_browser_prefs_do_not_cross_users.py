"""浏览器里存的偏好要按活动用户分开——否则甲的过滤器挂在乙的名单上。

多人共用一份 clone 是这个仓库明写支持的：数据在 `users/<名字>/` 下各自独立，
切换用户那个弹窗里就印着「每个人的资料、职位、投递记录都各自独立」。

**而浏览器里那两份原来是全局一把键**：

    jobSearchHidden.v1     不想看的公司、职位、列
    jobSearchExcluded.v2   静态模式下「不投」的增量（按岗位 id 存）

切用户走的是「命令行改 + 刷新页面」，刷新之后这两份原样还在。于是甲把某家公司
加进屏蔽词、切成乙，**乙的名单里那些岗静默少掉**——他不会知道少了什么，
更不会想到是别人的过滤器还挂着。排除增量更糟：它按岗位 id 存，而同一个岗被两个人
抓到时 id 相同，甲标的「不投」会直接盖在乙的名单上。

这两份都不写盘、不改任何岗的状态，但它们**藏东西**。这个仓库对「静默吞掉」
一贯的判据是：宁可多显示一条，不可让人不知道自己没看见。

升级兼容：用户名为空（快照还没到）时用不带后缀的旧键，存量偏好不会凭空消失。
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "web" / "src"


def _src(rel: str) -> str:
    return (SRC / rel).read_text(encoding="utf-8")


class BothStoresAreScoped(unittest.TestCase):

    def test_one_helper_builds_the_key(self):
        h = _src("data/hidden.ts")
        self.assertIn("export function userKey(", h, "按用户取键的正本不在")
        self.assertIn('`${base}:${user}`', h, "键里没带用户名")
        self.assertIn("return user ? ", h,
                      "空用户名没有退回旧键——升级当天存量偏好会凭空消失")

    def test_both_modules_go_through_it(self):
        for rel in ("data/hidden.ts", "data/excluded.ts"):
            with self.subTest(rel):
                src = _src(rel)
                self.assertIn("userKey(KEY, user)", src,
                              f"{rel} 还在用全局键——两个人的偏好会串")

    def test_no_bare_key_reads_remain(self):
        """`getItem(KEY)` 只许作为**退回旧键**出现，不许还是主路径。"""
        for rel in ("data/hidden.ts", "data/excluded.ts"):
            with self.subTest(rel):
                src = _src(rel)
                for m in re.finditer(r"localStorage\.setItem\((\w+)", src):
                    self.assertNotEqual(
                        m.group(1), "KEY",
                        f"{rel} 还在往全局键里写——读分了键、写没分，"
                        "下次读回来的仍是共用那份")


class AppReadsThemAfterTheUserIsKnown(unittest.TestCase):

    def test_initial_state_is_empty_not_a_read(self):
        """在 useState 初值里读 = 读到上一个用户那份（那一刻 activeUser 还是空）。"""
        app = _src("App.tsx")
        self.assertIn("useState(EMPTY_HIDDEN)", app,
                      "初值又回去直接读 localStorage 了——那一刻还不知道是谁在用")
        self.assertNotIn("useState(loadHidden)", app)

    def test_the_effect_keys_on_active_user(self):
        app = _src("App.tsx")
        self.assertRegex(
            app, r"if \(activeUser\) setHidden\(loadHidden\(activeUser\)\);",
            "没有跟着 activeUser 换偏好")
        self.assertIn("}, [activeUser]);", app, "effect 的依赖不是 activeUser")

    def test_every_write_carries_the_user(self):
        app = _src("App.tsx")
        for call in ("saveHidden(p, activeUser)",
                     "saveDelta(deltaFrom(onDisk, next), activeUser)",
                     "loadDelta(activeUser)"):
            with self.subTest(call):
                self.assertIn(call, app, f"{call} 没带用户名")


class TheClaimInThePopupHolds(unittest.TestCase):
    """弹窗里印着「各自独立」——那句话现在必须是真的。"""

    def test_the_promise_is_still_on_screen(self):
        app = _src("App.tsx")
        self.assertIn("每个人的资料、职位、投递记录都各自独立", app,
                      "承诺没了就该连同这条守卫一起删——但别让承诺留着而实现走掉")


if __name__ == "__main__":
    unittest.main()
