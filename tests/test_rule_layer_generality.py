"""规则层的通用性：规则里不许藏「用户是谁」的假设。

## 这个测试在防什么

本仓库反复出现同一种缺陷，形态各异但根子一样：**把「手上这个样本长什么样」
误当成「规则该是什么样」**。已经清掉过写死词表、拿一个人的分数分布凑阈值、
行业专属的维度名、示例、脚手架小节名……

所以检验标准只有一条，对每条规则都问一遍：

    换一个完全不同职业的用户来用，这条还成立吗？

不成立的三种典型：
- 硬门表只有学历，没有**执业资格**——可医生、律师、会计、教师、电工的第一道门是执照，
  而且缺证是能去考的，判成「技能不匹配」等于把可行动的事实说成不可行动的结论
- 工作强度的判据写死成某一行的黑话——换个行业 JD 里一个词都不会出现，这一维
  （占 20% 权重）就静默全标「未知」
- 权重 30/25/20/25 当成事实——它其实是一种取舍，背房贷的人和求稳定的人排序相反

这些都**不是**从某个用户的数据里发现的，是拿上面那把尺子量出来的。
"""

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

FRAMEWORK = ROOT / "workflows" / "reference" / "04-job-evaluation.md"
SETUP = ROOT / "workflows" / "job-setup.md"
TEMPLATE = ROOT / "profile.example" / "candidate.md"


class LicensureIsAFirstClassGate(unittest.TestCase):
    """执业资格必须是独立硬门，不能"按技能维沉底、效果一样"。

    不一样的地方有三处，每处都影响用户能不能行动：
      1. 硬门出局且**不给分**；技能沉底会带着一个数字留在排序里
      2. 硬门显示在面板的「硬性条件」格里，能看到缺的是哪一项
      3. 缺证能去考，缺能力不能——判错了类别，可行动的事实就丢了
    """

    def test_framework_has_a_licensure_gate_row(self):
        t = FRAMEWORK.read_text(encoding="utf-8")
        self.assertRegex(t, r"\*\*执业资格[^\n]*\*\*\s*\|",
                         "硬门表里没有执业资格这一行")
        self.assertIn("准入", t, "没说清它是准入资格、不是技能高低")

    def test_licensure_uses_the_same_evidence_tiers(self):
        """必须 → FAIL，优先 → FLAG。和其它硬门一个标准，不能更松也不能更严。"""
        t = FRAMEWORK.read_text(encoding="utf-8")
        seg = t[t.index("执业资格 / 证照 / 职称：把"):]
        seg = seg[:2000]
        self.assertIn("FAIL", seg)
        self.assertIn("FLAG", seg)
        self.assertIn("优先", seg, "没区分「必须」和「优先」——套话会误杀")

    def test_setup_asks_about_licensure(self):
        """改了框架不改问的地方 = 这一节永远是空的。"""
        t = SETUP.read_text(encoding="utf-8")
        self.assertIn("执业资格", t, "/job-setup 从不问执业资格，那一节永远填不上")

    def test_template_has_a_place_to_write_it(self):
        """改了问的地方不改写入的模板，也是白问。"""
        self.assertIn("## 执业资格与证照", TEMPLATE.read_text(encoding="utf-8"))

    NAMED = ["护士执业", "执业医师", "法律职业资格", "注册会计师",
             "教师资格", "一级建造师", "执业药师", "特种作业"]

    def test_framework_does_not_require_any_named_qualification(self):
        """不许把某个具体资格写成**要求**——那既不会全，又暗示用户该是什么职业。

        判的是它出现在什么位置，不是出现没出现：

        - **规范性位置**（门的判据行、`- **X：**` 这类要求条目）出现 = 内置清单，禁止。
        - **举例位置**（说明某条规则长什么样）出现 = 允许，但要跨行业，见下一条。

        原来这条是全文禁止任何一个资格名。那把「证有有效期和适用范围」这条规则
        逼成了一句抽象话——AI 读到 JD 写「具有相应教师资格证」时，不会知道要去比
        学段。**「初中教师资格不能任教高中」这个例子本身就是规则的可执行部分。**
        真正要防的是「框架替用户列出他该有哪些证」，而那种东西只长在规范性位置。
        """
        t = FRAMEWORK.read_text(encoding="utf-8")
        # 规范性位置 = **硬门表本身的行**，以及资格门那张「JD 措辞 → 判定」表。
        # 两张表都按表头定位、取到第一个空行为止。
        #
        # 用「行长得像 `| **X** |`」来判是分不开的：讲有效期/适用范围/类别的那张
        # 说明表，每行也是 `| **有效期 / 复审** | … |`。它们的差别在**表头**，
        # 不在行的形状——`| 门槛 | FAIL 的判据 |` 是要求，`| 维度 | 意思 | 例 |` 是说明。
        normative = []
        for header in ("| 门槛 | FAIL 的判据 | 注意 |", "| JD 措辞 | 判定 |"):
            if header not in t:
                continue
            seg = t[t.index(header):]
            normative += seg[:seg.index("\n\n")].splitlines()
        # `- **X：**` 这类要求条目同样算规范位置
        normative += [ln for ln in t.splitlines() if ln.strip().startswith("- **")]
        self.assertTrue(normative, "一条规范性行都没解析到")

        bad = []
        for s in normative:
            for w in self.NAMED:
                if w in s:
                    bad.append(f"「{w}」 {s.strip()[:60]}")
        self.assertEqual(sorted(set(bad)), [],
                         "框架把具体资格写进了要求位置——那是在替用户列清单：\n"
                         + "\n".join(sorted(set(bad))))

    def test_named_qualifications_only_appear_as_multi_trade_examples(self):
        """举例可以，但**不许只举一个行业的**——那才是「暗示用户该是什么职业」。"""
        t = FRAMEWORK.read_text(encoding="utf-8")
        hit = {w for w in self.NAMED if w in t}
        if not hit:
            self.skipTest("框架里一个具体资格都没提，本条不适用")
        self.assertGreaterEqual(
            len(hit), 3,
            f"框架只提了 {sorted(hit)} —— 举例太集中会读成「这工具是给那个行业的」，"
            "要么多举几个不同行业的，要么一个都不举")


