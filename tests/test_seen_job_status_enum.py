"""`seen_jobs.json` 的 `status` 只有四个取值，`evaluated` 不在其中。

## `evaluated` 被写进了 status 枚举

`scrape.md` 的 schema 原来写着：

    "status": "new/skipped/evaluated/ranked/expired",

可 `evaluated` 是 `/job-apply` 深评之后写的**布尔字段**（`"evaluated": true`），
那时 `status` 仍然是 `"ranked"`——`rank.md` 说得很清楚：「届时前缀去掉、
改标 `"evaluated": true`」。

照 schema 真写出 `"status": "evaluated"` 的岗会从**每个视图里消失**：

- `/job-rank` 只挑 `new`，不会再评它
- 面板与 `gap_split` 都只统计 `ranked`，它不在任何一格里
- `n_parked` / `n_processed` 也数不到它

而且**全程不报错**。实测这份真实数据里 268 个条目的 status 只有
`ranked` / `skipped` / `new` / `expired` 四种，`evaluated` 一次都没出现过——
说明执行时没照着这份 schema 写，schema 一直是错的却没人发现。

## 判据

`scrape.md` 里那行 status 枚举的取值，必须与代码真正分支的那几个一致；
`evaluated` 不许出现在里面。
"""

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRAPE = ROOT / "workflows" / "job-scrape.md"

#: `seen_jobs.json` 的合法 status。**代码分支的就是这四个**，控制用例会核对。
#:
#: 不含 `evaluated`（布尔字段）、不含 `deprioritized`（也是独立字段，
#: 降权的岗 status 仍是 `new`——见 `prescreen.py` 与 `n_parked`）、
#: 不含 `blocked`（`rank.md` 明确：通道受限的岗保持 `new`）。
STATUSES = ("new", "skipped", "ranked", "expired")

#: 这几个是**字段**，不是 status 取值。混进枚举就是静默故障。
NOT_STATUSES = ("evaluated", "deprioritized", "blocked")


def schema_statuses() -> list:
    """`scrape.md` schema 里那行 status 的取值。"""
    m = re.search(r'"status":\s*"([^"]+)"', SCRAPE.read_text(encoding="utf-8"))
    if not m:
        return []
    return [x.strip() for x in re.split(r"[/|]", m.group(1)) if x.strip()]


class StatusEnumMatchesWhatTheCodeBranchesOn(unittest.TestCase):

    def test_the_schema_line_is_found(self):
        """控制用例：真抽到了那行枚举。"""
        self.assertTrue(
            schema_statuses(),
            "scrape.md 的 schema 里找不到 `\"status\": \"…\"` 那行了")

    def test_the_code_really_branches_on_these(self):
        """控制用例：这四个确实是代码认的，否则本测试拦的是我编的规则。"""
        blob = "\n".join(p.read_text(encoding="utf-8")
                         for p in (ROOT / "tools").glob("*.py"))
        for s in STATUSES:
            with self.subTest(status=s):
                self.assertIn(f'"{s}"', blob,
                              f"tools/ 里没有任何代码提到 `{s}`——它还是合法状态吗？")

    def test_schema_lists_exactly_the_valid_statuses(self):
        self.assertEqual(
            sorted(schema_statuses()), sorted(STATUSES),
            f"scrape.md 的 status 枚举与代码认的对不上。"
            f"\n  schema：{schema_statuses()}"
            f"\n  代码  ：{list(STATUSES)}"
            "\n多一个假状态，照它写的岗会从每个视图里消失且不报错；"
            "\n少一个真状态，执行者不知道那个状态存在。")

    def test_fields_are_not_smuggled_in_as_statuses(self):
        listed = schema_statuses()
        bad = [n for n in NOT_STATUSES if n in listed]
        self.assertEqual(
            bad, [],
            f"这些是**字段**，被写进 status 枚举了：{bad}"
            "\n`evaluated` 是 /job-apply 写的布尔值（那时 status 仍是 ranked）；"
            "\n`deprioritized` 是预筛降权标记（status 仍是 new）；"
            "\n`blocked` 的岗按 rank.md 也保持 new。")

    def test_real_data_uses_only_these(self):
        """有真实数据就核一遍——规范说得再对，落盘的才算数。"""
        found = set()
        for f in (ROOT / "users").glob("*/job_scraper/seen_jobs.json"):
            try:
                d = json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                continue
            for e in (d.get("seen", d) or {}).values():
                if isinstance(e, dict) and e.get("status"):
                    found.add(e["status"])
        if not found:
            self.skipTest("还没有真实的 seen_jobs.json")
        unknown = sorted(found - set(STATUSES))
        self.assertEqual(
            unknown, [],
            f"真实数据里出现了枚举之外的 status：{unknown}"
            "\n要么是执行时写错了，要么是这份枚举该扩——两种都得当场查清。")


if __name__ == "__main__":
    unittest.main()
