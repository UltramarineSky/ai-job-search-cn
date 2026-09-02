"""投递记录的 BOM 要往返保真，读的一侧也不能漏掉 `utf-8-sig`。

## 用户在 Excel 里存过，点一下按钮就乱码

`job_search_tracker.csv` 是用户真会用 Excel 打开的文件（那是他的投递记录）。
Windows 版 Excel 存 CSV 时会带 UTF-8 BOM；没有 BOM 时它按系统 ANSI
（中文机器上是 GBK）解——**公司名和备注全是乱码**。

`tracker.load()` 读用 `utf-8-sig`（会吃掉 BOM），`tracker.save()` 却一直写 `utf-8`。
于是往返一次 BOM 就没了：

    用户用 Excel 存 → 文件带 BOM
    → 在总览页点一下「我投了」→ save() 写回，BOM 没了
    → 他下次再用 Excel 打开 → 中文乱码

他不会想到那是「点了一下按钮」造成的。

## 读的一侧还有两处漏了 `utf-8-sig`

| 在哪 | 原来 | 带 BOM 时会怎样 |
|---|---|---|
| `build_dashboard.load_tracker` | `utf-8` | **不报错**——BOM 变成第一个字符，第一列列名成了 `\\ufeffdate`，`row.get("date")` 从此返回 `None` |
| `doctor.py` 数投递计数处 | `utf-8` | 同上（它只读 `status`，当前不受影响，但同样是错的） |

`tracker.py` 的注释还一直写着「`build_dashboard.load_tracker` 也是这么读的，
两边保持一致」——**声明的一致性并不存在**。

UTF-8 能正常解码 BOM，所以这一类错**永远不会抛异常**，只会让某一列静默变空。
"""

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import build_dashboard as bd  # noqa: E402
import tracker as tk  # noqa: E402

BOM = b"\xef\xbb\xbf"
CSV = ("date,company,role,status,notes\n"
       "2026-08-01,某某科技,产品经理,applied,首次投递\n")


def write(data: bytes) -> Path:
    p = Path(tempfile.mkdtemp()) / "job_search_tracker.csv"
    p.write_bytes(data)
    return p


class BomSurvivesTheRoundTrip(unittest.TestCase):

    def test_a_bom_file_keeps_its_bom(self):
        p = write(BOM + CSV.encode("utf-8"))
        cols, rows = tk.load(p)
        tk.save(p, cols, rows)
        self.assertEqual(
            p.read_bytes()[:3], BOM,
            "带 BOM 的台账写回后 BOM 没了——用户下次用 Excel 打开就是乱码，"
            "而他只是在页面上点了一下按钮。")

    def test_a_plain_file_does_not_gain_a_bom(self):
        """反向：不主动给所有文件加 BOM，那是改格式不是修 bug。"""
        p = write(CSV.encode("utf-8"))
        cols, rows = tk.load(p)
        tk.save(p, cols, rows)
        self.assertNotEqual(p.read_bytes()[:3], BOM, "凭空给文件加了 BOM")

    def test_the_content_survives_too(self):
        """控制用例：别为了保 BOM 把内容写坏了。"""
        for data in (CSV.encode("utf-8"), BOM + CSV.encode("utf-8")):
            with self.subTest(bom=data.startswith(BOM)):
                p = write(data)
                cols, rows = tk.load(p)
                tk.save(p, cols, rows)
                _, again = tk.load(p)
                self.assertEqual(again[0]["company"], "某某科技")
                self.assertEqual(again[0]["date"], "2026-08-01")


class EveryReaderHandlesTheBom(unittest.TestCase):

    def test_load_tracker_reads_the_first_column(self):
        """`build_dashboard.load_tracker` 带 BOM 时也要读得到第一列。

        这一条**不会**因为编码错误而失败——UTF-8 能解码 BOM。它失败的样子是
        `date` 悄悄变成 `None`，所以判据直接盯那一列。
        """
        for data in (CSV.encode("utf-8"), BOM + CSV.encode("utf-8")):
            with self.subTest(bom=data.startswith(BOM)):
                rows = bd.load_tracker(write(data))
                self.assertTrue(rows, "一行都没读到")
                self.assertEqual(
                    rows[0].get("date"), "2026-08-01",
                    "第一列读成 None 了——多半是用 `utf-8` 而不是 `utf-8-sig` 读的，"
                    "BOM 粘在了列名上（`\\ufeffdate`）")

    def test_the_readers_declare_utf8_sig(self):
        """源码层面钉住：三个读取方都要写 `utf-8-sig`。

        行为判据只覆盖 `load_tracker`；`doctor.py` 那处只读 `status`，
        带 BOM 时行为上看不出差别——但它同样是错的，将来读第一列就会踩。
        """
        # ⚠️ **台账那份读法 2026-09-01 搬进了 `_cli.read_tracker_rows`。**
        # `build_dashboard.load_tracker` 现在是薄壳（八个调用方引的是那个名字），
        # 所以 `utf-8-sig` 这几个字在它里面已经没有了 —— 行为没变，上面那条
        # 现算的照样绿。搬家的理由：`followups` 反过来被 build_dashboard
        # import（取 `parse_date`），够不着那一份，于是自己开了一份、
        # 又漏接 `UnicodeDecodeError`（GBK 台账上 13 个工具只有它甩栈回溯）。
        for rel, marker in (("tools/_cli.py", "utf-8-sig"),
                            ("tools/doctor.py", "utf-8-sig"),
                            ("tools/tracker.py", "utf-8-sig")):
            with self.subTest(f=rel):
                self.assertIn(
                    marker, (ROOT / rel).read_text(encoding="utf-8"),
                    f"{rel} 里没有 `utf-8-sig`——Excel 存出来的台账会被读坏，"
                    "而且不报错")


if __name__ == "__main__":
    unittest.main()
