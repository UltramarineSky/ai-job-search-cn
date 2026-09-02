# -*- coding: utf-8 -*-
"""`来源` 标着「深评回写」，`依据` 却是粗筛那一轮留下的话。

`writeback.py` 把分、判词、四维、`来源` 全按 `evaluation.md` 写回，**唯独不碰
`依据`**。于是这一格标着深评的出处、内容却在解释别的数字 —— 而它会过
`plain()` 进总览页短名单行的悬浮提示，是用户真读到的字。

实测活动用户 2026-08-27（跑完 `/job-auto` 出材料后查出来的，不是扫出来的）：
249 条标着深评回写的条目里

    形状 1  依据点名某一维给了多少分，而库里存的不是那个数     1 条
            （写「发展这一维给 85」，库里 72）
    形状 2  依据还写着「预筛 / 未抓 JD / 粗筛」，来源已标深评   18 条

## 为什么只报不改

试过按 `evaluation.md` 里每一维自己的说明机械重拼这一格，**实测更差**：

    旧（手写）：……JD 工作经验那条明写「具备互联网保险或保险科技公司的业务背景，
              熟悉人身险……能与保险业务方深度对话」——保险业务域你是零，这是这个
              岗最大的一道坎。……FLAG：要求「计算机、人工智能、保险、精算、金融等
              相关专业」，你是历史专业……
    新（重拼）：技能与经验：专业能力 80 · 行业经验 20……；发展与风险：见下；
              地点（跨城搬迁）：上海

JD 原话没了、专业那条提醒没了，换来一串维度名加冒号，还带进一句出了上下文
就没意义的「见下」。**重写这段话要判断力**，那是写深评那一步的事。

## 判据不许放宽成「字不一样」

第一版拿「重拼的结果和库里的不一样」当分叉判据，试运行当场报出要改 **249 条** ——
库里那些依据本来就是历次深评手写的正文，和机器拼的本就不同字。同一个教训
`writeback.py` 里已经写过一次（「检测『不一致』不该顺手删信息。数没变就别动
这一格」），这里是第二次。所以只认**能证明它旧了**的那两种形状。
"""
import pathlib
import re
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tests"))
import writeback as W  # noqa: E402
from _srcscan import code_of  # noqa: E402

DEEP = {"来源": "深评（writeback.py 从 evaluation.md 回写）",
        "发展与风险": 72, "强度与公司性质": 50}


class TheDetectorFiresOnWhatItCanProve(unittest.TestCase):
    def test_a_dimension_score_that_contradicts_the_store(self):
        self.assertTrue(W._basis_is_stale(
            "……发展这一维给 85：大厂 + AI 创新。", DEEP))

    def test_the_same_number_is_not_stale(self):
        self.assertFalse(W._basis_is_stale(
            "……发展这一维给 72：大厂 + AI 创新。", DEEP))

    def test_prescreen_wording_under_a_deep_eval_stamp(self):
        self.assertTrue(W._basis_is_stale(
            "年包上沿约 25 万（来源：预筛（未抓 JD））", DEEP))

    def test_prescreen_wording_under_a_prescreen_stamp_is_fine(self):
        """粗筛条目的依据写着粗筛口径，那是对的，不是旧的。"""
        self.assertFalse(W._basis_is_stale(
            "年包上沿约 25 万（来源：预筛（未抓 JD））", {"来源": "预筛（未抓 JD）"}))

    def test_an_empty_basis_is_not_stale(self):
        self.assertFalse(W._basis_is_stale("", DEEP))

    def test_other_two_digit_numbers_do_not_trip_it(self):
        """「团队 85 人」不是维度分。判据窄一点，宁可漏不可误伤。"""
        self.assertFalse(W._basis_is_stale("这个岗 30-60k，团队 85 人。", DEEP))


