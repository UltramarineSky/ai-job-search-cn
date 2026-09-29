# -*- coding: utf-8 -*-
"""`.agents/skills/` 下不全是渠道，而两处发现都当它们全是。

## 那底下的目录，只有一个是有 CLI 的渠道

    liepin-search              ← 真渠道：有 cli/src/cli.ts、有 url-reference.md
    job-application-assistant  ← 自动触发的技能壳，与 .claude/skills/ 下逐字相同
    job-scrape / job-upskill   ← 同上（原来只有这三份手写壳）
    job-setup … job-user       ← 2026-09-29 起由 tools/gen_entries.py 生成的 21 份

除了那个渠道，其余都是**壳**：21 条命令的壳由生成器同时落到两处，
手写的路由壳不生成，但同样两族各一份。2026-09-29 起两族 22 份**都入库**
（`.gitignore` 里那三条「镜像副本」的忽略已删）—— 不读 `.claude/` 的工具
（Codex、Qwen Code、Cursor…）只看得到 `.agents/`，同一份壳得放两处，
而一致与否由 `tests/test_shell_families_are_byte_identical.py` 按字节钉住。

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

今天钉它的是 `tests/test_shell_families_are_byte_identical.py`（`filecmp` 逐字节，
两族 + 手写那份路由壳一起）；本文件那条 `test_the_two_copies_are_identical`
比的是**解码后的文本**，管的是「有镜像的机器上别漂」，两条判据不是一回事。
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import _entries  # noqa: E402

AGENTS_SKILLS = ROOT / ".agents" / "skills"
CLAUDE_SKILLS = ROOT / ".claude" / "skills"

#: 两处都放、必须逐字相同的那些壳。
#:
#: **原来这是一张写死的三名表**（job-application-assistant / job-scrape /
#: job-upskill），而 2026-09-29 `tools/gen_entries.py` 把 21 条命令的壳都落到两处
#: 之后，它就只剩两个下场：留着 → 下面两条「目录里不该有别的」当场红，而红的
#: 原因是**生成器正常工作**；删掉 → 判据空转。
#: 正本改读 `_entries.shell_names()`（21 条生成的 + 手写的路由壳）—— 同样是
#: 「每个目录都要在案」，只是名册由派生器给，不再有人手抄一份。
#: 抄件的代价这仓库付过：`AGENTS.md`「一条规则只贴在一个写手身上」。
MIRRORED = tuple(_entries.shell_names())


def _dirs(base: Path) -> list:
    return sorted(p.name for p in base.glob("*") if (p / "SKILL.md").is_file())


class TheMirrorHolds(unittest.TestCase):
    """两族那 22 份壳是否镜像一致 —— **只在两族都在盘上时才验得了**。

    `.agents/skills/{job-application-assistant,job-scrape,job-upskill}/` 这三条
    曾被 `.gitignore` 点名排除（手写时代由 AI 工具镜像过去的旧账，理由写着
    「一条规则两个落点」）。生成器把这条理由接了过去 —— 落点仍是两个，正本只有
    一个 —— 于是 2026-09-29 那三条连同其余 19 份生成物一起入了库：
    **干净 clone 上这 22 份现在都在，缺席不再是预期。**

    那为什么这里还是 skip 而不是再断言一次「都在」：存在性已经被两条**不许跳过**的
    测试硬钉着（`test_generated_entries_are_current` 的
    `test_both_families_carry_every_generated_shell`，以及
    `tests/test_shell_families_are_byte_identical.py` 那三条），本类只补
    「内容一致」。在一台没跑过生成器的工作树上整类跳过，是不让同一件事红三次，
    不是把判据放宽 —— 红点由那两条出。
    """

    @classmethod
    def setUpClass(cls):
        missing = [n for n in MIRRORED
                   if not (AGENTS_SKILLS / n / "SKILL.md").is_file()]
        if missing:
            raise unittest.SkipTest(
                "`.agents/skills/` 下缺这些壳 —— 两族 22 份都已入库，"
                "缺席说明这台工作树没跑 `python tools/gen_entries.py` 或生成物被删了；"
                "存在性由 test_generated_entries_are_current 与 "
                f"test_shell_families_are_byte_identical 报，不在这里重复：{'、'.join(missing)}")

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

    # 原来这里还有一条 `test_the_claude_tree_holds_nothing_else`
    # （`.claude/skills/` 的目录集合 == 在案的壳）。它数的是**壳的数量**，
    # 而那个判据从 Task 5 起住在
    # `tests/test_shell_families_are_byte_identical.py::test_the_set_is_exactly_index_plus_router`
    # —— 两族一起按 `shell_names()` 核，且**不在可 skip 的类里**（本类没有镜像时会
    # 整类跳过，那条不会）。同一件事留两处红点，只会让人猜哪份是正本。


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

    def test_the_portal_set_is_exactly_the_dirs_with_a_cli(self):
        """渠道按**判据**数：有 `cli/src/cli.ts` 的那几个，今天就一个 liepin-search。

        这一条替掉的是原来那条数壳的名册的测试
        （`test_the_claude_tree_holds_nothing_else`：`.claude/skills/` 的目录集合
        == 手写时代那三名）—— 生成器把 21 份壳落到两处之后，那张三名表就是假事实，
        而 Task 3 把它改成读 `shell_names()` 之后，它与新文件里那条
        `test_the_set_is_exactly_index_plus_router` 成了同一件事的两个红点。
        **本文件从此只管「哪些目录是渠道」，壳的集合由那条两族一起钉。**
        """
        portals = {n for n in _dirs(AGENTS_SKILLS)
                   if (AGENTS_SKILLS / n / "cli" / "src" / "cli.ts").is_file()}
        self.assertEqual(
            portals, {"liepin-search"},
            "渠道集合变了。真接了新渠道 → 两处发现正文与 `AGENTS.md`「取数渠道的顺位」"
            f"要跟着写；没接 → 判据分不开渠道与壳了：{sorted(portals)}")

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

    #: 文档里那份「哪些地方会发现渠道」的点名清单。原来写的是「两处发现」——
    #: 一个没人数的数字：2026-09-29 把「工具特化」搬进 `docs/tool-entries.md` 之后，
    #: 那句还留在原位，而 SITES 这里已经悄悄是三条了（`AGENTS.md` 也写判据，
    #: 只是它不发现渠道）。数字会漂，点名的文件不会，所以改成名单对名单。
    DOC = "docs/tool-entries.md"
    PAT = "凡是发现渠道的地方都按这个判（"

    def test_the_doc_enumeration_matches_the_sites_being_scanned(self):
        text = (ROOT / self.DOC).read_text(encoding="utf-8")
        i = text.find(self.PAT)
        self.assertNotEqual(i, -1,
                            f"{self.DOC} 里那句点名清单换了写法，这条判据就成了空转")
        j = text.index("）", i)
        named = {tok.split()[0].strip("`").removesuffix(".md")
                 for tok in text[i + len(self.PAT):j].replace(chr(10), " ").split("、")}
        self.assertEqual(
            named,
            {Path(r).stem for r in self.SITES if r.startswith("workflows/")},
            f"文档点名 {sorted(named)} 与被扫的发现点不一致——"
            "加一处发现渠道的地方，SITES 与那句点名都要跟着改")


if __name__ == "__main__":
    unittest.main()
