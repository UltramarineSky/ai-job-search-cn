"""面试练习记录：写进归档、按岗回看。

## 边界（这条决定了整个设计）

练习在 Claude Code 里进行——那里才有模型能出题、追问、给反馈。`serve.py` 明写
「**不接大模型**：这里所有操作都是改一个字段，不需要判断力」。面板要是也去出题，
就得给它接模型和 API key，与那条边界直接冲突。所以分工是**对话里练 → 落盘 →
面板回看**，面板这一侧是只读的。

## 回看要看什么

不是重温自己答得多好，而是找出**上次答得含糊的那几题**——下一关多半还会问。
所以 `interview.md` Step 4b 规定答案**原话记录、不润色**：润色过的记录看着漂亮，
回看时一点用没有。

## 解析要宽进，但不许猜

练习记录是手写的。轮次/日期/阶段任何一段缺了都照样收，缺的留空——为一个格式
瑕疵丢掉整轮问答，比少显示一个日期糟得多。但读不出的字段留空字符串，不去推断。
"""

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import build_dashboard as bd  # noqa: E402

FULL = """## 第 2 轮 · 2026-08-04 · 专业面

- 场景：用人部门产品负责人，约 30 分钟

### Q1 你没有车载经验，怎么补？

**答**：座舱确实没做过，能迁移的是把智能体能力做成产品这件事。

**反馈**：承认得干脆，很好；但「多久能上手」没答，会被追问。

### Q2 带过多大团队？

**答**：AI 阶段是一人加 AI；更早带过 5 人市场团队。

**反馈**：⚠ 这里你临场说了「带过 8 人」——案例库里是 5 人，正式面试别这样讲。

## 第 1 轮 · 2026-07-31 · HR 面

- 场景：HR，20 分钟

### Q1 为什么看新机会？

**答**：想从一人全链路走向有团队支撑的核心岗。

**反馈**：够用，别展开抱怨前东家。
"""


def parse(text):
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "interview_log.md"
        p.write_text(text, encoding="utf-8")
        return bd.parse_interview_log(p)


class LogParsesIntoRounds(unittest.TestCase):

    def test_rounds_and_questions(self):
        r = parse(FULL)
        self.assertEqual([x["round"] for x in r], ["2", "1"], "轮次没解析出来")
        self.assertEqual([len(x["qa"]) for x in r], [2, 1])

    def test_fields_are_captured(self):
        r = parse(FULL)[0]
        self.assertEqual(r["date"], "2026-08-04")
        self.assertEqual(r["stage"], "专业面")
        self.assertIn("产品负责人", r["scene"])

    def test_answer_is_verbatim_not_trimmed(self):
        """答案是原话——回看时要能看出哪里含糊。"""
        qa = parse(FULL)[0]["qa"][0]
        self.assertIn("座舱确实没做过", qa["a"])
        self.assertIn("追问", qa["feedback"])

    def test_question_numbering_prefix_is_stripped(self):
        """`Q1 ` 是排版编号，界面自己排——留着会变成「1. Q1 …」。"""
        self.assertFalse(parse(FULL)[0]["qa"][0]["q"].startswith("Q1"))

    def test_fabrication_warning_survives(self):
        """临场编的内容必须留着提醒。

        少了它，一个案例库里没有的数字会**以问答记录的形式沉淀下来**——
        过两周回看，他会以为那是自己真实的经历。
        """
        self.assertIn("案例库里是 5 人", parse(FULL)[0]["qa"][1]["feedback"])