class ItReportsAndDoesNotRewrite(unittest.TestCase):
    """**只报不改。** 机器重拼这一格实测比手写的差，理由记在模块 docstring 里。"""

    SRC = (ROOT / "tools" / "writeback.py").read_text(encoding="utf-8")

    def test_the_basis_is_never_written_back(self):
        seg = code_of("tools/writeback.py", "def main(")
        self.assertNotIn('b["依据"]', seg,
                         "writeback 又开始改 `依据` 了 —— 那一格要判断力，只报不改")

    def test_the_report_names_the_command_that_fixes_it(self):
        """`AGENTS.md`「每一处引导都要写出该敲的命令」。"""
        self.assertRegex(self.SRC, r"重写那一段：/job-apply")

    def test_the_report_uses_words_the_user_speaks(self):
        """`AGENTS.md` 措辞表：`依据`、`四维`、`判词` 是内部词，不上台面。"""
        i = self.SRC.index("个岗的岗位详情里那段解释和分数对不上")
        line = self.SRC[i - 120:i + 220]
        for w in ("判词", "四维", "硬门", "台账", "读数"):
            self.assertNotIn(w, line, f"给用户看的那句里出现了内部词「{w}」")

    def test_the_reason_it_only_reports_is_written_down(self):
        head = self.SRC[:self.SRC.index("def ")]
        self.assertIn("只报不改", head, "撤掉机械重写的理由没留在原地")
        self.assertIn("2026-08-27", (ROOT / "tests" / pathlib.Path(__file__).name)
                      .read_text(encoding="utf-8"), "实测数没带日期")


class TheStampAndTheProseComeFromTheSamePlace(unittest.TestCase):
    """这条守卫的由头：`来源` 是 writeback 写的，`依据` 不是 —— 一格里两个出处。"""

    def test_writeback_still_stamps_the_source(self):
        seg = code_of("tools/writeback.py", "def main(")
        self.assertIn('b["来源"] = "深评（writeback.py 从 evaluation.md 回写）"', seg,
                      "那个戳没了，这条守卫的前提也就没了")

    def test_the_two_shapes_are_the_only_ones_claimed(self):
        """docstring 记的是「两种形状」。加了第三种要连同实测数一起更新。"""
        src = (ROOT / "tools" / "writeback.py").read_text(encoding="utf-8")
        i = src.index("_DIM_SAID = ")
        seg = src[max(0, i - 900):i]          # 判据前面那段 `#:` 注释
        self.assertIn("形状 1", seg)
        self.assertIn("形状 2", seg)
        self.assertNotIn("形状 3", seg, "加了第三种形状，实测数要一起更新")
        self.assertTrue(re.search(r"249 条", seg),
                        "分母没写在检测器旁边 —— 下一个人不知道这 19 条占多少")


class NamingThePrescreenIsNotLeftoverFraming(unittest.TestCase):
    """深评讲「粗筛当时怎么看」，那不是残留口径 —— 那正是它该写的东西。

    ## 实测

    形状 2（文本提到「预筛 / 未抓 JD / 粗筛」而来源已是深评回写）
    2026-08-31 报了 18 条。**18 条全都含「深评」二字**，讲的正是深评与粗筛
    的关系：

        深评翻案（粗筛 68 值得投 → 深评 67 可以考虑）。判词被技能 58 压下来。
        这家的工作强度粗筛没有信号，深评读完 JD 才补上。

    那解释的就是面板上当前这个分怎么来的。而报文写着「用户读到的是在解释
    别的数字」—— 对这 18 条来说，**那句话本身才是假的**。

    收窄之后这一形状归零，整条检查从 22 个降到 4 个（只剩形状 1），
    收尾去重总数 110 → 109。

    ## 判据

    真正的残留长什么样：通篇按粗筛口径讲、**一次都没提深评**。
    """

    def test_a_deep_eval_narrating_the_flip_is_not_stale(self):
        b = {"来源": "深评（writeback.py 从 evaluation.md 回写）",
             "技能与经验": 58}
        old = "深评翻案（粗筛 68 值得投 → 深评 67 可以考虑）。判词被技能 58 压下来。"
        self.assertFalse(W._basis_is_stale(old, b))

    def test_real_leftover_framing_is_still_caught(self):
        """通篇粗筛口径、一次没提深评 —— 那才是抓 JD 之前留下的。"""
        b = {"来源": "深评（writeback.py 从 evaluation.md 回写）"}
        old = "粗筛按标题给的分：门槛低、方向对得上，正文没读。"
        self.assertTrue(W._basis_is_stale(old, b))

    def test_a_wrong_number_is_still_caught(self):
        """形状 1 不受影响 —— 收窄不能把它一起收掉。"""
        b = {"来源": "深评（writeback.py 从 evaluation.md 回写）",
             "技能与经验": 58}
        old = "深评翻案。技能这一维给 72。"
        self.assertTrue(W._basis_is_stale(old, b))

    def test_the_measurement_is_recorded(self):
        src = (pathlib.Path(W.__file__).read_text(encoding="utf-8"))
        i = src.index("_PRESCREEN_WORDS")
        seg = src[max(0, i - 1600):i]
        self.assertIn("18 条全都含", seg, "没留实测，这条收窄就成了口味")


if __name__ == "__main__":
    unittest.main()
