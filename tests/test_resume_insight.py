"""市场怎么读这份简历：只说数据支撑得起的话。

## 这块存在的理由

面板上的「简历分析」有两种做法，只有一种值得占位置：

- **点评简历本身**（措辞、结构、要不要加量化）——任何工具都能给，跟这个仓库攒下的
  上百份比对没关系，放上去是装饰。
- **市场对这份简历的反馈**——攒够评估才说得出来，别处拿不到。

这里做的是后者，三块：主场在哪、什么在挡你、简历要补什么。全部从**已有的评估结果**
反推，不凭空点评。

## 盯住三件最容易出错的事

1. **没数据就不说话。** 评估太少时返回 None，面板整块不显示——比显示一个
   「主场 0 个岗」的空面板诚实。本仓库反复栽在「把空数据渲染成结论」上
   （空的硬门区写着「都核对过了」、`综合 /100`、永远为真的竞业提醒）。
2. **简历读不到 ≠ 简历没写。** `inResume` 要能表达第三种状态（None），
   界面显示「没比对」。把「读不到」显示成「没写」是编造缺口。
3. **词表必须来自用户自己的资料，不能写死在代码里。** 第一版把
   `Prompt / Agent / RAG / Dify / Cursor` 硬编码进去——对一位 AI 产品候选人好用，
   换成护士、律师、财务就全空或答非所问，**那是把一个人的样本当成了所有人的规则**。
   代价是字面比对看不到「你的说法 ≠ 市场的说法」，界面要把这条边界说清楚。
"""

import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import export_web_data as ex  # noqa: E402

#: 测试用的候选人资料。技能词从这里抽——**不是从代码里的写死词表**。
#: 换成护士的资料就该抽出护理术语，这份工具才对所有人成立。
PROFILE = """# 候选人资料

### 技能

- **主力：** Prompt 设计；工作流编排；某某专项能力
- **次要：** 知识库搭建

#### 明确的能力边界

- 这一节不该被抽进技能词——它是说明性散文，不是技能
- 绝不可在材料中含糊或夸大
"""

JD = ("岗位职责：负责内部 AI 应用的产品规划与落地，聚焦效率工具与自动化流程。"
      "设计 Agent、知识库、RAG 等核心能力，负责 Prompt 设计与工作流编排。"
      "任职要求：熟练使用 Cursor、Claude Code 等 AI 编程工具，熟悉 Dify、n8n。")


def _repo(tmp: Path, entries: dict, details: dict, resume: str | None):
    u = tmp / "users" / "张三"
    (u / "job_scraper" / "details").mkdir(parents=True)
    (u / "profile").mkdir(parents=True)
    (u / "profile" / "candidate.md").write_text(PROFILE, encoding="utf-8")
    if resume is not None:
        (u / "resume").mkdir(parents=True)
        (u / "resume" / "main.typ").write_text(resume, encoding="utf-8")
    (u / "job_scraper" / "seen_jobs.json").write_text(
        json.dumps({"seen": entries}, ensure_ascii=False), encoding="utf-8")
    for jid, d in details.items():
        (u / "job_scraper" / "details" / f"{jid}.json").write_text(
            json.dumps({"description": d}, ensure_ascii=False), encoding="utf-8")
    (tmp / ".active_user").write_text("张三", encoding="utf-8")


def entry(i, stack, domain):
    url = f"https://x/{i}"
    return url, {
        "url": url, "title": f"岗{i}", "company": "某公司", "status": "ranked",
        "first_seen": "2026-07-01", "salary": "40-50k·14薪", "compIndustry": "互联网",
        "rank_score": 70, "rank_verdict": "粗筛：值得投",
        "rank_breakdown": {
            "技能与经验": 60,
            "四维": f"技能60=专业能力{stack}×0.6+业务域{domain}×0.4｜薪资85｜强度70｜发展70",
            "依据": "测试"},
    }


def run(n_sweet=6, n_cold=8, resume="Prompt 设计 工作流编排", with_bodies=True):
    entries, details = {}, {}
    for i in range(n_sweet + n_cold):
        dom = 70 if i < n_sweet else 20
        url, e = entry(i, 80, dom)
        entries[f"{url}#岗{i}"] = e
        if with_bodies:
            details[ex.stable_id(url, f"岗{i}")] = JD
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        _repo(tmp, entries, details, resume)
        saved = ex.ROOT
        ex.ROOT = tmp
        try:
            return ex.resume_insight(
                "张三", entries, tmp / "users" / "张三" / "job_scraper" / "details")
        finally:
            ex.ROOT = saved


