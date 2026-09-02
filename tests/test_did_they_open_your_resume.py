# -*- coding: utf-8 -*-
"""平台白给的那一个字，此前无处可落——查一次，忘一次。

国内平台在「投递记录 / 我的投递」里**逐条标着简历有没有被打开**（猎聘、智联写
「已查看 / 未查看」，BOSS 看那条会话对面点没点开）。它把「投了没回音」拆成两件
后果完全相反的事，`job-outcome.md` Step 2b 那张表早就写清楚了：

    大多已查看、还是没回  → HR 打开了看完没往下走，这才轮到审简历
    大多未查看            → 简历根本没被打开，**改简历没用**

而这条判据**只写在那一个工作流里**：它让用户去平台看一眼，然后那个答案没有任何
地方能记下来。实测 2026-08-24 全库搜「已查看 / 未查看 / viewed」——只有
`job-outcome.md` 那三行，没有任何字段、按钮、统计或诊断读它。

后果：面板与自检的下一步**永远停在「先催一遍」**，「要不要审简历」这个问题
一次都没被回答过。而它恰好是这个用户流水线上最大的那个问题（85 投、0 回音）。

## 这一条要成立，四样东西缺一不可

- **存**：`user_state.json` 里 `hr_viewed`（和 `decision` 同行不同键）
- **写**：面板上每个投过的岗两个按钮 → `/api/hr-viewed`
- **算**：只在企业直招那组统计（猎头那组的「已查看」是顾问看了，不是用人方）
- **用**：面板与自检的零回音分支读它

## 三态，不是布尔

`None`（还没查过）和 `False`（查过、没打开）的结论正好相反。一路上任何一层把它
折成布尔值，都会把「我还没去看」变成「对方没看」——凭空造出一个诊断。
"""
import json
import pathlib
import re
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import _cli  # noqa: E402
import build_dashboard as bd  # noqa: E402
import doctor  # noqa: E402

BD = (ROOT / "tools" / "build_dashboard.py").read_text(encoding="utf-8")
DR = (ROOT / "tools" / "doctor.py").read_text(encoding="utf-8")
EX = (ROOT / "tools" / "export_web_data.py").read_text(encoding="utf-8")
SRV = (ROOT / "tools" / "serve.py").read_text(encoding="utf-8")
CLI = (ROOT / "tools" / "_cli.py").read_text(encoding="utf-8")
JR = (ROOT / "web" / "src" / "components"
      / "JobReadout.tsx").read_text(encoding="utf-8")
API = (ROOT / "web" / "src" / "data" / "excluded.ts").read_text(encoding="utf-8")
TYPES = (ROOT / "web" / "src" / "types.ts").read_text(encoding="utf-8")
OUTCOME = (ROOT / "workflows" / "job-outcome.md").read_text(encoding="utf-8")


def flat(s: str) -> str:
    s = " ".join(re.sub(r"^\s*(?:>|#:?|//:?|\*)\s?", "", s, flags=re.M).split())
    return re.sub(r"(?<=[一-鿿，。；：、（）「」])"
                  r" +(?=[一-鿿，。；：、（）「」])", "", s)


class TheFlagLandsOnDisk(unittest.TestCase):
    def _tmp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        sp = pathlib.Path(t.name) / "seen_jobs.json"
        sp.write_text("{}", encoding="utf-8")
        return sp

    def test_it_writes_true_and_false_and_a_date(self):
        sp = self._tmp()
        _cli.set_hr_viewed(sp, "k", False)
        row = _cli.load_user_state(sp)["k"]
        self.assertIs(row["hr_viewed"], False)
        self.assertRegex(row["hr_viewed_date"], r"^\d{4}-\d{2}-\d{2}$")

    def test_none_clears_it(self):
        sp = self._tmp()
        _cli.set_hr_viewed(sp, "k", True)
        _cli.set_hr_viewed(sp, "k", None)
        self.assertNotIn("k", _cli.load_user_state(sp))

    def test_it_coexists_with_a_decision(self):
        """一个岗可以既「对方没点开」又被标「不投」——两件事互不覆盖。"""
        sp = self._tmp()
        _cli.set_hr_viewed(sp, "k", False)
        _cli.set_user_decision(sp, "k", "skipped", reason="不想投")
        row = _cli.load_user_state(sp)["k"]
        self.assertIs(row["hr_viewed"], False)
        self.assertEqual(row["decision"], "skipped")

    def test_undoing_a_decision_keeps_the_flag(self):
        """「放回可以投」不该顺手把这条观察也抹掉。

        `set_user_decision(..., None)` 原来是整行 `pop` —— 那会连着删。
        """
        sp = self._tmp()
        _cli.set_hr_viewed(sp, "k", True)
        _cli.set_user_decision(sp, "k", "skipped")
        _cli.set_user_decision(sp, "k", None)
        self.assertEqual(_cli.load_user_state(sp)["k"].get("hr_viewed"), True)

    def test_undoing_the_last_thing_removes_the_row(self):
        """两样都撤了就别留一个空壳。"""
        sp = self._tmp()
        _cli.set_user_decision(sp, "k", "skipped")
        _cli.set_user_decision(sp, "k", None)
        self.assertEqual(_cli.load_user_state(sp), {})

    def test_a_decision_write_is_a_merge_not_a_replace(self):
        """钉住这条：整行替换回来，上面那两条就都塌了。"""
        i = CLI.index("def set_user_decision(")
        seg = CLI[i:CLI.index("def set_hr_viewed(", i)]
        self.assertIn("row.update(", seg)
        self.assertNotIn('st[key] = {"decision": decision', seg)


