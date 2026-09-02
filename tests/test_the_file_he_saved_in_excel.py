# -*- coding: utf-8 -*-
"""他在 Excel 或记事本里改完存回去 —— 编码就不是 UTF-8 了。

中文 Windows 上这是**默认行为**，不是极端情况：Excel 存 CSV 默认 ANSI(cp936)，
记事本存「UTF-8」带 BOM，Windows PowerShell 5 的 `Out-File -Encoding utf8`
也带 BOM —— 而本仓库的主 shell 就是 PowerShell。

实测 2026-09-01：

    台账存成 GBK        13 个工具里只有 followups 甩栈回溯
    职位库带 BOM        13 个里 10 个甩（export_web_data 那个 = 面板出不来）
    职位库存成 GBK      同上

## 判据分两种，因为「猜不猜得起」不同

- **BOM**：`utf-8-sig` 有就剥、没有等同 `utf-8`，**没有任何副作用** —— 透明吃掉。
- **别的编码**：猜不得。猜错了是把一份中文资料读成乱码再据此判断，比停下更坏。
  所以停下（码 2），说清是哪份文件、该怎么办。

## 台账那一侧早有正解，只是有一处没用它

`build_dashboard.load_tracker` 两条都接住了，`export_web_data` 的调用点还写着
「**不要在这里内联一份 DictReader**」。而 `followups.load_rows` 自己开了一份 ——
它接不到那一份是因为 `build_dashboard` 反过来 import 它（取 `parse_date`），
直接引就成环。读法搬进 `_cli`，两边都够得着。
"""
import json
import os
import pathlib
import shutil
import subprocess
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tests"))
from _live import keep_panel_snapshot  # noqa: E402
import _cli  # noqa: E402

USER = "探针用户_编码"
_restore = None

JOB = {"url": "https://www.liepin.com/job/1.shtml", "title": "产品经理",
       "company": "某公司", "status": "ranked", "rank_score": 70,
       "rank_verdict": "值得投", "first_seen": "2026-08-01"}
CSV = ("company,role,status,date,source,notes" + chr(10)
       + "某公司,产品经理,applied,2026-08-10,https://x/1,面了一轮" + chr(10))

#: 都碰这两份文件。加新工具就往这儿加一行。
TOOLS = ("doctor", "export_web_data", "audit_pipeline", "followups", "archive",
         "applied_jds", "gap_split", "prescreen", "stale_materials",
         "writeback", "outreach_header", "trim_opening", "query_yield")


def setUpModule():
    """跑 `export_web_data` 会盖掉共享的面板快照 —— 护住它。

    判据与实测代价见 `_live.keep_panel_snapshot`。**这一份原来漏了
    「干净 clone 上本来就没有快照」那一半**，于是探针那份假快照留在盘上，
    同一个 clone 第二次跑就红。
    """
    global _restore
    _restore = keep_panel_snapshot()


def tearDownModule():
    shutil.rmtree(ROOT / "users" / USER, ignore_errors=True)
    _restore()


def _mk(sj_bytes=None, csv_bytes=None):
    d = ROOT / "users" / USER
    shutil.rmtree(d, ignore_errors=True)
    (d / "job_scraper").mkdir(parents=True)
    (d / "profile").mkdir(parents=True)
    (d / "job_scraper" / "seen_jobs.json").write_bytes(
        sj_bytes or json.dumps({"seen": {"a": JOB}},
                               ensure_ascii=False).encode("utf-8"))
    (d / "job_search_tracker.csv").write_bytes(csv_bytes or CSV.encode("utf-8"))


