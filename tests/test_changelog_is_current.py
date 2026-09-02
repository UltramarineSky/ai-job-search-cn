# -*- coding: utf-8 -*-
"""CHANGELOG 顶部那条的日期，不能早于仓库最后一次提交。

## 为什么

打 tag 之前的最后一刻，最容易忘的就是这个日期。它错了不会有任何报错，
而**读者点开 CHANGELOG 看到的第一行就是它** —— 一个写着「2026-08-18 发布」
的 1.0.0，而仓库里最新的改动是 08-21，读起来像「作者自己都没在维护」。

2026-08-21 通读时的实况：当时的根提交与 `[1.0.0]` 都是 08-18，**此刻恰好对上**；
但工作树里躺着 89 个改过的文件。它们一提交，日期就对不上了 ——
**而那正是要打 tag 的时刻。**

## 两种合法写法，都放行

1. 把顶部那条的日期改成真实的发布日；
2. 或者按 Keep a Changelog 的惯例加一段 `## [未发布]` / `## [Unreleased]`
   把未发布的改动放进去。

判据只在**两者都没有**时红。

## 边界

- 取不到 git（打包分发、浅克隆没有历史）→ skip，不假装通过。
- 只看顶部那一条：更早的版本条目本来就该早于最新提交。
"""

import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHANGELOG = ROOT / "CHANGELOG.md"

#: `## [1.0.0] - 2026-08-18`，日期可缺（未发布条目常常没有）
ENTRY = re.compile(r"^##\s*\[([^\]]+)\]\s*(?:-\s*(\d{4}-\d{2}-\d{2}))?", re.M)
UNRELEASED = ("未发布", "Unreleased", "unreleased")


class ChangelogIsCurrent(unittest.TestCase):

    def test_the_changelog_exists_and_has_an_entry(self):
        """控制用例：抽得到顶部那一条，否则下面那条对着空气跑。"""
        self.assertTrue(CHANGELOG.is_file(), "CHANGELOG.md 不在")
        m = ENTRY.search(CHANGELOG.read_text(encoding="utf-8"))
        self.assertIsNotNone(m, "CHANGELOG 里找不到 `## [版本] - 日期` 形式的条目")

    def test_the_top_entry_is_not_older_than_the_last_commit(self):
        try:
            out = subprocess.run(
                ["git", "log", "-1", "--format=%ad", "--date=short"],
                cwd=ROOT, capture_output=True, text=True, timeout=30)
        except (OSError, subprocess.SubprocessError):
            self.skipTest("跑不了 git")
        if out.returncode != 0 or not out.stdout.strip():
            self.skipTest("取不到提交日期（浅克隆 / 无历史）")
        last_commit = out.stdout.strip()

        text = CHANGELOG.read_text(encoding="utf-8")
        m = ENTRY.search(text)
        self.assertIsNotNone(m, "抽不到顶部条目")
        version, date = m.group(1), m.group(2)

        if any(u in version for u in UNRELEASED):
            return          # 有「未发布」段，未提交的改动有地方放
        self.assertIsNotNone(
            date, f"顶部条目 `[{version}]` 没有日期")
        self.assertGreaterEqual(
            date, last_commit,
            f"CHANGELOG 顶部写着 `[{version}] - {date}`，"
            f"而最后一次提交是 {last_commit} —— 发布日期早于最后一次改动。"
            "\n打 tag 前把日期改成真实发布日，"
            "或加一段 `## [未发布]` 收未发布的改动。")


if __name__ == "__main__":
    unittest.main()
