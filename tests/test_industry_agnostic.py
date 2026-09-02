"""这个工具必须对**所有职业**成立，不只是互联网。

用户问过一次「你现在确定不同职业都可以用这个工具吗」。这个文件是那个问题的
可执行答案——每一条都对着一个具体的、会让别的行业用不了的失败方式。

## 已经验过成立的（下面各有对应测试）

- **抽技能词**从候选人自己的资料里抽，不用写死的词表。实测：律师抽出
  「商事争议解决 / 合同审查」、电工抽出「PLC 基础调试 / 配电柜安装」、
  教师抽出「班主任管理 / 学困生辅导」——零硬编码。
- **判断层没有行业词表**。AST 扫 `tools/*.py` 里所有中文字面量列表，只有界面
  标签、停用词、内部词翻译、日期格式、学历阶梯——没有一条是行业词。

## 抓到并修掉的那一条

**薪资折算只认互联网的写法。** 第一版是「数字 = k 或万，按月」，喂进别的行业
常见的写法就产出**看着像数的错数**：

    300-400元/天    → 360-480 万      （产线、建筑、装修按日结）
    25-30元/小时    → 30-36 万        （家教、兼职、家政）
    计件 6000-9000  → 7200-10800 万   （计件工）
    底薪5k+提成      → 6 万，提成没了   （销售、律师、中介、保险）

前三条差两个数量级，第四条把大头整个丢了。而它们都返回**一个正常模样的数字**，
页面照常渲染——静默做错、看起来像成功。
"""

import ast
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import export_web_data as ex  # noqa: E402


class SalaryParsingCoversMoreThanTech(unittest.TestCase):
    """薪资写法按行业差得很远。认不出的宁可不折算，不许编一个数。"""

    #: (说明, 原始串, 期望年包下沿万, 期望上沿万, 该带哪些标记)
    #: 数字是按法定月计薪天数 21.75、每日 8 小时算出来的，不是拍的。
    CASES = [
        # 互联网那几种——这些是回归护栏，改别的别把它们弄坏
        ("月薪 k + 薪数", "25-35k·16薪", 40.0, 56.0, set()),
        ("月薪 k 无薪数", "30-60k", 36.0, 72.0, {"assumed12"}),
        ("月薪写成万", "3.5-5万", 42.0, 60.0, {"assumed12"}),
        ("千万混用", "8千-1.5万", 9.6, 18.0, {"assumed12"}),
        # 产线 / 建筑 / 装修：按日结
        ("日薪带单位", "300-400元/天", 7.8, 10.4, {"estimated"}),
        ("日薪前置写法", "日薪 300-400", 7.8, 10.4, {"estimated"}),
        # 家教 / 兼职 / 家政：按小时
        ("时薪", "25-30元/小时", 5.2, 6.3, {"estimated"}),
        # 传统企业常把元写全
        ("元/月写全", "6000-9000元/月", 7.2, 10.8, {"assumed12"}),
        ("月薪 N 元", "月薪 8000", 9.6, 9.6, {"assumed12"}),
        # 销售 / 律师 / 中介 / 保险：大头在浮动
        ("底薪+提成", "底薪5k+提成", 6.0, 6.0, {"assumed12", "variable"}),
        ("创收分成", "8k+创收分成", 9.6, 9.6, {"assumed12", "variable"}),
        ("计件", "计件 6000-9000元/月", 7.2, 10.8, {"assumed12", "variable"}),
        # 教师 / 事业单位：直接给年薪
        ("年薪", "编制内 8-10万/年", 8.0, 10.0, set()),
    ]

    def test_each_format_converts_sanely(self):
        for name, s, lo, hi, flags in self.CASES:
            with self.subTest(fmt=name, raw=s):
                r = ex.annual_package(s, None)
                self.assertIsNotNone(r, f"{name}「{s}」折算不出来")
                self.assertAlmostEqual(r["low"], lo, places=1,
                                       msg=f"{name}「{s}」下沿不对")
                self.assertAlmostEqual(r["high"], hi, places=1,
                                       msg=f"{name}「{s}」上沿不对")
                got = {k for k in ("assumed12", "estimated", "variable") if r.get(k)}
                self.assertEqual(got, flags, f"{name}「{s}」标记不对")

    def test_unknown_units_are_not_guessed(self):
        """量级靠猜就会差两个数量级。宁可显示「—」，原始串照旧可见。

        `底薪5000` 猜成 5000k 就是 60 万——一个正常模样的、完全错的数。
        """
        for s in ("面议", "薪资面议", "另议", "5000", "8000", "底薪 5000"):
            with self.subTest(raw=s):
                self.assertIsNone(
                    ex.annual_package(s, None),
                    f"「{s}」没有单位，量级只能靠猜——不许猜")

    def test_daily_rate_uses_the_statutory_constant(self):
        """21.75 是法定月计薪天数（劳社部发〔2008〕3 号），不是随手取的 30 或 22。

        取 30 会把日薪岗整体高估 38%，取 22 会低估 1%——前者足以让一个岗
        排到不该排的位置上。
        """
        self.assertAlmostEqual(ex._PAY_DAYS_PER_MONTH, 21.75, places=2)
        r = ex.annual_package("300元/天", None)
        self.assertAlmostEqual(r["low"], round(300 * 21.75 * 12 / 10000, 1), places=1)

    def test_variable_pay_is_flagged_not_swallowed(self):
        """只算底薪却不说，等于告诉销售「这岗只值 6 万」。"""
        r = ex.annual_package("底薪5k+提成", None)
        self.assertTrue(r["variable"], "带提成却没标出来")

    def test_the_ui_shows_the_flags(self):
        """标了不显示等于没标。「+浮动」必须出现在**表格里**，不能只藏在 tooltip。"""
        s = (ROOT / "web" / "src" / "components" / "Shortlist.tsx"
             ).read_text(encoding="utf-8")
        code = re.sub(r"\{/\*.*?\*/\}", " ", s, flags=re.S)
        self.assertIn("annual.variable", code, "界面没读 variable")
        self.assertIn("+浮动", code, "表格里没显示浮动标记")
        self.assertIn("annual.estimated", code, "界面没读 estimated")
        self.assertIn("21.75", code, "没说清估算用的是什么口径")


class RealDataStillConvertsTheSameWay(unittest.TestCase):
    """加行业覆盖不能动到已有结果。"""

    def test_no_regression_on_scraped_formats(self):
        vals = []
        for p in (ROOT / "users").glob("*/job_scraper/seen_jobs.json"):
            try:
                seen = json.loads(p.read_text(encoding="utf-8")).get("seen", {})
            except Exception:
                continue
            for e in seen.values():
                s = (e.get("salary") or "").strip()
                if s:
                    vals.append((s, e.get("salaryMonths")))
        if not vals:
            self.skipTest("本机没有抓取数据")
        # 抓来的串都出自 k / 万 / 万+薪数 这几种口径，全都要算得出来
        bad = [s for s, m in vals
               if re.search(r"[kK千万]", s) and ex.annual_package(s, m) is None]
        self.assertEqual(sorted(set(bad)), [],
                         f"这些平台给的串本来算得出，现在算不出了：{sorted(set(bad))[:6]}")


