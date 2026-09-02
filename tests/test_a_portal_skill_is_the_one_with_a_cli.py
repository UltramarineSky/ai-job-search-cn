# -*- coding: utf-8 -*-
"""`.agents/skills/` 下不全是渠道，而两处发现都当它们全是。

## 那底下有四个目录，只有一个是渠道

    liepin-search              ← 真渠道：有 cli/src/cli.ts、有 url-reference.md
    job-application-assistant  ← 自动触发的技能壳，与 .claude/skills/ 下逐字相同
    job-scrape                 ← 同上
    job-upskill                ← 同上

三份壳在那儿是**有意的**：不读 `.claude/` 的工具（Codex、Gemini、Cursor…）
只看得到 `.agents/`，同一份壳得放两处。

## 而两处发现都是「目录名一把捞」

- `job-scrape.md` 1b：「读遍 `.agents/skills/*/SKILL.md`，把已装的渠道 CLI
  全找出来」
- `job-add-portal.md` Step 0 `--list`：打印「已安装 portal 技能的表格
  （名称、覆盖市场、`url-reference.md` 里的数据来源）」

照字面做，前者会去找三个不存在的 CLI，后者会给用户印出三行空表格
（那三份既没有 CLI 也没有 `url-reference.md`）。实测 2026-08-31：
4 个目录，1 个是渠道。

判据现在写在两处正文里，也写在 `AGENTS.md`「工具特化」那一节：
**有没有 `cli/src/cli.ts`**。

## 两份壳还必须逐字一致

它们此前**没有任何东西钉着**。分叉的样子是：同一个技能在 Claude Code 里
触发词是一套、在别的工具里是另一套；`allowed-tools` 也能不一样 ——
而那正好是「换个工具就少一条规则」的老毛病，本仓库为它交过好几次学费。
"""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENTS_SKILLS = ROOT / ".agents" / "skills"
CLAUDE_SKILLS = ROOT / ".claude" / "skills"

#: 两处都放、必须逐字相同的那几份壳。
MIRRORED = ("job-application-assistant", "job-scrape", "job-upskill")


def _dirs(base: Path) -> list:
    return sorted(p.name for p in base.glob("*") if (p / "SKILL.md").is_file())


class TheMirrorHolds(unittest.TestCase):
    """镜像那三份壳是否一致 —— **只在镜像真的在盘上时才验得了**。

    `.agents/skills/{job-application-assistant,job-scrape,job-upskill}/` 三条
    在 `.gitignore` 里点名排除（`AGENTS.md`：「收进版本库就是本仓库最反对的那件事：
    一条规则两个落点」）。它们由所在的 AI 工具自动镜像出来，不是仓库内容。

    所以在**干净 clone 上它们本来就不存在** —— 那是设计，不是故障。
    这里原来无条件断言它们在，于是发布前的干净 clone 实测里这一个类红了 7 条
    （2026-09-02）。而它守的东西仍然有价值：在**有镜像的机器上**，两份壳分叉
    就当场逮住。所以是 skip，不是删。
    """

    @classmethod
    def setUpClass(cls):
        missing = [n for n in MIRRORED
                   if not (AGENTS_SKILLS / n / "SKILL.md").is_file()]
        if missing:
            raise unittest.SkipTest(
                "`.agents/skills/` 下没有镜像壳（这三条是 gitignore 的，"
                f"干净 clone 上缺席是预期）：{'、'.join(missing)}")

    def test_the_scan_sees_both_trees(self):
        """**先证明两边都扫到了东西。** 空目录上「逐字相同」永远为真。"""
        self.assertGreaterEqual(len(_dirs(AGENTS_SKILLS)), 2)
        self.assertGreaterEqual(len(_dirs(CLAUDE_SKILLS)), 2)

    def test_every_mirrored_shell_is_in_both_trees(self):
        for name in MIRRORED:
            with self.subTest(name=name):
                self.assertTrue((AGENTS_SKILLS / name / "SKILL.md").is_file())
                self.assertTrue((CLAUDE_SKILLS / name / "SKILL.md").is_file())

    def test_the_two_copies_are_identical(self):
        """改一份忘一份，同一个技能在两类工具里就是两套触发词和两套权限。"""
        for name in MIRRORED:
            with self.subTest(name=name):
                a = (AGENTS_SKILLS / name / "SKILL.md").read_text(
                    encoding="utf-8")
                b = (CLAUDE_SKILLS / name / "SKILL.md").read_text(
                    encoding="utf-8")
                self.assertEqual(a, b, f"{name} 的两份壳不一样了")

    def test_the_claude_tree_holds_nothing_else(self):
        """`.claude/skills/` 里只该有这三份 —— 多出来的说明镜像表该更新了。"""
        self.assertEqual(sorted(_dirs(CLAUDE_SKILLS)), sorted(MIRRORED))


class APortalIsTheOneWithACli(unittest.TestCase):

    def test_every_dir_is_either_a_portal_or_a_declared_shell(self):
        """那底下每个目录，要么有 CLI（渠道），要么在镜像表里。漏网当场红。"""
        stray = [n for n in _dirs(AGENTS_SKILLS)
                 if n not in MIRRORED
                 and not (AGENTS_SKILLS / n / "cli" / "src" / "cli.ts").is_file()]
        self.assertEqual(
            stray, [],
            "这几个目录既没有 cli/src/cli.ts、也不是登记过的技能壳：" + repr(stray))

    def test_there_is_at_least_one_real_portal(self):
        """控制用例：一个渠道都没有时，上面那条在空集上没意义。"""
        portals = [n for n in _dirs(AGENTS_SKILLS)
                   if (AGENTS_SKILLS / n / "cli" / "src" / "cli.ts").is_file()]
        self.assertTrue(portals, "一个带 CLI 的渠道都没有？")

    def test_the_shells_really_have_no_cli(self):
        """反过来也要成立 —— 否则「有 CLI 才是渠道」这条判据分不开它们。"""
        for name in MIRRORED:
            with self.subTest(name=name):
                self.assertFalse(
                    (AGENTS_SKILLS / name / "cli").exists(),
                    f"{name} 有了 CLI，那它就该按渠道处理，镜像表要改")


class BothDiscoverySitesSayIt(unittest.TestCase):
    """两处「发现渠道」的正文都要写出判据，别再照目录名一把捞。"""

    SITES = ("workflows/job-scrape.md", "workflows/job-add-portal.md",
             "AGENTS.md")

    def test_each_site_names_the_criterion(self):
        for rel in self.SITES:
            with self.subTest(rel=rel):
                t = (ROOT / rel).read_text(encoding="utf-8")
                self.assertIn(".agents/skills/*/cli/src/cli.ts", t,
                              f"{rel} 没说清哪些才算渠道")

    def test_they_name_the_shells_that_would_be_picked_up(self):
        """点名那三份 —— 只说「有 CLI 的才算」，读的人不知道会捞到谁。"""
        for rel in self.SITES:
            with self.subTest(rel=rel):
                t = (ROOT / rel).read_text(encoding="utf-8")
                self.assertIn("job-application-assistant", t)


if __name__ == "__main__":
    unittest.main()
