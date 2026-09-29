"""照着念给用户听的话，必须是中文。

## 这一类反复冒出来，因为每次都只修看得见的那几处

`AGENTS.md`：「**凡是给用户看的东西**——聊天里的回答、面板上的字、终端输出、简历与
话术——一律换成内地求职者自己会说的话。」

工作流里「照这个说」的台词写在引用块（`> `）里。逐轮手工扫过去，每收紧一次判据就
冒出新的一批——**因为漏的不是同一处，是同一类**：

| 轮次 | 漏掉的原因 |
|---|---|
| 第一次扫 | 只认以句点收尾的行 → 漏了 `Report saved to ….\"`（以 `."` 收尾） |
| 第二次扫 | 排除了以 `**` 开头的行 → 漏了 `/job-expand` 的「How would you like to proceed?」 |
| 第三次扫 | 排除了以 `-` 开头的行 → 漏了 `/job-add-template` 的整段总结 |
| 第四次扫 | 同上 → 漏了 `/job-setup` **第一屏**的三条路径说明（新用户看到的第一段字） |
| 第五次扫 | 门槛「短于 26 字不算话」 → 漏了 `/job-reset` 确认提示里的「This cannot be undone.」（22 字）|

最后那处尤其说明问题：欢迎语和结尾问句都是中文，**中间那三段他要读来做选择的
正文是英文**——半句中文半句英文，比整段英文更难读。

## 判据

`workflows/` 里引用块中的整行英文句子（长度够、以句末标点收尾、不含中文）就是违规。
命令、路径、URL、表格不算。

**例外表现在是空的。** 曾经有过一条：`add-template.md` 写进激活文件的那段覆盖说明，
理由是「读者是 `/job-apply`，AI 读 AI，不是用户」。2026-08-20 那一段随
`job-add-template.md` 一起翻成了中文，例外自然作废——**下面那条控制用例当场把它顶红了**，
断言消息写的就是「找不到了，例外该撤掉」。守卫自己指出了自己该收紧的地方。

再往这张表里加之前先想清楚：AI 读 AI 也不是英文的理由——**这个仓库里 AI 读的东西
本来就该是中文**（见 `tests/test_workflow_prose_is_chinese.py`）。真要加，写清理由。
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKFLOWS = ROOT / "workflows"

#: **空的就是目标状态。** 用「文件 + 特征串」定位，不用行号——行号会随编辑漂移。
#: 下面 `test_the_exemption_still_points_at_something` 会盯着：例外指向的串一旦消失就报红，
#: 逼人把作废的例外删掉，而不是让它烂在表里。
EXEMPT = ()

#: 不是「话」的行：命令、路径、表格、URL。
NOT_SPEECH = ("http", "|", "Bash(", "site:", "node ", "bun ", "python ",
              "npm ", "cd ", "typst ", "git ")


def spoken_lines():
    """引用块里「照着念」的行 → (相对路径, 行号, 内容)。"""
    for p in sorted(WORKFLOWS.rglob("*.md")):
        rel = p.relative_to(ROOT).as_posix()
        for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            s = line.strip()
            if not s.startswith(">"):
                continue
            body = re.sub(r"^>\s*", "", s).strip().lstrip("-*").strip().strip("*`")
            # **门槛 26 → 10（2026-09-01）。** 见上面那张表的第五行：
            # `job-reset.md` 的确认提示写的是「This cannot be undone.」——
            # 去掉 `>` 和 `**` 之后 **22 个字符**，差 4 个字躲过去了。
            # 而它是整个仓库唯一会删数据的地方、告诉用户「回不去了」的那一句。
            # 降到 10 实测**只多命中这一条**，零误伤（26/22/18/14/10 各算过一遍）。
            if len(body) < 10 or re.search(r"[一-鿿]", body):
                continue
            if not re.search(r"""[.?!:]["'）)]?\s*$""", body):
                continue
            if body.startswith(NOT_SPEECH):
                continue
            yield rel, i, body


def is_exempt(rel: str, body: str) -> bool:
    return any(rel.endswith(f) and marker in body for f, marker in EXEMPT)