class SaysNothingWithoutData(unittest.TestCase):
    def test_too_few_evaluations_yields_none(self):
        """评估不足就返回 None，面板整块不显示——比显示空面板诚实。"""
        self.assertIsNone(run(n_sweet=1, n_cold=2))

    def test_enough_evaluations_yields_a_result(self):
        self.assertIsNotNone(run())


class SweetSpotIsCountedFromDomainScore(unittest.TestCase):
    def test_only_domain_60_plus_counts_as_sweet_spot(self):
        r = run(n_sweet=6, n_cold=8)
        self.assertEqual(r["sweetSpot"]["count"], 6)
        self.assertEqual(r["sweetSpot"]["total"], 14)

    def test_medians_are_reported(self):
        r = run(n_sweet=6, n_cold=8)
        self.assertEqual(r["medianStack"], 80)
        self.assertLess(r["medianDomain"], r["medianStack"],
                        "业务域中位数低于专业能力——瓶颈在域，这是这块要说的核心结论")


class LegacyFieldNameStillParses(unittest.TestCase):
    """3.7.1 把「技术栈」改名为「专业能力」（前者是互联网行业词，对护士/律师
    读不通，而且它露在总览页上）。存量评估里写的是旧名——**一次改名不能让上百份
    历史数据变成读不出来的**，解析器两种都要认。"""

    def test_old_name_is_still_recognised(self):
        entries = {}
        for i in range(12):
            url = f"https://x/{i}"
            _, e = entry(i, 80, 70)
            e["rank_breakdown"]["四维"] = (
                f"技能60=技术栈80×0.6+业务域70×0.4｜薪资85｜强度70｜发展70")
            entries[f"{url}#岗{i}"] = e
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            _repo(tmp, entries, {}, "简历")
            saved = ex.ROOT
            ex.ROOT = tmp
            try:
                r = ex.resume_insight(
                    "张三", entries, tmp / "users" / "张三" / "job_scraper" / "details")
            finally:
                ex.ROOT = saved
        self.assertIsNotNone(r, "写着旧名「技术栈」的存量评估必须照样解析得出来")
        self.assertEqual(r["sweetSpot"]["count"], 12)


class ResumeComparisonDistinguishesThreeStates(unittest.TestCase):
    def test_term_in_resume_is_true(self):
        r = run(resume="我熟悉 Prompt 设计与工作流编排")
        prompt = next(a for a in r["sweetSpot"]["asks"] if a["term"] == "Prompt 设计")
        self.assertIs(prompt["inResume"], True)

    def test_term_missing_from_resume_is_false(self):
        r = run(resume="只写了别的东西")
        prompt = next(a for a in r["sweetSpot"]["asks"] if a["term"] == "Prompt 设计")
        self.assertIs(prompt["inResume"], False)

    def test_no_resume_file_is_none_not_false(self):
        """简历读不到 ≠ 简历没写。显示成「没写」是编造缺口。"""
        r = run(resume=None)
        self.assertFalse(r["sweetSpot"]["resumeChecked"])
        for a in r["sweetSpot"]["asks"]:
            self.assertIsNone(a["inResume"], f"{a['term']} 应为 None（没比对过）")

    def test_terms_absent_from_jds_are_not_listed(self):
        """主场岗没提的词不该出现——这块说的是「市场要什么」，不是背词表。"""
        r = run()
        self.assertNotIn("某某专项能力", [a["term"] for a in r["sweetSpot"]["asks"]])


