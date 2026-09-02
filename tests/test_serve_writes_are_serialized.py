"""总览页的写入请求必须串行——否则两次点击会静默丢一次。

## 每请求一线程 + 读-改-写 = 丢更新

`serve.py` 用的是 `ThreadingHTTPServer`（每请求一个线程），而四个写入端点做的
都是**读-改-写整份文件**：

| 端点 | 改什么 |
|---|---|
| `/api/skip` `/api/restore` | 整份读出 `seen_jobs.json`，改一个条目，整份写回 |
| `/api/status` `/api/status/undo` | 整份读出台账 CSV，改一行，整份写回 |

两个请求同时进来，各读到同一份、各写回自己那份——**后写的把先写的盖掉**。

实测（两个线程各追加一行台账）：

    两次点击后，台账里有几行: 1 （应为 2）

**没有任何报错**。用户连着点了两个岗的「我投了」，只生效了一个，而他看到的是
两次都成功。人手点看似撞不上，可页面上这几个按钮本来就是连着点的，
两次请求相隔几十毫秒很正常。

原来只有 `_REGEN_LOCK`，护的是**派生快照**的重新生成；上游数据本身没人护。

## 判据

- 源码里四个写入端点必须在 `_WRITE_LOCK` 之下。
- 行为上：并发写同一份台账，条数不能少。
"""

import re
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import serve  # noqa: E402
import tracker as tk  # noqa: E402

SERVE_SRC = (ROOT / "tools" / "serve.py").read_text(encoding="utf-8")


def write_endpoints() -> tuple:
    """从 do_POST 的源码里**派生**写入端点清单，不再手工维护。

    手工清单的问题：新增一个写端点时默认没人守——清单不更新，缩进扫描就
    不看它，锁漏挂也是绿的。派生自 `path == "/api/…"` 的路由判断，
    新端点一写进路由就自动进入扫描面。
    """
    i = SERVE_SRC.index("def do_POST")
    j = SERVE_SRC.index("def ", i + 10)
    return tuple(re.findall(r'path == "(/api/[^"]+)"', SERVE_SRC[i:j]))


WRITE_ENDPOINTS = write_endpoints()


class WriteRequestsAreSerialized(unittest.TestCase):

    def test_the_endpoint_list_is_derived_and_nonempty(self):
        """控制用例：派生出的端点清单至少要有已知的四个——正则失效时空清单
        会让缩进扫描在零个端点上恒绿。"""
        for ep in ("/api/skip", "/api/restore", "/api/status", "/api/status/undo"):
            self.assertIn(ep, WRITE_ENDPOINTS,
                          f"从 do_POST 派生的端点清单里没有 {ep}——派生正则失效了")

    def test_the_lock_exists(self):
        """控制用例：锁还在，否则下面两条无从谈起。"""
        self.assertTrue(
            hasattr(serve, "_WRITE_LOCK"),
            "serve.py 里没有 `_WRITE_LOCK` 了——写入请求又变成并发的了")

    def test_all_write_endpoints_are_under_the_lock(self):
        """四个写入端点都要落在 `with _WRITE_LOCK:` 的块里。

        判据取缩进：`with _WRITE_LOCK:` 之后、缩进没有退回去之前的那一段。
        """
        lines = SERVE_SRC.splitlines()
        guarded, depth = set(), None
        for line in lines:
            stripped = line.strip()
            indent = len(line) - len(line.lstrip())
            if stripped.startswith("with _WRITE_LOCK"):
                depth = indent
                continue
            if depth is not None:
                if stripped and indent <= depth:
                    depth = None            # 块结束
                    continue
                for ep in WRITE_ENDPOINTS:
                    if f'"{ep}"' in line:
                        guarded.add(ep)
        missing = [e for e in WRITE_ENDPOINTS if e not in guarded]
        self.assertEqual(
            missing, [],
            f"这些写入端点不在 `_WRITE_LOCK` 块里：{missing}"
            "\n它们都是读-改-写整份文件，并发时后写的会盖掉先写的，而且不报错。")

    def test_the_regen_lock_is_a_different_one(self):
        """两把锁各管各的：这把护上游数据，那把护派生快照。合成一把会互相拖慢。"""
        self.assertTrue(hasattr(serve, "_REGEN_LOCK"))
        self.assertIsNot(serve._WRITE_LOCK, serve._REGEN_LOCK,
                         "两把锁变成同一个了——加锁顺序的推理要重做")

    def test_concurrent_appends_do_not_lose_rows(self):
        """行为判据：并发追加，一行都不能少。

        不加锁时这条**会红**——控制用例在下面单独证明了这一点。
        """
        p = Path(tempfile.mkdtemp()) / "job_search_tracker.csv"
        p.write_text("date,company,role,status,notes\n", encoding="utf-8")

        # ⚠️ 分工说明：这条证明的是「_WRITE_LOCK 能把这种读-改-写串行化」
        # （锁是测试自己拿的）；「端点真的拿了这把锁」由上面的缩进扫描 +
        # 派生端点清单负责。两条合起来才是完整的链——单看这一条它只是
        # 锁的机理演示，不是端点行为验证。
        def click(name):
            with serve._WRITE_LOCK:
                cols, rows = tk.load(p)
                time.sleep(0.01)
                rows.append({c: "" for c in cols} | {
                    "date": "2026-08-04", "company": name,
                    "role": "产品经理", "status": "applied", "notes": "x"})
                tk.save(p, cols, rows)

        ts = [threading.Thread(target=click, args=(f"公司{i}",)) for i in range(4)]
        for t in ts:
            t.start()
        for t in ts:
            t.join()
        _, rows = tk.load(p)
        self.assertEqual(
            len(rows), 4,
            f"4 次并发写只剩 {len(rows)} 行——写入没有被串行化")

    def test_without_the_lock_it_really_loses_rows(self):
        """控制用例：证明这个竞态是真的，不是我想象出来的。

        同样的并发，**不加锁**跑一遍。这条断言「至少丢一行」——它依赖时序，
        所以给了较长的让出窗口，让竞态稳定复现。
        """
        p = Path(tempfile.mkdtemp()) / "t.csv"
        p.write_text("date,company,role,status,notes\n", encoding="utf-8")

        def click(name):
            cols, rows = tk.load(p)
            time.sleep(0.05)                      # 都读到同一份
            rows.append({c: "" for c in cols} | {
                "date": "2026-08-04", "company": name,
                "role": "产品经理", "status": "applied", "notes": "x"})
            tk.save(p, cols, rows)

        ts = [threading.Thread(target=click, args=(f"公司{i}",)) for i in range(4)]
        for t in ts:
            t.start()
        for t in ts:
            t.join()
        _, rows = tk.load(p)
        self.assertLess(
            len(rows), 4,
            "不加锁竟然一行没丢？那这个竞态的前提要重新确认——"
            "本测试拦的可能是一个并不存在的问题")


if __name__ == "__main__":
    unittest.main()
