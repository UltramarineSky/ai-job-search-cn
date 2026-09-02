"""话术是**直接粘出去**的，正文里不许混进 markdown 标记。

## 为什么

开场白的用途只有一个：整段选中、粘进猎聘/BOSS 的聊天框。它在文件里常被写成
markdown 引用块（视觉上把「要发出去的那段」框起来），而 `> ` 会**原样跟着粘过去**
——HR 收到的是一段每行带尖括号的话。

而且这不只是文件好不好看的问题：**面板上的复制按钮取的就是解析出来的这段正文**
（`build_dashboard.parse_outreach` → `export_web_data` → `JobReadout`）。
解析器原来只剥尾部的自检备注，不管整段引用，于是标记一路走到用户的剪贴板。

同一条对邮件正文与网申自评成立——它们同样是整段贴进输入框的。

## 两层

1. **解析层兜底**：`_strip_wordcount` 在整段都是引用行时把行首 `> ` 剥掉。
   这是补救，护住已经写成引用块的存量文件。
2. **产出层规范**：`06-outreach-templates.md` 的产出格式明写 `<正文>` 是裸文本。
   补救不能变成「可以随手写引用块」的理由。
"""

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import build_dashboard as bd  # noqa: E402

TPL = ROOT / "workflows" / "reference" / "06-outreach-templates.md"


class TheParserStripsQuoteMarkers(unittest.TestCase):
    """存量文件写成引用块时，解析出来的正文不能带 `>`。"""

    def test_a_fully_quoted_greeting_comes_back_clean(self):
        got = bd._strip_wordcount("> 您好，看到贵司招 AI 产品经理。\n>\n> 想问下这个岗…")
        self.assertNotIn(">", got, f"引用标记没剥干净：{got!r}")
        self.assertTrue(got.startswith("您好"), got)
        self.assertIn("想问下这个岗", got, "剥标记时把正文也吃掉了")

    def test_plain_text_is_untouched(self):
        src = "您好，看到贵司招 AI 产品经理。\n\n想问下这个岗现在最缺哪一块？"
        self.assertEqual(bd._strip_wordcount(src), src)

    def test_a_stray_quote_line_inside_prose_is_not_stripped(self):
        """只在**整段**都是引用行时才剥——正文里偶然引用 JD 原话的那行要留着。

        这一条防的是矫枉过正：把「> JD 原话」也剥掉会让引用失去边界，
        读的人分不清哪句是 JD 说的。
        """
        src = "您好。JD 里写着：\n> 熟悉 Skills、MCP\n这条正是我的日常。"
        self.assertIn(">", bd._strip_wordcount(src),
                      "正文中间的单行引用被误剥了")

    def test_the_word_count_tail_still_goes(self):
        """两种字数尾巴都要剥——它们是元数据，跟着粘出去就是事故。"""
        for tail in ("（字数：168）", "（**168 字**，不含空白。）"):
            with self.subTest(tail=tail):
                got = bd._strip_wordcount(f"您好，看到贵司招 AI 产品经理。\n\n{tail}")
                self.assertNotIn("字", got.replace("产品", ""),
                                 f"字数尾巴没剥：{got!r}")


class TheTemplateSaysItPlainly(unittest.TestCase):
    """规范里要写死，否则下一个生成器还会套引用块。"""

    def test_the_output_format_forbids_markers_and_metadata(self):
        t = TPL.read_text(encoding="utf-8")
        i = t.find("## 产出格式")
        self.assertNotEqual(i, -1, "找不到产出格式一节")
        seg = t[i:]
        self.assertIn("只许有要发出去的那段字", seg,
                      "产出格式没写明小节里不许有别的东西")
        self.assertIn("字数", seg, "没说清字数不能放进小节里")
        self.assertIn("自检", seg, "没给出自检信息该放哪儿")


