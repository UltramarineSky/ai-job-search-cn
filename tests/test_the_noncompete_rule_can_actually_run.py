# -*- coding: utf-8 -*-
"""竞业限制那条规则，在批量评分这条路上执行不了 —— 指针悬空了两层。

`04-job-evaluation.md` 的规则本身很稳（**不做成硬门**是对的，理由在下面）：

> 候选人资料里**明确记录了**真实的竞业限制（写明了限制公司或范围，不是「无」、
> 不是带 `← 假设值` 标记的默认值）→ 目标公司命中限制范围时，
> 写进输出格式里「有哪些信息没核实上」那一节（不计分），让用户自己判断。

而 `/job-rank` Step 2 分发给子代理时，硬门那份枚举里 7 道门**每一道都给了判据**
（连「候选人自己划的『明确排除』」这种带取值的都在），只有竞业给的是一句
**「处理见 `04-job-evaluation.md` 那一节」**。两层都够不着：

1. **代理读不到那份文件。** 紧挨着的下一句就是「东西全部写进提示里」
   「**不要**让代理再去读一遍资料文件」—— Step 1 把框架和资料
   **只读一次**然后蒸馏进提示，代理手上只有提示。
2. **就算读到了，也没地方写。** 那条规则要求写进「有哪些信息没核实上」那一节 ——
   那是 `/job-apply` 的输出格式才有的。`/job-rank` 落盘只有
   `rank_score` / `rank_verdict` / `rank_date` / `rank_breakdown`。

更根本的一点：那条规则要拿**用户的竞业范围**去比对目标公司，而那个**取值**
根本不在提示的枚举里 —— 代理没有可比的东西，规则从来没生效过。

## 为什么不顺手把它升成硬门

框架自己给了判据（第 4 节末）：

> 只有当一个条件既是二值的、又有确凿证据时，才配当一票否决。连续量和假设值都不配。

真值竞业两条都占 —— 但**框架仍然故意不把它做成一票否决**，那是个有理由的决定：
国内竞业补偿未付即可能失效、范围解释常有争议、前东家多数并不追究。
该由本人判断，不由工具替他判掉。**这次不动那个决定**，只让中间那条分支能跑。

## 落点为什么选 `依据`

它是 `/job-rank` 输出里**真实存在**、且会到用户眼前的字段：
`export_web_data` 过一道 `plain()` 变成 `skillWhy`，进短名单行的悬浮提示。
实测 2026-08-23：2456 个岗**全部**有 `依据`。
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RANK = (ROOT / "workflows" / "job-rank.md").read_text(encoding="utf-8")
EVAL = (ROOT / "workflows" / "reference"
        / "04-job-evaluation.md").read_text(encoding="utf-8")
APPLY = (ROOT / "workflows" / "job-apply.md").read_text(encoding="utf-8")


def prompt_spec() -> str:
    """Step 2 里「每个代理要用的东西全部写进提示里」那一条的正文。"""
    i = RANK.index("每个代理要用的东西**全部写进提示里**")
    return RANK[i:RANK.index("\n- 每个代理用网页抓取能力", i)]


class TheRuleHasSomewhereToRun(unittest.TestCase):
    def test_the_dangling_pointer_is_gone(self):
        self.assertNotIn("竞业限制的处理见 `04-job-evaluation.md` 那一节",
                         prompt_spec(),
                         "还是一句指向文件的指针 —— 代理被明令不许再读文件")

    def test_both_branches_are_spelled_out(self):
        """两支缺一支都会出错：缺前一支 → 每个岗挂一条永远为真的提醒；
        缺后一支 → 真签过的人一个提醒都收不到。"""
        seg = " ".join(prompt_spec().split())
        self.assertRegex(seg, r"一个字都不要放进提示",
                         "「无 / 假设值」那一支没了")
        self.assertRegex(seg, r"明确记录了真实范围",
                         "「有真值」那一支没了")

    def test_the_real_branch_passes_the_value_not_a_pointer(self):
        """这才是要害 —— 代理要有**可比的东西**，不是一句「按规则办」。"""
        seg = " ".join(prompt_spec().split())
        self.assertRegex(seg, r"把那个范围原样写进提示")

    def test_it_lands_in_a_field_that_exists(self):
        seg = prompt_spec()
        self.assertIn("rank_breakdown.依据", seg)
        self.assertIn("⚠️ 可能在你的竞业范围内：", seg, "没给出要写的原话")

    def test_the_landing_field_is_really_in_the_output_spec(self):
        """落点得真的在落盘规范里 —— 否则换个地方悬空而已。"""
        i = RANK.index("落盘形状（**注意与 Step 2 回传格式的差别**）")
        self.assertIn('"依据"', RANK[i:i + 700])

    def test_it_changes_no_number(self):
        """它不是硬门，也不计分。少了这句，下一个人会顺手把它做成扣分项。"""
        seg = " ".join(prompt_spec().split())
        self.assertRegex(seg, r"不扣分、不改判词、不算硬门 FAIL")

    def test_it_says_why_it_is_not_a_veto(self):
        """「不一票否决」不给理由，就会被当成疏漏「修」掉。"""
        seg = " ".join(prompt_spec().split())
        self.assertRegex(seg, r"补偿未付即可能失效")
        self.assertRegex(seg, r"该由本人判断")

    def test_it_names_the_backstop(self):
        """不否决的前提是后面还有人接。那一道没了，这里就得重新想。"""
        self.assertIn("/job-offer", prompt_spec())
        self.assertIn("**竞业限制**：签过吗？范围涵盖新东家吗？",
                      (ROOT / "workflows" / "job-offer.md")
                      .read_text(encoding="utf-8"))

    def test_the_two_dead_ends_are_written_down(self):
        """不写下来，下一版会觉得这几行啰嗦，把它压回一句「见框架」。"""
        seg = " ".join(prompt_spec().split())
        self.assertRegex(seg, r"指针悬空了两层")
        self.assertRegex(seg, r"根本没有这一节")


class TheFrameworkAdmitsItsSectionIsApplyOnly(unittest.TestCase):
    """规则的正本要说清那一节只有一条路上有，否则两边还会各写各的。"""

    def _rule(self) -> str:
        i = EVAL.index("### 竞业限制**不是硬门**")
        return EVAL[i:EVAL.index("## 第二步：四维打分", i)]

    def test_it_says_the_section_is_apply_only(self):
        self.assertRegex(" ".join(self._rule().split()),
                         r"那一节是 `/job-apply` 的输出格式才有的")

    def test_it_names_where_rank_lands_it(self):
        self.assertIn("rank_breakdown.依据", self._rule())

    def test_it_stays_the_authority(self):
        """交叉引用不是把判据搬走。判据仍在这一节。"""
        seg = self._rule()
        self.assertIn("判据仍以本节为准", seg)
        self.assertIn("不进硬门表，不参与一票否决", seg)

    def test_the_silent_branch_survives(self):
        """「无 / 假设值 → 一个字都不要提」是它不污染每份评估的关键。"""
        self.assertRegex(" ".join(self._rule().split()),
                         r"资料里是「无」或假设值 → \*\*一个字都不要提\*\*")

    def test_it_is_still_not_a_gate(self):
        """本轮没有动这个决定 —— 动了的话上面几条的理由全要重写。"""
        self.assertIn("竞业限制", str(_not_gates()))

    def test_the_veto_criterion_it_leans_on_still_exists(self):
        """这句话在引用块里跨了两行，中间既有 `> ` 也有折行 —— 拉平会变成
        `…确凿证据 > 时，才配…`，再用单空格拼又变成 `…确凿证据 时，…`。
        中文本来就不带空格，**整句去掉空白和 `**` 再比**最省事。"""
        flat = "".join(EVAL.split()).replace(">", "").replace("*", "")
        self.assertIn("只有当一个条件既是二值的、又有确凿证据时，才配当一票否决",
                      flat)


def _not_gates():
    """硬门枚举守卫里那份「显式不算硬门」的清单。"""
    src = (ROOT / "tests"
           / "test_hard_gate_enumeration_is_complete.py").read_text(
        encoding="utf-8")
    m = re.search(r"NOT_GATES\s*=\s*\(([^)]*)\)", src)
    assert m, "找不到 NOT_GATES"
    return re.findall(r"[\"']([^\"']+)[\"']", m.group(1))


class TheOtherConsumerIsUnaffected(unittest.TestCase):
    """`/job-apply` 自己读框架与资料，规则在那儿本来就能落地 —— 别顺手改坏它。"""

    def test_apply_reads_the_framework_itself(self):
        self.assertIn("workflows/reference/04-job-evaluation.md", APPLY)

    def test_apply_reads_the_profile_itself(self):
        self.assertIn("profile/candidate.md", APPLY)

    def test_rank_says_apply_is_unaffected(self):
        self.assertRegex(" ".join(prompt_spec().split()),
                         r"`/job-apply` 那边不受影响")


class TheSetupReallyCollectsIt(unittest.TestCase):
    """整条链的起点：`/job-setup` 真的会问这个值。不问，两支都是空转。"""

    def test_setup_asks(self):
        s = (ROOT / "workflows" / "job-setup.md").read_text(encoding="utf-8")
        self.assertIn("**问：竞业限制", s)

    def test_setup_does_not_mark_it_assumed(self):
        """标成假设值会让每份评估挂一条永远为真的提醒 —— setup 早写明了。"""
        s = " ".join((ROOT / "workflows" / "job-setup.md")
                     .read_text(encoding="utf-8").split())
        self.assertRegex(s, r"竞业\*\*不是硬门\*\*")

    def test_setup_keeps_it_apart_from_the_shareholding_question(self):
        """竞业是前雇主限制你，对外持股是你对新雇主的申报义务 —— 两回事。"""
        s = (ROOT / "workflows" / "job-setup.md").read_text(encoding="utf-8")
        self.assertIn("这和上一问的竞业限制不是一回事，别合并着问", s)


class TheGraduateSectionDoesNotWaveAwayWhatStillApplies(unittest.TestCase):
    """「对外任职 / 持股 / 在营公司」这一条，应届生**同样要问**。

    Step 2 那张背调自查表有五条，而「应届生查的是另外几样」那一节原来写着
    「**上面那五条对他们一条都不适用**」，理由只列了四个
    （没有当前薪资、没有前雇主、没有离职证明、没有离职原因）——
    **五条，四个理由**。漏掉的正是第五条。

    而第五条是**后来补进那张表的**（表里那段说明写着「这一条原来整个不在
    这张表里」）：**计数从四改成了五，这句断言和应届生那张清单都没跟。**

    它对应届生不但成立，还更容易踩：在校创业、被家里人挂成法人或股东、
    代持 —— 工商关联与对外投资是背调报告的标准栏目，企查查一查就有，
    而它是**现在时**，没有「离职证明」可以对。学生身份不豁免这一栏。

    枚举改一处漏一处 —— 同 `documents/` 那六个子目录的三次学费
    （`/job-setup` 只建一个、`/job-reset` 只删五个、预览只报五个）。
    """

    OFFER = (ROOT / "workflows" / "job-offer.md").read_text(encoding="utf-8")

    def _graduate_section(self) -> str:
        i = self.OFFER.index("### 应届生查的是另外几样")
        return self.OFFER[i:self.OFFER.index("\n## ", i)]

    def _body(self) -> str:
        """只看正文，不看讲经过的引用块 —— 我为这次修补写的说明里就点了
        「一条都不适用」这句原话，算进去的话断言会被自己的说明喂饱。"""
        return "\n".join(l for l in self._graduate_section().splitlines()
                         if not l.lstrip().startswith(">"))

    def test_the_main_list_still_has_the_equity_item(self):
        """控制用例：那一条还在主表里，否则下面两条在为一条不存在的规则把关。"""
        i = self.OFFER.index("## Step 2")
        main = self.OFFER[i:self.OFFER.index("### 应届生", i)]
        self.assertIn("对外任职", main, "主表里那条「对外任职 / 持股」不见了")

    def test_it_does_not_claim_all_of_them_are_moot(self):
        self.assertNotIn(
            "一条都不适用", self._body(),
            "又宣称主表那几条对应届生「一条都不适用」—— "
            "「对外任职 / 持股 / 在营公司」照样成立，而且在校创业过的最容易踩")

    def test_the_graduate_checklist_covers_it(self):
        b = self._body()
        self.assertRegex(
            b, r"对外任职|持股|在营公司",
            "应届生那张清单里没有「对外任职 / 持股」这一条 —— "
            "被上面那句「不适用」挡掉之后，它在两处都查不到")


if __name__ == "__main__":
    unittest.main()
