# -*- coding: utf-8 -*-
"""86 份深评「整个没有」职位真伪信号 —— 内容其实一条没少，只是搬了家。

上一轮把这条报告从假趋势改成了报批次，并写下「该查的是那几次跑法」。查了：

    08-11（`/job-apply --top 20`）  87 份，中位 1898 字，真伪信号 87/87
    08-17（`/job-auto` 自动批量）   40 份，中位 2350 字，真伪信号  0/40

原来记的诊断是「输出格式的最后两节一起缺 → 生成到一半停了」。**三条全错**：
那批文件更长、写了更靠后的小节（「投前必问」40/40 都有）、而真伪信号的内容
被并进了「待核实的信息」，还更细 ——

> 平台字段行业写「互联网/电商」、融资写「融资未公开」——BAT 三家都已上市，
> 字段本身就不可靠。

真正的原因在模板：**04 把同一件事要了两遍。** 「职位真伪信号」和
「有哪些信息没核实上」的内容清单几乎重合（雇主匿名、平台字段自相矛盾、
核实不一致同时列在两边），不同批次各挑一个名字写。而 04 里另外两对
（投前必问 / 投前先问清楚、有哪些信息没核实上 / 待核实清单）都专门写过分工，
唯独这一对没有。

「建议」那 86 份是另一个形状：它们的结论行里已经带着条件
（「值得投（64），但钱这一关先过不了」），而写了这一节的 179 份里 **89 份（50%）**
以「投 / 不投」开头 —— 复述判词。模板对这一节只说了「投 / 不投 / 有条件地投」，
没说它和判词的分工。

两处都修在模板（那才是源头），审计同步认两个标题 —— 判「整个没有」
等于把**搬了家**说成**没查过**，而这条检查的整句结论偏偏就是「前者是没查」。
"""
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tests"))
import audit_pipeline as AP  # noqa: E402
from _srcscan import strip_comments  # noqa: E402

DOC = (ROOT / "workflows" / "reference"
       / "04-job-evaluation.md").read_text(encoding="utf-8")


def _section(head: str) -> str:
    i = DOC.index(head)
    m = re.search(r"^#{3,4}\s", DOC[i + len(head):], re.M)
    return DOC[i:i + len(head) + (m.start() if m else 1600)]


class TheTemplateSaysWhichSectionGetsWhat(unittest.TestCase):
    def test_the_signal_section_has_a_division_of_labour(self):
        """04 里另外两对都写过分工，唯独这一对没有 —— 于是它们分了家。"""
        seg = _section("### 职位真伪信号")
        self.assertIn("有哪些信息没核实上", seg, "没点名和哪一节分工")
        self.assertRegex(seg, r"我看出了什么")
        self.assertRegex(seg, r"我还不知道什么")

    def test_the_line_is_operational(self):
        """一句抽象的分工判不了具体条目。要给出各自装什么。"""
        seg = _section("### 职位真伪信号")
        self.assertIn("两个不同薪资的挂法", seg)
        self.assertIn("内部职位号", seg)
        self.assertRegex(seg, r"雇主匿名两边都沾")

    def test_positive_signals_are_invited(self):
        """「带内部职位号 = 自有岗位」是正面信号。只收负面的话，
        这一节在真实的岗上永远写「无」。"""
        seg = _section("### 职位真伪信号")
        self.assertRegex(seg, r"\*\*正面\*\*|正面信号也写")

    def test_it_carries_the_measured_cost(self):
        seg = _section("### 职位真伪信号")
        self.assertRegex(seg, r"86 份")
        self.assertRegex(seg, r"不是漏写，是这份模板要了同一件事两遍")


class TheAdviceSectionIsNotTheVerdictAgain(unittest.TestCase):
    def test_it_forbids_restating_the_verdict(self):
        seg = _section("### 建议")
        self.assertRegex(seg, r"不要复述上面的结论")

    def test_it_says_what_the_section_is_for(self):
        """光禁不给，写手只能留白 —— 那正是另外 86 份干的事。

        **不许写成 `A|B`。** 第一版写的是「要给的是＜条件＞」或「这一节要的是」二选一，
        而同一段末尾恰好有一句「错的是这份模板没说清这一节要的是什么」——
        删掉那条正面指示照样绿。变异实测抓到的，本文件第四次栽在这个形状上。"""
        seg = _section("### 建议")
        self.assertIn("要给的是**条件**", seg, "只禁不给，写手只能留白")
        self.assertIn("同上", seg, "没说条件已在结论里时怎么办")

    def test_it_keeps_the_measured_cost(self):
        seg = _section("### 建议")
        self.assertRegex(seg, r"89 份（50%）|50%")

    def test_the_placeholder_no_longer_leads_with_the_verb(self):
        """占位符原来写着「投 / 不投 / 有条件地投」—— 写手照抄，
        于是一半的产出以判词开头。示例本身就是那个坑。"""
        seg = _section("### 建议")
        body = "\n".join(ln for ln in seg.splitlines()
                         if not ln.startswith("<!--") and "-->" not in ln)
        self.assertNotIn("[1-2 句：投 / 不投 / 有条件地投，条件是什么]", body)


