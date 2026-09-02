"""`/job-reset` 把「删掉整个用户目录」当推荐做法写给用户——那 `/job-user` 就必须真能做到。

## 这个矛盾是怎么来的

`workflows/job-reset.md` 告诉用户：

    要连这些一起清掉，最干净的做法是删掉整个 `users/<你的用户名>/` 再跑 `/job-setup`
    （或用 `/job-user` 删除该用户后重建）

而 `workflows/job-user.md` 原来写的是：

    --remove <名> → 删除：……**不允许删除当前活动用户**（先 `/job-user <其他>` 切走）

`/job-user <名>` 切换时要**校验目标目录存在**。于是**只有一个用户时根本无处可切**，
那个用户永远删不掉——而单用户正是绝大多数人的情形。

用户照着 `/job-reset` 的建议做，撞上 `/job-user` 的拒绝。两份文档各自读都通顺，**放在一起
才是死路**，而当时 `/job-user` 一条测试都没有。

## 判据

跨文档一致性：只要 `reset.md` 还把 `/job-user` 删除当作出路，`user.md` 就必须
明确覆盖「删的是唯一用户 / 当前活动用户」这两种情形，而不是拒绝。
"""

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
USER_MD = ROOT / "workflows" / "job-user.md"
RESET_MD = ROOT / "workflows" / "job-reset.md"


class DeletingTheLastUserMustWork(unittest.TestCase):

    def setUp(self):
        self.user = USER_MD.read_text(encoding="utf-8")
        self.reset = RESET_MD.read_text(encoding="utf-8")

    def test_reset_still_points_at_user_deletion(self):
        """控制用例：`reset.md` 确实把这条路指给用户，否则下面几条无的放矢。

        哪天 reset.md 不再这么建议了，这条会红——那时下面的要求可以重新讨论，
        而不是留一条永远绿的断言。
        """
        self.assertIn("/job-user", self.reset,
                      "reset.md 不再提 /job-user 了？那这条测试的前提没了，一起改")
        self.assertTrue(
            "删掉整个" in self.reset or "删除该用户" in self.reset,
            "reset.md 不再建议整目录删除了？重新评估本测试")

    def test_user_md_covers_deleting_the_only_user(self):
        """必须明确处理「唯一的用户」，而不是拒绝。"""
        self.assertTrue(
            any(w in self.user for w in ("唯一的用户", "只有一个用户", "最后一个用户")),
            "user.md 没有交代「要删的是唯一一个用户」怎么办。"
            "而 /job-user <名> 切换要求目标存在，单用户时无处可切——"
            "拒绝删除等于让这个用户永远删不掉，"
            "而 reset.md 正把这条路推荐给用户。")

    def test_user_md_says_what_happens_to_the_pointer(self):
        """删完之后 `.active_user` 指向哪里，必须写明。

        不写的话，指针会悬在一个已经不存在的目录上——CLAUDE.md 把这个状态单列为
        「/job-setup 修不了、要走 /job-user」的故障，正是从这儿来的。
        """
        self.assertIn(".active_user", self.user, "user.md 没提指针")
        tail = self.user[self.user.index("--remove"):]
        self.assertTrue(
            any(w in tail for w in ("清空", "切到", "切换到", "删除该文件")),
            "user.md 没说删完用户之后 `.active_user` 怎么办——"
            "指针会悬在一个不存在的目录上")

    def test_the_confirmation_is_not_just_retyping_the_name(self):
        """确认强度要配得上破坏性。

        名字在命令里已经打过一遍，让他再打一遍等于复制粘贴。`/job-reset profile` 只清
        4 个文件，尚且要求敲一个**没打过的**词；删整个用户目录不该比它更容易。
        """
        tail = self.user[self.user.index("--remove"):]
        self.assertIn("删除 <名>", tail,
                      "删除确认没有要求一个「刚才没打过」的词——"
                      "只重复一遍用户名，复制粘贴就过了")


if __name__ == "__main__":
    unittest.main()