class SoftWrapsAreJoinedRealBreaksSurvive(unittest.TestCase):
    r"""换行的语义在**取数层**定死，不在 CSS。

    两个工作流对「一个 \n 是什么意思」的约定不一样：`outreach.md` 一段一行，
    `interview_log.md` 按 80 列硬折行。渲染层看到的都只是 \n，光靠 CSS 分不出
    哪个是作者要的断行。所以按 markdown 自己的规矩在这里判：**单个换行是软折行，
    空行才是分段**，`- ` / `1. ` / `>` / `#` / `|` 开头的行另起一块，``` 围栏原样不动。

    修错过一次：只给 `.ilog-fb` 加 `white-space: pre-line`，让所有 \n 都成硬换行。
    真实记录里 4 个换行有 3 个是 80 列折行，于是句子被从中间劈开。
    **那次的检查也建在 CSS 源码上，没有一条断言走数据——这个类就是补那条。**
    """

    WRAPPED = """## 第 1 轮 · 2026-07-31 · 专业面

### Q1 介绍一下自己。

**答**：我先讲跟这个岗位最相关的那段，再补一句
为什么现在看新机会。

**反馈**：45 分钟的面试，开场超过
3 分钟就会挤掉后面的深度问题。「把 Prompt 升级成
可用产品」应在前 30 秒内命中。

⚠ 提示过：那个数字在你的案例库里没有依据。
"""

    def setUp(self):
        self.qa = parse(self.WRAPPED)[0]["qa"][0]

    def test_a_wrap_between_two_chinese_characters_leaves_no_space(self):
        """这是当初报出来的原症：「升级成 可用产品」，中文里凭空多个空格。"""
        self.assertIn("升级成可用产品", self.qa["feedback"])
        self.assertNotIn("升级成 可用产品", self.qa["feedback"])

    def test_a_wrap_before_a_number_keeps_the_conventional_space(self):
        """中文与数字之间本来就该有个空格——折行接回去时要补上，不能一律不补。"""
        self.assertIn("开场超过 3 分钟", self.qa["feedback"])

    def test_a_blank_line_is_a_real_break_and_survives(self):
        """作者要断行就空一行——那是 markdown 唯一说得清的写法。"""
        lines = [ln for ln in self.qa["feedback"].split("\n") if ln.strip()]
        self.assertTrue(any(ln.startswith("⚠") for ln in lines),
                        f"⚠ 那行并进了上一段：{self.qa['feedback']!r}")

    def test_the_answer_goes_through_the_same_rule(self):
        """答案和反馈是同一个文件里的同一种正文，不能只修一边。"""
        self.assertIn("再补一句为什么现在看新机会", self.qa["a"])

    def test_a_list_is_not_flattened_into_one_line(self):
        src = "要点：\n- 第一条\n- 第二条"
        self.assertEqual(bd.unwrap_soft_wraps(src), src)

    def test_a_list_item_continuation_is_joined(self):
        """markdown 的惰性续行：不带块标记的缩进行是上一条的接续，该接回去。"""
        self.assertEqual(bd.unwrap_soft_wraps("- 很长的一条\n  接着写"), "- 很长的一条接着写")

    def test_a_code_fence_is_left_alone(self):
        """代码的换行和缩进都是内容，不是排版。"""
        src = "示例：\n```\ndef f():\n    return 1\n```"
        self.assertEqual(bd.unwrap_soft_wraps(src), src)

    def test_english_words_are_joined_with_a_space(self):
        self.assertEqual(bd.unwrap_soft_wraps("hello\nworld"), "hello world")

    def test_nothing_is_inserted_after_chinese_punctuation(self):
        """「。」自带间距，后面再补空格就是多的。"""
        self.assertEqual(bd.unwrap_soft_wraps("深度问题。\nJD 两条"), "深度问题。JD 两条")

    def test_outreach_is_left_alone_it_has_the_other_convention(self):
        """**约定是逐文件的**——别顺手把这条推广到 `parse_outreach`。

        `outreach.md` 是一段一行写的，相邻两行本身就是结构：网申自评里
        「1. 对岗位的理解」下面紧跟正文。接回去就成了「1. 对岗位的理解这个岗位
        要解决的是…」，实测 14 行压成 7 行——用户复制进网申框的就是那一坨。
        """
        src = "1. 对岗位的理解\n这个岗位要解决的是内容批量生产。\n\n2. 匹配点\n做过 0→1。"
        got = bd.parse_outreach("## 网申自评\n\n" + src + "\n")["wangshen"]
        self.assertEqual(got, src, "网申自评被接回去了——标题会和正文并成一行")


class ParsingIsLenientButNeverGuesses(unittest.TestCase):

    def test_missing_date_and_stage_still_collect_the_qa(self):
        r = parse("## 第 1 轮\n\n### Q1 问题？\n\n**答**：答案\n")
        self.assertEqual(len(r), 1, "缺日期缺阶段就把整轮丢了")
        self.assertEqual(r[0]["date"], "")
        self.assertEqual(r[0]["stage"], "")
        self.assertEqual(r[0]["qa"][0]["a"], "答案")

    def test_missing_answer_is_empty_not_invented(self):
        r = parse("## 第 1 轮 · 2026-08-01 · 专业面\n\n### Q1 问题？\n\n**反馈**：待答\n")
        self.assertEqual(r[0]["qa"][0]["a"], "", "没答的题被填了内容")

    def test_no_file_is_empty_list(self):
        self.assertEqual(bd.parse_interview_log(Path("不存在.md")), [])

    def test_prose_without_questions_is_not_a_round(self):
        self.assertEqual(parse("## 随便写的标题\n\n一段散文。\n"), [])