class TheGeneratedFilesAreClean(unittest.TestCase):
    """已经落盘的话术：开场白那一节解析出来不许带标记。

    跑在真实用户目录上；没有投递目录就跳过（新 clone、CI）。
    """

    def test_every_greeting_on_disk_parses_clean(self):
        au = ROOT / ".active_user"
        if not au.is_file():
            self.skipTest("没有活动用户")
        apps = ROOT / "users" / au.read_text(encoding="utf-8").strip() / \
            "documents" / "applications"
        if not apps.is_dir():
            self.skipTest("还没有投递目录")
        bad, empty = [], []
        for f in sorted(apps.glob("*/outreach.md")):
            g = bd.parse_outreach(f.read_text(encoding="utf-8")).get("greeting") or ""
            if not g.strip():
                empty.append(f.parent.name)
                continue
            if re.search(r"^\s*[>\-*#]", g, re.M):
                bad.append(f"{f.parent.name}: {g[:40]!r}  ← markdown 标记")
            if re.search(r"（\s*(?:字数|\*\*\d+\s*字)", g):
                bad.append(f"{f.parent.name}: 正文里混着字数统计")
            if "<!--" in g:
                bad.append(f"{f.parent.name}: 正文里混着 HTML 注释")
        self.assertEqual(bad, [],
                         "这些开场白解析出来还混着不该发出去的东西，"
                         "整段粘进聊天框会一起发出去：\n  " + "\n  ".join(bad))
        # 空也要报：剥标记剥过头会把正文吃光，而空串在面板上表现为
        # 「话术是空的」，比带标记更难发现。
        self.assertEqual(empty, [],
                         f"这些投递目录的开场白解析成空（可能被剥过头）：{empty}")

    def test_every_email_body_on_disk_parses_clean(self):
        """**邮件正文同样是整段贴出去的**，这条本文件开头就写着，却只验了开场白。

        代价（2026-08-18 实测，6 份真实邮件里 3 份中招）：邮件正文只剥了开头那个
        「**正文：**」标签，于是这些东西一路留到用户的剪贴板——

          > 每行的引用前缀（整段引用块的邮件，粘出去每行都带尖括号）
          **附件命名**：某某-某某岗-简历.pdf        ← 写给你自己看的操作备注
          ⚠️ **附件改名**：落盘的文件叫 resume.pdf…  ← 同上
          **收件人留空**：…                          ← 同上
          （正文字数：397，含署名、不含主题与附件名）
          > 字数校验：约 385 字，≤400 ✓
          ```                                        ← 主题那段围栏的收尾
          **正文**                                   ← 排版标签

        而这段字**是要发给用人方的**：备注混进去比标记混进去更难看——它等于把
        「记得给附件改个名」发给了对方。
        """
        au = ROOT / ".active_user"
        if not au.is_file():
            self.skipTest("没有活动用户")
        apps = ROOT / "users" / au.read_text(encoding="utf-8").strip() / \
            "documents" / "applications"
        if not apps.is_dir():
            self.skipTest("还没有投递目录")
        bad, seen = [], 0
        for f in sorted(apps.glob("*/outreach.md")):
            b = bd.parse_outreach(f.read_text(encoding="utf-8")).get("email_body") or ""
            if not b.strip():
                continue                      # 没写邮件那一节，不是问题
            seen += 1
            for pat, why in (
                (r"^\s*>", "行首引用前缀"),
                (r"^\s*```", "代码围栏"),
                (r"\*\*正文\*\*", "排版标签「**正文**」"),
                (r"（[^）]*字数[：:]", "字数统计"),
                (r"字数校验", "字数自检"),
                (r"附件命名|附件改名|收件人留空", "写给你自己看的操作备注"),
                (r"<!--", "HTML 注释"),
            ):
                if re.search(pat, b, re.M):
                    bad.append(f"{f.parent.name}: {why}")
        self.assertEqual(
            bad, [],
            "这些邮件正文里混着不该发给用人方的东西：\n  " + "\n  ".join(bad))


class CommentsAtBothEndsDoNotEatTheBody(unittest.TestCase):
    """开头提示注释 + 尾部自检注释同时在场时，正文必须活下来。

    `<!--.*?-->` 的非贪婪只是「找最近的 `-->`」，配上 `$` 锚点后，匹配从
    **第一个** `<!--` 一直吞到结尾——两头都有注释的开场白被整段吃成空串
    （实测复现），而空串在面板上表现为「话术是空的」，比带标记更难发现。
    盘上文件那条守卫只扫当前真实文件，盖不住这个输入类，所以直接测函数。
    """

    def test_body_survives_comments_at_both_ends(self):
        got = bd._strip_wordcount(
            "<!-- 提示：复制后直接粘进聊天框 -->\n"
            "你好，看到贵司岗位…\n"
            "<!-- 字数校验：42 字，达标 -->")
        self.assertEqual(got, "你好，看到贵司岗位…",
                         f"正文被注释剥离吃掉了：{got!r}")

    def test_multiline_comments_at_both_ends(self):
        got = bd._strip_wordcount(
            "<!-- 提示\n第二行 -->\n正文在这。\n<!-- 自检\n两行 -->")
        self.assertEqual(got, "正文在这。")

    def test_single_comment_cases_still_work(self):
        self.assertEqual(bd._strip_wordcount("你好。\n<!-- 字数：40 -->"), "你好。")
        self.assertEqual(bd._strip_wordcount("<!-- 提示 -->\n你好。"), "你好。")


if __name__ == "__main__":
    unittest.main()
