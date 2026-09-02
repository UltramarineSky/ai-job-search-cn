# -*- coding: utf-8 -*-
"""「搜到 2638 → 打过分 2450」并排画着，中间那 188 从来没被点名。

读的人得自己减，减完还不知道那是不是待办。**而它不全是待办** ——
实测活动用户 2026-08-23：

    188 = 182 个 `status: new`（真在排队等着评）
        +   6 个已下线且从没评过的死岗

印 188 就是把 6 个死岗说成积压；而一个字都不印，182 个可能有货的岗就
在任何一处都不出现 —— 同一屏上面板正在说库存见底（行业对口只剩 49、
备好没发的 62）。

**这一段本该是空的。** `AGENTS.md` 的承诺是「抓完直接排出可以投的，
不停在待评」；它有数，说明那条自动衔接断过一次。所以判据故意比
`len(seen) - n_processed(seen)` 更窄，两者的差就是那批死岗。

判据在 `doctor.n_waiting`，面板那边由 `build_dashboard` **import 同一个函数**
（不是复刻）—— doctor 自己不许 import 仓库模块，方向只能是这一个。
"""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import build_dashboard as B  # noqa: E402
import doctor  # noqa: E402

APP = (ROOT / "web" / "src" / "App.tsx").read_text(encoding="utf-8")
TYPES = (ROOT / "web" / "src" / "types.ts").read_text(encoding="utf-8")


class TheJudgeCountsOnlyWhatIsWaiting(unittest.TestCase):
    def _seen(self, *rows):
        return {f"k{i}": r for i, r in enumerate(rows)}

    def test_a_new_job_with_no_score_is_waiting(self):
        self.assertEqual(doctor.n_waiting(
            self._seen({"status": "new", "rank_score": None})), 1)

    def test_a_dead_job_is_not_waiting(self):
        """已下线且从没评过的 —— 它在 `n_processed` 的补集里，但**不是待办**。
        实测 188 个缺口里有 6 个是这种。"""
        self.assertEqual(doctor.n_waiting(
            self._seen({"status": "expired", "rank_score": None})), 0)

    def test_a_scored_job_is_not_waiting(self):
        for row in ({"status": "new", "rank_score": 61},
                    {"status": "ranked", "rank_score": 61},
                    {"status": "skipped", "rank_score": None}):
            with self.subTest(row=str(row)):
                self.assertEqual(doctor.n_waiting(self._seen(row)), 0)

    def test_it_is_narrower_than_the_raw_gap(self):
        """**不许写成 `len(seen) - n_processed(seen)`** —— 那个差把死岗算进来。"""
        seen = self._seen({"status": "new", "rank_score": None},
                          {"status": "expired", "rank_score": None},
                          {"status": "ranked", "rank_score": 61})
        self.assertEqual(len(seen) - doctor.n_processed(seen), 2)
        self.assertEqual(doctor.n_waiting(seen), 1, "把死岗也算成待办了")

    def test_junk_entries_do_not_crash_it(self):
        self.assertEqual(doctor.n_waiting({"a": None, "b": "x", "c": 3}), 0)


class BothSidesUseTheOneFunction(unittest.TestCase):
    def test_the_dashboard_imports_it_from_doctor(self):
        """**不是复刻。** doctor 不许 import 仓库模块，方向只能是这一个。"""
        src = (ROOT / "tools" / "build_dashboard.py").read_text(encoding="utf-8")
        i = src.index("from doctor import")
        self.assertIn("n_waiting", src[i:i + 300], "没从 doctor 取")
        self.assertIs(B.n_waiting, doctor.n_waiting, "拿到的不是同一个函数")

    def test_there_is_no_fallback_copy(self):
        """**兜底副本已经删掉了，别再长出来。**

        这里原来有一份 `except ImportError` 里的复刻，docstring 写着「口径必须
        与那边一致」，而守它的就是这条测试——比的是文本形状
        （`== "new"` 在不在、`rank_score` 在不在）。那拦不住真分叉：
        条件写反、少一个 `or` 分支，两样都还在。

        更要紧的是**它复制的正是出过事的那个函数**：`build_dashboard.py` 开头
        那段注释记着 `n_processed` 两处各写一套时，自检说「已评 193」、
        面板说「打过分 195」。为「doctor 被删/改坏」留一份会静默偏离的副本，
        等于把那次事故的条件重新装回来 —— 而 doctor 是 stdlib-only、就在隔壁，
        真挂了该炸在 import，跟同一个文件里 `import tracker` 那条一样
        （「没有兜底，它挂了就该炸在 import，而不是在半路 NameError」）。

        环境那两个（`probe_env` / `template_tokens`）**仍然留着 try**：
        它们有 `if ... else` 的消费点，缺了页面照样完整；计数缺了页面就是错的。
        """
        src = (ROOT / "tools" / "build_dashboard.py").read_text(encoding="utf-8")
        for fn in ("n_waiting", "n_processed"):
            with self.subTest(fn=fn):
                self.assertNotIn(
                    f"def {fn}(", src,
                    f"build_dashboard 又自己定义了一份 {fn} —— "
                    f"它的正本在 doctor，两份必然分叉（193/195 那次就是这么来的）")
        # 环境那块的 try 要还在，别把这条读成「所有 except 都该删」。
        i = src.index("except Exception")
        self.assertIn("_probe_env = None", src[i:i + 200],
                      "环境那块的兜底被一起删了 —— 它是真可选的，该留")

    def test_the_export_puts_it_in_the_pipeline(self):
        src = (ROOT / "tools" / "export_web_data.py").read_text(encoding="utf-8")
        self.assertIn('"waiting": _n_wait', src, "导出没带这个数")
        i = src.index('"waiting": _n_wait')
        self.assertIn("if _n_wait else {}", src[i:i + 80],
                      "没有「有才给」的门槛 —— 平时会印一个 0")


