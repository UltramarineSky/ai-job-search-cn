# -*- coding: utf-8 -*-
"""把岗放回待评队列时抹掉旧判词 —— 同一个操作，另一个写手是留痕的。

`serve.py` 的「撤销规则淘汰」和 `audit_pipeline.requeue_unfounded_gate_fails`
做的是同一件事：`status` 回 `new`，弹掉 `rank_verdict` / `rank_score` /
`rank_date` / `rank_breakdown`。而 `serve.py` 那边的 docstring 明写着：

> 撤掉的判词存进 `prev_verdict` 留痕，不是删掉——事后要能查这个岗当初为什么被杀。

审计那一条没有这么做。实测代价（2026-08-23，活动用户）：上一次 `--apply`
退回 107 个，**99 个的上一轮判词彻底没了**（另外 8 个带 `prev_verdict`，
还是更早从面板上撤销时留的）。它们在备份 `seen_jobs.json.bak-before-requeue`
里全是 `硬门 FAIL (工作年限)`。后果三条：

- 自检和面板都说「还有 182 个没评」，而 107 个是**判据不成立退回来重评的**、
  75 个才是真没评过 —— 两种东西一个数；
- `/job-rank` 重评时拿不到「上一轮判的是什么」，规则若没真修好，
  同一批会以同样的理由再死一次，而**没人看得出这是第二次**；
- 一个岗来回弹也查不出来。

「不写新判词」（重评是 `/job-rank` 的活）和「抹掉旧判词不留痕」是两件事，
第一版把它们做成了一件。
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tests"))
import audit_pipeline as AP  # noqa: E402
from _srcscan import strip_comments  # noqa: E402


def _entry(**over):
    """一个会被「年限门判据不成立」那一支命中的岗：平台写「经验不限」。"""
    e = {"url": "https://www.liepin.com/job/1.shtml", "title": "AI产品经理",
         "company": "示例科技", "portal": "liepin-search", "status": "ranked",
         "workYears": "经验不限", "fit": "high",
         "rank_verdict": "硬门 FAIL (工作年限)", "rank_score": 58,
         "rank_date": "2026-08-11",
         "rank_breakdown": {"依据": "JD 要 5 年，他 3 年"}}
    e.update(over)
    return e


def _store(root: Path, entries: dict):
    d = root / "users" / "u" / "job_scraper"
    d.mkdir(parents=True)
    (d / "details").mkdir()
    (root / "users" / "u" / "profile").mkdir(parents=True)
    (root / "users" / "u" / "profile" / "candidate.md").write_text(
        "# 候选人\n\n## 工作年限\n\n产品方向 3 年，总年限 8 年。\n", encoding="utf-8")
    (d / "seen_jobs.json").write_text(
        json.dumps({"seen": entries}, ensure_ascii=False), encoding="utf-8")
    return d / "seen_jobs.json"


def _run(root: Path, apply=True):
    old = AP.ROOT
    try:
        AP.ROOT = root
        return AP.requeue_unfounded_gate_fails("u", apply=apply)
    finally:
        AP.ROOT = old


def _read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))["seen"]


class TheDashboardClickIsNotClobbered(unittest.TestCase):
    """读到写之间隔着几分钟，而用户就在那几分钟里点了按钮。

    这个函数读完职位库之后要读 `candidate.md`、glob 全部 `details/*.json`、
    再逐份读 `evaluation.md` —— 2262 条的库上是几十秒到几分钟。
    `load_json_stamped` 的 docstring 把这类窗口点名叫「长窗口」，
    而它原来是 `data, _ = ...`：戳读了、扔了，写回不带 `expect`。
    于是总览页那一下被十分钟前的快照静默盖掉，一个字的提示都没有
    （有 `.bak-before-requeue` 兜底，但没人会知道要去翻它）。

    同一个文件的三个兄弟写手全都传了戳（`archive` / `prescreen` / `writeback`）。
    """

    def test_a_write_during_the_window_makes_it_yield(self):
        import _cli
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p = _store(root, {"a": _entry()})
            real = AP._cli.load_json_stamped

            def racing(path):
                """先照常读，再模拟总览页那一下落盘 —— 戳当场就旧了。"""
                out = real(path)
                p.write_text(json.dumps(
                    {"seen": {"a": _entry(status="skipped",
                                          skip_reason="他自己点的不投")}},
                    ensure_ascii=False), encoding="utf-8")
                return out

            AP._cli.load_json_stamped = racing
            try:
                with self.assertRaises(_cli.StaleWrite):
                    _run(root)
            finally:
                AP._cli.load_json_stamped = real
            e = _read(p)["a"]
        self.assertEqual(e["status"], "skipped", "用户点的那一下被盖掉了")
        self.assertEqual(e["skip_reason"], "他自己点的不投")


class TheOldVerdictIsKept(unittest.TestCase):
    def test_it_lands_in_prev_verdict(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p = _store(root, {"a": _entry()})
            self.assertEqual(_run(root), ["a"])
            e = _read(p)["a"]
        self.assertIn("prev_verdict", e, "上一轮判词被抹掉了，没留痕")
        self.assertEqual(e["prev_verdict"]["判词"], "硬门 FAIL (工作年限)")
        self.assertEqual(e["prev_verdict"]["分"], 58)
        self.assertEqual(e["prev_verdict"]["依据"], "JD 要 5 年，他 3 年")

    def test_it_records_when(self):
        """没有日期就分不出「这次退回的」和「上个月退回的」。"""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p = _store(root, {"a": _entry()})
            _run(root)
            e = _read(p)["a"]
        self.assertRegex(e["prev_verdict"]["退回于"], r"^\d{4}-\d{2}-\d{2}$")

    def test_the_flat_score_is_kept_too(self):
        """`/job-apply` 拿 `prev_score` 和 `rank_score` 现算粗筛与深评的落差，
        它读的是平铺字段，不是上面那个字典。"""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p = _store(root, {"a": _entry()})
            _run(root)
            e = _read(p)["a"]
        self.assertEqual(e["prev_score"], 58)

    def test_an_earlier_receipt_is_not_overwritten(self):
        """更早那次撤销记的才是「当初为什么被杀」。"""
        old = {"判词": "粗筛：跳过", "分": 12, "依据": "标题含「开发」",
               "撤销于": "2026-08-01"}
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p = _store(root, {"a": _entry(prev_verdict=old)})
            _run(root)
            e = _read(p)["a"]
        self.assertEqual(e["prev_verdict"], old, "把更早那张单据盖掉了")

    def test_every_requeued_entry_gets_one(self):
        """**这一条原来是反着写的，而且空转。** 第一版验「没有 `rank_verdict`
        的不发单据」，却把 `rank_verdict` 设成了空串 —— 那样它连三个选择器
        （年限门 / 无依据 / 排除无出处）都进不了，压根没被退回，
        断言自然通过。变异实测抓到。

        真正的不变式反过来：**三个选择器都以「有判词」为前提，
        所以凡是被退回的，都必须留下一张单据。**"""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p = _store(root, {"a": _entry(),
                              "b": _entry(url="https://www.liepin.com/job/2.shtml",
                                          rank_verdict="硬门 FAIL (工作年限)",
                                          rank_score=None)})
            keys = _run(root)
            seen = _read(p)
        self.assertEqual(sorted(keys), ["a", "b"])
        for k in keys:
            with self.subTest(key=k):
                self.assertIn("prev_verdict", seen[k], "退回了却没留单据")
                self.assertTrue(seen[k]["prev_verdict"]["判词"])


class TheRequeueItselfStillWorks(unittest.TestCase):
    """留痕是加出来的，原来那几件事一件都不许少。"""

    def test_status_goes_back_to_new(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p = _store(root, {"a": _entry()})
            _run(root)
            self.assertEqual(_read(p)["a"]["status"], "new")

    def test_all_four_rank_fields_are_popped(self):
        """`rank_breakdown` 也要抹 —— 只抹前三个时导出侧照着四维拆解
        重建出了判词，流水线计数对不上（原有的判据，别丢）。"""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p = _store(root, {"a": _entry()})
            _run(root)
            e = _read(p)["a"]
        for f in ("rank_verdict", "rank_score", "rank_date", "rank_breakdown"):
            with self.subTest(field=f):
                self.assertNotIn(f, e)

    def test_no_new_verdict_is_written(self):
        """重评是 `/job-rank` 的活。留痕不等于改判。"""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p = _store(root, {"a": _entry()})
            _run(root)
            e = _read(p)["a"]
        self.assertNotIn("rank_verdict", e)
        self.assertEqual(e["prev_verdict"]["判词"], "硬门 FAIL (工作年限)",
                         "留下的必须是原判，不是新写的")

    def test_a_dry_run_writes_nothing(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p = _store(root, {"a": _entry()})
            before = p.read_text(encoding="utf-8")
            self.assertEqual(_run(root, apply=False), ["a"])
            self.assertEqual(p.read_text(encoding="utf-8"), before)

    def test_the_backup_is_still_written(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p = _store(root, {"a": _entry()})
            _run(root)
            bak = p.with_suffix(".json.bak-before-requeue")
            self.assertTrue(bak.is_file(), "落盘前那份备份没了")
            self.assertEqual(
                json.loads(bak.read_text(encoding="utf-8"))["seen"]["a"]["rank_score"],
                58, "备份存的不是改动前那份")

    def test_a_deep_evaluated_job_is_left_alone(self):
        """读过 JD 的深评结论不放回 —— 原有的判据。"""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p = _store(root, {"a": _entry(evaluated=True)})
            self.assertEqual(_run(root), [])
            self.assertEqual(_read(p)["a"]["status"], "ranked")


class TheTwoWritersAgree(unittest.TestCase):
    """同一个动作两个写手。哪天一边改了形状，另一边要跟着。"""

    def test_serve_still_keeps_a_receipt(self):
        src = (ROOT / "tools" / "serve.py").read_text(encoding="utf-8")
        self.assertIn('entry["prev_verdict"] = {', src,
                      "撤销那一侧不再留痕了 —— 这条规矩的另一半没了")
        self.assertIn("留痕，不是删掉", src)

    def test_the_shapes_match_except_the_date_key(self):
        serve = strip_comments((ROOT / "tools" / "serve.py")
                               .read_text(encoding="utf-8"))
        audit = strip_comments((ROOT / "tools" / "audit_pipeline.py")
                               .read_text(encoding="utf-8"))
        for k in ("判词", "分", "依据"):
            with self.subTest(key=k):
                self.assertIn(f'"{k}":', serve)
                self.assertIn(f'"{k}":', audit)
        self.assertIn('"撤销于"', serve, "撤销那边的日期键变了")
        self.assertIn('"退回于"', audit, "退回这边的日期键变了")

    def test_the_reason_is_written_down(self):
        """一段「先存再抹」看着像多余，理由不挨着写就会被下一版删掉。"""
        src = (ROOT / "tools" / "audit_pipeline.py").read_text(encoding="utf-8")
        i = src.index("def requeue_unfounded_gate_fails(")
        seg = src[i:i + 3000]
        self.assertIn("抹掉之前先存进 `prev_verdict`", seg)
        self.assertRegex(seg, r"99 个的上一轮判词彻底没了", "没留下实测的量")
        self.assertRegex(seg, r"没人看得出这是第二次")


if __name__ == "__main__":
    unittest.main()
