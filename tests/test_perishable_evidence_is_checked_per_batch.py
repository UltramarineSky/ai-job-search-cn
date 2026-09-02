# -*- coding: utf-8 -*-
"""有几条证据过了这一批就没了，不能等整轮收尾再查。

最典型的是「判词自称读过 JD，库里却没有」：浏览器读来的正文**只活在读它的
那一刻**。当批发现，跑一次 `jd_store.py --save` 就补上了；等全量自检跑完再
发现，那段正文早已不在手里，只能重开页面、再花一次额度。

实测 2026-08-30：这一条积到了 **145 个岗**，而落库这条规则在三个工作流里都
写着（`job-scrape.md`、`job-rank.md` Step 0 与 Step 2）。**规则没缺，缺的是
「什么时候查」** —— 全量审计是收尾用的，而这条证据是易腐的。

所以这条守卫钉三件事：**能单跑**（`audit_pipeline --only`）、**每批真的跑了**
（两个工作流的机械步骤里都点名）、以及**单跑的名字是真存在的**（写错一个字
就静默跑 0 条检查，看起来永远是绿的）。
"""
import pathlib
import subprocess
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tests"))
from _live import user_or_skip  # noqa: E402
import audit_pipeline as ap  # noqa: E402

#: 每批收尾要跑的那几条，逗号分隔——与两个工作流里写的那一行是同一个串。
PER_BATCH = "证据,JD：读了没落库"
RANK = (ROOT / "workflows" / "job-rank.md").read_text(encoding="utf-8")
AUTO = (ROOT / "workflows" / "job-auto.md").read_text(encoding="utf-8")


class TheFilterWorks(unittest.TestCase):
    def test_every_term_matches_a_real_check(self):
        """写错一个字就跑 0 条 —— 而 0 条检查全过，看起来和真的全过一样。"""
        names = [n for n, _ in ap.CHECKS]
        for term in PER_BATCH.split(","):
            with self.subTest(term=term):
                self.assertTrue([n for n in names if term in n],
                                f"没有名字含「{term}」的检查")

    def test_it_runs_fewer_than_everything(self):
        """筛出来的得是**一小撮**，否则「每批跑」就成了每批跑全量。"""
        hit = [n for n, _ in ap.CHECKS
               if any(t in n for t in PER_BATCH.split(","))]
        self.assertGreaterEqual(len(hit), 2)
        self.assertLess(len(hit), len(ap.CHECKS) // 4)

    def test_an_unknown_term_says_so_instead_of_passing(self):
        """名字不存在时要报错并列出全部名字，不能静默返回「全过」。"""
        user_or_skip()   # 没有真实数据可读时 skip（见 tests/_live.py）
        r = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "audit_pipeline.py"),
             "--only", "这个名字不存在"],
            capture_output=True, text=True, encoding="utf-8", cwd=str(ROOT))
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn("没有名字里含", r.stdout)


class TheListLivesInExactlyOnePlace(unittest.TestCase):
    """清单在 `job-rank.md` Step 0，`job-auto.md` 只许指路。

    **两处都写会分叉，而且当场就分叉了。** 2026-08-30 加 `score.py --deep` 和
    `--only` 那两条时两边各加一遍，而 job-auto 那句「Step 0 那几条」还停在旧的
    四条上 —— 同一个文件里「那几条」指四条、下面又「再加一条」加了两条。
    判据与 `AGENTS.md`「换个工具，哪些命令还能用」那张表下面记的是同一课。
    """

    def test_the_rank_step_owns_the_list(self):
        self.assertIn(f"audit_pipeline.py --only {PER_BATCH}", RANK)

    def test_the_rank_step_says_why_it_is_per_batch(self):
        """只给一条命令不够 —— 不说清「为什么不能留到收尾」，下一个人会把它挪走。"""
        self.assertIn("只活在读它的那一刻", RANK)

    def test_the_fix_command_is_right_there(self):
        """发现了要能马上补 —— 引导得给出该敲的那条（AGENTS.md 那条通则）。"""
        self.assertIn("jd_store.py --save <职位链接> --apply", RANK)

    def test_the_auto_run_points_at_it_instead_of_copying(self):
        self.assertIn("job-rank.md", AUTO)
        self.assertIn("每批都要跑", AUTO)

    def test_the_auto_run_does_not_re_list_them(self):
        """抄一份回去就等着它再分叉一次。

        **只看「每批都要跑的机械步骤」那一节。** 收尾块里的
        `writeback.py --apply` 是另一步（出完材料才跑），它在那儿是对的 ——
        第一版没划范围，把收尾那条也当成了抄件。
        """
        i = AUTO.index("### 每批都要跑的机械步骤")
        j = AUTO.index("\n## ", i)
        section = AUTO[i:j]
        for cmd in (f"audit_pipeline.py --only {PER_BATCH}",
                    "score.py --deep --apply", "score.py --apply",
                    "prescreen.py --annual-floor", "writeback.py --apply"):
            with self.subTest(cmd=cmd):
                self.assertNotIn(cmd, section,
                                 "job-auto 又把 Step 0 的命令抄了一份")


if __name__ == "__main__":
    unittest.main()
