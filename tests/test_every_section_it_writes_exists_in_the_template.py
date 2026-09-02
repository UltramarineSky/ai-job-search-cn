# -*- coding: utf-8 -*-
"""三条命令写同一份资料，而「小节名以模板为准」这条规则没有任何守卫。

`AGENTS.md`「往 `candidate.md` 里写东西：小节名以模板为准」那一节自己记着代价：

> **这条原来只写在 `/job-expand` 里**，而三条命令都在写。实测代价（2026-08-13）：
> `/job-expand` 曾经照着 `Technical Skills` / `Domain Knowledge` 写，模板里根本
> 没这两节（叫 `## 技能`、`## 执业资格与证照`），资料被切碎；`/job-rank` 则自造了
> 两个「补充确认」小节，而模板里查无此节。
> **一条规则只贴在一个写手身上，另外两个照样会犯。**

规则从那以后搬进了 `AGENTS.md`。而 2026-08-31 扫了一遍：`AGENTS.md` 的 17 个小节
里有 3 个在全仓的测试与工具里**一次都没被引用过**，这一节是其中之一 ——
也就是说，那次事故之后立的规矩，到今天仍然只是散文。

## 判据

写手在正文里点名的每一个 `## 小节`，都要在 `profile.example/` 的某份模板里
真的存在。现算 2026-08-31：三份工作流共点名 25 个小节，25 个都在。

**按「某份模板」判，不按「哪一份」判**：`/job-setup` 一条命令写好几份资料
（`candidate.md` / `behavioral.md` / `interview-star.md` / `search-queries.md` /
`hr-answers.md`），把 `STAR 案例库` 说成「candidate.md 里查无此节」是误报 ——
第一版就是这么写的，当场报了 5 个假的。事故那两个名字（`Technical Skills`、
`Domain Knowledge`）在**任何一份**模板里都不存在，这个粒度已经够抓它。

## 写手名单也要是派生的

规则说「三条命令都会写这一个文件」。真有第四条时，那句话与这份守卫会一起过期，
而没有任何东西会红。所以名单从正文里扫，不认识的要么进名单、要么写明为什么
不算写手。
"""
import pathlib
import re
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
WF = ROOT / "workflows"
TPL = ROOT / "profile.example"

#: 会往 `candidate.md` 的某一节里写东西的命令。正本是 `AGENTS.md` 那一节。
WRITERS = ("job-setup", "job-expand", "job-rank")

#: 正文里出现「写进 candidate.md」、但**不是**写手的：值是理由。
NOT_A_WRITER = {
    "job-outcome.md": "它说的是 /job-setup 路线 A 会来挖归档；正文明写"
                      "「只负责写数据……也不改资料文件」",
    "job-reset.md": "拿模板整份覆盖，不是往某一节里写",
}

_WRITE = re.compile(r"(写[进入回到]|落盘到|追加到|更新)[^。\n]{0,24}candidate\.md")
#: 正文里点名一个小节的两种写法：`` `## X` `` 和 「## X」。
_SECTION = re.compile(r"`#{2,4}\s*([^`]{2,20})`|[「『]#{2,4}\s*([^」』]{2,20})[」』]")


def _template_sections() -> set:
    out = set()
    for f in sorted(TPL.glob("*.md")):
        out |= {h.strip() for h in
                re.findall(r"(?m)^#{2,4}\s*(.+?)\s*$",
                           f.read_text(encoding="utf-8"))}
    return out


def _named_by(stem: str) -> set:
    t = (WF / f"{stem}.md").read_text(encoding="utf-8")
    return {(a or b).strip() for a, b in _SECTION.findall(t)}


class TheRulerWouldLightUp(unittest.TestCase):
    """尺子先证明自己会亮 —— 两边任一为空时，下面那条永远绿。"""

    def test_the_templates_have_sections(self):
        self.assertGreater(len(_template_sections()), 40)

    def test_the_writers_name_sections(self):
        for w in WRITERS:
            with self.subTest(w):
                self.assertGreater(len(_named_by(w)), 0,
                                   f"{w}.md 一个小节都没点名 —— 解析多半失配了")

    def test_the_two_incident_names_would_be_caught(self):
        """事故那两个名字在任何一份模板里都不存在，判据要认得出来。"""
        have = _template_sections()
        for name in ("Technical Skills", "Domain Knowledge"):
            with self.subTest(name):
                self.assertNotIn(name, have)

    def test_both_citation_shapes_are_parsed(self):
        got = {(a or b).strip() for a, b in _SECTION.findall(
            "写进 `## 技能`，再看「## 明确排除」那一节")}
        self.assertEqual(got, {"技能", "明确排除"})


class EverySectionTheyNameExists(unittest.TestCase):

    def test_no_writer_invents_a_section(self):
        have = _template_sections()
        bad = {}
        for w in WRITERS:
            gone = sorted(s for s in _named_by(w) if s not in have)
            if gone:
                bad[w] = gone
        self.assertEqual(
            bad, {},
            "这几条命令让写手往模板里没有的小节写东西 —— 资料会被切碎："
            + repr(bad) + "。规则见 `AGENTS.md`「小节名以模板为准」："
            "模板里没有合适的节就先往模板里加，别在用户的资料里就地发明")


class TheWriterListIsDerived(unittest.TestCase):

    def _mentions(self) -> set:
        return {f.name for f in sorted(WF.glob("*.md"))
                if _WRITE.search(f.read_text(encoding="utf-8"))}

    def test_the_scan_finds_the_writers(self):
        got = self._mentions()
        for w in WRITERS:
            with self.subTest(w):
                self.assertIn(f"{w}.md", got)

    def test_no_unregistered_writer(self):
        extra = sorted(self._mentions() - {f"{w}.md" for w in WRITERS}
                       - set(NOT_A_WRITER))
        self.assertEqual(
            extra, [],
            "这几份也在往 candidate.md 里写，而「小节名以模板为准」那条规则"
            "点名的只有三条：" + repr(extra)
            + "。要么进 WRITERS，要么写明为什么不算写手")

    def test_the_exemptions_are_still_real(self):
        stale = sorted(set(NOT_A_WRITER) - self._mentions())
        self.assertEqual(stale, [], f"这几条豁免已经没有对应的正文了：{stale}")

    def test_the_rule_still_names_three(self):
        """守卫的名单与 `AGENTS.md` 那句枚举必须同时过期，不能只过期一个。

        **只看那句枚举本身**，不看它后面那一整节：`/job-rank` 在下面的实测
        段落里还会再出现一次（「`/job-rank` 则自造了两个「补充确认」小节」），
        按整节找的话，把它从枚举里删掉这条照样绿 —— 变异当场照出来的。
        """
        t = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        i = t.index("**三条命令都会写这一个文件**")
        line = t[t.rindex("\n\n", 0, i):i]      # 枚举那一句，到这半句为止
        for w in WRITERS:
            with self.subTest(w):
                self.assertIn(f"/{w}", line,
                              f"AGENTS.md 那句枚举不再点名 {w}：{line.strip()}")
        self.assertEqual(len(re.findall(r"`/job-[a-z]+`", line)), len(WRITERS),
                         f"枚举里的条数和 WRITERS 对不上：{line.strip()}")


if __name__ == "__main__":
    unittest.main()