class IntensitySignalsAreDerivedNotHardcoded(unittest.TestCase):
    """强度这一维占 20% 权重，判据却曾是某一行的黑话。

    换个按班次运转的岗位，那些词一个都不会在 JD 里出现，于是整维静默标「未知」
    ——不是没信息，是拿错了尺子。
    """

    JARGON = ["大小周", "奋斗者", "弹性加班"]

    def test_no_industry_jargon_as_the_signal_list(self):
        """只看**规范性正文**，跳过 `>` 引用块。

        引用块里记的是「当初为什么错」——那段必须留着（本仓库的规矩：修正要连
        原因一起写进文档，否则会被改回去），但它引用旧词表只是为了说明问题，
        不是在规定判据。测试若不区分这两者，就会逼着文档把教训删掉。
        """
        t = FRAMEWORK.read_text(encoding="utf-8")
        seg = t[t.index("**工作强度信号词"):][:1400]
        rules = "\n".join(ln for ln in seg.splitlines()
                          if not ln.lstrip().startswith(">"))
        for w in self.JARGON:
            self.assertNotIn(
                w, rules,
                f"强度判据里还写死着「{w}」——换个行业这条规则就静默失效")

    def test_it_tells_you_to_derive_from_the_candidate(self):
        t = FRAMEWORK.read_text(encoding="utf-8")
        seg = t[t.index("**工作强度信号词"):][:1400]
        self.assertIn("candidate.md", seg, "没说从候选人资料推导")
        self.assertIn("未知", seg, "「JD 不提就标未知」这条不能丢")

    def test_company_nature_table_admits_it_is_not_exhaustive(self):
        """所有权/融资阶段只是一条轴。用工形式、公私、层级都可能更要紧。"""
        t = FRAMEWORK.read_text(encoding="utf-8")
        seg = t[t.index("**公司性质**"):][:1800]
        self.assertIn("不是全集", seg, "那张表被当成了全集")
        self.assertIn("编制", seg, "没提到用工形式这条轴（对体制内求职者最要紧）")


class WeightsAreAChoiceNotAFact(unittest.TestCase):

    def test_weights_can_be_overridden_per_candidate(self):
        t = FRAMEWORK.read_text(encoding="utf-8")
        self.assertIn("权重", t)
        seg = t[t.index("### 权重："):][:1600]
        self.assertIn("candidate.md", seg, "没说权重可以从候选人资料读")
        self.assertIn("100", seg, "没规定四项之和")

    def test_the_cost_of_custom_weights_is_stated(self):
        """调权的代价是跨用户不可比。不写出来，用户会拿两个人的分数互相比。"""
        seg = FRAMEWORK.read_text(encoding="utf-8")
        seg = seg[seg.index("### 权重："):][:1600]
        self.assertIn("可比", seg, "没说明调权后分数不再跨用户可比")

    def test_template_has_a_weights_section(self):
        self.assertIn("## 评分权重", TEMPLATE.read_text(encoding="utf-8"))

    def test_setup_offers_it_but_does_not_push(self):
        t = SETUP.read_text(encoding="utf-8")
        self.assertIn("评分权重", t, "/job-setup 不问权重，那一节永远是默认值")


