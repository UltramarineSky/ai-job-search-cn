# -*- coding: utf-8 -*-
"""HR 反复问的那几句，事先写好、面板上能改。

用户 2026-08-24 提的：「方便了解一下您看机会的原因吗以及看哪里的机会呀」这种问题
每谈一家都要答一遍 —— 总览页上该有一块常用问答，提前写好、能直接改。

## 为什么不是「随手记几条」

**临场编的代价不是慢，是口径不一致。** 同一个问题在打招呼、HR 初面、背调三处说法
对不上，正是面试官交叉验证时要抓的（`07-interview-prep.md`：「面试官对同一个问题
反复问，是在交叉验证一致性」）。所以这份东西的价值全在**它是事先定稿的那一版**。

## 三条不能含糊的

1. **和 `candidate.md` 不是重复。** 那边的「离职原因」是完整版（面试、背调用的长度），
   这边是聊天框那一版（短、能直接粘）。两个渠道两种长度 —— 合并它们等于让其中
   一个渠道用错长度。
2. **有些问题的正确答案不是一个数字。** 期望薪资、当前薪资两条写的是「怎么把话
   接回去」—— 国内背调查个税流水是常规动作，随手填一个像工资的数字是最贵的错法。
3. **占位符没换掉 = 还没写。** 它比空着更危险：看着像准备过了。所以 `empty`
   同时认「空」和「`[YOUR_...]` 还在」。

## 存回去只换那一节

文件顶上的说明、每节里给填表人看的注释（「这一条不该是一个数字」那种），都是他
下次改的时候要看的。整份重写等于把它们冲掉。
"""
import pathlib
import re
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import export_web_data as ex  # noqa: E402

TPL = (ROOT / "profile.example" / "hr-answers.md").read_text(encoding="utf-8")
APP = (ROOT / "web" / "src" / "App.tsx").read_text(encoding="utf-8")
QA = (ROOT / "web" / "src" / "components"
      / "HrAnswers.tsx").read_text(encoding="utf-8")
SERVE = (ROOT / "tools" / "serve.py").read_text(encoding="utf-8")
CSS = (ROOT / "web" / "src" / "theme" / "cockpit.css").read_text(encoding="utf-8")


def flat(s: str) -> str:
    s = " ".join(re.sub(r"^\s*(?:>|//:?|#:?)\s?", "", s, flags=re.M).split())
    return re.sub(r"(?<=[一-鿿，。；：、（）「」])"
                  r" +(?=[一-鿿，。；：、（）「」])", "", s)


class FakeUser:
    """在临时树里放一份 hr-answers.md，`ex.ROOT` 指过去。"""

    def __init__(self, body: str):
        self.body = body

    def __enter__(self):
        self._old = ex.ROOT
        self._t = tempfile.TemporaryDirectory()
        r = pathlib.Path(self._t.name)
        (r / "users" / "甲" / "profile").mkdir(parents=True)
        self.path = r / "users" / "甲" / "profile" / ex.HR_ANSWERS
        self.path.write_text(self.body, encoding="utf-8")
        ex.ROOT = r
        return self

    def __exit__(self, *a):
        ex.ROOT = self._old
        self._t.cleanup()


SAMPLE = """# 标题

### 怎么用

说明性的小节用三级标题。

## 看机会的原因是什么

想找个团队一起做。

## 期望薪资多少

<!-- ⚠️ 这一条不该是一个数字。 -->

先问对方预算。

## 你最大的优势是什么

[YOUR_PITCH]
"""


