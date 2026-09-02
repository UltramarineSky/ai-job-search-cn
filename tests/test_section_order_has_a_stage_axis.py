# -*- coding: utf-8 -*-
"""章节顺序要按**行业**调，也要按**他在职业的哪一段**调。

`05-cv-templates.md` 的基线顺序把「教育背景」放在第 6 位 —— 对有若干年经验的人
是对的，**对应届生是反的**：校招里学校与专业是第一道筛，而这批人的「工作经历」
通常只有一段实习、「项目经历」是课程作业。把最强的信号压在第 6 行，
等于让 HR 先读两段最弱的。

原来那一节写着「基线顺序本身不是普适的」，然后列了两处调整 ——
**两处都在行业轴上**（项目经历的叫法、执业资格前置）。阶段这一轴整个没有。

> 而同一份文件的「页数」那一节**已经点到应届生**（「一段实习 + 课程项目……
> 压不满 2 页就写 1 页」）—— 知道有这类用户，却只在长度上照顾了，顺序上没有。
> **一条规则只写在一个维度上，另一个维度照样会错。**
"""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CV = (ROOT / "workflows" / "reference"
      / "05-cv-templates.md").read_text(encoding="utf-8")


def _order_section() -> str:
    i = CV.index("### 章节顺序按行业定")
    return CV[i:CV.index("\n## ", i)]


class TheStageAxisExists(unittest.TestCase):
    def test_fresh_graduates_get_education_early(self):
        seg = _order_section()
        self.assertIn("应届生", seg, "顺序那一节没管应届生")
        self.assertRegex(seg, r"「教育背景」要提到「工作经历」之前",
                         "没说清应届生该怎么排")

    def test_it_is_marked_as_a_different_axis(self):
        """前两处是行业轴，这一条是阶段轴 —— 不点明就会被当成第三个行业例子。"""
        seg = _order_section()
        self.assertRegex(seg, r"不是行业、是阶段|看他在职业的哪一段",
                         "没说清这一条和前两条不是同一个轴")

    def test_the_intro_counts_three_not_two(self):
        """引导句说「典型是两处」而底下有三条，读的人会以为漏了一条。"""
        seg = _order_section()
        self.assertNotIn("典型是两处", seg, "引导句还写着两处")
        self.assertIn("典型是三处", seg)

    def test_the_content_depth_differs_too(self):
        """应届那份教育要写得更厚 —— 只调顺序不调内容，等于把一行字挪了个位置。"""
        seg = _order_section()
        self.assertRegex(seg, r"GPA|专业课", "没说清应届的教育背景要写什么")


class TheBaselineIsStillTheBaseline(unittest.TestCase):
    """别把例外写成默认 —— 多数用户是社招。"""

    def test_the_default_order_is_unchanged(self):
        self.assertRegex(CV, r"6\. 教育背景", "基线顺序被改掉了")

    def test_the_no_reorder_per_job_rule_survives(self):
        """这一节的原意是「不许为每个岗重排」，加阶段轴时不能把它顺手放松。"""
        self.assertIn("不许为每个岗重排", CV)

    def test_it_still_refuses_to_ship_an_industry_list(self):
        self.assertRegex(CV, r"框架不提供行业清单",
                         "顺手塞了一张行业清单进来")


if __name__ == "__main__":
    unittest.main()
