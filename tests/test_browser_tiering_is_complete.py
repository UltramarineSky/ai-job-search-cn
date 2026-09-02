"""讲「怎么用浏览器取数」的地方，三层顺位不能只讲两层。

## 漏的总是第 1 层

`AGENTS.md`「取数渠道的顺位（别搞反）」定的是：

| 顺位 | 用什么 | 为什么在这个位置 |
|---|---|---|
| 1 | **你所在 AI 工具自带的浏览器能力** | 驱动的就是用户自己那个已登录的 Chrome，登录态天然带着，用户不必装任何第三方东西 |
| 2 | `web-access` skill 的 CDP 代理 | 只在没有第 1 层、或它够不着时才用。**第三方全局技能，本项目不附带** |
| 3 | `site:` 域名限定搜索 | 前两层都没有时的兜底，字段少得多 |

这套顺位在仓库里有五份副本。实测 `workflows/reference/search-queries.md` 写的是：

    有 `web-access` skill 时走 CDP 流程，否则退到下面的 `site:` 兜底。

**第 1 层整个不见了。** 执行者照它办，会跳过用户已经登录好的浏览器，
直接去要求他装一个本项目并不附带的第三方全局技能——而那一层恰恰是
`AGENTS.md` 反复强调「不要搞反」的那一层，也是唯一不需要用户额外做任何事的。

`AGENTS.md` 还专门写过一句：「**「浏览器能力」不是这个仓库要你装的东西**，
它由你所在的 AI 工具提供」。漏掉第 1 层，正好把这句话推翻了。

## 判据

一份文件只要同时讲到第 2 层（`web-access`）和第 3 层（`site:` 兜底），
它就是在描述这套顺位——那它必须也讲第 1 层。判据不看措辞，看**这三层在不在**。
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

TIER1 = re.compile(r"工具自带的浏览器|自带的浏览器能力|浏览器扩展")
TIER2 = "web-access"
TIER3 = re.compile(r"`site:`|site: 兜底")


def docs():
    yield from sorted((ROOT / "workflows").rglob("*.md"))
    # SETUP.md / README.md 也讲这套顺位，而且是**用户先读到**的那两份——
    # 第一版只扫 workflows + AGENTS/CLAUDE，于是 SETUP.md 里那句
    # 「覆盖方式是 CDP 为主、site: 兜底」（跳过第 1 层）一直没人拦。
    for name in ("AGENTS.md", "CLAUDE.md", "SETUP.md", "README.md"):
        p = ROOT / name
        if p.is_file():
            yield p


def describes_tiering(text: str) -> bool:
    return TIER2 in text and bool(TIER3.search(text))


class EveryCopyStatesAllThreeTiers(unittest.TestCase):

    def test_the_scan_finds_copies(self):
        """控制用例：真扫到了讲这套顺位的文件。"""
        found = [p.name for p in docs()
                 if describes_tiering(p.read_text(encoding="utf-8"))]
        self.assertGreaterEqual(
            len(found), 3,
            f"只扫到 {found} 在讲浏览器顺位——判据大概失效了")

    def test_the_authority_still_defines_it(self):
        """控制用例：AGENTS.md 里那节还在，否则本测试没有依据。"""
        self.assertIn(
            "取数渠道的顺位", (ROOT / "AGENTS.md").read_text(encoding="utf-8"),
            "AGENTS.md 里「取数渠道的顺位」一节不见了——本测试失去依据")

    def test_no_copy_drops_tier_one(self):
        bad = []
        for p in docs():
            text = p.read_text(encoding="utf-8")
            if not describes_tiering(text):
                continue
            if not TIER1.search(text):
                bad.append(p.relative_to(ROOT).as_posix())
        self.assertEqual(
            bad, [],
            "这些地方讲了第 2、3 层，却没讲第 1 层：\n  " + "\n  ".join(bad)
            + "\n执行者照它办，会跳过用户已经登录好的浏览器，"
            "\n直接要求他装一个本项目并不附带的第三方全局技能。"
            "\n（AGENTS.md：「「浏览器能力」不是这个仓库要你装的东西」）")


if __name__ == "__main__":
    unittest.main()
