# -*- coding: utf-8 -*-
"""那句话写着「短期内」，而它数的是**有史以来**。

面板在他决定投不投的地方印这句：

    这家你已经投过 5 个岗。同一家短期内连投几个，
    对面在一个系统里看到的是同一个人在刷屏。

数它的是 `collections.Counter` —— **没有任何时间维度**。实测 2026-08-24：
他 85 条投递全落在 3~14 天内，一条都没出窗口，所以那句话**碰巧**是对的。
三个月后同一份台账、同一段代码，会对着去年的投递印出同一句「在刷屏」。

这是这个仓库刚点过名的那一类（`batch_note`：「全库累计数只会随产量涨，
回答不了规则生效了没有」）—— 只是这一次，累计数还被一句带时间状语的话
背书了。

## 为什么窗口内外不是「说不说」，是「说什么」

    窗口内   连投多个 = 对面一个后台里看到同一个人在刷屏
    窗口外   隔得够久，重投不算刷屏 —— 但**话术里提「上次投过贵司」**
             是国内常见失误：对面查得到，而你把「这次也没别的选择」写在脸上

撞单（同一家既走猎头报备、自己又直投）跨窗口都成立，一个岗也会发生，
所以它不设门槛 —— 但窗口外那句要换成另一半。

## 句子在 Python 拼，不在 TSX 拼

`SAME_COMPANY_DAYS` 只许有一份。在 TSX 里再写一次 `>= 90` 就是第二份，
而这个仓库为「同一个概念两个数」立过专门的判据
（`tests/test_one_number_per_concept.py`）。同文件那条老注释说的是同一件事：
「TS 侧不另写一套状态机 —— 两份状态机迟早会分叉，
而分叉的样子是：页面画出一个按钮，服务端拒绝它」。

## 90 从哪来

国内几家大厂 ATS 简历保护期 / 锁定期常见 3~6 个月，取**下限** ——
宁可少喊一次，也别在窗口外喊。真正让这个数不必被信任的是
**把日期印出来**：他自己看得见「11 天前」还是「去年」。

## 这份文件只守「时钟」那一半

这条提醒**存不存在、算在什么时候、公司怎么归并**归
`tests/test_the_same_company_warning_comes_before_sending.py` ——
那份是这个字段的正本守卫，比这份早。两份别互相抄断言。
"""
import json
import pathlib
import re
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tests"))
from _live import user_or_skip  # noqa: E402
import export_web_data as ex  # noqa: E402

EX = (ROOT / "tools" / "export_web_data.py").read_text(encoding="utf-8")
JR = (ROOT / "web" / "src" / "components"
      / "JobReadout.tsx").read_text(encoding="utf-8")
TYPES = (ROOT / "web" / "src" / "types.ts").read_text(encoding="utf-8")


def flat(s: str) -> str:
    s = " ".join(re.sub(r"^\s*(?:>|#:?|//:?|\*)\s?", "", s, flags=re.M).split())
    return re.sub(r"(?<=[一-鿿，。；：、（）「」])"
                  r" +(?=[一-鿿，。；：、（）「」])", "", s)


