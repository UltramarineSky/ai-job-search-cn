# -*- coding: utf-8 -*-
"""「还有 N 个材料就绪但没投」必须是数出来的，不能是减出来的。

`next_step` 原来算 `left = counts["materials"] - counts["applied"]`。
那个减法有个没写出来的前提：**投过的岗一定也留了材料目录**。它不成立——
手动投的岗、或直接跑 `/job-outcome` 记一笔的岗，`applied` 有、`materials` 没有，
减法就会把它多减一次。

2026-08-12 实测：面板说「还有 104 个」，直接数是 105，差的正是一个
「投了但没材料目录」的岗。少报一个不致命，但这类**代理式计数**会随着
手动投递变多而越错越远，而且错得完全无声。
"""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from build_dashboard import next_step  # noqa: E402


BASE = dict(scraped=100, ranked=90, materials=20, applied=5, interviewing=0)


def text(counts):
    return next_step(counts, True, "https://x/1")[0]


class ReadyCountIsCounted(unittest.TestCase):

    def test_uses_the_real_count_when_given(self):
        """给了 ready 就用 ready，不再自己减。"""
        self.assertIn("15 个", text({**BASE}))          # 20-5 的旧算法
        self.assertIn("16 个", text({**BASE, "ready": 16}))

    def test_the_subtraction_would_have_been_wrong(self):
        """复现实测那一例：投了但没材料目录的岗让减法少报一个。

        materials=158 / applied=54 → 减法给 104；真实「有材料且没投」是 105。
        """
        real = {**BASE, "materials": 158, "applied": 54, "ready": 105}
        self.assertIn("105 个", text(real))
        self.assertNotIn("104 个", text(real),
                         "又退回 materials − applied 了")

    def test_zero_ready_does_not_claim_there_is_work(self):
        """全投完了就该指回抓岗，不能因为减法算出正数而催人去投。

        断言从「等回复」换成「接着抓」：那一格 2026-08-29 改了口径
        （`AGENTS.md`「跟进归用户，工具不催」）。这条测试盯的东西没变 ——
        `ready` 为 0 时不许说「还有材料没投」。
        """
        t = text({**BASE, "materials": 20, "applied": 5, "ready": 0})
        self.assertIn("接着抓", t)
        self.assertNotIn("材料就绪但没投", t)

    def test_both_panels_supply_it(self):
        """两个面板都得传 ready——只有一边传，两页就会各报各的数。"""
        for f in ("build_dashboard.py", "export_web_data.py"):
            with self.subTest(file=f):
                src = (ROOT / "tools" / f).read_text(encoding="utf-8")
                self.assertIn('"ready"', src, f"{f} 没提供 ready 计数")

    def test_web_export_reuses_the_row_filter(self):
        """网页版的 ready 必须借 `funnels_of` 的口径，不能另写一份筛选。

        另写一份就会与页面行集漂移——这一页最容易出现的自相矛盾就是
        「名单显示 105，下一步按另一个数提醒」。

        **认两种等价写法**：现算 `funnels_of(j)`，或读上面刚存好的 `j["funnels"]`
        （存进去的就是它的返回值）。这条原来只认前者，于是「别按岗重算四遍」
        这个纯性能改动把它弄红了——又一次「断言绑死一种写法而非规则」。
        """
        src = (ROOT / "tools" / "export_web_data.py").read_text(encoding="utf-8")
        block = src[src.index('"ready": sum('):][:300]
        self.assertTrue(
            "funnels_of(j)" in block or 'j["funnels"]' in block,
            "ready 没有借用 funnels_of 的口径，会和页面行集分家")

    def test_the_cached_field_really_holds_funnels_of(self):
        """上一条认 `j["funnels"]`，前提是那一格装的确实是 `funnels_of` 的返回值。
        少了这条，缓存字段哪天改成别的算法，上面就成了一句空话。"""
        src = (ROOT / "tools" / "export_web_data.py").read_text(encoding="utf-8")
        self.assertIn('j["funnels"] = funnels_of(j)', src,
                      "funnels 那一格不再是 funnels_of 算的了")


if __name__ == "__main__":
    unittest.main()
