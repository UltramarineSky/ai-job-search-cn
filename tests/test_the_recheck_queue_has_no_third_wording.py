# -*- coding: utf-8 -*-
"""复核队列说「靠不住有两种」—— 实测有五种，漏掉三种共 217 个岗。

`fetch_details.missing_urls` 的 docstring 写着：

> `recheck=True` 时把判过但正文靠不住的一并收进来 …… 「靠不住」有两种，
> 缺一种就漏一批

两个判据都**按措辞**判：`needs_recheck` 找「未抓 JD」，
`judged_without_stored_body` 找「读过 JD」。而 `来源` 是自由文本。

实测活动用户 2026-08-24，猎聘 · 已评 · 库里没有正文的那批，按措辞分：

    预筛（未抓 JD）                       238   认
    粗筛（读过 JD 正文）                    135   认
    深评（读过 JD 正文）                     48   认
    粗筛（未抓 JD）                        26   认
    粗筛（标题即判据）                      129   **不认**
    粗筛（历史条目，来源未记录）                 56   **不认**
    深评（writeback.py 从 evaluation.md 回写）  32   **不认**

**「标题即判据」那 129 个最刺眼**：`needs_recheck` 的 docstring 说的就是
「判据没经过 JD 正文复核」，而那句措辞是它最直白的自白。那段注释还记着
一次同样的教训（「粗筛（未抓 JD）」vs「预筛（未抓 JD）」，精确匹配漏 32 条），
结论是「按语义片段判，不能按整串」—— 学会了那一课，却仍然只盯同一个词根。

「深评回写」那 32 个落在两个判据**中间**：不说「未抓 JD」，也不说「读过 JD」。
而 `judged_without_stored_body` 问的是「证据还在不在」—— 按事实该收，按措辞才漏。

## 代价落在他真正投出去的那批上

`applied_jds` 的语料是「投过的岗」（信号最干净的一批）。85 个里 39 个没有正文，
其中 **21 个是猎聘的**。改之前 `--recheck` 只够得着 **6** 个；改之后 21 个全部
进队，全库同类从 217 降到 **0**。
"""
import json
import pathlib
import re
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import fetch_details as fd  # noqa: E402

FD = (ROOT / "tools" / "fetch_details.py").read_text(encoding="utf-8")
AJ = (ROOT / "tools" / "applied_jds.py").read_text(encoding="utf-8")


def flat(s: str) -> str:
    s = " ".join(re.sub(r"^\s*>\s?", "", s, flags=re.M).split())
    return re.sub(r"(?<=[一-鿿，。；：、（）「」])"
                  r" +(?=[一-鿿，。；：、（）「」])", "", s)


def _e(src: str, evidence: str = "") -> dict:
    return {"rank_breakdown": {"来源": src, "证据": evidence}}


class EveryWordingThatMeansUncheckedIsCaught(unittest.TestCase):
    """`needs_recheck` 问「判据够不够硬」—— 说法有好几种，全要认。"""

    CASES = ("预筛（未抓 JD）", "粗筛（未抓 JD）",
             "粗筛（标题即判据）", "粗筛（历史条目，来源未记录）")

    def test_each_one(self):
        for src in self.CASES:
            with self.subTest(src=src):
                self.assertTrue(fd.needs_recheck(_e(src)), f"漏了「{src}」")

    def test_the_evidence_field_still_counts(self):
        """另一条老路：`证据` 里写「未经…」。别被这次改动带掉。"""
        self.assertTrue(fd.needs_recheck(_e("粗筛（读过 JD 正文）", "未经复核")))

    def test_a_verdict_that_really_read_the_body_is_not_flagged_here(self):
        """读过正文的归另一个判据管，这里不该认 —— 两个问题不许互相吞。"""
        self.assertFalse(fd.needs_recheck(_e("粗筛（读过 JD 正文）")))
        self.assertFalse(fd.needs_recheck(_e("深评（读过 JD 正文）")))

    def test_the_title_only_case_is_recorded(self):
        i = FD.index("def needs_recheck(")
        seg = flat(FD[i:FD.index("def judged_without_stored_body(", i)]
                   .replace("#", " "))
        self.assertRegex(seg, r"粗筛（标题即判据）\s*129 个")
        self.assertRegex(seg, r"它明说了只看标题")

    def test_the_unknown_source_case_says_why_it_counts(self):
        i = FD.index("def needs_recheck(")
        seg = flat(FD[i:FD.index("def judged_without_stored_body(", i)]
                   .replace("#", " "))
        self.assertRegex(seg, r"\*\*不知道硬不硬，就当不够硬\*\*")


class TheEvidenceQuestionIsAskedByFact(unittest.TestCase):
    """`judged_without_stored_body` 问「证据还在不在」—— 深评回写那类也算。"""

    def _judged(self, src: str, body: bool) -> bool:
        real = fd.st.has_body
        fd.st.has_body = lambda d: body
        try:
            return fd.judged_without_stored_body("谁", _e(src) | {"url": "u"})
        finally:
            fd.st.has_body = real

    def test_the_writeback_wording_counts(self):
        self.assertTrue(
            self._judged("深评（writeback.py 从 evaluation.md 回写）", False))

    def test_the_classic_wording_still_counts(self):
        self.assertTrue(self._judged("粗筛（读过 JD 正文）", False))

    def test_a_stored_body_is_not_flagged(self):
        """正文在库里就没问题 —— 这个函数问的是证据在不在，不是措辞。"""
        self.assertFalse(self._judged("深评（writeback.py 回写）", True))
        self.assertFalse(self._judged("粗筛（读过 JD 正文）", True))

    def test_a_title_only_verdict_is_not_this_functions_business(self):
        self.assertFalse(self._judged("粗筛（标题即判据）", False))

    def test_the_between_the_two_reason_is_recorded(self):
        i = FD.index("def judged_without_stored_body(")
        seg = flat(FD[i:FD.index("    src = str(", i)].replace("#", " "))
        self.assertRegex(seg, r"\*\*正好落在两个判据之间\*\*")
        self.assertRegex(seg, r"按事实该收，按措辞才漏")

    def test_it_records_that_two_was_a_snapshot(self):
        """「有两种」写死在 docstring 里 —— 那句话本身就是这次漏掉的原因。"""
        i = FD.index("def judged_without_stored_body(")
        seg = flat(FD[i:FD.index("    src = str(", i)].replace("#", " "))
        self.assertRegex(seg, r"写死「两种」正是这类枚举最容易过期的地方")