class NoIndustryWordListsInTheJudgingCode(unittest.TestCase):
    """判断层不许出现行业词表——一出现，这份工具就只服务那一个行业。

    抽技能词已经改成从 `profile/candidate.md` 抽（见 `profile_terms` 的注释：
    第一版把 `Prompt / Agent / RAG / Dify / Cursor` 写死在代码里，对当时那位 AI
    产品候选人好用，换成护士、律师、财务就全空）。这条测试防它回潮。
    """

    #: 一旦出现在 `tools/*.py` 的字面量列表里，就说明有人又写死了行业词
    INDUSTRY_WORDS = [
        "产品经理", "运营", "算法", "前端开发", "后端开发", "测试工程师",
        "护士", "医生", "律师", "会计", "教师", "电工", "销售",
        "Prompt", "RAG", "Agent", "Dify", "Coze", "Cursor", "LLM",
        "Python", "Java", "SQL", "Docker", "GitHub", "Kaggle",
    ]

    #: 开发侧检查工具不属于「判断层」——它们不读任何人的资料，也不给职位打分。
    #: 排除它们不是为了让测试变绿：`lint_skills.py` 里那个 `"Agent tool"` 是
    #: **Claude Code 的能力名**（AGENTS.md 能力对照表里的一行），不是 AI 行业的
    #: 「智能体」。同字不同义，硬算进来就是误报。
    #: 下一条测试会验这个排除是不是真的成立。
    DEV_SIDE = {"lint_skills.py", "security_guards.py"}

    #: 判断层的标志：**去拼路径读**这些文件，而不是只提到文件名
    USER_DATA_FILES = ("candidate.md", "seen_jobs.json", "job_search_tracker.csv")

    @classmethod
    def _reads_user_data(cls, src: str) -> list:
        """有没有 `<某个根> / "candidate.md"` 这种拼路径的写法。

        判据不能是「源码里出现这个文件名」：`security_guards.py` 的
        `REQUIRED_IGNORE_RULES` 里就列着 `job_search_tracker.csv`——那是在检查
        它有没有被 gitignore，从头到尾没读过它。同一个误报形状在
        `test_cli_contract` 里也踩过一次。
        """
        return [ast.unparse(n) for n in ast.walk(ast.parse(src))
                if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Div)
                and isinstance(n.right, ast.Constant)
                and n.right.value in cls.USER_DATA_FILES]

    def test_the_dev_side_exclusion_is_real(self):
        """被排除的必须真的不碰候选人/职位数据，否则这个排除就是在掩盖问题。"""
        for name in self.DEV_SIDE:
            with self.subTest(tool=name):
                hits = self._reads_user_data(
                    (ROOT / "tools" / name).read_text(encoding="utf-8"))
                self.assertEqual(hits, [],
                                 f"{name} 会去读用户数据（{hits}），"
                                 "它属于判断层，不该被排除")

    def test_that_exclusion_check_can_actually_fail(self):
        """反查判据有效——拿一个确实读用户资料的工具去跑，必须命中。"""
        hits = self._reads_user_data(
            (ROOT / "tools" / "export_web_data.py").read_text(encoding="utf-8"))
        self.assertTrue(hits, "判据连导出器读 candidate.md 都认不出来，排除检查是空的")

    def test_no_hardcoded_industry_vocabulary(self):
        bad = []
        for f in sorted((ROOT / "tools").glob("*.py")):
            if f.name in self.DEV_SIDE:
                continue
            src = f.read_text(encoding="utf-8")
            for n in ast.walk(ast.parse(src)):
                if not isinstance(n, (ast.Set, ast.List, ast.Tuple)):
                    continue
                vals = [e.value for e in n.elts
                        if isinstance(e, ast.Constant) and isinstance(e.value, str)]
                for v in vals:
                    for w in self.INDUSTRY_WORDS:
                        if w == v or (len(vals) >= 3 and w in v):
                            bad.append(f"{f.name}:{n.lineno} 列表里有行业词「{w}」：{v[:34]}")
        self.assertEqual(sorted(set(bad)), [],
                         "判断层写死了行业词——换个行业这块就废了：\n"
                         + "\n".join(sorted(set(bad))))

    def test_skills_come_from_the_candidates_own_file(self):
        """抽词的唯一来源是候选人自己的资料。"""
        src = (ROOT / "tools" / "export_web_data.py").read_text(encoding="utf-8")
        fn = src[src.index("def profile_terms("):]
        fn = fn[:fn.index("\ndef ", 1)]
        self.assertIn('"profile" / "candidate.md"', fn,
                      "profile_terms 不是从候选人资料里抽的")

    def test_stop_words_carry_no_industry_terms(self):
        """停用词表只能放通用的中文结构词。放一个行业词进去，那个行业就被削了。"""
        for w in ex._STOP:
            with self.subTest(word=w):
                self.assertLessEqual(
                    len(w), 4, f"停用词「{w}」太长，像个行业词而不是结构词")
                self.assertNotIn(w, self.INDUSTRY_WORDS)


