"""`serve.py` 的静态文件守卫要做「在目录里」，不是「字符串以它开头」。

## 前缀匹配挡不住同级目录

`serve.py` 的 docstring 承诺：

> 静态文件只从 `web/dist/` 取，路径要落在该目录内（挡 `../` 穿越）。

实现原来是：

    target = (DIST / path.lstrip("/")).resolve()
    if not str(target).startswith(str(DIST.resolve())):

`str.startswith` 比的是**字符串前缀**，不是路径包含。`DIST` 是 `web/dist` 时：

| 请求 | 解析成 | 前缀匹配 | 真的在 dist 里？ |
|---|---|---|---|
| `/index.html` | `web/dist/index.html` | 放行 | 是 |
| `/../../.active_user` | `<repo>/.active_user` | 拦住 | 否 |
| **`/../dist-evil/secret.txt`** | `web/dist-evil/secret.txt` | **放行** | **否** |
| **`/../dist2/x`** | `web/dist2/x` | **放行** | **否** |

两者只在**同级、同前缀**时分岔——而那正是穿越要利用的那一档。

## 影响有多大：如实说

- 服务只绑 `127.0.0.1`，GET 不带 token 也不校验 Origin，但**跨源读不到响应**
  （CORS），所以别的网站拿不走内容。
- 当前 `web/` 下也没有以 `dist` 开头的同级目录。

所以这是**潜在弱点，不是当下可利用的漏洞**。修它的理由是：这是仓库里唯一有网络面的
组件，而它的守卫没做到自己 docstring 承诺的事——差距本身就该消掉，不该等到某天
有人加了个 `web/dist-old/` 才发现。

## 判据

`Path.is_relative_to`（Python 3.9+，本仓库要求 3.10+）就是「在这个目录里」的正解。
下面用真实路径逐条比对，并显式钉住那两个前缀匹配会漏的例子。
"""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

SERVE = ROOT / "tools" / "serve.py"

#: (请求路径, 应不应该放行)
CASES = [
    ("/index.html", True),
    ("/assets/app.js", True),
    ("/../../.active_user", False),
    ("/../dist-evil/secret.txt", False),   # 前缀匹配会放行的那一档
    ("/../dist2/x", False),                # 同上
    ("/../public/data.json", False),
]


def resolves_inside(dist: Path, req: str) -> bool:
    """按 serve.py 现在的判据算一遍。"""
    target = (dist / req.lstrip("/")).resolve()
    return target.is_relative_to(dist.resolve())


class StaticFilesStayInsideDist(unittest.TestCase):

    def test_the_implementation_uses_containment_not_prefix(self):
        """源码里必须是 `is_relative_to`，不能退回 `startswith`。

        行为判据（下一条）用的是本文件自己的实现，源码换回 `startswith` 它也不会红——
        所以这一条直接盯源码。
        """
        src = SERVE.read_text(encoding="utf-8")
        self.assertIn(
            "is_relative_to", src,
            "serve.py 不再用 `is_relative_to` 判包含了——"
            "换回 `str().startswith()` 的话，同级的 `dist-evil/` 会被放行")
        # 允许 docstring/注释里出现 startswith（它正是在讲这个反例），
        # 只禁它出现在**判据那一行**。
        bad = [f"serve.py:{i}  {l.strip()[:70]}"
               for i, l in enumerate(src.splitlines(), 1)
               if "startswith(str(DIST" in l]
        self.assertEqual(
            bad, [], "静态路径判据又用回了字符串前缀匹配：\n  " + "\n  ".join(bad))

    def test_containment_accepts_and_rejects_correctly(self):
        dist = ROOT / "web" / "dist"
        for req, want in CASES:
            with self.subTest(req=req):
                self.assertEqual(
                    resolves_inside(dist, req), want,
                    f"`{req}` 应当{'放行' if want else '拦住'}")

    def test_prefix_matching_really_would_have_leaked(self):
        """控制用例：证明旧判据确实漏——否则本测试拦的是一个想象出来的问题。"""
        dist = (ROOT / "web" / "dist").resolve()
        leaky = "/../dist-evil/secret.txt"
        target = (dist / leaky.lstrip("/")).resolve()
        self.assertTrue(
            str(target).startswith(str(dist)),
            "旧的前缀判据居然拦住了它？那本测试的前提不成立，重新确认")
        self.assertFalse(
            target.is_relative_to(dist),
            "新判据没拦住它——那这次修改没解决问题")


if __name__ == "__main__":
    unittest.main()