class WhatWeSayToTheUserIsChinese(unittest.TestCase):

    def test_the_scan_sees_quoted_speech(self):
        """控制用例：引用块里确实有话，否则下面那条永远绿。

        扫的是**所有**引用行（不限语言）——只数英文的话，全修好之后这条就空转了。
        """
        n = 0
        for p in WORKFLOWS.rglob("*.md"):
            n += sum(1 for l in p.read_text(encoding="utf-8").splitlines()
                     if l.strip().startswith("> ") and len(l.strip()) > 26)
        self.assertGreaterEqual(
            n, 50, f"只扫到 {n} 行引用块内容——判据大概失效了")

    def test_the_exemption_still_points_at_something(self):
        """控制用例：例外不是空的，否则它在掩盖一条已经不存在的规则。"""
        for fname, marker in EXEMPT:
            with self.subTest(f=fname):
                p = WORKFLOWS / fname
                self.assertTrue(p.is_file(), f"例外指向的 {fname} 不存在")
                self.assertIn(
                    marker, p.read_text(encoding="utf-8"),
                    f"{fname} 里找不到 {marker!r} 了——例外该撤掉")

    def test_the_command_menu_itself_is_chinese(self):
        """敲 `/` 弹出的那一屏，才是用户读到的**第一句**中文（或英文）。

        本文件原来只扫 `workflows/` 里引用块中的台词——管的是流程中途 AI 念给用户
        听的话，却完全没看命令标题和 skill 描述。于是 16 个命令里有 11 个在 `/` 菜单
        里写着「Drafter-Reviewer Job Application Workflow」「Triage Scraped Jobs into
        a Ranked Shortlist」，三个 skill 的描述整段英文。**用户还没进任何流程，就先
        撞上一屏英文**——比中途冒一句英文更早、更劝退。

        **那一屏今天由谁提供，这里就扫谁。** 2026-09-29 那次实测扫的是
        `.claude/commands/*.md` 的 H1 标题（形如 `# /job-apply —— <说明>`，命令名本身
        是英文，只查它后面的说明）。命令 stub 已整体删除（Task 8），那个目录现在是空的
        —— 原来那段循环留着也不会报错，只会**每轮扫 0 个文件还全绿**，正是这一节在防的
        「没看伪装成都通过了」。斜杠命令与自动触发现在都出自两族技能壳，所以覆盖的是
        壳 frontmatter 里那行 `description:`，下面还有一条元测试钉住扫到的份数。

        壳那份 description 的**中文要求本身**由 `tests/test_workflow_prose_is_chinese.py`
        与生成器一路也盯着；本条是它在「英文整句」这个判据上的那一份，两处判据不同、
        不重复。
        """
        bad = []
        shells = sorted((ROOT / ".claude" / "skills").glob("*/SKILL.md")) + \
            sorted((ROOT / ".agents" / "skills").glob("*/SKILL.md"))
        for p in shells:
            fm = p.read_text(encoding="utf-8").split("---")[1]
            m = re.search(r"^description:\s*>?\s*\n?((?:\s+.+\n)+)", fm, re.M)
            if m and not re.search(r"[一-鿿]", m.group(1)):
                bad.append(f"{p.relative_to(ROOT).as_posix()}  {m.group(1).strip()[:60]}")
        self.assertEqual(
            bad, [],
            "这些是命令面板/技能列表里看到的说明，却是英文——用户还没进流程就先撞一屏英文：\n  "
            + "\n  ".join(bad))

    def test_the_shell_scan_is_not_scanning_nothing(self):
        """元测试：上面那条的扫描集不许为空。

        删掉 `.claude/commands/` 那半截的同时，把「扫到 0 个文件 = 全绿」这个失败方式
        也一起删掉：两族各 22 份壳，加 `.agents/` 里的渠道壳，少了就是 glob 打空了。
        """
        n = len(list((ROOT / ".claude" / "skills").glob("*/SKILL.md"))) + \
            len(list((ROOT / ".agents" / "skills").glob("*/SKILL.md")))
        self.assertGreaterEqual(n, 44, f"只扫到 {n} 份壳 —— glob 打空了")

    def test_no_english_speech(self):
        bad = [f"{rel}:{i}  {body[:72]}"
               for rel, i, body in spoken_lines() if not is_exempt(rel, body)]
        self.assertEqual(
            bad, [],
            "这些是「照着念给用户听」的话，却是英文：\n  " + "\n  ".join(bad)
            + "\n\n这是给内地求职者用的工具（AGENTS.md「给用户看的措辞」）。"
            "\n半中半英比整段英文更难读——`/job-setup` 第一屏就栽过：欢迎语和问句是中文，"
            "\n中间那三段他要读来做选择的正文是英文。"
            "\n确实是 AI 读 AI 的（比如写进激活文件给 `/job-apply` 读的块），加进 EXEMPT 并写清理由。")


if __name__ == "__main__":
    unittest.main()
