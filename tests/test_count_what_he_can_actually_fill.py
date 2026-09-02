# -*- coding: utf-8 -*-
"""「库里有姓的 6 个直接取」—— 台账那 88 行里对得上的只有 1 行。

`check_tracker_columns_nobody_fills` 报「`contact_person` 在 88 行里填了 0 行」，
后面接一句怎么补。那句话由 `_surname_note` 拼，而它数的是**职位库里有几个姓** ——
读的人自然理解成「这 88 行里有 6 行能直接补」。

实测 2026-09-01：按 `source` 链接对得上、且职位库有姓的台账行，**只有 1 行**。
另外 5 个姓挂在他从没投过的岗上，台账里根本没有对应的行，补无可补。

## 这条理由是这个函数自己写下的

上一版立它时的原话：

> 原来那句无条件写「猎聘的岗库里就有，直接取」—— 对 99% 的岗是句假话，
> 而假话的代价不是这一次白翻，是他下次连这条建议一起不信。
> **能取到几个就说几个。**

当时把「库里有没有」当成了「补得上几个」，只学到一半 —— 于是同一个毛病用一个
**差 6 倍**的数又犯了一次，就摆在「补它：」那句话里。
"""
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import audit_pipeline as ap  # noqa: E402


def _seen(*surnames_by_url):
    """`(链接, 姓)` 若干 → 一份职位库。姓给空串表示这个岗没记到姓。"""
    return {f"k{i}": {"url": u, "title": f"岗{i}", "company": "c",
                      "recruiterSurname": s}
            for i, (u, s) in enumerate(surnames_by_url)}


def _rows(*urls):
    return [{"company": "c", "role": "r", "source": u} for u in urls]


class ItCountsTheRowsHeCanFill(unittest.TestCase):

    def test_it_says_the_matched_number_not_the_store_number(self):
        """库里 3 个姓，台账只对得上 1 行 —— 那句话要说 1。"""
        seen = _seen(("https://x/1", "张"), ("https://x/2", "王"),
                     ("https://x/3", "李"))
        got = ap._surname_note(seen, _rows("https://x/1", "https://x/9"))
        self.assertIn("1 行能从职位库直接取", got,
                      "又拿库里那个数当成台账里补得上的数了")
        self.assertIn("库里共 3 个姓", got, "另外那几个去哪了要交代")

    def test_none_matching_says_so_plainly(self):
        """一行都对不上时，别把人指向职位库 —— 他翻不到，下次连这条也不信。"""
        seen = _seen(("https://x/1", "张"), ("https://x/2", "王"))
        got = ap._surname_note(seen, _rows("https://x/8", "https://x/9"))
        self.assertIn("一个都对不上", got)
        self.assertNotIn("直接取", got, "对不上还叫人去取")

    def test_an_empty_store_still_says_the_old_thing(self):
        """支点：库里一个姓都没有那一支不许被这次改动带掉。"""
        got = ap._surname_note(_seen(("https://x/1", "")), _rows("https://x/1"))
        self.assertIn("一个姓都没有", got)

    def test_an_old_caller_does_not_get_a_tracker_claim(self):
        """`rows` 传不进来时**明说那是库里的数**，不装成台账的。"""
        got = ap._surname_note(_seen(("https://x/1", "张")))
        self.assertIn("职位库里有 1 个姓", got)
        self.assertNotIn("行能从", got, "没有台账还敢说「几行能补」")

    def test_the_url_match_is_normalised(self):
        """`http` 与 `https` 是同一个岗 —— 按 `norm_url` 对，不按字面。

        那是 `norm_url` 的头号用例（智联那次：页面给 `http://`、库里存的是
        `https://`，20 个新岗里 4 个重复入库）。按字面比的话，这一行本来
        补得上、却会被算成「对不上」。

        ⚠️ **别拿查询串当例子。** 第一版写的是 `?from=list` —— `norm_url`
        按设计不剥它（剥了会把某些平台上不同的岗并成一个），于是那一版红的
        是我的前提，不是代码。
        """
        seen = _seen(("http://x/1", "张"))
        got = ap._surname_note(seen, _rows("https://x/1"))
        self.assertIn("1 行能从职位库直接取", got)


class TheLiveMessageUsesIt(unittest.TestCase):

    def test_the_check_hands_it_the_tracker_rows(self):
        """光改函数没用 —— 调用点不把台账传进去，它还是走老那一支。

        钉行为：造一份「库里 3 个姓、台账只对得上 1 行」的语料，跑真检查，
        看它印出来的是 1 还是 3。第一版钉的是源码里那一行
        `_surname_note(seen, rows)`，被 `test_a_guard_pins_behaviour_not_a_line`
        拦下 —— 拦得对，换个写法它就红，而行为一点没变。
        """
        import shutil
        import unittest.mock as _m
        seen = _seen(("https://x/1", "张"), ("https://x/2", "王"),
                     ("https://x/3", "李"))
        # ⚠️ **不能把 `ROOT` 搬到临时目录。** 这条检查要在 `workflows/` 与
        # `tools/` 里数「有几处在读这一列」，读者少于两个就不报 —— 搬走之后
        # 那两棵树是空的，检查一声不响，而断言会红在「语料没构造对」上。
        # 第一版就是这么红的。所以在**真仓库**下开一个临时用户。
        name = "临时用户_数得对不对"
        udir = ROOT / "users" / name
        shutil.rmtree(udir, ignore_errors=True)
        udir.mkdir(parents=True)
        try:
            # 台账：两行，只有一行对得上库里那个带姓的岗；
            # `contact_person` 整列空着，正是这条检查要报的形状。
            (udir / "job_search_tracker.csv").write_text(
                "company,role,status,date,source,contact_person" + chr(10)
                + "甲,岗,applied,2026-09-01,https://x/1," + chr(10)
                + "乙,岗,applied,2026-09-01,https://x/9," + chr(10),
                encoding="utf-8")
            with _m.patch.object(ap._cli, "pick_user", lambda *a, **k: name):
                rows = ap.check_tracker_columns_nobody_fills(seen, {})
        finally:
            shutil.rmtree(udir, ignore_errors=True)
        hit = [r for r in rows if "contact_person" in r[2]]
        self.assertTrue(hit, "这条检查没报出那一列 —— 语料没构造对")
        self.assertIn("1 行能从职位库直接取", hit[0][2],
                      "调用点没把台账行传进去，印的还是库里那个数")


if __name__ == "__main__":
    unittest.main()
