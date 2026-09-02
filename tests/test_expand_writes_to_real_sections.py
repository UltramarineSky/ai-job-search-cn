"""`/job-expand` 往资料里写东西时，点名的小节必须真的存在。

## 它原来指向四个不存在的小节

`expand.md` 的 Step 5 是**唯一**会往 `profile/candidate.md` 与 `profile/behavioral.md`
追加内容的地方。它原来这么写：

    - Technical skills (primary and secondary) → append to the Technical Skills section
    - Domain knowledge → append to the Domain Knowledge or Technical Skills section
    - Soft/behavioral signals → append to the "Strongest Behavioral Traits"
      or "How I Work Best" section

而 `profile.example/` 里这两个文件的小节名**全是中文**：`## 技能`、`## 执业资格与证照`、
`## 核心特质`、`## 最突出的行为`。四个英文名一个都对不上。执行者只能新建几个英文
小节，把用户的资料切成中英两套结构——而下游按中文名解析（`export_web_data`
找的是 `^#{1,6}\\s*技能\\s*$`），新建的那半永远读不到。

同一个形状这个文件里已经出现两次并被记下来：

- Step 1e：发现层写死成「GitHub Profile」→ 改成「资料里列的那个平台」
- Step 3：产出层的组名写死成 `Technical Skills / Domain Knowledge` → 改成中文组名，
  复盘写着「Step 1e 已经中性化了发现层，这里是产出层没跟上」

Step 5 是第三层——**写入层**。前两层都改了，它没改。

## 判据

Step 5 里点名的每一个 `## 小节`，都要在对应模板文件里存在。
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXPAND = ROOT / "workflows" / "job-expand.md"


def template_sections(name: str) -> set:
    """`profile.example/<name>` 里的所有标题名（层级不限）。"""
    p = ROOT / "profile.example" / name
    if not p.is_file():
        return set()
    return {re.sub(r"^#{1,6}\s+", "", l).strip()
            for l in p.read_text(encoding="utf-8").splitlines() if l.startswith("#")}


def step5_blocks() -> dict:
    """Step 5 里两个写入子节 → 它们各自点名的小节。

    子节标题里带着目标文件名（「写进 `profile/candidate.md`」），所以归属是显式的，
    不靠猜。
    """
    text = EXPAND.read_text(encoding="utf-8")
    out = {}
    for m in re.finditer(r"^#{3}\s+.*?`profile/([a-z-]+\.md)`.*$", text, re.M):
        start = m.end()
        nxt = re.search(r"^#{2,3}\s+", text[start:], re.M)
        body = text[start:start + nxt.start()] if nxt else text[start:]
        names = {re.sub(r"^#{1,6}\s*", "", x).strip()
                 for x in re.findall(r"`(#{2,6}\s*[^`]{2,24})`", body)}
        out.setdefault(m.group(1), set()).update(names)
    return out


class Step5PointsAtSectionsThatExist(unittest.TestCase):

    def test_the_scan_finds_the_write_steps(self):
        """控制用例：真抽到了写入子节和它点名的小节，否则下面那条永远绿。"""
        blocks = step5_blocks()
        self.assertTrue(blocks, "expand.md 里找不到「写进 `profile/xxx.md`」的子节了")
        self.assertTrue(
            any(v for v in blocks.values()),
            f"抽到了子节但一个 `## 小节` 都没点名：{blocks}——"
            "判据可能失效了，而不是它真的不点名小节了")

    def test_the_template_has_sections_to_compare_against(self):
        """控制用例：模板读得到，否则比对的是空集。"""
        for f in ("candidate.md", "behavioral.md"):
            with self.subTest(f=f):
                self.assertTrue(template_sections(f),
                                f"profile.example/{f} 里抽不到小节名")

    def test_every_named_section_exists_in_the_template(self):
        bad = []
        for fname, names in step5_blocks().items():
            have = template_sections(fname)
            if not have:                      # 模板不在，这一份无从判断
                continue
            for n in sorted(names):
                if n not in have:
                    bad.append(f"{fname}: 点名了 `## {n}`，模板里没有")
        self.assertEqual(
            bad, [],
            "/job-expand 的写入步骤指向了不存在的小节：\n  " + "\n  ".join(bad)
            + "\n执行者只能新建小节，把资料切成两套结构——"
            "\n而下游按模板里的名字解析，新建的那半永远读不到。"
            "\n模板现有小节："
            + "".join(f"\n  {f}: {sorted(template_sections(f))}"
                     for f in ("candidate.md", "behavioral.md")))

    def test_it_does_not_name_the_old_english_sections(self):
        """那四个英文名是这条规则的原始反例，别再写回去。"""
        t = EXPAND.read_text(encoding="utf-8")
        for name in ("Strongest Behavioral Traits", "How I Work Best"):
            with self.subTest(name=name):
                self.assertNotIn(
                    name, t,
                    f"又点名了 `{name}` —— profile.example/behavioral.md 里没有这一节")
        # `Technical Skills` / `Domain Knowledge` 允许出现在**讲这条规则**的复盘文字里，
        # 但不能出现在写入指令里。判据：不许出现在「→ append」「→ 落到」这类指派句里。
        for i, line in enumerate(t.splitlines(), 1):
            if "→" not in line:
                continue
            for name in ("Technical Skills", "Domain Knowledge"):
                with self.subTest(line=i, name=name):
                    self.assertNotIn(
                        name, line,
                        f"expand.md:{i} 把内容指派给了 `{name}`，模板里没有这一节")


class SetupStep3PointsAtSectionsThatExist(unittest.TestCase):
    """`/job-setup` 的 Step 3 §1 也一样——它是**新用户资料的生成步骤**，错在这里最贵。

    原来它写着：

        structured sections: Identity, Education, Professional Experience,
        Independent Projects, Technical Skills, Publications, Awards, References, Salary

    九个里有四个模板里不存在（`Independent Projects` / `Publications` / `Awards` /
    `References`）。而 **Section 5 问了发表与获奖、Section 8 问了推荐人**——
    问卷认真问完，模板却没有位置放，执行者只能新建英文小节或者把答案丢掉。

    修法是两头都补：模板加了 `## 发表与获奖` 与 `## 推荐人`（没有就写「无」），
    Step 3 §1 换成一张「哪一节的答案写进哪一节」的对应表。

    与 `/job-expand` Step 5 是同一个错、同一个判据。
    """

    SETUP = ROOT / "workflows" / "job-setup.md"

    def _named_sections(self):
        """Step 3 里那张对应表点名的 `## 小节`。"""
        t = self.SETUP.read_text(encoding="utf-8")
        i = t.index("## Step 3：")
        j = t.index(chr(10) + "## Step 4：", i)
        return {re.sub(r"^#{1,6}\s*", "", x).strip()
                for x in re.findall(r"`(#{2,6}\s*[^`]{2,20})`", t[i:j])}

    def test_the_mapping_table_is_there(self):
        """控制用例：真抽到了对应表，否则下面那条永远绿。"""
        got = self._named_sections()
        self.assertGreaterEqual(
            len(got), 8,
            f"Step 3 里只抽到 {len(got)} 个小节名：{sorted(got)}——"
            "对应表可能被删了，或者又改回了英文散文")

    def test_every_named_section_exists(self):
        have = template_sections("candidate.md")
        self.assertTrue(have, "profile.example/candidate.md 抽不到小节名")
        bad = sorted(n for n in self._named_sections() if n not in have)
        self.assertEqual(
            bad, [],
            f"/job-setup Step 3 点名了模板里没有的小节：{bad}"
            + chr(10) + "问卷认真问了，却没有位置放——执行者只能新建小节或把答案丢掉。"
            + chr(10) + f"模板现有：{sorted(have)}")

    def test_the_questionnaire_targets_have_a_home(self):
        """Section 5 与 Section 8 问的东西，模板里必须有地方放。

        这两节问的是发表·获奖与推荐人。模板原来一节都没有，于是
        「认真问完再丢掉」——比不问更糟，用户还以为记下了。
        """
        have = template_sections("candidate.md")
        for name in ("发表与获奖", "推荐人"):
            with self.subTest(section=name):
                self.assertIn(
                    name, have,
                    f"模板里没有 `## {name}`，而 /job-setup 正在问这件事")


class ApplyWritesIntoSectionsTheFrameworkDeclares(unittest.TestCase):
    """`/job-apply` 说要写进 `evaluation.md` 的小节，框架输出模板里必须有。

    实测：`apply.md` 第 1.7 步写着「逐条写进 `evaluation.md` 的「信息质量提示」一节」，
    而 `04-job-evaluation.md` 的输出格式里**根本没有这一节**——照模板产出的评估，
    那些提示无处可去。

    它和模板里的「待核实清单」也不是一回事：

    | 小节 | 装的是什么 |
    |---|---|
    | 有哪些信息没核实上 | **查不到 / 对不上的**：雇主匿名、平台字段自相矛盾、核实结果与字段不符 |
    | 待核实清单 | **要去查什么**：公司官网、脉脉、工商信息、是否长期重复挂 |

    这是「规则声明了、另一头没落点」的第五次——前四次是执业资格与明确排除没有行、
    可披露口径没有列、简历章节顺序三处全无、发表获奖与推荐人没有小节。
    """

    APPLY = ROOT / "workflows" / "job-apply.md"
    FRAMEWORK = ROOT / "workflows" / "reference" / "04-job-evaluation.md"

    def _template_sections(self):
        t = self.FRAMEWORK.read_text(encoding="utf-8")
        i = t.index("## 输出格式")
        j = t.index(chr(10) + "## 权重", i)
        return {re.sub(r"^#+\s*", "", l).split("（")[0].split("：")[0].strip()
                for l in t[i:j].splitlines() if l.startswith("###")}

    def _referenced(self):
        ap = self.APPLY.read_text(encoding="utf-8")
        return [(ap[:m.start()].count(chr(10)) + 1, m.group(1))
                for m in re.finditer(r"`evaluation\.md` 的「([^」]{2,16})」", ap)]

    def test_the_scan_finds_references(self):
        """控制用例：真抽到了「写进 evaluation.md 的「X」一节」这类引用。"""
        self.assertTrue(
            self._referenced(),
            "apply.md 里找不到任何「写进 `evaluation.md` 的「X」一节」——"
            "措辞可能变了，抽取器要跟着改，否则这条永远绿")

    def test_the_template_has_sections(self):
        """控制用例：模板抽得到小节，否则比对的是空集。"""
        self.assertGreaterEqual(
            len(self._template_sections()), 6,
            f"输出格式里只抽到 {sorted(self._template_sections())}")

    def test_every_referenced_section_exists(self):
        have = self._template_sections()
        bad = [f"apply.md:{ln} 「{name}」" for ln, name in self._referenced()
               if name not in have]
        self.assertEqual(
            bad, [],
            "/job-apply 要写进这些小节，而 04-job-evaluation.md 的输出格式里没有：" + chr(10)
            + "  " + (chr(10) + "  ").join(bad)
            + chr(10) + f"模板现有：{sorted(have)}"
            + chr(10) + "照模板产出的评估没有那一节，写进去的内容无处可去。")


if __name__ == "__main__":
    unittest.main()


class RankWritesToTheNamedSection(unittest.TestCase):
    """`/job-rank` 是往 `candidate.md` 写的**第三个**写手，同样要点名小节。

    `AGENTS.md`：「`/job-setup`、`/job-expand`、`/job-rank` **三条命令都会写这一个
    文件**……小节名一律以 `profile.example/candidate.md` 为准……每条写入都标
    **日期与来源**」。

    本文件原来只盯前两条。而 `AGENTS.md` 记着的那次实测代价恰恰是第三条的：
    **`/job-rank` 自造了两个「补充确认」小节，而模板里当时查无此节。**
    模板后来补上了这一节，`/job-rank` 的正文却始终没指过去 ——
    执行者照它做，只能再猜一次（2026-08-21 通读时发现）。
    """

    RANK = ROOT / "workflows" / "job-rank.md"

    def test_the_template_has_the_section(self):
        """控制用例：模板里确实有这一节，否则下面那条指的是空气。"""
        t = (ROOT / "profile.example" / "candidate.md").read_text(encoding="utf-8")
        self.assertIn("## 补充确认", t,
                      "模板里没有「补充确认」了？那 /job-rank 该指向别处")

    def test_rank_names_the_section(self):
        t = self.RANK.read_text(encoding="utf-8")
        i = t.index("待问清单")
        seg = t[i:i + 900]
        self.assertIn(
            "补充确认", seg,
            "/job-rank 的待问清单没说答案写进哪一节 —— "
            "它自造小节的历史就是这么来的（见 AGENTS.md）")

    def test_rank_requires_date_and_provenance(self):
        """`AGENTS.md` 要求「日期**与来源**」，而这里原来只写了日期。"""
        t = self.RANK.read_text(encoding="utf-8")
        i = t.index("待问清单")
        seg = t[i:i + 900]
        self.assertIn(
            "来源", seg,
            "/job-rank 只要求标日期，没要求标来源 —— "
            "AGENTS.md 要的是「日期与来源（哪条命令、因为什么问的）」")

