# -*- coding: utf-8 -*-
"""「p5-p7 命中率 0-2%」—— 哪个命中率？两种读法差 5-10 倍。

`query_yield.is_high` 的注释拿这个数当「深页是噪音层」的论据。它是对的，
但它没说是**哪个率**。2026-08-23 复核时按「可投三档」（强匹配 / 值得投 /
可以考虑）重算，得到 p5 6% · p6 13% · p7 11%，与 0-2% 差 5-10 倍 ——
**差一点把一个正确的数字当成过期数据改掉。**

真正的口径是**顶两档**（强匹配 / 值得投）。同一份语料，已评过的岗为分母：

    页码      已评    可投三档    顶两档
    p1-p4    1442      18%       5.3%
    p5-p10    333      11%       1.5%    ← 顶两档 3/198，就是那句 0-2%

## 为什么两个都要留

它们各答一个问题：

- **顶两档**答「深页还出不出直接能发的岗」—— 基本不出。
- **可投三档**答「深页还值不值得抓」—— 11% 对 18%，是浅页的六成，**不是零**。

只留前者会得出「永远别翻页」这个过头的结论。额度紧张时该做的是
「先把每个词的第 1 页跑遍，再回头翻深页」，不是把深页整个划掉 ——
而抓取额度是这套系统里最稀缺的（每次请求之间要隔 8/4/3 秒、撞了风控整站冷却 24 小时）。

## 这条不钉具体数字

语料每天在长，钉死 18%/11% 只会让测试变成维护负担。钉的是**两件事**：
注释里写清了是哪个口径、以及**两个口径在真实语料上确实不是一回事**
（后者现算，语料变了它跟着变）。
"""
import json
import pathlib
import re
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import _cli  # noqa: E402

QY = (ROOT / "tools" / "query_yield.py").read_text(encoding="utf-8")


def flat(s: str) -> str:
    s = " ".join(re.sub(r"^\s*>\s?", "", s, flags=re.M).split())
    return re.sub(r"(?<=[一-鿿，。；：、（）「」])"
                  r" +(?=[一-鿿，。；：、（）「」])", "", s)


def seg() -> str:
    """`is_high` 的文档区间。

    ⚠️ **收尾锚点原来用的是「函数体第一行代码」，那是会变的东西。**
    它钉的是 `v = str(r.get("rank_verdict")` —— 2026-08-30 把散在 18 处的
    「削掉粗筛前缀」收拢到 `_cli.strip_triage` 时，这一行跟着改了，
    八条断言一起 `ValueError: substring not found`。
    改成钉**下一个 `def`**：文档区间到下一个函数为止，而函数边界比
    「某一行长什么样」稳得多。
    """
    i = QY.index("def is_high(")
    j = QY.index("\ndef ", i + 1)
    return flat(QY[i:j])


class TheClaimSaysWhichRate(unittest.TestCase):
    def test_the_original_number_survives(self):
        """它是对的 —— 这次不是改它，是说清它。"""
        self.assertRegex(seg(), r"p5-p7 命中率 0-2%")

    def test_it_now_names_the_band(self):
        self.assertRegex(seg(), r"「命中率」说的是\*\*顶两档\*\*，不是「可投」")

    def test_it_records_the_near_miss(self):
        """误读是真发生过的 —— 不写下来，下一个人照样会「修」它。"""
        s = seg()
        self.assertRegex(s, r"差一点把一个 \*\*正确的数字\*\* 改掉"
                            r"|\*\*差一点把一个正确的数字改掉\*\*")
        self.assertIn("2026-08-23", s)

    def test_it_carries_both_columns(self):
        s = seg()
        self.assertRegex(s, r"p1-p4 1442 18% 5\.3%")
        self.assertRegex(s, r"p5-p10 333 11% 1\.5%")

    def test_it_says_what_each_column_answers(self):
        s = seg()
        self.assertRegex(s, r"顶两档答「深页还出不出直接能发的岗」")
        self.assertRegex(s, r"可投三档答「深页还值不值得抓」")

    def test_it_states_the_load_bearing_conclusion(self):
        """整段改动承重的就是这半句：深页更差，但**不是零**。

        变异实测：把「不是零」改成「基本是零」，其余断言全绿 ——
        因为它们钉的是现算的数据，没有一条钉这个结论本身。
        """
        s = seg()
        self.assertRegex(s, r"是浅页的六成，\*\*不是零\*\*")

    def test_it_warns_against_the_overshoot(self):
        """把 11% 读成 0 会得出「永远别翻页」—— 那才是这条注释的实际风险。"""
        s = seg()
        self.assertRegex(s, r"「永远别翻页」这个 过头的结论"
                            r"|「永远别翻页」这个过头的结论")
        self.assertRegex(s, r"先把每个词的第 1 页跑遍，再回头翻深页")

    def test_the_original_argument_is_intact(self):
        """这段注释本来是在讲 `fit` 比判词乐观 —— 那个论证不能被冲淡。"""
        s = seg()
        self.assertRegex(s, r"fit 说 202 个高匹配、判词说 128 个可投")
        self.assertRegex(s, r"\*\*单岗错位 204 个\*\*")

    def test_the_function_still_prefers_the_verdict(self):
        import query_yield as qy
        self.assertTrue(qy.is_high({"rank_verdict": "值得投", "fit": "low"}))
        self.assertFalse(qy.is_high({"rank_verdict": "可以考虑", "fit": "high"}))
        self.assertTrue(qy.is_high({"fit": "high"}))
        self.assertFalse(qy.is_high({"rank_verdict": "硬门 FAIL (学历)",
                                     "fit": "high"}))

    def test_the_top_two_are_the_first_two_bands(self):
        """「顶两档」不是这里另立的说法 —— 它就是判词表的前两个。"""
        self.assertEqual(_cli.VERDICTS[:2], ("强匹配", "值得投"))


