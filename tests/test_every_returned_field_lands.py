# -*- coding: utf-8 -*-
"""子代理交回一个值，而落盘清单里没有它的位置 —— 于是它无声蒸发。

`/job-rank` Step 2 派子代理批量打分，回传一份 JSON。Step 4 负责把它写进
`seen_jobs.json`。两份 schema 分开写，于是它们会分家 —— **本仓库为此栽过三次**：

| 什么 | 后果 |
|---|---|
| `rank_breakdown` 整块 | 五个消费方全在读，而 Step 4 的清单里没有它。照那份清单跑一轮，`/job-upskill` 没数据、面板技能分整列空白 |
| `调整`（四维之外的加减分） | 约定写在用户资料里（「记为『专业减分』」），落盘 schema 里没有字段 —— 129 个岗对不上账，只有 8 个记成了字段 |
| `deadline` | 三条规则等着它（7 天内标 🔥、过期转 `expired`、并列时的第三裁决器），**落盘 0 / 1847**，从上线起一次都没跑过 |

三次的形状完全一样：**产出方给了，消费方在等，中间那张清单没有它。**
而这种失败永远不报错 —— 值就是没了。

## 所以现在有一张映射表

`job-rank.md`「Step 2 回传的每个字段，落在哪」逐字段写明落点，**包括「不落盘」的**
（`key` 是定位用的、`location` 是本轮输出里的事、`language` 只决定材料用什么语言）。
写「不落盘」不是废话：**空着的格和漏掉的行长得一样**，而前者是裁定、后者是事故。

这个文件盯的就是那张表：**回传 schema 里每一个字段，表里都要有一行。**

## deadline 那次还有一层

它此前被当成「改名问题」修过一次 —— 抓取 schema 写 `validThrough`、消费方读
`deadline`，`jd_store.MERGE_RENAME` 把两边接上了。改名是对的，但那修的是**另一条
路**：详情库那边至今 0 覆盖。而评分这条路上值一直是有的，只是没处放。
**同一个字段两条路，只修通了没数的那条。**
"""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RANK = (ROOT / "workflows" / "job-rank.md").read_text(encoding="utf-8")

#: 子对象的名字：它们自己不需要一行，里面的字段各自有落点。
_CONTAINERS = {"hard_gates", "scores"}


def _return_schema() -> str:
    """Step 2 那份回传 JSON —— 用里面独有的键定位，不靠行号。"""
    i = RANK.index('"gate_fail_reason"')
    return RANK[RANK.rfind("```json", 0, i):RANK.index("```", i)]


def _mapping_section() -> str:
    i = RANK.index("### Step 2 回传的每个字段，落在哪")
    j = RANK.find("\n## ", i)
    return RANK[i:j if j > 0 else len(RANK)]


def _mapping_rows() -> str:
    """**只取表格行**，不要整节。

    第一版拿整节去搜，而那一节的引言里就点名了 `deadline`
    （「三条规则等着它，0/1847」）—— 于是把表里那一行整条删掉，测试照样绿。
    变异当场露馅：判据落在散文上，而散文不是落点。
    """
    return "\n".join(ln for ln in _mapping_section().splitlines()
                     if ln.lstrip().startswith("|"))


def _returned_fields() -> list:
    """回传 schema 的**顶层**字段。子对象里的门名/维度名不算 —— 它们
    整块落进 `硬性条件` / 四个同名键，表里各有一行说明。"""
    block = _return_schema()
    out, depth = [], 0
    for line in block.splitlines():
        stripped = line.strip()
        m = re.match(r'"([^"]+)"\s*:', stripped)
        if m and depth == 1:
            out.append(m.group(1))
        depth += line.count("{") - line.count("}")
    return out


class TheRulerLightsUp(unittest.TestCase):
    def test_it_finds_the_return_schema(self):
        self.assertIn('"deadline"', _return_schema())
        self.assertGreater(len(_returned_fields()), 8,
                           f"只解析出 {_returned_fields()} —— 顶层字段没取全")

    def test_it_finds_the_mapping_table(self):
        t = _mapping_rows()
        self.assertIn("| 回传字段 | 落在哪 |", t)
        self.assertGreater(t.count("\n|"), 8, "表里行数太少，多半没截全")


class EveryReturnedFieldHasARow(unittest.TestCase):
    def test_nothing_returned_is_missing_from_the_table(self):
        table = _mapping_rows()
        missing = [f for f in _returned_fields()
                   if f not in _CONTAINERS and f"`{f}`" not in table]
        self.assertEqual(missing, [],
                         "回传 schema 里有这些字段，映射表里却没有它们的行 —— "
                         "值会在 Step 4 蒸发，而且不报错：\n  " + "\n  ".join(missing))

    def test_the_containers_are_accounted_for_too(self):
        """子对象整块落盘，表里也要有一行说清落在哪。"""
        table = _mapping_rows()
        for c in _CONTAINERS:
            with self.subTest(field=c):
                self.assertIn(f"`{c}`", table)

    def test_not_stored_is_spelled_out(self):
        """「不落盘」要写出来 —— 空着的格和漏掉的行长得一样。"""
        table = _mapping_rows()
        self.assertIn("不落盘", table)
        self.assertIn("空着的格和漏掉的行长得一样", _mapping_section())


class TheDeadlineNowHasASlot(unittest.TestCase):
    """它是这条守卫的由头：三个消费者，落盘 0 / 1847。"""

    def test_step_four_says_where_to_write_it(self):
        i = RANK.index("## Step 4：写回状态")
        j = RANK.index("\n---\n", i)
        self.assertIn('"deadline"', RANK[i:j], "Step 4 里还是没有它的位置")

    def test_it_says_not_to_write_a_null_placeholder(self):
        """写 `null` 占位和「读过但没有」分不开。"""
        i = RANK.index("## Step 4：写回状态")
        self.assertIn("别写 `null` 占位", RANK[i:i + 3000])

    def test_the_three_consumers_are_still_there(self):
        """哪天这三条规则没了，这个字段就不必落盘了 —— 那时该改的是表，不是这里。"""
        self.assertIn("7 天内截止的标一个 🔥", RANK)
        self.assertIn("已经过期的把这个岗标成 `expired`", RANK)
        self.assertIn("技能分也相同才看截止日期", RANK)

    def test_the_incident_is_on_record(self):
        i = RANK.index("## Step 4：写回状态")
        seg = RANK[i:i + 3000]
        self.assertIn("0 次", seg)
        self.assertIn("1847", seg, "没记下当时的分母")


if __name__ == "__main__":
    unittest.main()
