"""`tools/doctor.py` 是新用户的导航——它自己绝不能是需要排查的那个东西。

它的存在意义是「什么都还没配好的时候也能告诉你下一步」，所以它的契约比别的脚本更严：

1. **零依赖**：只用标准库，不 import 本仓库任何模块。否则在「还没装好」的状态下它自己
   就先崩了，而那正是最需要它的时刻。
2. **只读**：不创建、不修改任何文件。用户第一次跑陌生仓库的脚本时，它不该动他的东西。
3. **任何状态都不崩**：`.active_user` 缺失/指向不存在的用户、profile 全是占位符、
   `seen_jobs.json` 损坏——全都要给出有用输出，而不是 traceback。
4. **必给且只给一条下一步**：给三条并列选项等于没给。
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCTOR = REPO_ROOT / "tools" / "doctor.py"


def _run_in(root: Path):
    """在 root 目录下跑 doctor，返回 (returncode, stdout+stderr)。"""
    # ⚠️ 这里**不设** PYTHONUTF8 / PYTHONIOENCODING。原来设了，于是这条测试一直绿——
    # 而它绿的原因是把用户真实遇到的条件配置掉了：Windows 上管道输出会回落到
    # cp936，doctor 的中文提示到 Git Bash / VS Code 终端里就是一屏乱码。
    # 同期 test_cli_contract 没设、照实撞见乱码而变红，那条红的才是诚实的。
    # 现在 doctor.py 自己把非 tty 的输出定到 UTF-8，不再需要外部环境变量兜。
    #
    # 但 JOBS_CODE_TOOL 要钉死：这些断言钉的是文档正本的标准形式（带斜杠）。
    # doctor 会按宿主工具去斜杠，子进程默认继承本会话的探测信号——Claude Code
    # 会话里有 CLAUDECODE=1 就带斜杠、CI 与普通终端是 generic 就不带，同一套测试
    # 两处判得不一样（2026-09-12 CI 红了 6 条）。去斜杠那一层由
    # test_code_tool_detection 整条覆盖，这里只管引导内容对不对。
    env = dict(os.environ)
    env["JOBS_CODE_TOOL"] = "claude"
    res = subprocess.run([sys.executable, str(root / "tools" / "doctor.py")],
                         cwd=str(root), capture_output=True, text=True,
                         encoding="utf-8", errors="strict", timeout=180, env=env)
    return res.returncode, (res.stdout or "") + (res.stderr or "")


def _scaffold(tmp: Path) -> Path:
    """搭一个最小的「像本仓库」的目录，只放 doctor 需要看到的东西。"""
    (tmp / "tools").mkdir(parents=True)
    shutil.copy(DOCTOR, tmp / "tools" / "doctor.py")
    (tmp / "workflows").mkdir()
    (tmp / "workflows" / ".keep").write_text("", encoding="utf-8")
    (tmp / "AGENTS.md").write_text("# stub\n", encoding="utf-8")
    return tmp


class ContractTests(unittest.TestCase):
    def test_exists_and_is_executable_as_script(self):
        self.assertTrue(DOCTOR.is_file(), "tools/doctor.py 不存在")

    def test_imports_only_stdlib(self):
        """不得 import 本仓库任何模块——它要在什么都没配好时能跑。"""
        text = DOCTOR.read_text(encoding="utf-8")
        forbidden = ("build_dashboard", "security_guards", "lint_skills",
                     "verify_pdf")
        for name in forbidden:
            self.assertNotIn(f"import {name}", text,
                             f"doctor.py 不该 import 本仓库模块 {name}")
        # 第三方包同样不行（只允许标准库）
        for mod in re.findall(r"^\s*import\s+([a-zA-Z_][\w.]*)", text, re.M):
            top = mod.split(".")[0]
            self.assertIn(top, sys.stdlib_module_names,
                          f"doctor.py import 了非标准库模块 {top}")

    def test_no_write_operations(self):
        """只读：不得出现写文件的调用。

        注意判据要按**语义**而不是子串——`.open(encoding=…)` 是读，
        早先一版把 `open(` 直接列进禁用子串，把正常的读操作也报成了违规。
        """
        text = DOCTOR.read_text(encoding="utf-8")
        for pat in ("write_text(", "write_bytes(", ".mkdir(", ".unlink(",
                    "shutil.copy", "shutil.rmtree", "os.remove", "os.rename",
                    ".touch("):
            self.assertNotIn(pat, text,
                             f"doctor.py 出现了写盘调用 `{pat}` —— 它必须只读")
        # open()/Path.open() 只允许读模式
        for m in re.finditer(r"open\(([^)]*)\)", text):
            args = m.group(1)
            self.assertFalse(
                re.search(r"""["'][wax]b?\+?["']""", args),
                f"doctor.py 用写模式打开了文件：open({args}) —— 它必须只读")


