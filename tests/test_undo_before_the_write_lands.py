"""撤销必须等写盘落地——`prev: null` 有两个含义，撞在一起就是丢数据。

`tracker.set_status` 的返回里，`prev` 是改之前的状态；**新建那一行时是 `None`**。
`tracker.undo` 照这个约定办事：

    prev is None  → 这行是页面刚建的 → **删掉整行**
    prev = "applied" → 退回 applied

而面板做乐观更新时，先把 `marked` 置成 `{prev: null, …}` 占位（那一刻还不知道
改之前是什么），**撤销按钮同时就可点了**（`mark()` 明确不设 `busy`）。于是：

    一个已投的岗 → 点「约面了」 → 抢在 POST 回来之前点「撤销」
    → 送出去的是占位 null → 服务端当成「这行是我刚建的」→ 整行删除

用户以为撤回了一步，实际撤掉的是**整次投递**：投递日期、备注、原因全没了，
岗位还会回到「可以投的岗位」里，像从没投过。

窗口只有一次 POST 的时间，但两个控件挨着，代价是不可逆的。
修法是加一个 `pending`：`prev` 落地之前撤销既不可点、函数里也直接 return。

下面第一个用例**直接跑真实的 tracker**，不是复述前端逻辑——它证明这条路径确实
会删行，所以那道闸不能撤。
"""

from __future__ import annotations

import datetime
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import tracker  # noqa: E402

SRC = ROOT / "web" / "src" / "components" / "JobReadout.tsx"


class NullPrevReallyDeletesTheRow(unittest.TestCase):
    """先证明危险是真的：拿真实 tracker 跑一遍那条时序。"""

    def _fresh(self):
        return Path(tempfile.mkdtemp()) / "t.csv"

    def test_a_placeholder_undo_wipes_the_application(self):
        path = self._fresh()
        job = {"url": "https://x/1", "company": "某公司", "title": "岗"}
        today = datetime.date.today().isoformat()
        r1 = tracker.set_status(path, None, job, "applied", today)
        self.assertIsNone(r1.get("prev"), "新建行的 prev 应当是 None")
        _, rows = tracker.load(path)
        r2 = tracker.set_status(path, rows[0], job, "interview", today)
        self.assertEqual(r2.get("prev"), "applied",
                         "第二次改状态，prev 应当是改之前的真值")
        _, rows = tracker.load(path)
        tracker.undo(path, rows[0], None, today)          # 占位 null
        _, rows = tracker.load(path)
        self.assertEqual(len(rows), 0,
                         "这条断言是在**记录危险**：拿占位 null 去撤销，"
                         "服务端会删掉整行。所以前端那道 pending 闸不能撤")

    def test_the_real_prev_only_steps_back(self):
        """对照：带上真值，撤销只退一步，行还在。"""
        path = self._fresh()
        job = {"url": "https://x/2", "company": "某公司", "title": "岗"}
        today = datetime.date.today().isoformat()
        tracker.set_status(path, None, job, "applied", today)
        _, rows = tracker.load(path)
        tracker.set_status(path, rows[0], job, "interview", today)
        _, rows = tracker.load(path)
        tracker.undo(path, rows[0], "applied", today)
        _, rows = tracker.load(path)
        self.assertEqual(len(rows), 1, "带真值撤销不该删行")
        self.assertEqual(rows[0]["status"], "applied", "应当退回上一个状态")


class TheGateIsInPlace(unittest.TestCase):

    def _src(self):
        return SRC.read_text(encoding="utf-8")

    def test_the_placeholder_is_marked_pending(self):
        self.assertIn('then: "", value, pending: true', self._src(),
                      "乐观更新的占位没标 pending——撤销分不出占位和真值")

    def test_the_response_clears_pending(self):
        self.assertIn("pending: false", self._src(),
                      "响应回来没清 pending，撤销会一直点不动")

    def test_the_button_and_the_handler_both_check_it(self):
        """按钮禁用**和**函数里的 return 都要有：只禁按钮挡不住键盘触发。"""
        src = self._src()
        self.assertIn("marked.pending) return", src,
                      "undo() 里没有 pending 早退")
        self.assertRegex(src, r"disabled=\{Boolean\(busy\) \|\| Boolean\(marked\.pending\)\}",
                         "撤销按钮没有随 pending 禁用")

    def test_busy_is_still_not_set_during_mark(self):
        """别用 `busy` 去凑：那会把「不投这个岗」「职位已下线」一起禁掉，
        而它们与这次写盘无关——`mark()` 的注释专门说了不设 busy 的理由。"""
        src = self._src()
        i = src.index("async function mark(")
        body = src[i:src.index("\n  }", i)]
        self.assertNotIn("setBusy", body,
                         "mark() 里又设 busy 了——那会连带禁掉旁边两个无关按钮")


if __name__ == "__main__":
    unittest.main()
