"""`/job-html-report` 的中文词表必须和真正在用的那两套对齐。

## 它自己造了第三套说法，而它自己禁止这么做

`html-report.md` 的状态桶表原来把 `applied` 显示成「**等回音**」——
这个词在 `web/src/` 和 `tools/` 里**一次都没出现过**。而同一段下面十行就写着：

> 同一个状态在总览页和这份报表里必须是同一个词。

仓库里实际有两套合法词汇，各有各的场合：

| 场合 | 用哪套 | 例 |
|---|---|---|
| **数状态**（漏斗计数、报表的桶） | 总览页漏斗 | 材料就绪 / 已投递 / 面试中 |
| **记动作**（按钮上的字） | `tracker.LABEL` | 我投了 / 约面了 / 挂了 …… |

「等回音」两套里都没有。用户在总览页看到「已投递 12」，在报表里看到「等回音 12」，
要自己把两个词对上号——而它们是同一个数。

## 顺带钉住按钮词表

修这处时我做了一次全文替换「约面了→面试中」，把**按钮词表那一行**也改错了
（那一行是抄 `tracker.LABEL` 的，不该跟着桶名走）。批量替换扫过自己写的说明，
是这轮反复出现的形状——所以这里直接和 `tracker.LABEL` 对一遍，不靠人眼。
"""

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import tracker as tk  # noqa: E402

DOC = ROOT / "workflows" / "job-html-report.md"

#: 漏斗那套的词，取自总览页实际渲染的字。
FUNNEL_WORDS = ("材料就绪", "已投递", "面试中")


class ReportWordingMatchesWhatIsActuallyUsed(unittest.TestCase):

    def test_the_scan_reaches_the_frontend(self):
        """对照用例：扫描真的够到了文件 —— 否则同文件里那些「没问题」是恒绿的。

        2026-08-20 实测：把 `Path.glob`/`rglob` 打成空之后本文件全绿。
        **扫不到文件时，「没有问题」和「没有检查」长得一模一样。**

        这不是假想——这个仓库真搬过目录（工作流正文从 `.claude/skills/` 搬到
        `workflows/`，`AGENTS.md` 里记着）。glob 还指着旧路径时，守卫会安静地失效。
        """
        found = list((ROOT / "web" / "src").rglob("*.ts*"))
        self.assertGreaterEqual(
            len(found), 12,
            f"只扫到 {len(found)} 个前端源文件 —— 判据大概是够不到文件了，"
            "而不是仓库真的只剩这么几个")

    def test_the_button_label_list_matches_tracker(self):
        m = re.search(r"记动作（按钮上的字）\*\* → 用 `tools/tracker\.py` 的 `LABEL`：(.+?)。",
                      DOC.read_text(encoding="utf-8"), re.S)
        self.assertIsNotNone(m, "html-report.md 里找不到按钮词表那一行了")
        listed = {x.strip() for x in re.findall(r"`([^`]+)`", m.group(1))}
        canon = set(tk.LABEL.values())
        self.assertEqual(
            listed, canon,
            "按钮词表和 tracker.LABEL 对不上。"
            + chr(10) + f"  文档：{sorted(listed)}"
            + chr(10) + f"  代码：{sorted(canon)}"
            + chr(10) + "这一行是抄 LABEL 的，别跟着桶名改。")

    def test_no_invented_third_wording(self):
        """「等回音」这类自造词不许出现在指令里（解释这条规则的段落除外）。"""
        bad = []
        for i, line in enumerate(DOC.read_text(encoding="utf-8").splitlines(), 1):
            if "原来把" in line or "自己造的第三套" in line:
                continue
            if "等回音" in line:
                bad.append(f"html-report.md:{i}  {line.strip()[:56]}")
        self.assertEqual(
            bad, [],
            "报表里又出现了自造的状态词：" + chr(10) + "  " + (chr(10) + "  ").join(bad)
            + chr(10) + "总览页和 tools/ 里都没有这个词——同一个数两个名字，用户要自己对号。")

    def test_the_funnel_words_are_the_ones_the_panel_uses(self):
        """控制用例：漏斗那套词确实是页面在用的，否则本测试拦的是我编的规则。"""
        blob = ""
        for p in list((ROOT / "web" / "src").rglob("*.ts*")) + [ROOT / "tools" / "export_web_data.py"]:
            if p.is_file():
                blob += p.read_text(encoding="utf-8", errors="replace")
        for w in FUNNEL_WORDS:
            with self.subTest(word=w):
                self.assertIn(w, blob, f"「{w}」在页面代码里找不到了——漏斗词表要重新确认")


if __name__ == "__main__":
    unittest.main()
