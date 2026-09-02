"""判词天花板 + 薪资平台化：判词档不得高于技能档，钱只封顶不惩罚。

## 这套规则是两轮改出来的，两轮的教训都要钉住

**第一轮**：发现「只要钱给够，技能再差总分也能爬到 60」——技能 28 的岗写着
「值得投」。当时补了两刀：技能 <25/25-39 的判词封顶，和「薪资超期望 1.5 倍罚到 70」。

**第二轮**（用户叫停「你不要盲目改」之后重推）发现第一轮自己有两个错：

1. **封顶只封了下半区。** 构造一个完全合法的输入就能穿过去：
   技能 55 · 薪资 90 · 强度 85 · 发展 90 → 总分 78.5 → 强匹配。
   技能 55 的定义是「部分命中，需要明显补课」——顶着「强匹配」同样是误导。
   所以天花板改成全档。**第三轮**又发现边界 70/50/30 是照一位候选人的分数分布凑的
   （过拟合），改为直接取技能与经验自己的分档：≥80 / 60-79 / 40-59 / <40。
2. **1.5× 罚分是重复计账。** 「职级不对」是可行性事实，技能那一维已经直接量过；
   薪资再罚一次，同一个事实计两次，还会误伤「技能 85 + 年包 100 万」的真对口岗。
   撤掉：分数平台化（到期望即 90，再多不加），警示降级为强制 ⚠ 标志。

另外粗筛的强度/发展只许 30/50/70/85 四档取值——精确到个位的数字是假精度，
它们合计 45% 权重，±10 的猜测噪声足以淹没技能 5 分的真实差异。

判词由 AI 按框架给出，没有可执行的实现，所以这里钉三层：规则还在文档里、
`/job-rank` 照做、真实产出里不出现被禁的组合。
"""

import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import scoring as _sc  # noqa: E402
FRAMEWORK = ROOT / "workflows" / "reference" / "04-job-evaluation.md"
RANK = ROOT / "workflows" / "job-rank.md"

#: 各判词要求的技能最低档。低于它就不许挂这个判词。
VERDICT_FLOOR = {"强匹配": 80, "值得投": 60, "可以考虑": 40}

#: 粗筛阶段强度/发展允许的取值。**正本在 `scoring.COARSE_LEVELS`** ——
#: 这里原来自己抄了一份 `{30, 50, 70, 85}`，改一处另一处不会红。
COARSE_LEVELS = set(_sc.COARSE_LEVELS)


class TheRuleIsDocumented(unittest.TestCase):
    def test_framework_states_the_full_ceiling(self):
        t = FRAMEWORK.read_text(encoding="utf-8")
        self.assertIn("判词天花板", t, "框架里找不到「判词天花板」这一节")
        self.assertRegex(t, r"≥\s*80", "缺少「技能 ≥80 才可强匹配」")
        self.assertRegex(t, r"60-79", "缺少「60-79 → 最高值得投」")
        self.assertRegex(t, r"40-59", "缺少「40-59 → 最高可以考虑」")
        self.assertRegex(t, r"<\s*40", "缺少「<40 → 最高不建议」")

    def test_the_upper_half_hole_is_recorded(self):
        """全档天花板的存在理由：只封下半区时，技能 55 也能顶着强匹配。"""
        t = FRAMEWORK.read_text(encoding="utf-8")
        self.assertIn("78.5", t, "要留下那个穿洞的构造例，否则天花板又会被简化回下半区")

    def test_rank_workflow_applies_the_ceiling(self):
        t = RANK.read_text(encoding="utf-8")
        self.assertIn("判词天花板", t,
                      "rank.md 的判词映射没提天花板，框架写了也不会被执行")
        self.assertIn("较低者", t, "要写明判词取总分档与技能档的较低者")

    def test_boundaries_derive_from_the_dimension_not_from_a_sample(self):
        """档位边界必须从框架自己的语义推，不能从某一个用户的分数分布拟合。

        曾经写成 70/50/30，理由是「用实测案例校准」——那是看着**一位**候选人的
        高分岗恰好落在 84/82/79，于是 70 看起来像个好切点。换个人换个行业，
        分布不一样，这套切点就没有任何依据：**把「这批数据长什么样」误当成了
        「规则该是什么样」**。
        """
        t = FRAMEWORK.read_text(encoding="utf-8")
        self.assertIn("过拟合", t, "要写明 70/50/30 错在哪，否则会被改回去")
        self.assertRegex(
            t, r"技能与经验自己的分档|取技能与经验自己的分档",
            "要写明边界直接取第 1 维的分档，不是另定的数字")
        # 第 1 维那两张表的边界就是 80/60/40，两处必须一致
        for b in ("80-100", "60-79", "40-59"):
            self.assertIn(b, t, f"第 1 维的 {b} 档不在了，天花板就失去依据")

    def test_the_reason_is_recorded_so_it_is_not_deleted_later(self):
        t = FRAMEWORK.read_text(encoding="utf-8")
        self.assertIn("行动建议", t, "要写明判词是行动建议，不是总分的换算结果")


