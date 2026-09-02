"""`/job-setup --section <名>` 用到的每个名字，都必须在文件里定义过跳到哪一节。

## 为什么

`setup.md` 里 `--section boundaries` / `--section search` 一共出现七处（Section 9 结尾、
Section 10 结尾、简历语言那条提示……），**却从没有一张表说这两个名字对应哪一节**。
而另一处还写着「编号是给 `--section` 定位用的」——**一处说编号、七处用名字**，两边对不上。

执行者只能靠猜。`boundaries` → 「能力边界与作品分层」猜得中是运气；
`search` 更容易偏（Section 10 叫 Job Search Configuration，但 Section 1 的联系方式、
Section 4 的技能里也都有和搜索相关的字）。**而这是个改用户资料的命令**，跑错节
就是把用户已经填好的另一节重新问一遍。

## 判据

从全文抽出所有 `--section <名>` 的用法，每个名字都必须出现在 Step 0 的映射表里。
新增可点名的小节时，表和用法一起改——这条测试保证不会只改一半。
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SETUP = ROOT / "workflows" / "job-setup.md"

USAGE = re.compile(r"--section\s+([a-z][a-z0-9_-]*)")


class EverySectionNameIsDefined(unittest.TestCase):

    def setUp(self):
        self.text = SETUP.read_text(encoding="utf-8")
        # 映射表在 Step 0 里：从 `--section <name>` 那句到下一个 `##` 标题。
        #
        # ⚠️ 只取**表格行**（`|` 开头），不要整段。第一版取整段，而同一段里
        # 那条解释性引用块本身就写着「`boundaries` → 「能力边界」猜得中是运气」——
        # 变异验证当场打脸：把表里那行改名之后，**解释文字里的 `boundaries`
        # 仍然满足断言**，测试照样绿。断言撞上解释自己的文字，这个仓库里反复出现，
        # 解法一律是把判据收到结构上（这里是「必须是一行表格」）。
        i = self.text.index("`--section <名>`")
        block = self.text[i:self.text.index("\n## ", i)]
        self.table = "\n".join(l for l in block.splitlines()
                               if l.lstrip().startswith("|"))

    def test_user_docs_only_name_defined_sections(self):
        """`SETUP.md` / `README.md` 教用户敲的 `--section` 名字，同样要在表里。

        第一版只扫 `workflows/job-setup.md` 自己用到的名字。可**真正让用户敲命令的是
        用户文档**——实测 `SETUP.md` 写着 `/job-setup --section skills` 与
        `--section experience`，而映射表里只有 `boundaries` / `search` / 纯数字。
        用户照着敲，执行者只能猜跳到哪一节；而这是个改用户资料的命令，猜偏了
        就是把已经填好的另一节重新问一遍。
        """
        bad = []
        for name in ("SETUP.md", "README.md"):
            p = ROOT / name
            if not p.is_file():
                continue
            for n in sorted(set(USAGE.findall(p.read_text(encoding="utf-8")))):
                if n == "name":
                    continue
                if f"`{n}`" not in self.table:
                    bad.append(f"{name}: `--section {n}`")
        self.assertEqual(
            bad, [],
            "用户文档教了这些 `--section` 名字，而 setup.md 的映射表里没有：\n  "
            + "\n  ".join(bad)
            + "\n用户照着敲，执行者只能猜——而 /job-setup 会改他已经填好的资料。")

    def test_the_flag_is_actually_used(self):
        """控制用例：真有人用这个参数，否则下面那条是空跑。"""
        names = set(USAGE.findall(self.text))
        self.assertTrue(
            names, "setup.md 里没有任何 `--section <名>` 用法——"
            "参数没了就把这条测试一起删，别留一条永远绿的")

    def test_every_used_name_appears_in_the_mapping_table(self):
        names = set(USAGE.findall(self.text))
        # 表本身也含 `--section` 那句里的占位符，排掉
        names -= {"name"}
        missing = sorted(n for n in names if f"`{n}`" not in self.table)
        self.assertEqual(
            missing, [],
            f"这些 --section 名字没在 Step 0 的映射表里定义：{missing}"
            "\n执行者只能猜跳到哪一节，而 /job-setup 是改用户资料的命令——"
            "\n猜偏了就是把已经填好的另一节重新问一遍。"
            "\n新增可点名的小节时，映射表和用法要一起改。")

    def test_the_table_says_numbers_work_too(self):
        """编号也得认。文件别处说「编号是给 --section 定位用的」，
        表里不写编号就等于把那句话悬空了。"""
        self.assertTrue(
            any(w in self.table for w in ("纯数字", "编号")),
            "映射表没说编号也能用，而文件别处正是这么讲的")


if __name__ == "__main__":
    unittest.main()
