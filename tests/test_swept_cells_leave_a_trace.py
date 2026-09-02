# -*- coding: utf-8 -*-
"""扫过的「词 × 平台」必须留痕，否则下一轮会把它当新大陆重扫。

`query_yield.py` 从 `seen_jobs.json` 的 `found_by` 反推每个词在每个平台的产出。
**没入库的岗它看不见**——于是「这个格子扫过、全是低薪、一个没要」这件事无处记录。

2026-08-13 `/job-auto` 实测：智联扫 3 个词共 43 个岗、前程无忧扫 38 个，
因为全在薪资底线以下没入库，跑完产出表照旧显示那 6 个格子是空的。
下一轮的「优先补空格子」清单会原样再列一遍。
"""

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WF = (ROOT / "workflows" / "job-scrape.md").read_text(encoding="utf-8")


class SweptCellsAreRecorded(unittest.TestCase):

    def test_the_rule_is_written_down(self):
        self.assertIn("扫过的格子必须留痕", WF)
        self.assertIn("没入库的岗它看不见", WF)

    def test_it_says_to_store_the_rejects(self):
        """光说「要留痕」不够，得写清怎么留：入库并落已结案状态。"""
        self.assertIn("按薪资/方向筛掉的岗也要入库", WF)
        self.assertIn("粗筛：不建议", WF)

    def test_it_distinguishes_rejects_from_backlog(self):
        """必须解释清楚它和 Step 0.5 防的「积压」不是一回事，
        否则下一个读的人会以为两条规则打架，然后随便挑一条执行。"""
        self.assertIn("它们**不是积压**", WF)
        self.assertIn("Step 0.5", WF)


if __name__ == "__main__":
    unittest.main()


class EveryDriverNameLandsInAColumn(unittest.TestCase):
    """留痕了、但 portal 名对不上别名表，等于没留痕。

    这是上面那条的变种，而且更隐蔽：岗**入库了**，`found_by` 也写了，
    只是 `portal` 写成表里没有的名字 → 整批落进「其它」列 →
    「下一轮最值钱的格子」照旧把这几家推荐一遍，永远推荐下去。

    2026-08-19 实测：用 AI 工具自带的浏览器扩展抓 BOSS / 智联 / 前程共 72 个岗，
    portal 写成 `boss-browser` / `zhaopin-browser` / `51job-browser`——三个都不在
    `PORTAL_ALIAS` 里（表里只有 `-cdp` 那一代）。跑完 `query_yield --apply`，
    刚扫完的「智能体开发 × 前程无忧」等三格仍列在「还没跑过」的清单里。

    根因是**后缀会随驱动方式增生**：同一家平台先后有过 CLI、CDP 代理、浏览器扩展
    三种驱动，每换一种就多一个后缀。所以守的不是某一个名字，是「每种驱动方式的
    名字都要落进四列之一」。
    """

    def _portal_of(self):
        import sys
        sys.path.insert(0, str(ROOT / "tools"))
        import query_yield as qy
        return qy.norm, qy.PORTALS

    def test_every_known_driver_suffix_maps_to_a_real_column(self):
        portal_of, PORTALS = self._portal_of()
        for base, col in (("liepin", "猎聘"), ("51job", "前程无忧"),
                          ("boss", "BOSS"), ("zhaopin", "智联")):
            for name in (base, f"{base}-cdp", f"{base}-browser"):
                got = portal_of(name)
                self.assertIn(got, PORTALS,
                              f"portal「{name}」落进了「{got}」——不在四列里，"
                              f"这一批的产出会被当成没跑过，下轮重扫")
                self.assertEqual(got, col, f"portal「{name}」应归到「{col}」列")

    def test_an_unknown_driver_is_still_caught_by_the_column_check(self):
        """反例：编一个没登记的后缀，必须落到「其它」——说明这条检测有效。"""
        portal_of, PORTALS = self._portal_of()
        self.assertNotIn(portal_of("boss-carrierpigeon"), PORTALS)
