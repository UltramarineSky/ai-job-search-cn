# -*- coding: utf-8 -*-
"""「剩 180 个仍需抓 JD 才能评」—— 其中 126 个的正文，详情库里早就有了。

同一件事，两个工具两个数（实测活动用户 2026-08-23）：

    prescreen   剩 180 个仍需抓 JD 才能评
    jd_store    待评的 182 个里有 126 个已有，还需新抓 56 个

`jd_store` 是对的。`prescreen` 把「**要读 JD 才能评**」说成了「**要去抓**」——
这两件事在这套系统里差得很远：

**抓取额度是这里最稀缺的资源**（每次请求之间要隔 8/4/3 秒、撞了风控整站冷却 24 小时、
撞风控冷却 24 小时，`portal_budget` 那一整个文件都在管它）。而
「剩 N 个仍需抓 JD」正是用户决定「今天还抓不抓、抓几轮」时读到的那一句。
**说成 180 而不是 56，把下一步的代价报贵了三倍。**

判据借 `jd_store.status()`，不另数一遍 —— 这个仓库为「同一个概念两份实现」
已经修过好几处（日期解析、脱敏公司名、`n_processed`）。
读不出详情库时**少说那半句**，不猜。
"""
import sys
import unittest
import unittest.mock as mock
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tests"))
import jd_store  # noqa: E402
import prescreen as ps  # noqa: E402
from _srcscan import code_of  # noqa: E402

SRC = (ROOT / "tools" / "prescreen.py").read_text(encoding="utf-8")


class TheTwoThingsAreSaidSeparately(unittest.TestCase):
    def test_the_verb_is_read_not_fetch(self):
        seg = code_of("tools/prescreen.py", "def main(")
        self.assertIn("要读 JD 才能评", seg, "还在说「仍需抓 JD」")
        self.assertNotIn("仍需抓 JD", seg)

    def test_it_says_how_many_really_need_fetching(self):
        seg = code_of("tools/prescreen.py", "def main(")
        self.assertIn("还得先去抓正文", seg, "没把真正要抓的那个数说出来")

    def test_that_number_comes_from_the_store(self):
        """**不另数一遍。** 详情库那边已经有 `status()`，两份实现必然分叉。"""
        seg = code_of("tools/prescreen.py", "def main(")
        self.assertIn("jd_store.status(user)", seg)

    def test_an_unreadable_store_says_nothing(self):
        """读不出就少说那半句，不猜一个数出来。

        **`SystemExit` 也要接。** `jd_store._seen` 在没有职位库时抛的正是它
        （`BaseException` 的子类，`except Exception` 接不住）——第一版就漏了，
        全套当场红 15 条：夹具用户没有职位库，而「少说半句」变成了「整条掀翻」。
        """
        seg = code_of("tools/prescreen.py", "def main(")
        self.assertRegex(seg, r"except \(Exception, SystemExit\):",
                         "详情库读不出时会把整条 prescreen 掀翻")

    def test_nothing_waiting_means_no_second_half(self):
        seg = code_of("tools/prescreen.py", "def main(")
        self.assertIn('if st["new_total"]', seg, "待评为 0 时会印一句废话")


class TheCostIsWrittenDownNextToIt(unittest.TestCase):
    """这半句看起来像凑字数，理由必须挨着写 —— 否则下一个人会把它删掉。"""

    def test_the_reason_names_the_scarce_resource(self):
        # **锚 print 那一行。** 「要读 JD 才能评」这几个字在上面那段注释里
        # 也逐字出现（它就是在解释这句话），`index` 会落在注释里。
        i = SRC.index('f"剩 {todo} 个要读 JD')
        seg = SRC[max(0, i - 1600):i]
        self.assertRegex(seg, r"额度.*最稀缺|最稀缺的资源")

    def test_it_keeps_the_measured_numbers(self):
        # **锚 print 那一行。** 「要读 JD 才能评」这几个字在上面那段注释里
        # 也逐字出现（它就是在解释这句话），`index` 会落在注释里。
        i = SRC.index('f"剩 {todo} 个要读 JD')
        seg = SRC[max(0, i - 1600):i]
        self.assertRegex(seg, r"182 个里 126 个已有")
        self.assertRegex(seg, r"56 个")


class TheStoreSideIsTheOneSource(unittest.TestCase):
    def test_status_still_splits_the_two(self):
        """`status()` 是这两个数的唯一出处。它一旦不再分开算，
        上面那半句就跟着变成猜的。"""
        seg = code_of("tools/jd_store.py", "def status(")
        for k in ("new_total", "new_have"):
            with self.subTest(k=k):
                self.assertIn(k, seg)

    def test_having_a_body_is_what_counts(self):
        """有文件不等于有正文 —— 空壳 detail 不算「已有」。"""
        self.assertFalse(jd_store.has_body(None))
        self.assertFalse(jd_store.has_body({"url": "x"}))
        self.assertFalse(jd_store.has_body({"url": "x", "description": "  "}))
        self.assertTrue(jd_store.has_body(
            {"url": "x", "description": "职位描述" * 40}))


if __name__ == "__main__":
    unittest.main()
