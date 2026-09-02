# -*- coding: utf-8 -*-
"""「没做深评」和「没读 JD」是两件事，短名单上却由同一枚章代表。

那枚章的判据是 `!job.evaluated`，而它的字面写着「没读 JD」、悬浮提示写着
「完整 JD 没读、硬性条件没核对、公司没查」。

实测活动用户 2026-08-26：会挂那枚章的 **1416 个岗里，940 个的判词来源明写
「粗筛（读过 JD 正文）」** —— 对这 940 个，那三条里有两条是假的：JD 读了、
硬门也逐条核了，真正没做的只有公司调研与双角色审稿。

**屏幕上说的必须是真的。** 这不是措辞不够好，是把一件做过的事印成了没做：
用户照它去「先自己看一眼原文」，看的是一份已经被读过、被核过的 JD。

修法是把「读没读 JD」单独导出（`jdRead`），前端按它分两枚章：

    !evaluated && !jdRead  → 「没读 JD」（琥珀，要你动手）
    !evaluated &&  jdRead  → 「没查公司」（弱色，出材料时自己会补）

判据取判词自己记的 `来源`：写着读过就是读过；写「未抓 JD」「标题即判据」
或没记来源的一律算没读 —— **拿不准的不许说成读过**（同 04 的证据分级）。
"""
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

SL = (ROOT / "web" / "src" / "components" / "Shortlist.tsx").read_text(encoding="utf-8")
EXP = (ROOT / "tools" / "export_web_data.py").read_text(encoding="utf-8")
TYPES = (ROOT / "web" / "src" / "types.ts").read_text(encoding="utf-8")


class TheTwoChipsAreSplit(unittest.TestCase):
    def test_the_exporter_carries_whether_the_jd_was_read(self):
        self.assertIn('"jdRead"', EXP, "导出里没有这个字段，前端分不了")
        self.assertIn("jdRead?: boolean", TYPES, "类型里没有它")

    def test_the_hard_chip_requires_both(self):
        """「没读 JD」只能出现在**真没读**的那一档上。"""
        self.assertIn("!job.evaluated && !job.jdRead", SL,
                      "「没读 JD」那枚章还在只看 evaluated —— 读过 JD 的岗也会挂上")

    def test_the_soft_chip_exists(self):
        self.assertIn("!job.evaluated && job.jdRead", SL, "读过 JD 那一档没有自己的章")
        self.assertIn("没查公司", SL, "那枚章没说清到底缺的是什么")

    def test_the_soft_tooltip_does_not_claim_the_jd_is_unread(self):
        """这一枚的提示里不许再说 JD 没读、硬门没核 —— 那正是被推翻的两条。"""
        i = SL.index("!job.evaluated && job.jdRead")
        seg = SL[i:i + 400]
        for wrong in ("完整 JD 没读", "硬性条件没核对"):
            self.assertNotIn(wrong, seg, f"这一档的提示还写着「{wrong}」，而它是假的")


class TheJudgementComesFromTheRecordedSource(unittest.TestCase):
    """不许另起一套判据 —— 判词自己记着来源，就用那一份。"""

    #: 判据连同它的说明在源码里是一整块 —— 说明写在字段**上面**，所以前后都要看。
    def _seg(self, before=1400, after=500):
        i = EXP.index('"jdRead"')
        return EXP[max(0, i - before):i + after]

    def test_it_reads_the_source_field(self):
        seg = self._seg()
        self.assertIn("来源", seg, "没有去读判词记的来源")
        self.assertIn("读过 JD", seg)

    def test_unknown_counts_as_unread(self):
        """没记来源的一律算没读。误报向上（说成读过）会让人少看一眼原文。"""
        self.assertRegex(self._seg(), r"拿不准的不许说成读过|一律算没读")


class TheLiveCorpusSplitsIntoBoth(unittest.TestCase):
    """现算：两档都得有人，否则这个改动等于没分。"""

    def test_both_buckets_are_non_empty(self):
        f = ROOT / "web" / "public" / "data.json"
        if not f.is_file():
            self.skipTest("还没导出过面板数据")
        jobs = json.loads(f.read_text(encoding="utf-8")).get("jobs") or []
        noeval = [j for j in jobs if not j.get("evaluated")]
        if len(noeval) < 50:
            self.skipTest("语料太小，分不出两档")
        read = sum(1 for j in noeval if j.get("jdRead"))
        self.assertGreater(read, 0, "没有一个岗被认成「读过 JD」—— 判据可能失效了")
        self.assertLess(read, len(noeval), "全都算读过了，那这枚章又变回一个了")


if __name__ == "__main__":
    unittest.main()