class BlockersCarryAnAction(unittest.TestCase):
    def test_each_blocker_says_what_to_do_about_it(self):
        entries = dict(x for x in [entry(i, 80, 20) for i in range(12)])
        entries = {f"u{i}": e for i, (_, e) in
                   enumerate(entry(i, 80, 20) for i in range(12))}
        entries["g1"] = {"url": "https://x/g1", "title": "英语岗", "status": "ranked",
                         "rank_verdict": "硬门 FAIL (英语)", "rank_breakdown": {}}
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            _repo(tmp, entries, {}, "简历")
            saved = ex.ROOT
            ex.ROOT = tmp
            try:
                r = ex.resume_insight(
                    "张三", entries,
                    tmp / "users" / "张三" / "job_scraper" / "details")
            finally:
                ex.ROOT = saved
        self.assertTrue(r["blockers"], "有硬门与低分数据时必须给出阻碍分析")
        for b in r["blockers"]:
            self.assertTrue(b["note"].strip(), f"{b['name']} 没写「该怎么办」")
            self.assertIn(b["tone"], ("fixed", "ask", "choose"),
                          "每样阻碍要标明是改不了、该问一句、还是靠选择绕开")


class TermsComeFromTheUserNotFromHardcodedVocabulary(unittest.TestCase):
    """**这块最容易过拟合，所以单独钉住。**

    第一版把 `Prompt / Agent / RAG / Dify / Cursor` 写死在代码里。对当时那位 AI 产品
    候选人好用，但换成护士、律师、财务的资料，这块面板要么全空、要么答非所问——
    那是**把一个人的样本当成了所有人的规则**。

    改成从 `profile/candidate.md` 的「技能」小节抽词：用户写什么就拿什么比对，
    谁的行业都成立。
    """

    def test_terms_are_extracted_from_the_profile(self):
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            (tmp / "users" / "张三" / "profile").mkdir(parents=True)
            (tmp / "users" / "张三" / "profile" / "candidate.md").write_text(
                PROFILE, encoding="utf-8")
            saved = ex.ROOT
            ex.ROOT = tmp
            try:
                terms = ex.profile_terms("张三")
            finally:
                ex.ROOT = saved
        self.assertIn("Prompt 设计", terms)
        self.assertIn("知识库搭建", terms)

    def test_prose_outside_the_skills_section_is_not_a_skill(self):
        """「技能」小节到下一个标题为止——包括 `####`。

        第一版只挡了 `^###\\s`，`#### 明确的能力边界` 挡不住，一路吞掉后面几节，
        抽出 140 个词，大半是整句散文。
        """
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            (tmp / "users" / "张三" / "profile").mkdir(parents=True)
            (tmp / "users" / "张三" / "profile" / "candidate.md").write_text(
                PROFILE, encoding="utf-8")
            saved = ex.ROOT
            ex.ROOT = tmp
            try:
                terms = ex.profile_terms("张三")
            finally:
                ex.ROOT = saved
        for prose in terms:
            self.assertNotIn("绝不可", prose, f"散文被当成技能词了：{prose}")
            self.assertNotIn("说明性", prose)

    def test_no_industry_vocabulary_is_hardcoded_in_the_tool(self):
        """工具里不许再出现行业词表——一放行业词，它就只服务那一个行业。"""
        src = (ROOT / "tools" / "export_web_data.py").read_text(encoding="utf-8")
        stop = re.search(r"_STOP\s*=\s*\{(.*?)\}", src, re.S)
        self.assertIsNotNone(stop, "找不到停用词表")
        for industry_word in ("prompt", "agent", "rag", "dify", "cursor",
                              "护理", "财务", "法务"):
            self.assertNotIn(industry_word, stop.group(1).lower(),
                             f"停用词表里混进了行业词「{industry_word}」")

    def test_ui_states_what_this_comparison_can_and_cannot_see(self):
        """字面比对看不到「你的说法 ≠ 市场的说法」那类，界面要说清边界。"""
        src = (ROOT / "web" / "src" / "components" / "ResumeRead.tsx").read_text(
            encoding="utf-8")
        self.assertIn("怎么算的", src, "要给用户一个能点开看口径的入口")

    def test_source_documents_the_limitation(self):
        src = (ROOT / "tools" / "export_web_data.py").read_text(encoding="utf-8")
        self.assertIn("零依赖", src)
        self.assertIn("交给 `/job-upskill`", src,
                      "语义缺口该交给有模型的命令，边界要写在源码里")