class FreshCloneTests(unittest.TestCase):
    def test_fresh_clone_points_at_setup(self):
        """全新 clone（无 .active_user、无 users/）→ 引导 /job-setup，且 exit 0。"""
        with tempfile.TemporaryDirectory() as td:
            root = _scaffold(Path(td))
            code, out = _run_in(root)
            self.assertEqual(code, 0, f"全新状态下应 exit 0，实际 {code}\n{out}")
            self.assertIn("第一次", out)
            self.assertIn("/job-setup", out)
            self.assertIn("下一步", out)

    def test_no_files_created(self):
        """跑完之后目录内容必须一模一样。"""
        with tempfile.TemporaryDirectory() as td:
            root = _scaffold(Path(td))
            before = sorted(p.relative_to(root).as_posix()
                            for p in root.rglob("*") if "__pycache__" not in p.parts)
            _run_in(root)
            after = sorted(p.relative_to(root).as_posix()
                           for p in root.rglob("*") if "__pycache__" not in p.parts)
            self.assertEqual(before, after, "doctor.py 改动了目录内容——它必须只读")


class BrokenStateTests(unittest.TestCase):
    def test_active_user_pointing_nowhere_suggests_user_command(self):
        """指针坏了要引导 /job-user，而不是 /job-setup（跑 /job-setup 修不了指针）。"""
        with tempfile.TemporaryDirectory() as td:
            root = _scaffold(Path(td))
            (root / ".active_user").write_text("不存在的人", encoding="utf-8")
            (root / "users" / "已有用户" / "profile").mkdir(parents=True)
            (root / "users" / "已有用户" / "profile" / "candidate.md").write_text(
                "城市：上海\n", encoding="utf-8")
            code, out = _run_in(root)
            self.assertEqual(code, 0)
            self.assertIn("/job-user", out)
            step = out.split("下一步做什么")[-1]
            # 只看**被推荐的命令行**（缩进的那几行），不看解释性文字——
            # 解释里出现「跑 /job-setup 补资料修不了它」是对的，不该判违规。
            cmds = [ln.strip() for ln in step.splitlines()
                    if ln.startswith(("    ", "\t")) and ln.strip().startswith("/")]
            self.assertTrue(cmds, f"没给出任何可执行命令：\n{step}")
            self.assertTrue(all(c.startswith("/job-user") for c in cmds),
                            f"指针坏了时推荐的命令应只有 /job-user 系列，实际：{cmds}")

    def test_unfilled_profile_suggests_setup(self):
        with tempfile.TemporaryDirectory() as td:
            root = _scaffold(Path(td))
            (root / ".active_user").write_text("张三", encoding="utf-8")
            prof = root / "users" / "张三" / "profile"
            prof.mkdir(parents=True)
            (prof / "candidate.md").write_text("姓名：[YOUR_NAME]\n", encoding="utf-8")
            code, out = _run_in(root)
            self.assertEqual(code, 0)
            self.assertIn("/job-setup", out.split("下一步做什么")[-1])

    def test_corrupt_seen_jobs_does_not_crash(self):
        with tempfile.TemporaryDirectory() as td:
            root = _scaffold(Path(td))
            (root / ".active_user").write_text("张三", encoding="utf-8")
            prof = root / "users" / "张三" / "profile"
            prof.mkdir(parents=True)
            (prof / "candidate.md").write_text("城市：上海\n", encoding="utf-8")
            js = root / "users" / "张三" / "job_scraper"
            js.mkdir(parents=True)
            (js / "seen_jobs.json").write_text("{ 这不是合法 JSON", encoding="utf-8")
            code, out = _run_in(root)
            self.assertEqual(code, 0, f"损坏的 JSON 不该让它崩\n{out}")
            self.assertNotIn("Traceback", out)
            self.assertIn("下一步", out)

    def test_both_store_generations_are_counted(self):
        """`seen_jobs.json` 两代格式都要数得出来 —— 老格式不许静默变成 0。

        真实结构是 `{"seen": {…}}`，早期库顶层直接就是 `{key: {…}}`。
        `_cli.seen_of` 明写两代都认，八个碰这个文件的工具全走它——
        **只有 doctor 自己写了 `.get("seen", {})`**，于是老格式恒为空。

        2026-08-21 实测同一个文件：`_cli.seen_of` 数出 2，doctor 数出 0，
        于是自检说「已抓 0 个职位」并把下一步指成 `/job-scrape`——
        而库里可能有几千个岗。**它是每个会话的第一条命令，也是新用户的第一屏。**

        doctor 不能 import `_cli`（本文件的硬契约：什么都没配好也要能裸跑），
        所以那份兼容是内联的，只能靠这条测试钉住行为。
        """
        import json

        jobs = {
            "https://example.com/job/1": {
                "url": "https://example.com/job/1", "title": "岗一",
                "company": "甲公司", "status": "ranked",
                "rank_score": 78, "rank_verdict": "强匹配"},
            "https://example.com/job/2": {
                "url": "https://example.com/job/2", "title": "岗二",
                "company": "乙公司", "status": "ranked",
                "rank_score": 64, "rank_verdict": "值得投"},
        }
        for label, payload in (("老格式（顶层直接是岗位字典）", jobs),
                               ("新格式（包在 seen 里）", {"seen": jobs})):
            with self.subTest(格式=label):
                with tempfile.TemporaryDirectory() as td:
                    root = _scaffold(Path(td))
                    (root / ".active_user").write_text("张三", encoding="utf-8")
                    prof = root / "users" / "张三" / "profile"
                    prof.mkdir(parents=True)
                    (prof / "candidate.md").write_text("城市：上海\n", encoding="utf-8")
                    js = root / "users" / "张三" / "job_scraper"
                    js.mkdir(parents=True)
                    (js / "seen_jobs.json").write_text(
                        json.dumps(payload, ensure_ascii=False), encoding="utf-8")
                    code, out = _run_in(root)
                    self.assertEqual(code, 0, out)
                    self.assertIn(
                        "已抓 2 个职位", out,
                        f"{label}：自检没数出这 2 个岗 —— 老格式静默归零，"
                        f"用户会被指去重抓一批他早就有的\n{out}")

    def test_outside_repo_exits_nonzero_with_guidance(self):
        """不在仓库里是唯一该非零退出的情形，但也要给出怎么办。"""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "tools").mkdir()
            shutil.copy(DOCTOR, root / "tools" / "doctor.py")
            code, out = _run_in(root)
            self.assertEqual(code, 1)
            self.assertIn("cd", out)