class PrescreenDoesNotInventScores(unittest.TestCase):
    """预筛连 JD 都没读，就不该产出总分。

    框架算总分是 技能×0.30 + 薪资×0.25 + 强度×0.20 + 发展×0.25。一个技能完全对口、
    薪资低于底线的岗，框架约 65（「值得投」），预筛却写常数 25（「不建议」）——
    差 40 分、差两个档位，而这个数会上面板、参与排序。
    `None` 才是诚实的：和硬门 FAIL 一样表示「已结案、未评分」。
    """

    def test_no_numeric_score_constants_in_the_rule_table(self):
        src = (ROOT / "tools" / "prescreen.py").read_text(encoding="utf-8")
        seg = src[src.index("OBJECTIVE, INFERRED ="):]
        seg = seg[:seg.index("hits: list")] if "hits: list" in seg else seg[:1200]
        nums = re.findall(r"rules\.append\(\([A-Z]+, \"[^\"]+\", (\w+),", seg)
        self.assertTrue(nums, "没解析到规则表——测试锚点失效了")
        self.assertEqual(set(nums), {"None"},
                         f"预筛仍在编造分数 {nums} —— 它没算过四维，不该产出总分")

    def test_closing_a_case_writes_no_score(self):
        import json
        import tempfile
        import prescreen as ps
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            u = tmp / "users" / "张三" / "job_scraper"
            u.mkdir(parents=True)
            (tmp / ".active_user").write_text("张三", encoding="utf-8")
            sj = u / "seen_jobs.json"
            sj.write_text(json.dumps({"seen": {"u1#岗": {
                "title": "岗", "url": "u1", "company": "某公司",
                "status": "new", "salary": "6-7k"}}}, ensure_ascii=False),
                encoding="utf-8")
            saved = ps.ROOT
            try:
                ps.ROOT = tmp
                ps.main(["--annual-floor", "42", "--user", "张三", "--apply"])
                e = json.loads(sj.read_text(encoding="utf-8"))["seen"]["u1#岗"]
            finally:
                ps.ROOT = saved
        self.assertEqual(e["status"], "ranked")
        self.assertIsNone(e["rank_score"], "结案却编了一个分数出来")


if __name__ == "__main__":
    unittest.main()


class GatesAllFireOnSomeProfession(unittest.TestCase):
    """框架的每一道硬门，都要能被**某个职业**真实触发——否则它是纸面规则。

    跨职业走查（AI 产品 / 护理 / 应届生 / 律师 / 电工 / 教师）之后，六道门全部
    有真实触发案例：

        学历院校      硕士岗 vs 本科候选人（应届生、教师）
        工作年限      社招「3-5年」vs 应届无全职（应届生）
        户口与落户    JD 明写「限本市户籍」vs 外地生源（应届生）
        应届生与三方  JD 写「2025 届及以前」vs 2026 届（应届生）
        外包/驻场     人力资源服务公司 + 派遣（应届生、电工）
        执业资格      高压电工证 / 高中教师资格证（电工、教师）

    这条测试只钉住**门的定义仍然齐全且互不重复**；能不能触发由上面那轮走查负责，
    结论记在这里，防止有人把某道门当成「没人用」删掉。
    """

    GATES = ["学历与院校", "工作年限", "户口与落户", "应届生身份与三方协议",
             "外包 / 驻场 / 劳务派遣", "执业资格 / 证照 / 职称"]

    def test_every_gate_row_still_exists(self):
        t = FRAMEWORK.read_text(encoding="utf-8")
        for g in self.GATES:
            with self.subTest(gate=g):
                self.assertIn(f"**{g}**", t, f"硬门「{g}」从表里消失了")

    #: 具体职业的资质名。出现在**门的定义**里 = 框架内置了一份资格清单
    NAMED_QUALIFICATIONS = ["电工证", "教师资格", "护士执业", "律师执业",
                            "CPA", "建造师", "执业药师", "特种作业"]

    def test_no_gate_row_presumes_an_industry(self):
        """**门的定义**（表里那几行）必须是跨职业成立的类别，不能点名具体资质。

        判的是**表行**，不是整节正文。原来扫的是从表头到下一个二级标题之间的全部
        文字，于是给「有效期 / 适用范围」举例（电工证 3 年复审、初中教资教不了高中）
        也会被判违规——而那些例子恰恰是**跨多个行业各举一个**，正是这条守卫要防的
        失败模式的反面。真正要拦的是「框架内置一份该有哪些证的清单」，
        那种东西只会长在门的定义里。正文里的例子由下一条测试管。
        """
        t = FRAMEWORK.read_text(encoding="utf-8")
        # 只取**硬门表本身**：表头到第一个空行。范围放宽到「表头之后的整节」时，
        # 下面讲有效期/适用范围的那张表也会被当成门的定义扫进来——那张表的行是
        # 「有效期」「适用范围」「类别」，本来就该举具体例子。
        head = t[t.index("| 门槛 | FAIL 的判据 | 注意 |"):]
        head = head[:head.index("\n\n")]
        rows = [ln for ln in head.splitlines()
                if ln.startswith("|") and "**" in ln]
        self.assertGreaterEqual(len(rows), 6, "硬门表没解析全")
        for ln in rows:
            for w in self.NAMED_QUALIFICATIONS:
                with self.subTest(row=ln[:24], word=w):
                    self.assertNotIn(
                        w, ln,
                        f"硬门表某一行点名了具体职业的资质「{w}」——那该由候选人资料提供")

    def test_examples_in_the_gate_prose_span_several_trades(self):
        """正文里可以举例——但**不许只举一个行业的**。

        举一个行业的例子，读的人就会以为这工具是给那个行业用的；举三四个不同的，
        它才读作「你所在的行业也有对应的东西」。这条比「一个例子都不许有」有用：
        完全不举例，「证有适用范围」是一句抽象话，AI 不知道该去 JD 里找什么。
        """
        t = FRAMEWORK.read_text(encoding="utf-8")
        seg = t[t.index("### 执业资格 / 证照 / 职称"):]
        seg = seg[:seg.index("### 候选人自带的硬门")]
        if not any(w in seg for w in self.NAMED_QUALIFICATIONS):
            self.skipTest("这一节没举具体资质的例子，本条不适用")
        hit = {w for w in self.NAMED_QUALIFICATIONS if w in seg}
        self.assertGreaterEqual(
            len(hit), 3,
            f"这一节只举了 {sorted(hit)} —— 举例太集中会读成「这工具是给那个行业的」，"
            "要么多举几个不同行业的，要么一个都不举")