class ExtractionWorksAcrossProfessions(unittest.TestCase):
    """跨职业实测：本机有几个不同职业的资料就跑几个。

    没有那些资料时跳过——这条测的是「换个行业还灵不灵」，不是「本机装了什么」。
    """

    def test_each_profile_yields_its_own_vocabulary(self):
        users = [d.name for d in (ROOT / "users").glob("*")
                 if (d / "profile" / "candidate.md").is_file()]
        if len(users) < 2:
            self.skipTest("本机不足两个用户资料，跨职业测不出来")
        got = {u: ex.profile_terms(u) for u in users}
        empty = [u for u, t in got.items() if not t]
        # 占位符资料抽不出词是正常的，真实资料抽不出就是解析器挑行业了
        real_empty = [u for u in empty
                      if "[YOUR_" not in (ROOT / "users" / u / "profile" /
                                          "candidate.md").read_text(encoding="utf-8")]
        self.assertEqual(real_empty, [],
                         f"这些人的资料一个技能词都抽不出来：{real_empty}")
        # 不同人抽出的词应当**基本不重叠**——重叠高说明抽的是模板词不是本人的
        pairs = [(a, b) for i, a in enumerate(users) for b in users[i + 1:]]
        for a, b in pairs:
            if not got[a] or not got[b]:
                continue
            with self.subTest(pair=f"{a}×{b}"):
                overlap = set(got[a]) & set(got[b])
                self.assertLess(
                    len(overlap), max(2, min(len(got[a]), len(got[b])) // 2),
                    f"{a} 与 {b} 抽出的技能词重叠过多：{sorted(overlap)[:6]}"
                    "——说明抽的是模板里的词，不是各人自己的")


if __name__ == "__main__":
    unittest.main()


class TheFrameworkReadsWhatSetupWrites(unittest.TestCase):
    """`/job-setup` 认真问出来的每一节，评估框架都得有人读。

    五个职业视角的独立审阅里，教师那条抓到最狠的一处：**「明确排除」这一节
    没有任何消费者**。`/job-setup` 问了「有没有什么是你明确不接受的」、写进了
    `candidate.md`，而 `04-job-evaluation.md` 全文引用过「技能」「能力边界」
    「薪资」「求职偏好」「职业目标」「评分权重」「执业资格与证照」——唯独没有它。

    后果：一位教师写下「明确排除：无编制且无转编通道的长期代课岗」，一个编外
    合同制的初中数学岗照样技能维满分、落进「值得投」。
    **用户最明确表达过的那条意愿，是唯一没人读的那条。**
    """

    EVAL = ROOT / "workflows" / "reference" / "04-job-evaluation.md"

    #: `/job-setup` 会写进 candidate.md、且**必须**在评估时被读到的小节
    MUST_BE_CONSUMED = ["明确排除", "执业资格", "能力边界", "评分权重"]

    def test_every_collected_section_has_a_consumer(self):
        t = self.EVAL.read_text(encoding="utf-8")
        missing = [s for s in self.MUST_BE_CONSUMED if s not in t]
        self.assertEqual(missing, [],
                         f"这些小节 /job-setup 会问、会写进资料，但评估框架从没读过：{missing}"
                         "——问了不用，比不问更糟")

    def test_exclusions_are_a_hard_gate(self):
        """排除项是候选人自己下的结论，命中就该出局，不是扣几分。

        锚到**硬门表里那一行**。只查「明确排除」四个字会被下面的专节满足——
        把表行删掉、只剩一节说明，测试照样绿，而一票否决其实已经没了。
        """
        t = self.EVAL.read_text(encoding="utf-8")
        rows = [ln for ln in t.splitlines()
                if ln.startswith("|") and "明确排除" in ln]
        self.assertTrue(rows, "硬门表里没有「候选人自己划的排除项」这一行")
        self.assertIn("排除项", rows[0])

    def test_exclusions_still_need_evidence(self):
        """一票否决仍然只许建立在确凿证据上——排除项也不例外。

        而且排除项恰恰常是对方不会明写的那种（派遣不自称派遣、编外写「参照
        事业单位管理」），所以「确认不了」的处理必须写清楚：FLAG + 进必问清单，
        不能静默 PASS。
        """
        t = self.EVAL.read_text(encoding="utf-8")
        i = t.find("「明确排除」：他自己说了不要的")
        self.assertNotEqual(i, -1, "缺少「明确排除」那一节的正文")
        # **切到下一个小标题，不要数字符。** 原来写死 `t[i:i+1400]`，
        # 2026-08-24 在这一节开头插了一段（「别只读那一节」）之后，
        # 窗口就够不到后面那两句了 —— 测试红了，而它盯的规则一个字没动。
        # 位置无关的判据才盯得住内容。
        nxt = t.find(chr(10) + "### ", i + 1)
        seg = t[i:nxt if nxt != -1 else i + 4000]
        # 光找 "FLAG" 这四个字不够：这一节里另有一处讲模板话时也写 FLAG，
        # 把「证据标准」整条删掉照样能过（2026-08-24 变异实测）。
        # 盯那句话本身。
        self.assertIn("JD 正文能确认命中才 FAIL", seg,
                      "证据门槛那句没了 —— 只是「看着像」也会被判死")
        self.assertIn("→ FLAG", seg, "确认不了的情形没有降级为 FLAG")
        self.assertIn("静默 PASS", seg, "没说清「确认不了不许静默放行」")


class ScoringDocKnowsWhatTheCodeKnows(unittest.TestCase):
    """折算层与打分层不能各知各的。

    `annual_package()` 已经按日薪/时薪/提成/计件分开处理并给出 `estimated`
    / `variable` 标记，面板也显示了。**但分是在 `04-job-evaluation.md` 里打的**
    ——代码改了、那份文档没改，等于展示层知道、打分层不知道。

    三个不同职业的独立审阅（律师、蓝领、教师）同时指出了这一处。
    """

    EVAL = ROOT / "workflows" / "reference" / "04-job-evaluation.md"

    def test_pay_structures_beyond_monthly_salary_are_covered(self):
        t = self.EVAL.read_text(encoding="utf-8")
        for kw, why in [
            ("提成", "销售/律师/中介/保险的大头"),
            ("计件", "产线与加工"),
            ("日薪", "产线/建筑/装修"),
            ("21.75", "日薪折月薪的法定口径"),
            ("包吃住", "制造业里常占实际收入 10-18%"),
            ("公开工资标准", "事业单位/公务员——可算的定值，不是信息缺失"),
        ]:
            with self.subTest(topic=kw):
                self.assertIn(kw, t, f"薪资维没覆盖「{kw}」（{why}）")

    def test_variable_pay_does_not_take_the_band_directly(self):
        """带浮动时只算得出底薪，直接按底薪取档会把提成岗系统性判低。"""
        t = self.EVAL.read_text(encoding="utf-8")
        i = t.find("薪酬结构不止")
        self.assertNotEqual(i, -1, "缺少薪酬结构那一节")
        self.assertIn("不得直接按底薪取档", t[i:i + 1600])

    def test_the_constant_matches_the_code(self):
        """文档里的 21.75 必须和代码里的是同一个数，飘了就两套口径。"""
        self.assertIn(str(ex._PAY_DAYS_PER_MONTH),
                      self.EVAL.read_text(encoding="utf-8"))


class RulesSayWhereTheirExamplesEnd(unittest.TestCase):
    """给了信号词的地方，必须说清「这是示例，按行业现推」。

    `04` 的强度维有这句免责（还专门记了教训：写死词表是「拿错了尺子」），
    而同一份文件的**外包/派遣门没有**——于是那张互联网黑话词表最容易被当成
    完整清单机械套用。蓝领与教师两个视角独立指出：按那张表判，制造业的派遣岗
    和教育的编外岗**全部静默 PASS**，而那正是这道门要拦的东西。
    """

    def test_signal_word_lists_are_marked_as_examples(self):
        t = (ROOT / "workflows" / "reference" /
             "04-job-evaluation.md").read_text(encoding="utf-8")
        # 控制条款：扫描集不许为空。把「信号词按行业现推」那句整个改掉
        # （比如换成「关键词：」）恰恰是本守卫要防的缺陷本身，而那样一改，
        # 下面的循环一次都不跑、断言在零个样本上恒绿——实测就是这么穿过去的。
        hits = [ln for ln in t.splitlines() if "信号词" in ln]
        self.assertGreaterEqual(
            len(hits), 2,
            "框架里「信号词」的提法少于 2 处——多半是词表被改成了"
            "「关键词：」这类不带免责的写法，那正是本守卫要拦的东西")
        for line in hits:
            with self.subTest(line=line.strip()[:40]):
                self.assertTrue(
                    "现推" in line or "示例" in line or "只是例" in line,
                    "给了信号词却没说它只是示例——会被当成完整清单套用：\n"
                    + line.strip()[:150])


class PageCountIsAnUpperBoundNotATarget(unittest.TestCase):
    """内容只有半页的人，被要求「恰好 2 页」时唯一的出路是注水。

    蓝领、设计师、应届生三个视角独立指出同一处：`05` 写「硬性 2 页，不是 1 页」，
    而 `/job-apply` 5d 是硬校验（不满足就重编译直到通过），同时 `05` 又禁止「为凑页数
    删掉诚实标注的缺口」——把人往编内容上逼。本仓库不许自相矛盾。
    """

    def test_the_rule_allows_one_page(self):
        t = (ROOT / "workflows" / "reference" /
             "05-cv-templates.md").read_text(encoding="utf-8")
        self.assertNotIn("硬性 2 页\n\n不是 1 页", t, "还在写死「不是 1 页」")
        self.assertIn("不得为凑页数注水", t)

    def test_apply_checks_an_upper_bound(self):
        t = (ROOT / "workflows" / "job-apply.md").read_text(encoding="utf-8")
        self.assertNotIn("恰好 `简历页数上限` 页", t,
                         "/job-apply 还在按「恰好 N 页」硬校验")
        self.assertIn("不超过 `简历页数上限` 页", t)


class SubmissionMaterialsAreDecidedPerJob(unittest.TestCase):
    """「这个岗要交什么」必须先于「要不要求职信」。

    框架本来就有一个「读 JD 决定这次要交什么」的位置（`/job-apply` 第 1.6 步），
    却**写死成只判一种材料**——而那恰好是设计岗几乎从不要的那一种。

    设计 JD 里近乎标配的「请附作品集，无作品集不予考虑」没有任何一步会读到；
    律所要的代表案例清单、考编要的报名表与资格证扫描件同理。更糟的是第 6 步的
    核对清单会把这次投递逐项打勾报成「全部通过」——**把一份对这个岗根本无效的
    投递，报告为完整**。设计师与律师两个视角独立指出同一处。
    """

    APPLY = ROOT / "workflows" / "job-apply.md"

    def test_the_step_is_about_materials_not_only_cover_letters(self):
        t = self.APPLY.read_text(encoding="utf-8")
        self.assertIn("第 1.6 步：投递材料判定", t,
                      "第 1.6 步还叫「求职信判定」——它只判得了一种材料")
        i = t.index("第 1.6 步：投递材料判定")
        seg = t[i:i + 2600]
        self.assertIn("要求提交的全部材料", seg, "没有「读出全部材料」这一步")
        self.assertIn("求职信", seg, "求职信判定不能丢，它是其中一种材料")

    def test_missing_required_material_is_a_gate_not_a_warning(self):
        """JD 写「无 X 不予考虑」而候选人没有 X，不能照常生成材料然后报通过。"""
        t = self.APPLY.read_text(encoding="utf-8")
        i = t.index("第 1.6 步：投递材料判定")
        seg = t[i:i + 2600]
        self.assertIn("FAIL", seg, "缺件没有接进硬门判定")
        self.assertIn("不要照常往下生成材料然后报通过", seg)

    def test_no_industry_checklist_is_baked_in(self):
        """材料清单按行业写死，就又变成一份永远不全、且暗示用户该是什么职业的表。"""
        t = self.APPLY.read_text(encoding="utf-8")
        i = t.index("第 1.6 步：投递材料判定")
        self.assertIn("不要预设是哪个行业该交什么", t[i:i + 2600])

    def test_the_final_checklist_covers_every_material(self):
        """核对清单里必须逐件交代，否则又会把无效投递报成完整。"""
        t = self.APPLY.read_text(encoding="utf-8")
        self.assertIn("第 1.6a 列出的每一件材料都已交代", t,
                      "核对清单没管材料，仍然只勾求职信")


class LicencesHaveExpiryAndScope(unittest.TestCase):
    """「有这个证」不等于「这个证现在能用在这个岗上」。

    准入资格有**有效期**和**适用范围**，任一不满足，「持有」就不成立——
    而这是 100% 确定的准入失败，不该被处理成「待确认」。

    实测两个形状（蓝领与教师视角各一）：
    - 持证 15 年但复审早已过期的电工，在这道门上**静默 PASS**
      （特种作业操作证 3 年一复审，逾期证书作废、不得上岗）
    - 持初中教资的老师投高中岗，公告只写「具有相应教师资格证」→ 判 FLAG →
      照常打分 → 技能维很高 → 输出「值得投」（初中资格教不了高中）
    """

    EVAL = ROOT / "workflows" / "reference" / "04-job-evaluation.md"

    def test_the_gate_checks_more_than_the_name(self):
        t = self.EVAL.read_text(encoding="utf-8")
        i = t.find("「有这个证」不等于")
        self.assertNotEqual(i, -1, "资格门还是只判名字对不对")
        seg = t[i:i + 2200]
        for kw in ("有效期", "适用范围", "准入", "水平评价"):
            with self.subTest(topic=kw):
                self.assertIn(kw, seg, f"资格门没覆盖「{kw}」")

    def test_unknown_expiry_is_a_flag_not_a_pass(self):
        """资料里没写到期日 → 不许当成通过。静默 PASS 会让人到证件核验那天才知道。"""
        t = self.EVAL.read_text(encoding="utf-8")
        i = t.find("「有这个证」不等于")
        self.assertNotEqual(i, -1, "框架里找不到资格门那一节，锚点变了")
        seg = t[i:i + 2200]
        self.assertIn("没写", seg)
        self.assertIn("FLAG", seg, "缺日期/范围时没有降级为 FLAG")

    def test_setup_actually_asks_for_them(self):
        """评估端要用的字段，采集端得问——否则又是「评估端知道、采集端没问」。

        这正是本轮抓到的另一处形状（强度维按班次运转已在评估端修好，
        而 setup 的四个加班选项一个都装不下倒班）。
        """
        t = (ROOT / "workflows" / "job-setup.md").read_text(encoding="utf-8")
        # 锚**标题**，不锚裸串「Section 4b」：Path C 开头的提问顺序表里也会点到
        # 各小节的名字，裸串会先命中那里，窗口整个偏到别处——断言还在，验的却不是
        # 这一节了。（`tests/jsx.py` 顶上警告过同一个坑，这次是在 md 上又栽一次。）
        i = t.find("### Section 4b")
        self.assertNotEqual(i, -1)
        seg = t[i:i + 1800]
        # 锚到**追问那两句本身**。只查「复审」两个字会被下面那段解释
        # （「特种作业操作证 3 年一复审」）满足——把真正的问句删掉照样绿。
        self.assertIn("这个证有有效期或要复审吗", seg, "/job-setup 没问有效期")
        self.assertIn("它的适用范围是什么", seg, "/job-setup 没问适用范围")

    def test_the_profile_schema_has_a_place_for_them(self):
        """问出来了得有地方放。没有字段就等于没问。"""
        t = (ROOT / "profile.example" / "candidate.md").read_text(encoding="utf-8")
        i = t.find("执业资格与证照")
        self.assertNotEqual(i, -1, "模板里找不到「执业资格与证照」这一节，锚点变了")
        seg = t[i:i + 1600]
        # 锚到**字段行的写法**。只查关键词会被同一段里的举例满足
        # （「长期有效」「准入」在示例行里都出现）——字段说明删掉照样绿。
        self.assertIn("名称 · 类别 · 有效期 · 适用范围", seg,
                      "profile 模板没给出「每条证怎么写」的格式")
        for kw in ("下次复审", "水平评价"):
            with self.subTest(field=kw):
                self.assertIn(kw, seg, f"profile 模板里没有「{kw}」的位置")


class NotEveryJobHasSomeoneToTalkTo(unittest.TestCase):
    """三个渠道的话术全部预设「对面有个会读文案的人」。有一整类投递没有这个人。

    校招网申、考编/事业单位报名系统只收**结构化字段 + 附件**，资格审核是形式审查，
    看证不看文采。而渠道判定原来只有「猎头 / HR 直招」二值——这类岗被硬塞进
    「HR 直招版」，拿到一段 ≤200 字的打招呼开场白，无处可发。
    **规则最细、约束最硬的那个渠道，对它们完全用不上。**
    应届生与教师两个视角独立指出同一处。
    """

    APPLY = ROOT / "workflows" / "job-apply.md"

    def _channel_step(self) -> str:
        t = self.APPLY.read_text(encoding="utf-8")
        i = t.index("## 第 1.5 步：渠道判定")
        return t[i:t.index("## 第 1.6 步", i)]

    def test_it_asks_whether_there_is_anyone_to_talk_to_first(self):
        """锚到**那张判定表**，不是「有没有对话方」这句话。

        那句话在小节标题和引言里各写了一遍，删掉任一处还剩一处——散文满足得了
        关键词断言，满足不了「有一张按投递路径分流的表」。
        """
        seg = self._channel_step()
        rows = [ln for ln in seg.splitlines() if ln.startswith("|")]
        self.assertTrue(
            any("无对话方" in ln for ln in rows)
            and any("有对话方" in ln for ln in rows),
            "渠道判定里没有按投递路径分流的表——还是只判「猎头/HR 直招」二值")
        self.assertLess(seg.index("对话方"), seg.index("isHeadhunter"),
                        "顺序反了：得先判有没有人，再判那个人是谁")

    def test_no_greeting_is_generated_without_a_counterparty(self):
        """没有聊天框却生成开场白，用户会以为还有一步没做。"""
        seg = self._channel_step()
        self.assertIn("不生成", seg, "无对话方时没说清渠道 1 不生成")
        self.assertIn("渠道 3", seg, "没给出这类投递真正该产出的东西")

    def test_the_email_channel_is_offered_too(self):
        """无对话方的四条路径里有「投简历到公共邮箱」—— 那一条的主战场是**邮件**。

        原来这份产出清单只给了渠道 3（网申自评）和渠道 4（求职信），
        **渠道 2（邮件正文）整个缺席**。于是投公共邮箱的岗会拿到一个
        网申自评框的文案，而它根本没有那个框。

        `/job-apply` 第 0 步批量那段早就写着「邮件与网申自评……只有判定为
        『无对话方』（网申表单、考编报名、**公共邮箱**）时才出」——
        **规则在一处写对了，另一处的清单没跟上**（2026-08-21 通读时发现）。
        """
        seg = self._channel_step()
        self.assertIn("公共邮箱", seg, "无对话方的路径里不再列公共邮箱了？")
        self.assertIn(
            "渠道 2", seg,
            "无对话方的产出清单里没有渠道 2（邮件正文）—— "
            "而它自己列的路径里就有「投简历到公共邮箱」，那一条只能靠邮件")

    def test_the_drafting_step_defers_to_the_channel_decision(self):
        """第 2 步不许宣称「生成全部三个渠道」—— 第 1.5a 明说渠道 1 有时不生成。

        照字面做的后果正是 1.5a 要治的那件事：网申与考编岗拿到一段
        无处可发的打招呼开场白。**同一份文件里，一步定了规矩、下一步推翻它。**

        「三渠道」是这套模板的**名字**（`06-outreach-templates.md` 的标题、
        面板类型、导出器都用它），不是「每次都出三份」—— 所以判据盯的是
        「**全部**三个渠道」这种无条件的说法，不是「三渠道」这个词。
        """
        t = self.APPLY.read_text(encoding="utf-8")
        i = t.index("## 第 2 步")
        seg = t[i:t.index("## Step 3", i)]
        # **讲这条规则本身的行要放过**：改对之后正文里留了一段
        # 「这里原来写的是『生成全部三个渠道』」的说明，第一版判据当场
        # 撞上自己的反例。同 `test_no_exact_page_count_in_the_override`
        # 与 `test_status_spelling_is_one_way` 踩过的形状 —— 断言撞上
        # 解释自己的文字，是这个仓库的常客。
        live = chr(10).join(
            ln for ln in seg.splitlines()
            if not ln.lstrip().startswith(">") and "原来" not in ln)
        for claim in ("生成全部三个渠道", "生成全部 3 个渠道", "三个渠道全部生成"):
            self.assertNotIn(
                claim, live,
                f"第 2 步写着「{claim}」，而第 1.5a 说无对话方时渠道 1 不生成 —— "
                "两步互相矛盾，执行者按哪一步做都能自圆其说")
        self.assertIn(
            "1.5a", seg,
            "第 2 步没说清按哪一步的判定生成渠道 —— 那个判定就在 1.5a")

    def test_the_presentation_head_reports_the_path(self):
        """第 1.5a 说判定结果要写进产出物头部 —— 呈现模板原来只报了一半。

        1.5a 的原话：「判定结果（**有无对话方** + 猎头/HR/用人方）写入产出物的头部」。
        而第 6 步那份呈现模板的头部三行里只有「渠道判定：<猎头 / HR 直招>」。

        **一步加了个新维度，下游模板没跟上** —— 同一次通读里这个形状出现了三回：
        1.5a 的产出清单漏了渠道 2、第 2 步仍写「生成全部三个渠道」、
        这里的头部只报猎头/HR。加维度的那一步改对了，被它影响的都没动
        （2026-08-21）。

        判据盯「对话方」这个词出现在头部，不盯具体措辞 —— 换个说法照样成立。
        """
        t = self.APPLY.read_text(encoding="utf-8")
        i = t.index("## 投递话术已生成")
        head = t[i:t.index("### 核对清单", i)]
        # **要有独立的一行**，不能只在「渠道判定」那行的括号里捎带一句。
        # 第一版判据就是只查「head 里有没有『对话方』」，结果把整行删掉之后
        # 它照样绿 —— 因为「渠道判定：…（无对话方时写「不适用」）」也含这三个字。
        # 变异验证当场暴露的（2026-08-21）。
        own = [ln for ln in head.splitlines()
               if ln.startswith("- ") and "对话方" in ln and "猎头" not in ln]
        self.assertTrue(
            own,
            "呈现模板的头部没有独立一行报第 1.5a 的判定（有无对话方），"
            "只报了猎头/HR —— 而网申/考编岗与直聊岗的产出根本不是同一批东西")

    def test_the_outreach_file_header_reports_the_path_too(self):
        """落盘的 `outreach.md` 抬头同样要报第 1.5a 的判定。

        1.5a 说的是「写入**产出物**的头部」——产出物包括落盘那份
        `outreach.md`，它的格式规格在 `06-outreach-templates.md`。
        而 06 的抬头块原来只有「渠道判定」，**且紧接着写着
        「下面这几行是允许的全部」—— 执行者照它做，想补也不许补**。

        同一天在 `/job-apply` 的呈现头部修过一次；这是同一处规定的
        另一个落点（2026-08-21）。

        **2026-08-24 改判据：查内容，不查它占几行。** 原来这条要求「有一行写着
        『对话方』且不含『猎头』」—— 那等于钉死两行的形状。而实测 236 份真实产出
        **一份都没照那个形状写**：它们把两件事并成一行
        （`渠道判定：**有对话方 · 猎聘聊天框（猎头）**`），一行答完，更好。
        06 已经改成只钉内容，这条跟着改 —— 要的是「抬头说了有没有对话方」，
        不是「那句话单独占一行」。
        """
        f = ROOT / "workflows" / "reference" / "06-outreach-templates.md"
        t = f.read_text(encoding="utf-8")
        i = t.index("# <公司> - <岗位> 投递话术")
        head = t[i:t.index("## 打招呼开场白", i)]
        own = [ln for ln in head.splitlines()
               if ln.startswith("- ") and "对话方" in ln]
        self.assertTrue(
            own,
            "06 的抬头块没说「有无对话方」—— "
            "而 /job-apply 1.5a 要求判定结果写进产出物头部")
        self.assertTrue(
            any("猎头" in ln or "直招" in ln for ln in own),
            "抬头说了有无对话方，却没说是猎头还是 HR 直招 —— "
            "1.5a 要的是两件事，实测 110 份只写了前一半")

    def test_the_checklist_says_when_the_greeting_lines_apply(self):
        """无对话方时不出开场白，那几行核对就永远打不了勾。

        一张打不满的清单会被读成「这次投递没做完」。模板里对
        「简历/照片相关行」本来就有这么一句条件说明，开场白那几行漏了。
        """
        t = self.APPLY.read_text(encoding="utf-8")
        i = t.index("### 核对清单")
        seg = t[i:i + 1200]
        self.assertIn(
            "开场白相关", seg,
            "核对清单没说明开场白那几行只在「有对话方」时适用")

    def test_the_fallback_question_offers_the_right_options(self):
        """无法判定时问的那句话，选项里必须包含正确答案。

        原来问的是「猎头发布还是企业 HR 直招？」——对网申/报名制的岗，
        两个选项都不对，用户只能被迫选一个错的。
        """
        seg = self._channel_step()
        i = seg.find("无法判定")
        self.assertNotEqual(i, -1)
        self.assertIn("网申", seg[i:i + 400], "兜底问句里没有第三种可能")


class ClosedApplicationsStopEarly(unittest.TestCase):
    """报名窗口关了才发现，前面整条流水线白做。

    `/job-rank` 有 `deadline`（7 天内 🔥、过期转 expired），但那是**排序加权**，
    只活在 `/job-rank` 里——`/job-apply` 从头到尾不检查报名是否还开着，可以为一个上周
    就截止的岗完整跑完评估、话术、简历编译。

    对平台直聊的岗这最多是白做一次；**对校招与考编，那是这一年唯一的机会**。
    """

    APPLY = ROOT / "workflows" / "job-apply.md"

    def _window_step(self) -> str:
        """只取这一小节。切到固定字符数会吃进相邻小节——相邻的 profile 守卫里
        那句「**停下**并提示先跑 /job-setup」会让「已截止要停下」这条断言在规则被
        删掉之后照样通过。

        （原注释写的是「第 0.5 步紧跟其后」——那时 0.7 排在 0.5 前面，
        **编号顺序与文档顺序相反**。而本类下面那条测试的注释明说
        「比的是步骤编号，不是它在文件里的字节位置」，即编号才是执行顺序。
        两块已对调，现在 0.5 在前、0.7 在后，两种读法一致。
        这里不再写死谁在前后——切片按「下一个 `## ` 一级标题」定界，与顺序无关。）"""
        t = self.APPLY.read_text(encoding="utf-8")
        i = t.index("## 第 0.7 步")
        return t[i:t.index("\n## ", i + 4)]

    def test_there_is_a_window_precheck(self):
        t = self.APPLY.read_text(encoding="utf-8")
        self.assertIn("## 第 0.7 步：投递窗口预检", t, "/job-apply 没有报名窗口检查")

    def test_it_runs_before_the_evaluation(self):
        """放在评估之后就没意义了——白做的正是评估那一段。

        比的是**步骤编号**，不是它在文件里的字节位置：把标题上的编号往后改
        而不挪动位置，按字节比照样通过，而实际执行顺序已经错了。
        """
        t = self.APPLY.read_text(encoding="utf-8")
        import re as _re
        m = _re.search(r"## 第 ([\d.]+) 步：投递窗口预检", t)
        self.assertIsNotNone(m, "窗口预检没有步骤编号")
        self.assertLess(float(m.group(1)), 1.0,
                        f"窗口预检排在第 {m.group(1)} 步——评估在第 1 步，"
                        "排在它之后就救不回白做的那一段")

    def test_a_closed_window_stops_the_workflow(self):
        seg = self._window_step()
        self.assertIn("**停下**", seg, "已截止时没有停下")
        self.assertIn("不要往下评估", seg)

    def test_it_does_not_judge_the_job(self):
        """这一步只回答「来不来得及」，不许顺带下「这岗不值得投」的结论。"""
        self.assertIn("不判断岗位好不好", self._window_step())


class PreInterviewStagesExist(unittest.TestCase):
    """校招淘汰量最大的一关在面试之前，而阶段地图里一行都没有。

    真实漏斗是 网申 → 在线测评 → **笔试·机试** → 技术面 → HR 面。
    原来 `/job-interview` 问 stage 时给的四个选项（phone screen / technical / case /
    final round）没有笔试，学生只能选 `technical`，然后拿到一份按「专业面 +
    STAR 案例」组织的准备包，去应对一场两小时的在线编程考试。
    """

    PREP = ROOT / "workflows" / "reference" / "07-interview-prep.md"
    CMD = ROOT / "workflows" / "job-interview.md"

    def test_the_stage_map_covers_them(self):
        t = self.PREP.read_text(encoding="utf-8")
        for stage in ("在线测评", "笔试", "群面"):
            with self.subTest(stage=stage):
                self.assertIn(stage, t, f"阶段地图里没有「{stage}」")

    def test_the_written_exam_row_says_star_does_not_apply(self):
        """笔试备的是题不是故事。不说清，准备包会照「专业面」那套组织。"""
        t = self.PREP.read_text(encoding="utf-8")
        rows = [ln for ln in t.splitlines() if "笔试" in ln and ln.startswith("|")]
        self.assertTrue(rows, "笔试没有独立的一行")
        self.assertIn("STAR", rows[0], "没说清 STAR 案例在这一关用不上")

    def test_the_command_offers_them_as_choices(self):
        """地图里有、问的时候不给选项，用户还是选不到。"""
        t = self.CMD.read_text(encoding="utf-8")
        i = t.index("**问清楚这次面试是什么**")
        seg = t[i:i + 900]
        for stage in ("在线测评", "笔试", "群面"):
            with self.subTest(stage=stage):
                self.assertIn(stage, seg, f"问 stage 时没给「{stage}」这个选项")

    def test_fresh_grad_hr_questions_are_covered(self):
        """「离职原因」对没工作过的人不成立，而那是 HR 初面那一行的主考察点。"""
        t = self.PREP.read_text(encoding="utf-8")
        rows = [ln for ln in t.splitlines() if "HR 初面" in ln and ln.startswith("|")]
        self.assertTrue(rows)
        self.assertIn("应届生", rows[0], "HR 初面那一行没管没工作过的人")


class WanWithoutAPeriodMarkerIsDisambiguated(unittest.TestCase):
    """「万」不写「/年」时按月算——但数字大到一定程度就只可能是年包。

    `30-60万（含提成）` 按月算是 360-720 万，这个数不存在。销售、地产、金融的
    岗位标题里直接写年包区间是常态，而框架原来一律当月薪，产出一个高 12 倍、
    却长得像正常数字的结果。

    分界不是拍的：本机 72 个当月薪解析的「万」值全部落在 1.2-6 区间；而语义上
    月薪到 10 万（年包 120 万）的岗，招聘页基本都直接写「年薪」或「100-130k·20薪」。
    """

    def test_small_wan_is_still_monthly(self):
        """猎聘给的就是这种，改分界不能把它弄坏。"""
        r = ex.annual_package("3.5-5万", None)
        self.assertAlmostEqual(r["low"], 42.0, places=1)
        self.assertFalse(r.get("estimated"), "确定按月的不该标成推断")

    def test_large_wan_is_read_as_annual(self):
        for s, lo, hi in [("30-60万（含提成）", 30.0, 60.0),
                          ("50-80万", 50.0, 80.0),
                          ("15-25万", 15.0, 25.0)]:
            with self.subTest(raw=s):
                r = ex.annual_package(s, None)
                self.assertAlmostEqual(r["low"], lo, places=1,
                                       msg=f"「{s}」没被读成年包")
                self.assertAlmostEqual(r["high"], hi, places=1)
                self.assertTrue(r["estimated"],
                                "推断出来的年包必须标出来——原文没说按月还是按年")

    def test_the_boundary_matches_the_documented_reason(self):
        """常数改了，注释里那句理由就不成立了——两者必须一起改。"""
        self.assertEqual(ex._WAN_MONTHLY_CEILING, 10)
        src = (ROOT / "tools" / "export_web_data.py").read_text(encoding="utf-8")
        self.assertIn("年包 120 万", src, "没写清这个分界对应的年包量级")

    def test_an_explicit_year_marker_is_not_marked_as_inferred(self):
        """写了「年薪」的是读到的，不是推的，不该标 estimated。"""
        r = ex.annual_package("年薪 30-60万", None)
        self.assertFalse(r["estimated"])

    def test_written_months_veto_the_annual_inference(self):
        """串里写明「N薪」是月薪的铁证——数字再大也不许推成年包。

        「10-15万·13薪」是高管岗的真实写法：按年包读是 10-15 万，
        实际是月薪 ×13 ≈ 130-195 万，差一个数量级。原来的推断只看
        数字大小（≥10 万 → 年包），把薪数这条铁证整个无视了。
        """
        r = ex.annual_package("10-15万·13薪", None)
        self.assertAlmostEqual(r["low"], 130.0, places=0,
                               msg="写了 13 薪还被当成年包 10-15 万")
        self.assertAlmostEqual(r["high"], 195.0, places=0)
        self.assertFalse(r.get("assumed12"))

    def test_the_field_alone_does_not_veto_the_inference(self):
        """薪数只来自 salaryMonths 字段时不否决——字段是详情页另给的，
        证明不了串里那个数是月薪口径；「30-60万」照旧按年包推。"""
        r = ex.annual_package("30-60万", 12)
        self.assertAlmostEqual(r["low"], 30.0, places=1)
        self.assertTrue(r["estimated"])

    def test_the_ui_explains_both_kinds_of_estimate(self):
        """`estimated` 现在有两个来源（日薪折算 / 推断为年包），
        tooltip 只说一种就是在骗另一半的人。"""
        s = (ROOT / "web" / "src" / "components" / "Shortlist.tsx"
             ).read_text(encoding="utf-8")
        self.assertIn("21.75", s, "没说日薪折算的口径")
        self.assertIn("按月还是按年", s, "没说另一种估算来源")


class EducationLadderCoversEveryone(unittest.TestCase):
    """学历阶梯漏掉一档，那一档的用户拿到的是**假装在跑的空规则**。

    原阶梯是 `["不限","大专","本科","硕士","博士"]`——中专/高中/技校/初中全部映射到
    -1，而 `rule_edu` 判 `have < 0` 就 `return None`：一条都不淘汰、也不说一句话。
    本科用户享受得到的学历预筛，一个中专学历的一线店长拿到的是静默空转。

    这是「取值域」层的问题，不是措辞层的——仓库已经把词表、信号词、清单系统性改成
    「按行业现推」，但选项表、阶梯、字段 schema 还保留着「用户有本科学历」的假设。
    """

    def _ps(self):
        import importlib
        return importlib.import_module("prescreen")

    def test_the_ladder_reaches_below_college(self):
        ps = self._ps()
        for lv in ("初中", "高中", "中专", "技校", "职高", "大专", "本科", "硕士", "博士"):
            with self.subTest(level=lv):
                self.assertGreaterEqual(ps.edu_rank(lv), 0,
                                        f"「{lv}」映射不上阶梯，规则会静默空转")

    def test_the_ladder_is_ordered(self):
        ps = self._ps()
        seq = ["初中", "高中", "中专", "大专", "本科", "硕士", "博士"]
        ranks = [ps.edu_rank(x) for x in seq]
        self.assertEqual(ranks, sorted(ranks), f"阶梯顺序不对：{list(zip(seq, ranks))}")

    def test_an_unknown_floor_raises_instead_of_passing_silently(self):
        """认不出**用户自己的**学历时必须报错。

        职位那侧（`eduLevel`）认不出仍然放过——那是平台给的串，脏是常态。
        两侧的处理必须不一样：一侧是数据脏，另一侧是我们的取值域漏了这个人。
        """
        ps = self._ps()
        with self.assertRaises(SystemExit) as cm:
            ps.rule_edu({"eduLevel": "本科"}, "小学")
        self.assertIn("学历阶梯", str(cm.exception), "报错没说清可用的取值")

    def test_a_dirty_job_side_value_still_passes(self):
        ps = self._ps()
        self.assertIsNone(ps.rule_edu({"eduLevel": "全日制统招若干"}, "本科"),
                          "职位侧认不出应当放过，不该淘汰")

    def test_it_actually_filters_for_a_sub_college_user(self):
        ps = self._ps()
        self.assertIsNotNone(ps.rule_edu({"eduLevel": "大专"}, "中专"),
                             "中专用户遇到要求大专的岗，规则该命中")
        self.assertIsNone(ps.rule_edu({"eduLevel": "不限"}, "中专"))


class SetupAsksTheAxisBeforeTheValue(unittest.TestCase):
    """闭合选项会把判据饿死——尺子对了，量程是空的。

    `04` 已经把强度维改成「先判断候选人在哪种工作形态里」，公司性质维也写着
    「上表没有的轴就照他的说法自己建一行」。但 `/job-setup` 第 5 组是写死的单选题，
    保证了那些话永远写不进 `candidate.md`：三班倒的护士只能选「不接受大小周」，
    「只看三甲」「要编制」在公司性质五选一里没有位置。

    而 `setup.md` 自己在 160 行前立过规矩：「任何情况下都不要照抄本文档写死的示例词
    ……会让护士、教师、财务、施工员当场认定这工具不是给他用的」。**文件违反了自己。**
    四个不同职业的独立审阅、跨两轮，都指到这一处。
    """

    SETUP = ROOT / "workflows" / "job-setup.md"

    def _group5(self) -> str:
        t = self.SETUP.read_text(encoding="utf-8")
        i = t.index("#### 第 5 组")
        return t[i:t.index("\n#### ", i + 4)]

    def test_it_asks_the_axis_first(self):
        seg = self._group5()
        self.assertIn("先问轴", seg, "公司性质还是直接给选项")
        self.assertIn("先判形态", seg, "工作强度还是直接给选项")

    def test_the_hints_are_marked_as_hints_not_options(self):
        seg = self._group5()
        self.assertIn("不要念给用户", seg,
                      "提示词没标明「不是选项表」，会被当成单选题念出来")

    def test_the_intensity_forms_match_the_scoring_doc(self):
        """追问什么，要和 `04` 第 3 维的三种形态对齐——两边各说各的就白问了。"""
        seg = self._group5()
        for form in ("按项目", "按班次", "按周期"):
            with self.subTest(form=form):
                self.assertIn(form, seg, f"追问表里没有「{form}」这一形态")

    def test_average_and_peak_are_recorded_separately(self):
        """一年三个月每周 70 小时、其余正点走——用任何一个平均值描述都是错的。"""
        self.assertIn("平均强度与周期峰值要分开记", self._group5())

    def test_the_file_no_longer_contradicts_its_own_rule(self):
        """那条举例规则还在，且第 5 组不再是闭合单选题。"""
        t = self.SETUP.read_text(encoding="utf-8")
        self.assertIn("不要照抄本文档写死的示例词", t, "举例规则被删了")
        seg = self._group5()
        # 「1. X   2. Y   3. Z」这种形状 = 闭合选项表
        import re as _re
        closed = _re.findall(r"^>\s*1\..+2\..+3\.", seg, _re.M)
        self.assertEqual(closed, [],
                         f"第 5 组还有闭合选项表：{closed}")


class DevelopmentDimensionIsIndustryNeutral(unittest.TestCase):
    """四维里唯独这一维没做中立化，而它权重并列最高（25%）。

    原来的四条判据（行业周期 / 是否核心业务线 / 团队状态 / 岗位天花板）量的全是
    **公司/业务线的风险**，默认这个人在一家有业务线、有融资、有裁员周期的公司里
    按职级往上走。医院没有「行业收缩」、科室不是「业务线」；学校看的是有没有高级
    职称的空缺名额；律所看创收与合伙人轨道；门店看能不能带更多店。

    更要紧的是方向会反：非升即走把「聘期—考核—长聘」写得很清晰，按原分档正好命中
    「有明确成长路径」拿 80-100——**风险最高的合同结构被打成最高分**。
    """

    EVAL = ROOT / "workflows" / "reference" / "04-job-evaluation.md"

    def _dim5(self) -> str:
        t = self.EVAL.read_text(encoding="utf-8")
        i = t.index("### 5. 发展与风险")
        return t[i:t.index("\n### ", i + 4)] if "\n### " in t[i + 4:] else t[i:]

    def test_it_derives_the_form_first(self):
        seg = self._dim5()
        self.assertIn("先判断这个人的上升通道是什么形态", seg,
                      "第 5 维还是直接给四条判据，没有形态分支")

    def test_several_progression_forms_are_covered(self):
        seg = self._dim5()
        for form in ("职称阶梯", "合伙人", "门店"):
            with self.subTest(form=form):
                self.assertIn(form, seg, f"上升通道形态里没有「{form}」")

    def test_the_original_four_are_scoped_to_one_form(self):
        """那四条不是错的，是**只在一种形态下成立**。不圈定范围就会继续误用。"""
        self.assertIn("只在这一档成立", self._dim5())

    def test_job_survival_risk_is_separate_from_intensity(self):
        """末位淘汰、开单期限判成「工作强度大」，用户就看不到真正的结论。"""
        seg = self._dim5()
        self.assertIn("岗位存续风险", seg)
        self.assertIn("与「累不累」是两回事", seg)

    def test_it_checks_whether_the_candidate_can_reach_the_next_level(self):
        """「差的是大专学历，两年半能补上」比「你不满足硬性条件」有用得多。"""
        self.assertIn("候选人够不够得到下一级", self._dim5())


class HandsOnStagesAreNotRoleplayedAsInterviews(unittest.TestCase):
    """有一整类关卡是**当场做一遍**，不是回答问题。

    销售的模拟拜访、护士的技能操作考核、教师的试讲、高校的学术报告、技工的上机实操
    ——四个不同职业各有一种，而阶段地图里一行都没有，模拟面 protocol 从头到尾是
    「面试官出题—回答—反馈」的对话循环，**结构上练不了这些**。

    上一轮为笔试写了「备的是题不是故事」，那修的是实例；这一类才是它所属的类。
    """

    PREP = ROOT / "workflows" / "reference" / "07-interview-prep.md"
    CMD = ROOT / "workflows" / "job-interview.md"

    def test_the_stage_map_has_the_class_not_just_one_instance(self):
        t = self.PREP.read_text(encoding="utf-8")
        rows = [ln for ln in t.splitlines() if ln.startswith("|") and "演练" in ln]
        self.assertTrue(rows, "阶段地图里没有「演练 / 实操 / 试讲」这一类")
        # 只看**应对要点那一格**。整行算进去会把阶段名本身（「演练 / 实操 / 试讲」）
        # 当成举例——把行业例子全删光，光靠阶段名就凑够了 3 个，测试照样绿。
        cell = rows[0].strip().strip("|").split("|")[-1]
        forms = [w for w in ("模拟拜访", "操作考核", "试讲", "学术报告", "上机实操")
                 if w in cell]
        self.assertGreaterEqual(len(forms), 3,
                                f"应对要点里只举了 {forms} —— 举例太集中会读成"
                                "「只有那个行业有这一关」")

    def test_star_is_explicitly_ruled_out_there(self):
        t = self.PREP.read_text(encoding="utf-8")
        rows = [ln for ln in t.splitlines() if ln.startswith("|") and "演练" in ln]
        self.assertIn("STAR", rows[0], "没说清 STAR 在这一关用不上")

    def test_the_mock_protocol_branches_before_the_qa_loop(self):
        """分流必须在「出题—回答」循环**之前**，否则那套还是会先跑起来。"""
        t = self.PREP.read_text(encoding="utf-8")
        i = t.index("模拟面 roleplay protocol")
        seg = t[i:i + 2400]
        # 锚到**分流标记本身**的位置。用「演练型」三个字比位置会被解释性文字满足
        # ——变异只改了前一句，标记还在，顺序检查照样通过。
        self.assertIn("下面第 2-6 步整套不适用", seg, "模拟面没有演练关的分流")
        self.assertIn("**先看这一关是不是「演练型」**", seg,
                      "分流的触发句被改掉了，读的人不会知道要先分流")
        self.assertLess(seg.index("下面第 2-6 步整套不适用"),
                        seg.index("从热身问题开始"),
                        "分流排在出题循环之后，那套还是会先跑")

    def test_the_ai_plays_the_counterparty_not_the_interviewer(self):
        t = self.PREP.read_text(encoding="utf-8")
        i = t.index("模拟面 roleplay protocol")
        self.assertIn("扮演的是对手方", t[i:i + 2400],
                      "没说清演练关里 AI 该演谁")

    def test_the_command_lists_it_as_a_choice(self):
        t = self.CMD.read_text(encoding="utf-8")
        i = t.index("**问清楚这次面试是什么**")
        self.assertIn("演练", t[i:i + 900], "问 stage 时没给演练关这个选项")


class PersonalRulingsStayInTheProfile(unittest.TestCase):
    """候选人的个人裁定（连同数值）不进共享的 workflows/ ——它们只住在他自己的资料里。

    2026-08-14 实测泄漏：一位用户把「明确专业清单不含本专业」的处理从硬门放宽为
    减分之后，执行者顺手把**他的**数值写成了共享规则——`job-rank.md` 里出现
    「本仓库活动用户 2026-08-14 的现行裁定：… → 综合分 −5」。多人共用一份 clone，
    下一个用户（专业不同、取舍不同）进来，评估器照着共享文件执行的就是**上一个人**
    的规则。用户当场指出：「其他用户的专业可能不同的，注意规则」。

    正确形态：共享文件只写**怎么去读**（读活动用户 candidate.md 的「明确排除」与
    「补充确认」，没写的走默认），数值一个都不带。
    """

    #: 两份共享文件里谈「候选人裁定」的那一段
    def _ruling_segments(self):
        segs = []
        t04 = (ROOT / "workflows" / "reference" / "04-job-evaluation.md").read_text(
            encoding="utf-8")
        i = t04.find("#### 候选人裁定优先")
        self.assertGreater(i, 0, "04 里「候选人裁定优先」一节没了")
        j = t04.find("### ", i + 10)
        segs.append(("04-job-evaluation.md", t04[i:j if j > 0 else i + 2500]))
        tr = (ROOT / "workflows" / "job-rank.md").read_text(encoding="utf-8")
        i = tr.find("先查候选人自己的裁定")
        self.assertGreater(i, 0, "job-rank 里「先查候选人自己的裁定」那段没了")
        segs.append(("job-rank.md", tr[i:i + 900]))
        return segs

    def test_no_concrete_deduction_value_in_shared_files(self):
        """裁定段里不许出现具体的减分数值——那是某一位用户的取舍。"""
        import re as _re
        for name, seg in self._ruling_segments():
            with self.subTest(file=name):
                m = _re.search(r"[−]\s*\d+|减\s*\d+\s*分", seg)
                self.assertIsNone(
                    m, f"{name} 的裁定段带着具体数值「{m.group(0) if m else ''}」——"
                       "写在这儿就成了强加给所有用户的默认")

    def test_shared_files_say_read_it_from_the_profile(self):
        """共享文件必须写明「数从活动用户的资料里读」，不能只删数不给出处。"""
        for name, seg in self._ruling_segments():
            with self.subTest(file=name):
                self.assertIn("写明的数", seg,
                              f"{name} 没说减分数值从用户资料里读——删了数就没了出处")
