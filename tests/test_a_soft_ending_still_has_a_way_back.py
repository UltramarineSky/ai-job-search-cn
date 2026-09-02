# -*- coding: utf-8 -*-
"""点完「没下文」，那一行就没有出口了 —— 而这个状态是按天数判的，不是雇主说的。

面板在投后四格下面已经有一句：

> 「大概率没戏」是按投递日期算的：投出去超过 10 天还没任何动静就归到这里，
> 不用你去点。真确认没了想结案，展开那个岗点「没下文」。

**它只说了进去的路。** 点完之后那一行没有按钮（`tracker.NEXT` 里
`rejected` / `no response` 没有出口，那是有意的），也没有一句话说后来真有动静
该去哪儿 —— 而这两条复活路径在国内都真实：拒信多是同一天群发的模板，
隔几天某个岗位重启或另一个部门单独捞人；沉默几周后 HR 回信也常见。
实测活动用户 2026-08-23：85 笔投递里 **76 笔**够那条 10 天线，
上面那句一路在劝他点它。

## 试过两种更重的改法，都撤回了

1. **给 `rejected` / `no response` 加一个「又约面了」按钮。** 撤回，两条理由：
   拒信后来邀约有三种读法（同一条线 / 两次不同投递 / 看不清），
   `job-outcome.md` Step 2 自己写着**「别替他判第一种」**，而按钮会把它塌成第一种；
   另外 `undo` 撤销时无条件清空 `outcome_reason`，那之所以安全全靠
   「终结态出不去」这条前提（`test_terminal_states_cannot_be_left` 的 docstring
   早就点名了它）。
2. **逐行给这些岗一条「下一步」。** 撤回：他有 76 行会走到这个状态，
   逐行加就是几十条一模一样的话 —— 那正是
   `test_closed_cases_have_no_next_step`（「硬凑一条会让人做无用功」）防的东西。

留下的是最轻的那种：**在四格下面多说一句，只说一次。**
"""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tests"))
import build_dashboard as B  # noqa: E402
from _srcscan import strip_comments  # noqa: E402
import tracker as tk  # noqa: E402


def _step(status):
    return B.job_next_step({"applied": {"status": status}, "company": "示例科技"})


OS_TSX = (ROOT / "web" / "src" / "components"
          / "OutcomeStats.tsx").read_text(encoding="utf-8")


class ThePanelSaysItOnce(unittest.TestCase):
    def test_the_note_exists(self):
        self.assertIn("「挂了」和「没下文」都不是终局", OS_TSX,
                      "四格下面仍然只说了进去的路")

    def test_it_names_what_would_bring_it_back(self):
        """「有动静就回来」太虚。要说出那几种真会发生的事。

        **先把 JSX 的字符串拼接拉平再比。** 那句话在源码里是
        `"…别的部门" + "捞人…"` 两段（渲染出来没问题，中文之间不会插空格），
        跨拼接点的断言会落空 —— 第一版就栽在这儿。"""
        # 去掉所有空白（含换行）再抹掉 `"+"`，拼接点就没了。
        flat = "".join(OS_TSX.split()).replace('"+"', "")
        for w in ("拒信常是群发的", "岗位重启", "别的部门捞人", "隔很久回信"):
            with self.subTest(w=w):
                self.assertIn(w, flat)

    def test_it_carries_the_command(self):
        """`AGENTS.md`：面板每处引导都要写出命令。"""
        i = OS_TSX.index("「挂了」和「没下文」都不是终局")
        self.assertIn("/job-outcome", OS_TSX[i:i + 400])

    def test_it_does_not_promise_the_row_will_change(self):
        """三种读法里有两种**不改这一行**。"""
        i = OS_TSX.index("「挂了」和「没下文」都不是终局")
        seg = OS_TSX[i:i + 500]
        self.assertIn("先问清是不是同一次投递", seg)
        self.assertIn("再决定改不改那一行", seg)

    def test_the_half_it_completes_is_still_there(self):
        """它补的是既有那句的另一半。那句没了，这句就没有对象。"""
        self.assertIn("真确认没了想结案", OS_TSX)

    def test_the_two_reverted_attempts_are_recorded(self):
        """不写下来，下一轮会再试一次同样的两种改法。"""
        i = OS_TSX.index("上面那句只说了进去的路")
        seg = " ".join(OS_TSX[i:i + 1400].split())
        self.assertIn("只在这里说一次，不逐行说", seg)
        self.assertRegex(seg, r"硬凑一条下一步让人做无用功")
        self.assertRegex(seg, r"别替他判第一种")


class NoPerRowNextStep(unittest.TestCase):
    """逐行加会长出几十条一样的话 —— 既有守卫说的「硬凑一条让人做无用功」。"""

    def test_a_soft_ending_has_no_per_row_step(self):
        for st in ("rejected", "no response"):
            with self.subTest(st=st):
                self.assertIsNone(
                    B.job_next_step({"company": "示例科技",
                                     "applied": {"status": st}}))

    def test_a_hard_ending_has_none_either(self):
        for st in ("hired", "offer declined", "withdrawn"):
            with self.subTest(st=st):
                self.assertIsNone(
                    B.job_next_step({"company": "示例科技",
                                     "applied": {"status": st}}))

    def test_an_open_application_still_gets_one(self):
        """别把整条分支关掉 —— 还在跑的岗仍然要有下一步，而且要指对地方。

        **只验非空不够**：关掉 `interview` 那一支之后，它会落到下面的通用分支
        （「投完了在等」）照样返回非空 —— 变异实测就是这么绿的。
        验它真的指向备面。"""
        step = B.job_next_step({"company": "示例科技",
                                "applied": {"status": "interview"}})
        self.assertIsNotNone(step)
        self.assertEqual(step["command"], "/job-interview 示例科技")


class TheButtonStaysOff(unittest.TestCase):
    """页面画什么按钮由 `tracker.NEXT` 说了算。这一条盯着别有人（包括下一轮的我）
    绕过上面那两条理由又把它加回去。"""

    def test_no_button_on_a_soft_ending(self):
        for s in ("rejected", "no response"):
            with self.subTest(s=s):
                self.assertEqual(tk.next_steps(s), [])

    def test_the_server_would_refuse_it_too(self):
        """页面画什么和服务端放什么过，是同一张表 —— 别只关一边。"""
        for s in ("rejected", "no response"):
            with self.subTest(s=s):
                self.assertFalse(tk.can_go(s, "interview"))

    def test_the_undo_invariant_it_protects_is_still_stated(self):
        """撤销时无条件清空 `outcome_reason`，靠的就是「终结态出不去」。"""
        src = (ROOT / "tools" / "tracker.py").read_text(encoding="utf-8")
        i = src.index("def undo(")
        seg = " ".join(src[i:i + 1800].split())
        self.assertIn("无条件清空是安全的", seg)
        self.assertRegex(seg, r"终结态的可达集是空的")

    def test_the_judgement_it_defers_to_still_exists(self):
        """指过去的那一步得真的会问。它没了，这里就成了踢皮球。"""
        out = (ROOT / "workflows" / "job-outcome.md").read_text(encoding="utf-8")
        self.assertIn("别替他判第一种", out)
        self.assertIn("不是同一次投递", out)


if __name__ == "__main__":
    unittest.main()
