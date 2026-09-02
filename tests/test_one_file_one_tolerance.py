# -*- coding: utf-8 -*-
"""同一个文件，各工具的宽容度必须一致；派生快照的写法也只留一种。

代码审查（2026-08-18）报出来的一组同形缺陷：**A 处考虑了的边界，B 处没考虑**，
而 A 的注释里往往还写着「B 也是这么做的」。逐条：

| 文件 | 谁宽容 | 谁不宽容 | 后果 |
|---|---|---|---|
| `seen_jobs.json` 老格式 | `export_web_data` / `writeback` | `serve` / `prescreen` / `jd_store` / `fetch_details` | 点「不投」是 500，命令行是 traceback |
| 台账 CSV 非 UTF-8 | `build_dashboard.load_tracker` | `export_web_data` 内联的 DictReader | Excel 存一次，整个面板空掉 |
| `data.json` 原子写 | `_cli.atomic_write` | `export_web_data` 自拼的固定 .tmp | 并发导出撞名；Windows 上读句柄让 replace 抛 |

外加两条「判据跟注释说的相反 / 不全」：`parse_dimensions` 撞列时丢的是分数不是
权重；`serve.sources_mtime` 漏了导出真正会读的几个上游。
"""
import json
import re
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parent.parent

#: 读冷库（`archive.json`）那一行的局部变量名。整词匹配——
#: 裸的 `"arc" in l` 会把每一行带 `search` 的也一起放过去。
_ARC = re.compile(r"\barc\b")
sys.path.insert(0, str(ROOT / "tools"))
import _cli  # noqa: E402
import export_web_data as ex  # noqa: E402
import serve  # noqa: E402

ENTRY = {"url": "https://x/1", "title": "岗A", "company": "甲公司",
         "status": "ranked", "rank_score": 80, "rank_verdict": "强匹配"}