class ThePanelCanRecordIt(unittest.TestCase):
    def test_the_endpoint_exists(self):
        self.assertIn('path == "/api/hr-viewed"', SRV)
        self.assertIn("def apply_hr_viewed(", SRV)
        self.assertIn('"/api/hr-viewed": "记简历看没看"', SRV)

    def test_the_endpoint_keeps_three_states(self):
        """`bool(body.get("viewed"))` 会把撤销变成「没看过」——两者结论相反。"""
        i = SRV.index('path == "/api/hr-viewed"')
        seg = SRV[i:i + 700]
        self.assertIn("None if _v is None else bool(_v)", seg)

    def test_it_writes_under_the_same_lock(self):
        i = SRV.index('path == "/api/hr-viewed"')
        self.assertLess(SRV.index("with _WRITE_LOCK:"), i)

    def test_it_needs_a_job_id(self):
        """它是针对某一次投递的观察，没有 id 就无从落。"""
        i = SRV.index("if not job_id and path not in")
        self.assertNotIn("/api/hr-viewed", SRV[i:i + 260])

    def test_the_client_keeps_three_states_too(self):
        self.assertIn("export function postHrViewed(id: string, "
                      "viewed: boolean | null)", API)

    def test_the_buttons_are_on_applied_jobs_only(self):
        i = JR.index('className="act-group act-viewed"')
        self.assertIn("job.applied && hasServer() && !marked", JR[max(0, i - 300):i])

    def test_the_buttons_are_a_toggle(self):
        """再点一下要能撤销 —— 标错了没有退路，用户就不敢标第一下。"""
        i = JR.index('className="act-group act-viewed"')
        seg = JR[i:i + 900]
        self.assertIn("markViewed(viewed === v ? null : v)", seg)

    def test_the_optimistic_update_rolls_back(self):
        i = JR.index("async function markViewed(")
        seg = JR[i:i + 700]
        self.assertIn("setViewed(was)", seg)

    def test_the_type_says_three_states(self):
        i = TYPES.index("hrViewed?: boolean;")
        seg = flat(TYPES[max(0, i - 900):i])
        self.assertRegex(seg, r"`undefined` 和 `false` 不是一回事")


class TheCountOnlyUsesDirectEmployers(unittest.TestCase):
    def test_the_export_splits_it(self):
        self.assertIn('"viewedDirect": viewed[0],', EX)
        self.assertIn('"unviewedDirect": viewed[1],', EX)

    def test_it_is_counted_inside_the_direct_branch(self):
        """猎头那组的「已查看」是顾问看了，不是用人方看了。"""
        i = EX.index('hv = j.get("hrViewed")')
        seg = EX[max(0, i - 400):i]
        self.assertIn("direct[0] += 1", seg)

    def test_unmarked_ones_enter_neither_side(self):
        i = EX.index('hv = j.get("hrViewed")')
        seg = EX[i:i + 260]
        self.assertIn("if hv is True:", seg)
        self.assertIn("elif hv is False:", seg)

    def test_the_field_reaches_each_job(self):
        self.assertIn('"hrViewed": ustate[k]["hr_viewed"]', EX)

    def test_counts_are_handed_to_the_panel(self):
        self.assertIn('counts["viewed_direct"] = ostats.get("viewedDirect", 0)', EX)
        self.assertIn('counts["unviewed_direct"] = '
                      'ostats.get("unviewedDirect", 0)', EX)

    def test_the_selfcheck_collects_it(self):
        self.assertIn('st["unviewed_direct"] = n_unviewed', DR)
        self.assertIn('_e["hr_viewed"] = _row["hr_viewed"]', DR)


BASE = {"applied": 85, "ready": 62, "ready_strong": 4, "interviewing": 0,
        "ranked": 300, "replied": 0, "decided": 76, "applied_months": [],
        "direct_decided": 33, "direct_replied": 0}


def panel(**over):
    c = dict(BASE); c.update(over)
    return bd.next_step(c, True, top_ranked_url="u", n_sellable=9)[0]


def selfcheck(**over):
    st = {"in_repo": True, "user": "u", "gaps": {}, "scraped": 500,
          "ranked": 300, "materials": 60, "offers": 0, **BASE}
    st.update(over)
    return "\n".join(doctor.next_step({"node": True, "web_build": True}, st))




class TheReasonIsRecordedOnce(unittest.TestCase):
    def test_the_original_carries_the_why(self):
        i = BD.index("VIEWED_BAD_SHARE = ")
        seg = flat(BD[max(0, i - 1600):i])
        self.assertRegex(seg, r"只写在那一个工作流里")
        self.assertRegex(seg, r"查一次忘一次")
        self.assertIn("2026-08-24", seg)
        self.assertRegex(seg, r"猎头那组的「已查看」是顾问看了")

    def test_the_copy_is_gone(self):
        """`doctor.py` 里那份抄件删了 —— 它服务的那一支已经撤了。

        这条原来钉的是「抄件必须指回正本」。2026-08-29 撤掉「零回音 → 先催一遍」
        之后（`AGENTS.md`「跟进归用户，工具不催」），抄件连一个读者都没有 ——
        **一个没人读的抄件，指得再准也只是多一处会飘的定义。**
        判据从「指对了没有」换成「还在不在」。
        """
        self.assertNotIn("VIEWED_BAD_SHARE = ", DR)
        self.assertNotIn("CHAT_FIRST_SHARE = ", DR)

    def test_the_workflow_points_at_the_button(self):
        """那张表原来只说「去平台看一眼」，看完无处可落。"""
        i = OUTCOME.index("大多**未查看**")
        seg = flat(OUTCOME[i:i + 1400])
        self.assertRegex(seg, r"对方点开简历了吗")
        self.assertRegex(seg, r"没标过 ≠ 没打开")


if __name__ == "__main__":
    unittest.main()