class SalaryIsAPlateauNotAPenalty(unittest.TestCase):
    def test_no_extra_credit_above_expectation(self):
        t = FRAMEWORK.read_text(encoding="utf-8")
        self.assertIn("不再加分", t, "要写明到达期望后钱再多不加分")
        self.assertRegex(
            t, r"年包\*\*下沿\*\*|区间的下沿",
            "要写明用年包下沿打分——上沿是给最理想候选人的")

    def test_overshoot_is_a_flag_not_a_penalty(self):
        t = FRAMEWORK.read_text(encoding="utf-8")
        self.assertIn("1.5 倍", t, "缺少 1.5 倍这个标志触发线")
        self.assertIn("标志", t, "区间远超期望要打强制标志")
        self.assertIn("重复计账", t,
                      "撤掉罚分的原因必须写着——否则下次又会有人把可行性塞进薪资维度")


class TriageDimsAreCoarse(unittest.TestCase):
    def test_framework_lists_the_four_levels(self):
        t = FRAMEWORK.read_text(encoding="utf-8")
        self.assertRegex(t, r"30\s*/\s*50\s*/\s*70\s*/\s*85",
                         "粗筛的强度/发展要限定四档取值")
        self.assertIn("≤ 5", t.replace("≤5", "≤ 5"), "缺少「总分差 ≤5 视为并列」")

    def test_real_triage_entries_use_only_coarse_levels(self):
        """控制测试：真实粗筛产出里，强度/发展必须落在四档上。

        **这条守卫 2026-08-13 之前是反的。** 它写着
        `if b.get("来源") != "粗筛（读了 JD 正文）": continue`——精确匹配一个字符串。
        而 `来源` 是自由文本，库里实际有 **15 种写法**：

            粗筛（读过 JD 正文）        458 条
            粗筛（标题即判据）          113 条
            粗筛（未抓 JD）             32 条
            粗筛（读过 JD 正文/岗位标签行） 14 条
            粗筛（读了 JD 正文）          1 条   ← 守卫只认这一种

        「读**过**」和「读**了**」一字之差。**这条守卫在 1246 条数据里只检查了 1 条**，
        放过了另外 613 条粗筛——实测其中 28 条用了 5/15/40/45/55/60/75 这些四档之外
        的假精度取值，而它一路绿着。

        更要命的是它**恰好放过了最该查的那批**：框架限制四档的理由是「粗筛连 JD 都
        没读，给 62、58 这种数字是假精度」，而被跳过的正是 `粗筛（未抓 JD）`。

        改成**按大类前缀判**。`来源` 的措辞后缀（读过正文 / 标题即判据 / 岗位标签行）
        是有信息量的，不必强行统一；但大类只有那么几个，按前缀匹配就不会再被
        一个字绊倒。
        """
        entries = _all_ranked()
        bad = []
        for title, _, b in entries:
            if not str(b.get("来源") or "").startswith(("粗筛", "预筛")):
                continue
            for name, key in (("强度", "强度与公司性质"), ("发展", "发展与风险")):
                v = b.get(key)
                if v is None:                      # 老条目把四维写在 `四维` 那行里
                    m = re.search(name + r"(\d+)", b.get("四维") or "")
                    v = int(m.group(1)) if m else None
                if isinstance(v, int) and v not in COARSE_LEVELS:
                    bad.append(f"{title[:20]}·{name}{v}")
        self.assertFalse(bad, f"粗筛的强度/发展出现四档之外的取值：{bad}")

    def test_the_source_field_stays_in_a_few_families(self):
        """`来源` 的**大类**是枚举，不是自由文本。

        后缀可以自由写（它记的是这次判断读了什么），但开头必须落在已知大类里——
        否则下一个按 `来源` 分流的守卫又会被一个新写法绕过去，而且是静默绕过。
        """
        # 族清单的正本在 _cli（2026-08-20 收拢）。这里原来自写一份四项的，
        # 与 audit_pipeline 的五项**已经分叉**——「批量」开头的来源那边放行、
        # 这边拦下，当时还错把数据改了来迁就测试。清单跟着正本走；
        # 「哪些族算合法」要收紧时改 _cli 一处，两个守卫一起变。
        import sys as _sys
        _sys.path.insert(0, str(ROOT / "tools"))
        import _cli
        fams = _cli.SOURCE_FAMILIES
        bad = sorted({str((b.get("来源") or ""))
                      for _, _, b in _all_ranked()
                      if b.get("来源")
                      and not str(b["来源"]).startswith(fams)})
        self.assertEqual(bad, [],
                         f"这些「来源」不属于任何已知大类 {fams}：{bad}\n"
                         "——按来源分流的守卫会静默放过它们")

    def test_every_verdict_declares_where_it_came_from(self):
        """**有判词就必须有 `来源`。** 空着比写错更危险。

        上面那条只管「有来源的，大类要对」——于是**根本没有 `来源` 的条目
        从它下面整个漏过去**。2026-08-13 体检实测：库里 75 条有判词、
        `rank_breakdown` 里却没有 `来源`，而四档守卫是
        `if not str(b.get("来源") or "").startswith(("粗筛","预筛")): continue`
        ——空串不匹配任何前缀，这 75 条被静默跳过。

        **一条按字段分流的守卫，必须同时管住「字段缺失」这一支**，
        否则删掉字段就是绕过它最省事的办法（而且往往不是故意的，是历史遗留）。

        `04-job-evaluation.md` 也要求过这件事：预筛的结论要在 `rank_breakdown.来源`
        里标明，「好让复核时能一眼找出来」。没有来源 = 复核时找不出来。
        """
        bad = [f"{t[:24]}（{v}）" for t, v, b in _all_ranked()
               if not (b.get("来源") or "").strip()]
        self.assertEqual(bad, [],
                         f"这些岗有判词却没写来源，复核时无从判断它是怎么来的"
                         f"，也会被按来源分流的守卫跳过：\n  " + "\n  ".join(bad[:20]))

    def test_every_breakdown_says_why(self):
        """有 `rank_breakdown` 就得有 `依据`——面板展开后要能看到一句人话。

        实测漏过 1 条：深评补账只回写了四维分数，没回写依据。
        用户在面板上看到「值得投 64」，展开却没有任何一句说明为什么。
        """
        bad = [f"{t[:24]}（{v}）" for t, v, b in _all_ranked()
               if b and not (b.get("依据") or "").strip()]
        self.assertEqual(bad, [],
                         "这些岗有评分明细却没有一句依据，面板上只有数字：\n  "
                         + "\n  ".join(bad[:20]))


