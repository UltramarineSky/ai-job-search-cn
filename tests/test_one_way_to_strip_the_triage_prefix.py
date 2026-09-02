# -*- coding: utf-8 -*-
"""「粗筛：」这个前缀，全仓库只能有一种削法。

实测 2026-08-30：**18 处**在处理它，三种写法、**两种行为**：

    re.sub(r"^粗筛[：:]\\s*", "", …)    认全角半角两种冒号，且只削前缀
    .replace("粗筛：", "")             只认全角，而且是**全串替换**、不限前缀
    .startswith("粗筛：")              同上，只认全角

`.replace` 那一支两处都比正则那一支弱。库里眼下全是全角前缀（756 条），
所以**这是个潜伏的分叉，不是活的 bug** —— 但两种行为并存意味着
「同一个判词，问不同的函数得到不同答案」，而这个仓库为这一类形状栽过太多次：
`gates_in_verdict` 那次单复数混用漏 22 个、`adjust_of` 那次两个名字丢掉 −5、
门名那次两个住址只查了一个。收成 `_cli.strip_triage` / `_cli.is_triage`。

`doctor.py` 那一份留着 —— 它按契约不 import 本仓库任何模块（要在什么都没配好
时裸跑），和 `norm_url` / `QUIET_DAYS` 是同一类抄件，源码里标注了。
"""
import pathlib
import re
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import _cli  # noqa: E402

#: 按契约允许自己写一份的。**每一条都要说清为什么。**
EXEMPT = {"doctor.py": "契约：不 import 本仓库任何模块，要在什么都没配好时裸跑",
          "_cli.py": "正本就在这里，strip_triage / is_triage 两个函数都在它里面"}

_HAND = re.compile(r"""粗筛[：:]?\s*["']?\s*,\s*["']["']|粗筛\[：:\]|"粗筛："\)""")


class OnlyOneImplementation(unittest.TestCase):
    def test_no_tool_rolls_its_own(self):
        for f in sorted((ROOT / "tools").glob("*.py")):
            if f.name in EXEMPT:
                continue
            code = "\n".join(ln for ln in f.read_text(encoding="utf-8").splitlines()
                             if not ln.lstrip().startswith("#"))
            with self.subTest(module=f.name):
                self.assertNotRegex(
                    code, _HAND,
                    f"{f.name} 自己削了一遍「粗筛：」前缀 —— 走 "
                    f"_cli.strip_triage / _cli.is_triage，别再写一份")

    def test_every_exemption_says_why(self):
        for name, why in EXEMPT.items():
            with self.subTest(module=name):
                self.assertTrue((ROOT / "tools" / name).is_file())
                self.assertGreater(len(why), 8)

    def test_the_doctor_copy_is_marked_as_one(self):
        """抄件要标注，不然下一个人以为是漏网的，删掉它就把 doctor 弄坏了。"""
        src = (ROOT / "tools" / "doctor.py").read_text(encoding="utf-8")
        i = src.index("^粗筛[：:]")
        self.assertIn("strip_triage", src[max(0, i - 400):i])
        self.assertIn("不是漏网的", src[max(0, i - 400):i])


class BothColonsAndOnlyThePrefix(unittest.TestCase):
    def test_both_colons(self):
        for v in ("粗筛：值得投", "粗筛:值得投", "粗筛： 值得投"):
            with self.subTest(v=v):
                self.assertEqual(_cli.strip_triage(v), "值得投")

    def test_only_the_prefix(self):
        """全串替换会把中段的同名子串也抹掉 —— 那是 `.replace` 那一支的毛病。"""
        v = "硬门 FAIL (候选人明确排除（上一轮粗筛：误判）)"
        self.assertEqual(_cli.strip_triage(v), v)

    def test_a_non_triage_verdict_is_untouched(self):
        for v in ("值得投", "硬门 FAIL (学历与院校)", ""):
            with self.subTest(v=v):
                self.assertEqual(_cli.strip_triage(v), v.strip())

    def test_none_is_an_empty_string(self):
        self.assertEqual(_cli.strip_triage(None), "")
        self.assertFalse(_cli.is_triage(None))

    def test_is_triage_agrees_with_strip(self):
        for v in ("粗筛：值得投", "粗筛:可以考虑", "值得投", None, "  粗筛：跳过 "):
            with self.subTest(v=v):
                self.assertEqual(_cli.is_triage(v),
                                 _cli.strip_triage(v) != str(v or "").strip())


if __name__ == "__main__":
    unittest.main()
