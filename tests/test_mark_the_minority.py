# -*- coding: utf-8 -*-
"""逐行标记只标**少数**那一方，多数那一方抽到表头说一次。

一列表格里，人人都有的属性标出来是零信息 —— 一千行「（猎头代招）」占的墨，
不如表头一句「这 9 个都是猎头代招」。这条规矩本来就写在 `Shortlist.tsx` 里。

真正难的是**中间那一档**：绝大多数是猎头、但不是全部。2026-08-22 实测这份名单
9 个里 8 个猎头代招 —— 原来的判据是 `jobs.every(viaHeadhunter)`，一个例外就让
整条提示消失；改成占比之后又出了反向的事故：沿用「有表头就不标行」，
于是那**唯一一个企业直招**（XTransfer）和 8 个猎头岗长得一模一样，
表头说「8 个是猎头代招」却看不出是哪 8 个 —— 而那一个恰恰是最值钱的
（具名直招才找得到人内推）。

所以三档各有各的标法，这里钉住这个三分支不被改回二分支：

    全是猎头   → 不标行（`agencyAll`）
    绝大多数   → 反过来标那几个**不是**猎头的
    其余       → 照常标猎头那几个
"""
import re
import unittest
from pathlib import Path

SRC = (Path(__file__).resolve().parents[1] / "web" / "src" / "components"
       / "Shortlist.tsx").read_text(encoding="utf-8")


class MarkTheMinority(unittest.TestCase):
    def test_the_uniform_case_has_its_own_flag(self):
        """`agencyAll` 必须存在且被行标记读到 —— 没有它就退回了二分支。"""
        self.assertIn("agencyAll:", SRC, "constants 里没有 agencyAll")
        self.assertIn("constants?.agencyAll", SRC, "行标记没读 agencyAll")

    def test_the_mostly_case_marks_the_other_side(self):
        """绝大多数是猎头时，标的是 `!job.viaHeadhunter` 那一边。"""
        # **`=== false` 而不是 `!`** —— 2026-08-22 起这个字段是三态的：
        # `null` = 抓取器没给标记（实测 2638 个岗里 66 个），那时不许贴
        # 「企业直招」（判据见 `test_unjudged_is_not_direct_hire`）。
        # 真值取反会把「没判过」也标上，而这枚标记是「内推够得着」的信号。
        self.assertRegex(
            SRC, r"job\.viaHeadhunter === false\s*&&\s*\"（企业直招）\"",
            "占比这一档没有反过来标直招 —— 那一个直招岗会淹没在猎头堆里")

    def test_the_old_two_branch_form_is_gone(self):
        """`!constants?.agency && job.viaHeadhunter` 是被改掉的那一版，不许回来。"""
        self.assertNotRegex(
            SRC, r"!constants\?\.agency\s*&&\s*job\.viaHeadhunter",
            "行标记又变回「有表头就整列不标」了")

    def test_the_header_reports_a_share_not_all_or_nothing(self):
        """表头用占比判据，且把真实个数说出来 —— 「8 个是猎头代招」比「都是」更准。"""
        self.assertNotRegex(
            SRC, r"agency:\s*jobs\.every",
            "表头又变回 every 了：一个例外整条提示就消失")
        self.assertRegex(SRC, r"个是猎头代招", "表头没有报真实个数")

    def test_the_way_out_is_named(self):
        """猎头压满这一档时要说出具名直招的那批在哪 —— 否则「去内推」是句空话。"""
        self.assertIn("namedDirectBelow", SRC, "没有指向具名直招那批的出口")
        app = (Path(__file__).resolve().parents[1] / "web" / "src"
               / "App.tsx").read_text(encoding="utf-8")
        self.assertIn("namedDirectInRest", app, "App 侧没算这个数")
        # 判据要真的排除猎头和匿名 —— 少一个条件这个数就变成「所有还没投的」
        m = re.search(r"namedDirectInRest\s*=\s*restList\.filter\(([\s\S]{0,240}?)\)\.length",
                      app)
        self.assertIsNotNone(m, "namedDirectInRest 的算法找不到了")
        body = m.group(1)
        for cond in ("viaHeadhunter", "anonymousEmployer", "company"):
            self.assertIn(cond, body, f"算「具名直招」时漏了 {cond} 这个条件")


if __name__ == "__main__":
    unittest.main()
