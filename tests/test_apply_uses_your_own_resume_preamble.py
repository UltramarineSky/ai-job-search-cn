"""定制简历的排版必须取自用户自己那份 `main.typ`，不是共享模板。

## 为什么

`users/<用户>/resume/main.typ` 按设计是**自包含**的：`/job-setup` 生成它时就把
`resume/template.typ` 内联了进去（AGENTS.md「活动用户与多用户」写明这一条）。
也就是说——**它的正文是对着它自己那份前导写的**。

`/job-apply` 第 5b 步要把「骨架」的定义复制到定制版产物顶部。如果骨架取的是共享的
`resume/template.typ`，而用户改过自己 `main.typ` 的前导，两边就分叉了。

## 分叉不会报错，只会静默变样

实测的一次分叉：

| | main.typ | 共享模板 |
|---|---|---|
| `常规` | 330（MiSans 的 Regular） | 400 |
| `加重` | 520 | 600 |
| 成果数字加重的 `show regex` | 生效的代码 | 只在注释里当示例 |
| 字体链首位 | MiSans | Noto Sans SC |

两边**函数名完全一致**（`resume`/`section`/`entry`/`链`/`成果`），所以定制版照样
编译得过、typst 也不报警。但产出的字重全错一档（装了 MiSans 时 `400` 会选到
Medium，正文过重），候选人那几个成果数字不再加粗——
**用户以为发出去的是自己那份简历。**

## 判据

`apply.md` 的 5.0 决议表在「没有激活自定义模板」这一支里，骨架必须指向
`resume/main.typ`（用户自己那份），而不是共享的 `resume/template.typ`。
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APPLY = ROOT / "workflows" / "job-apply.md"


class TailoredResumeLooksLikeYourBaseResume(unittest.TestCase):

    def setUp(self):
        text = APPLY.read_text(encoding="utf-8")
        # 决议表那一段：从 5.0 标题到 5a 标题
        self.table = text.split("### 5.0")[1].split("### 5a")[0]

    def test_the_resolution_table_exists(self):
        """控制用例：真抽到了决议表，否则下面两条是空跑。"""
        self.assertIn("激活文件", self.table, "抽不到 5.0 决议表——判据可能失效了")
        self.assertIn("不存在", self.table, "决议表里没有「不存在」那一支")

    def test_the_default_skeleton_is_the_users_own_main_typ(self):
        """没激活模板时，骨架取用户自己那份 main.typ 的前导。"""
        row = [l for l in self.table.splitlines() if l.strip().startswith("| **不存在**")]
        self.assertTrue(row, "决议表里找不到「不存在 →」那一行")
        # ⚠️ 必须**按单元格**判，不能按整行。这一行有两列（简历 / 求职信），
        # 第一版对整行 assertIn("main.typ")——变异验证当场打脸：只把简历那半改回
        # 共享模板，求职信那半仍写着 `cover_letter/main.typ`，整行照样含 main.typ，
        # 测试全绿。**判据的粒度比判据的内容更容易出错。**
        cells = [c.strip() for c in row[0].strip().strip("|").split("|")]
        self.assertGreaterEqual(len(cells), 3, f"决议表这一行不是三列：{row[0][:120]}")

        # ⚠️ 两列**不对称**，别顺手把它们改成一样的。
        # 第一版把求职信那列也断言成 `cover_letter/main.typ`——而 `/job-setup` **从不创建**
        # 那个文件（用户目录里连 `cover_letter/` 都不建）。求职信是每次按岗现写的，
        # 没有承载内容的基版可继承；简历有（`resume/main.typ` 就是用户的基简历，
        # 正文从那儿来，所以排版也该从那儿来）。
        self.assertIn(
            "resume/main.typ", cells[1],
            f"简历骨架没指向用户自己的 resume/main.typ：\n  {cells[1][:140]}"
            "\n\nmain.typ 是自包含的，正文对着它自己那份前导写；"
            "\n去复制共享模板的前导，两边一分叉产出就和基简历不是一个样子——"
            "\n而且函数名一致所以照样编译得过，不会有任何报错。")
        self.assertIn(
            "cover_letter/template.typ", cells[2],
            f"求职信骨架应当是共享模板：\n  {cells[2][:140]}"
            "\n\n没有「基求职信」这回事——/job-setup 不创建 cover_letter/main.typ，"
            "\n指过去就是指了一个永远不存在的文件。")
        self.assertNotIn(
            "cover_letter/main.typ", cells[2],
            "求职信骨架指向了 cover_letter/main.typ，而 /job-setup 从不创建它——"
            "这是个悬空引用")

    def test_the_cv_reference_points_at_the_same_rule(self):
        """`05-cv-templates.md` 也要指向这条 —— 它是起草简历前必读的那一份。

        05 有三处把 `resume/template.typ` 称作「模板」，而 5.0 决议表说
        运行时的骨架是**用户自己那份 `main.typ` 的前导**。
        两者不冲突（一个是种子、一个是骨架），**但 05 里原来一个字都没提**，
        而这条失败是**静默的**：字重全错一档，编译照样通过。

        05 的用法示例里还有 `#import "template.typ"` —— 那是在说明共享模板的
        调用方式（`test_cv_doc_example_compiles` 把 template.typ 拷到旁边验过），
        可它长得正像「定制版该长的样子」，而定制版必须自包含、不写 import。
        两处都补了说明（2026-08-21 通读时发现）。
        """
        cv = ROOT / "workflows" / "reference" / "05-cv-templates.md"
        t = cv.read_text(encoding="utf-8")
        self.assertIn(
            "5.0", t,
            "05 没指向 `job-apply.md` 的 5.0 决议表 —— "
            "读它的人会把 `template.typ` 当成运行时骨架")
        self.assertIn(
            "自包含", t,
            "05 没说定制版必须自包含 —— 它的用法示例里有 `#import`，"
            "照抄进 applications/ 目录会编译失败")

    def test_it_says_to_copy_the_whole_preamble(self):
        """必须说清「整段照抄」，漏抄哪一样都会静默变样。

        分叉可能出现在字体链、字重常量、辅助函数、或 `resume()` 内部的 show 规则上——
        只说「复制函数定义」会让人以为抄那三个函数就够了。
        """
        text = APPLY.read_text(encoding="utf-8")
        step5b = text.split("### 5b.")[1].split("### 5c.")[0]
        self.assertTrue(
            any(w in step5b for w in ("整段照抄", "全部内容", "包括字体链")),
            "5b 没说清要把前导整段照抄——"
            "漏抄字重常量或 show 规则，产出会静默变样")


if __name__ == "__main__":
    unittest.main()