def _seen():
    ptr = ROOT / ".active_user"
    if not ptr.is_file():
        raise unittest.SkipTest("这个 clone 里没有活动用户")
    sj = (ROOT / "users" / ptr.read_text(encoding="utf-8").strip()
          / "job_scraper" / "seen_jobs.json")
    if not sj.is_file():
        raise unittest.SkipTest("这个 clone 里没有真实职位数据")
    return json.loads(sj.read_text(encoding="utf-8"))["seen"]


def _real_entries():
    """**只返回带技能分的条目**——判词天花板要拿技能档当上限，没有技能分就无从判起。

    ⚠️ 别把「每条判词都该满足」的守卫挂在这个取样上：它在真实库里只覆盖
    366/1246（29%），剩下 880 条静默漏过。要覆盖全部就用 `_all_ranked()`。
    2026-08-13 实测踩过：新加的「来源必须存在」挂在这里，抹掉一条的来源做变异
    验证，测试照绿——因为那一条恰好没有技能分。
    """
    out = []
    for e in _seen().values():
        b = e.get("rank_breakdown") or {}
        skill = b.get("技能与经验")
        if isinstance(skill, int):
            out.append((e.get("title") or "", skill,
                        str(e.get("rank_verdict") or ""), b))
    if not out:
        raise unittest.SkipTest("还没有带技能分的评估结果")
    return out


def _all_ranked():
    """**所有落过判词的条目**，不管有没有分数、有没有四维。

    `(标题, 判词, breakdown)`。用于「每条判词都该满足」那一类断言。
    """
    out = [(e.get("title") or "", str(e.get("rank_verdict") or ""),
            e.get("rank_breakdown") or {})
           for e in _seen().values() if (e.get("rank_verdict") or "")]
    if not out:
        raise unittest.SkipTest("还没有任何判词")
    return out


