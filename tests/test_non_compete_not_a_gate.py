"""竞业限制不是硬门。

## 为什么改

国内**绝大多数求职者没签过竞业协议**，签了的自己很清楚限制哪几家。把它做成一票否决的
硬门，代价是候选人资料里那一栏多半是 `/job-setup` 填的假设值「无（← 假设值）」，于是
**每一个职位都会挂一条「投前请自己确认」**——用一条永远为真的提醒污染每份评估，
而它对 99% 的岗位没有任何判别力。实测 3 个深评岗全部中招。

规则：不进硬门表；只有用户**真报了限制范围**时，才作为一条不计分的提醒出现。
"""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import export_web_data as ex  # noqa: E402

HEAD = "## 硬门检查\n\n| 门槛 | 结果 | 依据 |\n|---|---|---|\n"


def gates(rows: str):
    """跑一遍导出器的硬门解析，返回门名列表。"""
    text = HEAD + rows + "\n## 四维打分\n\n| 维度 | 分数 |\n|---|---|\n| 技能与经验 | 70 |\n"
    header, body = ex.parse_table(text, "硬门")
    i_g = ex._col(header, "硬门", "门槛", "条件", default=0)
    i_v = ex._col(header, "判定", "结果", "结论", default=1)
    i_b = ex._col(header, "依据", "说明", "原文", default=2)
    out = []
    for row in body:
        if len(row) <= max(i_g, i_v, i_b):
            continue
        r = [row[i_g], row[i_v], row[i_b]]
        if "竞业" in r[0]:
            basis = r[2]
            if ("假设值" in r[1] or "假设值" in basis or "无" in basis
                    or "未涉及" in basis):
                continue
        out.append(r[0])
    return out


class AssumedNonCompeteIsDropped(unittest.TestCase):
    def test_assumed_value_row_is_dropped(self):
        g = gates("| 学历院校 | PASS | 本科即可 |\n"
                  "| 竞业限制 | PASS（基于假设值，请确认） | 你的资料未确认 |\n")
        self.assertNotIn("竞业限制", g,
                         "假设值来的竞业条目会让每个岗都挂一条无判别力的提醒")
        self.assertIn("学历院校", g, "别把别的硬门一起删了")

    def test_explicit_none_is_dropped(self):
        g = gates("| 竞业限制 | PASS | 候选人竞业为「无」 |\n")
        self.assertNotIn("竞业限制", g)

    def test_real_restriction_is_kept(self):
        """用户真报了限制范围的，要留着让他自己判断。"""
        g = gates("| 竞业限制 | FLAG | 与前东家签至 2027-03，限制字节/腾讯/阿里 |\n")
        self.assertIn("竞业限制", g, "真实的竞业限制不能丢")

    def test_other_gates_survive(self):
        g = gates("| 学历院校 | PASS | 本科即可 |\n"
                  "| 外包/驻场 | PASS | 甲方直招 |\n"
                  "| 竞业限制 | PASS（基于假设值） | 未确认 |\n"
                  "| 工作年限 | FLAG | 刚过线 |\n")
        self.assertEqual(g, ["学历院校", "外包/驻场", "工作年限"])


class FrameworkNoLongerListsItAsAGate(unittest.TestCase):
    """文档也要改掉——留在硬门表里，下一轮 /job-rank 又会把它判成一票否决。"""

    def test_not_in_the_veto_table(self):
        t = (ROOT / "workflows" / "reference" / "04-job-evaluation.md").read_text(
            encoding="utf-8")
        veto = t[t.index("## 第一步"):t.index("### 竞业限制")]
        self.assertNotIn("| **竞业限制**", veto, "竞业还在一票否决表里")

    def test_the_reason_is_written_down(self):
        """要写清为什么不是硬门，否则下次又会被加回去。"""
        t = (ROOT / "workflows" / "reference" / "04-job-evaluation.md").read_text(
            encoding="utf-8")
        self.assertIn("竞业限制**不是硬门**", t)
        self.assertIn("没有签过竞业协议", t)

    def test_rank_prompt_does_not_ask_for_it(self):
        t = (ROOT / "workflows" / "job-rank.md").read_text(encoding="utf-8")
        self.assertNotIn('"竞业限制": "PASS"', t,
                         "rank 的输出结构里还要求这一项，agent 就还会去判")


class SetupDoesNotMarkItAsAssumed(unittest.TestCase):
    def test_setup_tells_not_to_mark_assumed(self):
        t = (ROOT / "workflows" / "job-setup.md").read_text(encoding="utf-8")
        i = t.index("问：竞业限制")
        seg = t[i:i + 700]
        self.assertIn("不要加", seg, "要明确交代别标成假设值")
        self.assertIn("假设值", seg)


if __name__ == "__main__":
    unittest.main()
