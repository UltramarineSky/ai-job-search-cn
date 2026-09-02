# -*- coding: utf-8 -*-
"""`/job-outcome` 说校准会并进 `04-job-evaluation.md` —— 而没有任何一处会写它。

三处这么写：

    第 6 行    「`/job-setup` 的路线 A 会来挖它，用来校准 `04-job-evaluation.md`」
    Step 5     「跑一次 `/job-setup`（路线 A）把它们并进评估标准」
    Step 5     「不要自己往 `04-job-evaluation.md` … 里写任何东西。那次合并归路线 A 管」

而路线 A 自己明写着**不改它**：

> 写进 `profile/candidate.md`，**带上日期** ——匹配信号记在「求职偏好」下，
> 重复被拒的模式记在「明确排除」下。**不要改 `04-job-evaluation.md`**，
> 那是纯框架的打分标准，不是数据文件。

全仓扫过（2026-08-23）：**04 到处都是只读的，没有任何一处会写它。**

## 为什么这不只是措辞

禁令本身是对的（谁都不该写 04），错的是它给的理由：「那次合并归路线 A 管」——
而路线 A 拒绝做那次合并。更要紧的是用户那一头：他被告知「并进评估标准」，
回头去看 `04-job-evaluation.md` 一个字没动，会以为这条校准根本没跑。
**真正的落点是 `candidate.md`**，而那也正是打分时会被读到的地方
（硬门取值、明确排除、求职偏好）。

这是跨命令交接扫查的第三例：`job-reset → /job-user`（不列要清的东西）、
`job-gmail-sync → /job-outcome`（冲突没落点）、这一条（指错落点）。
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = (ROOT / "workflows" / "job-outcome.md").read_text(encoding="utf-8")
SETUP = (ROOT / "workflows" / "job-setup.md").read_text(encoding="utf-8")
GMAIL = (ROOT / "workflows" / "job-gmail-sync.md").read_text(encoding="utf-8")


def _step5() -> str:
    i = OUT.index("## Step 5：把校准信号交出去")
    return OUT[i:OUT.index("## Step 6", i)]


class TheHandoffNamesTheRightFile(unittest.TestCase):
    def test_the_intro_line_points_at_the_profile(self):
        i = OUT.index("路线 A 会来挖它")
        seg = OUT[i:i + 160]
        self.assertIn("profile/candidate.md", seg)
        self.assertIn("不是 `04-job-evaluation.md`", seg,
                      "没把「不是那份」说出来 —— 那正是原来读错的地方")

    def test_the_offer_to_the_user_says_where_it_lands(self):
        """他要能对着结果去核。说「并进评估标准」，他会去看错的文件。

        **只看念给他听的那几行**（`> ` 引用块）。下面那段 ⚠️ 逐字引了旧措辞
        （说明它为什么被换掉），整段扫会撞上自己的解释 —— 变异实测抓到。"""
        want = ("> 你已经有", "> 真的约到面", "> 面试反馈里")
        quoted = chr(10).join(ln for ln in _step5().splitlines()
                              if ln.strip().startswith(want))
        self.assertTrue(quoted, "念给他听的那段不见了")
        self.assertIn("并进你的资料", quoted)
        self.assertNotIn("并进评估标准", quoted, "念给他听的那句还指着框架文件")

    def test_it_names_the_two_kinds_of_signal(self):
        """一句「校准」什么也没说。约到面的记成什么、被拒的记成什么，要写出来。"""
        seg = " ".join(_step5().split())
        self.assertRegex(seg, r"已验证的匹配信号")
        self.assertRegex(seg, r"两次以上没下文或被拒")

    def test_the_star_half_survives(self):
        """路线 A 同时会挖 STAR 素材 —— 那半不许被这次改动带掉。"""
        self.assertIn("STAR", _step5())

    def test_the_prohibition_survives(self):
        """禁令是对的，只是理由错了。别把禁令一起改掉。"""
        self.assertIn("**不要**自己往 `04-job-evaluation.md`", _step5())

    def test_the_real_reason_replaces_the_false_one(self):
        seg = " ".join(_step5().split())
        self.assertRegex(seg, r"禁令对，理由原来是错的")
        self.assertRegex(seg, r"04 是框架不是数据")

    def test_it_quotes_route_a_saying_it_will_not(self):
        """引原话，别转述 —— 转述会再飘一次。

        **理由那半也要引。** 只验第一行的话，把「那是纯框架的打分标准，
        不是数据文件」删掉照样绿（变异实测）—— 而那半才是禁令真正的依据。"""
        seg = _step5()
        self.assertIn("不要改 `04-job-evaluation.md`", seg)
        self.assertIn("那是纯框架的打分标准，不是数据文件", seg,
                      "只引了禁令，没引它的理由")

    def test_it_says_what_the_user_would_have_concluded(self):
        """规则不带后果就会被当成措辞洁癖删掉。"""
        self.assertRegex(" ".join(_step5().split()),
                         r"就会以为这条校准根本没跑")

    def test_it_says_the_profile_is_what_scoring_reads(self):
        """「落点在 candidate.md」听起来像降级。要说清那才是打分真正读的地方。"""
        seg = " ".join(_step5().split())
        self.assertRegex(seg, r"硬门取值、明确排除、求职偏好")


class RouteAReallyDoesThis(unittest.TestCase):
    """这一段全建立在路线 A 的行为上。它变了，这里要跟着。"""

    def test_route_a_reads_the_applications_archive(self):
        self.assertIn("`applications/`", SETUP)
        i = SETUP.index("**`applications/<公司>_<岗位>/` 这些子目录：**")
        self.assertIn("job-outcome.md", SETUP[i:i + 600])

    def test_route_a_writes_to_the_profile(self):
        """**要那句祈使，不是那一行的抬头。** 那一段的抬头本身就是
        「`profile/candidate.md`（校准信号，来自归档的…」—— 从锚点往后切，
        文件名在锚点**前面**，于是把「写进 `profile/candidate.md`」删掉照样绿
        （变异实测）。"""
        i = SETUP.index("校准信号，来自归档的")
        seg = SETUP[i:i + 700]
        self.assertIn("写进 `profile/candidate.md`", seg, "没说清写到哪儿去")
        self.assertIn("求职偏好", seg)
        self.assertIn("明确排除", seg)

    def test_route_a_refuses_to_touch_the_framework(self):
        i = SETUP.index("校准信号，来自归档的")
        self.assertIn("不要改 `04-job-evaluation.md`", SETUP[i:i + 700])

    def test_route_a_skips_unfinished_applications(self):
        """还在跑的给不了信号 —— 这条是校准能成立的前提。"""
        self.assertRegex(" ".join(SETUP.split()), r"校准时跳过 `in_progress` 的")


class NobodyWritesTheFramework(unittest.TestCase):
    """整条论证的事实基础：04 全仓只读。哪天真有人写它，上面几条都要重写。"""

    def test_route_a_and_this_step_agree(self):
        """**两处必须说同一件事。** 这才是当初露出来的那一头：
        路线 A 写「不要改 04，写进 candidate.md」，而这一步说「并进评估标准」。

        （第一版这里是个正则扫描器，想在全仓找「声称会写 04」的句子 ——
        中文散文判不准：`这一项不写入独立占位符——04…`、`就写「无」，04 的这道门
        自动不适用` 都被当成了违规，加上我自己引用旧措辞的那一句，三个误报。
        判不准的扫描器比没有更坏，换成这两处对齐。）"""
        self.assertIn("不要改 `04-job-evaluation.md`", SETUP)
        self.assertIn("不要改 `04-job-evaluation.md`", _step5())
        self.assertIn("profile/candidate.md", _step5())

    def test_the_gmail_side_does_not_name_it_either(self):
        """`job-gmail-sync` 指的是「与 `/job-outcome` 提的同一条」——
        它不点 04 的名，所以只要这边说对了它就跟着对。"""
        i = GMAIL.index("走 `/job-setup` 路线 A 的校准")
        seg = GMAIL[max(0, i - 200):i + 200]
        self.assertNotIn("04-job-evaluation", seg)
        self.assertIn("与 `/job-outcome` 提的是同一条", seg)

    def test_the_gmail_side_still_refuses_to_duplicate(self):
        self.assertIn("不要在这里复制那套逻辑，指过去就行", GMAIL)


if __name__ == "__main__":
    unittest.main()
