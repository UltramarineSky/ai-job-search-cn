# -*- coding: utf-8 -*-
"""审计报了 14 份深评判错，给的修法是 `/job-rank --all` —— 那条命令改不到深评。

`check_years_gate_vs_platform_field` 的第三档（「年限门挡掉的其实是领域经验」）
读的是 `documents/applications/*/evaluation.md`：那个 FAIL 写在深评文件里。
而 `/job-rank --all` 只重写职位库的 `rank_*`，**深评文件一个字不动**
（写它的是 `/job-apply`；`job-rank.md` 自己划的边界就是「`/job-rank` 从不写
投递目录」）。

实测活动用户 2026-08-25，那 14 份：

    evaluated=True                 14/14   ← requeue 按设计一律不碰
    status=skipped                  1/14   ← `--all` 明写不覆盖 skipped
    面板硬性条件表仍写 `fail`      14/14   ← 那张表就是从 evaluation.md 出的

也就是说：照那条建议跑一遍，用户点开岗位看到的「工作年限 · 不满足」原封不动。

## 同一份文件里早就有正确的说法

`check_unknown_months_is_not_a_death_sentence` 的判词写着
「修：对这几个岗逐个跑 /job-apply <职位链接> 重评（/job-rank --all 只改粗筛，
改不到深评）」，它的 docstring 也写着同一句。**一个流程两条相反的规则** ——
这一条把分叉的那半接了回去。

## 顺带补上的两处

- 「年限门挡掉了他年限够的岗」原来报完 11 个就收尾，**一条命令都没给**。
  而它是两批：6 个粗筛判的（`--requeue-unfounded --apply` 一条搞定）、
  5 个深评判的（只能逐个 `/job-apply`）。混成一条写，就有一半人改不动。
- `--requeue-unfounded` 只说「会放回 6 个」，故意没动的那批**一个字没提**。
  现在报出来，而且取的是**并集不是和**：两档实测 5 与 14，交集 4 个 ——
  相加会报 19，真数是 15。
"""
import json
import pathlib
import re
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import audit_pipeline as ap  # noqa: E402
import _cli  # noqa: E402

AUDIT = (ROOT / "tools" / "audit_pipeline.py").read_text(encoding="utf-8")


def flat(s: str) -> str:
    s = " ".join(re.sub(r"^\s*(?:>|#:?)\s?", "", s, flags=re.M).split())
    return re.sub(r"(?<=[一-鿿，。；：、（）「」])"
                  r" +(?=[一-鿿，。；：、（）「」])", "", s)


def _live():
    """现算：活动用户那份真库跑出来的三档年限判词。"""
    p = ROOT / ".active_user"
    if not p.is_file():
        raise unittest.SkipTest("没有活动用户")
    user = _cli.pick_user("", root=ROOT)
    seen, details = ap.load(user)
    ap._USER[:] = [user]
    return user, seen, details


class TheAdviceCanActuallyFixIt(unittest.TestCase):
    """报的是深评，指的却是粗筛命令 —— 这是这一条全部的内容。"""

    def _msg(self) -> str:
        i = AUDIT.index('"年限门挡掉的其实是领域经验"')
        return AUDIT[i:AUDIT.index("))", i)]

    def test_it_names_the_command_that_rewrites_a_deep_eval(self):
        self.assertIn("/job-apply <职位链接>", self._msg())

    def test_it_no_longer_points_at_the_coarse_command(self):
        """**这是修掉的那一处。** 留着它，14 个岗永远出不来。"""
        self.assertNotIn("/job-rank --all", self._msg())

    def test_it_says_what_gets_changed(self):
        """只给命令不说改什么，用户不知道跑完该看哪儿。"""
        self.assertIn("改这几份深评", self._msg())

    def test_the_reason_is_recorded_next_to_it(self):
        i = AUDIT.index("# **这一档的修法不是 `/job-rank --all`。**")
        seg = flat(AUDIT[i:AUDIT.index("smuggled = _years_gate_smuggling_domain", i)])
        self.assertRegex(seg, r"那个 FAIL 写在深评文件里")
        self.assertRegex(seg, r"只重写库里的 `rank_\*`，\*\*深评文件一个字不动\*\*")
        self.assertIn("2026-08-25", seg)

    def test_the_reason_carries_the_three_measurements(self):
        i = AUDIT.index("# **这一档的修法不是 `/job-rank --all`。**")
        seg = AUDIT[i:AUDIT.index("smuggled = _years_gate_smuggling_domain", i)]
        for w in ("evaluated=True", "status=skipped", "面板硬性条件表仍写 fail"):
            with self.subTest(w=w):
                self.assertIn(w, seg)

    def test_it_points_at_the_boundary_that_makes_it_true(self):
        """「`/job-rank` 从不写投递目录」是这条论证的支点。"""
        i = AUDIT.index("# **这一档的修法不是 `/job-rank --all`。**")
        seg = flat(AUDIT[i:AUDIT.index("smuggled = _years_gate_smuggling_domain", i)])
        self.assertRegex(seg, r"`/job-rank` 从不写投递目录")

    def test_that_boundary_really_is_in_the_workflow(self):
        """支点没了，这一条就成了自说自话。"""
        rank = (ROOT / "workflows" / "job-rank.md").read_text(encoding="utf-8")
        self.assertRegex(flat(rank), r"\*\*不要动 `job_search_tracker.csv`\*\*")
        self.assertRegex(flat(rank), r"`/job-rank` 从不投")