class TheLegacyStoreShapeIsToleratedEverywhere(unittest.TestCase):

    def test_the_scan_reaches_the_tools(self):
        """对照用例：扫描真的够到了文件 —— 否则同文件里那些「没问题」是恒绿的。

        2026-08-20 实测：把 `Path.glob`/`rglob` 打成空之后本文件全绿。
        **扫不到文件时，「没有问题」和「没有检查」长得一模一样。**

        这不是假想——这个仓库真搬过目录（工作流正文从 `.claude/skills/` 搬到
        `workflows/`，`AGENTS.md` 里记着）。glob 还指着旧路径时，守卫会安静地失效。
        """
        found = list((ROOT / "tools").glob("*.py"))
        self.assertGreaterEqual(
            len(found), 12,
            f"只扫到 {len(found)} 个工具脚本 —— 判据大概是够不到文件了，"
            "而不是仓库真的只剩这么几个")

    def test_helper_accepts_both_shapes(self):
        self.assertEqual(_cli.seen_of({"seen": {"k": ENTRY}}), {"k": ENTRY})
        self.assertEqual(_cli.seen_of({"k": ENTRY}), {"k": ENTRY})
        self.assertEqual(_cli.seen_of([]), {})

    def test_it_returns_a_live_reference(self):
        """就地改完写回外层仍然对——两种格式下都是。"""
        for store in ({"seen": {"k": dict(ENTRY)}}, {"k": dict(ENTRY)}):
            with self.subTest(shape=list(store)[0]):
                _cli.seen_of(store)["k"]["status"] = "skipped"
                self.assertEqual(_cli.seen_of(store)["k"]["status"], "skipped")

    #: 不宽容老格式的两种写法。
    #:
    #: 第一版**只抓裸 `["seen"]`**，于是 `.get("seen", {})` 这一族整个漏过去——
    #: 2026-08-21 实测同一天抓到两处，判据都给了绿灯：
    #:
    #: - `doctor.py`：`.get("seen", {})` → 老库上**静默报「已抓 0 个职位」**，
    #:   并把下一步指成 `/job-scrape`（它是每个会话的第一条命令、新用户的第一屏）；
    #: - `build_dashboard.py`：`.get("seen") or {}` → 老库上报「里面没有职位」，
    #:   比静默响，但同样是错的。
    #:
    #: **裸 KeyError 至少会炸；`.get` 那一族给你一个空字典，然后一路往下走。**
    #: 后者更该抓，而它恰恰是原判据看不见的那半边。
    BAD_SHAPES = ('["seen"]', '.get("seen", {})', '.get("seen") or',
                  ".get('seen', {})", ".get('seen') or", '.get("seen", None)')

    def test_no_tool_reads_seen_the_unforgiving_way(self):
        """两种不宽容的写法都要抓：裸 `["seen"]` 与 `.get("seen", {})` 一族。

        允许的写法只有两种：走 `_cli.seen_of`，或者内联同样的回退
        （`raw.get("seen", raw)` —— `doctor.py` 的硬契约是不许 import 本仓库模块，
        所以它只能内联）。
        """
        import ast as _ast

        bad = []
        for p in sorted((ROOT / "tools").glob("*.py")):
            src = p.read_text(encoding="utf-8")
            lines = src.splitlines()
            tree = _ast.parse(src)
            # **按函数取段**：只管「这一段里也提到 seen_jobs.json」的地方。
            # 不收窄的话 `archive.py` / `query_yield.py` 读 `archive.json`
            # 的那两处会被误报——那个文件是本仓库自己写的，形状固定，
            # `.get("seen", {})` 在那里是对的。
            segs = []
            for n in _ast.walk(tree):
                if isinstance(n, (_ast.FunctionDef, _ast.AsyncFunctionDef)):
                    segs.append((n.lineno, n.end_lineno))
            for lo, hi in segs:
                seg = lines[lo - 1:hi]
                if not any("seen_jobs.json" in x for x in seg):
                    continue
                for off, l in enumerate(seg):
                    if l.strip().startswith(("#", "`", '"', "'")):
                        continue
                    if "seen_of" in l:
                        continue
                    # 同一个函数里可能既读 `seen_jobs.json` 又读 `archive.json`
                    # （`query_yield` 就是），按函数取段分不开——所以这一行读的是
                    # 冷库时跳过。冷库是本仓库自己写的，形状固定。
                    #
                    # **`"arc" in l` 太宽**：它同时放过了每一行带 `search` 的
                    # （s-e-**a-r-c**-h），而 `job-search`、`search-queries`、
                    # `liepin-search` 在这些文件里到处都是。
                    # 要认的是 `query_yield.py` 里那个叫 `arc` 的**变量**
                    # （`arc.read_text(...)`，那一行整行没有 archive 这个词），
                    # 所以按整词匹配——`search` 里的 arc 前面是字母，够不着词边界。
                    if _ARC.search(l) or "archive" in l:
                        continue
                    if any(shape in l for shape in self.BAD_SHAPES):
                        bad.append(f"{p.name}:{lo + off}: {l.strip()[:80]}")
        # **裸 `["seen"]` 那一半仍然全文件扫。**
        #
        # 上一版是整个 `tools/*.py` 逐行扫 `["seen"]`，这一版为了能同时抓
        # `.get("seen", {})` 一族（那族会误伤读冷库的地方）改成了「按函数取段、
        # 只看同段里提到 `seen_jobs.json` 的」——判据宽了一类，**扫的面却窄了一大截**：
        # 实测 serve.py 只剩 3/26 个函数在扫描内，export_web_data.py 只剩 1/52。
        # 而 `_cli.seen_of` 的说明点名的历史惯犯（`serve` 的取条目那几个函数）
        # 恰恰都不在里面——它们通过 `seen_path(user)` 拿路径，段里根本不出现
        # 那个字面量。裸 `["seen"]` 在冷库上不成立（`archive.json` 里没有这个键），
        # 所以那一半本来就没有误伤问题，全文件扫回来，一寸都不让。
        for p in sorted((ROOT / "tools").glob("*.py")):
            for i, l in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
                if l.strip().startswith(("#", "`", '"', "'")):
                    continue
                if '["seen"]' in l and "seen_of" not in l:
                    hit = f"{p.name}:{i}: {l.strip()[:80]}"
                    if hit not in bad:
                        bad.append(hit)
        self.assertEqual(
            bad, [],
            "这些地方读不了老格式的库：裸 `[\"seen\"]` 会 KeyError，"
            "`.get(\"seen\", {})` 更坏——它给你一个空字典，然后一路往下走，"
            "报出来的是「里面没有职位」：\n  " + "\n  ".join(bad))

    def test_the_archive_file_is_not_flagged(self):
        """`archive.json` 是本仓库自己写的，形状固定 —— 那里 `.get("seen", {})` 是对的。

        判据按**函数**取段、只管同段里提到 `seen_jobs.json` 的地方，
        就是为了不误伤 `archive.py` / `_cli.archived` 读冷库的那两行。
        第一版没收窄，当场把它们报成缺陷。

        ⚠️ **`query_yield.py` 2026-08-30 起不在这张名单里了。** 它改走
        `_cli.archived` —— 读文件、解析、兜住坏文件那三步原来在两个文件里
        各有一份，收口到了 `_cli`。豁免跟着搬：这条测试自己就写着
        「不再读了？这条豁免该重看」，那正是这次发生的事。
        """
        for name, needle in (("archive.py", "archive.json"),
                             ("_cli.py", "archive.json")):
            f = ROOT / "tools" / name
            if not f.is_file():
                continue
            with self.subTest(name=name):
                self.assertIn(needle, f.read_text(encoding="utf-8"),
                              f"{name} 不再读 {needle} 了？这条豁免该重看")

    def test_the_inline_fallback_is_accepted(self):
        """`doctor.py` 只能内联那份回退（它不许 import 本仓库模块）—— 不该被误报。"""
        t = (ROOT / "tools" / "doctor.py").read_text(encoding="utf-8")
        self.assertIn('.get("seen", _raw)', t,
                      "doctor 的两代格式回退不见了 —— 老库上它会静默报 0 个职位")

    def test_the_widened_check_can_fire(self):
        """变异内建：`.get("seen", {})` 这一族必须被认出来。"""
        for shape in ('data.get("seen", {})', 'data.get("seen") or {}',
                      'store["seen"]'):
            with self.subTest(shape=shape):
                self.assertTrue(any(b in shape for b in self.BAD_SHAPES),
                                f"这种写法没被认出来：{shape}")
        for ok in ('_cli.seen_of(data)', 'raw.get("seen", raw)'):
            with self.subTest(ok=ok):
                self.assertFalse(
                    any(b in ok for b in self.BAD_SHAPES) and "seen_of" not in ok,
                    f"正确写法被误报：{ok}")

    def test_skipping_works_on_a_legacy_store(self):
        with TemporaryDirectory() as d:
            p = Path(d) / "seen_jobs.json"
            p.write_text(json.dumps({"https://x/1": dict(ENTRY)}),
                         encoding="utf-8")
            orig_user, orig_path = serve.active_user, serve.seen_path
            serve.active_user = lambda: "谁"
            serve.seen_path = lambda user: p
            try:
                jid = ex.stable_id(ENTRY["url"], ENTRY["title"])
                out = serve.apply_skip(jid, "试试")
            finally:
                serve.active_user, serve.seen_path = orig_user, orig_path
            self.assertTrue(out.get("ok"), f"老格式库上标不了不投：{out.get('error')}")
            # 状态在叠加层里（2026-08-19 拆出去的），老格式库照样能标
            import _cli
            st = _cli.load_user_state(p)
            entry = json.loads(p.read_text(encoding="utf-8"))["https://x/1"]
            self.assertEqual(_cli.decided_status(entry, st.get("https://x/1")), "skipped")