class PerJobNextStepGoesBackwards(unittest.TestCase):
    """倒着判断。正着判会给出倒退的建议——已面完的岗因为「有材料」被劝去投递。"""

    def test_interview_stage_points_at_prep(self):
        s = bd.job_next_step({"company": "某司", "score": 80, "materials": {"greeting": "x"},
                              "applied": {"status": "interview", "date": "2026-07-01"},
                              "interviewLog": [{"qa": []}]})
        self.assertIn("面试", s["text"])
        self.assertEqual(s["command"], "/job-interview 某司")
        self.assertIn("已练 1 轮", s["text"], "没告诉他练过几轮")

    def test_applied_points_at_outcome(self):
        """两支都要盯，而且**把「今天」钉死**。

        这条原来只传一个写死的过去日期、不传 today —— 于是它的含义
        随真实时间漂移：写的时候那是「刚投几天」，2026-08-21 再跑已经是
        32 天前，落进了另一支。**测试里写死一个过去的日期就是个时间炸弹。**
        """
        import datetime as _d
        today = _d.date(2026, 8, 21)

        def step(day):
            return bd.job_next_step(
                {"company": "某司", "score": 80, "materials": {},
                 "applied": {"status": "applied", "date": day}}, today=today)

        fresh = step("2026-08-18")                    # 3 天前
        self.assertIn("等回复", fresh["text"], "还没到线的岗该说「等回复」")
        self.assertEqual(fresh["command"], "/job-outcome 某司")

        stale = step("2026-07-20")                    # 32 天前
        self.assertIn("32 天", stale["text"], "过了线却不说已经等了多久")
        self.assertNotIn("超过", stale["text"],
                         "对已经过线的岗还在用将来时的条件句")
        self.assertEqual(stale["command"], "/job-outcome 某司")

    def test_materials_but_not_applied(self):
        """投递本身没有命令（这个仓库不替你提交），但**投完那一步**有。

        这条原来断言「不给命令」，理由是「去投递没有命令可跑，别给一个假的」。
        原则对，结论错——`/job-outcome` 不是假命令，它是紧接着的下一步。断在这里的
        后果实测摆着：**材料就绪 4 份、投递记录 0 条**。投出去之后线索就没了，
        后面的催进度、备面、报表全都无从谈起。

        全局那条「下一步」在同一状态下早就给 `/job-outcome <公司>` 了；是每岗这条
        不一致。要紧的是**文案把顺序说清**：先自己投，投完再记一笔——
        不能让人读成「跑这条就算投了」。
        """
        s = bd.job_next_step({"company": "某司", "score": 80,
                              "materials": {"greeting": "x"}})
        self.assertIn("还没投", s["text"])
        self.assertEqual(s["command"], "/job-outcome 某司")
        self.assertIn("自己投出去", s["text"], "没说清投递要自己做")
        self.assertIn("投完", s["text"], "没说清 /job-outcome 是投完之后才跑的")

    def test_no_materials_points_at_apply(self):
        s = bd.job_next_step({"company": "某司", "score": 70, "url": "https://x/1"})
        self.assertEqual(s["command"], "/job-apply https://x/1")

    def test_resolved_and_gate_failed_have_no_next_step(self):
        for job in [
            {"company": "某司", "score": 80, "applied": {"status": "rejected"}},
            {"company": "某司", "score": None},          # 硬性条件没过
        ]:
            with self.subTest(job=job):
                self.assertIsNone(bd.job_next_step(job),
                                  "已结案/出局的岗还在给下一步")