class TheSelfCheckSaysIt(unittest.TestCase):
    def _seg(self):
        src = (ROOT / "tools" / "doctor.py").read_text(encoding="utf-8")
        i = src.index('print(f"{OK}已抓 ')
        return src[max(0, i - 500):i + 400]

    def test_the_line_carries_it(self):
        self.assertIn("st['waiting']", self._seg(), "自检那行还是要人自己减")

    def test_it_gives_the_command(self):
        self.assertIn("/job-rank", self._seg(), "说了有多少没评，没说怎么评")

    def test_it_stays_quiet_when_there_is_none(self):
        """正常抓完就自动评了。没有待评时多一句「还有 0 个」是噪音。"""
        self.assertRegex(self._seg(), r'if st\.get\("waiting"\)',
                         "没有「有才说」的门槛 —— 平时会印一句「还有 0 个没评」")


class ThePanelSaysIt(unittest.TestCase):
    def _seg(self):
        #: **只取渲染那一段。** 往后多取几百字就会跨进隔壁 `parked` 那个 `<p>`，
        #: 于是「两句不许混在一起」那条断言在别人的文字上求值 —— 本仓库
        #: 反复栽过的定位坑。以 `</p>` 收边。
        i = APP.index("pipeline.some((s) => (s.waiting ?? 0) > 0)")
        return APP[i:APP.index("</p>", i) + 4]

    def test_it_renders(self):
        self.assertIn("waiting", APP, "面板没有这个数")
        self.assertRegex(self._seg(), r"抓回来没评分|没评分")

    def test_it_gives_the_command(self):
        self.assertIn("/job-rank", self._seg(), "没给命令")

    def test_it_says_why_it_matters(self):
        """只报数是观察。要说出它对他的意思：这批不在任何名单里。"""
        self.assertRegex(self._seg(), r"不在上面任何一份名单|能不能投还不知道")

    def test_it_is_not_merged_with_the_parked_note(self):
        """`parked` 说的是「不用管的那一半」，这条说的是待办 ——
        两句管的不是一件事，并成一句就再也分不开。"""
        seg = self._seg()
        self.assertNotIn("不用管", seg, "和「不用管」那条混在一起了")

    def test_the_field_is_optional_in_the_type(self):
        i = TYPES.index("PipelineStage")
        self.assertRegex(TYPES[i:i + 900], r"waiting\?: number",
                         "写成必填了 —— 旧快照没有它")


class OnRealDataTheNumbersLineUp(unittest.TestCase):
    def test_the_self_check_and_the_panel_say_the_same(self):
        p = ROOT / ".active_user"
        data = ROOT / "web" / "public" / "data.json"
        if not p.is_file() or not data.is_file():
            self.skipTest("没有活动用户或还没导出面板数据")
        ud = ROOT / "users" / p.read_text(encoding="utf-8").strip()
        sj = ud / "job_scraper" / "seen_jobs.json"
        if not sj.is_file():
            self.skipTest("还没抓过职位")
        raw = json.loads(sj.read_text(encoding="utf-8"))
        mine = doctor.n_waiting(raw.get("seen", raw))
        snap = json.loads(data.read_text(encoding="utf-8"))
        step2 = next(x for x in snap["pipeline"] if x["step"] == 2)
        self.assertEqual(step2.get("waiting", 0), mine,
                         f"自检 {mine}、面板 {step2.get('waiting', 0)}")

    def test_it_never_exceeds_the_raw_gap(self):
        data = ROOT / "web" / "public" / "data.json"
        if not data.is_file():
            self.skipTest("还没导出面板数据")
        snap = json.loads(data.read_text(encoding="utf-8"))
        s1 = next(x for x in snap["pipeline"] if x["step"] == 1)
        s2 = next(x for x in snap["pipeline"] if x["step"] == 2)
        self.assertLessEqual(s2.get("waiting", 0), s1["count"] - s2["count"],
                             "待评比整个缺口还大，口径反了")


if __name__ == "__main__":
    unittest.main()
