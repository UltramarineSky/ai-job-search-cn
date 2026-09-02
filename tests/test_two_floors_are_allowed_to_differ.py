# -*- coding: utf-8 -*-
"""薪资底线在这个仓库里有两个取值，而且**必须**是两个。

资料里常有两个数：常规的「可接受底线」，加一句「方向极对的岗可以降到 X 谈」。
两处代码各取一个，方向相反：

| 谁 | 取哪个 | 用途 | 取错了的代价 |
|---|---|---|---|
| `prescreen.py --annual-floor`（工作流传进去） | **最宽**（低的） | 淘汰 | 结案不可逆，那个岗就没了 |
| `audit_pipeline._annual_floor()` | **常规**（高的） | 打分分档 | 重评一次就好 |

预筛只有标题和薪资串，**判不了方向极不极对** —— 那是评估那一步才知道的事；
而它又是四条规则里唯一能结案的。所以它只能用最宽的。打分那一侧不同：
弹性是谈判姿态，不是打分输入，`04-job-evaluation.md` 的「有月薪、但没写几薪」
拿常规底线当基准分档。

## 为什么这条测试要存在

**看到两个数不一样，下一个人会想去统一它。** 而两边统一都会坏事：

- 都改成宽的 → 打分那条的分档基准跟着降，该挂「先问几薪」的挂不出来
- 都改成严的 → 预筛误杀的恰好是弹性条款专门要保护的那批

2026-08-26 之前，两处各自都对，却**没有任何一处写着它们为什么不同** ——
那正是等着被「顺手统一」的形状。这个文件把那句话钉住。
"""
import re
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import audit_pipeline as ap  # noqa: E402

AUTO = (ROOT / "workflows" / "job-auto.md").read_text(encoding="utf-8")
SRC = (ROOT / "tools" / "audit_pipeline.py").read_text(encoding="utf-8")

#: 一份两个数都写了的资料 —— 现实里最常见的形状。
#: **数字是编的**（`test_no_maintainer_data_in_repo` 盯着：真实取值 + 归属词
#: 出现在同一行，就算把它当成某个人的数在引用）。这条测试验的是「读哪一行」，
#: 与具体取多少无关，随便两个数都行 —— 只要够分得开。
PROFILE = """## 薪资

- **目标区间：** 50k × 16薪
- **可接受底线：** 40k × 16薪（年包 **77 万**）
- **薪资弹性**：方向极对的岗可以降到 **63 万**谈；一般岗位按底线执行。
"""
#: 上面那份里两个数各是多少 —— 断言引它，别在下面重写字面量。
REGULAR, FLEXIBLE = 77.0, 63.0


class TheScoringSideReadsTheRegularFloor(unittest.TestCase):
    def _floor(self, text: str):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            d = root / "users" / "u" / "profile"
            d.mkdir(parents=True)
            (d / "candidate.md").write_text(text, encoding="utf-8")
            with mock.patch.object(ap, "ROOT", root), \
                 mock.patch.object(ap, "_USER", ["u"]):
                return ap._annual_floor()

    def test_it_takes_the_regular_one_not_the_flexible_one(self):
        got = self._floor(PROFILE)
        self.assertNotEqual(got, FLEXIBLE,
                            "打分那一侧读成了弹性下限 —— 该挂「先问几薪」的会漏挂")
        self.assertEqual(got, REGULAR)

    def test_the_flexibility_line_alone_is_not_enough(self):
        """只有弹性那句、没有「可接受底线」时如实说没查，不要拿弹性数顶上。"""
        only_flex = ("## 薪资\n\n- **薪资弹性**：方向极对的岗可以降到 "
                     f"**{FLEXIBLE:.0f} 万**谈。\n")
        self.assertIsNone(self._floor(only_flex))

    def test_no_profile_reads_nothing(self):
        self.assertIsNone(self._floor("## 薪资\n\n- 面议\n"))


class BothSitesSayWhyTheyDiffer(unittest.TestCase):
    """两处都要写明，因为下一个人只会读到其中一处。"""

    def _seg(self) -> str:
        i = SRC.index("def _annual_floor(")
        return SRC[i:SRC.index("\ndef ", i + 10)]

    def test_the_scoring_side_warns_against_unifying(self):
        seg = self._seg()
        self.assertIn("别去统一", seg)
        self.assertIn("打分", seg)
        self.assertIn("不可逆", seg, "没说清另一侧为什么必须更宽")

    def test_the_workflow_side_warns_too(self):
        i = AUTO.index("`--annual-floor` 取最宽的那个数")
        self.assertIn("别去统一", AUTO[i:i + 2000],
                      "流程那侧只讲了自己该取哪个，没说另一处取别的也是对的")

    def test_the_scoring_side_names_the_other_site(self):
        """指名道姓，否则读者不知道去哪核对。"""
        self.assertIn("prescreen", self._seg())

    def test_the_workflow_side_names_the_scoring_helper(self):
        i = AUTO.index("`--annual-floor` 取最宽的那个数")
        self.assertIn("_annual_floor", AUTO[i:i + 2000])


class TheDirectionOfTheAsymmetryIsRecorded(unittest.TestCase):
    def test_both_sides_state_which_error_is_recoverable(self):
        """判据不是「哪个数大」，是「错了能不能挽回」—— 只有这句能推出该取哪个。"""
        for name, text in (("audit_pipeline", SRC), ("job-auto.md", AUTO)):
            with self.subTest(where=name):
                self.assertTrue(
                    re.search(r"打分错了还能重评，结案错了那个岗就没了", text),
                    f"{name} 没写下那条不对称 —— 少了它，两个数看着就只是矛盾")


if __name__ == "__main__":
    unittest.main()