class TheTwoRatesReallyDiffer(unittest.TestCase):
    """现算：两个口径在真实语料上确实不是一回事，深页确实更差但不是零。"""

    def _by_depth(self):
        p = ROOT / ".active_user"
        if not p.is_file():
            self.skipTest("没有活动用户")
        u = p.read_text(encoding="utf-8").strip()
        f = ROOT / "users" / u / "job_scraper" / "seen_jobs.json"
        d = ROOT / "web" / "public" / "data.json"
        if not (f.is_file() and d.is_file()):
            self.skipTest("没有语料或没导出过")
        seen = json.loads(f.read_text(encoding="utf-8"))["seen"]
        by = {j.get("url"): j for j in
              json.loads(d.read_text(encoding="utf-8"))["jobs"] if j.get("url")}
        good = set(_cli.VERDICTS[:3]) | {f"粗筛：{v}" for v in _cli.VERDICTS[:3]}
        top = set(_cli.VERDICTS[:2]) | {f"粗筛：{v}" for v in _cli.VERDICTS[:2]}
        out = {"shallow": [0, 0, 0], "deep": [0, 0, 0]}   # [顶两档, 可投, 已评]
        for e in seen.values():
            if not isinstance(e, dict):
                continue
            fb = e.get("found_by") or ""
            if not fb:
                continue
            m = re.search(r"\bp(\d+)\s*$", fb)
            box = out["deep"] if (m and int(m.group(1)) >= 5) else out["shallow"]
            v = (by.get(e.get("url")) or {}).get("verdict") or ""
            if not v:
                continue
            box[2] += 1
            if v in good:
                box[1] += 1
            if v in top:
                box[0] += 1
        if out["shallow"][2] < 200 or out["deep"][2] < 100:
            self.skipTest("某一档样本太少，说明不了")
        return out

    def test_the_top_two_rate_is_much_lower_than_the_sellable_rate(self):
        """两个口径要是差不多，那句「说清是哪一个」就没有意义了。"""
        d = self._by_depth()["deep"]
        self.assertLess(d[0] / d[2], d[1] / d[2] / 2,
                        f"深页顶两档 {d[0]}/{d[2]}、可投 {d[1]}/{d[2]} —— "
                        f"两个口径已经差不多了，重新量一次")

    def test_deep_pages_are_worse_on_the_top_two(self):
        o = self._by_depth()
        self.assertLess(o["deep"][0] / o["deep"][2],
                        o["shallow"][0] / o["shallow"][2],
                        "深页顶两档不比浅页差了 —— 「噪音层」这个说法要重估")

    def test_deep_pages_are_not_zero_on_sellable(self):
        """这半条才是这次要防的：把 11% 读成 0，就会把深页整个划掉。"""
        d = self._by_depth()["deep"]
        self.assertGreater(d[1] / d[2], 0.03,
                           f"深页可投 {d[1]}/{d[2]} —— 真的接近零了，"
                           f"那注释里那句「不是零」要改")

    def test_shallow_still_beats_deep_overall(self):
        o = self._by_depth()
        self.assertGreater(o["shallow"][1] / o["shallow"][2],
                           o["deep"][1] / o["deep"][2],
                           "深页可投率反超浅页 —— 「先跑第 1 页」那条建议要重估")


if __name__ == "__main__":
    unittest.main()
