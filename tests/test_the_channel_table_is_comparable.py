# -*- coding: utf-8 -*-
"""同一页上，头条按猎头/直招拆，渠道表却把两者一视同仁地横着比。

投后统计那一页有两处在解释「投了这么多为什么没回音」：

    头条    「其中 43 个投的是猎头代招——简历先进猎头的库，推不推由他定，
             那批没动静**说明不了你简历的事**。但企业直招那 33 个也是一个
             回音都没有，这批才是信号。」
    渠道表  「投在哪个网站，那边回不回」：猎聘 66 / BOSS 直聘 16 / 智联招聘 3，
             全 0%，结论「每个网站都是 0，那问题多半不在选哪个网站」。

**而各渠道的猎头占比差得极远。** 实测活动用户 2026-08-23：

    猎聘        66 个 · 猎头 43（65%）
    BOSS 直聘   16 个 · 猎头  1（ 6%）
    智联招聘     3 个 · 猎头  0

头条刚说完那 43 个的沉默说明不了什么，渠道表转头就把它们算进「猎聘 0%」——
读者会把它读成「猎聘这个网站不行」，而那 66 个里三分之二根本没到用人方手里。
两段隔着不到一屏。

## 判据不是新立的，是本来就有、只用在了一半

导出侧那段注释早就写着：

> 「投了 N 个 0 回音」这句话的分量**完全取决于 N 里有多少是猎头代招**：
> 简历投给猎头是先进他的库，推不推、什么时候推由他定，岗位可能早关了——
> 那批的沉默说明不了简历的事。拿混在一起的总数去说「回头审简历」，
> 是把渠道问题误判成简历问题。

这条当时只落在**全局**那个数（`viaAgency`）上。而逐渠道的差异，
恰恰是让这张表不能横着比的原因 —— 同一条规则，用在总数上、没用在分表上。

## 顺带修掉一个错的实测数

`tracker.channel_of` 的文档写着「85 行全是 `liepin.com` …… **全在猎聘**」。
实际是 66 / 16 / 3。这个数**错到与它支撑的功能的前提相矛盾**：
面板那张渠道表有 `length > 1` 的门槛（只有一个渠道时不显示），
照那句话这张表根本不该出现。
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPORT = (ROOT / "tools" / "export_web_data.py").read_text(encoding="utf-8")
OS_TSX = (ROOT / "web" / "src" / "components"
          / "OutcomeStats.tsx").read_text(encoding="utf-8")
TYPES = (ROOT / "web" / "src" / "types.ts").read_text(encoding="utf-8")
TRACKER = (ROOT / "tools" / "tracker.py").read_text(encoding="utf-8")


class TheExporterCountsAgencyPerChannel(unittest.TestCase):
    def test_the_bucket_has_three_slots(self):
        self.assertIn("by_channel.setdefault(ch, [0, 0, 0])", EXPORT,
                      "渠道桶还是两格 —— 猎头数没地方放")

    def test_the_comment_says_what_the_third_slot_is(self):
        i = EXPORT.index("by_channel = {}")
        self.assertIn("其中猎头代招几个", EXPORT[i:i + 120])

    def test_it_counts_from_the_same_judgement_as_the_headline(self):
        """**必须用 `viaHeadhunter`**，别在这儿另起一套判法 ——
        头条和这张表得说同一件事。"""
        i = EXPORT.index("by_channel.setdefault(ch, [0, 0, 0])")
        seg = EXPORT[i:i + 900]
        self.assertIn('j.get("viaHeadhunter")', seg)
        self.assertIn("c[2] += 1", seg)

    def test_it_is_exported(self):
        i = EXPORT.index('"byChannel"')
        self.assertIn('"agency": n[2]', EXPORT[i:i + 260])

    def test_the_reason_is_recorded_with_its_numbers(self):
        i = EXPORT.index("by_channel.setdefault(ch, [0, 0, 0])")
        seg = " ".join(EXPORT[i:i + 900].split())
        self.assertRegex(seg, r"猎聘 66 个里 43 个是猎头（65%）")
        self.assertIn("2026-08-23", seg, "实测数没带日期")
        self.assertRegex(seg, r"两段隔着不到一屏")

    def test_it_cites_the_rule_it_extends(self):
        """这条判据是本来就有的，不是新发明。引它，别另立一条。"""
        seg = " ".join(EXPORT[EXPORT.index("by_channel.setdefault(ch, [0, 0, 0])"):
                              ][:900].split())
        self.assertRegex(seg, r"上面那段已经立了判据")

    def test_the_global_rule_it_extends_survives(self):
        """**在它原来的地方找，不是全文找。** 上面那条断言要求新注释**引用**
        这句原话 —— 于是全文扫的话，把正本删掉照样绿（变异实测），
        找到的是我自己那份抄件。正本在 `direct` 那个分支里。"""
        i = EXPORT.index("**直招那批要单独有个分母。**")
        self.assertRegex(" ".join(EXPORT[i:i + 700].split()),
                         r"完全取决于 N 里有多少是猎头代招")


class ThePanelSaysTheTableIsNotComparable(unittest.TestCase):
    def _note(self) -> str:
        i = OS_TSX.index("投在哪个网站，那边回不回")
        return OS_TSX[i:OS_TSX.index("被拒的原因", i)]

    def test_the_caveat_exists(self):
        self.assertIn("但这几栏不能直接比：", self._note(),
                      "渠道表仍然只报数，不说它们不可比")

    def test_it_names_both_ends(self):
        """只说「猎聘猎头多」没有对照，读者不知道多到什么程度。"""
        seg = self._note()
        self.assertIn("hi.channel", seg)
        self.assertIn("lo.channel", seg)

    def test_it_repeats_why_agency_silence_means_nothing(self):
        """光给个数不够 —— 要说清那个数为什么让这一栏不可比。"""
        flat = "".join(self._note().split()).replace('"+"', "")
        self.assertIn("简历进猎头的库，推不推由他定", flat)
        self.assertIn("那批没动静说明不了这个网站行不行", flat)

    def test_it_stays_quiet_when_the_shares_are_close(self):
        """占比都差不多时这句话是噪音，而且会稀释头条那句。"""
        seg = self._note()
        self.assertIn("< 0.3", seg, "没有差距门槛 —— 它会每次都出现")
        self.assertRegex(" ".join(seg.split()), r"只在真的差得远时才说")

    def test_it_stays_quiet_with_a_single_channel(self):
        self.assertIn("s.byChannel!.length < 2", self._note())

    def test_it_handles_a_missing_agency_field(self):
        """`agency` 是可选字段。旧的 data.json 里没有它，不能因此崩掉。

        **四处都要兜，逐处钉。** 只验「`c.agency ?? 0` 出现过」是不够的：
        它在文件里出现多次，把其中任何一处换成 `c.agency!` 都照样绿
        （变异实测第一版就是这么漏的 —— 变异改的是筛选那处，
        而断言验的是 `share()` 那处）。"""
        seg = self._note()
        self.assertIn("(c.agency ?? 0) > 0", seg, "筛选那处没兜住缺字段")
        self.assertIn("c.sent ? (c.agency ?? 0) / c.sent : 0", seg,
                      "算占比那处没兜住缺字段")
        self.assertIn("${hi.agency ?? 0}", seg, "印第一个数那处没兜住缺字段")
        self.assertIn("${lo.agency ?? 0}", seg, "印第二个数那处没兜住缺字段")

    def test_the_three_existing_verdicts_survive(self):
        """原来那三支（有回音 / 全 0 且能拆 / 全 0 拆不出）一条都不能少。"""
        seg = self._note()
        for w in ("哪个高就往哪个多投一点",
                  "上面那栏已经拆出来了",
                  "而在简历或岗位匹配这两样上"):
            with self.subTest(w=w):
                self.assertIn(w, seg)

    def test_the_type_declares_it(self):
        i = TYPES.index("byChannel?:")
        self.assertIn("agency?: number", TYPES[i:i + 400])


class TheStaleNumberIsFixed(unittest.TestCase):
    def _doc(self) -> str:
        i = TRACKER.index("def channel_of(")
        return TRACKER[i:TRACKER.index('said = (row.get("channel")', i)]

    def test_it_no_longer_claims_a_single_channel(self):
        """**只看正文，不看那段 `>` 引用。** 下面那块逐字引了旧措辞
        （说明它为什么被换掉），整段扫会撞上自己的解释 —— 这个坑本仓库踩过不止一次。"""
        body = "\n".join(ln for ln in self._doc().splitlines()
                         if not ln.strip().startswith(">"))
        self.assertNotIn("全在猎聘", body)

    def test_it_carries_the_real_split(self):
        seg = " ".join(self._doc().split())
        self.assertRegex(seg, r"猎聘 66 · BOSS 直聘 16 · 智联招聘 3")
        self.assertIn("2026-08-23", seg)

    def test_it_records_why_the_old_number_mattered(self):
        """一个数错到与它支撑的功能的前提矛盾，说明它从没被回读过 ——
        这比数字本身更值得记。"""
        seg = " ".join(self._doc().split())
        self.assertRegex(seg, r"`length > 1` 的门槛")
        self.assertRegex(seg, r"从来没被回读过")

    def test_the_threshold_it_cites_really_exists(self):
        """引了面板的门槛，那门槛得真的在。"""
        self.assertIn("s.byChannel && s.byChannel.length > 1", OS_TSX)

    def test_the_derivation_still_prefers_the_written_column(self):
        """手填过 `channel` 的以他为准 —— 这条不许被这次改动带掉。"""
        seg = self._doc()
        self.assertIn("手填过 `channel` 的以他为准", seg)
        self.assertIn("只推不写", seg)


if __name__ == "__main__":
    unittest.main()