class TheFileParsesIntoQuestions(unittest.TestCase):
    def test_only_level_two_headings_are_questions(self):
        """说明性的小节用 `###` —— 否则「怎么用」会被摆成一个 HR 会问的问题
        （第一版就是这么上去的）。"""
        with FakeUser(SAMPLE):
            qs = [x["q"] for x in ex.hr_answers("甲")]
        self.assertNotIn("怎么用", qs)
        self.assertEqual(qs[0], "看机会的原因是什么")
        self.assertEqual(len(qs), 3)

    def test_comments_are_stripped_from_the_answer(self):
        """注释是写给填表人的，不是要粘给 HR 的话。"""
        with FakeUser(SAMPLE):
            a = next(x for x in ex.hr_answers("甲") if x["q"] == "期望薪资多少")
        self.assertNotIn("<!--", a["a"])
        self.assertEqual(a["a"], "先问对方预算。")

    def test_a_placeholder_counts_as_not_written(self):
        """占位符比空着更危险：看着像准备过了。"""
        with FakeUser(SAMPLE):
            got = {x["q"]: x["empty"] for x in ex.hr_answers("甲")}
        self.assertTrue(got["你最大的优势是什么"])
        self.assertFalse(got["看机会的原因是什么"])

    def test_an_empty_answer_is_still_listed(self):
        """静默跳过等于把没准备的那几条藏起来。"""
        with FakeUser("## 问一句\n\n"):
            got = ex.hr_answers("甲")
        self.assertEqual(len(got), 1)
        self.assertTrue(got[0]["empty"])

    def test_no_file_is_no_crash(self):
        with FakeUser(SAMPLE) as f:
            f.path.unlink()
            self.assertEqual(ex.hr_answers("甲"), [])


class SavingOnlyTouchesThatSection(unittest.TestCase):
    def test_it_writes_the_new_answer(self):
        with FakeUser(SAMPLE) as f:
            self.assertEqual(ex.set_hr_answer("甲", "看机会的原因是什么", "换了一句。"),
                             {"ok": True})
            self.assertIn("换了一句。", f.path.read_text(encoding="utf-8"))

    def test_it_keeps_the_comment_in_that_section(self):
        """那句注释是他下次改的时候要看的判据，不该被这次编辑冲掉。"""
        with FakeUser(SAMPLE) as f:
            ex.set_hr_answer("甲", "期望薪资多少", "新说法。")
            t = f.path.read_text(encoding="utf-8")
        self.assertIn("这一条不该是一个数字", t)
        self.assertIn("新说法。", t)

    def test_it_keeps_the_other_sections(self):
        with FakeUser(SAMPLE) as f:
            ex.set_hr_answer("甲", "期望薪资多少", "新说法。")
            t = f.path.read_text(encoding="utf-8")
        self.assertIn("想找个团队一起做。", t)
        self.assertIn("### 怎么用", t)
        self.assertEqual(t.count("\n## "), SAMPLE.count("\n## "),
                         "节数变了 —— 多半是追加了一节")

    def test_an_unknown_question_errors_instead_of_appending(self):
        """静默追加会给出两个同名问题，而他以为自己改的是其中一个。"""
        with FakeUser(SAMPLE) as f:
            r = ex.set_hr_answer("甲", "查无此问", "x")
            self.assertFalse(r["ok"])
            self.assertNotIn("查无此问", f.path.read_text(encoding="utf-8"))

    def test_a_missing_file_errors(self):
        with FakeUser(SAMPLE) as f:
            f.path.unlink()
            self.assertFalse(ex.set_hr_answer("甲", "看机会的原因是什么", "x")["ok"])

    def test_a_question_with_regex_chars_is_escaped(self):
        """「能接受出差 / 大小周吗」里那个 `/` 无所谓，但 `(` 会炸。"""
        with FakeUser("## 现在（上一份）多少\n\n旧的。\n") as f:
            self.assertTrue(ex.set_hr_answer("甲", "现在（上一份）多少", "新的。")["ok"])
            self.assertIn("新的。", f.path.read_text(encoding="utf-8"))


