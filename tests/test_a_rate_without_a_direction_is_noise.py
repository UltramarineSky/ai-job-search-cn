# -*- coding: utf-8 -*-
"""一个比例不说方向，读的人分不出「一直这样」和「已经好了」。

**而方向本身也可能是量出来的假象** —— 这份文件第一版就栽在这里。它当时记着：

    可以考虑缺「投前必问」   全量 46%  ·  最近 30 份 73%   ← 新出的更差
    深评缺小节               全量 35%  ·  最近 30 份 13%   ← 新出的已经好了

两个数都是按**文件 mtime** 排出来的。2026-08-23 改成按深评自己写的评估日期排，
第二行当场翻成「最近 30 份 90%」—— 同一份数据，方向反了。查下来两个都不是真的：
缺口按批次成团（08-10 / 08-13 / 08-17 整批全缺，08-11 / 08-12 整批全写），
30 份的窗口跨在批次边界上，落哪边报哪边。第一行更糟：「投前必问」是 08-22 才进
输出格式的，而最新一份深评写于 08-17 —— 那 73% 全部产于规则之前。

所以这份文件现在守的不是「要报方向」，是**报之前先问这个数是从什么材料上算的**：

- 规则生效前的产出算不出这条规则的执行率 → `_ASK_RULE_SINCE` 切分母；
- 成团的缺口算不出时间趋势 → 报批次，不报方向。

判据与行为断言在 `test_a_trend_needs_something_to_trend_over.py`，这里只留
那次改动**不该带掉**的几条：最小样本、全清就闭嘴、窗口常量只有一个、
两节同时缺是一种行为、硬门 FAIL 不进分母。

顺带那个结构事实仍然成立：86 份里 **84 份同时缺「真伪信号」和「建议」**
（输出格式的最后两节）—— 不是两个问题，是生成到一半停了。
"""
import sys
import tempfile
import unittest
import unittest.mock as mock
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tests"))
import audit_pipeline as A  # noqa: E402
from _srcscan import strip_comments  # noqa: E402

_FULL = ("# 职位评估\n\n## 结论：值得投\n\n## 评分明细\n\n## 优势\n\n"
         "## 缺口\n\n## 职位真伪信号\n\n无\n\n## 建议\n\n投。\n")
#: 缺最后两节 —— 实测里最常见的那种（生成到一半停了）。
_CUT = ("# 职位评估\n\n## 结论：值得投\n\n## 评分明细\n\n## 优势\n\n## 缺口\n")


def _run(check, files):
    """按给定顺序造文件；后写的 mtime 更大，于是「最近 N 份」就是列表尾部。"""
    import os
    import time
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        apps = root / "users" / "u" / "documents" / "applications"
        base = time.time() - 10000
        for i, text in enumerate(files):
            d = apps / f"示例科技{i:03d}_产品经理"
            d.mkdir(parents=True)
            f = d / "evaluation.md"
            f.write_text(text, encoding="utf-8")
            os.utime(f, (base + i, base + i))
        with mock.patch.object(A, "ROOT", root), \
             mock.patch.object(A._cli, "pick_user", lambda *a, **k: "u"):
            return check({}, {})


class ItDoesNotInventADirection(unittest.TestCase):
    """老的全缺、新的全齐 —— 这**看着**像「已经好多了」，而它其实是两个批次。
    检查现在报批次，不下方向断语。"""

    def test_a_clean_batch_and_a_broken_batch_are_named(self):
        out = _run(A.check_evaluation_sections, [_CUT] * 40 + [_FULL] * 30)
        self.assertEqual(len(out), 1)
        msg = out[0][2]
        self.assertNotIn("已经好多了", msg, f"又下方向断语了：{msg}")
        self.assertNotIn("新出的更差", msg, f"又下方向断语了：{msg}")

    def test_the_reverse_order_reads_the_same(self):
        """把两批调个个儿，结论不该变 —— 那正是「方向」是假象的证据。
        （这里两批同日，所以走的是「没有整批分界」那一支。）"""
        a = _run(A.check_evaluation_sections, [_CUT] * 40 + [_FULL] * 30)[0][2]
        b = _run(A.check_evaluation_sections, [_FULL] * 40 + [_CUT] * 30)[0][2]
        for msg in (a, b):
            self.assertNotIn("新出的更差", msg)
            self.assertNotIn("已经好多了", msg)

    def test_the_total_is_still_there(self):
        """报批次不等于不报规模。"""
        msg = _run(A.check_evaluation_sections, [_CUT] * 40 + [_FULL] * 30)[0][2]
        self.assertRegex(msg, r"该写全的 \d+ 份")

    def test_a_tiny_sample_says_nothing(self):
        """样本太小时一两份就能把比例带到 100% —— 那不是趋势，是噪音。"""
        out = _run(A.check_evaluation_sections, [_CUT] * 3)
        self.assertNotIn("整批", out[0][2])

    def test_all_clean_reports_nothing_at_all(self):
        self.assertEqual(_run(A.check_evaluation_sections, [_FULL] * 30), [])


class NeitherCheckAssertsADirectionAnyMore(unittest.TestCase):
    """**这两条原来是空转的。** 它们查的是「源码里有没有『新出的更差』」，
    而改完之后那句话仍留在**注释**里（讲的正是它为什么被删）—— 照样绿。
    现在剥掉注释再查，并且只查真会印出去的字符串。"""

    CHECKS = ("check_evaluation_sections", "check_maybe_tier_has_questions")

    def _code(self, name):
        src = strip_comments((ROOT / "tools" / "audit_pipeline.py")
                             .read_text(encoding="utf-8"))
        i = src.index(f"def {name}(")
        return src[i:src.index("\ndef ", i + 10)]

    def test_no_direction_verdict_is_hardcoded(self):
        for name in self.CHECKS:
            for phrase in ("新出的更差", "已经好多了"):
                with self.subTest(check=name, phrase=phrase):
                    self.assertNotIn(phrase, self._code(name),
                                     "又把一句方向断语写死进消息了")

    def test_the_window_is_shared(self):
        """`RECENT_EVALS` 只剩「投前必问」那条在用（样本不足时报个规模），
        但它仍然只许有一个定义 —— 两处各定各的就会各自漂。"""
        self.assertTrue(hasattr(A, "RECENT_EVALS"))
        src = (ROOT / "tools" / "audit_pipeline.py").read_text(encoding="utf-8")
        self.assertEqual(src.count("RECENT_EVALS = "), 1, "又多了一个窗口常量")


class TheCoOccurrenceIsWrittenDown(unittest.TestCase):
    def test_the_two_last_sections_go_missing_together(self):
        """86 份里 84 份同时缺 —— 那是一种行为，不是两个问题。
        不写下来，下一个人会分别去修「真伪信号」和「建议」。"""
        src = (ROOT / "tools" / "audit_pipeline.py").read_text(encoding="utf-8")
        i = src.index("def check_evaluation_sections(")
        seg = src[i:src.index("\ndef ", i + 10)]
        self.assertRegex(seg, r"84 份同时缺|不是两个问题")

    def test_the_gate_fail_exemption_survives(self):
        """硬门 FAIL 的文件本来就该短。这一条不许被这次改动带掉 ——
        少排它，这个数常年虚高，然后没人再当真。"""
        out = _run(A.check_evaluation_sections,
                   [_FULL] * 12 + ["# x\n\n## 结论：不满足硬性条件（学历）\n"] * 5)
        self.assertEqual(out, [], "硬门 FAIL 的短文件被算成缺小节了")


if __name__ == "__main__":
    unittest.main()
