"""共享模板库的撞名闸门：注册前必须知道有没有人正在用。

`templates/cv/`、`templates/cover_letters/` 全 clone 共享，只有「谁激活了哪个
模板」这个指针按用户隔离。于是重名注册 = 覆写别人的骨架：他下次 `/job-apply` 出来的
简历**静默改样**——不报错、不提示，直到他自己看出排版不对。

`add-template.md` 原来只有散文告诫（「重名即覆盖…同 clone 的其他用户可能正激活
着它」），却没给查的手段：AI 只能挨个翻 `users/*/templates/active-*.md`。
本仓库在 `--off-track` 上刚栽过同一形状——`rank.md` 写着「要格外克制」，
照样误杀了 9 个年包 72-160 万的岗。告诫要配机制。
"""

import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import template_usage as tu  # noqa: E402


class _Repo:
    """临时仓库：几个用户、几个模板，随手摆。"""

    def __enter__(self):
        self._t = tempfile.TemporaryDirectory()
        self.tmp = Path(self._t.name)
        self._saved = tu.ROOT
        tu.ROOT = self.tmp
        return self

    def __exit__(self, *a):
        tu.ROOT = self._saved
        self._t.cleanup()

    def template(self, name, kind="cv"):
        d = self.tmp / "templates" / kind / name
        d.mkdir(parents=True, exist_ok=True)
        (d / "TEMPLATE.md").write_text(f"# Template: {name}\n", encoding="utf-8")

    def activate(self, user, name, kind="cv"):
        fname = "active-cv.md" if kind == "cv" else "active-cover-letter.md"
        d = self.tmp / "users" / user / "templates"
        d.mkdir(parents=True, exist_ok=True)
        (d / fname).write_text(
            f"# 活动模板\n\n- **模板：** {name}\n- **路径：** templates/{kind}/{name}/\n",
            encoding="utf-8")


class UsageIsDetected(unittest.TestCase):

    def test_users_on_a_template_are_listed(self):
        with _Repo() as r:
            r.template("甲模板")
            r.activate("张三", "甲模板")
            r.activate("李四", "甲模板")
            self.assertEqual(sorted(tu.usage()[("cv", "甲模板")]), ["张三", "李四"])

    def test_unused_template_has_no_users(self):
        with _Repo() as r:
            r.template("没人用的")
            self.assertNotIn(("cv", "没人用的"), tu.usage())

    def test_cv_and_cover_letter_are_separate_namespaces(self):
        """同名的 CV 模板与求职信模板互不相干，不能混成一个。"""
        with _Repo() as r:
            r.template("同名", "cv")
            r.template("同名", "cover_letters")
            r.activate("张三", "同名", "cv")
            u = tu.usage()
            self.assertEqual(u.get(("cv", "同名")), ["张三"])
            self.assertNotIn(("cover_letters", "同名"), u)

    def test_pointer_variants_are_read(self):
        """指针是 AI 写的 markdown，写法会有变体——认不出就等于漏报使用者。"""
        with _Repo() as r:
            r.template("甲模板")
            d = r.tmp / "users" / "王五" / "templates"
            d.mkdir(parents=True)
            (d / "active-cv.md").write_text(
                "# Active CV\n\n- **Template:** 甲模板\n", encoding="utf-8")
            self.assertEqual(tu.usage().get(("cv", "甲模板")), ["王五"])

    def test_unreadable_pointer_is_not_guessed(self):
        """认不出就返回 None。猜错会把「没人用」说成「有人用」，反过来也一样。"""
        with _Repo() as r:
            d = r.tmp / "users" / "赵六" / "templates"
            d.mkdir(parents=True)
            (d / "active-cv.md").write_text("随便写了点什么\n", encoding="utf-8")
            self.assertEqual(tu.usage(), {})


class CollisionCheckIsAUsableGate(unittest.TestCase):
    """`--name` 的退出码就是闸门：1 = 换名，0 = 可以用。"""

    def test_busy_name_exits_one(self):
        with _Repo() as r:
            r.template("紧凑双列")
            r.activate("张三", "紧凑双列")
            self.assertEqual(tu.main(["--name", "紧凑双列"]), 1,
                             "有人正在用却放行了 —— 覆写会静默改掉他的产出")

    def test_registered_but_unused_exits_zero(self):
        with _Repo() as r:
            r.template("闲置模板")
            self.assertEqual(tu.main(["--name", "闲置模板"]), 0,
                             "没人用的模板不该拦着")

    def test_brand_new_name_exits_zero(self):
        with _Repo() as r:
            self.assertEqual(tu.main(["--name", "全新名字"]), 0)


