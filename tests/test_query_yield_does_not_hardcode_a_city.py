# -*- coding: utf-8 -*-
"""写回 `search-queries.md` 的那段可跑命令，城市要取自用户自己的资料。

`build_block` 里原来是 `-q "{q}" -l "上海"` ——写死的。它每次 `--apply` 都会重写
**每个用户**的自动维护块，于是北京的人跑一次，块里那几条命令全变成搜上海；
他照着敲，抓回来的岗一个都不对口，而下一次重跑又写回上海。

这跟本仓库其它阈值一个道理：**取值域的东西从用户资料里取，不在工具里定**
（`test_industry_agnostic` / `test_no_industry_presets` 守的是同一条）。

城市的来源是这份文件**自动维护块之外**的那些 `-l "…"` 行——那块归用户，
`/job-setup` 按他的目标城市生成。不能从块内取：块内的城市正是本工具上次写的，
拿它当来源就是自我循环，错一次就永远错下去。
"""
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import query_yield as qy  # noqa: E402

USER_BLOCK = """# 职位搜索查询策略

## 目标城市

- 北京

## 查询分类

### 优先级 A
```
-q "数据分析" -l "北京"
-q "数据科学" -l "北京"
```
"""


def _write(tmp: Path, text: str) -> Path:
    p = tmp / "search-queries.md"
    p.write_text(text, encoding="utf-8")
    return p


class TheCityComesFromTheProfile(unittest.TestCase):

    def test_no_city_is_hardcoded_in_the_source(self):
        """直接扫源码：写死一个中国城市名就红。"""
        src = (ROOT / "tools" / "query_yield.py").read_text(encoding="utf-8")
        block = src[src.index("def build_block"):]
        for city in ("上海", "北京", "深圳", "广州", "杭州", "成都"):
            with self.subTest(city=city):
                self.assertNotIn(f'-l "{city}"', block,
                                 f"build_block 里写死了 {city}")

    def test_it_reads_the_users_own_city(self):
        with TemporaryDirectory() as d:
            p = _write(Path(d), USER_BLOCK)
            self.assertEqual(qy.primary_city(p), "北京")

    def test_the_runnable_lines_use_that_city(self):
        with TemporaryDirectory() as d:
            p = _write(Path(d), USER_BLOCK)
            by = {"数据分析": {"猎聘": [{"fit": "high"}] * 20}}
            block = qy.build_block(by, "2026-08-18", 0,
                                   {("数据分析", "猎聘")}, qy.primary_city(p))
            self.assertIn('-l "北京"', block)
            self.assertNotIn("上海", block)

    def test_the_auto_block_is_not_its_own_source(self):
        """块内的城市是上次自己写的，不能拿它当来源——否则错一次就永远错。"""
        polluted = USER_BLOCK.replace('-q "数据科学" -l "北京"', "") + (
            f'\n{qy.BEGIN} -->\n```\n-q "x" -l "上海"\n```\n{qy.END}\n')
        with TemporaryDirectory() as d:
            p = _write(Path(d), polluted)
            self.assertEqual(qy.primary_city(p), "北京",
                             "从自动维护块里取了城市——自我循环")

    def test_no_city_means_no_fabricated_one(self):
        """资料里找不到城市时不许编一个：宁可不给可跑命令，也不给一条错的。"""
        with TemporaryDirectory() as d:
            p = _write(Path(d), "# 职位搜索查询策略\n\n## 查询分类\n")
            self.assertEqual(qy.primary_city(p), "")
            by = {"数据分析": {"猎聘": [{"fit": "high"}] * 20}}
            block = qy.build_block(by, "2026-08-18", 0,
                                   {("数据分析", "猎聘")}, "")
            self.assertNotIn('-l "', block, "没有城市却还是端出了 -l 参数")


if __name__ == "__main__":
    unittest.main()


class HighMatchFollowsTheVerdict(unittest.TestCase):
    """「其中高匹配」判过的以判词为准，没判过的才退回抓取时的 fit 标记。

    2026-08-20 全库对账：只看 `fit=="high"` 时报 202 个高匹配，按判词只有 128 个
    可投，单岗错位 204 个；「研发效能」fit 报 27、判词只有 4。词表的「最值钱的
    格子」就靠这列推荐——旧口径推的是 fit 虚高的词，新口径下推荐名单整个换了脸
    （换成了真出过可投岗的 AI原生 / AI应用产品经理）。

    判词是评过 JD 的结论，fit 是评之前的猜测——有前者时用后者没有道理。
    """

    def test_verdict_wins_over_fit(self):
        import query_yield as qy
        # 判过且可投：fit 是什么都算高
        self.assertTrue(qy.is_high({"rank_verdict": "值得投", "fit": "pending"}))
        self.assertTrue(qy.is_high({"rank_verdict": "粗筛：强匹配", "fit": "low"}))
        # 判过且不可投：fit=high 也不算——这正是虚高 3-8 倍的来源
        self.assertFalse(qy.is_high({"rank_verdict": "跳过", "fit": "high"}))
        self.assertFalse(qy.is_high({"rank_verdict": "可以考虑", "fit": "high"}))
        # 硬门 FAIL 这类不在五档里的结论：明确不是高匹配
        self.assertFalse(qy.is_high({"rank_verdict": "硬门 FAIL (工作年限)", "fit": "high"}))
        # 真没判过：退回抓取时的标记
        self.assertTrue(qy.is_high({"rank_verdict": "", "fit": "high"}))
        self.assertFalse(qy.is_high({"fit": "medium"}))

    def test_stats_uses_it(self):
        import query_yield as qy
        n, high = qy.stats([
            {"rank_verdict": "值得投", "fit": "pending"},
            {"rank_verdict": "跳过", "fit": "high"},
            {"fit": "high"},
        ])
        self.assertEqual((n, high), (3, 2))
