# -*- coding: utf-8 -*-
"""「已出材料 N 份」在两处必须是同一个数——而它又飘了。

`doctor.count_materials` 的 docstring 里白纸黑字写着：

    两处都对着同一个概念，却各答各的……谁也不比谁更对，
    但它们**必须说同一个数**。

**写下这句话之后它还是飘了。** 实测活动用户 2026-08-23：

    会话开始的自检   已出材料 155 份
    面板导航条       材料就绪 142

两个原因，都在 `count_materials` 里：

1. **只排了 `skipped`。** 面板走 `build_dashboard.is_parked`（不投 + 已下线 +
   重复挂法）再加判词出局。实测 12 个目录的岗**已经下线** —— 而 `is_parked`
   自己的 docstring 记的就是这 12 个：「催一个关掉的岗去投，比不催更糟」。
2. **按原始字符串比链接。** 同一个岗在两处存 `http://` 与 `https://` 是真实
   发生过的（`_cli.norm_url` 存在的全部理由）。比不上就漏排。

一句「必须说同一个数」拦不住它，所以有了这个文件。

**只剩一类对不齐，而且对不齐是对的：重复挂法。** 面板按「公司 + JD 正文前 300 字」
并行，那要读 `details/` 里几千份正文，而 doctor 是零依赖、只读几个小文件的自检。
所以这里不按相等验，也不按「差额 == 重复挂法数」验（那也是错的：
有的重复挂法同时还被别的理由排掉了）——验的是那句精确的话：
**自检多出来的每一个，都必须是重复挂法。**
"""
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import build_dashboard as B  # noqa: E402
import doctor  # noqa: E402


def _code_only(src: str) -> str:
    """把注释和字符串（含 docstring）剔掉，只留真正的代码。

    「这个名字出现了几次」这类判据，一旦把说明也数进去，就等于禁止解释它。
    见 `test_the_users_of_that_rule_go_through_it` 的说明。
    """
    import io
    import tokenize
    keep = []
    for tok in tokenize.generate_tokens(io.StringIO(src).readline):
        if tok.type in (tokenize.COMMENT, tokenize.STRING):
            continue
        keep.append(tok.string)
    return " ".join(keep)


def _mk(tmp, jobs):
    """按 `jobs`（(链接, status, 判词) 三元组）造一份最小用户目录。"""
    apps = tmp / "documents" / "applications"
    seen = {}
    for i, (url, status, verdict) in enumerate(jobs):
        d = apps / f"示例科技{i}_产品经理"
        d.mkdir(parents=True)
        (d / "outreach.md").write_text(
            f"# 示例\n\n职位链接：{url}\n\n## 打招呼开场白\n\n您好。\n",
            encoding="utf-8")
        seen[f"{url}#岗{i}"] = {"url": url, "status": status,
                               "rank_verdict": verdict}
    return seen


class TheSamePredicateOnBothSides(unittest.TestCase):
    """doctor 的排除口径必须等于面板的 `is_parked` + 判词出局。"""

    CASES = [
        ("ranked", "值得投", True, "普通可投的，两边都算"),
        ("skipped", "值得投", False, "你点了不投"),
        ("expired", "值得投", False, "已下线 —— doctor 原来漏了这一类"),
        ("ranked", "硬门 FAIL (工作年限)", False, "硬门没过"),
        ("ranked", "不满足硬性条件（学历）", False, "深评写法的硬门"),
        ("ranked", "跳过", False, "规则判跳过"),
        ("ranked", "不建议", False, "分太低"),
    ]

    def test_each_state_lands_the_same_way(self):
        import tempfile
        for status, verdict, counted, why in self.CASES:
            with self.subTest(why=why):
                with tempfile.TemporaryDirectory() as td:
                    tmp = Path(td)
                    seen = _mk(tmp, [("https://x/1", status, verdict)])
                    got = doctor.count_materials(tmp, seen)
                    self.assertEqual(got, 1 if counted else 0, why)
                    # 面板那一侧对同一个岗的判断
                    job = {"skipped": status == "skipped",
                           "expired": status == "expired",
                           "dupOf": None}
                    panel = not (B.is_parked(job) or _out(verdict))
                    self.assertEqual(bool(got), panel,
                                     f"两边不一致（{why}）")

    def test_the_scheme_does_not_decide_it(self):
        """台账存 `https://`、库里存 `http://` 是真实发生过的。
        按原始字符串比，这一条就漏排。"""
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            seen = _mk(tmp, [("https://x/1", "skipped", "值得投")])
            # 目录里写 http，库里存 https —— 同一个岗
            d = next((tmp / "documents" / "applications").iterdir())
            (d / "outreach.md").write_text(
                "# 示例\n\n职位链接：http://x/1\n\n## 打招呼开场白\n\n您好。\n",
                encoding="utf-8")
            self.assertEqual(doctor.count_materials(tmp, seen), 0,
                             "只因为协议不同就没排掉")

    def test_a_half_finished_directory_is_not_a_material(self):
        """`/job-apply` 跑一半会留下只有 `posting.md` 的空壳 —— 原有的规矩，
        不许被这次改动顺手弄丢。"""
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            d = tmp / "documents" / "applications" / "示例科技_产品经理"
            d.mkdir(parents=True)
            (d / "posting.md").write_text("x", encoding="utf-8")
            self.assertEqual(doctor.count_materials(tmp, {}), 0)


