"""工作流里点名的 `[YOUR_*]` 占位符，模板里必须真的有。

## 编出来的占位符没有源

占位符是 `/job-setup` 填、`/job-apply` 读的**契约**。工作流举例时随手编一个名字，
执行者就会照着写进产物——而那一格永远没有数据可填：要么空着，
要么被落盘前的占位符扫描当成「没填完」拦下来。

实测两处，都是「指着一个不存在的东西说照它写」：

| 在哪 | 编的是什么 | 真实的是什么 |
|---|---|---|
| `add-template.md` 教怎么把模板去个人化 | `[YOUR_LINKEDIN_URL]` | `[YOUR_PORTFOLIO_URL]`（「作品集 / 个人主页」）——领英是西方平台，资料模板里没有这个字段 |
| `add-portal.md` 教怎么加 `site:` 兜底 | 「用文件里**已有的** `[YOUR_JOB_BOARD]` 占位符风格」 | 那个占位符**全仓库都不存在**；实际写法是 `site:<域名> "[QUERY_1]" [YOUR_PRIMARY_CITY]` |

## 判据

占位符的**权威来源**是 `profile.example/*.md` 与 `workflows/reference/search-queries.md`
（那两处是 `/job-setup` 真正生成的文件）。工作流正文里用反引号点名的 `[YOUR_*]`，
必须在其中之一里出现。讲这条规则本身的行（要引用反例）免检。
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

#: 占位符的权威来源——`/job-setup` 真正会生成的那几份文件。
SOURCES = (["profile.example/" + p.name for p in (ROOT / "profile.example").glob("*.md")]
           + ["workflows/reference/search-queries.md"])

#: 讲这条规则本身的行必然要引用反例，免检。
ABOUT = ("不存在", "别自己编", "原来举的是", "原来写的是", "全仓库")


def known_tokens() -> set:
    out = set()
    for rel in SOURCES:
        p = ROOT / rel
        if p.is_file():
            out |= set(re.findall(r"\[([A-Z][A-Z0-9_]*)\]",
                                  p.read_text(encoding="utf-8")))
    return out


class WorkflowsOnlyNameRealPlaceholders(unittest.TestCase):

    def test_the_sources_are_found(self):
        """控制用例：真读到了模板，否则下面那条比对的是空集。"""
        toks = known_tokens()
        self.assertGreaterEqual(
            len(toks), 50,
            f"只抽到 {len(toks)} 个占位符——模板路径大概变了：{SOURCES}")

    def test_every_named_placeholder_exists(self):
        known = known_tokens()
        bad = []
        for p in sorted((ROOT / "workflows").rglob("*.md")):
            for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
                if any(k in line for k in ABOUT):
                    continue
                for tok in re.findall(r"`\[(YOUR_[A-Z0-9_]*)\]`", line):
                    if tok not in known:
                        rel = p.relative_to(ROOT).as_posix()
                        bad.append(f"{rel}:{i}  `[{tok}]`")
        self.assertEqual(
            bad, [],
            "工作流点名了模板里没有的占位符：" + chr(10) + "  " + (chr(10) + "  ").join(bad)
            + chr(10) + "占位符是 /job-setup 填、/job-apply 读的契约——编一个出来，"
            + chr(10) + "那一格永远没有数据可填，而且落盘前会被当成「没填完」拦下来。"
            + chr(10) + f"权威来源：{SOURCES}")

    def test_the_detector_can_actually_fail(self):
        """变异内建：编一个模板里没有的 token，检查器必须认得。"""
        self.assertNotIn("YOUR_DEFINITELY_NOT_A_FIELD", known_tokens())


if __name__ == "__main__":
    unittest.main()
