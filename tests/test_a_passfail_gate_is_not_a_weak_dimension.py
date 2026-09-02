# -*- coding: utf-8 -*-
"""面板把 96 个「地点：上海」摆进了「要掂量的地方」—— 而他就在上海。

`04-job-evaluation.md` 说得很死：

> 计权的是**四**维（技能与经验、薪资与职级、强度与公司性质、发展与风险）。
> 地点是 Pass/Fail 的门（跨城搬迁），不计权重——**所以别再叫「五维」**。

而实测活动用户 2026-08-23：238 份评分明细里 **106 份**多一行
「地点（跨城搬迁）」。写手其实很小心 —— `score` 给 None、`weight` 给 0，
那是「不计权重」的一种合理读法。

**出事的是显示层。** `splitReasons` 的第二行是
`d.score === null || d.score < 70` → 归入 `minus`，于是：

- 96 条写着「上海」的行被摆进**「要掂量的地方」**（他人在上海，那是**通过**）；
- 措辞还是「这项没打分」—— 对一道 Pass/Fail 的门来说，不打分是**设计如此**，
  不是评估有缺。

## 判据只能按名字

**不能用「没有分数」**：真维度里也有 5 条没打分，那 5 条的「这项没打分」是对的。
**更不能用「权重为 0」**：实测 826 条 weight 为 0 的行里 **716 条是真维度**
（那一列常常没解析出来）。

所以加了一份四维正本 `_cli.WEIGHTED_DIMS`，服务端按名字给每行打 `weighted`，
面板只读这个标记。

## 不丢内容

那 106 条里有 **3 条是真信号**（「杭州（跨城，需自行拍板）」「深圳」
「上海/北京待确认」）。所以不是删掉，是**挪到单独一行、不判好坏**：
原样把写手那句话摆出来，他自己看得懂。
"""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import _cli  # noqa: E402
import export_web_data as ex  # noqa: E402

EX = (ROOT / "tools" / "export_web_data.py").read_text(encoding="utf-8")
CLI = (ROOT / "tools" / "_cli.py").read_text(encoding="utf-8")
JR = (ROOT / "web" / "src" / "components"
      / "JobReadout.tsx").read_text(encoding="utf-8")
TYPES = (ROOT / "web" / "src" / "types.ts").read_text(encoding="utf-8")
EVAL = (ROOT / "workflows" / "reference"
        / "04-job-evaluation.md").read_text(encoding="utf-8")


class TheFourAreNamedOnce(unittest.TestCase):
    def test_the_constant_exists(self):
        self.assertEqual(_cli.WEIGHTED_DIMS,
                         ("技能与经验", "薪资与职级", "强度与公司性质", "发展与风险"))

    def test_each_of_the_four_passes(self):
        for n in _cli.WEIGHTED_DIMS:
            with self.subTest(n=n):
                self.assertTrue(_cli.is_weighted_dim(n))

    def test_the_gate_row_does_not(self):
        for n in ("地点（跨城搬迁）", "地点", "通勤时长", "地点（当前/搬迁）"):
            with self.subTest(n=n):
                self.assertFalse(_cli.is_weighted_dim(n))

    def test_it_is_lenient_about_suffixes(self):
        """写「技能与经验匹配」也算 —— 表头措辞从来不统一。"""
        self.assertTrue(_cli.is_weighted_dim("技能与经验匹配（0-100）"))

    def test_empty_is_not_a_dimension(self):
        for n in ("", "   ", None):
            with self.subTest(n=n):
                self.assertFalse(_cli.is_weighted_dim(n))

    def test_the_framework_still_says_four(self):
        flat = "".join(EVAL.split()).replace("*", "").replace(">", "")
        self.assertIn("计权的是四维", flat)
        self.assertIn("所以别再叫「五维」", flat)

    def test_the_reason_is_recorded(self):
        i = CLI.index("WEIGHTED_DIMS = (")
        seg = " ".join(CLI[max(0, i - 1400):i].replace("#:", " ").split())
        self.assertRegex(seg, r"238 份评分明细里 \*\*106 份\*\*多一行")
        self.assertRegex(seg, r"那是通过")
        self.assertIn("2026-08-23", seg)

    def test_it_says_why_not_weight_zero(self):
        """这是选判据时最容易走错的一步 —— 理由必须留下。"""
        i = CLI.index("WEIGHTED_DIMS = (")
        seg = " ".join(CLI[max(0, i - 1400):i].replace("#:", " ").split())
        self.assertRegex(seg, r"不能按 `weight == 0`")
        self.assertRegex(seg, r"826 条 weight 为 0 的行里 有 716 条是真维度"
                              r"|826 条 weight 为 0 的行里有 716 条是真维度")


class TheExportMarksEachRow(unittest.TestCase):
    def test_the_field_is_emitted(self):
        got = ex.parse_dimensions(
            "## 评分明细\n| 维度 | 分数 | 权重 | 依据 |\n|---|---|---|---|\n"
            "| 技能与经验 | 72 | 30 | 对口 |\n"
            "| 地点（跨城搬迁） | — | — | 上海 |\n")
        self.assertEqual([d["weighted"] for d in got], [True, False])

    def test_it_uses_the_shared_judge(self):
        i = EX.index('"weighted": _cli.is_weighted_dim(name)')
        self.assertGreater(i, EX.index("def parse_dimensions("))

    def test_it_does_not_hand_roll_the_list(self):
        i = EX.index("def parse_dimensions(")
        body = EX[i:EX.index("\ndef ", i + 10)]
        self.assertNotIn("薪资与职级", body, "又在这里抄了一份四维")

    def test_the_other_fields_survive(self):
        got = ex.parse_dimensions(
            "## 评分明细\n| 维度 | 分数 | 权重 | 依据 |\n|---|---|---|---|\n"
            "| 技能与经验 | 72 | 30 | 对口 |\n")
        self.assertEqual(got[0]["score"], 72)
        self.assertEqual(got[0]["weight"], 30)
        self.assertEqual(got[0]["note"], "对口")


