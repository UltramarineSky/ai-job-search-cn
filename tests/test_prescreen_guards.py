"""预筛的两道闸：不许按领域词误杀目标职能，淘汰了也必须能撤回。

## 为什么要有这个测试

中文岗位名把**职能放在尾部**、领域放在前面：`采购经理` 的职能是采购，
`智能体开发产品经理` 的职能是产品经理、领域才是智能体开发。而 `--off-track` 是整个
标题的子串匹配，看不出位置——于是「开发」把 `智能体开发产品经理` 当成了开发岗。

实测代价（都是真实数据，`/job-rank` 的某一轮用 `算法,工程,标注,测试,销售` 跑出来的）：

    智能体开发产品经理        80-100k·16薪   年包 128-160 万   死于「开发」
    智能体开发产品经理        50-80k·17薪    年包  85-136 万   死于「开发」
    AI智能体开发产品经理      40-50k·20薪    年包  80-100 万   死于「开发」
    AI大模型产品经理（算法平台）  <某大厂>                     死于「算法」

一共 9 个，**JD 一个字都没读过**。作为对比，深评 82 分的那个岗是年包 64-96 万——
被误杀的这批里最贵的是它的两倍，而「智能体开发产品经理」几乎是这份数据里跟候选人
履历最对口的标题。

`rank.md` 早就写着「`--off-track` 要格外克制：`AI产品经理（算法方向）` 含「算法」
但未必不合适」——**散文告诫拦不住**，所以改成机制：给了 `--off-track` 就必须给
`--protect`，否则直接拒绝执行。

第二道闸是撤销。规则的结论来自一份当场传进来的词表，那正是最容易给错的东西；
可原来只有用户手点的「不投」能放回，规则杀掉的 103 个（占全部 38%）在界面上
没有任何回头路。谁下的结论谁最可能错，就更要留撤销口。
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import prescreen as ps  # noqa: E402
import serve as srv  # noqa: E402

PROTECT = ["产品经理", "产品负责人", "产品专家"]
OFF = ["开发", "算法", "测试", "销售", "采购", "研发专家"]


class DomainWordsMustNotKillTheTargetRole(unittest.TestCase):
    """标题里写着目标职能的，off-track 一律不许杀。"""

    SHOULD_SURVIVE = [
        "智能体开发产品经理",              # 领域=智能体开发，职能=产品经理
        "AI智能体开发产品经理",
        "AI大模型产品经理（算法平台）-Data XX",
        "认证测试产品经理 (MJ000000)",
        "智能盒+算法平台解决方案产品经理",
        "Agent算法（多模态大模型/产品经理）",   # 含糊 → 拿不准就别判死，留到读 JD
        "销售赋能产品经理",
    ]
    SHOULD_DIE = [
        "电控产品采购经理",                # 职能=采购
        "智能体研发专家",                  # 没有目标职能词
        "算法工程师",
        "大客户销售总监",
    ]

    def test_target_role_in_title_is_protected(self):
        for t in self.SHOULD_SURVIVE:
            with self.subTest(title=t):
                self.assertIsNone(
                    ps.rule_off_track({"title": t}, OFF, PROTECT),
                    f"「{t}」的职能就是产品经理，不该按领域词判成另一条职能线")

    def test_real_off_track_still_dies(self):
        """保护不能宽到把规则废掉。"""
        for t in self.SHOULD_DIE:
            with self.subTest(title=t):
                self.assertIsNotNone(
                    ps.rule_off_track({"title": t}, OFF, PROTECT),
                    f"「{t}」确实是另一条职能线，该淘汰")

    def test_without_protect_the_bug_reproduces(self):
        """钉住因果：不给保护词，误杀立刻重现 —— 这就是当初发生的事。"""
        self.assertIsNotNone(
            ps.rule_off_track({"title": "智能体开发产品经理"}, OFF, []),
            "没有保护词时本该误杀（这条在描述 bug 本身，不是要它不发生）")


class OffTrackRefusesToRunUnguarded(unittest.TestCase):
    """散文告诫换成机制：只给淘汰词不给保护词，直接拒绝执行。"""

    def _fixture(self, tmp: Path):
        u = tmp / "users" / "张三" / "job_scraper"
        u.mkdir(parents=True)
        (tmp / ".active_user").write_text("张三", encoding="utf-8")
        (u / "seen_jobs.json").write_text(json.dumps({"seen": {
            "u1#智能体开发产品经理": {
                "title": "智能体开发产品经理", "url": "u1",
                "company": "某公司", "status": "new", "salary": "80-100k",
            },
        }}, ensure_ascii=False), encoding="utf-8")
        return tmp

    def test_off_track_without_protect_exits_nonzero(self):
        with tempfile.TemporaryDirectory() as td:
            saved = ps.ROOT
            try:
                ps.ROOT = self._fixture(Path(td))
                code = ps.main(["--off-track", "开发", "--user", "张三"])
            finally:
                ps.ROOT = saved
        self.assertEqual(code, 2, "只给 --off-track 不给 --protect 竟然放行了")

    def test_with_protect_it_runs_and_spares_the_job(self):
        with tempfile.TemporaryDirectory() as td:
            saved = ps.ROOT
            try:
                tmp = self._fixture(Path(td))
                ps.ROOT = tmp
                code = ps.main(["--off-track", "开发", "--protect", "产品经理",
                                "--user", "张三", "--apply"])
                seen = json.loads((tmp / "users/张三/job_scraper/seen_jobs.json")
                                  .read_text(encoding="utf-8"))["seen"]
            finally:
                ps.ROOT = saved
        self.assertEqual(code, 0)
        self.assertEqual(list(seen.values())[0]["status"], "new",
                         "有保护词还是被淘汰了")


class RuleEliminationIsRecordedAndReversible(unittest.TestCase):

    def _seen(self, tmp: Path, entry: dict):
        u = tmp / "users" / "张三" / "job_scraper"
        u.mkdir(parents=True)
        (tmp / ".active_user").write_text("张三", encoding="utf-8")
        (u / "seen_jobs.json").write_text(
            json.dumps({"seen": {"u1#岗": entry}}, ensure_ascii=False),
            encoding="utf-8")
        return u / "seen_jobs.json"

    def _run(self, entry: dict, argv: list[str]) -> dict:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            saved = ps.ROOT
            try:
                p = self._seen(tmp, entry)
                ps.ROOT = tmp
                ps.main(argv + ["--user", "张三", "--apply"])
                return json.loads(p.read_text(encoding="utf-8"))["seen"]["u1#岗"]
            finally:
                ps.ROOT = saved

    # 结案和降权**两种归宿都要记规则**。只记结案的那种，等于降权那批
    # （数量还更多）事后照样查不出是被哪份词表判的。

    def test_the_ruleset_is_recorded_when_a_case_is_closed(self):
        e = self._run({"title": "电控产品采购经理", "url": "u1", "company": "某公司",
                       "status": "new", "salary": "6-7k"},
                      ["--off-track", "采购", "--protect", "产品经理",
                       "--annual-floor", "42"])
        rs = (e.get("rank_breakdown") or {}).get("本轮规则") or {}
        self.assertEqual(rs.get("另一条职能线的词"), "采购",
                         "没记下这轮用的淘汰词 —— 事后无法复现也无法审计")
        self.assertEqual(rs.get("受保护的目标职能"), "产品经理")
        self.assertEqual(rs.get("年包底线万"), 42.0)

    def test_the_ruleset_is_recorded_when_a_job_is_only_parked(self):
        e = self._run({"title": "电控产品采购经理", "url": "u1", "company": "某公司",
                       "status": "new", "salary": "80-100k"},
                      ["--off-track", "采购", "--protect", "产品经理"])
        self.assertEqual(e["status"], "new", "只有标题依据不该结案")
        rs = (e.get("deprioritized") or {}).get("本轮规则") or {}
        self.assertEqual(rs.get("另一条职能线的词"), "采购",
                         "降权也要记规则 —— 数量比结案的还多，同样要能审计")

    def test_restoring_a_rule_elimination_clears_the_verdict(self):
        """只把 status 改回去是没用的：判词还在，它照样躺在不投的岗位里。"""
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            saved = srv.ROOT
            try:
                p = self._seen(tmp, {
                    "title": "岗", "url": "u1", "company": "某公司",
                    "status": "ranked", "rank_score": 20,
                    "rank_verdict": "粗筛：跳过", "rank_date": "2026-07-01",
                    "rank_breakdown": {"依据": "标题含「开发」", "来源": "预筛（未抓 JD）"},
                })
                srv.ROOT = tmp
                r = srv.apply_restore(srv.ex.stable_id("u1", "岗"))
                e = json.loads(p.read_text(encoding="utf-8"))["seen"]["u1#岗"]
            finally:
                srv.ROOT = saved
        self.assertTrue(r["ok"])
        self.assertEqual(e["status"], "new", "规则淘汰放回后应回到待评重走评估")
        self.assertNotIn("rank_verdict", e, "判词没撤 —— 放回等于没放")
        self.assertNotIn("rank_score", e)
        self.assertEqual(e["prev_verdict"]["判词"], "粗筛：跳过",
                         "撤掉的判词要留痕，不是删掉 —— 事后要能查当初为什么被杀")

    def test_restoring_a_manual_skip_keeps_the_score(self):
        """用户手点的不投是他自己的结论，分数与依据都还作数，只撤标记。"""
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            saved = srv.ROOT
            try:
                p = self._seen(tmp, {
                    "title": "岗", "url": "u1", "company": "某公司",
                    "status": "skipped", "skip_reason": "太远", "rank_score": 71,
                    "rank_verdict": "粗筛：值得投",
                })
                srv.ROOT = tmp
                srv.apply_restore(srv.ex.stable_id("u1", "岗"))
                e = json.loads(p.read_text(encoding="utf-8"))["seen"]["u1#岗"]
            finally:
                srv.ROOT = saved
        self.assertEqual(e["status"], "ranked")
        self.assertEqual(e["rank_score"], 71, "手点的不投不该把分数抹掉")
        self.assertNotIn("skip_reason", e)


class PipelineCountsFinishedWorkAsFinished(unittest.TestCase):
    """硬性条件没过的岗 `rank_score: null`，但它已经结案了，不是积压。"""

    # 调 `ex.n_processed` ——导出器用的就是它。在测试里自己重算一遍是假绿：
    # 改坏导出器那边的计法，测试照样通过（本会话已经栽过一次，见 parse_gates）。

    def test_gate_failed_jobs_count_as_processed(self):
        import export_web_data as ex
        n = ex.n_processed({
            "a#1": {"status": "ranked", "rank_score": 70},
            "b#2": {"status": "ranked", "rank_score": None,      # 硬性条件没过
                    "rank_verdict": "硬门 FAIL (学历院校)"},
            "c#3": {"status": "new"},                            # 真没处理
        })
        self.assertEqual(n, 2, "硬性条件没过的被算成了没处理 —— 队列显得比实际长")

    def test_new_and_expired_are_not_counted(self):
        import export_web_data as ex
        self.assertEqual(ex.n_processed({
            "a#1": {"status": "new"},
            "b#2": {"status": "expired"},
        }), 0, "没处理的和已过期的不该算进「打过分」")


if __name__ == "__main__":
    unittest.main()


class InferenceAloneCannotCloseACase(unittest.TestCase):
    """标题推断只能降权，要结案得有第二个**客观**证据。

    这是比 `--protect` 更根上的一条。`--protect` 拦的是「领域词误杀目标职能」这一种
    具体形态；这条拦的是形态本身——**标题这层证据不该有终局权**。

    因为同一份证据在 `/job-rank` 第 7b 步已经用于排序（「按标题与 focus/profile 的相关度
    排序，取前 M 去抓」），在那里它只决定抓取顺序、可逆、不下结论。7a 把它升格成判词，
    唯一多出来的作用是让「待评」的计数好看（`rank.md`：「只 defer 不淘汰的话队列永远
    排不空」）——那是记账问题，不该用判词解决。

    实测：53 个「另一条职能线」淘汰里 44 个只有标题一个依据，年包中位 88 万、
    17 个 ≥100 万，全部永久结案且错误静默。
    """

    def _run(self, entry: dict, argv: list[str]):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            u = tmp / "users" / "张三" / "job_scraper"
            u.mkdir(parents=True)
            (tmp / ".active_user").write_text("张三", encoding="utf-8")
            sj = u / "seen_jobs.json"
            sj.write_text(json.dumps({"seen": {"u1#岗": entry}}, ensure_ascii=False),
                          encoding="utf-8")
            saved = ps.ROOT
            try:
                ps.ROOT = tmp
                ps.main(argv + ["--user", "张三", "--apply"])
                return json.loads(sj.read_text(encoding="utf-8"))["seen"]["u1#岗"]
            finally:
                ps.ROOT = saved

    BASE = {"title": "算法工程师", "url": "u1", "company": "某公司", "status": "new"}

    def test_title_alone_parks_but_does_not_close(self):
        e = self._run({**self.BASE, "salary": "80-100k", "salaryMonths": 16},
                      ["--off-track", "算法", "--protect", "产品经理"])
        self.assertEqual(e["status"], "new", "只有标题一个依据就结案了 —— 标题判不了死刑")
        self.assertNotIn("rank_verdict", e, "降权不该写判词")
        self.assertTrue(e.get("deprioritized"), "没有留下降权标记，等于什么都没做")
        self.assertIn("算法", e["deprioritized"]["依据"])

    def test_title_plus_salary_closes_with_the_objective_reason(self):
        """两个证据齐了才结案，而且依据要以**可复核的那条**为准。"""
        e = self._run({**self.BASE, "salary": "1.5-2万", "salaryMonths": 12},
                      ["--off-track", "算法", "--protect", "产品经理",
                       "--annual-floor", "42"])
        self.assertEqual(e["status"], "ranked")
        self.assertIn("低于底线", e["rank_breakdown"]["依据"],
                      "结案依据该写薪资算术，不该只写标题猜测 —— 前者才能复核")
        self.assertIn("另有推断信号", e["rank_breakdown"]["依据"],
                      "第二个信号也要留档")
        self.assertIn("算法", e["rank_breakdown"]["依据"], "没说清第二个信号是什么")

    def test_two_inferred_signals_still_do_not_close(self):
        """标题 + 学历字段都命中，仍然只是降权。

        **两个不可靠的信号叠在一起不会变可靠。** 这条原来叫
        `test_title_plus_education_closes_as_a_hard_gate`，断言学历把它判成硬门——
        那时学历算「客观证据」。实测推翻了那个分类：列表页 `eduLevel` 与 JD 正文
        对不上的有 7/12（58%），其中一个年包 100-160 万的岗，正文白纸黑字写着
        「本科及以上」。算术没错，错的是输入，所以它归推断。

        能结案的只剩薪资那一条——这个岗 80-100k 够得着底线，于是不结案。
        """
        e = self._run({**self.BASE, "eduLevel": "硕士", "salary": "80-100k"},
                      ["--off-track", "算法", "--protect", "产品经理",
                       "--edu-floor", "本科"])
        self.assertEqual(e["status"], "new",
                         "两条推断把岗结案了 —— 谁都没读过 JD")
        self.assertNotIn("rank_verdict", e, "降权不该写判词")
        why = e["deprioritized"]["依据"]
        self.assertIn("算法", why, "标题那条信号没留档")
        self.assertIn("硕士", why, "学历那条信号没留档")
        self.assertNotIn("一票否决", why,
                         "降权的依据里写着一票否决 —— 复核的人会以为读过正文")

    def test_objective_rule_alone_still_closes(self):
        """降权机制不能把客观规则也一起削弱了。"""
        e = self._run({"title": "产品经理", "url": "u1", "company": "某公司",
                       "status": "new", "salary": "6-7k"},
                      ["--annual-floor", "42"])
        self.assertEqual(e["status"], "ranked")
        self.assertNotIn("deprioritized", e)


class ParkedJobsAreCountedAndQueuedLast(unittest.TestCase):

    def test_parked_are_counted_separately(self):
        import export_web_data as ex
        seen = {
            "a#1": {"status": "new"},
            "b#2": {"status": "new", "deprioritized": {"依据": "标题含「算法」"}},
            "c#3": {"status": "ranked", "rank_score": 70},
        }
        self.assertEqual(ex.n_parked(seen), 1)
        self.assertEqual(ex.n_processed(seen), 1,
                         "降权的还没处理完，不该算进「打过分」")

    def test_parked_sort_last_in_the_fetch_queue(self):
        """降权是排到队尾，**不是**排除 —— 额度富余时它照样轮得到。"""
        import fetch_details as fd
        rows = [{"title": "降权的", "deprioritized": {"依据": "x"}},
                {"title": "正常的"}]
        rows.sort(key=lambda e: bool(e.get("deprioritized")))
        self.assertEqual([r["title"] for r in rows], ["正常的", "降权的"])
        self.assertTrue(hasattr(fd, "missing_urls"))
