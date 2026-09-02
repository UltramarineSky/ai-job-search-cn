# -*- coding: utf-8 -*-
"""「明天二面」——而阶段地图里没有「二面」这一行。

`07-interview-prep.md` 那张阶段地图按**谁面、考察什么**索引：
在线测评 / 笔试机试 / 群面无领导 / 演练实操 / HR 初面 / 专业面 / 交叉面 /
总监面终面 / 谈薪 / 背调。整份准备包（`/job-interview` Step 3）也是按**性质**分流的
——「电话初筛问动机和时间线；专业面问 JD 那套技术；终面问价值观、薪资」。

**而 HR 通知里写的、候选人嘴里说的，几乎都是序数。** 两套叫法之间**没有固定映射**：
同样是「一面」，有的公司是 HR 初面、有的直接上用人部门 leader；有的把交叉面并进
二面、有的压根没有终面（那张表开头「可能合并或跳过其中几关」说的就是这件事）。

Step 1 原来问的是「第几关、什么时间、什么形式、谁来面（知道名字和职务的话一并问）」
—— 序数是必答的，而**决定性质的那一问是括号里的可选项**。用户答「二面」，
分流就只能靠猜。

所以：**记序数，判性质**，两件事。序数照旧用来编号（准备包文件名、模拟面轮次），
性质靠追问一句「这一关是谁面你」——**面试官的身份决定这一关问什么**。
问不出来就按上一关往下推一格，并说明那是推断。
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PREP = (ROOT / "workflows" / "reference"
        / "07-interview-prep.md").read_text(encoding="utf-8")
IV = (ROOT / "workflows" / "job-interview.md").read_text(encoding="utf-8")


def _stage_map() -> str:
    i = PREP.index("## 一、国内面试阶段地图")
    m = re.search(r"^## ", PREP[i + 5:], re.M)
    return PREP[i:i + 5 + m.start()] if m else PREP[i:]


class TheStageMapSaysItIsNotIndexedByOrdinal(unittest.TestCase):
    def test_the_note_exists(self):
        self.assertIn("「二面」不是这张表里的一行", _stage_map(),
                      "阶段地图没说清它不按序数索引")

    def test_it_says_there_is_no_fixed_mapping(self):
        """给一张假的映射表（一面=HR 初面…）比不给更坏。"""
        self.assertRegex(_stage_map(), r"没有固定映射")

    def test_it_gives_the_resolving_question(self):
        """光说「别猜」是把人留在原地。要给出问哪一句。"""
        seg = _stage_map()
        self.assertRegex(seg, r"这一关是谁面你")
        self.assertRegex(seg, r"面试官的身份决定这一关问什么")

    def test_it_says_what_to_do_when_nobody_answers(self):
        """问不出来时要有一条路，而且要标明那是推断。"""
        seg = _stage_map()
        self.assertRegex(seg, r"按\*\*上一关是谁\*\*往下推一格|往下推一格")
        self.assertRegex(seg, r"那是推断，不是事实|让他自己核一眼")

    def test_the_ordinal_is_still_used_for_numbering(self):
        """**别把序数一起否掉** —— 文件名和模拟面轮次都按它编号。"""
        seg = _stage_map()
        self.assertRegex(seg, r"记序数，判性质")
        self.assertIn("interview_prep_", seg, "没说清序数还用在哪儿")

    def test_the_merged_rounds_caveat_survives(self):
        """「可能合并或跳过其中几关」是这条规矩的前提，不许被挤掉。"""
        self.assertIn("可能合并或跳过其中几关", _stage_map())


class TheWorkflowAsksTheResolvingQuestion(unittest.TestCase):
    def _seg(self):
        i = IV.index("**问清楚这次面试是什么**")
        return IV[i:i + 900]

    def test_who_is_interviewing_is_not_optional_any_more(self):
        """原来那一问是括号里的「知道名字和职务的话一并问」——
        而它才是决定整份准备包怎么分流的那一项。"""
        seg = self._seg()
        self.assertIn("**谁来面**", seg, "「谁来面」还是可选的附带项")
        self.assertNotIn("知道名字和职务的话一并问", seg)

    def test_it_says_the_ordinal_is_not_the_answer(self):
        self.assertRegex(self._seg(), r"他多半会答「二面」|那不是性质")

    def test_it_does_not_draw_its_own_table(self):
        """判据只有一份。把序数→性质写成表就是伪造那个映射 ——
        阶段地图自己刚说过没有固定映射。"""
        rows = re.findall(r"^\s*\|", self._seg(), re.M)
        self.assertEqual(rows, [], "这一步自己又画了一张表")

    def test_the_link_to_the_stage_map_survives(self):
        """这一步只说「问谁面」，**怎么应对**在阶段地图里 ——
        那条链接（这一步原有的）断了，追问到的答案就无处可用。
        新加那段不再自带链接：同一段里已经有一条，重复即噪音。"""
        seg = self._seg()
        self.assertIn("07-interview-prep.md", seg, "这一步不再指向阶段地图")
        self.assertEqual(seg.count("07-interview-prep.md"), 1,
                         "同一段里指了两次同一份文件")

    def test_the_role_outranks_the_name(self):
        """姓名用来查公开主页（Step 3 那条），职务用来定这一关问什么 ——
        后者才是这一步要拿到的。"""
        self.assertRegex(self._seg(), r"职务比姓名要紧|面试官的身份决定")

    def test_step_three_still_branches_on_nature(self):
        """这一步的全部意义就是喂给 Step 3 那个分流。它没了就白问。"""
        self.assertIn("**这一关是什么性质**", IV)


class TheStageListItselfIsUnchanged(unittest.TestCase):
    """阶段清单是这条规矩的对象，动了它这条就落空。"""

    STAGES = ("在线测评", "笔试", "群面", "无领导", "演练", "HR 初面",
              "专业面", "交叉面", "终面", "谈薪", "背调")

    def test_every_stage_still_has_a_row(self):
        seg = _stage_map()
        for st in self.STAGES:
            with self.subTest(stage=st):
                self.assertIn(st, seg, f"阶段地图里没有「{st}」了")

    def test_the_workflow_still_lists_them_when_asking(self):
        """Step 1 问的时候要把清单摆出来 —— 用户不知道有「交叉面」这种东西。"""
        seg = IV[IV.index("**问清楚这次面试是什么**"):][:1600]
        for st in ("在线测评", "群面", "交叉面", "谈薪"):
            with self.subTest(stage=st):
                self.assertIn(st, seg)


if __name__ == "__main__":
    unittest.main()
