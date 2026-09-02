# -*- coding: utf-8 -*-
"""装个人数据的目录，要整目录忽略，别用扩展名通配。

`upskill/` 原来写的是 `upskill/*.md` —— 而同族的 `gmail_sync/`、`reports/`
都是整目录规则。扩展名通配的脆处很具体：**哪天有人往那儿落一个 `.json` 缓存
就会被静默提交**，而 `/job-upskill` 写进去的是他的能力差距分析。

这个仓库刚在同一类脆处上栽过：`web/public/` 一直在 `.gitignore` 里、
却从没进过 `security_guards` 的必需清单，而它是「全仓个人数据密度最高的单个文件」
（`security_guards` 那段注释的原话，2026-08-20 补的）。

**两处都要改**：`.gitignore` 挡住它，`security_guards.REQUIRED_IGNORE_RULES`
盯住那条规则别被删 —— 只改一处的话，另一处照样是空的。
"""
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import security_guards as G  # noqa: E402

#: 装个人数据、且**整个目录**都该被忽略的。加新的产出目录时要加进来。
WHOLE_DIRS = ["users/", "gmail_sync/", "reports/", "upskill/",
              "web/public/", ".private/"]


class EachOneIsAWholeDirectoryRule(unittest.TestCase):
    def test_the_guard_requires_the_directory_form(self):
        for d in WHOLE_DIRS:
            with self.subTest(dir=d):
                self.assertIn(d, G.REQUIRED_IGNORE_RULES,
                              f"{d} 不在必需清单里——删掉那行没有守卫会报警")

    def test_no_extension_glob_stands_in_for_them(self):
        """`upskill/*.md` 这种写法只挡一种扩展名，换个后缀就漏。"""
        for d in WHOLE_DIRS:
            bad = d.rstrip("/") + "/*."
            with self.subTest(dir=d):
                self.assertFalse(
                    any(r.startswith(bad) for r in G.REQUIRED_IGNORE_RULES),
                    f"{d} 又退回扩展名通配了")

    def test_git_actually_ignores_a_foreign_extension(self):
        """判据要落到 git 上，不是只落到清单上。"""
        for d in WHOLE_DIRS:
            probe = d + "probe.json"
            with self.subTest(path=probe):
                r = subprocess.run(["git", "check-ignore", "-q", probe],
                                   cwd=ROOT, capture_output=True)
                self.assertEqual(r.returncode, 0,
                                 f"{probe} 没被忽略——落一个非 md 就会进版本库")


class TheGuardItselfStillPasses(unittest.TestCase):
    def test_it_runs_clean(self):
        r = subprocess.run([sys.executable, "tools/security_guards.py"],
                           cwd=ROOT, capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        self.assertEqual(r.returncode, 0, (r.stdout + r.stderr)[-400:])


if __name__ == "__main__":
    unittest.main()
