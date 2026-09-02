# -*- coding: utf-8 -*-
"""抓回来的 JD 要按**读取方用的那个键**存，否则每一轮都会重抓同一个岗。

详情库的键是 `stable_id(url, title)`，而读取方一侧只有职位库的标题
（`jd_store.load(user, entry["url"], entry["title"])` —— `prescreen`、`/job-rank`、
`/job-apply`、`export_web_data` 全走它）。`fetch_details` 原来拿**详情接口返回的
标题**去算键，两个标题不一样时：文件写下了、请求花掉了、而谁都读不回来。

实测 2026-08-27（跑 `/job-auto` 时撞出来的，不是扫出来的）：盘上 6 份详情这么废掉，例

    职位库「AI研发效能岗」            ← 详情页「证券公司AI治理岗」
    职位库「AI产品经理--上海/广州/北京」  ← 详情页「…/广州/北京/成都」

当轮 CLI 打印「抓到 2 份」，而 `jd_store.status` 的 `new_have` 纹丝不动 ——
**失败是静默的**，正是 `save_from_text` 的 docstring 早就写过的那句：
「存进去的这份就再也读不回来 —— 而它**看起来是成功的**（写盘了、有文件、没报错）」。

`--save` 那条路当时已经做对了（只收链接，标题从职位库取）。这条路绕开了那道保护。
"""
import ast
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tests"))
import export_web_data as ex  # noqa: E402
import jd_store  # noqa: E402
from _srcscan import code_of  # noqa: E402


class TheKeyMatchesWhatReadersLookUp(unittest.TestCase):
    def test_a_renamed_detail_still_lands_under_the_library_title(self):
        """详情页改了名，存下来的那份仍要能按职位库的标题读回来。"""
        url = "https://example.invalid/job/1"
        lib, detail = "AI研发效能岗", "证券公司AI治理岗"
        # 修好之后的行为：键按 lib 算
        self.assertEqual(jd_store.key_for(url, lib),
                         ex.stable_id(url, lib))
        # 而按详情页标题算出来的是另一个键 —— 这就是当初废掉那 6 份的原因
        self.assertNotEqual(jd_store.key_for(url, lib),
                            jd_store.key_for(url, detail),
                            "两个标题算出同一个键？那这条测试就失去意义了")

    def test_fetch_details_overwrites_the_title_before_saving(self):
        seg = code_of("tools/fetch_details.py", "def run(")
        self.assertIn('d["title"] = e.get("title")', seg,
                      "存盘前没把标题换成职位库那条的 —— 存进去会读不回来")
        i = seg.index('d["title"] = e.get("title")')
        j = seg.index("st.save(user, d)")
        self.assertLess(i, j, "换标题写在了 save 之后，等于没换")

    def test_the_detail_title_is_kept_not_dropped(self):
        """详情页那个标题更全（带地点、带真实岗位名），别丢，留着好对账。"""
        seg = code_of("tools/fetch_details.py", "def run(")
        self.assertIn('d["detail_title"]', seg,
                      "详情页标题被直接丢掉了 —— 两边不一致时就看不出来了")

    def test_the_reason_is_written_down_next_to_it(self):
        """静默失败的坑要把代价写在原地，否则下一个人会觉得这两行多余。"""
        src = (ROOT / "tools" / "fetch_details.py").read_text(encoding="utf-8")
        i = src.index('d["title"] = e.get("title")')
        seg = src[max(0, i - 2000):i]
        self.assertIn("读不回来", seg)
        self.assertIn("2026-08-27", seg, "实测数没带日期")


class TheOtherPathAlreadyDidThis(unittest.TestCase):
    """`--save` 那条路早就只收链接、标题从职位库取。两条路要一致。"""

    def test_save_from_text_takes_the_title_from_the_library(self):
        seg = code_of("tools/jd_store.py", "def save_from_text(")
        self.assertIn('hit[f] for f in ("title", "company")', seg,
                      "--save 那条路也开始信调用方给的标题了？")

    def test_its_docstring_still_carries_the_warning(self):
        doc = jd_store.save_from_text.__doc__ or ""
        self.assertIn("读不回来", doc,
                      "那段警告没了 —— 它是这两条路都要遵守的理由")


if __name__ == "__main__":
    unittest.main()
