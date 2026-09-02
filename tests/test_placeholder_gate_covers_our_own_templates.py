"""落盘前那道占位符闸门，必须认得**本仓库自己模板里的**占位符。

## 这个洞是怎么活下来的

`/job-apply` 第 6 步有一道闸门：材料落盘前扫一遍，发现未填的占位符就拒绝落盘。
它存在的理由只有一个——不让「尊敬的 [目标公司名称]招聘负责人」发到真实雇主手上。

判据原来写的是 **`[A-Z_]+`**（全大写加下划线），照着 `[YOUR_NAME]` 这种英文模板定的。
可**本仓库的模板用的是中文方括号占位符**：

    cover_letter/example.typ:  [姓名] [电话] [城市] [目标公司名称] [具体业务场景]

`[A-Z_]+` 一个都匹配不到。**这道闸门对自家的占位符是瞎的。**

而已有的那条测试（`test_apply_step5_single_source.py`）只检查「闸门别按 typst
扩展名写死」——它管的是**扫哪些文件**，没管**按什么判据扫**。于是文件枚举有人盯，
判据本身没人盯，洞就一直在。

## 判据

从仓库自己的模板/示例里**取真实的占位符**，据此要求闸门的判据不能是纯 ASCII 的。
不猜正则、不钉措辞——占位符样式变了，这条测试跟着变。
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APPLY = ROOT / "workflows" / "job-apply.md"

#: 用户材料的骨架来源。它们带什么样的占位符，闸门就得认得什么样的。
SKELETONS = ("cover_letter/example.typ", "resume/example.typ")

#: 方括号里的内容。Typst 的内容块（`[#姓名]`、`[— 说明]`）以 # 或标点开头，排掉。
BRACKETED = re.compile(r"\[([^\[\]\n]{1,24})\]")


def placeholders_in(rel: str) -> set:
    p = ROOT / rel
    if not p.is_file():
        return set()
    out = set()
    for m in BRACKETED.finditer(p.read_text(encoding="utf-8")):
        s = m.group(1).strip()
        # 排掉标记语法与真实内容：占位符是「一个待填的名词」
        if not s or s[0] in "#—…-*" or "." in s or "/" in s:
            continue
        out.add(s)
    return out


class TheGateKnowsOurOwnPlaceholders(unittest.TestCase):

    def setUp(self):
        text = APPLY.read_text(encoding="utf-8")
        self.gate = text.split("### 落盘前成品扫描")[1].split("### 落盘\n")[0]

    def test_our_skeletons_really_use_non_ascii_placeholders(self):
        """控制用例：仓库里**真有**中文占位符，否则下面那条是空跑。

        哪天骨架全换成 `[YOUR_NAME]` 式的英文占位符，这条会红——那时下面那条
        对 ASCII 判据的限制就该跟着放开，而不是留着一条永远绿的断言。
        """
        found = set()
        for rel in SKELETONS:
            found |= placeholders_in(rel)
        self.assertTrue(found, f"{SKELETONS} 里一个方括号占位符都没抽到——判据多半失效了")
        non_ascii = {s for s in found if any(ord(c) > 127 for c in s)}
        self.assertTrue(
            non_ascii,
            f"骨架里没有非 ASCII 占位符了（抽到：{sorted(found)[:8]}）。"
            "若模板确实全换成英文占位符，请一并放宽下面那条断言。")

    def test_the_gate_names_both_non_regex_criteria(self):
        """必须**同时**给出两条不依赖猜正则的判据，缺一条都不成立。

        ⚠️ 这条断言盯的是**规则本身是什么**，不是「有没有写警告词」。
        第一版盯的是 `不要只扫` / `匹配不到` 这类词——结果变异验证当场打脸：
        把判据改回 `[A-Z_]+` 唯一判据后测试照样绿，因为**解释这个坑的正文里
        本来就有那些词**。断言匹配到自己的说明文字，是这个仓库反复出现的形状。

        为什么必须是两条：
        - 源文件里占位符和标记语法长得一样（`[姓名]` vs `[#姓名]` vs `[— 说明]`），
          单靠正则扫源文件，必然在**漏判**和**误拒**之间二选一；
        - PDF 文本层没有标记语法，判据可以放到最宽 —— 但引擎缺失时没有 PDF；
        - 那种情况只能拿产物与模板骨架差分：**方括号内容两边一模一样 = 没填过**。
        纯正则的写法这两条一条都不会有，所以它是能真正变红的判据。
        """
        has_pdf_layer = any(w in self.gate for w in ("文本层", "PDF 文本"))
        has_diff = any(w in self.gate for w in ("差分", "逐处比对", "与它所依据的模板"))
        self.assertTrue(
            has_pdf_layer and has_diff,
            f"闸门缺少不依赖正则的判据（PDF 文本层={has_pdf_layer}、"
            f"与模板差分={has_diff}）。只靠正则扫源文件，"
            "要么漏掉 [目标公司名称] 这类中文占位符，要么把 Typst 的 [#姓名] 误判成占位符。")

    def test_no_checklist_item_restates_the_pattern(self):
        """同一条规则不许在多处各写一份判据。

        实测：`[A-Z_]+` 这个判据在 `apply.md` 里出现过**三遍**——
        第 6 步「落盘前成品扫描」、5e 的 ATS 校验清单、以及打印给用户的核对清单。
        修的时候一次只发现一处，改完还剩两处；而它们会**各自演化**。
        第三处尤其糟：那是给用户自己核对用的，等于让他按错的判据检查。

        判据落在**结构**上：`- [ ]` 清单项是「要执行的检查」，里面不许出现正则；
        正文里当反例讨论随便写（前几版盯措辞的断言就是被自己的反例干红的）。
        """
        text = APPLY.read_text(encoding="utf-8")
        bad = [f"{i}: {l.strip()[:90]}"
               for i, l in enumerate(text.splitlines(), 1)
               if l.lstrip().startswith("- [ ]") and "[A-Z_]+" in l]
        self.assertEqual(
            bad, [],
            "这些清单项自带了占位符正则：\n  " + "\n  ".join(bad)
            + "\n判据只该有一份（第 6 步「落盘前成品扫描」），别处引用它，不要复述——"
            "复述出来的那几份会各自演化，改一处漏一处。")

    def test_the_gate_acknowledges_non_ascii_placeholders(self):
        """闸门必须点名「本仓库的占位符是中文的」这件事。

        判据取自**真实骨架**：从 example 里抽出的非 ASCII 占位符，至少有一个
        要在闸门说明里被提到。骨架换了样式，这条自然跟着变。
        """
        real = {s for rel in SKELETONS for s in placeholders_in(rel)
                if any(ord(c) > 127 for c in s)}
        self.assertTrue(real, "抽不到非 ASCII 占位符——控制用例应该已经先红了")
        hit = [s for s in real if f"[{s}]" in self.gate]
        self.assertTrue(
            hit,
            f"闸门说明里没有出现任何一个本仓库真实使用的中文占位符"
            f"（骨架里有：{sorted(real)[:6]}）。不点名就没人知道 [A-Z_]+ 漏了什么。")


if __name__ == "__main__":
    unittest.main()
