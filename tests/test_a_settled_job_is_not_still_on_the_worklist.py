# -*- coding: utf-8 -*-
"""判过死刑的岗还排在「去抓 JD」的待办里，而那条队每一格都是一次浏览器访问。

`fetch_details._missing_alive` 是「缺 JD 且还活着」的唯一定义，计数与
`--browser-list` 共用它。它挡住了两条出局路径 —— 库里的 `status`、以及用户在
总览页点的那层叠加（`user_state.json`）—— **漏了第三条：预筛/粗筛已经结案**。
那些岗 `status` 仍是 `ranked`、用户也没点过什么，但判词已经是
「跳过 / 不建议 / 硬门没过」，再抓一次 JD 不改变任何决定。

实测 2026-08-27 一次 `/job-auto`：名单 549 个，其中 **362 个已经结案**
（跳过 273、硬门 FAIL 39、不建议 23……）。更直接的代价是队首 ——
连着三条都是同一轮 `prescreen --apply` 刚判为「这家的这个岗你已经投过」的岗，
照名单走，头三次浏览器访问全花在了已经结案的岗上。修好之后名单 549 → 187。

这正是 `browser_todo` 存在的理由（它的 docstring：手挑会漏掉叠加层，
而那两次动作是那一轮唯一能用在别处的额度）—— 当时只想到了叠加层这一条。

## 判据只有一份

判词出局与否在 `doctor.is_out_verdict`。`doctor` 是依赖链的底（只用标准库、
不 import 仓库里的任何模块），所以别处 import 它，方向是对的；反过来不行。
"""
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tests"))
import doctor  # noqa: E402
import fetch_details as fd  # noqa: E402
from _srcscan import code_of  # noqa: E402


class SettledJobsLeaveTheQueue(unittest.TestCase):
    """真实职位库上跑；没有语料就 skip，不拿构造数据假装验过。"""

    def setUp(self):
        p = ROOT / ".active_user"
        if not p.is_file():
            self.skipTest("没有活动用户")
        self.user = p.read_text(encoding="utf-8").strip()
        if not (ROOT / "users" / self.user / "job_scraper"
                / "seen_jobs.json").is_file():
            self.skipTest("这个用户还没有职位库")
        self.todo = fd.browser_todo(self.user)
        if len(self.todo) < 20:
            self.skipTest("名单太短，说明不了什么")

    def test_no_settled_job_is_on_the_list(self):
        bad = [f"{str(e.get('rank_verdict'))[:12]} {(e.get('title') or '')[:24]}"
               for e in self.todo if doctor.is_out_verdict(e.get("rank_verdict"))]
        self.assertEqual(bad, [], "这些岗判词已经出局，却还排在待抓 JD 的队里：\n  "
                                  + "\n  ".join(bad[:8]))

    def test_the_list_is_a_subset_of_the_backlog(self):
        """名单是「还缺 JD」那个数的**子集**，不是同一个数。

        计数那一层留着判词已经出局的岗（`--recheck` 要抓的正是它们），
        名单这一层把它们滤掉 —— 名单只会更短，不会更长。
        """
        alive = fd._missing_alive(self.user)
        total = sum(len(v) for v in alive.values())
        self.assertLessEqual(len(self.todo), total,
                             "名单比「还缺 JD」的总数还长 —— 混进了不该在的条目")


class ThePredicateHasOneHome(unittest.TestCase):
    def test_browser_todo_imports_it_rather_than_rewriting(self):
        # `code_of` 已经剥掉 docstring，拿到的就是代码本身
        seg = code_of("tools/fetch_details.py", "def browser_todo(", "def missing_urls(")
        for w in ("跳过", "不建议", "硬门 FAIL"):
            self.assertNotIn(w, seg, f"又在这里手写了一份判词出局判据（{w}）")
        self.assertIn("is_out_verdict(", seg)

    def test_the_filter_never_sinks_into_the_backlog_count(self):
        """**这道过滤不许下沉到 `_missing_alive`。** 下沉了 `--recheck` 就整个失效：
        它要抓的正是「判过、判据没经 JD 正文复核」的那批，全带着出局判词。
        2026-08-27 第一版就放错了层，`test_fetch_details` 里那条
        `test_the_backlog_count_drops_the_ones_he_dropped` 当场变红 ——
        夹具里被标「不投」的那个岗判词是「硬门 FAIL」，已经先被滤掉了，
        于是标不标都不影响计数，那条守卫再也测不到它要测的东西。
        """
        # `code_of` 的下界是「包含」的，会把下一个函数体也带进来 —— 自己截一刀
        seg = code_of("tools/fetch_details.py", "def _missing_alive(",
                      "def browser_todo(")
        seg = seg[:seg.index("def browser_todo(")]
        self.assertNotIn("is_out_verdict", seg,
                         "判词出局的过滤下沉到 `_missing_alive` 了 —— --recheck 会失效")

    def test_doctor_still_imports_nothing_from_the_repo(self):
        """它是链的底。这一条一破，反向 import 就成了环。"""
        src = (ROOT / "tools" / "doctor.py").read_text(encoding="utf-8")
        for line in src.splitlines():
            t = line.strip()
            if t.startswith(("import ", "from ")) and " import " in t + " import ":
                mod = t.split()[1].split(".")[0]
                self.assertNotIn(mod, {"_cli", "jd_store", "export_web_data",
                                       "build_dashboard", "fetch_details",
                                       "portal_budget", "gap_split", "writeback"},
                                 f"doctor 开始 import 仓库模块了：{t}")

    def test_the_old_private_name_is_gone(self):
        src = (ROOT / "tools" / "doctor.py").read_text(encoding="utf-8")
        self.assertNotIn("_re_out", src, "旧的私名还在，两个名字迟早各走各的")

    def test_the_measured_cost_is_recorded(self):
        doc = fd._missing_alive.__doc__ or ""
        self.assertIn("362", doc, "实测数没留下")
        self.assertIn("2026-08-27", doc, "实测数没带日期")


if __name__ == "__main__":
    unittest.main()