def _out(verdict: str) -> bool:
    v = (verdict or "").strip()
    return (v.startswith(("硬门 FAIL", "硬门FAIL", "不满足硬性条件"))
            or "跳过" in v or "不建议" in v)


class TheInlinedRuleMatchesItsSource(unittest.TestCase):
    """doctor 不许 import 仓库里的模块，所以判据是内联的副本 ——
    副本就得有人钉着，不然它和正本必然分叉（这个文件就是分叉的产物）。"""

    def _seg(self):
        """`count_materials` 自己的那段（搁置状态、`dupOf` 那几条判据）。"""
        src = (ROOT / "tools" / "doctor.py").read_text(encoding="utf-8")
        i = src.index("def count_materials(")
        return src[i:src.index("\ndef ", i + 10)]

    def _rule(self):
        """判词判「出局」那条规则本身。

        这几个字面量 2026-08-27 从 `count_materials` 的函数体提到了模块级
        `is_out_verdict` —— 因为这个文件里它要用两次（数目录一次、挑「备好没发」
        一次），而 `ready_rows` 的说明立着规矩：「同一段判断在这个文件里
        不许写两遍」。收口是对的，**锚跟着搬**：查字面量去规则那儿查，
        查「谁在用它」用下面那条。
        """
        src = (ROOT / "tools" / "doctor.py").read_text(encoding="utf-8")
        i = src.index("_OUT_PREFIXES = ")
        return src[i:src.index("def _re_strong", i)]

    def test_the_users_of_that_rule_go_through_it(self):
        """提成函数之后，用它的地方必须真的调它 —— 否则等于又抄了一份。

        ⚠️ **只数代码里的，不数注释和 docstring 里的。** 原来这条数的是整份
        文件的 `src.count(...)`，于是**在说明里提一句这个名字就当场红** ——
        2026-09-01 给 `placeholders` 的 docstring 写「按值扫的守卫补上了
        `_OUT_PREFIXES` 这几对」，一句纯散文把它打红了。
        一条让人不敢写说明的守卫，钉的是行数不是行为
        （`test_a_guard_pins_behaviour_not_a_line` 讲的就是这件事）。
        """
        src = (ROOT / "tools" / "doctor.py").read_text(encoding="utf-8")
        self.assertEqual(_code_only(src).count("_OUT_PREFIXES"), 2,
                         "判据被抄成了不止一份")
        for fn in ("def count_materials(", "def ready_rows("):
            i = src.index(fn)
            body = src[i:src.index("\ndef ", i + 10)]
            with self.subTest(fn=fn):
                self.assertIn("is_out_verdict(", body, f"{fn} 没走那条共用判据")

    def test_the_prefixes_match_the_canonical_list(self):
        import _cli
        seg = self._rule()
        for pre in _cli.GATE_FAIL_PREFIXES:
            with self.subTest(prefix=pre):
                self.assertIn(f'"{pre}"', seg, f"内联那份漏了「{pre}」")

    def test_it_covers_the_two_substring_verdicts(self):
        """`is_out_verdict` 除了前缀还认「跳过」「不建议」两个子串。"""
        seg = self._rule()
        for w in ("跳过", "不建议"):
            with self.subTest(w=w):
                self.assertIn(f'"{w}"', seg)

    def test_it_covers_both_parked_states_it_can_see(self):
        seg = self._seg()
        self.assertIn('"skipped", "expired"', seg, "少排了一类搁置")

    def test_it_still_does_not_import_the_repo(self):
        """硬契约：doctor 要能在什么都没配好的机器上单文件裸跑。"""
        src = (ROOT / "tools" / "doctor.py").read_text(encoding="utf-8")
        self.assertNotRegex(src, r"(?m)^\s*(import|from)\s+_cli\b",
                            "doctor 开始 import 仓库模块了")

    def test_the_remaining_gap_is_written_down(self):
        """剩下的差额（重复挂法）是刻意的。不写下来，下一个人会去追它。"""
        self.assertIn("dupOf", self._seg(), "没说清剩下那一类差在哪")