class TheSiblingAlreadySaidIt(unittest.TestCase):
    """同一份文件里早就有正确说法 —— 这一条只是把分叉的那半接回去。"""

    def test_the_sibling_message_names_a_command_that_reaches_deep_evals(self):
        """兄弟那条给的命令得真能改到深评 —— 指一条改不到的等于让他白跑。

        **它 2026-08-30 换过一次。** 原来给的是「逐个 `/job-apply <职位链接>`，
        `/job-rank --all` 只改粗筛」；`score.py --deep` 补上那一层之后
        （连 `evaluation.md` 一起改），逐个敲成了白费力气 —— 实测那批 89 个，
        一条命令跑完 87 个。**判据没变**：别指一条改不到的命令。
        """
        i = AUDIT.index('"没标薪数的岗被薪资分埋掉了"')
        seg = flat(AUDIT[i:AUDIT.index(")]", i)])
        self.assertRegex(seg, r"score\.py --deep --apply")
        self.assertNotRegex(seg, r"/job-rank --all")

    def test_the_sibling_docstring_draws_the_line(self):
        """而且要说清分界在哪：确定性的机械改，判断的才 `/job-apply`。"""
        i = AUDIT.index("def check_unknown_months_is_not_a_death_sentence")
        seg = flat(AUDIT[i:i + 3000])
        self.assertRegex(seg, r"score\.py --deep --apply")
        self.assertRegex(seg, r"分界是.*这一维要不要读 JD 才知道")

    def test_the_library_side_tier_keeps_the_coarse_command(self):
        """**别一刀切。** 「经验不限」那一档读的是卡片字段，`--all` 对它是对的。"""
        i = AUDIT.index('"年限门挡掉了「经验不限」的岗"')
        self.assertIn("/job-rank --all", AUDIT[i:AUDIT.index("))", i)])


class TheMiddleTierNowSaysWhatToType(unittest.TestCase):
    """报完一个数就收尾，用户不知道该敲什么（AGENTS.md 那条规矩）。"""

    def _msg(self) -> str:
        i = AUDIT.index('"年限门挡掉了他年限够的岗"')
        return AUDIT[i:AUDIT.index("))", i)]

    def test_it_carries_a_command(self):
        self.assertIn("--requeue-unfounded --apply", AUDIT[
            AUDIT.index("ev = [e for e in low if e.get(\"evaluated\")]"):
            AUDIT.index('"年限门挡掉了他年限够的岗"')])

    def test_the_second_path_is_conditional(self):
        """深评那批为零时不该凭空多出半句 —— 这一档随数据会空。"""
        i = AUDIT.index('ev = [e for e in low if e.get("evaluated")]')
        seg = AUDIT[i:AUDIT.index('"年限门挡掉了他年限够的岗"')]
        self.assertIn("if ev:", seg)
        self.assertIn("/job-apply <职位链接>", seg)

    def test_it_says_which_command_covers_which_batch(self):
        """一条引导对应一条命令；真有分支就写清哪种情况敲哪条。"""
        i = AUDIT.index('ev = [e for e in low if e.get("evaluated")]')
        seg = flat(AUDIT[i:AUDIT.index('"年限门挡掉了他年限够的岗"')])
        self.assertRegex(seg, r"那条只放回粗筛判的")
        self.assertRegex(seg, r"它一律不碰")

    def test_the_reason_is_recorded(self):
        i = AUDIT.index("# **这一档要分两条路说，因为它本来就是两批。**")
        seg = flat(AUDIT[i:AUDIT.index('ev = [e for e in low', i)])
        self.assertRegex(seg, r"报一个数就收尾，用户不知道该敲什么")
        self.assertRegex(seg, r"混成一条写，就有一半人按那条改不动自己那几个岗")
        self.assertIn("2026-08-25", seg)

    def test_the_rule_it_cites_is_real(self):
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("## 每一处引导都要写出该敲的命令", agents)


