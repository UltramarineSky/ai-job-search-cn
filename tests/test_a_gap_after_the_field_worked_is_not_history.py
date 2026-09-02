# -*- coding: utf-8 -*-
"""「本字段是后加的，更早抓的补不上」——那句话是断言，不是算出来的，而且是错的。

`query_yield` 的整个设计前提写在它自己开头：「**发现交给数据**——每个岗记下
`found_by`（哪个词搜到的），不再靠回忆」。报告末尾对没记来源的那批只说一句
安慰，说它们是历史遗留、不用管。

实测活动用户 2026-08-23，按日看覆盖率：

    07-30  缺 150/150 = 100%    机制还没跑起来
    08-10  缺 171/171 = 100%
    08-11  缺 119/507 =  23%
    08-12  缺   0/274 =   0%    ← 跑通了
    08-13  缺   0/ 56 =   0%
    08-14  缺 186/186 = 100%    ← 之后整整一天全丢了
    08-17  缺   0/1008 =  0%

**08-14 那 186 个不是历史遗留，是一次回退。** 而那句安慰恰恰让人不会去看 ——
正是本仓库反复点名的最贵错法：把「上游丢了数据」说成「核对过没问题」。

代价不抽象：没来源的 702 个岗里 **129 个是评过分能投的**，占全部可投岗的
**30%**。而这张表决定的是**抓取额度往哪儿花**（每次请求之间要隔 8/4/3 秒、撞了风控整站冷却 24 小时）。

## 界线取哪儿：第一个满覆盖日

第一版取「有来源的岗里最早那个 `first_seen`」，被一个 07-29 的孤例把线拖到
前面，报出 **649** 个 —— 虚高 3.5 倍。报大了和报小了一样坏：读的人核对一次
发现多数是历史遗留，下次就不看这一行了。

改成「第一个覆盖率 100% 的日子」（当天不少于 `FULL_DAY_MIN` 个岗）之后是
**186**，全在 08-14。同一条流水线前一天做得到、后一天没做，无从辩解。
"""
import json
import pathlib
import re
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import query_yield as qy  # noqa: E402

QY = (ROOT / "tools" / "query_yield.py").read_text(encoding="utf-8")


def flat(s: str) -> str:
    s = " ".join(re.sub(r"^\s*>\s?", "", s, flags=re.M).split())
    return re.sub(r"(?<=[一-鿿，。；：、（）「」])"
                  r" +(?=[一-鿿，。；：、（）「」])", "", s)


def seen_of(spec: dict) -> dict:
    """`{日期: (有来源, 没来源)}` → 一份最小的 seen。"""
    out, i = {}, 0
    for day, (ok, missing) in spec.items():
        for _ in range(ok):
            out[f"k{i}"] = {"first_seen": day, "found_by": "某词"}
            i += 1
        for _ in range(missing):
            out[f"k{i}"] = {"first_seen": day}
            i += 1
    return out


class OnlyGapsAfterAFullDayCount(unittest.TestCase):
    def test_nothing_missing_means_nothing_to_report(self):
        n, days = qy.late_misses(seen_of({"2026-08-12": (20, 0)}))
        self.assertEqual((n, days), (0, {}))

    def test_gaps_before_the_full_day_are_history(self):
        """字段还不存在时抓的，确实补不上 —— 不许报成漏记。"""
        n, days = qy.late_misses(seen_of({
            "2026-08-10": (0, 171), "2026-08-12": (20, 0)}))
        self.assertEqual((n, days), (0, {}))

    def test_a_gap_after_the_full_day_is_a_leak(self):
        n, days = qy.late_misses(seen_of({
            "2026-08-12": (20, 0), "2026-08-14": (0, 186)}))
        self.assertEqual(n, 186)
        self.assertEqual(days, {"2026-08-14": 186})

    def test_both_sides_at_once(self):
        """真实语料就是这个形状：前面一段历史，中间跑通，后面漏一天。"""
        n, days = qy.late_misses(seen_of({
            "2026-08-10": (0, 171), "2026-08-11": (388, 119),
            "2026-08-12": (274, 0), "2026-08-14": (0, 186),
            "2026-08-17": (100, 0)}))
        self.assertEqual(n, 186, "把 08-11 之前那批也算成漏记了")
        self.assertEqual(list(days), ["2026-08-14"])

    def test_a_partial_day_after_the_line_counts_only_its_gap(self):
        n, days = qy.late_misses(seen_of({
            "2026-08-12": (20, 0), "2026-08-15": (7, 3)}))
        self.assertEqual((n, days), (3, {"2026-08-15": 3}))

    def test_several_leaky_days_are_all_listed(self):
        """按日期归档 —— 一个日期比一个总数好查得多。"""
        _, days = qy.late_misses(seen_of({
            "2026-08-12": (20, 0), "2026-08-14": (0, 9),
            "2026-08-16": (0, 4)}))
        self.assertEqual(days, {"2026-08-14": 9, "2026-08-16": 4})


