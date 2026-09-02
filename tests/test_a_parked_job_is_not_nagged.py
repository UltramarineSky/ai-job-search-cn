"""搁置的岗不催投递——「不数它」和「不催它」必须是同一个判断。

三类岗进搁置区：标了不投、已下线、重复挂法。`funnels_of` 一直知道这件事，
它的注释还写着理由：「标了『不投』的岗虽然做过材料，但它不再是待办」。

**而 `job_next_step` 不知道。** 2026-08-20 实测 90 个岗一边躺在搁置区、
一边在详情里被告知「材料就绪，还没投——复制开场白、开职位链接自己投出去，
投完回来记一笔」：77 个是用户自己刚标的不投，**12 个的职位已经关了**。
催一个关掉的岗去投，比不催更糟——用户点开链接才发现是死页。

同一个概念写了两份，漏的那份没人发现，因为它不在计数里、只在文案里。
现在正本是 `build_dashboard.is_parked`，两边共用。

**位置有讲究**：这道闸在「已投/面试/offer」之后。那三步讲的是已经发生的事，
搁置与否都该照给（投完再标不投，仍要能记回复）；从材料那步往下才是在催他
**开始**做点什么。
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import build_dashboard as bd  # noqa: E402


class ParkedJobsGetNoNudge(unittest.TestCase):

    def _job(self, **kw):
        base = {"materials": {"greeting": "你好"}, "score": 80,
                "verdict": "值得投", "company": "某公司", "url": "https://x/1"}
        base.update(kw)
        return base

    def test_each_parked_shape_is_silent(self):
        for field in ("skipped", "expired", "dupOf"):
            with self.subTest(field):
                self.assertIsNone(bd.job_next_step(self._job(**{field: True})),
                                  f"{field} 的岗还在被催投递——它已经在搁置区了")

    def test_an_active_job_still_gets_nudged(self):
        """闸不能关过头：没搁置的岗照样要催，否则「下一步」整块消失。"""
        step = bd.job_next_step(self._job())
        self.assertIsNotNone(step, "正常的岗没有下一步了——闸关过头了")
        self.assertIn("材料就绪", step["text"])

    def test_in_flight_steps_survive_being_parked(self):
        """已投/面试/offer 在搁置之后仍要给——那是已经发生的事，不是催他开始。"""
        for status, want in (("interview", "/job-interview"),
                             ("offer", "/job-offer"),
                             ("applied", "/job-outcome")):
            with self.subTest(status):
                j = self._job(skipped=True, applied={"status": status, "date": "2026-08-01"})
                step = bd.job_next_step(j)
                self.assertIsNotNone(step, f"{status} 的岗被搁置就没下一步了——"
                                           "投都投了，回复还得记")
                self.assertTrue(step["command"].startswith(want), step)

    def test_both_sides_share_one_predicate(self):
        """收拢不是删掉字面量就完了——两边得真的引用同一个函数。"""
        exp = (ROOT / "tools" / "export_web_data.py").read_text(encoding="utf-8")
        i = exp.index("def funnels_of")
        body = exp[i:exp.index("\nROOT = ", i)]
        self.assertIn("is_parked(job)", body,
                      "funnels_of 又自己手写了一遍三类搁置")
        self.assertNotIn('job.get("dupOf") or job.get("skipped")', body,
                         "旧的手写判断还在——两份迟早分叉，上次分叉了 90 个岗")


class TheRealCorpusAgrees(unittest.TestCase):
    """控制测试：真实数据里，被催的岗必须都在漏斗格里。"""

    def test_no_nagged_job_sits_in_the_parked_area(self):
        f = ROOT / "web" / "public" / "data.json"
        if not f.is_file():
            self.skipTest("还没导出过面板数据")
        jobs = json.loads(f.read_text(encoding="utf-8")).get("jobs", [])
        nagged = [j for j in jobs
                  if (j.get("nextStep") or {}).get("text", "").startswith("材料就绪")]
        if not nagged:
            self.skipTest("现在没有备好料还没投的岗")
        bad = [j["title"][:26] for j in nagged
               if "materials" not in (j.get("funnels") or [])]
        self.assertEqual(bad, [],
                         f"{len(bad)} 个岗一边被催投递、一边不在「材料就绪」格里——"
                         "漏斗和详情各说各话：" + "、".join(bad[:5]))


if __name__ == "__main__":
    unittest.main()
