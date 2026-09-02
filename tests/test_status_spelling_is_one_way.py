"""同一个投递状态，两条写入路径必须拼成同一个样子。

## 有两条路会往 `job_search_tracker.csv` 的 status 列写字

1. **总览页的按钮** —— 走 `tools/tracker.py` 的 `NEXT`，写的是 `no response`、
   `offer declined`（**空格**）
2. **`/job-outcome` 命令** —— 走 `workflows/job-outcome.md` 的规定

`outcome.md` 原来**同一个文件里两种写法并存**：Step 1.3 的终结态过滤写
`no response`（空格），二十行外的 Step 2 枚举写 `no_response`（下划线）。

## 拼错了会怎样

面板写 `no response`、`/job-outcome` 写 `no_response`，于是：

- Step 1.3 的终结态过滤匹配不上 → **那条投递永远显示成「还开着」**
- `tools/followups.py` 一直把它算成该催的
- `/job-html-report` 的桶映射漏掉它 → 拒绝率失真

全都是**静默**的：没有报错，只是数字一直不对。

## 为什么以前没人拦

`tests/test_enum_consistency.py` 名字像是管这个的，实际管的是**路径枚举**
（AGENTS.md ↔ gitignore），和状态值无关。读取方倒是有人做过兼容
（`test_status_from_the_page.py::test_case_and_spacing_do_not_break_it`、
`/job-html-report` 的桶映射把两种写法都列上了）——但**写入方一直各写各的**，
靠读取方兜底就是在等它兜不住的那天。

## 判据

以 `tools/tracker.py` 的 `NEXT` 为权威（那是真正写盘的代码），
`workflows/job-outcome.md` 里出现的同名状态必须用同一种拼法。
"""

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import tracker  # noqa: E402

#: 会写出或读取这套状态词的工作流——**全扫，不列清单**。
#:
#: 演进过两次，两次都是被漏掉的副本打脸：
#:
#: 1. 第一版只盯 `outcome.md`。而同一份枚举在 `setup.md` 的 Step A3 里还有一份
#:    （路线 A 解析归档 `outcome.md` 时用），仍是下划线写法。
#: 2. 于是改成手工清单 `("outcome.md", "setup.md")`。**清单同样会漏**——逐行通读
#:    `offer.md` 时发现它写着「记 `offer_declined`」，顺藤摸出 `gmail-sync.md` 三处、
#:    `html-report.md` 一处，全在清单之外。其中 `html-report.md` 那处是真 bug：
#:    `closed` 桶列了 `offer_declined` 却**没有列权威的 `offer declined`**，
#:    于是用户在总览页点「挂了」拒掉一个 offer，报表根本不把它算进已结案。
#:
#: 手工清单的毛病是它默认「我知道有几处」——而这条规则的全部危险恰恰在于**不知道**。
#: 逐行判据本来就对并排举例免疫（见下），扫全量不会误伤。
CONSUMERS = tuple(
    sorted(p.relative_to(ROOT).as_posix() for p in (ROOT / "workflows").rglob("*.md")))

OUTCOME_MD = ROOT / "workflows" / "job-outcome.md"

#: 权威写法：`NEXT` 里出现过的每一个状态码。
CANONICAL = {code for opts in tracker.NEXT.values() for code, _ in opts} | set(tracker.NEXT) - {""}

#: 只有 `/job-outcome` 写得出来的状态（总览页的状态机到不了），不在 tracker.py 里。
OUTCOME_ONLY = {"interview_only", "withdrawn", "in_progress"}


def variants(code: str) -> set:
    """一个状态码的所有可能拼法：空格 ↔ 下划线。"""
    return {code, code.replace(" ", "_"), code.replace("_", " ")}


