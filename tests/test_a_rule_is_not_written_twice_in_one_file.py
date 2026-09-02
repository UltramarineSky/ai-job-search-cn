# -*- coding: utf-8 -*-
"""同一份文件里，同一句话不许写两遍。

跨文件的重复这个仓库盯了很久（`test_one_value_one_home`、
`test_the_copies_in_doctor_still_match`、`test_shared_vocab_single_source`……），
**而文件自己内部的重复一直没人看**。

## 实测 2026-09-01：一处，而且已经飘了

`job-setup.md` 里新用户看到的**第一屏**招呼写了两份全文 —— `documents/` 里有
文件一份、空的一份 —— 而两份只差三处（文件清单那句、路线 A、路线 C 的尾巴）。

飘的是路线 C：「什么材料都没有的话走这条。」**只长在空的那一份上**，而两份里的
路线 C 本该是同一段话；没有任何地方说过它为什么该不同。

这是新用户看到的第一屏。两份全文各改各的，下一个改措辞的人只会改到其中一份。
改法是骨架写一份、把随情况变的三处单独列出来。

## 判据

同一份文件里，剥掉标记之后**逐字相同**、且长度 ≥ `MIN` 的整句出现两次以上。

- 只扫规则住的地方（`workflows/` 与 `AGENTS.md`）—— README 里
  「详见 SECURITY.md」这种指路重复两次是正常的。
- 代码块整段跳过：命令示例本来就会重复。
- `MIN` 定在 24 字：实测降到 16 字只多出一条「一票否决的条件，和必须满足的
  条件」——那是同一张表的两处列举，不是规则重复。**宁可漏，不可吵。**
"""
import collections
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

#: 短句撞车是正常的（「然后停下」「照实说」），要够长才说明是同一段规则。
MIN = 24

#: 允许在同一份文件里重复的整句 → 理由。**空着是好事。**
#:
#: ⚠️ 往里加之前先问：这两处会不会各改各的？会的话就不该加，该合。
ALLOWED: dict = {}


def _files():
    yield from sorted((ROOT / "workflows").rglob("*.md"))
    yield ROOT / "AGENTS.md"


def _dupes() -> dict:
    """`(文件名, 整句) → 出现次数`，只留出现两次以上的。"""
    out = {}
    for p in _files():
        if not p.is_file():
            continue
        text = re.sub(r"```.*?```", " ", p.read_text(encoding="utf-8"),
                      flags=re.S)
        seen = collections.Counter()
        for raw in re.split(r"[。！？\n]", text):
            s = re.sub(r"[\s*`>|#\-]+", "", raw)
            if len(s) >= MIN:
                seen[s] += 1
        for line, n in seen.items():
            if n > 1:
                out[(p.name, line)] = n
    return out


class NoSentenceIsWrittenTwiceInOneFile(unittest.TestCase):

    def test_the_scan_reads_the_files(self):
        """**先证明扫到了东西。** 读成空的话，下面那条在空集上永远绿。"""
        n = sum(1 for p in _files() if p.is_file())
        self.assertGreater(n, 15, f"只扫到 {n} 份文件")
        # 再证明它真的在拆句子：随便找一份长的，切出来的句子不该是 0。
        big = (ROOT / "workflows" / "job-apply.md").read_text(encoding="utf-8")
        got = [s for s in re.split(r"[。！？\n]", big)
               if len(re.sub(r"[\s*`>|#\-]+", "", s)) >= MIN]
        self.assertGreater(len(got), 100, "切句子那一步八成坏了")

    def test_no_undeclared_duplicate(self):
        bad = sorted(f"{f}：{line[:44]}" for (f, line) in _dupes()
                     if line not in ALLOWED)
        self.assertEqual(
            bad, [],
            "同一份文件里同一句话写了两遍 —— 下一个改措辞的人只会改到一处：\n  "
            + "\n  ".join(bad))

    def test_the_table_does_not_rot(self):
        live = {line for _f, line in _dupes()}
        gone = sorted(set(ALLOWED) - live)
        self.assertEqual(gone, [],
                         "ALLOWED 里这几句已经不重复了：" + repr(gone))


if __name__ == "__main__":
    unittest.main()
