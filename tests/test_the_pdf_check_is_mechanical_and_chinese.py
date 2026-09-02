# -*- coding: utf-8 -*-
"""字体没嵌进 PDF，你打开看一切正常，招聘系统抽出来一片方块 —— 而没人在查。

`job-apply.md` Step 5e 原来把这一条写成**清单项**，让人对着 `pdftotext` 的输出
肉眼判：

> - [ ] **中文无乱码**：提取文本中不含 `□` 与替换字符，CJK 字符数与简历实际内容量相称

这纯机械，人判不准，也不会每次都判。而它的失败方式是最坏的那种：
**PDF 看着完全正常，网申系统抽出来一片方块，简历被判成没内容，你收不到任何提示。**

工具本来就在（`tools/verify_pdf.py`），三件事同时成立：

1. **从没有任何工作流调过它** —— 全仓库只有测试和 CLI 契约的豁免名单提过它；
2. **它恰好缺这两条检查** —— 只查存在、页数、字符数、含某串，不查乱码也不查汉字占比；
3. **整个命令行界面是英文的**，说明原文是
   "Verify a PDF's page count and ATS-readable text layer." ——
   而 `ATS` 正是 `AGENTS.md` 词表里点名不许上屏的英文码。
   既有的英文守卫（`test_no_english_lines_spoken_to_the_user`）只扫
   `workflows/` 与 `.claude/`，**从没扫过命令行的 `--help`**，所以它一直没被看见。

三件一起修：补检查、翻中文、把 Step 5e 的前两条从「肉眼比对」换成
**能直接跑的 `grep` 和一个具体的数**。

（本来想让 5e 直接跑那个脚本，撤回了：`/job-apply` **对外承诺不依赖
Python**，README 与 SETUP 都这么写。脚本那条登记在 `AGENTS.md` 的
能力对照表里，给手里有 Python 的人。）

## 汉字占比默认关

第一版让它默认开，当场顶红了一条用英文样例的既有测试 —— 外企/英文岗的简历本来
就没有汉字。**工具不猜简历是哪种语言**，中文简历由调用方加 `--cjk`。
乱码那一条无条件查：替换字符在哪种语言里都是错的。
"""
import re
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
from _srcscan import strip_comments  # noqa: E402
from tools.verify_pdf import (CJK_FLOOR, VerificationError,  # noqa: E402
                              cjk_ratio, verify_pdf)

APPLY = (ROOT / "workflows" / "job-apply.md").read_text(encoding="utf-8")


def _step5e() -> str:
    i = APPLY.index("### 5e.")
    m = re.search(r"^### ", APPLY[i + 6:], re.M)
    return APPLY[i:i + 6 + (m.start() if m else 2600)]


def _check(text, path, **kw):
    """跑一次校验，`pdftotext` 的输出由 `text` 顶替。"""
    with patch("tools.verify_pdf.run_tool", return_value=text):
        return verify_pdf(path, **kw)


class MojibakeIsCaughtInAnyLanguage(unittest.TestCase):
    def setUp(self):
        self.pdf = ROOT / "tests" / "__mojibake_probe.pdf"
        self.pdf.write_bytes(b"%PDF-1.4\n")
        self.addCleanup(self.pdf.unlink)

    def test_the_replacement_character_fails(self):
        with self.assertRaisesRegex(VerificationError, "乱码"):
            _check("张三 �� 产品经理", self.pdf)

    def test_the_box_glyph_fails(self):
        with self.assertRaisesRegex(VerificationError, "乱码"):
            _check("张三 □□□ 产品经理", self.pdf)

    def test_it_names_the_likely_cause(self):
        """光说「有乱码」用户不知道去修什么。国内这条路很具体：字体没嵌进去。"""
        with self.assertRaisesRegex(VerificationError, "字体没嵌进"):
            _check("张三 � 产品经理", self.pdf)

    def test_it_fires_without_the_cjk_flag(self):
        """乱码无条件查 —— 英文简历里出现替换字符同样是坏的。"""
        with self.assertRaisesRegex(VerificationError, "乱码"):
            _check("John Smith � Product Manager", self.pdf, expect_cjk=False)

    def test_clean_chinese_passes(self):
        _check("张三 产品经理 上海 十年经验 负责智能体平台", self.pdf,
               expect_cjk=True)