class NotAResumeCritique(unittest.TestCase):
    """这块只放「市场反馈」，不放通用简历点评——后者任何工具都能给。"""

    def test_no_vanity_score_or_completeness_metric(self):
        src = (ROOT / "web" / "src" / "components" / "ResumeRead.tsx").read_text(
            encoding="utf-8")
        for bad in ("简历评分", "完整度", "简历得分"):
            self.assertNotIn(bad, src,
                             f"「{bad}」是没有对应动作的虚荣指标，不该出现")


if __name__ == "__main__":
    unittest.main()


class SkillHeadingLevelIsNotHardcoded(unittest.TestCase):
    """技能节标题**层级不设限**——解析器要照模板写，不照手上那份样本写。

    `profile.example/candidate.md`（/job-setup 写入的模板）用的是 `## 技能`（二级），
    而抽取器原来只认 `### 技能`（三级）：照模板建档的每一个新用户，这里都静默
    抽出 0 个词，「简历要补什么」整块空白。恰好有一份真实资料用了三级标题才没暴露。
    与硬门表只认字面标题同病，同一把尺子：换个照模板来的用户，还成立吗？
    """

    def _terms(self, heading):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            (tmp / "users" / "某测试" / "profile").mkdir(parents=True)
            (tmp / "users" / "某测试" / "profile" / "candidate.md").write_text(
                f"# 资料\n\n{heading} 技能\n\n- **主力：** 甲技能、乙技能\n\n"
                "## 下一节\n\n- 别的内容\n", encoding="utf-8")
            saved = ex.ROOT
            try:
                ex.ROOT = tmp
                return ex.profile_terms("某测试")
            finally:
                ex.ROOT = saved

    def test_template_level_h2_extracts(self):
        self.assertIn("甲技能", self._terms("##"),
                      "模板写的就是 ## 技能——抽不出来等于对所有照模板的用户失效")

    def test_h3_and_h4_also_extract(self):
        for h in ("###", "####"):
            with self.subTest(h=h):
                self.assertIn("甲技能", self._terms(h))

    def test_template_and_parser_agree(self):
        """控制测试：模板里的技能节标题，抽取器必须认得——两者再分家就当场红。"""
        import re
        tpl = (ROOT / "profile.example" / "candidate.md").read_text(encoding="utf-8")
        m = re.search(r"^(#{1,6})\s*技能\s*$", tpl, re.M)
        self.assertIsNotNone(m, "模板里没有技能节了？")
        self.assertIn("甲技能", self._terms(m.group(1)),
                      "模板的标题层级抽取器不认——解析器又照样本写了")


class BaseResumePanelIsHonestWhenItCannotRead(unittest.TestCase):
    """读不出章节 ≠ 简历没有章节——空要说出来。

    `sections` 靠 `#section("…")` 这个模板写法解析（`resume/template.typ` 定义、
    `example.typ` 在用）。换一套不这么写的模板（`/job-add-template` 明确支持这件事）
    就会解析为空，而页面原来只剩一个孤零零的「章节顺序」标签和一片空白——
    看起来像简历坏了，实际只是这一栏读不到。

    与 `GateGrid` 的「一条都没有 ≠ 都通过了」是同一条原则：
    **数据为空的地方要自己说明为什么空**，不能让调用方去猜。
    """

    def test_empty_sections_gets_an_explanation(self):
        c = (ROOT / "web" / "src" / "components" / "BaseResume.tsx").read_text(encoding="utf-8")
        self.assertIn("sections.length === 0", c, "空章节没有单独分支")
        self.assertIn("读不出章节顺序", c, "没说清是读不出来而不是没有")
        self.assertIn("不影响简历本身", c, "没说清这不是简历坏了")

    def test_pdf_stale_has_a_tolerance(self):
        """`typst compile` 常在改完 .typ 的同一秒跑完，严格比较会误报。"""
        src = (ROOT / "tools" / "export_web_data.py").read_text(encoding="utf-8")
        self.assertIn("pdfStale", src)
        seg = src.split('base["pdfStale"]')[1].split("\n")[0]
        self.assertIn("- 1", seg, "没有容差——同一秒编译完会被判成「PDF 比源文件旧」")

    def test_the_stale_warning_tells_you_how_to_fix_it(self):
        c = (ROOT / "web" / "src" / "components" / "BaseResume.tsx").read_text(encoding="utf-8")
        self.assertIn("typst compile", c, "提示了 PDF 旧，却没给重新编译的命令")
