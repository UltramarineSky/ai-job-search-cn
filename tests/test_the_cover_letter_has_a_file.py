# -*- coding: utf-8 -*-
"""求职信这条链断在两处，都是静默的。

## 一：导出找的文件名和流程规定的对不上

`job-apply.md` 正文里 **6 处**写的都是 `cover-letter.md`（连字符 + `.md`），
而 `export_web_data` 找的是 `cover_letter.pdf` / `cover_letter.typ`
（下划线 + 另外两个后缀）。三处对不上，于是 `materials.coverLetter`
**永远是假的** —— 面板那句「求职信已生成，在同一目录」一次都没渲染过。

同族前科这个仓库记了好几笔：`validThrough` vs `deadline`、同名材料目录、
http vs https —— `build_dashboard` 那处注释管它叫「这是第五处」。
**名字对不上永远不报错，只是静默地什么都没有。**

## 二：流程那一步的后半句从没执行过

渠道 4 写的是两步：「草稿先并入 `outreach.md` 的『求职信（场景触发）』小节……
**第 4 步定稿后再落一份纯文本到** `cover-letter.md`——两处内容必须一致」。
实测活动用户 2026-08-25：243 份话术里 3 份写了求职信小节，
而 286 个材料目录里 `cover-letter.*` **一个都没有** —— 3/3。

求职信只在网申 / 报名系统 / 外企表单**要你交一份**时才生成（渠道 4 的五条触发
场景），他要上传的就是那份纯文本。埋在一份还夹着开场白、缺口清单和自检元数据的
`outreach.md` 里，等于要他自己挑出来再贴一遍 —— 而那正是「两处内容必须一致」
想防的事。
"""
import pathlib
import re
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import audit_pipeline as ap  # noqa: E402

EX = (ROOT / "tools" / "export_web_data.py").read_text(encoding="utf-8")
APPLY = (ROOT / "workflows" / "job-apply.md").read_text(encoding="utf-8")
READOUT = (ROOT / "web" / "src" / "components"
           / "JobReadout.tsx").read_text(encoding="utf-8")


def flat(s: str) -> str:
    s = " ".join(re.sub(r"^\s*(?:>|#:?)\s?", "", s, flags=re.M).split())
    return re.sub(r"(?<=[一-鿿，。；：、（）「」])"
                  r" +(?=[一-鿿，。；：、（）「」])", "", s)


class TheExportLooksForWhatTheWorkflowWrites(unittest.TestCase):

    def test_it_uses_the_hyphenated_name(self):
        i = EX.index('mats["coverLetter"] = True')
        seg = EX[max(0, i - 500):i]
        self.assertIn('f"cover-letter{ext}"', seg)

    def test_the_underscore_spelling_is_gone(self):
        """下划线那版**一次都没命中过**，留着只会让下一个人以为两种都行。"""
        i = EX.index('mats["coverLetter"] = True')
        seg = EX[max(0, i - 500):i + 100]
        # 注释里点名了旧写法（那是验尸报告），判据行里不许再出现
        code = "\n".join(l for l in seg.splitlines()
                         if l.strip() and not l.lstrip().startswith("#"))
        self.assertNotIn("cover_letter", code)

    def test_it_takes_the_uploadable_forms_too(self):
        """网申表单要的是能上传的那份 —— `.md` 之外也收编译产物。"""
        i = EX.index('mats["coverLetter"] = True')
        seg = EX[max(0, i - 300):i]
        for ext in ('".md"', '".pdf"'):
            with self.subTest(ext=ext):
                self.assertIn(ext, seg)

    def test_the_workflow_really_prescribes_that_name(self):
        """引的是流程原话 —— 它改了名，上面那几条就该跟着红。"""
        self.assertIn("/cover-letter.md", APPLY)
        self.assertNotIn("cover_letter.md", APPLY)

    def test_the_reason_is_recorded(self):
        i = EX.index('mats["coverLetter"] = True')
        seg = flat(EX[max(0, i - 900):i])
        self.assertIn("名字对不上永远不报错", seg)
        self.assertIn("一次都没渲染过", seg)

    def test_the_panel_line_it_feeds_still_exists(self):
        """这一格没有消费方的话，修它就没有意义。"""
        self.assertIn("m?.coverLetter && ", READOUT)
        i = READOUT.index("m?.coverLetter && ")
        self.assertIn("求职信已生成", READOUT[i:i + 160])


