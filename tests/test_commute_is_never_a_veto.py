"""通勤时长不是门——这条规则在下游不许被偷偷加回去。

`04-job-evaluation.md` 第 4.2 节用一整节论证它，理由三条：

1. 通勤是**连续量**，45 分钟和 65 分钟没有本质区别，阈值定在哪都是武断的；
2. 资料里那个通勤上限**多半是假设值**（`/job-setup` 缺信息时填的，用户从没确认过）——
   拿没核实的数字去一票否决，是「最贵的判断 + 最弱的证据」；
3. 人会为好岗位接受更长通勤，这个权衡不该由工具替他做掉。

可 `scrape.md` 的「Important Rules」第 3 条原来写着：

    Skip jobs that require relocation or are clearly outside commute range.

**`/job-scrape` 是整条流水线的第一步。** 它这里丢掉的岗连 `/job-rank` 都到不了，
不会出现在任何清单、任何计数、任何报表里——用户永远不知道有过这个岗。
框架里那一整节论证，在最上游被一句话推翻了。

跨城**搬迁**是门（二值、且有确凿证据），同城**通勤**不是。这两件事不能混。
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FRAMEWORK = ROOT / "workflows" / "reference" / "04-job-evaluation.md"

#: 会在早期筛掉职位的工作流。新增一个就往这里加。
UPSTREAM = ("job-scrape.md", "job-rank.md")

#: 「按通勤筛掉」的说法。命中且同一行没有「不否决/不跳过」这类否定 → 违规。
VETO = (re.compile(r"outside commute range", re.I),
        re.compile(r"通勤.{0,12}(?:超过|太远|过远).{0,12}(?:跳过|排除|不要|剔除)"),
        re.compile(r"(?:跳过|排除|剔除).{0,12}通勤"))

ABOUT = ("不否决", "不跳过", "一概不", "不参与否决", "原来写的是", "直接冲突")


class CommuteIsNeverAVeto(unittest.TestCase):

    def test_the_framework_still_says_so(self):
        """控制用例：框架里那条规则还在，否则本测试拦的是不存在的规则。"""
        t = FRAMEWORK.read_text(encoding="utf-8")
        self.assertIn("不参与否决", t,
                      "框架里「同城通勤时长不参与否决」不见了——本测试失去依据")

    def test_upstream_files_exist(self):
        """控制用例：要扫的文件都在。"""
        missing = [f for f in UPSTREAM if not (ROOT / "workflows" / f).is_file()]
        self.assertEqual(missing, [], f"UPSTREAM 里这些文件不存在：{missing}")

    def test_no_upstream_step_skips_on_commute(self):
        bad = []
        for name in UPSTREAM:
            p = ROOT / "workflows" / name
            for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
                if any(k in line for k in ABOUT):
                    continue
                if any(r.search(line) for r in VETO):
                    bad.append(f"workflows/{name}:{i}  {line.strip()[:64]}")
        self.assertEqual(
            bad, [],
            "上游按通勤把职位筛掉了：" + chr(10) + "  " + (chr(10) + "  ").join(bad)
            + chr(10) + "框架第 4.2 节：通勤是连续量、上限多半是没确认过的假设值，不配当一票否决。"
            + chr(10) + "而且上游丢掉的岗连 /job-rank 都到不了——用户永远不知道有过它。")

    def test_the_detector_can_actually_fail(self):
        """变异内建：构造一句违规文本，检查器必须认得。"""
        self.assertTrue(any(r.search("Skip jobs clearly outside commute range.")
                            for r in VETO))
        self.assertTrue(any(r.search("通勤超过一小时的直接排除") for r in VETO))


if __name__ == "__main__":
    unittest.main()
