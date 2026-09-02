# -*- coding: utf-8 -*-
"""同一面 `--today`，五个工具三种脾气 —— 其中两种是失效在放行那一边。

实测 2026-09-01，`--today 不是日期`：

    archive          ValueError: Invalid isoformat string     裸栈回溯，码 1
    followups        TypeError: NoneType - datetime.date      裸栈回溯，码 1
    applied_jds      只报覆盖情况。要出清单加 --apply           **码 0**
    query_yield      试运行，未写盘（加 --apply 生效）          **码 0**
    score            试运行，没有写盘。确认无误后加 --apply     **码 0**

后三个不报错、不停下，而算出来的东西是错的：

- `query_yield` 把那串垃圾当成日期**字符串**参与比较（`first_seen` 也是字符串，
  而汉字的码位比数字大 —— 比较结果整个反过来）；
- `score` 在 `--apply` 那条路上把它**写进用户的评估正文**：
  「⚠️ 不是日期 `score.py` 现算订正：…」，那段字面板上看得见，而且留在盘上。

栈回溯那两个也不合规 —— `_cli.pick_user` 的说明里写着「新用户第一次撞见的
不该是栈回溯」。

## 判据

正本 `_cli.parse_today`：给了就必须是 `YYYY-MM-DD`，否则一句人话 + 退出码 2；
没给返回 `None`，**默认值由调用方自己定**（多数是今天，`query_yield` 是
「最近一次抓到的那天」，那个默认不能被这次统一抹掉）。

退出码 2 和 `portal_budget` 认不出渠道名时同一个：**1 是「这件事此刻不能做」，
2 是「你打错了，改命令再来」**。
"""
import datetime as dt
import os
import pathlib
import subprocess
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tests"))
from _live import user_or_skip  # noqa: E402
import _cli  # noqa: E402

#: 收 `--today` 的那几个工具。加新的就往这儿加一行。
TOOLS = ("applied_jds", "archive", "followups", "query_yield", "score")


def run(tool, *args):
    r = subprocess.run([sys.executable, str(ROOT / "tools" / f"{tool}.py"),
                        *args], cwd=ROOT, capture_output=True, text=True,
                       encoding="utf-8", errors="replace",
                       env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
    return r.returncode, (r.stdout or "") + (r.stderr or "")


class TheParserIsTheOneHome(unittest.TestCase):

    def test_a_real_date_comes_back(self):
        self.assertEqual(_cli.parse_today("2026-08-21"), dt.date(2026, 8, 21))

    def test_empty_means_the_caller_decides(self):
        """返回 `None`，不是今天 —— `query_yield` 的默认不是今天。"""
        for empty in ("", None, "   "):
            with self.subTest(empty=empty):
                self.assertIsNone(_cli.parse_today(empty))

    def test_a_non_date_stops_with_code_two(self):
        with self.assertRaises(SystemExit) as cm:
            _cli.parse_today("不是日期")
        self.assertEqual(cm.exception.code, 2,
                         "码 1 是「此刻不能做」，打错名字要的是「改命令再来」")

    def test_a_near_miss_is_still_refused(self):
        """像日期但不是日期的，最容易被放过。

        ⚠️ **`20260821` 不在这张单子上** —— 它是合法的 ISO 8601 基本格式，
        `date.fromisoformat` 从 3.11 起就认（第一版把它当成错例，红的是我的
        前提不是代码）。挡掉一个真日期比放过一个假日期更糟。
        """
        for bad in ("2026/08/21", "2026-8-21x", "2026-8-21", "2026-13-01",
                    "昨天", "-1"):
            with self.subTest(bad=bad):
                with self.assertRaises(SystemExit):
                    _cli.parse_today(bad)

    def test_the_basic_form_is_a_real_date(self):
        """反面：`20260821` 得原样收下。"""
        self.assertEqual(_cli.parse_today("20260821"), dt.date(2026, 8, 21))


class EveryToolRefusesTheSameWay(unittest.TestCase):

    def test_a_bad_date_is_refused_everywhere(self):
        user_or_skip()   # 没有真实数据可读时 skip（见 tests/_live.py）
        for t in TOOLS:
            with self.subTest(tool=t):
                code, out = run(t, "--today", "不是日期")
                self.assertEqual(code, 2, f"{t} 收下了一个不是日期的日期：{out[:90]}")

    def test_nobody_shows_a_traceback(self):
        """`pick_user` 那条约束：第一次撞见的不该是栈回溯。"""
        user_or_skip()   # 没有真实数据可读时 skip（见 tests/_live.py）
        for t in TOOLS:
            with self.subTest(tool=t):
                _code, out = run(t, "--today", "不是日期")
                self.assertNotIn("Traceback", out)
                self.assertIn("YYYY-MM-DD", out, "没说清要什么格式")

    def test_it_is_caught_before_any_early_return(self):
        """**这一条是那两个「码 0」的根因。**

        `applied_jds` 与 `score` 都有「只报不写」的早退路径，而校验原来写在
        写盘那一步 —— 敲错日期的人先拿到一份看着正常的输出，错误藏在
        `--apply` 后面。所以不加 `--apply` 也必须当场红。
        """
        for t in ("applied_jds", "score"):
            with self.subTest(tool=t):
                code, _out = run(t, "--today", "不是日期")
                self.assertEqual(code, 2, f"{t} 不加 --apply 时没验")

    def test_a_real_date_still_works(self):
        """反向支点：别为了挡住错的把对的也挡了。"""
        for t in TOOLS:
            with self.subTest(tool=t):
                code, out = run(t, "--today", "2026-08-21")
                self.assertNotEqual(code, 2, f"{t} 把一个真日期当成打错了：{out[:90]}")


class TheDefaultsAreNotFlattened(unittest.TestCase):
    """统一的是「给了要合法」，不是「不给一律算今天」。"""

    def test_query_yield_keeps_its_own_default(self):
        """它的默认是「最近一次抓到的那天」，不是今天 —— 抹掉就把词表产出
        按错误的时间轴切了。"""
        src = (ROOT / "tools" / "query_yield.py").read_text(encoding="utf-8")
        i = src.index("_today.isoformat() if _today else")
        self.assertIn("first_seen", src[i:i + 200],
                      "query_yield 的默认被换成今天了")


class TheDryRunNoteHasOneWording(unittest.TestCase):
    """顺带逮到的第八份：`query_yield` 自己写了一句「试运行，未写盘」。"""

    def test_it_uses_the_shared_sentence(self):
        user_or_skip()   # 没有真实数据可读时 skip（见 tests/_live.py）
        code, out = run("query_yield")
        self.assertEqual(code, 0, out[:120])
        self.assertIn(_cli.DRY_RUN_NOTE, out,
                      "又是一种「试运行」的说法")
        self.assertNotIn("未写盘（加 --apply 生效）", out)


if __name__ == "__main__":
    unittest.main()