class TheDraftMustLeaveTheDraftFile(unittest.TestCase):
    """写了小节、没落独立文件 —— 流程那一步的后半句。"""

    def _fn(self):
        return ap.check_cover_letter_never_left_the_draft

    def test_it_is_registered(self):
        self.assertIn(self._fn(), [f for _n, f in ap.CHECKS])

    #: 一封**真的**求职信。判据要求正文得像封信（`_has_a_letter`）——
    #: 用「正文」两个字当样本，和那三份误报一样薄。
    LETTER = "尊敬的招聘负责人：我关注贵司在智能体方向的进展，过去三年主要做 AI 产品的落地交付，想申请这个岗位。"

    def _run(self, dirs, tmp):
        """`dirs` = {目录名: {文件名: 内容}}，跑一次检查。"""
        base = tmp / "users" / "_t_cover" / "documents" / "applications"
        for name, files in dirs.items():
            d = base / name
            d.mkdir(parents=True, exist_ok=True)
            for fn, body in files.items():
                (d / fn).write_text(body, encoding="utf-8")
        old_root, old_user = ap.ROOT, list(ap._USER)
        try:
            ap.ROOT = tmp
            ap._USER[:] = ["_t_cover"]
            return self._fn()({}, {})
        finally:
            ap.ROOT = old_root
            ap._USER[:] = old_user

    def setUp(self):
        import tempfile
        self.tmp = pathlib.Path(tempfile.mkdtemp())

    def test_a_draft_without_the_file_is_caught(self):
        got = self._run({"甲公司_某岗": {"outreach.md": "## 求职信（场景触发）\n" + self.LETTER}},
                        self.tmp)
        self.assertEqual(len(got), 1)
        self.assertIn("没有 `cover-letter.md`", got[0][2])

    def test_the_file_being_there_silences_it(self):
        got = self._run({"甲公司_某岗": {"outreach.md": "## 求职信（场景触发）\n" + self.LETTER,
                                        "cover-letter.md": "尊敬的……\n"}}, self.tmp)
        self.assertEqual(got, [])

    def test_a_compiled_pdf_counts_too(self):
        """他真正上传的可能就是那份 PDF —— 有它就算落了盘。"""
        got = self._run({"甲公司_某岗": {"outreach.md": "## 求职信\n" + self.LETTER,
                                        "cover-letter.pdf": "x"}}, self.tmp)
        self.assertEqual(got, [])

    def test_no_cover_letter_section_is_never_scolded(self):
        """求职信默认不生成（渠道 4 是场景触发）—— 没写就不该被问。"""
        got = self._run({"甲公司_某岗": {"outreach.md": "## 打招呼开场白\n你好\n"}},
                        self.tmp)
        self.assertEqual(got, [])

    def test_the_other_two_headings_are_caught(self):
        for h in ("## 正式求职信", "### 自荐信"):
            with self.subTest(h=h):
                import tempfile
                got = self._run({"甲_岗": {"outreach.md": h + "\n" + self.LETTER}},
                                pathlib.Path(tempfile.mkdtemp()))
                self.assertEqual(len(got), 1)

    def test_a_not_triggered_note_is_not_a_letter(self):
        """**有标题不等于有信。** 渠道 4 是场景触发，不触发时写明一句才是对的。

        实测 2026-08-31：这条检查报的 3 份，正文全是
        「不触发（BOSS 平台直聊，非校招网申、非体制内）。」—— 报的每一份
        都是误报，而它给的处置是「重跑 `/job-apply`」：让他花三次深评去修
        三份本来就对的稿子。
        """
        # 最后那条**要够长**：短的那几条被「太短不算信」那道先挡掉了，
        # 于是「不触发」那张词表一次都没被走到 —— 把它整个作废掉，这条
        # 照样绿（变异照出来的）。真实产出里那句是 28 字，写长一点也常见。
        for body in ("不触发（BOSS 平台直聊，非校招网申、非体制内）。",
                     "不适用（这个岗是直聊）。", "无。", "暂无", "",
                     "不触发。这个岗是 BOSS 平台直聊，既不是校招网申，"
                     "也不是体制内报名系统，按渠道 4 的触发清单不生成。"):
            with self.subTest(body[:10]):
                import tempfile
                got = self._run(
                    {"甲_岗": {"outreach.md": "## 求职信（场景触发）\n" + body}},
                    pathlib.Path(tempfile.mkdtemp()))
                self.assertEqual(got, [], f"「{body[:12]}」被当成了一封信")

    def test_a_mention_in_prose_is_not_a_section(self):
        """正文里提到「求职信」三个字不算 —— 只认小节标题。"""
        got = self._run({"甲_岗": {"outreach.md": "## 打招呼\n这个岗不用求职信。\n"}},
                        self.tmp)
        self.assertEqual(got, [])

    def test_no_active_user_is_silent(self):
        old = list(ap._USER)
        try:
            ap._USER[:] = []
            self.assertEqual(self._fn()({}, {}), [])
        finally:
            ap._USER[:] = old

    def test_it_says_which_command_fixes_it(self):
        got = self._run({"甲_岗": {"outreach.md": "## 求职信\n" + self.LETTER}},
                        self.tmp)
        self.assertIn("/job-apply <职位链接>", got[0][2])

    def test_it_says_why_the_standalone_file_matters(self):
        got = self._run({"甲_岗": {"outreach.md": "## 求职信\n" + self.LETTER}},
                        self.tmp)
        self.assertIn("要你交一份", got[0][2])

    def test_the_docstring_records_the_false_positives(self):
        """报错的那一版要留在原地 —— 不然下一个人会把判据改回去。"""
        doc = flat(self._fn().__doc__ or "")
        self.assertIn("全是误报", doc)
        self.assertIn("2026-08-31", doc)

    def test_the_two_step_rule_it_cites_really_exists(self):
        """引的是渠道 4 那两句原话。"""
        self.assertIn("草稿先并入 `outreach.md`", APPLY)
        self.assertIn("两处内容必须\n  一致，不得分别起草", APPLY)


