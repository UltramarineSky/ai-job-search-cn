# -*- coding: utf-8 -*-
"""规则淘汰的岗，理由一直写着 —— 但页面上只显示两个字。

`rank_breakdown.依据` 里逐岗写着为什么跳过（实测 720 个岗 **720 个都有**）：

    「年包上沿约 32 万，低于底线 42 万（原文：20-25k·13薪）」
    「这是纯数据库 DBA 岗……被「低代码平台」这个搜索词误命中」

而「不投的岗位」里那 720 行的悬浮提示是 **「不投：跳过」**。
和硬门那次（第 28 轮）是同一类：**数据在盘上、断在最后一层**。

而且这批恰恰是最该给撤销口的 —— `Shortlist.tsx` 自己的注释写着「规则最容易错：
实测 4 个年包 72-160 万的『智能体开发产品经理』死于标题含『开发』」。

> 顺带修了它**根本露不出来**这件事：搁置区按「手点的 → 能放回的 → 硬门没过的」
> 排序、截前 60 行。他手点过 89 个 —— 60 个窗口全被占满，
> 规则淘汰的 720 个一行都看不到。那段注释写的时候「能放回的」只有 90 个，
> 现在是 809。
"""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tests"))
import export_web_data as X  # noqa: E402
from _srcscan import code_of  # noqa: E402

SL = (ROOT / "web" / "src" / "components"
      / "Shortlist.tsx").read_text(encoding="utf-8")
_SL_CODE = re.sub(r"\{/\*[\s\S]*?\*/\}|/\*[\s\S]*?\*/|^\s*//.*$", "", SL, flags=re.M)


class TheReasonReachesTheExport(unittest.TestCase):
    def test_the_breakdown_reason_fills_skip_reason(self):
        code = code_of("tools/export_web_data.py", "def build_payload(") \
            if "def build_payload(" in (ROOT / "tools" / "export_web_data.py").read_text(encoding="utf-8") \
            else (ROOT / "tools" / "export_web_data.py").read_text(encoding="utf-8")
        self.assertIn('"依据"', code, "导出侧没读那份拆解里的依据")

    def test_user_written_reason_still_wins(self):
        """他自己写的原因优先 —— 规则给的只是兜底。"""
        src = (ROOT / "tools" / "export_web_data.py").read_text(encoding="utf-8")
        i = src.index('"skipReason":')
        seg = src[i:i + 500]
        self.assertLess(seg.index("ustate"), seg.index("依据"),
                        "规则依据盖过了他自己写的原因")

    def test_only_rule_skipped_jobs_get_it(self):
        """手点不投的岗不该被塞一个规则依据 —— 那不是他的理由。"""
        src = (ROOT / "tools" / "export_web_data.py").read_text(encoding="utf-8")
        i = src.index('"skipReason":')
        self.assertIn("is_rule_skipped(e)", src[i:i + 500],
                      "没限定只有规则淘汰的才取依据")


class ThePanelShowsIt(unittest.TestCase):
    def test_the_rule_skipped_branch_reads_it(self):
        self.assertIn("job.skipReason\n          ? job.skipReason", _SL_CODE,
                      "规则淘汰那一支还是直接落到判词")

    def test_the_verdict_is_still_the_last_resort(self):
        """没有依据时仍要说点什么 —— 别留一个空悬浮。"""
        self.assertIn("plainVerdict(job.gateFailReason || job.verdict)", _SL_CODE)


class TheRestorableRowsAreActuallyVisible(unittest.TestCase):
    def test_the_manual_tier_is_capped(self):
        self.assertIn("MINE_CAP", _SL_CODE, "手点那一档还是不限量")

    def test_the_cap_leaves_room_for_the_rest(self):
        """留给规则淘汰的名额 = CAP − 手点那一档的上限。"""
        self.assertRegex(_SL_CODE, r"CAP - Math\.min\(mineRows\.length, MINE_CAP\)",
                         "剩余名额算错了，规则淘汰的还是挤不进来")

    def test_the_total_cap_survives(self):
        """整份铺开会让页面高 16 万像素、浏览器卡死 —— 那条不能被顺手放松。"""
        self.assertIn("const CAP = 60", _SL_CODE)


if __name__ == "__main__":
    unittest.main()