class TheSentenceKnowsWhatTimeItIs(unittest.TestCase):
    def test_it_prints_the_date(self):
        """**这是整条的支点。** 有了日期，他不必替那个 90 背书。"""
        self.assertIn("最近一次是 11 天前", ex.same_company_note(3, 11))

    def test_inside_the_window_it_says_spamming(self):
        self.assertIn("在刷屏", ex.same_company_note(5, 11))

    def test_outside_the_window_it_does_not(self):
        """去年投的 5 个岗不是「在刷屏」。"""
        got = ex.same_company_note(5, 200)
        self.assertNotIn("刷屏，", got)
        self.assertIn("重投不算刷屏", got)

    def test_outside_the_window_it_says_the_other_half(self):
        """窗口外不是「没事」，是另一件事。"""
        self.assertIn("话术里别提上次投过", ex.same_company_note(5, 200))

    def test_the_boundary_is_inclusive(self):
        n = ex.SAME_COMPANY_DAYS
        self.assertIn("在刷屏", ex.same_company_note(2, n))
        self.assertNotIn("在刷屏", ex.same_company_note(2, n + 1))

    def test_one_job_is_not_spamming(self):
        """投过一个岗不是「连投几个」—— 误报一次这条就会被整条忽略。"""
        self.assertNotIn("在刷屏", ex.same_company_note(1, 3))

    def test_but_one_job_still_warns_about_the_double_submit(self):
        """撞单一个岗也会发生，所以它不设门槛。"""
        self.assertIn("撞成重复候选人", ex.same_company_note(1, 3))

    def test_an_unreadable_date_does_not_silently_drop_the_warning(self):
        """台账是人手填的。日期读不出来时**宁可按窗口内说** —— 少说一次撞单
        的代价是两条流程一起卡住，比多说一次大得多。"""
        got = ex.same_company_note(2, None)
        self.assertIn("撞成重复候选人", got)
        self.assertNotIn("天前", got, "日期都没有，不许编一个出来")
        self.assertNotIn("在刷屏", got, "不知道多久以前，就别断言他在刷屏")

    def test_zero_says_nothing(self):
        self.assertEqual(ex.same_company_note(0, 3), "")
        self.assertEqual(ex.same_company_note(0, None), "")

    def test_no_markdown_reaches_the_panel(self):
        for args in ((5, 11), (5, 200), (1, None)):
            with self.subTest(args=args):
                got = ex.same_company_note(*args)
                self.assertNotIn("**", got)
                self.assertNotIn(chr(96), got)

    def test_no_framework_jargon(self):
        got = ex.same_company_note(5, 11) + ex.same_company_note(5, 200)
        for w in ("硬门", "四维", "判词", "台账", "短名单", "读数"):
            with self.subTest(w=w):
                self.assertNotIn(w, got)


class TheNumberHasExactlyOneHome(unittest.TestCase):
    def test_the_constant_exists(self):
        self.assertIsInstance(ex.SAME_COMPANY_DAYS, int)

    def test_the_panel_does_not_keep_a_second_copy(self):
        """在 TSX 里再写一次 `>= 90` 就是第二份，两份迟早分叉。"""
        self.assertNotRegex(JR, r"sameCompany\w*\s*[<>]=?\s*\d")

    def test_the_panel_only_renders(self):
        self.assertIn("{job.sameCompanyWarn}", JR)

    def test_the_panel_builds_no_sentence_of_its_own(self):
        i = JR.index("{job.sameCompanyWarn}")
        self.assertNotIn("在刷屏", JR[i - 200:i + 200], "句子回到 TSX 里了")

    def test_the_old_counter_field_is_gone(self):
        """留着旧字段名，两条链子会同时存在而只有一条被渲染。"""
        for f in ("tools/export_web_data.py", "web/src/types.ts",
                  "web/src/components/JobReadout.tsx"):
            with self.subTest(f=f):
                self.assertNotIn("sentSameCompany",
                                 (ROOT / f).read_text(encoding="utf-8"))

    def test_the_reason_is_recorded_on_the_constant(self):
        i = EX.index("SAME_COMPANY_DAYS = ")
        seg = flat(EX[max(0, i - 1400):i])
        self.assertRegex(seg, r"别让措辞跑在数字前面")
        self.assertRegex(seg, r"碰巧")
        self.assertIn("2026-08-24", seg)
        self.assertRegex(seg, r"3~6 个月）的\*\*下限\*\*")
        # 实测那两个数是这一条全部的分量 —— 「碰巧对」不写出来就只是个断言
        self.assertRegex(seg, r"85 条投递全落在 3~14 天内")
        self.assertRegex(seg, r"一条都没出窗口")

    def test_it_says_why_the_date_matters_more_than_the_number(self):
        i = EX.index("SAME_COMPANY_DAYS = ")
        seg = flat(EX[max(0, i - 1400):i])
        self.assertRegex(seg, r"不用替我的 90 背书")


