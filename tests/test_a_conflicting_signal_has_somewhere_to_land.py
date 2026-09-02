# -*- coding: utf-8 -*-
"""`/job-gmail-sync` 检出信号打架就不写盘，把人推给 `/job-outcome` —— 那边没这回事。

它的冲突规则写得很稳：

> 判出来的信号与这次投递当前的「是否已结案」相矛盾时（比如某家的投递记录刚写过
> 接近 `rejected` 的状态，却又来了一封「进入下一轮」；或者这一轮刚提议了 offer，
> 又来了拒信）——**不要提议覆盖它**。在 Step 6 里记成一条冲突，
> **留给用户手动跑 `/job-outcome` 定夺**。

报告里还专门有一节：「信号打架，要你自己判断（没提改动，用 `/job-outcome` 记）」。

**而这三个词当时在 `job-outcome.md` 里一次都没出现**（实测 2026-08-20，打架 0 次、冲突 0 次、矛盾 0 次；下面那几条断言补上之后才有）。用户带着两份互相
矛盾的证据过去，那边 Step 2 只会问一句「发生了什么」—— 交接落到地上就散了。

这是上一轮那个形状的第二例（A 说「这事去用 B」，B 不知道）：
`job-reset` 指着 `/job-user` 清 `upskill/`，而 `/job-user` 不列它。

## 为什么不能默认「后一封为准」

国内拒信多是**群发模板**：同一天群发，隔几天某个岗位重启、或另一个部门单独捞人
——两封都真，不是覆盖关系。反过来 offer 被撤回也真实存在。
所以按**证据**分三种，而不是按新旧；看不出来的那一种**不判**，
只把两封都追加进记录 —— 半年后回头看，「为什么这家先拒后邀」本身就是要查的东西。
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = (ROOT / "workflows" / "job-outcome.md").read_text(encoding="utf-8")
GMAIL = (ROOT / "workflows" / "job-gmail-sync.md").read_text(encoding="utf-8")


def _seg() -> str:
    i = OUT.index("## Step 2：问清楚发生了什么")
    return OUT[i:OUT.index("问用户发生了什么，然后归类：", i)]


class TheHandoffLands(unittest.TestCase):
    def test_step2_knows_the_case_exists(self):
        self.assertIn("被 `/job-gmail-sync` 推过来定夺一条打架的信号", _seg(),
                      "Step 2 仍然只会问「发生了什么」")

    def test_it_comes_before_the_normal_question(self):
        """摆在归类之后就晚了 —— 那时候已经按普通新事在问了。"""
        self.assertLess(OUT.index("被 `/job-gmail-sync` 推过来"),
                        OUT.index("问用户发生了什么，然后归类："))

    def test_it_says_what_arrives_is_not_a_new_event(self):
        """这是整段的要害：推过来的是一个**局面**，不是一件待记的事。"""
        self.assertRegex(" ".join(_seg().split()),
                         r"已经有两份互相矛盾证据的局面，不是一件待记的新事")

    def test_it_gives_three_outcomes_not_two(self):
        """**三种，不是两种。** 二分（改 / 不改）会把「其实是两次投递」
        那一类挤进「不改」，而那一类要做的事完全不同 —— 回 Step 1 重新认行。

        （从 `| 情形 |` 切起时表头那一行已经丢了行首的 `>`，所以这里数到的
        就是三行数据 —— 第一版按「表头 + 三行 = 4」写，当场差一。）"""
        seg = _seg()
        i = seg.index("| 情形 |")
        rows = [ln for ln in seg[i:].splitlines()
                if ln.strip().startswith(">") and "|" in ln and "---" not in ln]
        self.assertEqual(len(rows), 3, f"不是三行：{rows}")
        self.assertIn("以后一封为准", rows[0])
        self.assertIn("不是同一次投递", rows[1])
        self.assertIn("不判", rows[2])

    def test_the_split_is_by_evidence_not_recency(self):
        """按新旧分是最容易写的，也是错的。"""
        self.assertRegex(" ".join(_seg().split()), r"按\*\*证据\*\*分，不按新旧分")

    def test_the_unclear_case_writes_nothing(self):
        """看不出哪个对时改状态，就是拿一次猜测污染永久记录。"""
        seg = " ".join(_seg().split())
        self.assertIn("看不出哪个对", seg)
        self.assertRegex(seg, r"状态原样不动")

    def test_the_two_applications_case_is_there(self):
        """同一家公司两次投递是国内常态（不同部门各自推进）——
        那根本不是冲突，是认错了行。"""
        seg = " ".join(_seg().split())
        self.assertRegex(seg, r"不是同一次投递")
        self.assertIn("Step 1", seg, "没说清该回哪一步重新认")

    def test_all_three_append_both_letters(self):
        seg = " ".join(_seg().split())
        self.assertRegex(seg, r"三种都往 `## 记录` 里追加")
        self.assertRegex(seg, r"日期、发件人、标题", "没说清每封要记什么")

    def test_it_says_why_the_loser_is_kept(self):
        """只留胜者最省事，也最没用。"""
        self.assertRegex(" ".join(_seg().split()),
                         r"「为什么这家先拒后邀」本身就是要查的东西")

    def test_it_refuses_to_default_to_the_later_letter(self):
        """「后一封为准」听起来最像默认 —— 而国内拒信多是群发模板。"""
        seg = " ".join(_seg().split())
        self.assertRegex(seg, r"别替他判第一种")
        self.assertRegex(seg, r"群发模板")
        self.assertIn("问他", seg, "没给出该问的那一句")

    def test_it_leans_on_the_existing_append_only_rule(self):
        """「只追加、绝不覆盖」是这份归档本来的规矩，别在这里另立一条。"""
        seg = _seg()
        self.assertIn("幂等", seg, "没引 Step 3 那条既有规矩")


class TheOtherSideOfTheHandoffIsIntact(unittest.TestCase):
    """这一段的前提：gmail-sync 真的会把冲突推过来，而且自己不写。"""

    def test_gmail_still_refuses_to_overwrite(self):
        self.assertIn("**不要提议覆盖它**", GMAIL)

    def test_gmail_still_points_here(self):
        self.assertRegex(" ".join(GMAIL.split()),
                         r"留给用户手动跑 `/job-outcome` 定夺")

    def test_gmail_still_has_the_section_in_its_report(self):
        self.assertIn("### 信号打架，要你自己判断（没提改动，用 `/job-outcome` 记）",
                      GMAIL)

    def test_gmail_still_never_writes_without_approval(self):
        """整条交接建立在「它从不自己写盘」上。"""
        self.assertIn("从不自己写盘", GMAIL)


class TheNormalPathIsUntouched(unittest.TestCase):
    def test_the_classification_still_follows(self):
        self.assertIn("问用户发生了什么，然后归类：", OUT)
        for k in ("算进展的", "收到面试邀请", "拿到 offer"):
            with self.subTest(k=k):
                self.assertIn(k, OUT)

    def test_the_offer_nudge_survives(self):
        """记到 offer 时要在同一轮里提 `/job-offer` —— 谈薪准备必须在报数字之前。"""
        self.assertIn("/job-offer <公司>", OUT)
        self.assertRegex(" ".join(OUT.split()), r"事后再算没有意义")

    def test_the_append_only_archive_rule_survives(self):
        self.assertRegex(" ".join(OUT.split()),
                         r"既不会重复记，也不会改写历史")

    def test_the_followup_branch_survives(self):
        """上几轮加的两件事都在这条分支上。"""
        self.assertIn("## Step 2b：跟进分支", OUT)
        self.assertIn("猎头那批，催之前先看一眼邮箱", OUT)


if __name__ == "__main__":
    unittest.main()