class TheChineseRatioIsOptedInto(unittest.TestCase):
    def setUp(self):
        self.pdf = ROOT / "tests" / "__ratio_probe.pdf"
        self.pdf.write_bytes(b"%PDF-1.4\n")
        self.addCleanup(self.pdf.unlink)

    def test_an_english_resume_passes_by_default(self):
        """**默认关。** 第一版默认开，当场把一条用英文样例的既有测试顶红了。"""
        _check("John Smith Product Manager Shanghai", self.pdf)

    def test_an_english_resume_fails_when_you_claim_it_is_chinese(self):
        with self.assertRaisesRegex(VerificationError, "汉字"):
            _check("John Smith Product Manager Shanghai", self.pdf, expect_cjk=True)

    def test_a_real_chinese_resume_clears_the_floor(self):
        text = "张三 · 上海 · 138xxxx · AI 产品经理，负责智能体平台与数据管线"
        self.assertGreaterEqual(cjk_ratio(text), CJK_FLOOR)
        _check(text, self.pdf, expect_cjk=True)

    def test_the_floor_sits_far_below_a_real_resume(self):
        """**门槛的意义在于余量。** 实测真实简历是 55%，而字体没嵌进去时
        接近 0 —— 两端离得极远，所以门槛压低不影响灵敏度，却能不误伤
        中英混排很重的简历。这一条盯着别有人把它往真实值上抬。"""
        self.assertLess(CJK_FLOOR, 0.3,
                        "门槛抬到接近真实值了 —— 混排重的简历会被误判")
        self.assertGreater(CJK_FLOOR, 0.05, "低到抓不住空文本层了")

    def test_a_broken_text_layer_is_nowhere_near_the_floor(self):
        """字体没嵌进去时抽出来只剩标点和数字。"""
        broken = "· · · 2019-2026 | 138 | 上"
        self.assertLess(cjk_ratio(broken), CJK_FLOOR)
        with self.assertRaisesRegex(VerificationError, "汉字"):
            _check(broken, self.pdf, expect_cjk=True)

    def test_an_empty_text_layer_is_zero_not_a_crash(self):
        self.assertEqual(cjk_ratio(""), 0.0)
        self.assertEqual(cjk_ratio(None), 0.0)

    def test_the_floor_has_a_stated_basis(self):
        src = (ROOT / "tools" / "verify_pdf.py").read_text(encoding="utf-8")
        i = src.index("CJK_FLOOR = ")
        seg = " ".join(src[max(0, i - 900):i].split())
        self.assertRegex(seg, r"不是拍的", "这个门槛没说出处")
        # **实测数要能对上真跑一遍的结果。** 第一版这里写的是「0.42 和 0.39」——
        # 那是我编的，真跑 `pdftotext` 抽出来两份都是 55%。
        # 断言钉住真值，编一个数就红。
        self.assertRegex(seg, r"两份都是 55%", "没留下实测的数，或者数不对")
        self.assertRegex(seg, r"误报的代价是拦住一次投递", "没说清为什么要留余量")


class TheCommandLineSpeaksChinese(unittest.TestCase):
    def _help(self):
        r = subprocess.run([sys.executable, "-X", "utf8",
                            str(ROOT / "tools" / "verify_pdf.py"), "--help"],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=60)
        return (r.stdout or "") + (r.stderr or "")

    def test_no_bare_english_prose_line(self):
        cjk = re.compile(r"[一-鿿]")
        bad = [ln.strip() for ln in self._help().splitlines()
               if ln.strip() and re.search(r"[A-Za-z]{4,}", ln)
               and not cjk.search(ln)
               and not ln.strip().startswith(("usage:", "-", "python", "options:",
                                              "positional", "optional", "pdf"))
               # `usage:` 那行 argparse 会折行，续行以 `[` 开头（`[--cjk]`）。
               # 那是参数名不是散文 —— 第一版把它当违规抓了。
               and not ln.strip().startswith("[")]
        self.assertEqual(bad, [], f"--help 里还有整行英文：{bad}")

    def test_the_banned_code_is_gone(self):
        """`ATS` 在 `AGENTS.md` 的词表里被点名不许上屏。"""
        self.assertNotIn("ATS", self._help())

    def test_the_new_flag_is_explained(self):
        h = self._help()
        self.assertIn("--cjk", h)
        self.assertIn("英文简历别加", h)

    def test_the_user_facing_messages_are_chinese(self):
        src = (ROOT / "tools" / "verify_pdf.py").read_text(encoding="utf-8")
        for eng in ("PDF does not exist", "Verified ", "Error: ",
                    "expected at least", "install poppler-utils"):
            with self.subTest(eng=eng):
                self.assertNotIn(eng, src, f"还留着英文串「{eng}」")