class TheDatesActuallyGetCollected(unittest.TestCase):
    def test_the_exporter_keeps_dates_not_just_a_count(self):
        # 锚在声明那一行，不是裸「_sent_at」（它在这个文件里有三处，
        # `index()` 会取到注释里的那一处 —— `test_test_anchors_are_unambiguous` 拦过）
        i = EX.index("_sent_at: dict[str, list[str]]")
        seg = EX[i:EX.index("_now = _dt.date.today()", i)]
        self.assertNotIn("collections.Counter", seg,
                         "又退回只计数了 —— 那就说不出「短期内」是真是假")
        self.assertIn('_a.get("date")', seg)

    def test_it_parses_dates_through_the_canonical_helper(self):
        """台账是人手填的，正本 `_days_since` 认四种写法。"""
        i = EX.index("_note = same_company_note(")
        self.assertIn("_days_since(", EX[max(0, i - 400):i])

    def test_it_reports_the_most_recent_one(self):
        """投过 5 个岗、最早那个在去年 —— 要紧的是**最近**那次。"""
        i = EX.index("_note = same_company_note(")
        self.assertIn("min(_ago)", EX[i:i + 200])


class TheTypeSaysWhereTheSentenceIsBuilt(unittest.TestCase):
    def test_it_is_a_string_now(self):
        self.assertIn("sameCompanyWarn?: string;", TYPES)

    def test_it_points_at_the_builder(self):
        i = TYPES.index("sameCompanyWarn?: string;")
        seg = flat(TYPES[max(0, i - 900):i])
        self.assertIn("same_company_note", seg)
        self.assertRegex(seg, r"窗口内外说的话不一样")


class TheDrafterCanActuallyReadIt(unittest.TestCase):
    """**上游写了、下游读不到** —— 这个仓库排第一的缺陷形状。

    面板在他按下「复制开场白」那一刻说这句话，可写那段开场白的是
    `/job-apply`，而它此前对这件事一无所知：全文搜「同一家 / 重复投 /
    撞单 / 报备」，只搜得到「同一个岗的多个挂法」和内推那条
    「同一家公司只找一个人」—— 都不是这件事。

    接口用的是**第 0 步已经打开的那份 `data.json`**，不新加一次查表：
    `isHeadhunter` 就在隔壁一步（1.5b）以同样的方式取，1.5c 是它的同族。
    """

    APPLY = (ROOT / "workflows" / "job-apply.md").read_text(encoding="utf-8")

    def _seg(self) -> str:
        i = self.APPLY.index("### 1.5c 这家你之前投过没有")
        return flat(self.APPLY[i:self.APPLY.index("## 第 1.6 步", i)])

    def test_the_step_exists(self):
        self.assertIn("### 1.5c 这家你之前投过没有", self.APPLY)

    def test_it_reads_the_field_the_exporter_writes(self):
        """字段名对不上，这一步就是写给空气看的。"""
        self.assertIn("sameCompanyWarn", self._seg())

    def test_it_sits_next_to_the_sibling_lookup(self):
        """`isHeadhunter` 在 1.5b 以同样方式取 —— 同一份快照，不新加查表。"""
        a = self.APPLY.index("### 1.5b 对话方是谁")
        b = self.APPLY.index("### 1.5c 这家你之前投过没有")
        self.assertLess(a, b)
        self.assertLess(b, self.APPLY.index("## 第 1.6 步"))

    def test_it_forbids_both_halves(self):
        """**两头都不许碰**，只说一头等于把人推到另一头。"""
        seg = self._seg()
        self.assertRegex(seg, r"不许写成第一次接触")
        self.assertRegex(seg, r"也不许主动交代")

    def test_it_says_what_to_write_instead(self):
        """只给禁令，执行者还是得写点什么 —— 要给他那条路。"""
        seg = self._seg()
        self.assertRegex(seg, r"比平常更针对这个岗")
        self.assertRegex(seg, r"为什么是这个岗")

    def test_it_says_why_each_half_is_wrong(self):
        seg = self._seg()
        self.assertRegex(seg, r"后台里看得见你上几条投递记录")
        self.assertRegex(seg, r"把「海投」这个结论现成递过去")

    def test_the_headhunter_case_gets_its_extra_step(self):
        seg = self._seg()
        self.assertRegex(seg, r"先确认这家没被别的\s*顾问报备过你")
        self.assertRegex(seg, r"撞成重复候选人")

    def test_the_out_of_window_case_is_not_a_loophole(self):
        """**字段自己会说「重投不算刷屏」** —— 执行者会顺着那句话放行。"""
        seg = self._seg()
        self.assertRegex(seg, r"那也不等于可以提上次")
        self.assertRegex(seg, r"隔多久都一样")

    def test_it_scopes_the_consequence_to_one_channel(self):
        """渠道 2/3 是网申自评框，那里没有「第一次接触」这回事。"""
        self.assertRegex(self._seg(), r"只落在\*\*渠道 1")

    def test_no_field_means_skip(self):
        """没投过这家的岗占绝大多数 —— 不写这句，每个岗都要多想一遍。"""
        self.assertRegex(self._seg(), r"没有这个字段就跳过整节")