class OneStatusOneSpelling(unittest.TestCase):

    def setUp(self):
        text = OUTCOME_MD.read_text(encoding="utf-8")
        # ⚠️ 只看**定义状态的地方**，不看讨论状态的地方。
        #
        # 第一版扫的是全文所有反引号词——结果解释这条规则的正文里举了反例
        # （「面板写 `no response`、/job-outcome 写 `no_response`，于是……」），
        # 测试把**自己的反例**判成了违规，恢复原状后照样红。
        # 断言撞上解释自己的文字，是这个仓库反复出现的形状；这次的解法是把判据
        # 收到结构上：状态**定义**只出现在枚举条目（`- \`xxx\` - 说明`）和
        # 归档模板的 `**状态：**` 行里。正文怎么举例都不影响。
        self.ticks = set(re.findall(r"^\s*-\s+`([a-z_ ]{4,20})`\s+-", text, re.M))
        self.status_lines = [l for l in text.splitlines()
                             if l.strip().startswith("**状态：**")]

    def test_the_scan_reaches_the_workflows(self):
        """对照用例：扫描真的够到了文件 —— 否则同文件里那些「没问题」是恒绿的。

        2026-08-20 实测：把 `Path.glob`/`rglob` 打成空之后本文件全绿。
        **扫不到文件时，「没有问题」和「没有检查」长得一模一样。**

        这不是假想——这个仓库真搬过目录（工作流正文从 `.claude/skills/` 搬到
        `workflows/`，`AGENTS.md` 里记着）。glob 还指着旧路径时，守卫会安静地失效。
        """
        found = list((ROOT / "workflows").rglob("*.md"))
        self.assertGreaterEqual(
            len(found), 20,
            f"只扫到 {len(found)} 个工作流 —— 判据大概是够不到文件了，"
            "而不是仓库真的只剩这么几个")

    def test_tracker_really_defines_multiword_statuses(self):
        """控制用例：`NEXT` 里**真有**带空格的状态，否则下面那条无从判起。

        哪天 tracker.py 把 `no response` 改成 `no_response`，这条会红——
        那时该做的是把 outcome.md 一起改，而不是删掉这条测试。
        """
        multi = {c for c in CANONICAL if " " in c}
        self.assertTrue(
            multi,
            f"tracker.NEXT 里没有带空格的状态了（现有：{sorted(CANONICAL)}）——"
            "拼写歧义的前提消失了，本测试可以重新评估")

    def test_outcome_md_uses_the_canonical_spelling(self):
        bad = []
        for code in CANONICAL:
            if " " not in code:
                continue
            wrong = code.replace(" ", "_")
            if wrong in self.ticks:
                bad.append(f"`{wrong}` 应为 `{code}`")
        self.assertEqual(
            bad, [],
            "outcome.md 用了和 tools/tracker.py 不同的拼法：\n  " + "\n  ".join(bad)
            + "\n\n两条写入路径拼得不一样，那条投递会永远显示成「还开着」："
            "\n  · Step 1.3 的终结态过滤匹配不上"
            "\n  · followups.py 一直催"
            "\n  · /job-html-report 的拒绝率漏算"
            "\n全是静默的，不会报错。")

    def test_no_consumer_uses_the_underscore_form(self):
        """所有消费方都不许出现下划线写法。

        判据放宽到「整份文件里不许有」，因为这些文件里没有正当理由写下划线形式——
        它不是任何地方的合法值。唯一的例外是**解释这条规则本身的正文**
        （像 outcome.md 里那句「面板写 `no response`、/job-outcome 写 `no_response`」），
        所以先剥掉引用块与行内举例：只看 `- \\`xxx\\` -` 定义行和 `**Status:**` 行。
        """
        # 判据必须对**两个文件的不同写法**都成立：outcome.md 里枚举是
        # `- \`xxx\` - 说明` 的定义行，setup.md 里是行内散文。第一版照 outcome.md
        # 的结构写抽取正则，套到 setup.md 上抽到空集 —— 变异改了它照样绿。
        #
        # 改成逐行判，且对**对照举例**免疫：解释这条规则时必然把两种写法并排写出来
        # （「面板写 `no response`、/job-outcome 写 `no_response`」），那种行两者都有。
        # 只有「有错的、没有对的」才是真在用错写法。
        bad = []
        for rel in CONSUMERS:
            for n, line in enumerate((ROOT / rel).read_text(encoding="utf-8")
                                     .splitlines(), 1):
                for code in CANONICAL:
                    if " " not in code:
                        continue
                    wrong = code.replace(" ", "_")
                    if wrong in line and code not in line:
                        bad.append(f"{rel}:{n}  `{wrong}` 应为 `{code}`")
        self.assertEqual(
            bad, [],
            "这些消费方用了下划线写法：\n  " + "\n  ".join(bad)
            + "\n权威在 tools/tracker.py 的 NEXT（空格形式）。写法不一致时，"
            "\n那条投递会永远显示成「还开着」，而且全程静默。")

    def test_every_consumer_file_exists(self):
        """控制用例：CONSUMERS 里的文件都在，否则上面那条对着空气跑。"""
        missing = [r for r in CONSUMERS if not (ROOT / r).is_file()]
        self.assertEqual(missing, [], f"CONSUMERS 里这些文件不存在：{missing}")

    def test_nothing_refers_to_the_archive_field_by_its_old_name(self):
        """归档模板的字段叫 `状态` / `结案日期`，引用它的地方不许还写英文旧名。

        2026-08-21 把归档 `job-outcome.md` 的两个标签从 `**Status:**` /
        `**Date resolved:**` 译成中文（那份模板其余全是中文：`# 投递结果`、
        `## 走到了哪几关`、`- [ ] 在线测评`）。**改完当时没走下游**——
        通读 `/job-outcome` 时才撞见三处还写着 `Status`：
        `job-outcome.md` 的 Step 4 与 Step 5、`job-gmail-sync.md` 的回写说明。

        **这是这个仓库最常见的那个形状**（改了一处名字，没走一遍引用），
        而这一次是改名的人自己留下的。

        `job-notion-sync.md` 里的 `Status` **不在管辖范围**：那是 Notion 看板的
        属性名，与归档模板无关。
        """
        for name in ("job-outcome.md", "job-gmail-sync.md"):
            t = (ROOT / "workflows" / name).read_text(encoding="utf-8")
            for old in ("`Status`", "`Date resolved`", "**Status:**"):
                self.assertNotIn(
                    old, t,
                    f"{name} 里还用 {old} 指归档模板的字段 —— "
                    "那两个标签已经是 `状态` / `结案日期`，引用没跟上")

    def test_the_archive_status_line_matches_too(self):
        """归档 `outcome.md` 的状态行也得用同一套词。

        标签是散文（2026-08-21 从 `**Status:**` 译成中文），**值仍是机器词汇**
        —— 分界线同 `test_display_wording` 里 PASS/FAIL 那条：值留码，标签说人话。

        `/job-setup` 路线 A 与 `/job-html-report` 都要把归档和 CSV 两边合起来读——
        同一个状态两种写法，合并会静默漏掉一部分。
        """
        self.assertTrue(self.status_lines, "找不到归档模板的 **状态：** 行——判据可能失效了")
        for line in self.status_lines:
            for code in CANONICAL:
                if " " not in code:
                    continue
                self.assertNotIn(
                    code.replace(" ", "_"), line,
                    f"归档 Status 行用了 `{code.replace(' ', '_')}`，"
                    f"而 CSV 那边是 `{code}`：{line.strip()[:90]}")


if __name__ == "__main__":
    unittest.main()