class ATinyDayIsNotABoundary(unittest.TestCase):
    def test_a_one_job_day_does_not_set_the_line(self):
        """只抓到 1 个的日子全中，说明不了机制在跑。"""
        n, _ = qy.late_misses(seen_of({
            "2026-08-01": (1, 0), "2026-08-10": (0, 171),
            "2026-08-12": (20, 0)}))
        self.assertEqual(n, 0, "被一个只有 1 个岗的日子当成了界碑")

    def test_the_threshold_is_a_named_constant(self):
        self.assertGreaterEqual(qy.FULL_DAY_MIN, 2)
        i = QY.index("FULL_DAY_MIN = ")
        seg = flat(QY[max(0, i - 400):i].replace("#:", " "))
        self.assertRegex(seg, r"只抓到一两个的 日子全中|只抓到一两个的日子全中")

    def test_no_full_day_at_all_reports_nothing(self):
        """一天都没满覆盖过 —— 那就没有界线，别硬报。"""
        n, days = qy.late_misses(seen_of({
            "2026-08-10": (0, 50), "2026-08-11": (5, 45)}))
        self.assertEqual((n, days), (0, {}))

    def test_entries_without_a_date_are_ignored(self):
        seen = seen_of({"2026-08-12": (20, 0)})
        seen["nodate"] = {}
        self.assertEqual(qy.late_misses(seen), (0, {}))

    def test_non_dict_entries_do_not_crash(self):
        seen = seen_of({"2026-08-12": (20, 0)})
        seen["junk"] = "字符串"
        self.assertEqual(qy.late_misses(seen)[0], 0)


class TheReportTellsTheTruth(unittest.TestCase):
    BY = {"某词": {"猎聘": [{"fit": "high"}] * 6}}

    def test_the_blanket_reassurance_is_gone(self):
        block = qy.build_block(self.BY, "2026-08-23", 702)
        self.assertNotIn("本字段是后加的", block,
                         "又无条件说了一遍「后加的，补不上」")

    def test_it_still_says_they_are_not_in_the_table(self):
        """这半句是对的，不能连着删掉。"""
        self.assertIn("它们不进上表",
                      qy.build_block(self.BY, "2026-08-23", 702))

    def test_a_leak_is_named_with_its_dates(self):
        block = qy.build_block(self.BY, "2026-08-23", 702,
                               late={"n": 186, "days": {"2026-08-14": 186}})
        self.assertIn("186 个不是历史遗留", block)
        self.assertIn("2026-08-14 漏 186 个", block)

    def test_it_says_why_it_matters(self):
        block = flat(qy.build_block(self.BY, "2026-08-23", 702,
                                    late={"n": 9, "days": {"2026-08-14": 9}}))
        self.assertRegex(block, r"这张表决定下一轮把抓取额度花在哪")

    def test_it_points_at_where_to_look(self):
        block = qy.build_block(self.BY, "2026-08-23", 702,
                               late={"n": 9, "days": {"2026-08-14": 9}})
        self.assertIn("job-scrape.md", block)

    def test_no_leak_means_no_extra_paragraph(self):
        """没有漏记时一个字都别多说 —— 否则每次都是噪音。"""
        block = qy.build_block(self.BY, "2026-08-23", 702,
                               late={"n": 0, "days": {}})
        self.assertNotIn("不是历史遗留", block)

    def test_no_missing_at_all_means_no_note(self):
        block = qy.build_block(self.BY, "2026-08-23", 0)
        self.assertNotIn("没有 `found_by`", block)

    def test_many_days_are_truncated_not_dumped(self):
        days = {f"2026-08-{d:02d}": 3 for d in range(1, 9)}
        block = qy.build_block(self.BY, "2026-08-23", 99,
                               late={"n": 24, "days": days})
        self.assertIn("…", block)
        self.assertNotIn("2026-08-08 漏", block)