class RealDataHasNoForbiddenCombination(unittest.TestCase):
    """控制测试：真实产出里，判词档不得高于技能档。对老批次同样生效。"""

    def test_verdict_never_exceeds_the_skill_ceiling(self):
        bad = []
        for title, skill, verdict, _ in _real_entries():
            for word, floor in VERDICT_FLOOR.items():
                if word in verdict and skill < floor:
                    bad.append(f"{title[:22]}（技能 {skill} · {verdict}）")
        self.assertFalse(bad, f"判词档高于技能档：{bad}")


if __name__ == "__main__":
    unittest.main()


class TitleOnlyKillsAreFenced(unittest.TestCase):
    """「标题即判据」这条做法必须有明文边界——它在永久结案，实测错误率 20%。

    2026-08-19 拿库里已有 JD 的 5 个此类判定回头验，错了 1 个：某航空制造公司的
    「AI架构师」被当成写代码的岗毙了，而 JD 是「基于成熟大模型 API 打造能力平台、
    推动全流程提效落地」，年包六十多万。翻案后是「可以考虑 64」。

    （公司名与薪资串已脱敏。**它原来是真名**——那家公司在职位库里、不在台账里，
    而查泄漏的守卫只读台账「投过的公司」，看过没投的整类够不着。
    见 `test_no_maintainer_data_in_repo.researched_companies`。）
    """

    def test_the_practice_is_written_down_with_limits(self):
        d = (ROOT / "workflows" / "job-rank.md").read_text(encoding="utf-8")
        self.assertIn("标题即判据", d, "这条做法还没写进流程——它在永久结案")
        self.assertIn("架构师", d, "没点出「架构师」这类两可的词不能只看标题")
        self.assertIn("年包过了底线的一律读 JD", d,
                      "没写「钱够就别只看标题」——错杀一个 63 万的岗比多抓一次 JD 贵得多")

    def test_the_measured_error_rate_is_recorded(self):
        d = (ROOT / "workflows" / "job-rank.md").read_text(encoding="utf-8")
        self.assertIn("20%", d, "没记错误率，下次又会有人当它是零成本的捷径")

    def test_two_way_titles_are_not_closed_permanently(self):
        """两可标题只看标题判掉的，**必须标成待复核**，不能算已定案。

        守的不是「这种判定不存在」——库里有 43 个，它们的 JD 多半还没抓过，
        猎聘又在风控冷却里，今天清不掉。要守的是别的：
        **这类判定不许静默地永久结案。**

        标上 `证据: 未经 JD 正文复核…` 之后，`fetch_details.needs_recheck` 认得它们，
        `python tools/fetch_details.py --recheck --apply` 抓到正文后由 `/job-rank`
        重判（**`--recheck` 是 fetch_details 的参数，`/job-rank` 没有这个 flag**——
        这里原来就写错过，照着敲会敲空）。判词留着（可能本来就是对的），
        但它在队列里看得见——而不是悄悄躺在「跳过」里。

        这 43 个里有 `AI技术负责人 120-150k·15薪`（年包 216-270 万）、
        `Ai-agent 架构师 100-150k·15薪`、`AI技术总监 80-100k·15薪` 这一档。
        按实测 20% 的错判率，静默结案的代价不是抽象的。
        """
        TWO_WAY = ("架构师", "负责人", "专家", "组长", "总监", "主管")
        # 标题里同时写着**明确排除的职能**时，标题确实够判——那不是「两可」。
        # 实测触发者：「…销售总监级 Sales Head/Director」，含「总监」但也含「销售」。
        EXCLUDED_FN = ("销售", "营销", "市场", "渠道", "BD", "人力", "财务", "法务", "采购")
        bad = []
        for title, verdict, bd in _all_ranked():
            if "标题即判据" not in str(bd.get("来源") or ""):
                continue
            if any(w in title for w in EXCLUDED_FN):
                continue
            if not any(w in title for w in TWO_WAY):
                continue
            if "未经" in str(bd.get("证据") or ""):
                continue                     # 已经标了待复核，正是要的状态
            bad.append(f"{title} | {verdict}")
        self.assertEqual(
            bad, [],
            "这些岗的标题两可（架构师/负责人/专家…），只看标题就判了、而且没标待复核"
            "——等于在弱证据上永久结案。给 rank_breakdown 加一条"
            "「证据: 未经 JD 正文复核…」，让 fetch_details --recheck 捞得回来：\n  "
            + "\n  ".join(bad))
