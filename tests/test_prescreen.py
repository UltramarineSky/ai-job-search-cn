"""预筛的淘汰规则：宁可放过，不可误杀。

## 为什么每条都值得钉住

预筛是**不抓 JD 就结案**，被它否掉的岗不会再进流水线。所以它的错误是**静默**的：
一个本该投的岗从此消失，用户不会知道。这条不对称决定了所有规则的方向——
放过的代价是多抓一次 JD，误杀的代价是丢掉一个机会。

实测踩过的三个坑，每个都对应下面一组测试：

1. **薪数只在原始串里。** CDP 三家不填 `salaryMonths`，`30-40K·15薪` 的 15 只存在于
   `salary` 串中。第一版自己写了个折算、只读字段，把这个岗按 12 薪算成 36 万判出局
   ——按 15 薪是 45 万，够得着底线。**183 个岗里这样误杀了 44 个。**
   修法不是补一个正则，是**复用 `export_web_data.annual_package`**——它早就处理了，
   注释里连「实测低估 30-50%」都写着。同一件事只留一个实现。
2. **拿区间下沿比底线。** `40-70k` 的下沿 48 万够不着 50 万底线，但上沿 84 万显然够。
   淘汰要看**上沿**：连开到顶都够不着，才叫「明显偏低」。
3. **拿假设值淘汰。** 薪数未知时页面按 12 薪保守显示（不虚报），但淘汰要按最乐观的
   薪数估（不误杀）——同一个数字，两种用途，两个方向的保守。
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import prescreen as ps  # noqa: E402


def entry(**kw) -> dict:
    base = {"title": "某岗", "company": "某公司", "url": "https://x/1",
            "status": "new", "first_seen": "2026-07-01"}
    base.update(kw)
    return base


class SalaryMonthsComeFromTheStringToo(unittest.TestCase):
    """薪数优先从 `salary` 串里取——CDP 三家根本不填 `salaryMonths` 字段。"""

    def test_months_in_the_string_are_honoured(self):
        e = entry(salary="30-40K·15薪", salaryMonths=None)
        high, assumed = ps.annual_high_wan(e)
        self.assertAlmostEqual(high, 60.0, places=0,
                               msg="40k × 15薪 = 60 万；只读字段会算成 48 万")
        self.assertFalse(assumed, "串里写了 15薪，不该算作「未标薪数」")

    def test_the_real_case_that_was_wrongly_eliminated(self):
        """实测误杀的那个：按 12 薪 36 万出局，按串里的 15 薪 45 万应留下。"""
        e = entry(salary="30-40K·15薪", salaryMonths=None)
        self.assertIsNone(ps.rule_annual(e, 42.0),
                          "串里有 15薪，年包 60 万，不该被 42 万的底线淘汰")

    def test_field_is_used_when_the_string_has_no_months(self):
        e = entry(salary="30-40k", salaryMonths=14)
        high, _ = ps.annual_high_wan(e)
        self.assertAlmostEqual(high, 56.0, places=0)


class ComparesTheHighEnd(unittest.TestCase):
    def test_wide_range_whose_top_clears_the_floor_survives(self):
        e = entry(salary="40-70k", salaryMonths=12)
        self.assertIsNone(ps.rule_annual(e, 50.0),
                          "上沿 84 万够得着 50 万底线，不该因为下沿 48 万被淘汰")

    def test_range_entirely_below_the_floor_is_eliminated(self):
        e = entry(salary="1.5-2万", salaryMonths=12)
        why = ps.rule_annual(e, 42.0)
        self.assertIsNotNone(why)
        self.assertIn("低于底线", why)


class UnknownMonthsAreEstimatedOptimistically(unittest.TestCase):
    """薪数未知时按最乐观的薪数估，够得着就放过。"""

    def test_borderline_case_survives_on_the_optimistic_estimate(self):
        # 3 万/月：12 薪 = 36 万（会被 42 万淘汰），16 薪 = 48 万（够得着）
        e = entry(salary="1.5-3万", salaryMonths=None)
        self.assertIsNone(
            ps.rule_annual(e, 42.0),
            "薪数未知时该按最乐观的薪数估，这个岗有可能是够的，不该静默淘汰")

    def test_hopeless_case_is_still_eliminated(self):
        e = entry(salary="1.5-2万", salaryMonths=None)
        why = ps.rule_annual(e, 42.0)
        self.assertIsNotNone(why, "2 万 × 16 薪 = 32 万，怎么算都不够")
        self.assertIn("最乐观", why, "用了假设值就要在依据里说出来")

    def test_unparseable_salary_never_eliminates(self):
        """认不出口径就别猜——留给 /job-rank 抓 JD 去判。"""
        for s in ("", "面议", "薪资面谈"):
            self.assertIsNone(ps.rule_annual(entry(salary=s), 42.0),
                              f"「{s}」不该参与淘汰")


class EducationLadder(unittest.TestCase):
    def test_strictly_higher_requirement_is_eliminated(self):
        why = ps.rule_edu(entry(eduLevel="硕士"), "本科")
        self.assertIsNotNone(why)
        self.assertIn("硕士", why)

    def test_same_level_is_not_eliminated(self):
        """「统招本科」与「本科」同级：是不是「统招」有歧义，属于判断不属于机械匹配。"""
        for need in ("本科", "统招本科"):
            self.assertIsNone(ps.rule_edu(entry(eduLevel=need), "本科"),
                              f"{need} 与本科同级，不该淘汰")

    def test_lower_or_unlimited_is_not_eliminated(self):
        for need in ("大专", "学历不限", ""):
            self.assertIsNone(ps.rule_edu(entry(eduLevel=need), "本科"))

    def test_unrecognised_wording_never_eliminates(self):
        self.assertIsNone(ps.rule_edu(entry(eduLevel="见岗位描述"), "本科"))


class OffTrackIsNotAHardGate(unittest.TestCase):
    def test_title_match_reports_which_word_hit(self):
        why = ps.rule_off_track(entry(title="算法工程师"), ["算法", "测试"])
        self.assertIsNotNone(why)
        self.assertIn("算法", why, "要说出是哪个词命中的，用户才能判断筛得对不对")

    def test_no_match_returns_none(self):
        self.assertIsNone(ps.rule_off_track(entry(title="AI产品经理"), ["算法"]))


class WritesOnlyWhatItShould(unittest.TestCase):
    def _repo(self, entries):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(tmp, ignore_errors=True))
        u = tmp / "users" / "张三" / "job_scraper"
        u.mkdir(parents=True)
        (tmp / ".active_user").write_text("张三", encoding="utf-8")
        (u / "seen_jobs.json").write_text(
            json.dumps({"seen": entries}, ensure_ascii=False), encoding="utf-8")
        self._saved = ps.ROOT
        ps.ROOT = tmp
        self.addCleanup(lambda: setattr(ps, "ROOT", self._saved))
        return tmp, u / "seen_jobs.json"

    def test_dry_run_writes_nothing(self):
        _, sj = self._repo({"a": entry(salary="1.5-2万", salaryMonths=12)})
        before = sj.read_text(encoding="utf-8")
        ps.main(["--annual-floor", "42"])
        self.assertEqual(sj.read_text(encoding="utf-8"), before,
                         "不加 --apply 就绝不能写盘")

    def test_apply_records_the_reason(self):
        _, sj = self._repo({"a": entry(salary="1.5-2万", salaryMonths=12)})
        ps.main(["--annual-floor", "42", "--apply"])
        e = json.loads(sj.read_text(encoding="utf-8"))["seen"]["a"]
        self.assertEqual(e["status"], "ranked")
        self.assertIn("跳过", e["rank_verdict"])
        self.assertIn("低于底线", e["rank_breakdown"]["依据"])
        self.assertIn("未抓 JD", e["rank_breakdown"]["来源"],
                      "要写明这个判断没看过 JD —— 深度不同，用户有权知道")

    def test_never_touches_skipped_or_applied(self):
        """用户明确表过态的条目一律不碰（与 /job-rank Step 1.3 同一条规则）。"""
        _, sj = self._repo({
            "a": entry(salary="1.5-2万", salaryMonths=12, status="skipped",
                       skip_reason="我不想去"),
            "b": entry(salary="1.5-2万", salaryMonths=12, status="applied"),
            "c": entry(salary="1.5-2万", salaryMonths=12, status="ranked",
                       rank_score=61),
        })
        ps.main(["--annual-floor", "42", "--apply"])
        seen = json.loads(sj.read_text(encoding="utf-8"))["seen"]
        self.assertEqual(seen["a"]["status"], "skipped")
        self.assertEqual(seen["a"]["skip_reason"], "我不想去")
        self.assertEqual(seen["b"]["status"], "applied")
        self.assertEqual(seen["c"]["rank_score"], 61, "已评过的分数被覆盖了")

    def test_the_closing_reason_is_the_objective_one(self):
        """三条规则都命中时，**主依据只能是可复核的那一条**。

        原来这条叫 `test_first_matching_rule_wins`，断言学历胜出、写「硬门」。
        学历已经从「结案」降为「降权」——列表页 `eduLevel` 与 JD 正文实测 58% 对不上
        （数据见 `prescreen.py` 里 OBJECTIVE/INFERRED 那段），所以现在能结案的
        只剩薪资那一条算术。

        推断信号仍然要留档，但只能当**补充**接在主依据后面：事后要复核的是算术。
        """
        _, sj = self._repo({"a": entry(title="算法工程师", eduLevel="硕士",
                                       salary="1.5-2万", salaryMonths=12)})
        # --off-track 现在必须带 --protect（见 test_prescreen_guards.py：
        # 少了它，「智能体开发产品经理」会死于标题含「开发」）。
        ps.main(["--edu-floor", "本科", "--off-track", "算法",
                 "--protect", "产品经理",
                 "--annual-floor", "42", "--apply"])
        e = json.loads(sj.read_text(encoding="utf-8"))["seen"]["a"]
        why = e["rank_breakdown"]["依据"]
        self.assertNotIn("硬门", e["rank_verdict"],
                         "学历又拿回了结案权 —— 它只是个列表页字段")
        self.assertTrue(why.startswith("年包上沿"),
                        f"主依据不是薪资算术：{why!r}")
        self.assertIn("另有推断信号", why, "推断信号没留档")


class TerminalOutputSaysItInChinese(unittest.TestCase):
    """预筛印给用户看的判词与依据，不许带内部词或英文码。

    存盘的 `rank_verdict` 是 `硬门 FAIL (学历院校)`——那是**数据格式**，
    `build_dashboard`、`export_web_data`、`serve.py` 都按它匹配，不能改。
    但它**印到终端**之前必须过 `export_web_data.plain()`，那正是 `plain()` 存在的理由。

    实测漏过：终端上直接印着

        硬门 FAIL (学历院校)  1 个
        [硬门 FAIL (学历院校)] 高级产品经理   …… 硬门「学历院校」一票否决

    内部词加英文码一起上屏，正是 `AGENTS.md`「给用户看的措辞」点名禁掉的两样。

    ## 为什么现有守卫看不见它

    `test_display_wording.OneThingKeepsOneNameOnScreen` 扫的是 `print()` 的
    **字面量实参**。这里的词来自变量（`v`、`why` 从规则表里取），源码里根本没有
    那几个字——**扫源码扫不出来**。所以这条真跑一遍，看它到底印了什么。
    """

    def _run(self, *argv) -> tuple[str, dict]:
        """在临时用户目录里跑一次预筛，返回 (终端输出, 写盘后的条目)。"""
        import contextlib
        import io as _io
        d = Path(tempfile.mkdtemp())
        (d / "users" / "测试" / "job_scraper").mkdir(parents=True)
        (d / ".active_user").write_text("测试", encoding="utf-8")
        f = d / "users" / "测试" / "job_scraper" / "seen_jobs.json"
        f.write_text(json.dumps({"seen": {"k1": {
            "title": "高级产品经理", "company": "甲", "status": "new",
            "eduLevel": "硕士", "salary": "30-40k·15薪"}}},
            ensure_ascii=False), encoding="utf-8")
        old_root, old_cli = ps.ROOT, ps._cli.ROOT
        ps.ROOT = ps._cli.ROOT = d
        try:
            buf = _io.StringIO()
            with contextlib.redirect_stdout(buf):
                ps.main([*argv, "--user", "测试"])
            entry = json.loads(f.read_text(encoding="utf-8"))["seen"]["k1"]
            return buf.getvalue(), entry
        finally:
            ps.ROOT, ps._cli.ROOT = old_root, old_cli

    def test_it_really_eliminates_the_job(self):
        """控制用例：这个岗确实被判出局了，否则下面几条没有判词可看。

        用薪资而不是学历：学历已经不结案了，拿它做控制用例的话，下面那几条
        会在一个空输出上全绿——正是本文件开头说的那种静默空转。
        """
        out, _ = self._run("--annual-floor", "80")
        self.assertIn("结案 1 个", out, f"没淘汰？输出是：{out}")

    def test_education_alone_only_parks_it(self):
        """学历字段单独命中：排到队尾，不结案、不写判词。"""
        out, e = self._run("--edu-floor", "本科", "--apply")
        self.assertIn("先放一边 1 个", out, f"学历把岗结案了：{out}")
        self.assertEqual(e["status"], "new", "降权不该改 status")
        self.assertNotIn("rank_verdict", e, "降权不该写判词")
        self.assertTrue(e.get("deprioritized"), "没留下降权标记")

    def test_no_internal_words_on_the_terminal(self):
        out, _ = self._run("--annual-floor", "80")
        for w in ("硬门", "FAIL"):
            with self.subTest(word=w):
                self.assertNotIn(
                    w, out,
                    f"终端输出里有「{w}」：\n{out}\n"
                    "存盘保持内部形态是对的，但印出来之前要过 "
                    "`export_web_data.plain()`。")

    def test_the_stored_value_stays_internal(self):
        """反向：别为了好看把**存盘值**也改了——别的工具按它匹配。

        原来钉的是 `硬门 FAIL` 前缀，而那个判词只有学历规则会写。学历降为降权之后，
        **预筛再也不产出硬门判词**——这是好事：一个没读过 JD 的规则不该发一票否决。
        剩下的存盘形态是 `粗筛：跳过`，那个前缀同样是数据格式
        （`Shortlist.tsx` 的 `plainVerdict` 显示前才剥）。
        """
        _, entry = self._run("--annual-floor", "80", "--apply")
        self.assertTrue(
            (entry.get("rank_verdict") or "").startswith("粗筛："),
            f"存盘的判词被翻译过了：{entry.get('rank_verdict')!r}——"
            "`export_web_data` / `Shortlist.tsx` 都按 `粗筛：` 前缀处理，"
            "改了它们全失效。")
        self.assertIsNone(entry.get("rank_score"), "结案的岗不该有分数")


class HelpTextMatchesTheImplementation(unittest.TestCase):
    """`--help` 说的口径要和代码真做的一致。

    `prescreen.py` 顶上就记着同类旧账：「拿下沿比底线，却印成「上限」。
    显示与计算不一致，用户看不出哪里不对。」

    这次是反过来的一处：`--annual-floor` 的 help 写着「按薪资**下沿**保守折算」，
    而 `rule_annual` 走的是 `annual_high_wan`（**上沿**），它的 docstring 还专门
    论证过为什么必须用上沿——「拿下沿比会把 `40-70k` 这种上半段完全达标的岗一起扫掉」。

    用户按 help 理解去定这个数，定出来的门槛和实际判据差一整个区间宽度。
    而这条命令是**静默淘汰**职位的，看不出错。
    """

    def _help(self) -> str:
        import argparse
        import contextlib
        import io as _io
        buf = _io.StringIO()
        with contextlib.redirect_stdout(buf), self.assertRaises(SystemExit):
            ps.main(["--help"])
        return buf.getvalue()

    def test_help_is_printable(self):
        """控制用例：真拿到了 help 文本。"""
        self.assertIn("--annual-floor", self._help())

    def test_annual_floor_help_says_upper_bound(self):
        text = self._help()
        i = text.find("--annual-floor")
        seg = text[i:i + 400]
        self.assertIn(
            "上沿", seg,
            "`--annual-floor` 的 help 没说清是拿区间上沿比——"
            "而 `rule_annual` 用的正是 `annual_high_wan`（上沿）。")
        # 「拿下沿比会……」这种**解释为什么不用下沿**的句子要放行，
        # 只禁「按下沿折算」这类把它说成判据的说法。
        self.assertNotIn(
            "按薪资下沿", seg,
            "help 把判据说成了下沿，而实现用的是上沿——"
            "用户照它定出来的门槛会差一整个区间宽度，而淘汰是静默的。")

    def test_the_implementation_really_uses_the_high_end(self):
        """控制用例：实现确实取上沿，否则该改的是代码不是 help。"""
        import inspect
        src = inspect.getsource(ps.rule_annual)
        self.assertIn("annual_high_wan", src,
                      "rule_annual 不再用上沿了——那 help 和本测试都要跟着改")


if __name__ == "__main__":
    unittest.main()
