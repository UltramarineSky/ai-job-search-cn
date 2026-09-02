# -*- coding: utf-8 -*-
"""四段对外文案是**要发出去的字**，不只是屏幕上的字。

`AGENTS.md`「给用户看的措辞」那条写着：凡是从文件正文流向界面的字段，显示层
都要先剥掉 `**` 和反引号（`export_web_data.plain()`）。而开场白 / 邮件主题 /
邮件正文 / 网申自评这四段比面板上别处更要紧 —— **它们不只是显示**：

- 复制按钮 `CopyIcon text={m.emailBody}` 原样复制
- `mailto:` 链接 `encodeURIComponent(m.emailBody)` 把正文原样塞进去

也就是说 `**` 会跟着邮件发到用人方那里。

## 实测（2026-08-27）

导出的 `data.json` 里带 markdown 标记的字符串**只剩 1 条**，而它正是一段
`emailBody`（正文里编了号的三条加粗小标题）。别处早就剥干净了，只有这条路
没接上 —— 接上之后是 0 条。

`06-outreach-templates.md` 渠道 2 自己写着那一节的用途是「整段选中、粘进邮件
发给用人方」，同一段还留着一句「**比多几个星号糟得多**」：星号是那次已经看见、
却一直没处理的那一半。

## 为什么剥在导出侧，不是只改那一份文件

改文件只修这一份。**下一份还会这么写** —— 而 `03`/`06` 都没有一条「不许用
markdown」的铁律（它们管的是措辞，不是标记）。剥在导出侧，这条路就永远干净。
"""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import export_web_data as ex  # noqa: E402

SRC = (ROOT / "tools" / "export_web_data.py").read_text(encoding="utf-8")
READOUT = (ROOT / "web" / "src" / "components"
           / "JobReadout.tsx").read_text(encoding="utf-8")
BT = chr(96)


class TheFourFieldsGoThroughPlain(unittest.TestCase):
    FIELDS = ("greeting", "emailSubject", "emailBody", "wangshen")

    def _seg(self):
        i = SRC.index('for key, src in (("greeting"')
        return SRC[i:i + 400]

    def test_all_four_are_listed(self):
        seg = self._seg()
        for f in self.FIELDS:
            with self.subTest(field=f):
                self.assertIn(f'"{f}"', seg)

    def test_they_are_not_stored_raw(self):
        seg = self._seg()
        self.assertIn("plain(src.strip())", seg)
        self.assertNotIn("mats[key] = src.strip()", seg,
                         "又原样存了 —— 星号会跟着邮件发出去")

    def test_plain_actually_strips_the_markers(self):
        # 样例里的作品名与数字都是编的 —— `test_no_maintainer_data_in_repo`
        # 盯着：真实作品名进了版本库就是把维护者的个人数据发出去了。
        body = "您好，\n\n1. **面向开发者的产品**——`某某工具` 3 万+ 用户\n\n谢谢。"
        got = ex.plain(body)
        self.assertNotIn("**", got)
        self.assertNotIn(BT, got)
        self.assertIn("面向开发者的产品", got, "把字本身也剥掉了")

    def test_it_keeps_the_paragraphs(self):
        """邮件是分段的。剥标记不能把换行一起吃掉。"""
        body = "您好，\n\n第一段。\n\n1. **一条**\n2. **两条**\n\n谢谢。"
        self.assertEqual(ex.plain(body).count("\n"), body.count("\n"))


class ThisTextReallyLeavesTheScreen(unittest.TestCase):
    """如果它只是显示，剥不剥是观感问题；它会被发出去，所以是内容问题。"""

    def test_the_copy_button_takes_it_verbatim(self):
        self.assertIn("CopyIcon text={m.emailBody}", READOUT)

    def test_the_mailto_link_takes_it_verbatim(self):
        self.assertIn("encodeURIComponent(m.emailBody)", READOUT)

    def test_the_panel_renders_it_as_plain_text(self):
        """纯文本节点 —— JSX 不渲染 markdown，星号会原样显示。"""
        self.assertIn('<p className="greeting">{m.emailBody}</p>', READOUT)


class TheSnapshotIsClean(unittest.TestCase):
    def test_no_markdown_marker_survives_into_the_snapshot(self):
        snap = ROOT / "web" / "public" / "data.json"
        if not snap.is_file():
            self.skipTest("还没导出过面板数据")
        d = json.loads(snap.read_text(encoding="utf-8"))

        def walk(o):
            if isinstance(o, dict):
                for v in o.values():
                    yield from walk(v)
            elif isinstance(o, list):
                for v in o:
                    yield from walk(v)
            elif isinstance(o, str):
                yield o

        bad = [s[:60] for s in walk(d) if "**" in s or BT in s]
        self.assertEqual(bad, [],
                         "导出的快照里还有 markdown 标记：\n  " + "\n  ".join(bad))


class TheRuleItEnforcesIsStillWritten(unittest.TestCase):
    def test_agents_still_names_plain(self):
        text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("export_web_data.plain()", text)

    def test_the_measurement_moved_with_the_fix(self):
        """1035 是修之前的观测。句子原来是现在时 —— 那在修完之后就成了假话。

        **判据要贴到那句话上。** 第一版在整份 AGENTS.md 里找日期，
        而这份文档里日期到处都是 —— 把 1035 旁边那个删掉，测试照样绿。
        """
        text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        i = text.index("1035")
        # **只看它前面。** 后面 25 字处就有另一个日期（2026-08-27，
        # 属于「只剩 1 条」那一句）—— 取双侧窗口时，把 1035 自己的日期
        # 整个删掉测试照样绿。变异当场露馅。
        before = text[max(0, i - 40):i]
        self.assertRegex(before, r"20\d\d-\d\d-\d\d",
                         f"1035 前面没有日期，读起来像在说「现在」：{before}")
        self.assertIn("只剩 1 条", text, "没记下修之前最后剩的那一条是什么")

    def test_the_channel_two_note_is_still_there(self):
        """这条改动的由头就是 06 那句「比多几个星号糟得多」。"""
        ref = (ROOT / "workflows" / "reference"
               / "06-outreach-templates.md").read_text(encoding="utf-8")
        self.assertIn("比多几个星号糟得多", ref)
        self.assertIn("整段选中、粘进邮件发给用人方", ref)


if __name__ == "__main__":
    unittest.main()