class TheAuditDoesNotCallAMoveAMiss(unittest.TestCase):
    SEC = ("评分明细", "结论", "优势", "缺口", "建议")

    def _mk(self, root, texts):
        apps = root / "users" / "u" / "documents" / "applications"
        for i, t in enumerate(texts):
            d = apps / f"c{i:03d}_岗"
            d.mkdir(parents=True)
            (d / "evaluation.md").write_text(t, encoding="utf-8")

    def _run(self, root):
        old_root, old_pick = AP.ROOT, AP._cli.pick_user
        try:
            AP.ROOT = root
            AP._cli.pick_user = lambda *a, **k: "u"
            return AP.check_evaluation_sections({}, {})
        finally:
            AP.ROOT, AP._cli.pick_user = old_root, old_pick

    def _eval(self, *sections):
        out = ["# 职位评估：某公司 - 某岗位", "", "- 评估日期：2026-08-17（构造）", ""]
        for s in sections:
            out += [f"## {s}", "略", ""]
        return "\n".join(out)

    def test_the_merged_heading_counts(self):
        """08-17 那批的形状：没有「职位真伪信号」，有「待核实的信息」。"""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._mk(root, [self._eval(*self.SEC, "待核实的信息")
                            for _ in range(12)])
            self.assertEqual(self._run(root), [],
                             "把并进「待核实的信息」的内容judged成没查过")

    def test_neither_heading_still_fails(self):
        """认了别名不等于放行 —— 两个标题都没有才是真缺。"""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._mk(root, [self._eval(*self.SEC) for _ in range(12)])
            out = self._run(root)
        self.assertEqual(len(out), 1)
        self.assertIn("职位真伪信号 12 份", out[0][2])

    def test_the_alias_is_written_down_with_its_reason(self):
        """一个没有理由的别名，下一个人会当成手滑删掉。
        要的是那句判据本身，不是附近有没有出现过那几个字。"""
        src = (ROOT / "tools" / "audit_pipeline.py").read_text(encoding="utf-8")
        i = src.index('"职位真伪信号"')
        seg = src[max(0, i - 900):i + 200]
        self.assertIn("两个标题都没有才算真的缺", seg, "没写清别名的边界")
        self.assertIn("**搬了家**说成**没查过**", seg,
                      "没写清为什么不能判「整个没有」")
        self.assertIn("04 那一节", seg, "没指回正本那份分工")

    def test_the_advice_section_is_still_required(self):
        """这次没给「建议」加别名 —— 它的问题是内容重复，不是搬了家。
        真省掉那一节仍然要报。"""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._mk(root, [self._eval("评分明细", "结论", "优势", "缺口",
                                       "待核实的信息") for _ in range(12)])
            out = self._run(root)
        self.assertIn("建议 12 份", out[0][2])

    def test_the_batch_line_says_what_全缺_means(self):
        """「那批 40 份全缺」读起来像「每一节都没有」，实际是
        「每份都缺了至少一节」。"""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            good = [self._eval(*self.SEC, "职位真伪信号").replace(
                "2026-08-17", "2026-08-11") for _ in range(9)]
            bad = [self._eval("结论") for _ in range(7)]
            self._mk(root, good + bad)
            msg = self._run(root)[0][2]
        self.assertIn("每份都缺了至少一节", msg)
        self.assertNotIn("份全缺", msg)


class TheOldDiagnosisIsCorrectedWhereItLived(unittest.TestCase):
    """错的诊断留在原地，下一个人会照着它去修一个不存在的问题。"""

    def _doc(self):
        src = (ROOT / "tools" / "audit_pipeline.py").read_text(encoding="utf-8")
        i = src.index("def check_evaluation_sections(")
        return src[i:src.index('"""', src.index('"""', i) + 3)]

    def test_the_halfway_stop_story_is_gone(self):
        self.assertNotIn("生成到一半停了，不是有意省略", self._doc())

    def test_the_correction_names_what_was_wrong(self):
        seg = self._doc()
        self.assertRegex(seg, r"三条全错")
        self.assertRegex(seg, r"更长|2350")
        self.assertRegex(seg, r"投前必问」40/40|更靠后的小节")

    def test_it_points_at_the_root_cause(self):
        self.assertRegex(self._doc(), r"04 把同一件事要了两遍")

    def test_the_numbers_match_what_the_check_now_reports(self):
        """docstring 记的实测数要和它自己现在的口径一致 ——
        86 是认别名之前的数，现在是 44。"""
        seg = self._doc()
        self.assertRegex(seg, r"职位真伪信号  缺 44 份")
        self.assertRegex(seg, r"86 → 44|认了之后 86")

    def test_no_direction_verdict_crept_back(self):
        """上一轮删掉的那句话不许从 docstring 溜回消息里。"""
        src = strip_comments((ROOT / "tools" / "audit_pipeline.py")
                             .read_text(encoding="utf-8"))
        i = src.index("def check_evaluation_sections(")
        code = src[i:src.index("\ndef ", i + 10)]
        for phrase in ("新出的更差", "已经好多了"):
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, code)


if __name__ == "__main__":
    unittest.main()
