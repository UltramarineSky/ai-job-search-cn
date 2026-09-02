# -*- coding: utf-8 -*-
"""标了「挂了」之后，那排拒绝原因点得动。

页面的做法是**重发同一个状态**、只多带一个 `reason`（不另开 `/api/reason`：
「找到这一行、校验、写盘」`set_status` 已经做对了，包括给存量 CSV 补列）。
而 `apply_status` 先跑 `tracker.can_go(now, status)`——终结态按设计没有任何后继
（`NEXT` 不给它，`test_outcome_feedback_and_stats.test_terminal_states_cannot_be_left`
钉着这条），于是 `can_go("rejected", "rejected")` 为假，**每一次点原因都被挡下来**。

失败是静默的：状态早已记上，用户只看到一行红字；而 `outcome_stats` 的拒绝原因
分布永远是空的——「这套打分准不准」少了一路输入。

修的方向**不是放宽 `can_go`**：终结态出不去这条，是 `undo` 里「无条件清空原因」
的前提。补原因根本不是状态转移——状态不变，只往当前这一行补一个字段。
"""
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import serve  # noqa: E402
import tracker as tk  # noqa: E402

JOB = {"company": "某公司", "title": "某岗位", "url": "https://example.invalid/1"}


class _Fixture:
    """把 `_job_and_row` 换成临时台账，不碰活动用户的数据。"""

    def __init__(self, path):
        self.path = path

    def __call__(self, job_id):
        _, rows = tk.load(self.path)
        return dict(JOB), self.path, (rows[0] if rows else None)


class SavingAReasonIsNotAStateTransition(unittest.TestCase):

    def setUp(self):
        self._orig = serve._job_and_row
        self._tmp = TemporaryDirectory()
        self.path = Path(self._tmp.name) / "job_search_tracker.csv"
        self.path.write_text("date,company,role,status,notes,source\n",
                             encoding="utf-8")
        serve._job_and_row = _Fixture(self.path)

    def tearDown(self):
        serve._job_and_row = self._orig
        self._tmp.cleanup()

    def _cell(self, col):
        _, rows = tk.load(self.path)
        return (rows[0].get(col) or "").strip() if rows else ""

    def test_can_go_still_refuses_to_leave_a_terminal_state(self):
        """先钉住不该动的那条：放宽 `can_go` 会拆掉 `undo` 的前提。"""
        for s in ("applied", "interview", "offer", "hired"):
            with self.subTest(s=s):
                self.assertFalse(tk.can_go("rejected", s))

    def test_a_reason_lands_on_an_already_rejected_row(self):
        self.assertTrue(serve.apply_status("x", "applied")["ok"])
        self.assertTrue(serve.apply_status("x", "rejected")["ok"])
        self.assertEqual(self._cell("status"), "rejected")
        out = serve.apply_status("x", "rejected", "salary")
        self.assertTrue(out.get("ok"), f"补原因被挡下来了：{out.get('error')}")
        self.assertEqual(self._cell("outcome_reason"), "salary",
                         "接口报成功，盘上却没有这个原因")

    def test_resending_the_same_status_without_a_reason_is_still_refused(self):
        """放行的只有「带原因的补写」这一种，不是「同状态一律放行」——
        否则终结态就有了一条自环，`undo` 那句「无条件清空」又要重新想。"""
        self.assertTrue(serve.apply_status("x", "applied")["ok"])
        self.assertTrue(serve.apply_status("x", "rejected")["ok"])
        self.assertFalse(serve.apply_status("x", "rejected").get("ok"))

    def test_it_is_not_a_backdoor_around_the_state_machine(self):
        """没投过的岗，带上原因也不能一步标成 hired。"""
        out = serve.apply_status("x", "hired", "salary")
        self.assertFalse(out.get("ok"), "带 reason 就绕过了状态机")


if __name__ == "__main__":
    unittest.main()
