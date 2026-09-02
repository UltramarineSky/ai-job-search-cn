"""规则声明要收集的字段，模板里要有位置、问卷里要真的问。

本文件钉两处实例，形状完全一样：**可披露口径** 与 **简历章节顺序**。

## 「可披露口径」被声明了三年，从来没被收集过

`03-writing-style.md` 的铁律 6（「别人的秘密不是你的证据」）是三个职业的独立审阅
同时指出来的：律师的《律师法》保密义务、会计师的《注册会计师法》第十九条、
大客户销售的客户名单——**他们最有说服力的证据，恰恰是有法定义务不能点名的那些**。

那条铁律给了明确的判据来源：

> 怎么知道哪些不能写：`profile/candidate.md` 的「作品与项目的分层」里每条都带
> **可披露口径**（能点名 / 只能脱敏 / 完全不能提），`/job-setup` 会问。

可实测：

- `profile.example/candidate.md` 的分层表只有 `线 | 起始 | 项目 | 只能主张` **四列**
- `/job-setup` Section 9 §2 只问了分层与时间线，**一句没问过可披露口径**
- 「可披露口径」这五个字，全仓库只出现在**提出它的那个文件里**

规则写得很硬，数据一条都没有。执行时只能走它的兜底（「资料里没标 → 起草前问用户
一句」）——那条兜底于是 **100% 触发**，而用户以为 `/job-setup` 已经问过了。

这与「明确排除」那一节曾经**没有任何消费者**、执业资格门**没有落点**是同一个形状：
**规则层与数据层各改各的。**

## 判据

分层表的每一个列名，都要能在 `setup.md` 的 Section 9 里找到对应的问法。
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCAFFOLD = ROOT / "profile.example" / "candidate.md"
SETUP = ROOT / "workflows" / "job-setup.md"
STYLE = ROOT / "workflows" / "reference" / "03-writing-style.md"

#: 列名与它在问卷里可能的说法。判据认的是「问没问到这件事」，不是用词一致。
COLUMN_ASKS = {
    "线": ("分个层", "分层"),
    "起始": ("时间线", "从什么时候"),
    "项目": ("作品或项目", "作品"),
    "只能主张": ("只能主张", "绝不可写"),
    "可披露口径": ("可披露口径", "对外能说到什么程度"),
}


def tier_table_columns() -> list:
    """分层表的表头列名。"""
    t = SCAFFOLD.read_text(encoding="utf-8")
    i = t.find("## 作品与项目的分层")
    if i < 0:
        return []
    m = re.search(r"^\|(.+?)\|\s*$", t[i:], re.M)
    return [c.strip() for c in m.group(1).split("|") if c.strip()] if m else []


def section9() -> str:
    t = SETUP.read_text(encoding="utf-8")
    i = t.find("### Section 9：")
    return t[i:t.index("### Section 10：", i)] if i >= 0 else ""


class EveryColumnIsActuallyAsked(unittest.TestCase):

    def test_the_table_is_found(self):
        """控制用例：真抽到了表头。"""
        cols = tier_table_columns()
        self.assertGreaterEqual(
            len(cols), 4, f"分层表的表头只抽到 {cols}——模板结构可能改了")

    def test_section_9_is_found(self):
        """控制用例：真抽到了那一节。"""
        self.assertGreater(len(section9()), 200,
                           "setup.md 里抽不到 Section 9 的正文")

    def test_the_rule_still_depends_on_this_column(self):
        """控制用例：铁律 6 还在按这一列判断，否则本测试失去依据。"""
        self.assertIn(
            "可披露口径", STYLE.read_text(encoding="utf-8"),
            "03-writing-style.md 不再提「可披露口径」了——本测试的依据没了")

    def test_the_disclosure_column_exists(self):
        self.assertIn(
            "可披露口径", tier_table_columns(),
            "模板的分层表里没有「可披露口径」这一列，"
            "而 03-writing-style.md 的铁律 6 正是按它判断哪些内容不能写。"
            f"\n现有列：{tier_table_columns()}")

    def test_every_column_is_asked_in_section_9(self):
        sec = section9()
        bad = []
        for col in tier_table_columns():
            keys = COLUMN_ASKS.get(col, (col,))
            if not any(k in sec for k in keys):
                bad.append(f"「{col}」（也找过：{keys}）")
        self.assertEqual(
            bad, [],
            "分层表有这些列，Section 9 却没问：\n  " + "\n  ".join(bad)
            + "\n列在表里、问卷不问 = 规则声明了、数据从来没被收集，"
            "\n而执行时只会静默走兜底，用户以为已经问过了。"
            "\n换了说法而不是真漏，就往 COLUMN_ASKS 里加一行。")


class CvSectionOrderIsActuallyCollected(unittest.TestCase):
    """`05-cv-templates.md` 的「章节顺序按行业定一次」，三处一处都没有。

    那一节论证得很具体：

    - **「项目经历」不是每个行业都有** —— 有的行业这一节实际是教学成果、科室轮转、
      参与工程、办案记录、客户业绩、作品集
    - **执业资格是准入门槛的行业，「技能与证书」要提到前面** —— 压在最后一行
      等于把 HR 第一眼要确认的东西藏起来

    然后写着「顺序在 `/job-setup` 时定下来、写进 `profile/candidate.md`，
    此后所有 `/job-apply` 一律照用」。实测：

    - 模板里**没有这个字段**
    - `/job-setup` **一句没问过**
    - `/job-apply` **从不读它**

    三处都没有，于是每个人的简历都按那份互联网/泛商务的基线顺序排——
    而那正是这一节开头就说「本身不是普适的」的东西。
    """

    CV = ROOT / "workflows" / "reference" / "05-cv-templates.md"
    APPLY = ROOT / "workflows" / "job-apply.md"
    FIELD = "简历章节顺序"

    def test_the_rule_is_still_stated(self):
        """控制用例：规则还在，否则本测试拦的是不存在的东西。"""
        self.assertIn("章节顺序按行业定", self.CV.read_text(encoding="utf-8"),
                      "05-cv-templates.md 里那条规则不见了——本测试失去依据")

    def test_the_template_has_a_slot(self):
        self.assertIn(
            self.FIELD, SCAFFOLD.read_text(encoding="utf-8"),
            f"模板里没有「{self.FIELD}」字段，而规则说它要写进 candidate.md")

    def test_setup_asks_for_it(self):
        self.assertIn(
            self.FIELD, SETUP.read_text(encoding="utf-8"),
            f"`/job-setup` 从没问过「{self.FIELD}」——"
            "规则说它在 /job-setup 时定下来，那就得真的问")

    def test_apply_reads_it(self):
        self.assertIn(
            self.FIELD, self.APPLY.read_text(encoding="utf-8"),
            f"`/job-apply` 不读「{self.FIELD}」——"
            "收集了没人用，等于没收集；每份简历还是那份基线顺序")


if __name__ == "__main__":
    unittest.main()