class TheSignalItLeansOnIsReal(unittest.TestCase):
    """现算：这位用户此刻真的处在这个状态里。"""

    def _apps(self):
        p = ROOT / ".active_user"
        if not p.is_file():
            self.skipTest("没有活动用户")
        d = (ROOT / "users" / p.read_text(encoding="utf-8").strip()
             / "documents" / "applications")
        if not d.is_dir():
            self.skipTest("还没有材料")
        return d

    def test_some_material_has_a_cover_letter_section(self):
        """**支点。** 一份都没写过求职信的话，这一整条没有由头。"""
        apps = self._apps()
        n = sum(1 for f in apps.glob("*/outreach.md")
                if re.search(r"^#{1,3}\s*(?:求职信|正式求职信|自荐信)",
                             f.read_text(encoding="utf-8", errors="replace"), re.M))
        if not n:
            self.skipTest("这一批里没有触发求职信的岗 —— 那是正常的（场景触发）")
        self.assertGreater(n, 0)

    def test_the_audit_agrees_with_a_fresh_count(self):
        """审计报的份数和现数一遍对得上。"""
        apps = self._apps()
        # **现数要用同一个判据。** 只按标题数的话，那三份写着「不触发」的
        # 会被数进来，而审计（改对之后）不报 —— 于是这条守卫反过来在逼
        # 审计退回误报的那一版。
        want = [f.parent for f in sorted(apps.glob("*/outreach.md"))
                if ap._has_a_letter(
                    f.read_text(encoding="utf-8", errors="replace"))
                and not any((f.parent / f"cover-letter{e}").is_file()
                            for e in (".md", ".pdf", ".typ"))]
        old = list(ap._USER)
        try:
            ap._USER[:] = [(ROOT / ".active_user").read_text(encoding="utf-8").strip()]
            got = ap.check_cover_letter_never_left_the_draft({}, {})
        finally:
            ap._USER[:] = old
        if not want:
            self.assertEqual(got, [], "现数一个都没有，审计却报了")
            return
        self.assertEqual(len(got), 1)
        self.assertIn(f"{len(want)} 份话术里写了求职信", got[0][2])


if __name__ == "__main__":
    unittest.main()