class TheSkippedOnesAreCounted(unittest.TestCase):
    """故意没动的那批不能静默消失 —— 用户读到「放回 6 个」会以为就这 6 个。"""

    def test_the_counter_exists(self):
        self.assertIsInstance(ap._REQUEUE_SKIPPED, list)

    def test_the_tail_names_the_number(self):
        i = AUDIT.index("n_skip = _REQUEUE_SKIPPED[0]")
        seg = AUDIT[i:AUDIT.index('if n_skip else ""', i)]
        self.assertIn("{n_skip} 个判据同样不成立", seg)

    def test_the_tail_says_why_they_were_left(self):
        i = AUDIT.index("n_skip = _REQUEUE_SKIPPED[0]")
        seg = flat(AUDIT[i:AUDIT.index('if n_skip else ""', i)])
        self.assertRegex(seg, r"抹掉等于丢掉真做过的工作")

    def test_the_tail_names_the_right_command(self):
        i = AUDIT.index("n_skip = _REQUEUE_SKIPPED[0]")
        seg = AUDIT[i:AUDIT.index('if n_skip else ""', i)]
        self.assertIn("/job-apply <职位链接>", seg)
        self.assertIn("/job-rank --all 改不了它们", seg)

    def test_the_tail_is_plain_text(self):
        """终端里 `**` 会连着星号一起显示 —— 同 AGENTS.md 那条 markdown 规矩。"""
        i = AUDIT.index("n_skip = _REQUEUE_SKIPPED[0]")
        self.assertNotIn("**", AUDIT[i:AUDIT.index('if n_skip else ""', i)])

    def test_it_disappears_when_there_is_nothing_to_report(self):
        """0 个的时候不该多出一句「另有 0 个」。"""
        i = AUDIT.index("n_skip = _REQUEUE_SKIPPED[0]")
        self.assertIn('if n_skip else ""', AUDIT[i:i + 900])

    def test_the_two_tiers_are_unioned_not_summed(self):
        """**这是它唯一容易写错的地方。** 相加会把交集那批数两遍。"""
        i = AUDIT.index("skipped = set()")
        seg = AUDIT[i:AUDIT.index("_REQUEUE_SKIPPED[:] =", i)]
        self.assertIn("skipped.add(", seg)
        self.assertNotIn("skipped[k] = e", seg)

    def test_the_overlap_is_recorded(self):
        i = AUDIT.index("# **两档要取并集，不能相加。**")
        seg = flat(AUDIT[i:AUDIT.index("_REQUEUE_SKIPPED[:] =", i)])
        self.assertRegex(seg, r"实测 2026-08-25 是 5 和 14，而\*\*交集有 4 个\*\*")
        self.assertRegex(seg, r"相加会报 19，真数是 15")


class TheRequeueStillRefusesDeepEvals(unittest.TestCase):
    """这一条整个建立在「requeue 不碰深评」上 —— 它没了，报告就没意义了。"""

    def test_the_guard_is_still_there(self):
        i = AUDIT.index("def requeue_unfounded_gate_fails")
        seg = AUDIT[i:AUDIT.index("_REQUEUE_SKIPPED[:] =", i)]
        self.assertIn('if e.get("evaluated"):', seg)
        self.assertIn("读过 JD 的深评结论不放回", flat(seg))

    def test_the_other_selector_filters_them_too(self):
        i = AUDIT.index("hit.update({k: e for k, e in _unfounded_gate_fails")
        self.assertIn('not e.get("evaluated")', AUDIT[i:i + 200])


