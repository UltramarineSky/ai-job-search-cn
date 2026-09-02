# -*- coding: utf-8 -*-
"""点「我投了」，那一行要**立刻**从名单里走，不等写盘。

用户报了两次，是同一件事的两层：

  2026-08-13 ①「点了『我投了』前端应该马上变化，不用等数据处理，它们是不相关的」
  2026-08-13 ②「点了 我投了，它怎么没消失？」

第一次我只把**展开面板里**的内容改成了乐观更新（立刻显示「已记下」），
而**这一行还在不在名单里**是 `snap.jobs` 算出来的——写盘改了台账 mtime，
`serve.py` 下一次 `/data.json` 要重新导出整份数据，秒级。
于是用户看到：里面写着「已记下」，外面那行还杵在「可以投的岗位」里。

**半个乐观更新比没有更糟**：它让人以为记上了，又用一个没动的列表否认这件事。

「不投」那条路（`excluded`）早就是本地增量，状态按钮一直没跟上。
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP = (ROOT / "web" / "src" / "App.tsx").read_text(encoding="utf-8")
JR = (ROOT / "web" / "src" / "components" / "JobReadout.tsx").read_text(encoding="utf-8")


class TheRowLeavesImmediately(unittest.TestCase):

    @staticmethod
    def _code(body: str) -> str:
        """剥掉 `//` 注释 —— 断言只看代码。

        2026-08-21 踩到：新写的判据 `assertNotIn(".then(", body)` 撞上了
        **正文里解释这条规则的那句注释**（「压进下面的 `.then()` 里就成了
        先塌两秒后才跳」）。两边是同一次改动里写的，相隔两分钟。
        **「断言撞上解释自己的文字」在这个仓库是常客，剥注释是通解。**
        """
        return re.sub(r"//[^\n]*", "", body)

    def test_there_is_a_local_pending_set(self):
        self.assertIn("justActed", APP)

    def test_the_lists_honour_it(self):
        """两份名单都要滤掉刚点过的，只滤一份等于一半有效。"""
        n = len(re.findall(r"justActed\.has\(j\.id\)", APP))
        self.assertGreaterEqual(n, 2, f"只有 {n} 处名单认这个集合")

    def test_the_applied_view_does_not_hide_it(self):
        """在「已投递」视图里，刚点过的那个**恰恰该出现**——它就是刚投的。"""
        self.assertIn('funnel !== "applied" && justActed.has(j.id)', APP)

    def test_it_rolls_back(self):
        """写失败或撤销要把行放回来。乐观更新必须配回滚，
        否则「界面说记上了、盘上没有」比慢更糟。"""
        m = re.search(r"const afterStatus = .*?\n  \};", APP, re.S)
        self.assertIsNotNone(m, "找不到 afterStatus")
        self.assertIn("next.delete(id)", m.group(0), "没有回滚路径")

    def test_the_advance_is_immediate_too(self):
        """**第三层**：挪到下一条也不许等写盘。

        用户 2026-08-21 第三次报同一件事：「我点了我投了后，怎么很久才打开
        下一个了，不是乐观更新吗」。前两次修的是这件事的另外两层
        （面板内文案、这一行从名单消失），而**「下一条打开」还压在
        `refreshAnd` 的 `.then()` 里**。

        实测那一等有多久：平时 GET `/data.json` 0.18s；
        **记完状态后的那一次 2.13s** —— 写盘改了台账 mtime，`serve.py` 下一次
        请求要把 2600 多个岗整份重导。

        病灶的形状是「半个乐观更新」：`setJustActed` 让行立刻消失（同一次提交），
        `setSelectedId` 却在两秒后 —— **`refreshAnd` 的注释本来就写着
        「塌下去和跳过去必须同一次提交」，而这正是它自己被违反的样子。**

        判据：`afterStatus` 体内要有 `setSelectedId`，且它**不在** `.then(` 里面
        （等价写法：`refreshAnd()` 不带参数）。
        """
        m = re.search(r"const afterStatus = .*?\n  \};", APP, re.S)
        self.assertIsNotNone(m, "找不到 afterStatus")
        body = self._code(m.group(0))
        self.assertIn(
            "setSelectedId(", body,
            "afterStatus 不挪选中了 —— 那点完「我投了」就停在原地")
        self.assertNotIn(
            ".then(", body,
            "挪选中又回到了写盘之后 —— 用户会等两秒才看到下一条打开")

    def test_the_skip_path_advances_immediately_too(self):
        """「不投这个岗」是同一个形状：`setExcluded` 让行立刻消失，跳也得跟上。"""
        m = re.search(r"const exclude = .*?\n  \};", APP, re.S)
        self.assertIsNotNone(m, "找不到 exclude")
        body = self._code(m.group(0))
        i_sel = body.find("setSelectedId(")
        self.assertGreater(i_sel, -1, "exclude 不挪选中了")
        i_then = body.find(".then(")
        self.assertTrue(
            i_then == -1 or i_sel < i_then,
            "挪选中排在 .then() 之后 —— 标完「不投」要等写盘回来才跳")

    def test_the_panel_body_is_optimistic_too(self):
        """面板内部也要立刻变——两层都得是乐观的，缺一层就是「点了没反应」。"""
        m = re.search(r"async function mark\(.*?\n  \}", JR, re.S)
        self.assertIsNotNone(m, "找不到 mark()")
        body = m.group(0)
        i_set = body.index("setMarked(")
        i_await = body.index("await postStatus")
        self.assertLess(i_set, i_await,
                        "setMarked 还在 await 后面——界面又要等网络了")
        self.assertIn("setMarked(null)", body, "失败时没回滚")

    def test_the_row_and_the_advance_are_triggered_before_the_write(self):
        """**第四层**：让行走、让下一条打开的那个**触发**也不许等写盘。

        用户 2026-09-02 第四次报同一件事：「点了 我投了，怎么没乐观更新，
        还是要等几秒」。

        前三层查的都是**机制在不在**、**`afterStatus` 体内的顺序对不对**——
        三条都绿着，而 bug 是真的。**病灶在它被调用的时刻**：`justActed` 和
        `setSelectedId` 全挂在 `onChanged` 上，而 `mark()` 里 `onChanged`
        只在 `await postStatus` **之后**才调。机制齐备，扳机在后面。

        它是被上一条修复推过去的：为了不让重取抢在写盘前面（GET 会拿回旧快照），
        整个 `onChanged` 被挪到 await 之后，**该立刻做的 UI 一起被带走了**。
        一个回调捆着两件性质相反的事，就会这样按下葫芦浮起瓢 —— 现在拆成
        `"now"`（只动界面）/ `"settled"`（只重取）两拍。

        实测那一等有多久：`serve.py` 写完盘在**响应之前**同步跑导出子进程，
        单独计时 3.4–4.2 秒（注释里记的 2.13s 是数据更少那会儿的）。

        判据钉两件，都不钉措辞：
          1. `mark()` 里 `await postStatus` **之前**至少调过一次 `onChanged`；
          2. 那一次不触发重取（带 `"now"` 相位），否则又回到抢跑那个 bug。
        """
        m = re.search(r"async function mark\(.*?\n  \}", JR, re.S)
        self.assertIsNotNone(m, "找不到 mark()")
        body = self._code(m.group(0))
        i_await = body.index("await postStatus")
        before = body[:i_await]
        self.assertIn(
            "onChanged?.(", before,
            "mark() 在写盘之前一次都没叫 onChanged —— "
            "justActed / setSelectedId 全挂在它上面，"
            "于是行不走、下一条不开，要等导出跑完（实测 3.4-4.2 秒）")
        self.assertIn(
            '"now"', before,
            "写盘前那一次 onChanged 没带 \"now\" 相位 —— 它会顺带触发重取，"
            "GET 抢在写盘前面拿回旧快照，正是上一条注释里修掉的那个 bug")

    def test_the_two_phases_actually_split_the_work(self):
        """控制组：`afterStatus` 真的按相位分开，不是收了个参数不用。

        少了这条，上面那条可以靠「传个 `\"now\"` 进去、函数照样两件都做」蒙混：
        重取又回到写盘前面，而两条断言都是绿的。
        """
        m = re.search(r"const afterStatus = .*?\n  \};", APP, re.S)
        self.assertIsNotNone(m, "找不到 afterStatus")
        body = self._code(m.group(0))
        self.assertIn("phase", body, "afterStatus 根本没收相位")
        i_ret = body.find('phase === "now"')
        i_refresh = body.find("refreshAnd()")
        self.assertGreater(i_ret, -1, '没有「"now" 这一拍不重取」的出口')
        self.assertLess(i_ret, i_refresh,
                        '那个出口排在 refreshAnd() 后面 —— 等于没有')
        self.assertIn('phase !== "settled"', body,
                      '没有「"settled" 这一拍不再动界面」的判断 —— '
                      "写盘回来会把已经跳走的选中又挪一次")


if __name__ == "__main__":
    unittest.main()