class TheMissingToolFallbackDoesNotDependOnWording(unittest.TestCase):
    """翻译一次就断的那种判据 —— 这次真断了一回。

    `count_pages` 在没装 pdfinfo 时退回数 `pdftotext` 的换页符，判据原来是
    `if "was not found" not in str(exc)` —— **匹配英文错误文案**。
    2026-08-23 把文案翻成中文，兜底当场失效：只有 pdftotext 的机器上
    `--pages` 又开始永远报错，而那正是 `count_pages` 自己的注释记着的旧 bug
    （「10 份刚编译好的简历全被误判」）。改成看 `missing_tool` 字段。
    """

    def test_the_error_carries_which_tool_is_missing(self):
        err = VerificationError("随便什么话", missing_tool="pdfinfo")
        self.assertEqual(err.missing_tool, "pdfinfo")

    def test_a_plain_error_has_no_tool(self):
        self.assertIsNone(VerificationError("页数不对").missing_tool)

    def test_the_fallback_reads_the_field_not_the_text(self):
        code = strip_comments((ROOT / "tools" / "verify_pdf.py")
                              .read_text(encoding="utf-8"))
        i = code.index("def count_pages(")
        seg = code[i:code.index(chr(10) + "def ", i + 10)]
        self.assertIn("missing_tool", seg, "兜底又改回按文案匹配了")
        self.assertNotIn("was not found", seg)

    def test_the_fallback_still_works_end_to_end(self):
        from tools.verify_pdf import count_pages

        def fake(cmd):
            if cmd[0] == "pdfinfo":
                raise VerificationError("没装 pdfinfo", missing_tool="pdfinfo")
            return "第一页第二页"

        with patch("tools.verify_pdf.run_tool", side_effect=fake):
            self.assertEqual(count_pages(Path("x.pdf")), 2)

    def test_the_producer_really_sets_the_field(self):
        """**走真实那条路。** 上面几条自己造错误对象，
        `run_tool` 里那个 `missing_tool=command[0]` 删掉它们照样绿
        （变异实测）。这一条让 `FileNotFoundError` 真的发生一次。"""
        from tools.verify_pdf import run_tool
        with self.assertRaises(VerificationError) as cm:
            run_tool(["这个命令肯定不存在_zzz", "x"])
        self.assertEqual(cm.exception.missing_tool, "这个命令肯定不存在_zzz")

    def test_a_plain_command_failure_carries_no_tool(self):
        """命令在、但读不动文件 —— 那不是「没装」，不该进兜底。"""
        import subprocess as sp
        from tools.verify_pdf import run_tool
        with patch("tools.verify_pdf.subprocess.run",
                   side_effect=sp.CalledProcessError(1, "pdfinfo", "", "坏了")):
            with self.assertRaises(VerificationError) as cm:
                run_tool(["pdfinfo", "x.pdf"])
        self.assertIsNone(cm.exception.missing_tool)

    def test_another_missing_tool_is_not_swallowed(self):
        """pdftotext 缺席不该被当成「pdfinfo 缺席」而走进兜底 ——
        那条兜底本身就要靠 pdftotext，进去只会再撞一次同样的墙。

        **验的是「没去试」，不是「最后报了 pdftotext」**：
        兜底里那次调用同样会报 pdftotext，只看错误文案两种情况长得一样
        （变异实测：把判据放宽成 `not exc.missing_tool` 时这条照样绿）。
        所以数调用次数 —— 不进兜底就只该调一次。"""
        from tools.verify_pdf import count_pages
        calls = []

        def fake(cmd):
            calls.append(cmd[0])
            raise VerificationError("没装 pdftotext", missing_tool="pdftotext")

        with patch("tools.verify_pdf.run_tool", side_effect=fake):
            with self.assertRaisesRegex(VerificationError, "pdftotext"):
                count_pages(Path("x.pdf"))
        self.assertEqual(calls, ["pdfinfo"],
                         f"pdftotext 缺席时还去试了兜底：{calls}")