class ThePanelKeepsItOutOfBothColumns(unittest.TestCase):
    def _split(self) -> str:
        """**从上面那段 JSDoc 起切，不是从 `function` 起。**

        改动的理由写在 JSDoc 里，而它在函数签名之前 —— 从签名切读不到
        （两条实测断言第一版都栽在这儿）。"""
        j = JR.index("function splitReasons(")
        i = JR.rindex("/**", 0, j)
        return JR[i:JR.index("\n}", j)]

    def test_the_filter_is_there(self):
        self.assertIn("d.weighted !== false", self._split(),
                      "两栏仍然按「有没有分数」分，门会被摆成负面")

    def test_both_columns_use_the_filtered_set(self):
        seg = self._split()
        self.assertIn("const plus = scored.filter", seg)
        self.assertIn("const minus = scored.filter", seg)

    def test_the_gate_rows_are_kept_not_dropped(self):
        """106 条里有 3 条是真信号 —— 删掉不行。"""
        seg = self._split()
        self.assertIn("const gateLike = dims.filter((d) => d.weighted === false)",
                      seg)
        # 解构那一行里 `gateLike` 在 `splitReasons(...)` **左边** ——
        # 往右切读不到（第一版实测）。
        k = JR.index("= splitReasons(job.dimensions)")
        self.assertIn("gateLike", JR[max(0, k - 60):k])

    def test_it_says_why_not_the_score(self):
        seg = " ".join(self._split().split())
        self.assertRegex(seg, r"不能用「没有分数」或「权重为 0」")
        self.assertRegex(seg, r"真维度里也有 5 条没打分、716 条权重为 0")

    def test_it_carries_the_measurement(self):
        seg = " ".join(self._split().split())
        self.assertRegex(seg, r"106 份有这一行")
        self.assertRegex(seg, r"96 条写着「上海」")
        self.assertIn("2026-08-23", seg)

    def test_the_gate_line_is_neutral(self):
        i = JR.index("{gateLike.length > 0 && (")
        seg = " ".join(JR[max(0, i - 400):i + 300].split())
        self.assertRegex(seg, r"不判好坏、不说「没打分」")
        self.assertRegex(seg, r"对一道门来说不打分是设计如此")

    def test_the_gate_line_shows_the_writers_own_words(self):
        i = JR.index("{gateLike.length > 0 && (")
        self.assertIn("`${d.name}：${d.note}`", JR[i:i + 400])

    def test_the_empty_count_no_longer_counts_the_gate_row(self):
        """「这 N 项都不拖后腿」里的 N 不能再把门算进去。"""
        self.assertIn("这 {plus.length + minus.length} 项都不拖后腿", JR)
        self.assertNotIn("这 {job.dimensions.length} 项都不拖后腿", JR)

    def test_the_type_declares_it(self):
        i = TYPES.index("export interface Dimension {")
        self.assertIn("weighted?: boolean;", TYPES[i:i + 500])

    def test_the_all_unscored_branch_is_reachable_now(self):
        """**那个条件原来恒为真。**

        它写在 `plus.length === 0` 的分支里，而 `plus + minus` 就是全部计权维度
        —— `minus.length === job.dimensions.length` 在那儿永远成立，
        于是「没有明显加分项——分数主要靠没踩雷撑着」**一次都没出现过**。

        实测 2026-08-23：62 个没有加分项的岗里 **61 个是打过分、只是都低于 70**，
        它们看到的却是「这几项都还没打分」—— 一句事实上错误的话。
        """
        self.assertIn("minus.every((d) => d.score === null)", JR,
                      "还在按个数判「打没打过分」")
        # **先剥注释。** 旧那个表达式被逐字写进了解释它的注释里，
        # 整文件扫会撞上自己的说明。
        code = re.sub(r"/\*.*?\*/", "", JR, flags=re.S)
        self.assertNotIn("minus.length === job.dimensions.length", code)

    def test_both_empty_state_messages_survive(self):
        """两句都要在 —— 修的是走哪一句，不是删一句。"""
        self.assertIn("这几项都还没打分，加分项无从谈起。", JR)
        self.assertIn("没有明显加分项——分数主要靠没踩雷撑着。", JR)

    def test_the_always_true_reason_is_recorded(self):
        i = JR.index("minus.every((d) => d.score === null)")
        seg = " ".join(JR[max(0, i - 700):i].split())
        self.assertRegex(seg, r"那个等式\*\*恒为真\*\*")
        self.assertRegex(seg, r"61 个是打过分、 只是都低于 70"
                              r"|61 个是打过分、只是都低于 70")

    def test_the_not_scored_wording_survives_for_real_dimensions(self):
        """真维度没打分时那句话是对的 —— 不能被这次改动带掉。"""
        self.assertIn("这项没打分——", JR)


if __name__ == "__main__":
    unittest.main()