class TheTrackerIsReadTheRobustWay(unittest.TestCase):

    def test_export_uses_load_tracker(self):
        src = (ROOT / "tools" / "export_web_data.py").read_text(encoding="utf-8")
        self.assertIn("load_tracker(tracker)", src)
        self.assertNotIn("import csv as _csv", src,
                         "又内联了一份 DictReader——那份没有编码兜底")

    def test_a_non_utf8_csv_does_not_kill_the_run(self):
        import build_dashboard as bd
        with TemporaryDirectory() as d:
            p = Path(d) / "t.csv"
            p.write_bytes("date,company,role\n2026-08-01,甲公司,岗A\n"
                          .encode("gbk"))
            self.assertEqual(bd.load_tracker(p), [],
                             "非 UTF-8 台账该降级为空，而不是抛栈")


class DimensionScoresSurviveAColumnClash(unittest.TestCase):

    TEXT = ("## 四维评分\n\n"
            "| 维度 | 权重分 | 依据 |\n|---|---|---|\n"
            "| 技能匹配 | 8 | 对口 |\n| 薪资 | 6 | 略低 |\n")

    def test_the_score_is_kept_not_the_weight(self):
        dims = ex.parse_dimensions(self.TEXT)
        self.assertTrue(dims, "一个维度都没解析出来")
        scores = [d.get("score") for d in dims]
        self.assertEqual(scores, [8, 6],
                         f"撞列时把分数丢了（拿到 {scores}）——面板上四维会全掉进"
                         "「要掂量的地方」，技能列显示「—」")


class DerivedSnapshotsAreWrittenAtomically(unittest.TestCase):

    def test_export_uses_the_shared_atomic_write(self):
        src = (ROOT / "tools" / "export_web_data.py").read_text(encoding="utf-8")
        self.assertIn("_cli.atomic_write(out,", src)
        self.assertNotIn('out.with_suffix(".json.tmp")', src,
                         "又自拼了一个固定名 .tmp：并发导出会撞同一个名字")


class TheRefreshTriggerCoversWhatTheExportReads(unittest.TestCase):

    def test_sources_mtime_watches_the_resume_and_the_detail_store(self):
        src = (ROOT / "tools" / "serve.py").read_text(encoding="utf-8")
        # **按结构切到函数末尾，不按字符数。** 原来是 `i + 1600`：
        # 2026-08-24 往那张单子里加了一个写入源（`resume_refresh.json`）连同
        # 六行注释，`"details"` / `"reports"` 就被挤到窗口外，两条子断言当场落空。
        # 而它们要验的东西一个字没动 —— 本仓库为「窗口靠数字符」栽过好几次。
        i = src.index("def sources_mtime")
        seg = src[i:src.index(chr(10) + "def ", i + 10)]
        for needed in ('"main.typ"', '"main.pdf"', '"details"', '"reports"'):
            with self.subTest(needed=needed):
                self.assertIn(needed, seg,
                              f"{needed} 不在刷新判据里——改了它页面不会更新，"
                              "而模块说明写着「刷新页面即最新」")


if __name__ == "__main__":
    unittest.main()