class OnRealDataTheGapIsOnlyDuplicates(unittest.TestCase):
    def test_the_two_numbers_differ_only_by_duplicate_postings(self):
        p = ROOT / ".active_user"
        data = ROOT / "web" / "public" / "data.json"
        if not p.is_file() or not data.is_file():
            self.skipTest("没有活动用户或还没导出面板数据")
        user = p.read_text(encoding="utf-8").strip()
        ud = ROOT / "users" / user
        sj = ud / "job_scraper" / "seen_jobs.json"
        if not sj.is_file():
            self.skipTest("还没抓过职位")
        raw = json.loads(sj.read_text(encoding="utf-8"))
        seen = raw.get("seen", raw)
        try:
            us = json.loads((sj.with_name("user_state.json"))
                            .read_text(encoding="utf-8"))
        except (OSError, ValueError):
            us = {}
        for k, row in us.items():
            if k in seen and row.get("decision"):
                seen[k]["status"] = row["decision"]
        mine = doctor.count_materials(ud, seen)
        snap = json.loads(data.read_text(encoding="utf-8"))
        panel = next(x["count"] for x in snap["pipeline"]
                     if x["label"] == "材料就绪")
        # **按集合验，不按数验。** 「差额 == 重复挂法数」是错的：有的重复挂法
        # 同时还被别的理由排掉了（实测有材料的重复挂法 2 个，而差额只有 1）。
        # 要断言的是那句精确的话 —— **多出来的每一个都必须是重复挂法**。
        import _cli
        panel_urls = {_cli.norm_url(j.get("url") or "") for j in snap["jobs"]
                      if "materials" in (j.get("funnels") or [])}
        dup_urls = {_cli.norm_url(j.get("url") or "") for j in snap["jobs"]
                    if j.get("dupOf")}
        mine_urls = set()
        for d in sorted((ud / "documents" / "applications").iterdir()):
            if not d.is_dir() or not (d / "outreach.md").is_file():
                continue
            m = re.search(r"职位链接\s*[：:]\s*(\S+)",
                          (d / "outreach.md").read_text(encoding="utf-8",
                                                        errors="replace"))
            if not m:
                continue
            k = _cli.norm_url(m.group(1))
            if k in _parked_urls(seen):
                continue
            mine_urls.add(k)
        extra = mine_urls - panel_urls
        self.assertEqual(sorted(extra - dup_urls), [],
                         f"自检 {mine}、面板 {panel}，多出来的不是重复挂法：{extra}")
        self.assertLessEqual(mine - panel, len(dup_urls),
                             "差额比重复挂法总数还大")


def _parked_urls(seen):
    import _cli
    out = set()
    for e in seen.values():
        if not isinstance(e, dict):
            continue
        v = str(e.get("rank_verdict") or "").strip()
        if e.get("status") in ("skipped", "expired") or _out(v):
            out.add(_cli.norm_url(e.get("url") or ""))
    out.discard("")
    return out


if __name__ == "__main__":
    unittest.main()


class ReadyRowsDropsWhatTheVerdictThrewOut(unittest.TestCase):
    """「备好没发」也要排掉判词出局的岗 —— 否则自检会催你去投一个判了不投的。

    2026-08-27 实测：自检说「这 65 份材料放了中位 16 天……先发排得最久的那几个」，
    面板说 64。多出来的那一个判词是「跳过」。

    `is_out_verdict` 的说明里记着同一形状：「一个岗材料做完之后判词才降到
    『跳过』……页面一边把它算作出局、一边在详情里催『材料就绪，快去投』」。
    那次修的是 `job_next_step`，**`ready_rows` 这边漏了**。

    ## 字段缺席时要退回粗口径

    `ready_rows` 的原设计是「兜底口径，比正本松……宁可多说一个，也不要让一个
    真备好的岗从『下一步』里静默消失」。那条取舍针对的是**老快照没有那些字段**
    的情形，没有被这次改动推翻：`verdict` 不在时 `is_out_verdict("")` 返回 False，
    自动回到粗口径。
    """

    ROWS = [
        {"id": "a", "materials": {"greeting": "x"}, "verdict": "值得投"},
        {"id": "b", "materials": {"greeting": "x"}, "verdict": "跳过"},
        {"id": "c", "materials": {"greeting": "x"}, "verdict": "粗筛：不建议"},
        {"id": "d", "materials": {"greeting": "x"},
         "verdict": "不满足硬性条件（学历）"},
        {"id": "e", "materials": {"greeting": "x"}},          # 老快照：没有这个字段
    ]

    def test_an_out_verdict_is_not_ready_to_send(self):
        got = {j["id"] for j in doctor.ready_rows(self.ROWS)}
        self.assertEqual(got, {"a", "e"},
                         "判词出局的岗被算进了「备好没发」——"
                         "自检会催用户去投一个框架判了不投的岗")

    def test_a_snapshot_without_the_field_falls_back_to_coarse(self):
        """老快照没有 `verdict` 时不许把它当成「出局」而漏掉。"""
        self.assertIn("e", {j["id"] for j in doctor.ready_rows(self.ROWS)},
                      "字段缺席被当成了出局 —— 那会让真备好的岗静默消失")

    def test_it_agrees_with_the_panel_on_real_data(self):
        data = ROOT / "web" / "public" / "data.json"
        if not data.is_file():
            self.skipTest("还没导出面板数据")
        d = json.loads(data.read_text(encoding="utf-8"))
        jobs = d.get("jobs") or []
        panel = sum(1 for j in jobs if "ready" in (j.get("funnels") or []))
        if not panel:
            self.skipTest("现在一个「备好没发」都没有 —— 对不出来")
        self.assertEqual(len(doctor.ready_rows(jobs)), panel,
                         "自检与面板对「备好没发」又给出了两个数")
