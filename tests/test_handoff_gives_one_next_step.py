"""`/job-setup` 结束时只给一条「下一步」，不摆一个命令菜单。

## 规矩是仓库自己立的

`tools/doctor.py` 顶上的设计约束第 4 条：

    最后一定要给出「下一步做什么」，且**只给一条**。给三条并列选项等于没给。

doctor 严格照做（它整份输出的最后就是一条命令）。但 `/job-setup` 的 Step 4——
**新用户第一条命令的最后一屏**——原来摆的是：

    **Try it out:**
    - Run `/job-scrape` to search for matching jobs right now
    - Run `/job-apply` with a job posting URL to see the full application workflow
    - Run `/job-setup --section search` later to update your search queries

三条并列。刚建完资料的人本来就不知道该干嘛，给三个选项等于让他自己排序，
而正确答案只有一个（先 `/job-scrape`，没有职位数据后面全是空的）。

顺带一提，那第二条还把 `/job-apply` 说成「see the full application workflow」——
它可不是演示，它会真的写文件、出 PDF、生成要发给雇主的话术。

## 判据

Step 4 的交接里，**唯一那条命令必须放在围栏代码块里**（和 doctor 的格式一致：
命令单独成块，一眼能抄），且块里只有一条命令。别的命令可以在正文里提，
但不能和它并列成「你挑一个」。
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SETUP = ROOT / "workflows" / "job-setup.md"
DOCTOR = ROOT / "tools" / "doctor.py"

#: 命令行。`[\s>]*` 里的 `>` 不能少——交接那段整个在引用块里，围栏内每一行都带
#: `> ` 前缀。第一版写的是 `^\s*`，于是连基线都是红的，而我还照着跑了两次变异验证：
#: 两次都「变红」了，但红的是同一条既有失败，不是被变异触发的。
#: **基线不绿，变异验证不成立**——先看基线，再谈变异。
CMD = re.compile(r"^[\s>]*(/[a-z][a-z-]*)", re.M)


class OneNextStepNotAMenu(unittest.TestCase):

    def setUp(self):
        text = SETUP.read_text(encoding="utf-8")
        self.step4 = text.split("## Step 4：")[1].split("\n## ")[0]

    def test_the_rule_is_still_written_down(self):
        """控制用例：doctor 里那条约束还在，否则本测试没有依据。

        哪天那条规矩被撤了，这条会红——那时该重新讨论，而不是留一条无源之水。
        """
        d = DOCTOR.read_text(encoding="utf-8")
        self.assertIn(
            "只给一条", d,
            "doctor.py 顶上「下一步只给一条」的约束不见了——本测试的依据没了")

    def test_the_handoff_has_a_fenced_command_block(self):
        fences = re.findall(r"```[a-z]*\n(.*?)```", self.step4, re.S)
        self.assertTrue(
            fences,
            "Step 4 的交接里没有围栏命令块。新用户刚建完资料，"
            "下一步该敲什么必须一眼能抄走——doctor 就是这么排的。")
        cmds = [c for f in fences for c in CMD.findall(f)]
        self.assertEqual(
            len(cmds), 1,
            f"围栏块里有 {len(cmds)} 条命令：{cmds}。"
            "\n「下一步」只给一条——给三条并列选项等于没给"
            "（tools/doctor.py 的设计约束第 4 条）。"
            "\n次要建议写进正文即可，别和它并列成「你挑一个」。")

    def test_it_does_not_call_apply_a_demo(self):
        """`/job-apply` 不是演示——它真的写文件、出 PDF、生成要发给雇主的话术。"""
        for bad in ("see the full application workflow", "试一下 /job-apply", "体验一下"):
            self.assertNotIn(
                bad, self.step4,
                f"Step 4 把 /job-apply 说成了演示（「{bad}」）——"
                "它会真的落盘并产出要投出去的材料")


    def test_the_design_principles_do_not_contradict_step_4(self):
        """设计原则那一节不能还写着「顺便拿 `/job-apply` 试一个职位」。

        Step 4 改成只给一条之后，文末「Design Principles」的最后一行仍写着：

            At the end, suggest running `/job-scrape` and `/job-apply` with a test job posting.

        **同一份文件里的第二处**，而且它是给执行者看的总纲——执行者照总纲办，
        Step 4 的修改就白改了。上面那几条只看 Step 4 的围栏块，看不见这里。
        """
        text = SETUP.read_text(encoding="utf-8")
        i = text.find("## 设计原则")
        self.assertGreater(i, 0, "setup.md 里找不到「设计原则」一节了")
        block = text[i:]
        # 中英两种说法都要挡。第一版只查中文「试」，而原文正是英文
        # `with a test job posting` —— 变异验证当场证明它对英文形式空转。
        # 这个仓库里「同一个概念换种语言就绕过守卫」已经出现过两次
        # （另一次是废弃的「五维」写成 five-dimension）。
        TRY = ("试", "test job", "try ", "demo", "see the full")
        bad = [l.strip()[:80] for l in block.splitlines()
               if "/job-apply" in l
               and any(k in l.lower() for k in (t.lower() for t in TRY))
               and "不是" not in l]
        self.assertEqual(
            bad, [],
            "设计原则里还把 /job-apply 当成可以试一试的演示：" + chr(10) + "  "
            + (chr(10) + "  ").join(bad)
            + chr(10) + "它会真的写文件、出 PDF、生成要发给雇主的话术。")

    def test_the_design_principles_name_one_next_step(self):
        """正面判据：那一行必须明说只给一条。"""
        text = SETUP.read_text(encoding="utf-8")
        block = text[text.find("## 设计原则"):]
        self.assertRegex(
            block, r"只给\*{0,2}一条|只给一条",
            "设计原则里没写明「结束时只给一条下一步」——"
            "而 doctor.py 的设计约束第 4 条正是这么规定的")


if __name__ == "__main__":
    unittest.main()
