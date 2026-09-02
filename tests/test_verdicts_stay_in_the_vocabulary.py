# -*- coding: utf-8 -*-
"""判词只能取那五档。造一个新的，面板就没地方放它。

2026-08-13 实测：`/job-auto` 跑批量粗筛时，给「薪资面议、JD 还没读」的岗
编了一个 `粗筛：待定`。框架里没有这一档（`job-rank.md` 只列
强匹配 / 值得投 / 可以考虑 / 不建议 / 跳过，还专门写了「不造英文档」——
造中文的一样不行）。

后果不是「多了个标签」，是**路由错位**：`App.tsx` 把「可以考虑」折叠进下半区，
判断依据是判词**等于**「可以考虑」。「待定」不匹配，于是 4 个连 JD 都没读过、
薪资还没谱的岗留在了最显眼的主表里，而那份表叫「可以投的岗位」。
用户当场发现：「dashboard为什么突然多了一堆45分在前面了」。

判词是**路由键**，不是自由文本。加一档就要同时想清楚它在面板哪个区、
在漏斗哪一格、被哪些筛选排除——没想清楚就别加。
"""

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

#: 框架里的五档，正本在 `_cli.VERDICTS`（语义正本是 04 文档；这里原来自抄一份，
#: 2026-08-20 收拢）。加上硬门没过时的那句——它不是「档」，但确实会写进 rank_verdict。
import sys as _sys
_sys.path.insert(0, str(ROOT / "tools"))
import _cli
BANDS = set(_cli.VERDICTS)
GATE = "不满足硬性条件"

#: 已下线的岗上历史遗留的状态描述。它们只进搁置区，不参与任何路由，
#: 所以不拦——但**只在 expired 上豁免**，活着的岗一律按五档来。
STATE_WORDS = {"已评分", "已下线（评分前发现）"}


def plain(v: str) -> str:
    return re.sub(r"^粗筛[：:]\s*", "", (v or "").strip())


class VerdictsAreRoutingKeys(unittest.TestCase):

    def _jobs(self):
        f = ROOT / "web" / "public" / "data.json"
        if not f.is_file():
            self.skipTest("没有面板快照")
        return json.loads(f.read_text(encoding="utf-8")).get("jobs", [])

    def test_live_jobs_use_the_five_bands(self):
        bad = []
        for j in self._jobs():
            if j.get("expired"):
                continue
            v = plain(j.get("verdict") or "")
            if not v or v in BANDS or v.startswith(GATE) or v.startswith("硬门"):
                continue
            bad.append(f"{v!r} —— {(j.get('title') or '')[:28]}")
        self.assertEqual(sorted(set(bad)), [],
                         "这些判词不在五档里，面板不知道该把它们放哪：\n  "
                         + "\n  ".join(sorted(set(bad))))

    def test_the_framework_lists_exactly_these(self):
        """词表得跟框架同步，否则这条守卫拦的是自己想象的规矩。"""
        t = (ROOT / "workflows" / "job-rank.md").read_text(encoding="utf-8")
        for b in BANDS:
            with self.subTest(band=b):
                self.assertIn(b, t)
        self.assertIn("中文的新档同样不许造", t,
                      "job-rank 只禁了英文档——而实测被绕过的正是中文的")
        ja = (ROOT / "workflows" / "job-apply.md").read_text(encoding="utf-8")
        self.assertIn("不造英文档", ja, "job-apply 里那条告诫没了")

    def test_the_panel_routes_by_exact_match(self):
        """折叠区靠判词**精确等于**「可以考虑」来分流——所以造新档必然错位。

        钉住这个事实，下一个想加档的人能从这条测试看到代价。
        """
        tsx = (ROOT / "web" / "src" / "App.tsx").read_text(encoding="utf-8")
        self.assertIn('=== "可以考虑"', tsx)

    def test_the_detector_can_fail(self):
        self.assertEqual(plain("粗筛：待定"), "待定")
        self.assertNotIn(plain("粗筛：待定"), BANDS)
        self.assertIn(plain("粗筛：可以考虑"), BANDS)
        self.assertIn(plain("值得投"), BANDS)


if __name__ == "__main__":
    unittest.main()