class NoHardcodedPlatformNames(unittest.TestCase):
    """工作流不许写死作品/成果平台的名字——那是在预设用户是哪个行业的人。

    `profile.example` 的这一项早就中性化成「作品集 / 个人主页（可选）」，但
    `/job-expand` 的 Step 1e 仍写着「GitHub Profile —— Look up the GitHub username」，
    全文 8 处点名 GitHub，`/job-setup` 另有 2 处。**模板改了，消费方没跟上**——
    这与「改了 setup 的问法、没改它写入的模板」是同一形状，只是方向反过来。

    对护士、律师、教师、电工，「查一下他的 GitHub」既拿不到东西，也在告诉他
    这工具不是给他用的。真正通用的是**机制**（资料里列了什么就看什么；那个平台
    如果把作品分条目组织，就逐条目深挖），不是平台名字。

    说明性引用块（`>` 开头，记「当初为什么错」）不算——那是教训，按本仓库的
    规矩必须留着。
    """

    PLATFORMS = ["GitHub", "GitLab", "Kaggle", "Behance", "Dribbble",
                 "ResearchGate", "Google Scholar", "Stack Overflow"]

    def test_workflows_do_not_name_platforms(self):
        bad = []
        targets = list((ROOT / "workflows").rglob("*.md"))
        targets.append(ROOT / "profile.example" / "candidate.md")
        for f in sorted(targets):
            for i, ln in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
                s = ln.strip()
                if s.startswith(">"):          # 说明性引用：记教训，保留
                    continue
                for p in self.PLATFORMS:
                    # 大小写不敏感：`expand.md` 的输出模板里写的是全大写 `GITHUB`，
                    # 按 `"GitHub" in s` 精确匹配会**从守卫底下漏过去**——这条守卫
                    # 存在的全部目的就是拦它，却拦不住它自己文件里的那一处。
                    if p.lower() in s.lower():
                        bad.append(f"{f.name}:{i} 「{p}」 {s[:56]}")
        self.assertEqual(bad, [],
                         "工作流里写死了作品平台名——换个职业的用户会拿不到东西，"
                         "而且会觉得这工具不是给他用的：\n" + "\n".join(bad))

    def test_expand_derives_the_source_from_the_profile(self):
        t = (ROOT / "workflows" / "job-expand.md").read_text(encoding="utf-8")
        seg = t[t.index("### 1e."):t.index("### 1f.")]
        self.assertIn("别预设是哪家", seg, "1e 没说清不要预设平台")
        self.assertIn("跳过", seg, "没规定「一个链接都没有」时跳过而不是去猜")
        self.assertIn("条目", seg, "丢掉了「有条目结构就逐条目深挖」这个真正通用的机制")
