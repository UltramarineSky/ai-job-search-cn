"""框架里声明为「一票否决」的硬性条件，两处枚举里都必须有落点。

## 声明了规则，却没给它留位置

`04-job-evaluation.md` 为两道硬性条件各写了一整节，论证它们**必须独立成门**：

- **「明确排除」** —— 那一节自己就记着这笔账：「这一节原来**没有任何消费者**……
  一位教师写下「明确排除：无编制且无转编通道的长期代课岗」，一个编外合同制的初中
  数学岗照样技能维满分、落进「值得投」。**用户最明确表达过的那条意愿，是唯一没人
  读的那条。**」
- **「执业资格 / 证照 / 职称」** —— 「没有它，能力再强也不能上岗，而且这件事与技能
  水平无关。它必须是一条独立的硬门。」

规则补上了。可**两处真正决定「有没有人填」的枚举都没跟着改**：

| 枚举 | 原来有几项 | 缺 |
|---|---|---|
| `04-job-evaluation.md` 输出模板的硬性条件表 | 5 行 | 执业资格、明确排除 |
| `rank.md` 子代理回传的 `hard_gates` JSON | 4 个键 | 执业资格、明确排除 |

`rank.md` 自己在同一页写着「**这份枚举必须与硬门表逐条对齐**，少一道，批量打分就
整个看不见它」——然后隔二十行的 JSON 就少了两道。它还把道数写死成「the four
vetoing hard gates」，于是后加的那两道连数都对不上。

没有键就没人填，没有行就没人写。规则再对，也只是躺在框架里。

## 判据

每一道能一票否决的硬性条件，都要在**模板的表**和 **`/job-rank` 的回传格式**里各有一处。
新增一道硬门时三处一起改——这条测试保证不会只改框架那一处。
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FRAMEWORK = ROOT / "workflows" / "reference" / "04-job-evaluation.md"
RANK = ROOT / "workflows" / "job-rank.md"

#: 能一票否决的硬性条件。每项给一组可接受的写法——三处的叫法本来就不完全一样
#: （模板写「学历与院校」，JSON 键写「学历院校」），判据认的是**这道门在不在**，
#: 不是字面统一。
#:
#: ⚠️ 工作年限**在**这里：框架的规定是「差 1 年以内 FLAG、明确下限高出 1 年以上
#: FAIL」——它是一道门，只是带缓冲带。本表原来把它整个开除（注释还写着「框架明写
#: 它是 FLAG 不是一票否决」，那句只对了缓冲带那一半），rank 的回传格式于是连键都
#: 没有：「要求 5 年、候选人 3 年」的岗照常打分进短名单，直到 /job-apply 深评才被杀，
#: 正是 rank.md 自己批判的「最贵的环节替最便宜的环节做体检」。
#: 「专业不符」「竞业限制」仍被框架显式排除在硬门之外，不出现在这里——
#: 把纯 FLAG 塞进硬门表，等于把「可以投但要留意」变成「出局」。
GATES = {
    "学历院校": ("学历",),
    "工作年限": ("工作年限", "年限"),
    "户口与落户": ("户口",),
    "应届生与三方": ("应届生",),
    "外包驻场派遣": ("外包", "驻场", "派遣"),
    "执业资格·证照·职称": ("执业资格",),
    "候选人明确排除": ("明确排除",),
}

#: 框架里**明说不是硬门**的，用来做反向控制。
NOT_GATES = ("专业不符", "竞业限制")


def gate_table_rows() -> list:
    """输出模板里那张硬性条件表的行。"""
    t = FRAMEWORK.read_text(encoding="utf-8")
    i = t.index("### 硬性条件检查")
    # 切到**下一个同级标题**，不要写死它叫什么。原来这里硬编码 `### 四维打分`，
    # 那个标题一改（它是给用户看的字，本来就该按 AGENTS.md 的措辞表改）
    # 这里就 ValueError 崩掉——切片的锚点不该绑在一个会改的文案上。
    m = re.compile(r"^### ", re.M).search(t, i + 1)
    blk = t[i:m.start() if m else len(t)]
    return [l for l in blk.splitlines()
            if l.lstrip().startswith("|") and "---" not in l and "门槛" not in l]


def rank_json_keys() -> list:
    """`/job-rank` 子代理回传格式里 `hard_gates` 的键。"""
    m = re.search(r'"hard_gates":\s*\{(.*?)\n  \}', RANK.read_text(encoding="utf-8"), re.S)
    return re.findall(r'"([^"]+)"\s*:', m.group(1)) if m else []


class EveryVetoGateHasASlot(unittest.TestCase):

    def test_both_enumerations_are_found(self):
        """控制用例：两处枚举都抽得到，否则下面两条对着空气跑。"""
        self.assertGreaterEqual(len(gate_table_rows()), 5,
                                "模板里那张硬性条件表找不到或抽空了")
        self.assertGreaterEqual(len(rank_json_keys()), 4,
                                "rank.md 的 hard_gates JSON 找不到或抽空了")

    def test_the_framework_still_declares_them(self):
        """控制用例：这些门确实还写在框架里，否则本测试拦的是不存在的规则。"""
        t = FRAMEWORK.read_text(encoding="utf-8")
        for name, alts in GATES.items():
            with self.subTest(gate=name):
                self.assertTrue(any(a in t for a in alts),
                                f"框架里找不到「{name}」了——它被撤掉了就把本表一起改")

    def test_the_output_template_has_a_row_for_each(self):
        rows = "\n".join(gate_table_rows())
        missing = [n for n, alts in GATES.items() if not any(a in rows for a in alts)]
        self.assertEqual(
            missing, [],
            f"模板的硬性条件表里没有这几道门：{missing}"
            "\n没有行就没人写——框架为它们各写了一整节，评估却产不出那一行。"
            f"\n现有行：\n  " + "\n  ".join(gate_table_rows()))

    def test_the_rank_payload_has_a_key_for_each(self):
        keys = rank_json_keys()
        joined = " ".join(keys)
        missing = [n for n, alts in GATES.items() if not any(a in joined for a in alts)]
        self.assertEqual(
            missing, [],
            f"/job-rank 的 hard_gates 回传格式里没有这几道门：{missing}"
            "\n没有键就没人填。rank.md 自己写着「这份枚举必须与硬门表逐条对齐，"
            "少一道，批量打分就整个看不见它」。"
            f"\n现有键：{keys}")

    def test_flags_are_not_smuggled_in_as_gates(self):
        """反向：框架明说不是硬门的，不许出现在硬门表里。

        把 FLAG 写进一票否决表，等于把「可以投但要留意」变成「出局」——
        比漏一道门更糟，因为它是**静默地**砍掉可投的岗。
        """
        rows = "\n".join(gate_table_rows())
        t = FRAMEWORK.read_text(encoding="utf-8")
        for w in NOT_GATES:
            with self.subTest(word=w):
                self.assertIn(f"{w}**不是硬门", t.replace("### ", ""),
                              f"框架不再声明「{w}」不是硬门了，本条失去依据")
                self.assertNotIn(w, rows, f"「{w}」被写进了一票否决表，而框架说它不是硬门")

    def test_prose_enumerations_list_them_all_too(self):
        """散文里**顺手列一遍**硬门的地方，也得列全。

        `rank.md` 里这套枚举一共有三处：Step 2 的 rubric 说明、硬门预筛那段、
        以及末尾 Important Rules 第 4 条。前两处补齐后，第 4 条仍写着四道——
        **同一个文件里的第三份副本**，而它正是执行者最后读到的那段。

        判据取结构：一行里同时点名「学历」和「外包」，就是在枚举这套门，
        那它必须把每一道都点到。实测全 `workflows/` 只有 3 行符合这个形状，
        判据不会误伤。
        """
        bad = []
        for p in sorted(ROOT.joinpath("workflows").rglob("*.md")):
            for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
                if "学历" not in line or "外包" not in line:
                    continue
                miss = [n for n, alts in GATES.items()
                        if not any(a in line for a in alts)]
                if miss:
                    bad.append(f"{p.relative_to(ROOT).as_posix()}:{i} 缺 {miss}")
        self.assertEqual(
            bad, [],
            "这些地方列了硬性条件却没列全：\n  " + "\n  ".join(bad)
            + "\n列一半比不列更糟——执行者会以为那就是全部。")

    def test_rank_does_not_hardcode_a_gate_count(self):
        """道数写死过一次「four」，后加的两道就永远对不上。"""
        t = RANK.read_text(encoding="utf-8")
        bad = [l.strip()[:80] for l in t.splitlines()
               if re.search(r"\bthe (four|five|six) vetoing hard gates\b", l)]
        self.assertEqual(
            bad, [],
            "rank.md 又把硬性条件的道数写死了：\n  " + "\n  ".join(bad)
            + "\n写数字就得每加一道门改一次，而漏改是静默的——指向枚举本身。")


if __name__ == "__main__":
    unittest.main()


class EveryGateGetsARow(unittest.TestCase):
    """七道门每道都要有那一行——判不了写「未知」，不是不写。

    「没判」和「表里没有那行」在成品上长得一模一样：用户看到其余全 PASS，
    以为查全了。而前端只按 `state` 过滤、不按门名，**这种漏判在面板上永远不显形**。

    2026-08-20 实测 257 份带硬门表的深评：执业资格 76 份、应届生与三方 73 份、
    户口与落户 72 份整个没有那一行（各约 28%）。
    """

    def test_gate_names_normalise_to_seven(self):
        """门名是自由文本（实测 10+ 种写法），必须能归到七道正规门。"""
        import sys as _sys
        _sys.path.insert(0, str(ROOT / "tools"))
        import _cli
        self.assertEqual(len(_cli.GATES), 7)
        for written, canon in [
            ("外包/驻场", "外包/驻场/派遣"),
            ("外包·驻场·派遣", "外包/驻场/派遣"),
            ("你自己划的排除项", "候选人明确排除"),
            ("执业资格·证照·职称", "执业资格/证照/职称"),
        ]:
            with self.subTest(written):
                self.assertEqual(_cli.gate_of(written), canon)
        self.assertEqual(_cli.gate_of("同城通勤时长"), "",
                         "通勤不是硬门，不许被收进七道里")

    def test_the_rule_is_written_down(self):
        t = (ROOT / "workflows" / "reference" /
             "04-job-evaluation.md").read_text(encoding="utf-8")
        self.assertIn("判不了写「未知」，不是不写", t)
        self.assertIn("在面板上永远不显形", t,
                      "没写清为什么这种漏判自己不会冒头")

    def test_the_audit_watches_it(self):
        import sys as _sys
        _sys.path.insert(0, str(ROOT / "tools"))
        import audit_pipeline as audit
        self.assertTrue(any("硬门" in n for n, _ in audit.CHECKS),
                        "审计里没有「七道每道都要判」这一项")


class TheAuditReportsEveryMissingGate(unittest.TestCase):
    """审计报「漏判硬门」时**不许只报前几名**。

    ## 报告自己在少报

    2026-08-21 实测：这条检查写着 `missing.most_common(3)`，
    于是它只报最严重的三道，而真实情况是**七道门每一道都至少漏过一次**。
    被截掉的四道里有「**候选人明确排除**」（13 份）——
    而 `04-job-evaluation.md` 专门为它写过一节，那一节的原话是：

    > 「**用户最明确表达过的那条意愿，是唯一没人读的那条。**」

    它于是又成了唯一没被报出来的那道。

    一共只有七道门，截到三道省不下几个字，代价却是**报告本身在少报**——
    读的人会以为只有三道有问题。这正是这个仓库反复在治的形状：
    **少报比没有判据更坏，它让人以为已经清干净了。**

    ## 判据

    造五份深评、每份的硬门表只列两道，**真跑一次这条检查**，
    看它报出来的那句话里七道是不是都点了名。**不比源码、不看常量。**
    """

    #: 只列两道的硬门表 —— 其余五道都算「整个没有那一行」
    TABLE = "\n".join([
        "## 硬性条件",
        "",
        "| 门槛 | JD 原文 / 判据 | 判定 |",
        "|---|---|---|",
        "| 学历与院校 | JD 写「学历不限」 | PASS |",
        "| 工作年限 | JD 写「经验不限」 | PASS |",
    ])

    def test_it_names_all_seven_not_just_the_top_three(self):
        import sys as _sys
        import tempfile

        _sys.path.insert(0, str(ROOT / "tools"))
        import _cli
        import audit_pipeline as audit

        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            apps = tmp / "users" / "张三" / "documents" / "applications"
            for i in range(5):
                d = apps / f"某公司_岗位{i}"
                d.mkdir(parents=True)
                (d / "evaluation.md").write_text(self.TABLE, encoding="utf-8")
            (tmp / ".active_user").write_text("张三", encoding="utf-8")

            saved = audit.ROOT
            audit.ROOT = tmp
            try:
                out = audit.check_every_gate_is_judged({}, {})
            finally:
                audit.ROOT = saved

        self.assertTrue(out, "五份深评各缺五道门，审计却一声不吭")
        msg = out[0][2]
        missing_from_report = [g for g in _cli.GATES
                               if g not in ("学历与院校", "工作年限")
                               and g not in msg]
        self.assertEqual(
            missing_from_report, [],
            "审计截断了，这几道漏判没被报出来 —— **少报比没有判据更坏**，"
            f"读的人会以为只有报出来的那几道有问题：{missing_from_report}\n"
            f"报告原文：{msg}")

    def test_a_missing_table_is_not_dropped_from_the_denominator(self):
        """**一道门都没判的那份，正是这条检查存在的理由。**

        原来循环里是 `if not gates: continue` —— 整张表都没有的既不进分子
        也不进分母，在唯一为它写的检查里彻底隐形；而分母缩水之后，
        决定 warn 还是 error 的那个比例也跟着算错。
        实测 2026-08-25 活动用户：276 份里 11 份没有硬门表，全带可投档位。
        """
        import sys as _sys
        import tempfile

        _sys.path.insert(0, str(ROOT / "tools"))
        import _cli
        import audit_pipeline as audit

        rows = ["## 硬性条件", "", "| 门槛 | JD 原文 / 判据 | 判定 |", "|---|---|---|"]
        rows += [f"| {g} | 依据 | PASS |" for g in _cli.GATES]
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            apps = tmp / "users" / "张三" / "documents" / "applications"
            for i in range(3):
                d = apps / f"某公司_全判过{i}"
                d.mkdir(parents=True)
                (d / "evaluation.md").write_text("\n".join(rows), encoding="utf-8")
            d = apps / "某公司_整张表都没有"
            d.mkdir(parents=True)
            (d / "evaluation.md").write_text(
                "## 结论\n\n**可以考虑**\n", encoding="utf-8")
            (tmp / ".active_user").write_text("张三", encoding="utf-8")
            saved = audit.ROOT
            audit.ROOT = tmp
            try:
                out = audit.check_every_gate_is_judged({}, {})
            finally:
                audit.ROOT = saved

        self.assertTrue(out, "一份连硬门表都没有，审计却一声不吭")
        msg = out[0][2]
        self.assertIn("4 份深评", msg, "分母漏了没有硬门表的那份")
        self.assertIn("其中 1 份连硬门表都没有", msg,
                      "最坏的那个形状要点名说出来，不能混在七道的计数里")

    def test_a_clean_set_reports_nothing(self):
        """反向：七道都判了就不该报，否则这条检查是噪音。"""
        import sys as _sys
        import tempfile

        _sys.path.insert(0, str(ROOT / "tools"))
        import _cli
        import audit_pipeline as audit

        rows = ["## 硬性条件", "", "| 门槛 | JD 原文 / 判据 | 判定 |", "|---|---|---|"]
        rows += [f"| {g} | 依据 | PASS |" for g in _cli.GATES]
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            d = tmp / "users" / "张三" / "documents" / "applications" / "某公司_岗位"
            d.mkdir(parents=True)
            (d / "evaluation.md").write_text("\n".join(rows), encoding="utf-8")
            (tmp / ".active_user").write_text("张三", encoding="utf-8")
            saved = audit.ROOT
            audit.ROOT = tmp
            try:
                self.assertEqual(audit.check_every_gate_is_judged({}, {}), [],
                                 "七道都判了却还在报")
            finally:
                audit.ROOT = saved


class ThePanelDoesNotCallPartialAllClear(unittest.TestCase):
    """只判了四道门时，页面不许印「这些条件都核对过了，没有要问的」。

    `GateGrid` 早有一条守卫挡住「整张表为空却报全部通过」——那是这一页最危险的错。
    但**部分缺行**从它下面漏过去了：表在、行也在，只是七道里少了三道，
    `unknown`/`assumed` 都是 0，于是照旧印那句全清。

    2026-08-20 实测：236 个岗印着这句话，其中 **60 个实际有 2-3 道门没查**
    （执业资格、户口、应届生是重灾区，各约 28%）。
    局部的谎比整张表为空更难发现——用户看得到一张像模像样的表。

    判据放在导出器（`_cli.GATES` 归一化后算 `gatesNotJudged`），
    TS 侧不重写：重写就会飘。
    """

    def test_exporter_computes_unjudged_gates(self):
        import sys as _sys
        _sys.path.insert(0, str(ROOT / "tools"))
        import export_web_data as ex
        src = (ROOT / "tools" / "export_web_data.py").read_text(encoding="utf-8")
        self.assertIn("gatesNotJudged", src, "导出没算「缺哪几道」")
        self.assertIn("_cli.gate_of", src, "没走统一的门名归一化")

    def test_every_job_with_gates_carries_the_field(self):
        """带硬门表的岗都要有这个字段——缺省会被前端当成「都判过」。"""
        import json
        f = ROOT / "web" / "public" / "data.json"
        if not f.is_file():
            self.skipTest("还没导出过")
        jobs = json.loads(f.read_text(encoding="utf-8"))["jobs"]
        bad = [j.get("title", "")[:20] for j in jobs
               if j.get("gates") and j.get("gatesNotJudged") is None]
        self.assertEqual(bad, [], f"这些岗有硬门表却没带 gatesNotJudged：{bad[:5]}")

    def test_all_clear_line_is_gated_on_it(self):
        c = (ROOT / "web" / "src" / "components" / "GateStamp.tsx").read_text(encoding="utf-8")
        self.assertIn("notJudged.length === 0", c,
                      "「都核对过了」那句没把「有几道没判」算进条件")
        self.assertIn("项没核对", c, "没有把缺的那几道说出来")
        self.assertIn("不是「通过」", c, "没说清「没写」不等于「通过」")

    def test_the_field_is_threaded_from_the_job(self):
        r = (ROOT / "web" / "src" / "components" / "JobReadout.tsx").read_text(encoding="utf-8")
        self.assertIn("notJudged={job.gatesNotJudged}", r, "字段没传进 GateGrid")
