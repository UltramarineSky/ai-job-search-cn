# -*- coding: utf-8 -*-
"""往状态字典里写了、却没有任何人读的键。

## 怎么冒出来的

2026-08-29 的用户裁定（`AGENTS.md`「跟进归用户，工具不催」）撤掉了「零回音 →
先催一遍」那一支。撤的时候删干净了**动作**——`resume_unopened` / `chat_first` /
`_why_silent` / `NUDGE` 四件都删了，原地还留了墓碑注释。

**而喂给那一支的那几个数没跟着走。** 它们照旧每次都算、每次都写进
`doctor` 的 `st` 与 `export_web_data` 的 `counts`，而两个 `next_step`
（各自一份，一个给终端一个给面板）**一个都不读**。AST 点了一遍：

    doctor.next_step        读 st 的 17 个键，这 7 个一个都不在里面
    build_dashboard.next_step  读 counts 的 13 个键，同样一个都不在

## 为什么此前没人发现

**几条测试逐字钉着那些赋值语句**（`assertIn('st["chat_decided"] = ...', DR)`），
于是「这个字段还在」永远为真——而它们钉的是**写**，没有一条问过「谁读」。
一个只被「它还在不在」钉着的字段，等于用测试把死代码焊住。

## 这条守卫做什么

按 AST 数每个下标键的写与读。写了没人读的，要么删，要么进下面那张表并写清
**为什么留着、什么时候能删**。表是**例外清单**，不是免死金牌：
`test_the_table_does_not_rot` 会把已经不成立的条目报出来。
"""
import ast
import collections
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

#: 扫这几份 —— 状态字典在它们之间传递。
FILES = ("doctor.py", "build_dashboard.py", "export_web_data.py",
         "serve.py", "followups.py", "audit_pipeline.py", "writeback.py")

#: 写了没人读、而暂时留着的键 → 理由 + 什么时候能删。
#:
#: ⚠️ 每一条都要说清**留着的理由**和**出路**。说不出来的就该删 —— 这张表
#: 存在的意义是让死字段可见，不是让它体面地活下去。
ALLOWED = {
    k: ("2026-08-29 撤掉「零回音 → 先催一遍」那一支之后失去唯一读者。"
        "数据本身没丢：`outcomeStats` 里那几个驼峰字段照常导出、面板逐岗那段"
        "也照常显示（`JobReadout.tsx`「已查看 / 未查看」那一节）。"
        "留着的只是**再抄一遍进内部字典**的那两行。"
        "出路：要么给它一个统计侧的消费点（投后分析那一块，"
        "`AGENTS.md`「跟进归用户，工具不催」明说统计不算催），要么删。")
    for k in ("decided", "direct_decided", "direct_replied", "chat_decided",
              "viewed_direct", "unviewed_direct")
}
ALLOWED["profile_ok"] = (
    "`doctor` 自己算了一遍「搜岗这一档过没过」写进 `st`，而 `next_step` 读的是"
    "`profile_missing`。面板那边 `build_dashboard.next_step` 有个同名**形参**，"
    "两者不是一回事。出路：删掉这一行，或让终端那支也改读它。")


#: 只看这两个**内部状态字典**。
#:
#: 不扫所有下标：导出给面板的那份 payload 也是个 dict，它的键由 TypeScript 读，
#: 按 Python 侧数会一口气报出二十多个假阳性（第一版就是这样）。那一半另有守卫
#: 盯着（`test_no_field_is_written_that_nothing_reads`，它比的是 `types.ts`）。
DICTS = ("st", "counts")


def _census() -> tuple:
    """`(写的次数, 读的次数)`，只数 `st[...]` / `counts[...]`。"""
    store, load = collections.Counter(), collections.Counter()
    for name in FILES:
        tree = ast.parse((ROOT / "tools" / name).read_text(encoding="utf-8"))
        for n in ast.walk(tree):
            if (isinstance(n, ast.Subscript)
                    and isinstance(n.value, ast.Name)
                    and n.value.id in DICTS
                    and isinstance(n.slice, ast.Constant)
                    and isinstance(n.slice.value, str)):
                (store if isinstance(n.ctx, ast.Store) else load)[
                    n.slice.value] += 1
            # `st.get("k")` 也算读 —— 这个仓库两种写法都用。
            if (isinstance(n, ast.Call)
                    and isinstance(n.func, ast.Attribute)
                    and n.func.attr == "get"
                    and isinstance(n.func.value, ast.Name)
                    and n.func.value.id in DICTS
                    and n.args
                    and isinstance(n.args[0], ast.Constant)
                    and isinstance(n.args[0].value, str)):
                load[n.args[0].value] += 1
    return store, load


def _unread() -> list:
    store, load = _census()
    return sorted(k for k, n in store.items() if n and not load[k])


class EveryWrittenKeyHasAReader(unittest.TestCase):

    def test_the_census_sees_plenty(self):
        """**先证明数得到东西。** 抽取器坏掉时下面两条在空集上都为真。"""
        store, load = _census()
        self.assertGreater(len(store), 15, f"只数到 {len(store)} 个写")
        self.assertGreater(len(load), 10, f"只数到 {len(load)} 个读")

    def test_no_new_unread_key(self):
        extra = sorted(set(_unread()) - set(ALLOWED))
        self.assertEqual(
            extra, [],
            "这些键写进去就没人读了 —— 要么删，要么写清为什么留着："
            + repr(extra))

    def test_the_table_does_not_rot(self):
        """表里列了、实际已经有人读（或已经删了）的也要清掉。"""
        gone = sorted(set(ALLOWED) - set(_unread()))
        self.assertEqual(gone, [],
                         "ALLOWED 里这几个已经不是「写了没人读」了：" + repr(gone))

    def test_every_entry_says_what_to_do(self):
        for k, why in ALLOWED.items():
            with self.subTest(k=k):
                self.assertIn("出路", why, f"{k} 没说什么时候能删")


class TheDeadOnesAreTheOnesTheRulingLeftBehind(unittest.TestCase):
    """点名那一批的来历 —— 免得下一个人以为它们本来就该在。"""

    def test_the_tombstone_is_next_to_them(self):
        dr = (ROOT / "tools" / "doctor.py").read_text(encoding="utf-8")
        self.assertIn("跟进归用户，工具不催", dr,
                      "doctor 里没留下那条裁定的出处")

    def test_neither_next_step_reads_them(self):
        """两个 `next_step` 各自一份，一个都不读 —— 这是这条守卫的起点。"""
        import sys
        sys.path.insert(0, str(ROOT / "tools"))
        import build_dashboard as bd  # noqa: E402
        import doctor  # noqa: E402
        for fn in (doctor.next_step, bd.next_step):
            src = __import__("inspect").getsource(fn)
            for k in ("chat_decided", "viewed_direct", "direct_decided"):
                with self.subTest(fn=fn.__name__, k=k):
                    self.assertNotIn(f'"{k}"', src)


if __name__ == "__main__":
    unittest.main()
