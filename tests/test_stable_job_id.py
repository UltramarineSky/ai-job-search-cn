"""job id 必须稳定，否则浏览器里存的标记会张冠李戴。

## 为什么

原来 id 是枚举序号（`f"j{i}"`）—— `seen_jobs` 增删一条，后面所有 id 全部错位。
而页面把「不投」标记、「已发」勾选按 id 存在 localStorage 里：
**你排除了 A 岗，下次重新导出后被隐藏的是 B 岗。**

id 改为按 `url#职位名` 派生。带职位名是因为 51job 实测同一 URL 下挂着两个不同职位
（见 `workflows/reference/cdp-portals.md`），只用 URL 会让两个岗共用一个 id。
"""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import export_web_data as ex  # noqa: E402


class IdIsStable(unittest.TestCase):
    def test_same_input_same_id(self):
        a = ex.stable_id("https://x/1", "AI产品经理")
        b = ex.stable_id("https://x/1", "AI产品经理")
        self.assertEqual(a, b)

    def test_position_does_not_affect_it(self):
        """这是关键：原实现里 id 取决于枚举顺序，换个顺序就全变。"""
        ids_run1 = [ex.stable_id(u, t) for u, t in
                    [("https://x/1", "甲"), ("https://x/2", "乙"), ("https://x/3", "丙")]]
        # 中间插一条、顺序打乱，已有条目的 id 不该变
        ids_run2 = [ex.stable_id(u, t) for u, t in
                    [("https://x/9", "新"), ("https://x/3", "丙"),
                     ("https://x/1", "甲"), ("https://x/2", "乙")]]
        self.assertEqual(ids_run1[0], ids_run2[2])
        self.assertEqual(ids_run1[1], ids_run2[3])
        self.assertEqual(ids_run1[2], ids_run2[1])

    def test_same_url_different_titles_get_different_ids(self):
        """51job 实测同一 URL 挂两个职位——只用 URL 会让它们共用一个 id。"""
        a = ex.stable_id("https://jobs.51job.com/all/1.html", "AI产品经理")
        b = ex.stable_id("https://jobs.51job.com/all/1.html", "数据产品经理")
        self.assertNotEqual(a, b)

    def test_id_shape_is_usable_as_filename(self):
        """id 会被当成简历 PDF 的文件名，不能带路径字符。"""
        i = ex.stable_id("https://x/1?a=b&c=d#frag", "AI 产品/经理")
        self.assertRegex(i, r"^j[0-9a-f]{10}$")

    def test_real_export_ids_are_unique(self):
        import json
        f = ROOT / "web" / "public" / "data.json"
        if not f.is_file():
            self.skipTest("还没导出真实数据")
        ids = [j["id"] for j in json.loads(f.read_text(encoding="utf-8"))["jobs"]]
        self.assertEqual(len(ids), len(set(ids)), "导出的 id 有重复")
        self.assertTrue(all(i.startswith("j") and len(i) == 11 for i in ids),
                        "还有枚举序号形式的旧 id")


if __name__ == "__main__":
    unittest.main()


class SchemeMustBeNormalisedBeforeDedup(unittest.TestCase):
    """`http://` 与 `https://` 是同一个岗，查重前必须先剥掉协议。

    2026-08-19 抓智联实测：页面锚点给的是 `http://`，而库里 08-11 存的同一批岗是
    `https://`——20 个新岗里 4 个是重复的，其中两个早就判过硬门 FAIL，
    等于花了账号额度把已经出局的岗又抓评一遍。

    这是同一形状第三次咬人（前两次是「裸 URL vs url#职位名」和「同公司同职位名
    撞进一个材料目录」），所以规则要写死、并由测试盯着。
    """

    def test_the_rule_is_in_the_workflow(self):
        d = (ROOT / "workflows" / "job-scrape.md").read_text(encoding="utf-8")
        self.assertIn("归一化", d, "没写「比对前先归一化协议」")
        self.assertIn("https://", d)
        self.assertIn("archive.json", d, "没说存档也要一起查")

    def test_the_store_has_no_scheme_twins(self):
        """真实库里不许留下只差协议的孪生条目。"""
        import json
        import _cli
        ptr = ROOT / ".active_user"
        if not ptr.is_file():
            self.skipTest("没有活动用户")
        user = ptr.read_text(encoding="utf-8").strip()
        f = ROOT / "users" / user / "job_scraper" / "seen_jobs.json"
        if not f.is_file():
            self.skipTest("还没抓过")
        seen = _cli.seen_of(json.loads(f.read_text(encoding="utf-8")))
        by = {}
        for e in seen.values():
            u = _cli.norm_url(e.get("url"))    # 归一化正本在 _cli，别再手写 replace
            if not u:
                continue
            by.setdefault((u, e.get("title") or ""), set()).add(e.get("url"))
        twins = [k for k, v in by.items() if len(v) > 1]
        self.assertEqual(twins, [],
                         "同一个岗同时以 http 和 https 存了两份——"
                         f"查重漏了协议归一化：{twins[:3]}")