class NextStepTests(unittest.TestCase):
    def test_pipeline_states_each_give_exactly_one_next_step(self):
        """流水线各阶段都要给出下一步，且指向该阶段真正该跑的命令。"""
        stages = [
            # (已抓, 已评, 材料数, 期望出现的命令)
            # **零起点给脊梁那条，不是它的分解。** `AGENTS.md`「一次跑到头：只有三条命令」写着 `/job-setup → /job-auto → /job-outcome`，
            # 紧跟着一句「别把这条脊梁说成四步……多教一步的代价不是多敲一次，是让人以为不敲就会漏东西」。下面两行是**恢复态**（有岗没评、评了没材料）
            # ，各指自己那一阶段的命令 —— 那不是新用户的路。
            (0, 0, 0, "/job-auto"),
            (5, 0, 0, "/job-rank"),
            (5, 3, 0, "/job-apply"),
        ]
        for scraped, ranked, materials, expect in stages:
            with tempfile.TemporaryDirectory() as td:
                root = _scaffold(Path(td))
                (root / ".active_user").write_text("张三", encoding="utf-8")
                u = root / "users" / "张三"
                (u / "profile").mkdir(parents=True)
                (u / "profile" / "candidate.md").write_text("城市：上海\n", encoding="utf-8")
                # 搜岗那道门要的就是这份。原来夹具里没有它，而当时的门也不看它——
                # 两边一起漏，于是「自检说去搜岗、/job-scrape 说先去 /job-setup」全绿了半年。
                (u / "profile" / "search-queries.md").write_text(
                    "# 搜索查询\n- 产品经理 上海\n", encoding="utf-8")
                seen = {}
                for i in range(scraped):
                    seen[f"u{i}"] = {"title": f"岗{i}", "company": "某公司",
                                     "status": "ranked" if i < ranked else "new"}
                (u / "job_scraper").mkdir(parents=True)
                (u / "job_scraper" / "seen_jobs.json").write_text(
                    json.dumps({"seen": seen}, ensure_ascii=False), encoding="utf-8")
                apps = u / "documents" / "applications"
                for i in range(materials):
                    (apps / f"公司{i}_岗位").mkdir(parents=True)
                apps.mkdir(parents=True, exist_ok=True)
                code, out = _run_in(root)
                self.assertEqual(code, 0)
                step = out.split("下一步做什么")[-1]
                self.assertIn(expect, step,
                              f"已抓{scraped}/已评{ranked}/材料{materials} 时"
                              f"应引导 {expect}，实际输出：\n{step}")

    def test_a_step_that_needs_a_job_link_says_where_to_find_one(self):
        """「跑 `/job-apply <职位链接>`」——那个链接从哪儿来？

        上面那条只验「文案里出现了 /job-apply」，**而坏掉的那版文案也有 /job-apply**：
        原文是「排好了。下一步：从名单里挑一个，跑 /job-apply <职位URL>」。名单在
        `seen_jobs.json` 里，那是给机器读的；人能看的只有总览页，而这句话没提它。

        当场跑完 `/job-rank` 的人手上有那份清单，**第二天回来跑自检的人没有**——
        自检恰恰是给「不知道该干什么」的人用的。整条下一步链里就这一处，
        命令名给了、却给不出填进去的东西。

        这一条钉的不是措辞，是「占位符必须能被填上」。
        """
        sys.path.insert(0, str(REPO_ROOT / "tools"))
        import doctor

        st = {"in_repo": True, "user": "张三", "profile_ok": True,
              "scraped": 30, "ranked": 30, "materials": 0}
        for built in (True, False):
            with self.subTest(web_build=built):
                text = "\n".join(doctor.next_step({"web_build": built}, st))
                self.assertIn("/job-apply", text)
                self.assertIn(
                    "serve.py", text,
                    f"这一步要一个职位链接，却没说去哪儿看名单：\n{text}")
                if not built:
                    self.assertIn(
                        "npm run build", text,
                        "前端还没构建，却直接让人跑 serve.py —— "
                        f"照做会撞错：\n{text}")