class OrphanPointersAreSurfaced(unittest.TestCase):
    """指向已不存在的模板 —— 那个用户跑 /job-apply 会找不到骨架，得让他知道。"""

    def test_orphan_is_reported(self):
        import contextlib
        import io
        with _Repo() as r:
            r.activate("李四", "早就删了的模板")
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                tu.main([])
            out = buf.getvalue()
        self.assertIn("早就删了的模板", out)
        self.assertIn("找不到骨架", out, "没说清后果")


class WorkflowWiresTheGate(unittest.TestCase):
    """写了工具不接线，等于没写——本仓库反复出现的那一类。"""

    def test_add_template_calls_it(self):
        t = (ROOT / "workflows" / "job-add-template.md").read_text(encoding="utf-8")
        self.assertIn("template_usage.py", t,
                      "/job-add-template 没接上撞名检查，还是只有散文告诫")
        self.assertIn("退出码 1", t, "没说清退出码怎么用")


class TheCompileTestActuallyTestsTheFilledCopy(unittest.TestCase):
    """Step 4 那道编译检查要编译**填了假数据的那一份**，不是骨架。

    2026-09-01 实测：typst 分支写的是
    `typst compile <模板路径> /tmp/template_test.pdf` —— 三处都不对，
    而 typst 是**默认引擎**，多数人走的就是这条路：

    1. 编译的是骨架，`[占位符]` 原样留着 —— Step 1「填上像真的一样的假数据」
       对 typst 整步白做；
    2. Step 4.4 的版面检查因此是空的 —— 它要求「以这点假数据来说页数合理」，
       而根本没有假数据；
    3. Step 4.5 要删的 `_compile_test.pdf` 它从来不产生（产物去了 `/tmp/`），
       临时文件建了没用、真产物没人清。

    LaTeX 那条一直是对的（`<engine> … _compile_test.tex`）—— 也就是说
    **同一步里两个分支各写各的**，而只有一个是对的。
    """

    STEP4 = None

    def setUp(self):
        t = (ROOT / "workflows" / "job-add-template.md").read_text(encoding="utf-8")
        i = t.index("## Step 4")
        self.STEP4 = t[i:t.index("## Step 5", i)]

    def _code(self):
        """**只取第 2 步那一段的命令行。**

        第一版取的是整个 Step 4，于是断言在第 1 步的散文（「typst 是
        `_compile_test.typ`」）和第 5 步的清理清单（`_compile_test.pdf`）
        上就满足了 —— 变异测试当场照出来：把旧写法原样放回去，
        三条里两条**仍然是绿的**。收窄到真正要敲的那几行。
        """
        seg = self.STEP4[self.STEP4.index("2. 按所选引擎分支编译"):]
        seg = seg[:seg.index("\n3. ")]
        return "\n".join(l for l in seg.splitlines()
                         if not l.lstrip().startswith(">"))

    def test_both_engines_compile_the_temp_copy(self):
        code = self._code()
        for engine, src in (("typst", "_compile_test.typ"),
                            ("<engine>", "_compile_test.tex")):
            with self.subTest(engine=engine):
                self.assertRegex(
                    code, rf"{re.escape(engine)}[^\n]*{re.escape(src)}",
                    f"{engine} 那条没在编译 {src} —— 填假数据那一步就白做了")

    def test_the_artifact_is_the_one_step5_deletes(self):
        """产物名要和 Step 4.5 的清理清单对得上，否则删的是不存在的东西。"""
        self.assertIn("_compile_test.pdf", self._code(),
                      "编译命令没产出 `_compile_test.pdf`，而 Step 5 正要删它")

    def test_no_unix_only_path_in_the_command(self):
        """`/tmp/` 是 Unix 路径，而这个仓库在 Windows 上跑得最多。"""
        self.assertNotIn("/tmp/", self._code(),
                         "编译命令又写回 `/tmp/` 了")


if __name__ == "__main__":
    unittest.main()