def run(tool):
    r = subprocess.run([sys.executable, str(ROOT / "tools" / f"{tool}.py"),
                        "--user", USER], cwd=ROOT, capture_output=True,
                       text=True, encoding="utf-8", errors="replace",
                       env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
    return r.returncode, (r.stdout or "") + (r.stderr or "")


class TheJudgeIsOne(unittest.TestCase):

    def test_a_bom_is_eaten_transparently(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d) / "x.json"
            p.write_bytes(json.dumps({"a": 1}).encode("utf-8-sig"))
            self.assertEqual(_cli.read_json(p), {"a": 1})

    def test_plain_utf8_still_works(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d) / "x.json"
            p.write_bytes(json.dumps({"a": 1}).encode("utf-8"))
            self.assertEqual(_cli.read_json(p), {"a": 1})

    def test_another_encoding_stops_with_code_two(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d) / "x.json"
            p.write_bytes(json.dumps({"公司": "某某"},
                                     ensure_ascii=False).encode("gbk"))
            with self.assertRaises(SystemExit) as cm:
                _cli.read_json(p)
            self.assertEqual(cm.exception.code, 2)

    def test_the_tracker_reader_handles_both(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d) / "t.csv"
            p.write_bytes(CSV.encode("utf-8-sig"))
            rows = _cli.read_tracker_rows(p)
            self.assertEqual(rows[0]["company"], "某公司",
                             "BOM 让第一列的列名带上了那个不可见字符")
            p.write_bytes(CSV.encode("gbk"))
            self.assertEqual(_cli.read_tracker_rows(p), [],
                             "GBK 台账该降级成空，而不是抛")


class NoToolShowsATraceback(unittest.TestCase):

    def test_a_gbk_tracker(self):
        _mk(csv_bytes=CSV.encode("gbk"))
        for t in TOOLS:
            with self.subTest(tool=t):
                _c, out = run(t)
                self.assertNotIn("Traceback", out)

    def test_a_bom_store(self):
        _mk(sj_bytes=json.dumps({"seen": {"a": JOB}},
                                ensure_ascii=False).encode("utf-8-sig"))
        for t in TOOLS:
            with self.subTest(tool=t):
                code, out = run(t)
                self.assertNotIn("Traceback", out)
                self.assertNotEqual(code, 2, "BOM 该被透明吃掉，不该停下")

    def test_a_gbk_store_stops_but_says_why(self):
        _mk(sj_bytes=json.dumps({"seen": {"a": JOB}},
                                ensure_ascii=False).encode("gbk"))
        for t in TOOLS:
            with self.subTest(tool=t):
                _c, out = run(t)
                self.assertNotIn("Traceback", out)
        _c, out = run("export_web_data")
        self.assertIn("不是 UTF-8", out)
        self.assertIn("另存为 UTF-8", out, "没告诉他怎么办")

    def test_the_control_group_is_clean(self):
        """**先证明夹具跑得通。** 全 UTF-8 时不许有人喊。"""
        _mk()
        for t in TOOLS:
            with self.subTest(tool=t):
                _c, out = run(t)
                self.assertNotIn("Traceback", out)
                self.assertNotIn("不是 UTF-8", out)


class TheTrackerReaderHasOneHome(unittest.TestCase):

    def test_followups_does_not_open_its_own(self):
        """它原来自己 `DictReader`，BOM 接住了、`UnicodeDecodeError` 没接。

        ⚠️ **只看代码，把 docstring 摘掉再判。** 第一版按源码文本扫 ——
        而那个函数的说明里正写着「原来这里自己 `DictReader`」，
        断言当场红在**解释它为什么不该这么写的那句话**上。
        这个仓库为同一脚交过好几次学费。
        """
        import ast
        src = (ROOT / "tools" / "followups.py").read_text(encoding="utf-8")
        fn = next(n for n in ast.walk(ast.parse(src))
                  if isinstance(n, ast.FunctionDef) and n.name == "load_rows")
        body = fn.body[1:] if (isinstance(fn.body[0], ast.Expr) and isinstance(
            getattr(fn.body[0], "value", None), ast.Constant)) else fn.body
        code = chr(10).join(ast.unparse(x) for x in body)
        self.assertNotIn("DictReader", code, "又自己开了一份")
        self.assertIn("read_tracker_rows", code)

    def test_the_old_name_still_works(self):
        """八个调用方引的是 `load_tracker` 这个名字，壳得留着。"""
        import build_dashboard as bd
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d) / "t.csv"
            p.write_bytes(CSV.encode("utf-8-sig"))
            self.assertEqual(bd.load_tracker(p)[0]["role"], "产品经理")


if __name__ == "__main__":
    unittest.main()