class ProfileGatesAreStagedNotOneBlob(unittest.TestCase):
    """资料的门按步放行，不是一整块填完才准动。

    ## 原来那一道门同时错在两侧

    判据是「`candidate.md` 里还有 `[YOUR_` 占位符」，于是：

    **太紧**——最费神的那几项（能力边界的诚实校准、STAR 案例、行为特质）`/job-scrape`
    和 `/job-rank` 根本用不到，却拦着不让搜第一个岗。新用户要先做完**全部**自我剖析，
    十几二十分钟里全是输入、零产出。

    **太松**——`/job-scrape` 真正读的是 `search-queries.md`，那道门压根不看它。实测复现：
    自检说「求职资料已就绪，下一步：跑 /job-scrape 找新岗」，而 `/job-scrape` 一上来就停下
    说「先跑 /job-setup」。**导航工具自己把人送进墙里**，而它存在的理由就是别让人撞墙。

    还漏了一整类占位符：判据只认 `[YOUR_` 开头的，而模板里还有 `[DEGREE]`、
    `[JOB_TITLE]` 这些——`candidate.md` 的 74 种它只看得见 38 种，
    `interview-star.md` 的 20 种**一种都看不见**。学历、院校层次整行还是模板，
    自检照样说「已就绪」，而那两栏正是硬门取值。
    """

    @staticmethod
    def _doctor():
        sys.path.insert(0, str(REPO_ROOT / "tools"))
        import doctor
        return doctor

    def _user(self, td: Path, filled: dict) -> Path:
        """搭一个用户，`filled` 指定哪几份/哪几节已经填好（其余留模板原样）。"""
        root = _scaffold(td)
        shutil.copytree(REPO_ROOT / "profile.example", root / "profile.example")
        (root / ".active_user").write_text("张三", encoding="utf-8")
        prof = root / "users" / "张三" / "profile"
        prof.mkdir(parents=True)
        tok = re.compile(r"\[[A-Z][A-Z0-9_]*\]")
        for f in (REPO_ROOT / "profile.example").glob("*.md"):
            text = f.read_text(encoding="utf-8")
            want = filled.get(f.name)
            if want is True:
                text = tok.sub("已填", text)
            elif want:
                lines = text.splitlines()
                for title in want:
                    s = next((i for i, l in enumerate(lines)
                              if re.match(r"^##\s+", l)
                              and l.lstrip("# ").strip() == title), None)
                    self.assertIsNotNone(s, f"模板里没有「{title}」这一节")
                    e = next((j for j in range(s + 1, len(lines))
                              if re.match(r"^##\s+", lines[j])), len(lines))
                    lines[s:e] = [tok.sub("已填", l) for l in lines[s:e]]
                text = "\n".join(lines)
            (prof / f.name).write_text(text, encoding="utf-8")
        return root

    def test_an_empty_profile_blocks_scraping_and_says_what_is_missing(self):
        with tempfile.TemporaryDirectory() as td:
            code, out = _run_in(self._user(Path(td), {}))
        self.assertEqual(code, 0)
        step = out.split("下一步做什么")[-1]
        self.assertNotIn("跑 /job-scrape 找新岗", step,
                         "搜索配置还是模板，却让人去搜岗 —— /job-scrape 会当场停下")
        self.assertIn("搜索配置", step, f"没说清缺的是什么：\n{step}")

    def test_filling_only_the_search_config_is_enough_to_start_searching(self):
        """**这条是这次改动的全部收益**：答三分钟就能去搜岗，不必先做完自我剖析。"""
        with tempfile.TemporaryDirectory() as td:
            root = self._user(Path(td), {"search-queries.md": True})
            code, out = _run_in(root)
        step = out.split("下一步做什么")[-1]
        # **零起点给脊梁那条，不是它的分解。** `AGENTS.md`「一次跑到头：只有三条命令」写着 `/job-setup → /job-auto → /job-outcome`，
        # 紧跟着一句「别把这条脊梁说成四步……多教一步的代价不是多敲一次，是让人以为不敲就会漏东西」。
        self.assertIn("/job-auto", step,
                      f"只差后面几步才用得到的东西，却还是不让搜岗：\n{step}")

    def test_the_heavy_sections_are_not_required_to_rank(self):
        """能力边界、STAR、行为特质是最费时的三项，而 /job-rank 一个都不读。"""
        doctor = self._doctor()
        rank_block = [t for _, t in doctor.STAGE_NEEDS["rank"]["block"]]
        rank_files = [f for f, _ in doctor.STAGE_NEEDS["rank"]["block"]]
        self.assertNotIn("明确的能力边界", rank_block, "排序卡在了能力边界上")
        self.assertNotIn("interview-star.md", rank_files, "排序卡在了面试案例上")
        self.assertNotIn("behavioral.md", rank_files, "排序卡在了行为特质上")

    def test_the_rank_gate_covers_the_frameworks_hard_gates(self):
        """框架第一步（一票否决）点名的取值，必须在排序那一档挡住。

        缺了硬门取值，`/job-rank` 要么瞎猜要么静默跳过——两种都比拦住更糟。

        第一版我把「明确排除」排进了 `/job-apply`，**那是凭印象排的**；翻开
        `04-job-evaluation.md` 才发现它就写在第一步「一票否决」里。所以这条不比
        字面，它去框架里取当前的那一档，两边对不上就红。
        """
        doctor = self._doctor()
        fw = (REPO_ROOT / "workflows" / "reference" / "04-job-evaluation.md"
              ).read_text(encoding="utf-8")
        first = fw.split("## 第二步")[0]
        block = "".join(t or "" for _, t in doctor.STAGE_NEEDS["rank"]["block"])
        for name in ("明确排除", "执业资格"):
            if name not in first:
                continue                       # 框架改了就不再要求，别拿旧账压人
            with self.subTest(name=name):
                self.assertIn(
                    name, block,
                    f"框架把「{name}」列为一票否决，排序那一档却不要求它 —— "
                    "缺了它 /job-rank 只能瞎猜")

    def test_every_section_it_tells_you_to_run_really_exists(self):
        """报出去的 `--section <名>` 必须是 setup 认得的。

        报一个它不认识的名字，用户敲下去只会白跑一轮，而且不会有人告诉他为什么。
        """
        doctor = self._doctor()
        setup = (REPO_ROOT / "workflows" / "job-setup.md").read_text(encoding="utf-8")
        names = {v for v in doctor.SECTION_OF.values() if v}
        self.assertTrue(names, "一个可单跑的小节都没有？那 fix_for 永远只会说 /job-setup")
        for n in sorted(names):
            with self.subTest(section=n):
                self.assertIn(f"--section {n}", setup,
                              f"自检会让人跑 `/job-setup --section {n}`，"
                              "而 setup.md 里没有这个名字")

    def test_it_does_not_point_at_a_section_that_only_covers_part(self):
        """缺项掺了别的小节时就老实说整跑 `/job-setup`。

        原来按阶段写死：`apply` 一律报 `--section boundaries`，可那一档还缺
        「职业目标」，而 boundaries 那节根本不问它 —— 指了一条到不了的路。
        """
        doctor = self._doctor()
        self.assertEqual(doctor.fix_for(["明确的能力边界"]),
                         "/job-setup --section boundaries")
        self.assertEqual(doctor.fix_for(["明确的能力边界", "职业目标"]), "/job-setup")

    def test_it_finds_sections_whatever_heading_level_they_use(self):
        """真实的 `candidate.md` 比模板深一级，标题还带括注 —— 两条都要认。

        **实测当场空转过**：模板是 `# 候选人资料` + `## 身份 / ## 薪资 …`，而真实
        用户那份是 `## 候选人资料` + `### 身份 / ### 薪资 …`，能力边界那节还写作
        `#### 明确的能力边界（硬缺口，绝不可在材料中含糊或夸大）`。第一版写死「只认
        二级标题、标题必须一字不差」，于是每一节都「找不到」，按「找不到就不挡人」
        一路放行 —— **四档全都挡不住任何东西，分段放行整个是个摆设**。

        这条最要命的地方在于它**不会红**：门放开了，测试全绿，只有拿真实资料跑一遍
        才看得见。
        """
        doctor = self._doctor()
        body = "- **可接受底线：** 23k\n"
        for lead in ("##", "###", "####"):
            with self.subTest(level=lead):
                text = f"# 候选人资料\n\n{lead} 薪资\n{body}\n{lead} 教育背景\n- 本科\n"
                seg = doctor.section_of(text, "薪资")
                self.assertIsNotNone(seg, f"{lead} 这一级的标题找不到")
                self.assertIn("23k", seg)
                self.assertNotIn("本科", seg, "切过头了，把下一节也吞进来了")

    def test_a_heading_with_a_parenthetical_still_matches(self):
        doctor = self._doctor()
        text = "## 明确的能力边界（硬缺口，绝不可在材料中含糊或夸大）\n- 不会 X\n"
        seg = doctor.section_of(text, "明确的能力边界")
        self.assertIsNotNone(seg, "标题带括注就认不出来了")
        self.assertIn("不会 X", seg)

    def test_a_subsection_is_kept_inside_its_parent(self):
        """`技能` 底下的 `#### 能力边界` 是它的一部分，不能被当成结束标记切走。"""
        doctor = self._doctor()
        text = ("### 技能\n- A\n\n#### 明确的能力边界\n- B\n\n### 求职偏好\n- C\n")
        skills = doctor.section_of(text, "技能")
        self.assertIn("- B", skills, "子节被切走了")
        self.assertNotIn("- C", skills, "切过头，把同级的下一节吞了")
        inner = doctor.section_of(text, "明确的能力边界")
        self.assertIn("- B", inner)
        self.assertNotIn("- C", inner)

    def test_the_real_profile_layout_is_actually_covered(self):
        """控制用例：这个 clone 里那份真实资料，各节都得找得到。

        没有它，上面几条可能只是在验我自己造的假数据。
        """
        doctor = self._doctor()
        au = REPO_ROOT / ".active_user"
        if not au.is_file():
            self.skipTest("这个 clone 里还没有活动用户")
        cand = (REPO_ROOT / "users" / au.read_text(encoding="utf-8").strip()
                / "profile" / "candidate.md")
        if not cand.is_file():
            self.skipTest("活动用户还没有 candidate.md")
        text = cand.read_text(encoding="utf-8", errors="replace")
        heads = [re.sub(r"^#+\s*", "", l).strip() for l in text.splitlines()
                 if l.lstrip().startswith("#")]
        # 只验「文件里确实有这个标题」的那些。某一节整个不存在是合法的
        # （这份资料比模板旧，没有「执业资格与证照」那节），那时兜底就是不挡人。
        want = [t for _, t in doctor.STAGE_NEEDS["rank"]["block"]
                if t and any(h.startswith(t) for h in heads)]
        self.assertTrue(want, "真实资料里一个能对上的小节都没有？那这条验不出东西")
        missing = [t for t in want if doctor.section_of(text, t) is None]
        self.assertEqual(
            missing, [],
            f"这几节的标题在真实资料里明明有，`section_of` 却定位不到：{missing} —— "
            "定位不到就等于不挡人，分段放行会静默失效")

    def test_placeholders_that_do_not_start_with_your_are_seen_too(self):
        """`[DEGREE]`、`[JOB_TITLE]` 这类也算没填 —— 学历那一栏正是这种写法。"""
        doctor = self._doctor()
        toks = doctor.template_tokens("candidate.md")
        self.assertTrue(toks, "从模板里一个占位符都没抽到")
        self.assertTrue(
            any(not t.startswith("[YOUR") for t in toks),
            "模板里现在只剩 [YOUR_ 一种写法了？那这条防的事情已经不存在")


if __name__ == "__main__":
    unittest.main()
