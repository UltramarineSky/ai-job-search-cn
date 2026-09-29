"""两族壳逐字相同。

`AGENTS.md`「工具特化」原来把这条写成散文规则（「两份壳必须逐字一致，否则同一个技能
在 Claude Code 和别的工具里触发词、权限都能不一样」）。生成器落地后它成了可执行的断言。
"""
import filecmp
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import _entries  # noqa: E402


class ShellFamiliesAreByteIdentical(unittest.TestCase):
    def test_every_generated_shell_matches_across_families(self):
        bad = []
        for name in _entries.generated_names():
            a = ROOT / ".claude" / "skills" / name / "SKILL.md"
            b = ROOT / ".agents" / "skills" / name / "SKILL.md"
            if not (a.is_file() and b.is_file()):
                bad.append(f"{name}: 缺文件（.claude={a.is_file()} .agents={b.is_file()}）")
            elif not filecmp.cmp(a, b, shallow=False):
                bad.append(name)
        self.assertEqual(bad, [], "两族壳不一致：" + "、".join(bad))

    def test_the_handwritten_router_matches_too(self):
        """手写壳没有生成器兜着，这一对全靠人工同步 + 本条测试。"""
        for name in sorted(_entries.HANDWRITTEN_NAMES):
            a = ROOT / ".claude" / "skills" / name / "SKILL.md"
            b = ROOT / ".agents" / "skills" / name / "SKILL.md"
            self.assertTrue(a.is_file() and b.is_file(), f"{name} 两族都得有")
            self.assertTrue(filecmp.cmp(a, b, shallow=False),
                            f"{name} 两族不一致 —— 改一边就要改两边")

    def test_the_set_is_exactly_index_plus_router(self):
        """对照用例：壳的集合不许自己长大或缩小。

        多一个 = 有条命令没有工作流正文；少一个 = 用户敲得到面板上那条、
        但在别的工具里叫不动它。
        """
        for fam in _entries.SHELL_FAMILIES:
            on_disk = {p.parent.name for p in (ROOT / fam / "skills").glob("*/SKILL.md")}
            on_disk -= {"liepin-search"}          # 可插拔平台技能，不是命令壳
            self.assertEqual(on_disk, set(_entries.shell_names()),
                             f"{fam}/skills 的壳集合与索引对不上")


if __name__ == "__main__":
    unittest.main()