class TheSignalItLeansOnIsReal(unittest.TestCase):
    """现算：那 14 份真的全是深评，而且 `--all` 真的够不着它们。"""

    def _smuggled(self):
        user, seen, _d = _live()
        yrs = ap._candidate_years()
        if not yrs:
            self.skipTest("读不出候选人年限")
        sm = ap._years_gate_smuggling_domain(max(yrs))
        if len(sm) < 3:
            self.skipTest(f"只有 {len(sm)} 份 —— 这一档已经修得差不多了")
        apps = ROOT / "users" / user / "documents" / "applications"
        urls = []
        for d, _q in sm:
            t = (apps / d / "evaluation.md").read_text(encoding="utf-8",
                                                       errors="replace")
            m = re.search(r"https?://\S+", t)
            if m:
                urls.append(m.group(0).rstrip("）)」，。"))
        return seen, urls

    def test_they_are_all_deep_evaluated(self):
        """有一个不是深评，requeue 就该放回它 —— 那时这一条要重看。"""
        seen, urls = self._smuggled()
        byurl = {e.get("url"): e for e in seen.values()
                 if isinstance(e, dict) and e.get("url")}
        n = sum(1 for u in urls if (byurl.get(u) or {}).get("evaluated"))
        self.assertEqual(n, len(urls),
                         f"{len(urls) - n} 个不是深评 —— requeue 本该放回它们")

    def test_the_panel_still_shows_the_fail_row(self):
        """那一行来自 evaluation.md —— 它在，就说明 `--all` 改不到。"""
        _seen, urls = self._smuggled()
        p = ROOT / "web" / "public" / "data.json"
        if not p.is_file():
            self.skipTest("还没导出过面板数据")
        byurl = {j.get("url"): j for j in json.loads(
            p.read_text(encoding="utf-8"))["jobs"]}
        n = sum(1 for u in urls
                for g in (byurl.get(u) or {}).get("gates") or []
                if "工作年限" in str(g.get("name") or "")
                and str(g.get("state")) == "fail")
        self.assertGreater(n, 0, "面板上一行都没有了 —— 这一档可能已经修完")

    def test_the_two_tiers_really_overlap(self):
        """**并集那条判据的支点。** 不重叠时相加也对，这一条就没意义了。"""
        seen, urls = self._smuggled()
        yrs = ap._candidate_years()
        floor = min(yrs) + 1
        lib = {e.get("url") for e in seen.values()
               if isinstance(e, dict) and e.get("evaluated")
               and "工作年限" in str(e.get("rank_verdict") or "")
               and ((ap._min_years(e.get("workYears")) == 0)
                    or ((ap._min_years(e.get("workYears")) or 99) <= floor))}
        both = lib & set(urls)
        if not both:
            self.skipTest("两档现在不重叠了 —— 并集与和相等")
        self.assertLess(len(lib | set(urls)), len(lib) + len(urls))

    def test_the_counter_matches_that_union(self):
        seen, urls = self._smuggled()
        user = _cli.pick_user("", root=ROOT)
        ap.requeue_unfounded_gate_fails(user)          # dry-run，不落盘
        n = ap._REQUEUE_SKIPPED[0] if ap._REQUEUE_SKIPPED else 0
        self.assertGreaterEqual(n, len(urls),
                                f"计数器 {n} 比领域经验那一档的 {len(urls)} 还小 —— "
                                f"并集没并上")

    def test_requeue_never_touches_them(self):
        """现算：dry-run 放回的那批里，一个深评都不该有。"""
        seen, _urls = self._smuggled()
        user = _cli.pick_user("", root=ROOT)
        hit = ap.requeue_unfounded_gate_fails(user)
        bad = [k for k in hit if (seen.get(k) or {}).get("evaluated")]
        self.assertEqual(bad, [], f"{len(bad)} 个深评被放回了")


if __name__ == "__main__":
    unittest.main()
