# -*- coding: utf-8 -*-
"""「可以考虑」这一档的定义就是「先问清楚再决定投不投」——那份清单不能缺。

`04-job-evaluation.md` 给这一档的定义里，**问什么就是它存在的理由**。
没有那份清单，它和「值得投」在面板上没有区别 —— 而实测活动用户已经这样把
26 个这一档的岗直接发了出去，占全部投递的三成。

实测 2026-08-22：99 个有材料的「可以考虑」里，只有 52 个的深评真留下了那一节。
而面板那枚章的悬浮说明当时写着「评估里列了这个岗还没弄明白的地方」——
**对另外 47 个，这句话是假的**。

> 一枚章保证「打开有东西」，打开却是空的，**比不说更坏**：
> 下次真有东西时，他也不会再打开了。

所以两边都要钉：面板上那句话分两种说法，源头上缺了要能被查出来。
"""
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import audit_pipeline as A  # noqa: E402

SHORTLIST = (ROOT / "web" / "src" / "components"
             / "Shortlist.tsx").read_text(encoding="utf-8")


class ThePanelDoesNotPromiseAnEmptyList(unittest.TestCase):
    def test_the_claim_is_conditional_on_the_list_existing(self):
        """「评估里列了…」这句话只在真有清单时才许说。"""
        self.assertIn("(job.askBefore ?? []).length > 0", SHORTLIST,
                      "那枚章没看 askBefore 就下了「评估里列了」的断言")

    def test_the_empty_case_says_something_true_instead(self):
        """没有清单时也得说点真的，并给出补一份的办法。"""
        i = SHORTLIST.index("(job.askBefore ?? []).length > 0")
        seg = SHORTLIST[i:i + 1200]
        self.assertIn("没留下要问什么", seg, "空的那一支没说实话")
        self.assertIn("/job-apply", seg, "没告诉他怎么补一份")

    def test_the_two_variants_are_told_apart(self):
        """两种情况长得一样的话，拆开就没有意义。"""
        self.assertIn("data-thin", SHORTLIST, "弱变体没有视觉区分")
        css = (ROOT / "web" / "src" / "theme"
               / "cockpit.css").read_text(encoding="utf-8")
        self.assertRegex(css, r"\.ask-chip\[data-thin\]", "弱变体没有对应样式")


class TheAuditCatchesAMissingList(unittest.TestCase):
    @staticmethod
    def _run(evals):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            apps = root / "users" / "张三" / "documents" / "applications"
            for i, body in enumerate(evals):
                d = apps / f"公司{i}_岗位"
                d.mkdir(parents=True)
                (d / "evaluation.md").write_text(body, encoding="utf-8")
            (root / ".active_user").write_text("张三", encoding="utf-8")
            saved = A.ROOT
            try:
                A.ROOT = root
                return A.check_maybe_tier_has_questions({}, {})
            finally:
                A.ROOT = saved

    WITH = "### 结论：可以考虑\n\n### 投前必问\n- 这个岗带多少人？\n"
    WITHOUT = "### 结论：可以考虑\n\n### 建议\n- 可以投\n"
    OTHER = "### 结论：值得投\n\n### 建议\n- 投\n"

    def test_a_missing_section_is_reported(self):
        out = self._run([self.WITHOUT])
        self.assertTrue(out, "缺了那一节却没报")
        self.assertIn("投前必问", out[0][2])

    def test_a_present_section_is_not_reported(self):
        self.assertEqual(self._run([self.WITH]), [])

    def test_the_lenient_heading_variants_count(self):
        """解析器认「必问」「要问清」，审计要认同一份 —— 两处各写一份必然分叉。"""
        for head in ("### 必问的几条", "### 要问清的"):
            with self.subTest(head=head):
                self.assertEqual(
                    self._run([f"### 结论：可以考虑\n\n{head}\n- 问一句\n"]), [],
                    f"「{head}」这种写法没被认出来")

    def test_other_tiers_are_out_of_scope(self):
        """只有这一档有这个要求。一并查会造出一堆假阳性。"""
        self.assertEqual(self._run([self.OTHER]), [])

    def test_it_is_registered(self):
        self.assertTrue(
            any(getattr(fn, "__name__", "") == "check_maybe_tier_has_questions"
                for _, fn in A.CHECKS), "新检查没进 CHECKS")

    def test_the_heading_list_is_shared_with_the_parser(self):
        """审计和解析器认的标题必须是同一份。"""
        exp = (ROOT / "tools" / "export_web_data.py").read_text(encoding="utf-8")
        m = re.search(r"投前必问\|必问\|要问清", exp)
        self.assertIsNotNone(m, "解析器那边的标题词表变了")
        for w in A._ASK_HEADS:
            self.assertIn(w, m.group(0), f"审计认「{w}」，解析器不认")


if __name__ == "__main__":
    unittest.main()