class ThePanelShowsAndEditsThem(unittest.TestCase):
    def test_it_is_one_of_the_desk_buttons(self):
        self.assertIn('key: "hrqa", name: "HR 常问的"', APP)

    def test_the_button_says_how_many_are_unwritten(self):
        i = APP.index('key: "hrqa"')
        seg = APP[i:i + 900]
        self.assertIn("条没写", seg)
        self.assertIn("都写好了", seg)

    def test_unwritten_ones_light_the_button(self):
        """HR 问到时手上没说法，那是待办不是提示。"""
        i = APP.index('key: "hrqa"')
        self.assertRegex(APP[i:i + 900], r"alarm: \(snap\.hrAnswers \?\? \[\]\)\.some")

    def test_each_answer_can_be_copied(self):
        self.assertIn("navigator.clipboard?.writeText(it.a)", QA)

    def test_editing_is_hidden_when_the_server_is_not_running(self):
        """给了「改」却存不回盘，用户以为存上了 —— 同这一页别处对 `live` 的处理。"""
        self.assertIn("{live && (", QA)

    def test_line_breaks_survive(self):
        """答案是要直接粘进聊天框的字，折成一段会把他排好的分行毁掉。"""
        i = CSS.index("\n.hrqa-a {")
        self.assertIn("white-space: pre-wrap", CSS[i:CSS.index("}", i)])

    def test_it_says_how_many_are_unwritten_inside_too(self):
        self.assertIn("还有 {blank} 条没写", QA)

    def test_a_failed_save_says_so(self):
        """静默失败会让他以为存上了。"""
        self.assertIn("没存进去", QA)

    def test_the_endpoint_is_wired(self):
        self.assertIn('path == "/api/hr-answer"', SERVE)
        self.assertIn("ex.set_hr_answer(active_user()", SERVE)
        self.assertIn('"/api/hr-answer": "改常用问答"', SERVE)

    def test_the_endpoint_needs_no_job_id(self):
        i = SERVE.index("if not job_id and path not in")
        self.assertIn('"/api/hr-answer"', SERVE[i:i + 260])

    def test_it_writes_under_the_same_lock(self):
        """读-改-写整份文件 —— 两个标签页同时存，后写的会盖掉先写的。"""
        i = SERVE.index('path == "/api/hr-answer"')
        self.assertLess(SERVE.index("with _WRITE_LOCK:"), i)


class TheTemplateSaysWhatMatters(unittest.TestCase):
    def test_it_says_why_pre_written(self):
        self.assertRegex(flat(TPL), r"临场编的代价不是慢，是口径不一致")

    def test_it_says_it_is_not_a_duplicate_of_the_profile(self):
        seg = flat(TPL)
        self.assertRegex(seg, r"两者不是重复，是两个渠道两种长度")

    def test_the_pay_questions_are_not_a_number(self):
        seg = flat(TPL)
        self.assertRegex(seg, r"这一条的答案\*\*不该是一个数字\*\*")
        self.assertRegex(seg, r"随手填一个像工资的数字是最贵的错法")

    def test_the_workstyle_answer_must_match_the_exclusions(self):
        self.assertRegex(flat(TPL), r"和 `candidate.md`「明确排除」那一节对得上")

    def test_the_heading_level_rule_is_stated(self):
        """说明用 `###`，问题用 `##` —— 不写清楚就会多出一个假问题。"""
        self.assertRegex(flat(TPL), r"说明性的小节一律用 `### `")

    def test_every_question_has_a_placeholder(self):
        """模板里不许出现某一个人的答案 —— 那会被下一个用户照抄。"""
        qs = re.findall(r"^## (.+)$", TPL, re.M)
        self.assertGreaterEqual(len(qs), 8)
        for q in qs:
            with self.subTest(q=q):
                body = TPL.split("## " + q, 1)[1].split("\n## ")[0]
                self.assertRegex(body, r"\[YOUR_[A-Z_]+\]",
                                 f"「{q}」在模板里已经填了内容")


class TheSignalItLeansOnIsReal(unittest.TestCase):
    def test_the_active_user_has_one(self):
        p = ROOT / ".active_user"
        if not p.is_file():
            self.skipTest("没有活动用户")
        u = p.read_text(encoding="utf-8").strip()
        if not (ROOT / "users" / u / "profile" / ex.HR_ANSWERS).is_file():
            self.skipTest("这位用户还没有这份文件")
        got = ex.hr_answers(u)
        self.assertGreaterEqual(len(got), 5)
        self.assertNotIn("怎么用", [x["q"] for x in got],
                         "说明性的小节又被当成问题了")


if __name__ == "__main__":
    unittest.main()
