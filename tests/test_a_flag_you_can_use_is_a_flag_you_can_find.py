# -*- coding: utf-8 -*-
"""教了怎么用、却没有一处列得出来的旗子。

## 两层清单，各有各的读者

    工作流自己的「可选参数」    执行者照它决定这次能给什么
    `AGENTS.md` 的索引表        **面板上那份帮助的正文**（`parse_commands` 解析它，
                                `CommandBook` 渲染）——用户唯一看得见的一份

一面旗子只写在正文散文里，两层都列不出来，就等于只有读到那一段的人才知道它存在。

## 实测 2026-08-31

    /job-scrape --no-browser    只在 Step 0.4 的散文里出现一次
                                （「要临时不碰登录态账号用 `--no-browser`」），
                                参数表没有，索引表没有
    /job-notion-sync --min-score  参数表有，**索引表没有** —— 面板上查不到

第一面尤其可惜：面板上的勾选是长期开关，改一次要点三下再记得改回来；
而这面旗子正是「这一趟别动我的登录态账号」的一次性写法。

## 判据

- 工作流参数表里的每一面旗子，索引表都要有；
- 正文里以「用 \\`--x\\`」的形式教人用的旗子，参数表要有。

两条都只查**这条命令自己的**旗子 —— `python tools/xxx.py --apply` 那种是工具的
开关，不是斜杠命令的参数，不在此列。
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENTS = (ROOT / "AGENTS.md").read_text(encoding="utf-8")

#: 索引表一行 → 那一行「怎么敲（举例）」列里出现的旗子。
_FLAG = re.compile(r"(?<![\w-])(--[a-z][a-z-]+)")
#: 工作流「可选参数」列表里的一项：`- \`--x\`` 或 `- \`--x <N>\``。
_ITEM = re.compile(r"^\s*[-*]\s*`(--[a-z][a-z-]+)", re.M)


def _rows() -> dict:
    """`命令名 → 索引表那一行列出的旗子`。"""
    out = {}
    for ln in AGENTS.splitlines():
        if not (ln.startswith("|") and "workflows/" in ln):
            continue
        cells = [c.strip() for c in ln.strip("|").split("|")]
        m = re.search(r"workflows/([a-z0-9-]+)\.md", cells[1])
        if m and len(cells) > 2:
            out[m.group(1)] = set(_FLAG.findall(cells[2]))
    return out


def _listed(name: str) -> set:
    p = ROOT / "workflows" / f"{name}.md"
    if not p.is_file():
        return set()
    return set(_ITEM.findall(p.read_text(encoding="utf-8")))


#: 工作流里列着、而**有意不登台**的旗子 → 理由。
#:
#: 面板那份帮助是给用户看的，多一行就多一次「这个我要不要用」的判断。
#: 兼容别名、以及写不写都一样的旗子，登在那儿是噪音。
NOT_ADVERTISED = {
    "/job-rank --auto":
        "它自己的说明写着「显式写出默认行为……现在不写也一样，保留是为了让"
        "`/job-scrape` Step 5.5 与 `/job-auto` 里的既有写法继续可读」。"
        "一个不写也一样的旗子登上面板，只会让人以为不写就不自动。"
        "出路：等那两处既有写法改掉之后，这面旗子和这条例外一起删。",
}


class EveryDocumentedFlagIsOnThePanel(unittest.TestCase):

    def test_the_scan_reads_both_lists(self):
        """**先证明两份清单都读到了。** 任一份读成空，下面两条永远绿。

        这条不是形式主义：写这个文件时，参数表那条正则一度被 shell 吃掉了
        反引号，`listed` 恒为空集，于是「都对得上」报了个漂亮的 0 —— 而实际
        有两面旗子对不上。
        """
        rows = _rows()
        self.assertGreaterEqual(len(rows), 15, f"索引表只读到 {len(rows)} 行")
        self.assertGreater(sum(len(v) for v in rows.values()), 15,
                           "索引表里一面旗子都没读到")
        seen = sum(len(_listed(n)) for n in rows)
        self.assertGreater(seen, 8, f"工作流参数表里只读到 {seen} 面旗子")

    def test_every_listed_flag_reaches_the_panel(self):
        bad = []
        for name, shown in sorted(_rows().items()):
            for f in sorted(_listed(name) - shown):
                if f"/{name} {f}" in NOT_ADVERTISED:
                    continue
                bad.append(f"/{name} {f}")
        self.assertEqual(
            bad, [],
            "这几面旗子工作流里列着，而索引表（= 面板上那份帮助）没有 —— "
            "用户查不到：" + "; ".join(bad))

    def test_the_exception_table_does_not_rot(self):
        """登记为不登台的，得**确实**还在工作流里列着、也确实不在索引表。

        它要是已经登台了、或者整面旗子删了，这条例外就该跟着走。"""
        rows = _rows()
        for entry in NOT_ADVERTISED:
            name, flag = entry.lstrip("/").split(" ", 1)
            with self.subTest(entry=entry):
                self.assertIn(flag, _listed(name),
                              f"{entry} 已经不在这条命令的参数表里了")
                self.assertNotIn(flag, rows.get(name, set()),
                                 f"{entry} 已经登台了，这条例外该删")

    def test_every_exception_says_what_to_do(self):
        for k, why in NOT_ADVERTISED.items():
            with self.subTest(k=k):
                self.assertIn("出路", why, f"{k} 没说什么时候能删")

    def test_every_flag_taught_in_prose_is_listed(self):
        bad = []
        for name in sorted(_rows()):
            p = ROOT / "workflows" / f"{name}.md"
            if not p.is_file():
                continue
            t = p.read_text(encoding="utf-8")
            listed = _listed(name)
            for f in sorted(set(re.findall(r"用\s*`(--[a-z][a-z-]+)`", t))):
                if f not in listed:
                    bad.append(f"/{name} {f}")
        self.assertEqual(
            bad, [],
            "正文教人用这几面旗子，而这条命令自己的参数表里没有：" + "; ".join(bad))


if __name__ == "__main__":
    unittest.main()