class TheCountsAreRecorded(unittest.TestCase):
    def test_the_measurement_is_at_both_predicates(self):
        for anchor, need in (
                ("def needs_recheck(", "2026-08-24"),
                ("def judged_without_stored_body(", "2026-08-24")):
            with self.subTest(anchor=anchor):
                i = FD.index(anchor)
                self.assertIn(need, FD[i:i + 1800])

    def test_the_writeback_count_is_there(self):
        i = FD.index("def judged_without_stored_body(")
        self.assertRegex(flat(FD[i:i + 1200]), r"32 个条目的来源写的是")


class AppliedJdsPointsAtTheFix(unittest.TestCase):
    """报一个「46/85」然后停住，读的人不知道那 39 个补不补得回来。"""

    def test_it_names_the_command(self):
        self.assertIn("python tools/fetch_details.py --recheck --apply", AJ)

    def test_it_splits_recoverable_from_not(self):
        seg = flat(AJ[AJ.index("gap = cov.get("):][:1200])
        self.assertRegex(seg, r"个是猎聘的，补得回来")
        self.assertRegex(seg, r"只能在下次抓取当次顺手存，回头补不了")

    def test_it_says_what_the_gap_costs(self):
        seg = flat(AJ[AJ.index("gap = cov.get("):][:1200])
        # 这句在源码里被拆成两个拼接的 f-string，中间夹着 `" f"` ——
        # 整句断言必然落空。分两半钉，别为此去放宽 `flat`。
        self.assertRegex(seg, r"在清单里只有一行标题")
        self.assertRegex(seg, r"算能力差距时等于不存在")

    def test_it_stays_quiet_when_nothing_is_missing(self):
        self.assertIn("if gap:", AJ)

    def test_the_row_carries_the_portal(self):
        """不带这个字段，那句提示只能笼统说「都补不了」—— 而那是错的
        （实测第一版就这么印了：39 个全算成补不了，实际 21 个补得回来）。"""
        self.assertIn('"portal": e.get("portal") or "",', AJ)


class TheSignalItLeansOnIsReal(unittest.TestCase):
    """有语料时验一次：这三类措辞真的在库里，而且现在全被收进队列。"""

    def _seen(self):
        p = ROOT / ".active_user"
        if not p.is_file():
            self.skipTest("没有活动用户")
        u = p.read_text(encoding="utf-8").strip()
        f = ROOT / "users" / u / "job_scraper" / "seen_jobs.json"
        if not f.is_file():
            self.skipTest("没有职位库")
        import _cli
        return u, _cli.seen_of(json.loads(f.read_text(encoding="utf-8")))

    def test_the_three_wordings_really_occur(self):
        """**热库和存档一起扫。**

        `archive.py` 只是把岗搬进 `archive.json`，不是删除（`--revive` 能搬回来），
        所以 `needs_recheck` 那几条措辞照样要认得它们。
        实测 2026-08-28：一次归档把 `标题即判据` 那 199 条整批搬走，热库里一条
        不剩，这条守卫当场报「库里已经没有这种措辞」—— 而判据一个字没变，
        搬走的行回来还是那个写法。只扫热库，等于把归档误读成语义变更。
        （`needs_recheck` 认的是 `未抓 JD` 子串，热库新写法
        「粗筛（未抓 JD，只用标题与卡片字段）」包含它，没有漏判。）
        """
        u, seen = self._seen()
        rows = list(seen.values())
        arch = ROOT / "users" / u / "job_scraper" / "archive.json"
        if arch.is_file():
            import _cli
            rows += list(_cli.seen_of(
                json.loads(arch.read_text(encoding="utf-8"))).values())
        srcs = {str((e.get("rank_breakdown") or {}).get("来源") or "")
                for e in rows if isinstance(e, dict)}
        blob = " ".join(srcs)
        for w in ("标题即判据", "来源未记录", "writeback.py"):
            with self.subTest(w=w):
                self.assertIn(w, blob,
                              f"库里已经没有「{w}」这种措辞 —— 那一条判据的依据变了")

    def test_nothing_judged_without_a_body_is_left_out(self):
        u, seen = self._seen()
        import jd_store as st
        left = [e for e in seen.values()
                if isinstance(e, dict)
                and e.get("portal") == "liepin-search"
                and e.get("status") == "ranked"
                and not st.has_body(st.load(u, e.get("url") or "",
                                            e.get("title") or ""))
                and not (fd.needs_recheck(e)
                         or fd.judged_without_stored_body(u, e))]
        self.assertEqual(len(left), 0,
                         f"还有 {len(left)} 个猎聘岗判过、没正文、却进不了复核队列 "
                         f"—— 又冒出一种新措辞，去枚举一遍 `来源`")


if __name__ == "__main__":
    unittest.main()