class ExporterAndUiAreWired(unittest.TestCase):

    def test_exporter_emits_both_fields(self):
        src = (ROOT / "tools" / "export_web_data.py").read_text(encoding="utf-8")
        self.assertIn("interviewLog", src, "面试记录没导出")
        self.assertIn("job_next_step", src, "逐岗下一步没导出")

    def test_per_job_step_is_computed_after_applied_is_linked(self):
        """顺序要紧：放在 applied 回接之前算，已投/已面的岗会被判成「去投递」。"""
        src = (ROOT / "tools" / "export_web_data.py").read_text(encoding="utf-8")
        self.assertLess(src.index('j["applied"] = {'), src.index("job_next_step(j)"),
                        "逐岗下一步算在了 applied 回接之前")

    def test_ui_is_read_only_and_says_why(self):
        src = (ROOT / "web" / "src" / "components" / "InterviewLog.tsx").read_text(
            encoding="utf-8")
        self.assertIn("只负责回看", src, "没说清面板这一侧是只读的")
        self.assertNotIn("fetch(", src, "面板不该自己去要题目——出题需要模型")

    def test_log_is_collapsed_by_default(self):
        """回看用的东西不该每次展开岗位都摊开。

        这块排在详情区最末。自动展开最近一轮会把「怎么投」「为什么是这个结论」
        往下推一大截，而那两者才是展开一个岗位时真正要看的。轮次标题行已经给出
        日期/阶段/题数，够判断要不要点开。
        """
        src = (ROOT / "web" / "src" / "components" / "InterviewLog.tsx").read_text(
            encoding="utf-8")
        self.assertNotIn("defaultActiveKey", src,
                         "面试记录又变成默认展开了——它会把「怎么投」挤到屏幕外")

    def test_workflow_prescribes_the_format(self):
        t = (ROOT / "workflows" / "job-interview.md").read_text(encoding="utf-8")
        self.assertIn("interview_log.md", t, "/job-interview 没规定往哪写")
        self.assertIn("原话记录", t, "没规定答案不许润色")
        self.assertIn("追加", t, "没规定轮次累加、旧的不动")
        self.assertIn("要断行就空一行", t,
                      "没告诉写的人怎么表达断行——软折行会被接回去，"
                      "⚠ 提示会并进上一段，而写的时候根本看不出来")


if __name__ == "__main__":
    unittest.main()


class TheParserIsLenientButNeverGuesses(unittest.TestCase):
    """练习记录是手写的——格式瑕疵不许丢掉整轮问答，但缺的字段也不许猜。

    `interview.md` Step 4b 规定的格式是 `## 第 N 轮 · 日期 · 阶段`。
    实际手写时三段随时可能缺一段。2026-08-20 逐个边界验过：七种残缺写法
    全部宽进、不丢轮、缺的留空字符串。

    最易错的一处是「答案正文里含『反馈』二字」——`**答**：我说了反馈机制` 后面
    还跟着真正的 `**反馈**：`。非贪婪 + 前瞻断言处理对了，这里钉住它。
    """

    def _parse(self, text):
        import tempfile
        d = Path(tempfile.mkdtemp())
        f = d / "interview_log.md"
        f.write_text(text, encoding="utf-8")
        return bd.parse_interview_log(f)

    def test_missing_header_parts_never_drop_the_round(self):
        for label, text in [
            ("缺日期", "## 第 2 轮 · 专业面\n\n### Q1 问？\n\n**答**：答\n"),
            ("缺轮次", "## 2026-08-20 · HR 面\n\n### Q1 问？\n\n**答**：答\n"),
            ("只有轮次", "## 第 3 轮\n\n### Q1 问？\n\n**答**：答\n"),
        ]:
            with self.subTest(label):
                r = self._parse(text)
                self.assertEqual(len(r), 1, f"{label} 时整轮被丢掉了")
                self.assertEqual(len(r[0]["qa"]), 1)

    def test_missing_fields_stay_empty_not_inferred(self):
        r = self._parse("## 第 3 轮\n\n### Q1 问？\n\n**答**：答\n")
        self.assertEqual(r[0]["date"], "", "日期读不出时被猜了一个")
        self.assertEqual(r[0]["stage"], "", "阶段读不出时被猜了一个")

    def test_answer_containing_the_word_feedback(self):
        """`**答**：我说了反馈机制` + 真的 `**反馈**：` —— 别在答案里就截断。"""
        r = self._parse("## 第 5 轮\n\n### Q1 问？\n\n"
                        "**答**：我说了反馈机制\n\n**反馈**：真反馈\n")
        qa = r[0]["qa"][0]
        self.assertEqual(qa["a"].strip(), "我说了反馈机制")
        self.assertEqual(qa["feedback"].strip(), "真反馈")

    def test_empty_round_is_kept_and_explained(self):
        """0 题的轮要保留（起了个头就中断是真实情况），页面也要说清。"""
        r = self._parse("## 第 6 轮 · 2026-08-20 · 专业面\n\n- 场景：空轮\n")
        self.assertEqual(len(r), 1, "0 题的轮被丢掉了")
        self.assertEqual(len(r[0]["qa"]), 0)
        c = (ROOT / "web" / "src" / "components" / "InterviewLog.tsx").read_text(encoding="utf-8")
        self.assertIn("r.qa.length === 0", c, "0 题的轮展开后是一片空白")
        self.assertIn("没记下问答", c)
