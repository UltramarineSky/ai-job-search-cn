# -*- coding: utf-8 -*-
"""回写深评时，一个投递目录只能落到**一个**岗上。

51job 实测同一详情 URL 下挂着两个不同职位——这就是全仓用 `stable_id(url, title)`
而不是 url 当一对一键的原因（`serve.find_entry`、`jd_store.key_for`、
`export_web_data.stable_id` 都这么算，各自的注释里也都写了）。

`writeback.py` 是唯一还按 url 单键匹配的：`by_url.setdefault(url, v)` **只留第一条**。
于是 B 岗的深评分数会被写到 A 岗身上，而 export 的漂移检查照旧报 B 没同步——
两个工具从此互相打架，`writeback` 的模块说明里说它就是来终结这种打架的。

写错一个岗的分数不是小事：`/job-rank` 的「已评过就跳过」、预筛、`/job-upskill`
读的都是库。判据要求：认得出就写，认不出就**拒收并说清楚**，绝不猜一个。
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import writeback as wb  # noqa: E402

URL = "https://jobs.51job.com/all/12345.html"
A = {"url": URL, "title": "AI产品经理", "company": "甲公司"}
B = {"url": URL, "title": "数据分析师", "company": "甲公司"}


class OneDirectoryResolvesToOneJob(unittest.TestCase):

    def test_a_single_candidate_is_used(self):
        e, why = wb.pick_entry([A], "甲公司_AI产品经理")
        self.assertIs(e, A)
        self.assertEqual(why, "")

    def test_a_collision_is_resolved_by_the_directory_name(self):
        e, why = wb.pick_entry([A, B], "甲公司_数据分析师")
        self.assertIs(e, B, "同 URL 两个岗，按目录名该认出「数据分析师」")
        self.assertEqual(why, "")
        e2, _ = wb.pick_entry([A, B], "甲公司_AI产品经理")
        self.assertIs(e2, A)

    def test_order_does_not_decide(self):
        """反过来排一遍还得是同一个答案——`setdefault` 那种写法在这里会翻。"""
        e, _ = wb.pick_entry([B, A], "甲公司_AI产品经理")
        self.assertIs(e, A)

    def test_an_unresolvable_collision_is_refused_not_guessed(self):
        e, why = wb.pick_entry([A, B], "甲公司_某个岗")
        self.assertIsNone(e, "认不出却还是挑了一个——那正是把分写到错的岗上")
        self.assertIn("2 个岗", why)
        self.assertIn("AI产品经理", why)
        self.assertIn("数据分析师", why)

    def test_the_source_no_longer_keys_by_url_alone(self):
        src = (ROOT / "tools" / "writeback.py").read_text(encoding="utf-8")
        self.assertNotIn('by_url.setdefault(v.get("url") or "", v)', src,
                         "又变回按 URL 单键取第一条了")
        self.assertIn("pick_entry", src)

    def test_it_reads_the_store_the_tolerant_way(self):
        """顺带钉住：老格式也得认（`_cli.seen_of` 那条统一的读法）。"""
        src = (ROOT / "tools" / "writeback.py").read_text(encoding="utf-8")
        self.assertIn("_cli.seen_of(store)", src)


if __name__ == "__main__":
    unittest.main()