class BothConsumersSayTheSameThing(unittest.TestCase):
    """写回块和终端各说一半的话，读报告的人和读文件的人会拿到两个版本。"""

    def test_the_terminal_line_no_longer_asserts_history(self):
        i = QY.index('print(f"有来源的 {have} 个')
        seg = QY[max(0, i - 400):i + 200]
        self.assertNotIn("后加的字段，早期抓的补不上", seg)

    def test_the_terminal_line_reports_the_leak(self):
        i = QY.index('print(f"有来源的 {have} 个')
        seg = QY[max(0, i - 500):i + 200]
        self.assertIn("个是漏记的", seg)

    def test_the_terminal_says_why_both(self):
        i = QY.index('print(f"有来源的 {have} 个')
        seg = flat(QY[max(0, i - 500):i].replace("#", " "))
        self.assertRegex(seg, r"两处都要说实话")

    def test_main_computes_it(self):
        self.assertIn("late_n, late_days = late_misses(seen)", QY)

    def test_the_write_back_path_passes_it(self):
        i = QY.index("write_back(target, build_block(")
        self.assertIn('late={"n": late_n', QY[i:i + 400])


class TheReasonIsRecorded(unittest.TestCase):
    def _doc(self) -> str:
        i = QY.index("def late_misses(")
        return flat(QY[i:QY.index("    days: dict = defaultdict", i)])

    def test_it_carries_the_per_day_measurement(self):
        seg = self._doc()
        self.assertRegex(seg, r"08-14 缺 186/186 = 100%")
        self.assertRegex(seg, r"08-12 缺 0/274 = 0%")
        self.assertIn("2026-08-23", seg)

    def test_it_names_the_error_class(self):
        self.assertRegex(self._doc(),
                         r"把「上游丢了数据」说成「核对过没问题」")

    def test_it_says_what_it_costs(self):
        seg = self._doc()
        self.assertRegex(seg, r"\*\*129 个是评过分能投的\*\*")
        self.assertRegex(seg, r"抓取额度往哪儿花")

    def test_it_records_the_first_boundary_being_wrong(self):
        """选界线是这条改动里最容易走错的一步 —— 走错过的那次要留下。"""
        seg = self._doc()
        # 措辞里补了完整日期（`test_measured_numbers_carry_their_date`
        # 那把棘轮要求每个实测数带日期），这里跟着放宽到只钉那个数。
        self.assertRegex(seg, r"那样取会报 649 个")
        self.assertRegex(seg, r"\*\*虚高 3.5 倍\*\*")

    def test_it_says_why_over_reporting_is_also_bad(self):
        self.assertRegex(self._doc(), r"报大了和报小了一样坏")


class TheSignalItLeansOnIsReal(unittest.TestCase):
    """有语料时验一次：那条界线真的存在，界线之后真的还有缺口。"""

    def _seen(self):
        p = ROOT / ".active_user"
        if not p.is_file():
            self.skipTest("没有活动用户")
        u = p.read_text(encoding="utf-8").strip()
        f = ROOT / "users" / u / "job_scraper" / "seen_jobs.json"
        if not f.is_file():
            self.skipTest("没有职位库")
        seen = json.loads(f.read_text(encoding="utf-8"))["seen"]
        if len(seen) < 500:
            self.skipTest("语料太小")
        return seen

    def test_the_field_is_in_use_at_all(self):
        seen = self._seen()
        have = sum(1 for v in seen.values()
                   if isinstance(v, dict) and (v.get("found_by") or "").strip())
        self.assertGreater(have, len(seen) // 2,
                           f"只有 {have}/{len(seen)} 记了来源 —— 这张表本身就不可信了")

    def test_the_leak_count_is_far_below_the_naive_one(self):
        """朴素界线报 649、正确界线报 186。差得不多就说明这次收紧没起作用。"""
        seen = self._seen()
        n, _ = qy.late_misses(seen)
        naive = sum(1 for v in seen.values()
                    if isinstance(v, dict)
                    and not (v.get("found_by") or "").strip())
        if naive == 0:
            self.skipTest("已经一个都不缺了")
        self.assertLess(n, naive,
                        "收紧后的漏记数没有比「所有没来源的」少 —— 界线没生效")


if __name__ == "__main__":
    unittest.main()
