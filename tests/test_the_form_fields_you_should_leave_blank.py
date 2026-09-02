# -*- coding: utf-8 -*-
"""在线简历的核对表逐项走了七条，唯独没提平台**预置**的那几个个人信息格子。

`job-resume.md` 2.6 是「HR 主动搜的是在线简历」那一节，它逐项列了要看什么：
刷新时间、公开范围、求职状态、期望岗位/城市、期望薪资、简历完整度、屏蔽现任
公司、和 PDF 对不对得上。**七条里没有一条说「哪些格子别填」。**

而国内平台的在线简历表单**预置**了身份证号、婚姻/生育状况、民族、籍贯、
政治面貌这些字段 —— 摆在那儿，很多人顺手填满。而在线简历是**付费企业账号
可以批量下载**的。

## 这条不是一刀切，分三档

一刀切会错：体制内、国企、校招的网申表单常把政治面貌列为**必填**，而那一档是
形式审查，缺项直接不过（`job-apply.md` 渠道 3 那节的原话是「看证不看文采」）。
所以判据是**按这次投的是哪一类**：

- **永远别填**：身份证号 —— 录用前没有任何用途（背调、入职才要，且走 HR 正式
  渠道），纯风险，且收不回来。
- **别主动填**：婚姻 / 生育状况 —— 法律上不该拿它筛人，实际会；主动写等于替
  对方省了这一步。
- **看对方要不要**：民族 / 籍贯 / 政治面貌。

## 这是预防，不是修事故

实测活动用户 2026-08-24：他的简历与资料里这五项**一个都没有**。写这条是因为
风险落点很明确 —— 表单预置、逐项引导、下载不可逆，而核对表恰好走到那一屏。
"""
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
DOC = (ROOT / "workflows" / "job-resume.md").read_text(encoding="utf-8")


def flat(s: str) -> str:
    s = " ".join(re.sub(r"^\s*>\s?", "", s, flags=re.M).split())
    return re.sub(r"(?<=[一-鿿，。；：、（）「」])"
                  r" +(?=[一-鿿，。；：、（）「」])", "", s)


def row() -> str:
    i = DOC.index("| **表单里那几个「个人信息」字段** |")
    return flat(DOC[i:DOC.index("\n|", i + 5)])


class TheRowExists(unittest.TestCase):
    def test_it_is_in_the_online_resume_table(self):
        i = DOC.index("### 2.6 在线简历")
        seg = DOC[i:DOC.index("**报告里怎么写**", i)]
        self.assertIn("| **表单里那几个「个人信息」字段** |", seg,
                      "这一行没落在 2.6 那张核对表里")

    def test_it_names_the_fields_the_platform_prefills(self):
        seg = row()
        for f in ("身份证号", "婚姻", "民族", "籍贯", "政治面貌"):
            with self.subTest(f=f):
                self.assertIn(f, seg)

    def test_it_says_why_the_online_one_is_worse(self):
        """在线简历和自己电脑上那份 PDF 的风险不是一回事。"""
        self.assertRegex(row(), r"\*\*付费企业账号可以批量下载\*\*")

    def test_it_covers_the_pdf_too(self):
        self.assertRegex(row(), r"同一条规矩对导出的 PDF 也成立")


class ItIsNotABlanketBan(unittest.TestCase):
    """一刀切会错：体制内网申常把政治面貌列为必填，缺项直接不过。"""

    def test_the_three_tiers_are_spelled_out(self):
        seg = row()
        self.assertIn("**① 永远别填：身份证号。**", seg)
        self.assertIn("**② 别主动填：婚姻 / 生育状况。**", seg)
        self.assertIn("**③ 看对方要不要：民族 / 籍贯 / 政治面貌。**", seg)

    def test_the_third_tier_names_who_requires_it(self):
        seg = row()
        self.assertRegex(seg, r"体制内、国企、校招的网申表单常把政治面貌列为必填")
        self.assertRegex(seg, r"\*\*按这次投的是哪一类决定，别一刀切。\*\*")

    def test_each_tier_gives_the_cost_not_a_lecture(self):
        """说代价，不说教 —— 「保护隐私」这种话对填表的人没有作用。"""
        seg = row()
        self.assertRegex(seg, r"录用之前\*\*没有任何用途\*\*")
        self.assertRegex(seg, r"主动写等于替对方把这一步省了")

    def test_it_does_not_claim_leaving_them_blank_is_illegal(self):
        """留空不违规，但也别把它说成对方违法 —— 那不是这条能断的。"""
        self.assertIn("留空不违规", row())


class TheRestOfTheChecklistSurvives(unittest.TestCase):
    def test_all_seven_original_rows_are_still_there(self):
        i = DOC.index("| 要看什么 | 为什么它决定你会不会被搜到 |")
        seg = DOC[i:DOC.index("**报告里怎么写**", i)]
        for r in ("最近刷新/活跃时间", "简历公开范围", "求职状态",
                  "期望岗位 / 期望城市", "期望薪资", "简历完整度",
                  "屏蔽现任公司", "在线简历和 PDF 说的是不是一回事"):
            with self.subTest(r=r):
                self.assertIn(r, seg)

    def test_the_read_only_rule_still_stands(self):
        """这一节全部在平台上、在登录态后面 —— 工具只读不改。"""
        self.assertIn("**不要动任何设置**", DOC)
        self.assertIn("这一节里没有一项是这个工具能替你改的", DOC)

    def test_the_not_checked_rule_still_stands(self):
        """「没查」和「查过没有」是两件事。"""
        self.assertIn("如实说明你没查", DOC)


class TheSignalItLeansOnIsReal(unittest.TestCase):
    """有语料时验一次：这条是预防 —— 真出现了就不该再叫预防。"""

    FIELDS = ("身份证", "婚姻", "民族", "籍贯", "政治面貌")

    def _files(self):
        p = ROOT / ".active_user"
        if not p.is_file():
            self.skipTest("没有活动用户")
        u = p.read_text(encoding="utf-8").strip()
        d = ROOT / "users" / u
        out = list((d / "resume").glob("*.typ")) if (d / "resume").is_dir() else []
        if not out:
            self.skipTest("没有简历源文件")
        return out

    def test_the_resume_source_carries_none_of_them(self):
        hit = []
        for f in self._files():
            txt = f.read_text(encoding="utf-8", errors="replace")
            hit += [(f.name, w) for w in self.FIELDS if w in txt]
        self.assertEqual(hit, [],
                         f"简历源文件里出现了这些字段：{hit} —— "
                         f"那这条就不是预防了，去 2.6 那一行按分档处理")


if __name__ == "__main__":
    unittest.main()
