# -*- coding: utf-8 -*-
"""`resume/` 底下有两份 `.typ`，而整条流程只认 `main.typ`。

国内求职常见**两份并行**：网申/打招呼用的精简版，和猎头要、面试时带的详版。
目录本来就放得下，实测活动用户 2026-08-23 也确实这么用了：

    main.typ        12 KB   ← /job-resume 审它、/job-apply 与 /job-cv 发它
    main-长版.typ    15 KB   ← 从来没有任何一步打开过

危险的不是「少审一份」，是**审完之后那句话**：报告抬头叫「简历审核」、
结论写「必须改：无」（`resume-audit-2026-08-01.md` 就是这么写的），
用户读到的是「我的简历没问题」。同这个仓库那条**「没查」和「查过没有」是两件事**
—— 而这里连「没查」都没说出口。

两份并行还会漂：改了一份忘了另一份，数字对不上，面试或背调时是要解释的。

两处补，缺一不可：
- `job-resume.md` Step 1 加一步 `ls resume/*.typ`，多出来的进报告的「没查的」；
- `audit_pipeline` 加一条检查 —— 光写在流程里就是这个仓库那条
  「规则写了、没有东西验它」，执行者每次凭记忆遵守。
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

RESUME = (ROOT / "workflows" / "job-resume.md").read_text(encoding="utf-8")
HEAD = "### 读之前先 `ls resume/*.typ`"


def _step1() -> str:
    i = RESUME.index(HEAD)
    m = re.search(r"^(---|## )", RESUME[i:], re.M)
    return RESUME[i:i + (m.start() if m else 1800)]


class TheWorkflowLooksForOtherResumes(unittest.TestCase):
    def test_the_step_exists(self):
        self.assertIn(HEAD, RESUME, "Step 1 仍然只读那三样，不看目录里还有什么")

    def test_it_is_before_the_checks(self):
        """在 Step 2 之后发现就晚了 —— 报告的口径要从一开始就定住。"""
        self.assertLess(RESUME.index(HEAD), RESUME.index("## Step 2"))

    def test_the_extras_get_named_in_the_report(self):
        """只在流程里知道不算 —— 用户看的是报告。"""
        seg = _step1()
        self.assertRegex(seg, r"\*\*在报告里点名\*\*")
        self.assertIn("没查的", seg, "没说清进报告的哪一节")

    def test_it_says_why_silence_is_the_bug(self):
        """「少审一份」听着像小事，「必须改：无」才是代价。"""
        seg = _step1()
        self.assertIn("必须改：无", seg)
        self.assertRegex(seg, r"我那两份里的一份没问题")

    def test_it_cites_the_existing_rule(self):
        self.assertIn("「没查」和「查过没有」是两件事", _step1())

    def test_it_asks_instead_of_deciding(self):
        """废稿还是有意留的详版，工具判不了。"""
        seg = _step1()
        self.assertIn("别替他决定", seg)
        self.assertRegex(seg, r"由他说")

    def test_it_names_the_drift_risk(self):
        """这是他该在意的理由 —— 没有它，这一步读起来像洁癖。"""
        seg = _step1()
        self.assertRegex(seg, r"两份并行就会漂")
        self.assertRegex(seg, r"面试或背调")

    def test_it_keeps_the_measured_evidence(self):
        seg = _step1()
        self.assertIn("main-长版.typ", seg)
        self.assertIn("从来没有任何一步打开过", seg)

    def test_the_three_inputs_survive(self):
        """原来那三样是被审的对象与判据，不许被这一步挤掉。"""
        i = RESUME.index("## Step 1: 读三样")
        seg = RESUME[i:i + 400]
        for f in ("resume/main.typ", "profile/candidate.md", "05-cv-templates.md"):
            with self.subTest(f=f):
                self.assertIn(f, seg)


def _mk(root: Path, resumes=(), reports=()):
    d = root / "users" / "u" / "resume"
    d.mkdir(parents=True)
    for n in resumes:
        (d / n).write_text("x", encoding="utf-8")
    if reports:
        r = root / "users" / "u" / "reports"
        r.mkdir(parents=True)
        for n in reports:
            (r / n).write_text("x", encoding="utf-8")


def _run(root: Path):
    old_root, old_pick = AP.ROOT, AP._cli.pick_user
    try:
        AP.ROOT = root
        AP._cli.pick_user = lambda *a, **k: "u"
        return AP.check_extra_resumes_are_never_audited({}, {})
    finally:
        AP.ROOT, AP._cli.pick_user = old_root, old_pick


class TheAuditEnforcesIt(unittest.TestCase):
    """流程里的规矩要有东西验 —— 否则执行者每次凭记忆遵守。"""

    def test_the_check_is_registered(self):
        names = [n for n, _ in AP.CHECKS]
        self.assertTrue(any("resume/" in n for n in names),
                        f"CHECKS 里没有这一条：{names[-3:]}")

    def test_it_fires_on_a_second_typ(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _mk(root, ("main.typ", "main-详版.typ"))
            out = _run(root)
        self.assertEqual(len(out), 1, "多了一份 .typ 却没报")
        self.assertEqual(out[0][0], "warn", "级别不对：没有机械修法的不判 error")
        self.assertIn("main-详版.typ", out[0][2], "没说是哪一份")

    def test_it_is_quiet_with_only_main(self):
        """绝大多数用户只有一份 —— 那种情况下这条必须闭嘴。"""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _mk(root, ("main.typ",))
            self.assertEqual(_run(root), [])

    def test_the_shared_template_is_not_an_extra(self):
        """`resume/template.typ` 是共享框架文件（`AGENTS.md` 的例外清单），
        不是他的第二份简历。把它报出来就是每个用户都长一条假警报。"""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _mk(root, ("main.typ", "template.typ"))
            self.assertEqual(_run(root), [])

    def test_it_survives_a_missing_directory(self):
        """新用户还没跑 /job-setup —— 不许炸。

        **这是行为断言，不是那句 `is_dir()` 的影子。** `glob` 在缺目录上返回空，
        所以早退那一行是死代码（变异实测删掉它照样绿），已删。换成 `iterdir()`
        或 `os.listdir` 就会抛 —— 这条盯的是那种改写。"""
        with tempfile.TemporaryDirectory() as td:
            self.assertEqual(_run(Path(td)), [])

    def test_it_reports_which_audit_was_the_last_one(self):
        """「审过了」和「审的是哪一份」是两件事 —— 报告名要带上。"""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _mk(root, ("main.typ", "main-详版.typ"),
                ("resume-audit-2026-08-01.md",))
            out = _run(root)
        self.assertIn("resume-audit-2026-08-01.md", out[0][2])

    def test_it_says_so_when_never_audited(self):
        """没跑过和跑过只覆盖一份，用户该做的事不一样。"""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _mk(root, ("main.typ", "main-详版.typ"))
            out = _run(root)
        self.assertIn("还没跑过 /job-resume", out[0][2])

    def test_the_message_hands_over_a_fix(self):
        """这个审计的每一条都以「修：」收尾，不然就是抱怨。"""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _mk(root, ("main.typ", "main-详版.typ"))
            out = _run(root)
        self.assertIn("修：", out[0][2])
        self.assertIn("/job-resume", out[0][2])

    def test_the_message_names_the_real_cost(self):
        """「你还有一份没审」谁都会写。要说清那句「必须改：无」错在哪。"""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _mk(root, ("main.typ", "main-详版.typ"))
            msg = _run(root)[0][2]
        self.assertIn("必须改：无", msg)
        self.assertIn("漂", msg)


class TheToolchainReallyHardcodesMain(unittest.TestCase):
    """这条检查的前提。哪天某一步真的开始认第二份，它就该改写而不是留着。"""

    def test_the_workflows_still_name_one_file(self):
        for cmd in ("job-apply", "job-cv"):
            with self.subTest(cmd=cmd):
                t = (ROOT / "workflows" / f"{cmd}.md").read_text(encoding="utf-8")
                self.assertIn("resume/main.pdf", t)

    def test_no_tool_globs_the_resume_directory(self):
        """有人加了 `resume/*.typ` 的遍历，这条检查的前提就变了 ——
        `audit_pipeline` 自己那一处是这条规矩的执行者，不算。"""
        pat = re.compile(r'resume["\']?\s*/\s*["\']?\*\.typ|glob\(["\']\*\.typ')
        hits = [p.name for p in (ROOT / "tools").glob("*.py")
                if p.name != "audit_pipeline.py"
                and pat.search(strip_comments(p.read_text(encoding="utf-8")))]
        self.assertEqual(hits, [], f"这些工具开始遍历简历目录了，前提要重写：{hits}")


if __name__ == "__main__":
    unittest.main()
