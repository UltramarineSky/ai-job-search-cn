# -*- coding: utf-8 -*-
"""额度报告说「猎聘 可以抓」，面板同时说「猎聘 你关着」——两句都对，两句都不提对方。

抓不抓这家由**两道闸门**决定，`job-scrape.md` 明写着它们的主人不同：

    portals.json   用户说这一轮想不想抓这家
    额度            平台说现在还让不让抓

而那段话紧接着警告：**合并之后「用户明明开着、工具却不抓」就没人解释得清
是哪一层挡的。** 所以这两道门必须分开判 —— 这一条没有争议。

**但互不提及是那句警告的反面。** 实测活动用户 2026-08-23：

    python tools/portal_budget.py   猎聘  可以抓  今天 0/2 轮 · 猎聘 可以动
    面板                            猎聘 你关着（占库里 85%）

读的人一样不知道到底能不能抓。所以「可以抓 / 停」那个**判词不动**（它仍然只答
平台那一问），只在行尾补一句注脚。

判据 `switched_off` 与 `export_web_data.portals_enabled` 同源，内联一份 ——
那边 `import portal_budget as pb`，反向 import 就成环。
「缺文件 = 全开」是要紧的默认：抄漏它，第一次跑就会说四家全关。
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tests"))
import export_web_data as X  # noqa: E402
import portal_budget as pb  # noqa: E402
from _srcscan import code_of  # noqa: E402


class TheSwitchIsReadTheSameWay(unittest.TestCase):
    def _write(self, root, obj):
        d = root / "users" / "u" / "job_scraper"
        d.mkdir(parents=True)
        if obj is not None:
            (d / "portals.json").write_text(json.dumps(obj, ensure_ascii=False),
                                            encoding="utf-8")

    def test_missing_file_means_all_on(self):
        """**缺文件 ≠ 全关。** 抄漏这条，第一次跑就说四家全关。"""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write(root, None)
            import unittest.mock as mock
            with mock.patch.object(pb, "ROOT", root):
                self.assertEqual(pb.switched_off("u"), set())

    def test_a_broken_file_means_all_on_too(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "users" / "u" / "job_scraper").mkdir(parents=True)
            (root / "users" / "u" / "job_scraper" / "portals.json").write_text(
                "{ 坏了", encoding="utf-8")
            import unittest.mock as mock
            with mock.patch.object(pb, "ROOT", root):
                self.assertEqual(pb.switched_off("u"), set())

    def test_a_false_value_counts_as_off(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write(root, {"猎聘": False, "BOSS": True, "智联": True})
            import unittest.mock as mock
            with mock.patch.object(pb, "ROOT", root):
                self.assertEqual(pb.switched_off("u"), {"猎聘"})

    def test_a_null_value_counts_as_off(self):
        """正本是 `bool(d.get(k, True))` —— 手改过的文件里 `null` 算关。
        写成 `v is False` 的话两处当场说反。"""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write(root, {"猎聘": None, "BOSS": True})
            import unittest.mock as mock
            with mock.patch.object(pb, "ROOT", root):
                self.assertEqual(pb.switched_off("u"), {"猎聘"})

    def test_it_agrees_with_the_exporter(self):
        """两份判据同源。分叉了，面板和这份报告就会说反。
        **值域要扫全**：只拿 True/False 比，`null` 那一格的分叉照样漏。"""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write(root, {"猎聘": False, "BOSS": True,
                               "智联": None, "前程无忧": 0})
            import unittest.mock as mock
            with mock.patch.object(pb, "ROOT", root), \
                 mock.patch.object(X, "ROOT", root):
                mine = pb.switched_off("u")
                theirs = {k for k, v in X.portals_enabled("u").items() if not v}
            self.assertEqual(mine, theirs)


class TheVerdictStaysAboutThePlatform(unittest.TestCase):
    """**不许把两道门合并。** 合并之后没人解释得清是哪一层挡的。"""

    def _rows(self, off):
        import datetime as dt
        return pb.status_lines({}, dt.datetime(2026, 8, 23, 10, 0), off)

    def test_a_switched_off_portal_still_reads_as_scrapable(self):
        row = next(r for r in self._rows({"猎聘"}) if "猎聘" in r)
        self.assertIn("可以抓", row, "判词被开关改掉了 —— 那就是合并了两道门")

    def test_but_it_carries_the_footnote(self):
        row = next(r for r in self._rows({"猎聘"}) if "猎聘" in r)
        self.assertIn("你在总览页关掉了这家", row)

    def test_the_others_do_not(self):
        for r in self._rows({"猎聘"}):
            if "猎聘" in r:
                continue
            with self.subTest(row=r[:12]):
                self.assertNotIn("关掉了", r, "开着的渠道也挂了注脚")

    def test_nothing_off_means_no_footnotes(self):
        self.assertTrue(all("关掉了" not in r for r in self._rows(set())))

    def test_the_footnote_is_not_the_verdict_column(self):
        """判词那一列宽度固定、被别处按位置读过。注脚只许挂在行尾。

        **验的是位置，不是结尾那几个字。** 原来写的是
        `endswith("你在总览页关掉了这家")` —— 2026-08-23 注脚后面接了一句
        「；当初拦它的已经解了」（拦解了平台不通知，勾却一直关着），
        位置一点没变，这条却红了。注脚本来就允许再长。"""
        row = next(r for r in self._rows({"猎聘"}) if "猎聘" in r).rstrip()
        i = row.index("　← ")                      # 注脚以全角空格加箭头起头
        self.assertLess(row.index("可以抓"), i, "注脚跑到判词列前面去了")
        self.assertIn("你在总览页关掉了这家", row[i:])
        self.assertNotIn("　← ", row[i + 3:], "行尾挂了不止一条注脚")

    def test_main_actually_passes_it(self):
        """`status_lines` 收了参数、`main` 不传，注脚一辈子不出现 ——
        变异实测漏过一次（这一族在本仓库叫「算了没显示」）。"""
        src = (ROOT / "tools" / "portal_budget.py").read_text(encoding="utf-8")
        self.assertIn("status_lines(data, now, switched_off(user))", src,
                      "main 没把开关传进去")


class TheSeparationIsStillWrittenDown(unittest.TestCase):
    def test_the_workflow_still_explains_the_two_owners(self):
        t = (ROOT / "workflows" / "job-scrape.md").read_text(encoding="utf-8")
        self.assertIn("是**用户**说这一轮想不想抓这家", t)
        self.assertIn("是**平台**说现在还让不让抓", t)

    def test_the_helper_says_why_it_is_not_a_merge(self):
        """这段代码看起来就像在合并两道门，理由必须挨着它写 ——
        否则下一个人要么删掉它、要么真的去合并。"""
        src = (ROOT / "tools" / "portal_budget.py").read_text(encoding="utf-8")
        i = src.index("def switched_off(")
        seg = src[i:i + 1600]
        self.assertRegex(seg, r"不合并|不是把两道闸门合并")
        self.assertIn("缺文件", seg, "没写清那个默认")

    def test_the_check_api_is_untouched(self):
        """`--check` 的退出码是 `/job-scrape` 的闸门。**只扫代码** ——
        `switched_off` 的 docstring 里正引着「portals.json」那几个字。"""
        seg = code_of("tools/portal_budget.py", "def check(")
        self.assertNotIn("portals.json", seg, "闸门 API 开始读用户开关了")
        self.assertNotIn("switched_off", seg)


if __name__ == "__main__":
    unittest.main()
