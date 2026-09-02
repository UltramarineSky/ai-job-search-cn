# -*- coding: utf-8 -*-
"""还能动的那一行，必须说得出该敲什么 —— 而这件事只有散文在管。

`AGENTS.md`「每一处引导都要写出该敲的命令」把面板逐岗那一行点了名：

> 面板上用命令块（`<Cmd>`），一眼看得出那是要敲的东西，还能点着复制。

而逐岗那一行的「下一步」是导出侧算的（`build_dashboard.job_next_step` →
`nextStep = {text, command}`），`JobReadout` 只负责渲染。**算不出来时它整行
不渲染** —— 那对已结案的岗是对的（入职、挂了、已下线都没有下一步），
对一个还投得出去的岗就是把它晾在那儿。

## 已有的守卫管的是另一件事

`test_every_job_lands_somewhere` 钉的是「每个岗都落在某一份名单里，
没有岗从页面上凭空消失」。一个岗完全可以**落在「可以投的岗位」里、
而那一行什么也不说** —— 两条缝不重叠。

## 判据

「还能动」= 不是重复挂法、没标不投、没下线、还没投出去，且判词是正面的。
现算 2026-08-31：这样的岗**每一个都有 `nextStep`，每一个都带命令**
（`/job-apply` 206 个、`/job-outcome` 174 个），一个例外都没有。
这条守的是那一天。

命令还要是真存在的那几条 —— 面板上印一条敲不动的命令，比不印更坏
（同 `test_every_printed_command_runs` 的理由，只是那条扫的是源码里的
字面量，够不着这一层：这些命令是**算出来的**）。

依赖真实数据（`data.json` 不进版本库），CI 上会跳过。
"""
import json
import pathlib
import re
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import _cli  # noqa: E402

#: 正面判词 —— 这几档意味着「还可以往下走」。
#:
#: **切片，不另抄一份。** 五档的正本是 `_cli.VERDICTS`（倒序排好的），
#: 前三档就是「还能往下走」的那几个。第一版把它们逐字写了一遍，
#: `test_shared_vocab_single_source` 当场拦下 —— 抄一份，档序改了这里不会跟。
LIVE_VERDICTS = _cli.VERDICTS[:3]


def _live(jobs: list) -> list:
    out = []
    for j in jobs:
        if j.get("dupOf") or j.get("skipDate") or j.get("expiredDate"):
            continue
        if "applied" in (j.get("funnels") or []):
            continue
        if not any(v in (j.get("verdict") or "") for v in LIVE_VERDICTS):
            continue
        out.append(j)
    return out


class EveryLiveRowSaysWhatToType(unittest.TestCase):

    def setUp(self):
        p = ROOT / "web" / "public" / "data.json"
        if not p.is_file():
            self.skipTest("还没导出过面板数据 —— 这条这次什么都没验，不是通过")
        self.jobs = json.loads(p.read_text(encoding="utf-8"))["jobs"]

    def test_the_scan_sees_enough_rows(self):
        """尺子先证明自己会亮：一个「还能动」的岗都挑不出来时，下面全是空跑。"""
        self.assertGreater(len(_live(self.jobs)), 20,
                           f"只挑出 {len(_live(self.jobs))} 个 —— 筛法多半失配了")

    def test_the_filter_really_excludes_the_closed_ones(self):
        """判据自检：已投 / 不投 / 已下线 / 重复挂法确实被排掉了。"""
        live = {id(j) for j in _live(self.jobs)}
        for key in ("skipDate", "expiredDate", "dupOf"):
            got = [j for j in self.jobs if j.get(key) and id(j) in live]
            with self.subTest(key):
                self.assertEqual(got, [], f"{key} 的岗没被排掉")
        # **已投的那一档单列。** 它不是一个字段而是漏斗里的一格，
        # 上面那个循环够不着；漏掉它时红的是别的断言（变异照出来的），
        # 而一条自检该自己红。
        got = [j for j in self.jobs
               if "applied" in (j.get("funnels") or []) and id(j) in live]
        self.assertEqual(got, [], "已经投出去的岗没被排掉")

    def test_every_live_row_has_a_next_step(self):
        bad = [f"{str(j.get('title'))[:20]}（{j.get('verdict')}）"
               for j in _live(self.jobs) if not j.get("nextStep")]
        self.assertEqual(
            bad, [],
            f"{len(bad)} 个还投得出去的岗，那一行什么也不说 —— "
            "`JobReadout` 算不出下一步时整行不渲染：\n  " + "\n  ".join(bad[:8]))

    def test_every_next_step_carries_a_command(self):
        """说了「下一步」却不说敲什么，等于把他晾在那儿（`AGENTS.md` 那条）。"""
        bad = []
        for j in _live(self.jobs):
            ns = j.get("nextStep") or {}
            if not (ns.get("command") or "").strip():
                bad.append(f"{str(j.get('title'))[:20]}：{(ns.get('text') or '')[:30]}")
        self.assertEqual(bad, [], "\n  " + "\n  ".join(bad[:8]))

    def test_the_commands_are_real(self):
        """算出来的命令也得真存在 —— 印一条敲不动的比不印更坏。

        `test_every_printed_command_runs` 扫的是源码里的字面量，够不着这一层：
        这些命令是逐岗算出来的，源码里只有 `f"/job-apply {url}"` 那个模板。
        """
        have = {f"/{p.stem}" for p in (ROOT / "workflows").glob("job-*.md")}
        bad = set()
        for j in self.jobs:
            cmd = ((j.get("nextStep") or {}).get("command") or "").strip()
            if not cmd:
                continue
            head = re.split(r"\s", cmd)[0]
            if head.startswith("/") and head not in have:
                bad.add(head)
        self.assertEqual(sorted(bad), [], f"逐岗下一步指向不存在的命令：{bad}")

    def test_the_detector_can_fail(self):
        """判据自检：造一个没有下一步的正面岗，筛法必须挑得出来。"""
        fake = [{"title": "x", "verdict": "值得投", "funnels": []}]
        self.assertEqual(len(_live(fake)), 1)
        self.assertFalse(fake[0].get("nextStep"))


if __name__ == "__main__":
    unittest.main()