class Step5eGivesACommandNotAnEyeball(unittest.TestCase):
    """**它不能跑那个脚本 —— `/job-apply` 对外承诺不依赖 Python。**

    第一版把 5e 改成了 `python tools/verify_pdf.py …`，
    `test_materials_gap_nudge.test_the_batch_does_not_introduce_a_python_dependency`
    当场顶红：README 与 SETUP 都写着这条命令不需要 Python，没装的人就用不了了。
    那是**用户可见的承诺**，不是内部偏好，撤回。

    改成给可直接跑的 `grep`（`pdftotext` 本来就在这一步用着）和一个具体的数，
    脚本那条留给「手里有 Python」的人，登记在 `AGENTS.md` 的能力对照表里。
    """

    def test_it_no_longer_asks_a_human_to_eyeball(self):
        """**验它不再是清单项，不是「这几个字不许出现」。**
        下面那段解释里引用了那句旧规则（说明为什么撤掉它）——
        整段扫会撞上自己的解释，这个坑在本仓库有名字。"""
        seg = _step5e()
        self.assertIn("用命令判，别肉眼比对", seg)
        items = [ln for ln in seg.splitlines() if ln.strip().startswith("- [ ]")]
        self.assertTrue(items, "清单整个没了")
        for ln in items:
            with self.subTest(item=ln.strip()[:24]):
                self.assertNotIn("相称", ln, "还有清单项让人判「相称」")

    def test_it_gives_a_runnable_mojibake_check(self):
        seg = _step5e()
        self.assertIn("grep -c", seg, "没给能直接跑的命令")
        self.assertIn("必须是 0", seg, "没说这条命令该出什么数")

    def test_it_gives_a_number_for_the_ratio(self):
        """「相称」不是判据，「15%」才是。"""
        seg = _step5e()
        self.assertIn("15% 以上", seg)
        self.assertIn("CJK_FLOOR", seg, "没指向那个门槛的出处")

    def test_the_number_matches_the_constant(self):
        """文档里那个数和代码里的常量对不上，就是两处各说各的。"""
        self.assertIn(f"{CJK_FLOOR:.0%} 以上", _step5e())

    def test_it_exempts_english_resumes(self):
        self.assertIn("英文简历不适用这一条", _step5e())

    def test_it_says_why_this_failure_is_the_worst_kind(self):
        seg = " ".join(_step5e().split())
        self.assertRegex(seg, r"网申系统抽出来一片方块")
        self.assertRegex(seg, r"而你收不到任何提示")

    def test_it_does_not_reintroduce_a_python_dependency(self):
        """**这条和 `test_materials_gap_nudge` 那条重复是有意的。**
        那边扫整份文件，这里盯 5e —— 下一个人来改 5e 时，
        红的这条就在他改的那一段旁边。"""
        self.assertNotRegex(_step5e(), r"python\s+tools/",
                            "5e 又要 Python 了 —— README 承诺过不用")

    def test_the_tool_is_registered_where_python_is_allowed(self):
        """脚本不能进 `job-apply.md`，但也不该继续当孤儿 ——
        它此前从没有任何工作流提过。"""
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("tools/verify_pdf.py", agents,
                      "能力对照表里没登记它，它又成孤儿了")
        i = agents.index("tools/verify_pdf.py")
        self.assertIn("--cjk", agents[i:i + 200])

    def test_the_contact_check_survives(self):
        self.assertIn("**联系方式为可选中的文字**", _step5e())

    def test_the_human_judgement_items_survive(self):
        """阅读顺序、关键词覆盖、占位符外泄仍然要人判。"""
        seg = _step5e()
        for item in ("**阅读顺序正确**", "**JD 关键词覆盖**", "**无占位符/假设值外泄**"):
            with self.subTest(item=item):
                self.assertIn(item, seg)

    def test_the_raw_extraction_is_still_there(self):
        seg = _step5e()
        self.assertIn("pdftotext -layout -enc UTF-8", seg)
        self.assertIn("`-enc UTF-8` 不可省略", seg)

    def test_the_placeholder_rule_still_points_at_one_source(self):
        self.assertIn("不要在这里另写一份", _step5e())


if __name__ == "__main__":
    unittest.main()
