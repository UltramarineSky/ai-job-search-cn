# -*- coding: utf-8 -*-
"""抓取默认要跑全部分类，剪枝按实测数据、不按拍脑袋的顺序。

用户 2026-08-12：「job-scrape 默认应该最大去抓取吧」。原来的默认是
「只跑前 3 个优先级分类」，两个后果都实测到了：

- **「优先级 4：兜底」从来没有自动跑过**。某用户 1127 个岗全部评完、
  「值得投」那档 50 个投光补不上货时，兜底那一类一次都没跑过。
- 更要命的是**它替代了一份真实数据**：`QUERY-YIELD` 表（每个词在每个平台
  带来过多少新岗）和 profile 里「实测低效、可跳过的关键词」那一节，都是
  实测结论。拿一个当初拍的顺序去截断，等于把测出来的东西扔了。
  而那一节**当时根本没有任何代码路径读过它**——写在资料里，从没被用上。

改后：默认全跑 + 按实测剪枝（挖空的、低效的自动跳过），`broad` 的含义
收窄成「连剪掉的也重跑」。
"""

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WF = (ROOT / "workflows" / "job-scrape.md").read_text(encoding="utf-8")


class DefaultIsFullCoverage(unittest.TestCase):

    def test_default_runs_every_category(self):
        self.assertIn("默认跑全部优先级分类", WF)

    def test_the_old_truncation_is_gone(self):
        """只留在「原来是这样，改掉了」的说明里，不能还是活规则。"""
        for line in WF.splitlines():
            if "top 3 priority" in line or "前 3 个优先级分类" in line:
                self.assertTrue(line.lstrip().startswith(">"),
                                f"截断规则还活着，不在说明块里：{line.strip()[:70]}")

    def test_pruning_uses_both_measured_sources(self):
        """两份实测数据都要用上——只用一份等于另一份继续白写。"""
        self.assertIn("QUERY-YIELD", WF)
        self.assertIn("实测低效、可跳过的关键词", WF,
                      "profile 里那一节还是没人读")

    def test_broad_now_means_ignore_the_pruning(self):
        self.assertIn("连实测已挖空、已判低效的词也重跑", WF)
        idx = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("连上轮没产出的词也重抓一遍", idx,
                      "索引里 broad 的说明还是旧的（面板帮助就是它）")


if __name__ == "__main__":
    unittest.main()
