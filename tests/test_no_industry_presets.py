"""这个工具不预设用户是哪个行业。

## 规则

用户是什么行业、什么处境，**由 AI 读了他的资料再判断**——`/job-setup` 有 路线 A（文档夹）
和 路线 B（简历导入）正是干这个的。框架**不提供也不需要职业分类**：给出一份清单，
就等于替所有用户做了归类，而清单之外的人会当场认定这工具不是给他用的。

## 这条被违反过六次，形状一模一样

| 在哪 | 错的形状 |
|---|---|
| `resume_insight` 的词表 | 把**一个行业的词汇**（Prompt/Agent/RAG/Dify）当成所有人的 |
| 判词天花板 70/50/30 | 把**一个人的分数分布**当成规则该长的样子 |
| `/job-upskill` 的分档 | 同上 |
| 「技术栈匹配」这个维度名 | 把**一个行业的说法**当成通用术语 |
| `/job-upskill` 的**格式范例** | 主题清单、优先级表、学习条目、搜索查询、顺序表——16 处 Kubernetes / AWS / MLOps，整份是一位 DevOps 工程师的计划 |
| `/job-expand` 的课程清单 | `(Coursera, edX, Udemy, DataCamp, fast.ai)` 六个全是技术方向的 MOOC |

再加两处：`/job-setup` 问卷里写死「比如数据分析、后端开发、产品经理」；简历模板把
「项目经历」当成人人都有的章节、把执业证书压在最后一行。

> 后两条尤其说明「改一处不算改完」：`/job-upskill` 的**分档**上面第三行就记着改过了，
> 例子却原封不动；`/job-expand` 的发现层（1e）和产出层（Step 3）都中性化过，
> 中间那份课程清单和最后的写入层（Step 5）没跟上。**同一个文件里也会漏。**

都是同一件事：**把「手上这个样本长什么样」误当成「规则该是什么样」**。

## 这里钉什么

工作流由 AI 按文档执行，没有可执行实现，所以钉的是规则本身还在、且反例没被写回去。
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

_HEADING = re.compile(r"^(#{1,6})\s+(.*)$")


def _section(text: str, title: str) -> str:
    """取标题为 `title` 的那一节；没有就返回空串。

    与 `tools/doctor.section_of` 同一套找法：**任何标题层级都认、标题按前缀比**。
    实测的教训——真实 `candidate.md` 比模板深一级，标题还可能带括注，写死层级或
    要求一字不差的话，每一节都会「找不到」，而找不到通常是**静默放行**。
    """
    lines = text.splitlines()
    start = depth = None
    for i, ln in enumerate(lines):
        m = _HEADING.match(ln)
        if m and m.group(2).strip().startswith(title):
            start, depth = i, len(m.group(1))
            break
    if start is None:
        return ""
    end = len(lines)
    for j in range(start + 1, len(lines)):
        m = _HEADING.match(lines[j])
        if m and len(m.group(1)) <= depth:
            end = j
            break
    return "\n".join(lines[start:end])


SETUP = ROOT / "workflows" / "job-setup.md"
CV = ROOT / "workflows" / "reference" / "05-cv-templates.md"
EVAL = ROOT / "workflows" / "reference" / "04-job-evaluation.md"
OUTREACH = ROOT / "workflows" / "reference" / "06-outreach-templates.md"

#: 出现在**举例位置**就说明在预设行业的词。不是禁止提及——框架里讨论某个实测案例
#: 时当然可以出现——而是不许出现在「比如 X、Y、Z」这种给用户看的清单里。
ROLE_WORDS = ("后端开发", "前端开发", "算法工程师", "数据分析师", "BI 工程师",
              "运维工程师", "测试工程师")


def example_lists(text: str) -> list[str]:
    """抓出「比如/例如「A」「B」」这类给用户看的举例清单。"""
    out = []
    for m in re.finditer(r"(?:比如|例如|如)\s*((?:「[^」]{1,20}」\s*){2,})", text):
        out.append(m.group(1))
    return out


class SetupDoesNotPresetAnIndustry(unittest.TestCase):
    def test_the_example_rule_is_stated(self):
        t = SETUP.read_text(encoding="utf-8")
        self.assertIn("不预设用户是哪个行业", t,
                      "setup 里要写明这个工具不预设行业")
        self.assertRegex(
            t, r"从他自己的资料推|从这位用户已知的背景推导",
            "举例必须从用户自己的背景推，规则要写出来")

    def test_no_hardcoded_role_lists_in_examples(self):
        """问卷里不许出现写死的职业清单——清单之外的人会以为工具不是给他用的。"""
        t = SETUP.read_text(encoding="utf-8")
        bad = [lst for lst in example_lists(t)
               if any(w in lst for w in ROLE_WORDS)]
        self.assertFalse(bad, f"setup 的举例里写死了职业清单：{bad}")

    def test_path_a_and_b_read_the_user_materials_first(self):
        """「先读资料再判断」是这个模型的第一步，两条路径都得在。"""
        t = SETUP.read_text(encoding="utf-8")
        self.assertIn("路线 A", t)
        self.assertIn("路线 B", t)

    def test_no_profile_section_named_after_one_users_situation(self):
        """写入的 profile 小节名不能是某一类人才有的东西。

        实测：这一节的问法是通用的（作品/项目按谁在真实使用分层），但写入的目标
        小节名被写死成「开源作品的分层」——那是有开源项目的人才有的名字。
        """
        t = SETUP.read_text(encoding="utf-8")
        self.assertNotIn("开源作品的分层", t,
                         "小节名不能预设用户有开源作品")


class Section10DoesNotPresetTheUsersOwnField(unittest.TestCase):
    """问「你是哪一行 / 哪个岗」的问题，不许附写死的举例。

    Section 10 开头自己立了规矩：「**任何情况下都不要照抄本文档写死的示例词。**
    一份写着「比如数据分析、后端开发、产品经理」的问卷，会让护士、教师、财务、施工员
    当场认定这工具不是给他用的」。

    然后隔八十行，「行业/领域关键词」那问就写着「例如「新能源」「跨境电商」「医疗器械」」。

    `test_no_hardcoded_role_lists_in_examples` 没抓到，因为它比对的是**职业词表**
    （后端开发、数据分析师……），而这三个是**行业**。往词表里加词治不了本——
    词表天生不全，这正是本模块开头那句「把手上这个样本当成规则」的另一种形态。

    所以判据不用词表，用结构：**凡是问用户自己属于哪个岗位/方向/行业/领域的问题，
    都不许附带具体举例。** 至于「户口填什么样」「JD 里外包会怎么写」这类，
    举例是格式示范或匹配词表，不在此列——它们不给用户归类。
    """

    SETUP = ROOT / "workflows" / "job-setup.md"
    ABOUT_SELF = ("岗位", "方向", "行业", "领域", "技能")

    def _question_blocks(self):
        t = self.SETUP.read_text(encoding="utf-8")
        i = t.index("### Section 10：")
        j = t.index(chr(10) + "## Step 3：", i)
        return re.split(r"(?m)^\*\*问：", t[i:j])[1:]

    def test_the_scan_finds_questions(self):
        """控制用例：真抽到了问题块。"""
        blocks = self._question_blocks()
        self.assertGreaterEqual(len(blocks), 8,
                                f"Section 10 只抽到 {len(blocks)} 个问题块")
        titles = [b.split("**")[0].strip() for b in blocks]
        self.assertTrue(
            [x for x in titles if any(k in x for k in self.ABOUT_SELF)],
            f"没有一个问题是问「你属于哪一行/哪个岗」的？判据失效了：{titles}")

    #: 「例如：」后面直接跟列表的举例块。**要容忍折行**——第一版要求连续两行都以
    #: `-` 开头，而真实文本里列表项是折行的（第二行是续行不带 `-`），于是只匹配到
    #: 一行、`{2,}` 不成立，扫描当场空转：那处「Python + 领域经验 / 机器学习 +
    #: 行业背景 / 项目管理 + 技术背景」三个软件方向的举例一直没被抓到。
    BULLET_EXAMPLES = re.compile(
        r"(?:例如|比如)[：:][ 	]*" + chr(10) +
        r"((?:[ 	]*[-*0-9.]\s*[^" + chr(10) + r"]+" + chr(10) +
        r"(?:[ 	]+[^-*" + chr(10) + r"][^" + chr(10) + r"]*" + chr(10) + r")*){2,})")

    def test_no_bullet_style_example_lists_either(self):
        """「例如：」+ 列表也是写死的举例，换个排版不改变性质。

        判据只管 Section 10——那一节自己立了「任何情况下都不要照抄本文档写死的
        示例词」的规矩，别处（如硬门取值的格式示范、JD 信号词）不在此列。
        """
        t = self.SETUP.read_text(encoding="utf-8")
        i = t.index("### Section 10：")
        j = t.index(chr(10) + "## Step 3：", i)
        bad = []
        for m in self.BULLET_EXAMPLES.finditer(t[i:j]):
            ln = t[:i + m.start()].count(chr(10)) + 1
            first = m.group(1).strip().splitlines()[0].strip()[:56]
            bad.append(f"setup.md:{ln}  {first}")
        self.assertEqual(
            bad, [],
            "Section 10 里有写死的举例清单（「例如：」+ 列表）：" + chr(10) + "  "
            + (chr(10) + "  ").join(bad)
            + chr(10) + "换成**机制**——机制对所有职业都成立，例子只对一种。")

    def test_no_examples_on_questions_about_the_user(self):
        bad = []
        for b in self._question_blocks():
            title = b.split("**")[0].strip()
            if not any(k in title for k in self.ABOUT_SELF):
                continue
            for lst in example_lists(b):
                bad.append(f"「{title}」附了举例：{lst.strip()}")
        self.assertEqual(
            bad, [],
            "问用户属于哪个岗位/行业时写死了举例：" + chr(10) + "  " + (chr(10) + "  ").join(bad)
            + chr(10) + "本节开头自己写着「任何情况下都不要照抄本文档写死的示例词」——"
            + chr(10) + "举出来的那几个，恰恰会让不在其中的人认定这工具不是给他用的。"
            + chr(10) + "已读过资料就把读到的词报给他确认；没读过就开放地问。")


class UpskillExamplesAreNotOneTradesPlan(unittest.TestCase):
    """`/job-upskill` 的格式范例不许是某一个行业的学习计划。

    本测试模块开头那张表里就记着「`/job-upskill` 的分档」——**分档改了，例子没改**。
    实测这个文件里有 16 处 Kubernetes / Docker / AWS / MLOps / CI/CD：主题清单
    （Cloud & Infrastructure、MLOps、Security…）、优先级表、学习条目范例、
    搜索查询、学习顺序表，全是一份 DevOps 工程师的计划。

    护士、教师、律师、技工跑 `/job-upskill`，拿到的格式范例是一整页 Kubernetes——
    按这个模块自己的话说：「清单之外的人会当场认定这工具不是给他用的」。

    范例该示范的是**格式**（占位符 + 一句「内容从哪来」），不是内容。
    """

    UPSKILL = ROOT / "workflows" / "job-upskill.md"

    #: 一个行业的具体技术名。出现在工作流里就是把那个行业当成了所有人。
    STACK = ("Kubernetes", "Docker", "AWS", "MLOps", "CI/CD", "kubectl",
             "Helm", "Terraform", "GCP", "Azure")

    def test_the_file_still_has_examples(self):
        """控制用例：范例块还在，否则下面那条拦的是空气。"""
        t = self.UPSKILL.read_text(encoding="utf-8")
        self.assertIn("缺口名", t,
                      "upskill.md 里的占位符范例不见了——判据可能失效了")

    def test_no_one_trades_stack_in_the_examples(self):
        bad = []
        for i, line in enumerate(self.UPSKILL.read_text(encoding="utf-8").splitlines(), 1):
            for name in self.STACK:
                if name in line:
                    bad.append(f"upskill.md:{i} 「{name}」  {line.strip()[:52]}")
        self.assertEqual(
            bad, [],
            "范例里写死了一个行业的技术栈：" + chr(10) + "  " + (chr(10) + "  ").join(bad)
            + chr(10) + "范例要示范格式（占位符 + 内容从哪来），不是示范内容——"
            + chr(10) + "写死了就等于替所有用户假定了行业。")


class ExpandDoesNotNamePlatforms(unittest.TestCase):
    """`/job-expand` 的取数清单里不许出现平台名。

    `expand.md` 自己把这条讲了两遍——1f 说「不要按平台清单去找……列一串平台名既
    不会全，又在暗示他该是哪个行业的人」，Step 3 的复盘说组名与举例「不是补充举例，
    那是**唯一**的例子列表」。证照那条也已经改成「whatever his trade's are」。

    可同一份「Prioritise web lookup for」清单里，课程那条仍写着
    `(Coursera, edX, Udemy, LinkedIn Learning, DataCamp, fast.ai)`——六个全是
    技术/数据方向的 MOOC。**改了发现层、改了产出层、改了证照那一条，唯独漏了它。**
    护士的继续教育学分课、教师的国培、技工的取证培训都不在这些平台上。
    """

    EXPAND = ROOT / "workflows" / "job-expand.md"

    #: 这些名字出现在取数清单里就是预设行业。**不含**那些确实中性的说法
    #: （「有标准教学大纲的院校课程」不点任何平台的名）。
    PLATFORMS = ("Coursera", "edX", "Udemy", "DataCamp", "fast.ai", "LinkedIn Learning")

    def test_the_rule_is_still_stated_in_the_file(self):
        """控制用例：这条规则是文件自己立的，它没了本测试就失去依据。"""
        t = self.EXPAND.read_text(encoding="utf-8")
        self.assertIn("不要按平台清单去找", t,
                      "expand.md 里那条「不要按平台清单去找」不见了——本测试失去依据")

    def test_no_platform_names_in_the_lookup_list(self):
        t = self.EXPAND.read_text(encoding="utf-8")
        bad = []
        for i, line in enumerate(t.splitlines(), 1):
            # 讲这条规则本身的句子要引用反例，跳过
            if "平台清单" in line or "平台名" in line:
                continue
            for name in self.PLATFORMS:
                if name in line:
                    bad.append(f"expand.md:{i} 「{name}」  {line.strip()[:56]}")
        self.assertEqual(
            bad, [],
            "取数清单里点了平台的名：\n  " + "\n  ".join(bad)
            + "\n判据该是「他材料里有没有点名这门课」，不是「在不在某个平台上」——"
            "\n这几家 MOOC 只覆盖一部分行业，清单之外的人会当场认定这工具不是给他用的。")


class TheProfileScaffoldIsIndustryNeutral(unittest.TestCase):
    """`profile.example/` 是**每个新用户资料的生成源头**——预设藏在这里危害最大：
    `/job-setup` 按它的结构建资料，脚手架里的行业痕迹会被复制进所有人的 profile。

    复查时实测抓到三处：小节名「开源作品的分层」（有开源项目的人才有的名字）、
    「GitHub / 作品集」（GitHub 打头预设了技术岗）、「（如 AI 产品）」举例。
    第一轮改 setup.md 时漏了这里——**改了问法、没改问法要写入的模板**。
    """

    SCAFFOLD = ROOT / "profile.example" / "candidate.md"

    def test_no_open_source_section_name(self):
        t = self.SCAFFOLD.read_text(encoding="utf-8")
        self.assertNotIn("开源作品的分层", t,
                         "脚手架的小节名预设了用户有开源作品")
        self.assertIn("作品与项目的分层", t)

    def test_no_github_first_labeling(self):
        t = self.SCAFFOLD.read_text(encoding="utf-8")
        self.assertNotIn("GitHub / 作品集", t,
                         "GitHub 打头的字段名预设了技术岗——作品集/个人主页才是中性的")

    def test_scaffold_is_placeholders_not_a_persona(self):
        """脚手架只能是 [占位符]，不能是任何一个具体的人的影子。

        ## 词表从活动用户的真实资料里现取，不写死在这里

        原来这里写死了五个词（维护者的城市、雇主、两个作品名、一个业务域）。
        那样有两个毛病，而且都不小：

        1. **它把要防的东西写进了要保护的地方。** 这份测试是公开的，于是一条
           「检查有没有泄漏个人数据」的断言，自己成了个人数据泄漏点——审计时
           正是从这一行读到那几个词的。
        2. **它只护得住一个人。** 换个维护者、换个 fork，那五个词一个都不沾边，
           断言照样全绿，而他自己的痕迹泄进脚手架没人会发现。

        现在从 `users/<活动用户>/profile/` 里**按字段精确取**（姓名、雇主、院校
        ——都是明确的专有名词），那个目录本来就 gitignore。取不到就 skip，
        新 clone 和 CI 上不会因此变红。
        """
        terms = self._identifiers()
        if not terms:
            self.skipTest("这个 clone 里没有填好的活动用户资料，无从比对")
        t = self.SCAFFOLD.read_text(encoding="utf-8")
        for term in sorted(terms):
            with self.subTest(term=term[0] + "*" * (len(term) - 1)):
                self.assertNotIn(
                    term, t,
                    "脚手架里泄进了活动用户的真实信息（这条不打印具体值，"
                    "自己 grep profile 比对）")

    @staticmethod
    def _identifiers() -> set:
        """活动用户资料里那些**明确是专有名词**的字段值。

        **实现只有一份**，在 `test_no_maintainer_data_in_repo.identifiers()`。
        这里原来是它的一份副本，于是两份一起烂：抽取规则是照着
        `profile.example` 的模板形状写的（雇主在标题里、院校在表格里），而
        `/job-setup` 真写出来的是列表形状——两边都只抽到用户名一个词，
        两条守卫同时退化成「只查名字」，而各自的控制用例只验「非空」，全绿。
        2026-08-18 修的是那一份，这一份靠导入自动跟上。
        """
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from test_no_maintainer_data_in_repo import identifiers
        return identifiers()


class FrameworkDoesNotEnumerateProfessions(unittest.TestCase):
    def test_no_profession_taxonomy_table(self):
        """框架里不该有「职业 → 该填什么」的对照表。

        举例说明通用性时很容易顺手列一张「护士/律师/财务」的表——但**枚举职业
        本身就隐含了一套分类**，而分类是这个框架明确不提供的东西。
        """
        t = EVAL.read_text(encoding="utf-8")
        self.assertNotRegex(
            t, r"\|\s*职业\s*\|",
            "框架里出现了职业分类表——不提供职业分类是这条规则的全部意义")

    def test_the_generic_split_is_stated_without_examples(self):
        t = EVAL.read_text(encoding="utf-8")
        self.assertIn("不要预设任何行业", t)


class TemplatesAdaptToTheUsersField(unittest.TestCase):
    def test_cv_section_order_is_per_industry_not_universal(self):
        t = CV.read_text(encoding="utf-8")
        self.assertIn("章节顺序按行业定", t,
                      "简历章节顺序要按用户行业定一次，不能当成普适顺序")
        self.assertIn("不是每个行业都有", t,
                      "「项目经历」不是人人都有的章节，要写明")
        self.assertRegex(t, r"执业资格|证书.*往前提",
                         "执业资格类行业的证书要往前提，压在最后等于藏起来")

    def test_cv_still_forbids_per_job_reordering(self):
        """放宽的是「基线顺序按行业定」，**不是**「每个岗都能重排」——后者会让
        同一个人的简历结构在不同岗位下不一致，而 HR 常同时看在线简历与 PDF。"""
        t = CV.read_text(encoding="utf-8")
        self.assertIn("不许为每个岗重排", t)

    def test_outreach_tag_comes_from_the_user_not_a_template(self):
        t = OUTREACH.read_text(encoding="utf-8")
        self.assertRegex(t, r"从这位用户\s*自己的资料里挑|不要套模板",
                         "邮件标签要从用户自己的资料里挑，不能给固定示例")


if __name__ == "__main__":
    unittest.main()


class OnlyOneFileIsTheGenerationTemplate(unittest.TestCase):
    """`search-queries.md` 有两份，只有一份是 `/job-setup` 拷贝的正本。

    - `profile.example/search-queries.md` —— **正本**，`/job-setup` Step 3 §5
      明写「从它起手」；
    - `workflows/reference/search-queries.md` —— **策略**：`site:` 兜底模板、
      三层取数顺位、时间过滤。

    2026-08-21 通读时抓到：后者原来自称「由 /job-setup 按**本模板**的结构生成」。
    **两份都自称正本，而槽位数已经分叉**（AVOID 5 vs 3、LOW_YIELD 3 vs 2）——
    分叉本身就是这条判据的证据：它不是理论风险，已经发生了。
    """

    REF = ROOT / "workflows" / "reference" / "search-queries.md"
    EXAMPLE = ROOT / "profile.example" / "search-queries.md"

    def test_both_files_exist(self):
        for f in (self.REF, self.EXAMPLE):
            self.assertTrue(f.is_file(), f"{f} 不在，判据失去对象")

    def test_the_strategy_file_does_not_claim_to_be_the_source(self):
        # 讲这条规则本身的行要放过 —— 改对之后正文里留着
        # 「原来这一行写的是『按本模板的结构生成』」的说明。
        # 断言撞上自己的反例，今天第五次（前四次：页数上限、状态拼写、
        # 三渠道、gmail 铁律）。
        t = chr(10).join(
            ln for ln in self.REF.read_text(encoding="utf-8").splitlines()
            if "原来" not in ln)
        self.assertNotIn(
            "按本模板的结构生成", t,
            "策略文件又自称是 /job-setup 的生成模板 —— "
            "而 job-setup 拷的是 profile.example/search-queries.md，两处会各自漂")
        self.assertIn(
            "profile.example/search-queries.md", t,
            "策略文件没点明正本是哪一份")

    def test_setup_copies_from_the_example(self):
        """控制用例：`/job-setup` 确实是从 profile.example 起手的。"""
        t = (ROOT / "workflows" / "job-setup.md").read_text(encoding="utf-8")
        self.assertIn(
            "profile.example/search-queries.md", t,
            "/job-setup 不再从 profile.example 起手了？那上面两条要重看")

