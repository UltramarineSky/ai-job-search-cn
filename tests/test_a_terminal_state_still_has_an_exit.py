# -*- coding: utf-8 -*-
"""终结态没有按钮是对的，但页面上必须有一处说得出去处。

2026-08-23 撤掉了 `rejected` / `no response` 的出口按钮，理由写在
`tools/tracker.py` 的 `NEXT` 上方（两条独立理由，任一条都够）。**那次撤回
是有交换条件的**：不给按钮，就要「在页面上把去处说出来」。

而 `tracker.py` 里记的落点是错的 —— 它写「那一行现在会印一句」，实际那一行
对已结案的岗**整行不渲染**（`job.nextStep` 是 null，见 `JobReadout.tsx` 里
那段注释）。真正的落点在统计面板。名字错了一句话，代价是下一个读它的人
以为已经验过、不再去看。

这条守卫盯的不是措辞，是**交换条件还在不在**：

1. 终结态确实没有按钮（撤回本身没被悄悄反悔）；
2. 页面上有一处告诉他「这不是终局」并给出该敲的命令。

第 2 条同时受 `AGENTS.md`「每一处引导都要写出该敲的命令」管：只说「不是终局」
而不给命令，他还是不知道该敲什么。
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import tracker as tk        # noqa: E402


class ATerminalStateHasNoButton(unittest.TestCase):
    def test_the_two_terminal_states_stay_button_free(self):
        """撤回没被悄悄反悔 —— 理由见 `tracker.NEXT` 上方那两条。"""
        for st in ("rejected", "no response"):
            with self.subTest(st):
                self.assertEqual(tk.next_steps(st), [],
                                 st + " 又长出按钮了：撤它的两条理由还在")

    def test_a_live_application_still_has_them(self):
        """判据自检：不是「所有状态都没按钮」那种恒真。"""
        self.assertTrue(tk.next_steps("applied"), "等回复的岗也没按钮了？")


class ButThePageStillSaysWhereToGo(unittest.TestCase):
    #: 去处落在这里。`tracker.py` 的注释指的就是这个文件 —— 两处要一起改。
    HOME = ROOT / "web" / "src" / "components" / "OutcomeStats.tsx"

    def test_the_page_says_it_is_not_the_end(self):
        src = self.HOME.read_text(encoding="utf-8")
        self.assertIn("都不是终局", src,
                      "页面上不再说「挂了 / 没下文不是终局」——"
                      "那撤按钮的交换条件就没兑现")

    def test_it_names_the_command(self):
        """`AGENTS.md`「每一处引导都要写出该敲的命令」：只说不是终局不够。"""
        src = self.HOME.read_text(encoding="utf-8")
        self.assertIn("/job-outcome", src, "说了不是终局，没说该敲什么")

    def test_tracker_points_at_the_real_home(self):
        """注释里那个落点得是真的 —— 它错过一次，正是这条守卫的由来。"""
        note = (ROOT / "tools" / "tracker.py").read_text(encoding="utf-8")
        rel = self.HOME.relative_to(ROOT).as_posix()
        self.assertIn(rel, note,
                      "tracker.py 没指出那句话到底在哪个文件：" + rel)


if __name__ == "__main__":
    unittest.main()
