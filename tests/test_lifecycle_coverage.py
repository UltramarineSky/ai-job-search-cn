"""求职生命周期不许断在半路——尤其是收益最大的最后一段。

## 补过的两个缺口

**① 基简历从来没被审过。** 流程里有三处碰简历，没有一处审它的内容：
`/job-setup` 填完不回头看；`/job-apply` 的审稿者 **只审话术、简历连读都不读**；
Step 5d/5e 只做机械校验（页数/孤行/乱码/文本层）。而 Step 5 明令
「不得重排结构、增删经历、修改数字」——基简历一旦写歪，**每一次投递都带着
同一个毛病出去**，且越投越难改（已发出去的版本改不回来）。→ `/job-resume`

**② `offer` 只是 tracker 的一个状态值，没有动作接住它。** 而这是整条流水线
代价最大的一段：前面所有环节的收益都在这里兑现，谈砸一次的损失可能超过多投
十个岗。`07-interview-prep.md` 有谈薪方法论，但那是面试准备里的一段知识，
没人说什么时候用、拿哪些数据算。→ `/job-offer`

## 这个文件钉住什么

不是「命令存在」——那太弱。钉的是**接线完整**（工作流 ↔ stub ↔ 索引 ↔ 上游
指路）与**各自的底线规则**。本仓库反复出现「写了没接线」，光有文件等于没有。
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WF = ROOT / "workflows"
CMD = ROOT / ".claude" / "commands"
AGENTS = (ROOT / "AGENTS.md").read_text(encoding="utf-8")


class EveryWorkflowIsReachable(unittest.TestCase):
    """写了工作流不接线 = 没人知道它存在。这是本仓库最常见的一类漏。"""

    def skill_triggered(self):
        """由 skill 壳触发、不走 slash 命令的工作流——**从盘上推，不写手工清单**。

        原来这里是 `{"scrape", "upskill"}` 一张写死的表，注释还写着「目录名与工作流名
        不必相同」。命令统一加 job- 前缀后两边同名了，表退化成恒等映射；留着的唯一
        效果是下次加壳时忘了登记，然后收到「这个工作流没有入口」的假报警。
        `lint_skills.check_workflow_layout` 同一处也是这么改的——两边都按同名接线。
        """
        return {p.parent.name for p in
                (ROOT / ".claude" / "skills").glob("*/SKILL.md")}

    def test_the_scan_reaches_the_workflows(self):
        """对照用例：扫描真的够到了文件 —— 否则同文件里那些「没问题」是恒绿的。

        2026-08-20 实测：把 `Path.glob`/`rglob` 打成空之后本文件全绿。
        **扫不到文件时，「没有问题」和「没有检查」长得一模一样。**

        这不是假想——这个仓库真搬过目录（工作流正文从 `.claude/skills/` 搬到
        `workflows/`，`AGENTS.md` 里记着）。glob 还指着旧路径时，守卫会安静地失效。
        """
        found = list(WF.glob("*.md"))
        self.assertGreaterEqual(
            len(found), 15,
            f"只扫到 {len(found)} 个工作流 —— 判据大概是够不到文件了，"
            "而不是仓库真的只剩这么几个")

    def test_each_workflow_has_a_stub_or_a_skill(self):
        wf = {p.stem for p in WF.glob("*.md")}
        stubs = {p.stem for p in CMD.glob("*.md")}
        missing = sorted(wf - stubs - self.skill_triggered())
        self.assertEqual(missing, [],
                         f"这些工作流既没有 slash 命令也不由 skill 触发：{missing}")

    def test_no_stub_points_at_a_missing_workflow(self):
        wf = {p.stem for p in WF.glob("*.md")}
        stubs = {p.stem for p in CMD.glob("*.md")}
        self.assertEqual(sorted(stubs - wf), [], "有 stub 指向不存在的工作流")

    def test_each_workflow_is_in_the_index(self):
        """AGENTS.md 的索引是 AI 进入这个仓库的唯一目录。"""
        wf = {p.stem for p in WF.glob("*.md")}
        indexed = set(re.findall(r"workflows/([a-z-]+)\.md", AGENTS))
        self.assertEqual(sorted(wf - indexed), [],
                         "这些工作流没进 AGENTS.md 的索引，AI 不会知道它们存在")

    def test_stubs_stay_thin(self):
        """stub 只负责指路。内容写进 stub 会和工作流正文飘。"""
        for p in sorted(CMD.glob("*.md")):
            with self.subTest(cmd=p.stem):
                self.assertLessEqual(
                    len([l for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]),
                    5, f"{p.name} 太长了 —— stub 应该只有标题和一句「读取并执行」")


class ResumeAuditExistsAndKnowsItsLimits(unittest.TestCase):

    def setUp(self):
        self.t = (WF / "job-resume.md").read_text(encoding="utf-8")

    def test_it_audits_the_base_resume_not_the_tailored_one(self):
        self.assertIn("resume/main.typ", self.t)
        self.assertIn("基简历", self.t, "没说清审的是基简历而非某次投递的定制版")

    def test_it_never_writes_without_confirmation(self):
        """基简历是所有投递共用的。改它会让已投出去的版本与在线简历对不上
        ——`05-cv-templates.md` 说那「比说得不够好更具破坏性」。

        「未经确认」在正文与「重要规则」两处都出现，只查关键词在不在的话，
        把正文那句改成「可以直接动」照样绿。所以要求**禁令措辞**成对出现：
        动手那一步说「绝不」，规则表里说「不越权改」。
        """
        self.assertRegex(
            self.t, r"\*\*绝不\*\*未经确认就动 `resume/main\.typ`",
            "动手那一步没有明确禁令 —— 只在规则表里写一句拦不住")
        self.assertIn("不越权改", self.t, "重要规则里丢了这一条")

    def test_profile_is_the_single_source_of_truth(self):
        self.assertIn("唯一事实源", self.t)
        self.assertIn("不编造", self.t, "没禁止往简历里加资料没有的数字")

    def test_it_warns_about_typography_noise(self):
        """实测踩过：直接扫 .typ 捞出 40 多个「对不上」，绝大多数是字号与颜色。
        报告一旦有噪音，用户下次就不看了。"""
        self.assertIn("排版数字", self.t, "没提醒先剥掉字号/颜色/尺寸")
        self.assertIn("假阳性", self.t)

    def test_it_archives_the_report(self):
        """审核会反复做，历次报告放在一起才看得出「上次说要补的补了没有」。

        与 `/job-upskill` 的 `report-YYYY-MM-DD.md` 同一个约定：按日期存、不覆盖。
        """
        self.assertIn("resume-audit-", self.t, "报告不落盘，下次审无从对比")
        self.assertIn("不覆盖", self.t, "没规定按日期累加")

    def test_the_report_records_which_version_it_audited(self):
        """没有「审的是哪一版」，两周后回看不知道那份报告对应改前还是改后。"""
        seg = self.t[self.t.index("### 落盘"):]
        for k in ("修改时间", "页数", "框架版本"):
            with self.subTest(item=k):
                self.assertIn(k, seg, f"报告头部没记「{k}」")

    def test_the_report_does_not_duplicate_the_resume(self):
        """把简历全文粘进报告，两处必然飘。"""
        self.assertIn("不要重复粘简历全文", self.t)

    def test_setup_points_at_it(self):
        s = (WF / "job-setup.md").read_text(encoding="utf-8")
        self.assertIn("/job-resume", s, "/job-setup 写完简历后没指向审核这一步")


class OfferStageExistsAndProtectsTheUser(unittest.TestCase):

    def setUp(self):
        self.t = (WF / "job-offer.md").read_text(encoding="utf-8")

    def test_background_check_redline_is_mandatory(self):
        """报的薪资与个税记录对不上 → offer 被撤回，且不诚信记录可能被留存。
        这是整条流水线后果最重的一条，不许因为「他应该知道」而跳过。"""
        self.assertIn("背调", self.t)
        self.assertIn("个税", self.t, "没提个税记录这个可核实的锚点")
        self.assertIn("不许跳过", self.t, "背调自查没被标成必做")

    def test_it_does_not_decide_for_the_user(self):
        self.assertIn("不替他决定", self.t)
        # 唯一例外：低于底线要明确劝退——那个数是他清醒时定的
        self.assertIn("低于底线", self.t, "没有「低于底线明确建议不接」这条例外")

    def test_comparison_uses_the_candidates_own_weights(self):
        """多 offer 比较必须用同一把尺，且是**他自己的**权重。"""
        self.assertIn("评分权重", self.t)
        self.assertIn("30/25/20/25", self.t, "没说明没写权重时的默认值")

    def test_it_surfaces_irreversible_choices(self):
        """加权总分会掩盖不可逆项：编制、落户、行权期、竞业——选错几年改不回来。"""
        self.assertIn("不可逆", self.t)

    def test_exit_checklist_covers_the_transition(self):
        """锚到**清单那一节**，不是全文搜关键词。

        「竞业」全文出现 6 次（取数、不可逆项、重要规则都提到它），全文搜必然命中
        ——把清单里那一条整个删掉，测试照样绿。实测变异验证时就这么漏过。
        断言要落在它真正该出现的位置上。
        """
        seg = self.t[self.t.index("## Step 4:"):self.t.index("## Step 5:")]
        items = re.findall(r"^- \[ \] \*\*(.+?)\*\*", seg, re.M)
        joined = "".join(items)
        for k in ("离职证明", "竞业", "入职日期", "三方"):
            with self.subTest(item=k):
                self.assertIn(k, joined,
                              f"接 offer 前的清单里漏了「{k}」（当前有：{items}）")

    def test_it_only_reads_the_tracker(self):
        """两处都能写 tracker 会飘——写入统一由 /job-outcome 做。"""
        self.assertIn("只读不写 tracker", self.t)

    def test_it_never_contacts_the_employer(self):
        """与 /job-outcome 的跟进分支同一条底线：话术是给他用的，绝不代发。"""
        self.assertIn("不代劳", self.t)

    def test_outcome_points_at_it_when_an_offer_lands(self):
        """谈薪的准备必须发生在报数字**之前**，事后再算没有意义。"""
        o = (WF / "job-outcome.md").read_text(encoding="utf-8")
        self.assertIn("/job-offer", o, "/job-outcome 记到 offer 时没提示去做谈薪准备")


if __name__ == "__main__":
    unittest.main()
