# -*- coding: utf-8 -*-
"""`allowed-tools` 里的 Bash 规则要用前缀形式 `Bash(<命令>:*)`，不是 `Bash(<命令> *)`。

Claude Code 的 Bash 权限有两种写法：`Bash(<前缀>:*)` 是**前缀匹配**，
`Bash(<原样命令>)` 是**精确匹配**。写成 `Bash(node …/cli.ts *)`（空格加星）落进
第二种——它只匹配字面量以 ` *` 结尾的那一条命令，而真实调用长这样：

    node .agents/skills/liepin-search/cli/src/cli.ts search -q "…" -l "…"

于是永远匹配不上，每次搜岗都要用户手动批一次；在受限工具集里更可能直接被拒。

`.claude/settings.json` 里写的是对的冒号形式（`tools/security_guards.py` 的
`ALLOWED_PERMISSIONS` 逐字钉着它），而 `SKILL.md` 那几份是空格形式——
**守卫只看 settings.json，看不见这处漂移**。这条补上另一半。

## 这条只管**写法**，不管**写全了没有**

一条规则形式正确，不等于该有的规则都在。姊妹检查
`test_skill_permissions_cover_its_workflow.py` 管另一半：从工作流的 ```bash 块里
取命令，看壳上有没有对应的规则。2026-08-18 实测两处漏写（`job-scrape` 缺四条
`python tools/*.py`、`job-upskill` 一条 Bash 都没有），而本条测试对它们全绿——
它们那几条写下来的规则形式本来就没问题。**两条问的是不同的问题，缺一条就有整类
问题没人看。**
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

#: 所有带 frontmatter 的技能文件。`.agents/` 是可插拔的 portal 技能区，
#: 一个 portal 都没装也是合法状态，所以用 glob 收而不是写死清单。
SKILLS = sorted(ROOT.glob(".claude/skills/*/SKILL.md")) + \
    sorted(ROOT.glob(".agents/skills/*/SKILL.md"))

_ENTRY = re.compile(r"Bash\(([^)]*)\)")


def _bash_entries(path: Path):
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("allowed-tools:"):
            return _ENTRY.findall(line)
    return []


class BashRulesUsePrefixForm(unittest.TestCase):

    def test_there_are_skills_to_check(self):
        """元测试：glob 扫空了的话下面几条会无声全绿。"""
        self.assertTrue(SKILLS, "一个 SKILL.md 都没扫到")

    def test_no_space_star_form(self):
        bad = []
        for p in SKILLS:
            for e in _bash_entries(p):
                if e.rstrip().endswith("*") and not e.rstrip().endswith(":*"):
                    bad.append(f"{p.relative_to(ROOT).as_posix()}: Bash({e})")
        self.assertEqual(
            bad, [],
            "这些 Bash 规则用了空格加星（精确匹配），真实调用匹配不上；"
            "改成 `:*` 前缀形式：\n  " + "\n  ".join(bad))

    def test_the_detector_can_fail(self):
        """变异验证：把判据本身喂上下两种写法，确认它分得开。"""
        ok = "node a/cli.ts:*"
        bad = "node a/cli.ts *"
        self.assertTrue(ok.rstrip().endswith(":*"))
        self.assertFalse(bad.rstrip().endswith(":*"))
        self.assertTrue(bad.rstrip().endswith("*"))

    def test_lint_skills_catches_it(self):
        """判据要在 CI 的 lint 里也有一份，别只活在测试里——
        贡献者跑的是 `python tools/lint_skills.py`。"""
        src = (ROOT / "tools" / "lint_skills.py").read_text(encoding="utf-8")
        self.assertIn("prefix form", src,
                      "lint_skills.py 里没有这条检查")


if __name__ == "__main__":
    unittest.main()
