# -*- coding: utf-8 -*-
"""面板上每个写盘按钮，点下去屏幕上**必须立刻有东西变**。

## 为什么要一条扫描，而不是再写一条钉某个按钮的判据

用户为同一件事报了四次（`test_marking_applied_is_instant.py` 记着前三次，
2026-09-02 是第四次：「点了 我投了，怎么没乐观更新，还是要等几秒」）。
那份判据把「我投了」这一条钉得很死 —— 而修完之后机械扫一遍才发现：
**八个写盘按钮里只有两个是乐观的**，另外六个点下去屏幕上一个字不变：

    Portals.toggle / JobPrefs.toggle          开关不动、还变灰
    Portals.markRefreshed / Portals.unblock   同上
    JobReadout.undo / JobReadout.saveReason   同上

一条一条钉，只会在用户报第五次、第六次的时候才补上第五条、第六条。
所以这里钉的是**形状**：凡是 `await post*(...)`，那之前必须已经动过界面。

## 那几秒是从哪来的

`serve.py` 写完盘在**响应之前**同步跑导出子进程（`regenerate()`），
2026-09-02 实测 3.4-4.2 秒（起进程 + import 只占 353ms，其余是真在算）。
这条判据不管它快不快 —— **快慢是服务端的事，点下去有没有反应是前端的事**，
把两者绑在一起正是那四次报障的根源。

## 判据

「动过界面」= `await` 之前出现过 `setXxx(` 或 `onChanged?.(`，
**但 `setBusy` / `setErr` / `setStatusErr` 这类不算**：它们只把控件转起来或
变灰，屏幕上的内容一个字没变 —— 那正是用户说的「点了没反应」。

⚠️ **乐观更新必须配回滚**，否则就是「界面说记上了，盘上没有」，比慢更糟。
回滚由 `catch` 里那一支负责，这条一并钉。
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web" / "src"

#: `async function foo(` 与 `const foo = async (` 两种写法
_FN = re.compile(r"(?:async function (\w+)|const (\w+)\s*=\s*async)\s*\(")
_POST = re.compile(r"await\s+(post\w+)\(")
#: 「我在忙」不是「内容变了」。
_SPIN = re.compile(r"set(Busy|StatusErr|Err|Error|Loading|Saving|Pending)\(")
_TOUCH = re.compile(r"set[A-Z]\w*\(|onChanged\?\.\(")

#: 豁免要写理由，且要写清楚**用户点下去看到的是什么**。
#: 空着是件好事：现在八个写盘按钮全是乐观的。
EXEMPT: dict[str, str] = {}


def _handlers():
    """(文件名, 函数名, await 之前的片段, 整个函数体)，只挑真的写盘的那些。"""
    for path in sorted(WEB.rglob("*.tsx")):
        text = path.read_text(encoding="utf-8")
        for m in _FN.finditer(text):
            name = m.group(1) or m.group(2)
            body = "\n".join(text[m.start():].splitlines()[:70])
            end = body.find("\n  }")
            body = body[:end] if end > 0 else body
            post = _POST.search(body)
            if post:
                yield path.name, name, body[:post.start()], body


def _code(body: str) -> str:
    """剥掉 `//` 注释。

    这个仓库的常客：断言撞上**解释这条规则的那句注释**。本文件正文里就写着
    `setBusy`、`onChanged?.(` 这些词，不剥就会把注释当成代码读。
    """
    return re.sub(r"//[^\n]*", "", body)


class EveryWriteButtonAnswersImmediately(unittest.TestCase):

    def test_there_are_handlers_to_check(self):
        """控制组：真扫到了东西。

        没有它，哪天正则跟不上写法的变化（比如换成箭头函数的另一种写法），
        这条会一声不响地变成永远绿 —— 而它守的正是「静默失效」这一类。
        """
        found = list(_handlers())
        self.assertGreaterEqual(
            len(found), 6,
            f"只扫到 {len(found)} 个写盘处理函数 —— 多半是正则跟不上写法了")

    def test_the_screen_changes_before_the_write(self):
        for file, name, before, _ in _handlers():
            with self.subTest(handler=f"{file}:{name}"):
                if name in EXEMPT:
                    continue
                touched = [t for t in _TOUCH.findall(_code(before))
                           if not _SPIN.match(t)]
                self.assertTrue(
                    touched,
                    f"{file} 的 {name}() 在 `await post…` 之前什么都没改 —— "
                    f"点下去屏幕上一个字不变，要等写盘回来（实测 3.4-4.2 秒）。"
                    f"照 `Portals.tsx` 的 `ovOn` 加一层本地覆盖，"
                    f"或在本文件 EXEMPT 里写清为什么这一个不需要")

    def test_it_rolls_back(self):
        """乐观更新配回滚：`catch` 里要把界面改回去，不能只报个错。"""
        for file, name, before, body in _handlers():
            with self.subTest(handler=f"{file}:{name}"):
                if name in EXEMPT:
                    continue
                code = _code(body)
                catch = code[code.find("} catch"):] if "} catch" in code else ""
                rolled = [t for t in _TOUCH.findall(catch)
                          if not _SPIN.match(t)]
                self.assertTrue(
                    rolled,
                    f"{file} 的 {name}() 乐观更新了却没有回滚 —— "
                    f"写盘失败时界面会一直说它成了，而盘上没有。"
                    f"那比慢更糟：他不会再去看第二眼")


if __name__ == "__main__":
    unittest.main()