class TheSignalItLeansOnIsReal(unittest.TestCase):
    """现算：这批数据里真的有同一家投过多个的，而日期真的解析得出来。"""

    def _live(self):
        p = ROOT / "web" / "public" / "data.json"
        if not p.is_file():
            self.skipTest("还没导出过面板数据")
        return json.loads(p.read_text(encoding="utf-8"))["jobs"]

    def test_some_jobs_carry_it(self):
        user_or_skip()   # 没有真实数据可读时 skip（见 tests/_live.py）
        n = sum(1 for j in self._live() if j.get("sameCompanyWarn"))
        self.assertGreater(n, 0, "一个都没有 —— 要么他还没投过，要么这条链子断了")

    def test_the_dates_parse(self):
        """**「最近一次是 N 天前」印不出来，这一整条就退回原样。**

        台账里的日期读不出来时函数会静默省掉那半句 —— 那正是它此前的样子。
        """
        jobs = [j for j in self._live() if j.get("sameCompanyWarn")]
        if len(jobs) < 10:
            self.skipTest("样本太少")
        n = sum(1 for j in jobs if "天前" in j["sameCompanyWarn"])
        self.assertGreaterEqual(
            n, len(jobs) * 0.9,
            f"{len(jobs) - n}/{len(jobs)} 条读不出投递日期 —— "
            f"去看台账那一列是不是被 Excel 改成别的写法了")

    def test_no_warning_claims_an_absurd_count(self):
        """现算兜底：裸比的样子是一个岗印出「投过 100 多个岗」。

        判据不写死一个数 —— 拿**他真实的最大同公司投递数**当上界，
        脱敏串一旦被并进来，那个数会一步跳到几十上百。
        """
        import csv
        import collections
        p = ROOT / ".active_user"
        if not p.is_file():
            self.skipTest("没有活动用户")
        f = (ROOT / "users" / p.read_text(encoding="utf-8").strip()
             / "job_search_tracker.csv")
        if not f.is_file():
            self.skipTest("还没有投递记录")
        rows = list(csv.DictReader(f.open(encoding="utf-8-sig")))
        c = collections.Counter((r.get("company") or "").strip() for r in rows)
        c.pop("", None)
        top = max(c.values()) if c else 0
        for j in self._live():
            w = j.get("sameCompanyWarn")
            if not w:
                continue
            m = re.search(r"投过 (\d+) 个岗", w)
            self.assertLessEqual(
                int(m.group(1)), top,
                f"这条说的比他对任何一家的投递数都多，公司多半被并错了：{w}")

    def test_the_wording_matches_the_data(self):
        """**这条是这一轮的由来。** 今天全部落在窗口内，所以全都该说「刷屏」；
        哪天有一条说「重投不算刷屏」，说明窗口那一半开始真的生效了。"""
        jobs = [j for j in self._live() if j.get("sameCompanyWarn")]
        if not jobs:
            self.skipTest("还没有")
        multi = [j for j in jobs
                 if re.search(r"投过 [2-9]\d* 个岗", j["sameCompanyWarn"])]
        if not multi:
            self.skipTest("没有同一家投过 2 个以上的")
        self.assertTrue(
            any("在刷屏" in j["sameCompanyWarn"]
                or "重投不算刷屏" in j["sameCompanyWarn"] for j in multi),
            "两半都没说 —— 窗口判断没跑起来")


if __name__ == "__main__":
    unittest.main()
