"""名单头部的材料备得太少时，面板要说出来，并且给出那条能敲的命令。

## 为什么需要这条

实测：可以投的岗位 145 个，**前 20 里只有 2 个备好了材料**。而一份材料要走完整条
`/job-apply`（读 JD、查公司、起草、审稿、编译 PDF），不是点一下就有的。

于是面板处在一个很坏的状态：它给了你一份 145 行的名单，你挑中一个想投，
**却发现投不出去**——材料要现做，而做一份要几分钟到十几分钟。名单越长这件事越隐蔽，
因为它看起来「东西很多」。

## 三条边界

1. **必须给出命令，不能只报数字。** 这一页的通例是「每处引导都写出该敲的命令」——
   说「材料不够」而不说怎么补，等于把问题原样还给用户。
2. **命令要真的存在。** 面板打印 `/job-apply --top N`，`workflows/job-apply.md` 里就必须有
   这个参数的定义，否则用户照着敲，AI 只会当成一个不认识的输入。
   这一条是**跨文件**的：TSX 里改了数字、apply.md 忘了跟，两边不会互相报错。
3. **不许永远显示。** 名单本身不足 5 个的时候，「前 20 里只有 2 个有材料」是句废话；
   备齐之后它也该消失。一条永远在的提醒等于没有提醒
   （`test_web_copy.py::WarningsOnlyShowWhenThereIsSomethingToWarnAbout` 同一条原则）。

## 闸门那条为什么钉在这里

批量出材料最容易被写成「前 N 个全出」。那会把整条流程里最贵的一段
（每个岗一次公司调研 + 一次审稿 + 一次 Typst 编译）花在**读完 JD 之后发现不该投**
的岗上——而 `/job-apply` 第 1 步本来就会得出这个结论，实测过粗筛 76「强匹配」、
深评 62 的 14 分落差。所以闸门是这个批量模式存在的前提，不是可选优化，
它必须写在工作流里、并且被守住。
"""

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

APP = ROOT / "web" / "src" / "App.tsx"
APPLY = ROOT / "workflows" / "job-apply.md"


def batch_section() -> str:
    """`### --top N` 那一整节，到下一个同级标题为止。

    **不要用固定字数的窗口。** 原来这里写 `doc[i:i+3000]`，那一节后来补了选岗口径、
    兜底路径与「批量不回头问」几段，长度翻倍——于是「停手条件」掉出窗口，
    测试红了，而文档一个字都没少。固定窗口断言会随着文档变长而假报警，
    正是本仓库反复吃过亏的那种脆断言。
    """
    text = APPLY.read_text(encoding="utf-8")
    m = re.search(r"^###\s+`--top N`.*?(?=^###\s|\Z)", text, re.S | re.M)
    assert m, "apply.md 里找不到 `--top N` 那一节 —— 改标题了？"
    return m.group(0)


def app() -> str:
    return APP.read_text(encoding="utf-8")


class ThePanelNoticesAndSaysWhatToRun(unittest.TestCase):

    def test_the_threshold_is_named_not_inlined(self):
        """阈值要有名字。散落的魔法数字改一处漏一处。"""
        s = app()
        self.assertRegex(s, r"const TOP_N\s*=\s*\d+",
                         "没有 TOP_N —— 前多少个算「头部」得说出来")
        self.assertRegex(s, r"const MATERIALS_FLOOR\s*=\s*\d+",
                         "没有 MATERIALS_FLOOR —— 少于几个才提示得说出来")

    def test_it_prints_a_runnable_command(self):
        s = app()
        self.assertIn("/job-apply --top", s,
                      "只报了数字没给命令 —— 等于把问题原样还给用户")

    def test_the_command_uses_the_same_number_as_the_message(self):
        """句子里说「前 20 个」，命令却是 `--top 10`，用户照做会补不到他看到的那批。"""
        s = app()
        self.assertRegex(
            s, r"/job-apply --top \$\{TOP_N\}",
            "命令里的数字是写死的 —— 必须跟 TOP_N 同一个来源")

    def test_it_only_shows_when_it_has_something_to_say(self):
        s = app()
        self.assertRegex(
            s, r"const materialsThin\s*=",
            "没有触发条件 —— 提醒会一直挂在那儿")
        i = s.find("const materialsThin")
        seg = s[i:i + 300]
        self.assertIn("MATERIALS_FLOOR", seg, "触发条件没用上阈值")
        self.assertRegex(
            seg, r"\.size\s*>=\s*MATERIALS_FLOOR",
            "名单本身很短时也会提示 —— 只有 3 个可投的岗，"
            "「前 20 里只有 2 个有材料」是句废话")

    def test_the_count_comes_off_the_same_list_the_user_sees(self):
        """从 `sellable` 数，不另起一份过滤。两处各写一份判断，飘起来是必然的。"""
        s = app()
        i = s.find("const topReady")
        self.assertNotEqual(i, -1, "找不到 topReady")
        seg = s[i:i + 400]
        self.assertIn("sellable", seg,
                      "材料覆盖率不是从「可以投」那份名单数的 —— "
                      "会出现「名单里 20 个、提示说前 20 个」对不上的情况")


class TheCommandTheyAreToldToRunActuallyExists(unittest.TestCase):
    """跨文件：面板打印的参数，工作流里必须有定义。"""

    def test_apply_documents_the_flag(self):
        doc = APPLY.read_text(encoding="utf-8")
        self.assertIn("--top", doc,
                      "面板让用户敲 `/job-apply --top N`，而 apply.md 里没有这个参数")

    def test_apply_defines_the_gate(self):
        seg = batch_section()
        self.assertIn("闸门", seg,
                      "批量模式没有闸门 —— 会把最贵的那段花在读完 JD 才发现不该投的岗上")
        for w in ("值得投", "不建议"):
            self.assertIn(w, seg, f"闸门没说清「{w}」这一档怎么办")

    def test_apply_defines_a_stop_condition(self):
        """批量最怕闷头跑完 20 个。环境坏了要停、整批都不过也要停。"""
        seg = batch_section()
        self.assertIn("停手条件", seg, "批量模式没有停手条件")

    def test_the_selection_reads_the_panels_own_snapshot(self):
        """选岗必须读面板那份快照，不能照着 `seen_jobs.json` 自己再筛一遍。

        散文口径实测第一次跑就漏了两类：同一个岗在一家公司挂 3 个价会被跑 3 遍；
        已有材料的目录名去过括号（`AI产品经理Marketing方向`），拿原始标题模糊匹配
        匹不上。这两件事导出器早就算对了（`dupOf` / `materials`），
        第二个实现只会飘。
        """
        seg = batch_section()
        self.assertIn("data.json", seg, "没说从面板快照选岗")
        for f in ("dupOf", "materials", "applied"):
            self.assertIn(f, seg, f"选岗没用上 `{f}` 这个字段")

    def test_the_batch_does_not_introduce_a_python_dependency(self):
        """`/job-apply` 不依赖 Python——README 与 SETUP 都这么承诺。

        读 `data.json` 只是读一个文件；**刷新**它才要 Python，而那是 `/job-dashboard`
        的事。这条钉住的是「别在 apply.md 里写 `python tools/...`」——
        实测这么写过一次，`test_python_dependency_is_stated_honestly` 当场红。
        """
        doc = APPLY.read_text(encoding="utf-8")
        self.assertNotRegex(doc, r"python\s+tools/",
                            "apply.md 里出现了 python 命令 —— "
                            "没装 Python 的人就用不了 /job-apply 了")

    def test_the_fallback_keeps_the_same_semantics(self):
        """没有快照时的兜底，四条语义一条都不能少。"""
        seg = batch_section()
        for w in ("跳过", "不建议", "skipped", "已有目录"):
            self.assertIn(w, seg, f"兜底口径没排除「{w}」那一类")
        self.assertIn("公司不同就不要合并", seg,
                      "兜底没说清跨公司不许合并 —— 同一份 JD 模板会被不同雇主复用")

    def test_a_disappointing_verdict_is_not_a_stop_condition(self):
        """「连续 N 个没过闸门」不许再作为中止批量的理由。

        没过闸门的岗**照样是产出**：落了评估、深评结论写回了库、从待评堆里出去了。
        把它当失败中止，等于用户要了 20 个、你给了 13 个。

        实测就是这么用错的：跑到第 13 个时连续 5 个「可以考虑」于是停下，
        而剩下 7 个里恰恰有一个技能分 73（全批最高）、只被薪资压住的岗——
        中途停手把它埋了。用户原话：「apply 让你跑，你就继续，不要因为结论而停止」。

        真正该停的只有「同一个错误连续 2 次」（环境坏了，跑不下去）与「用户喊停」。
        """
        seg = batch_section()
        i = seg.find("停手条件")
        self.assertNotEqual(i, -1, "批量这一节没有停手条件了")
        block = seg[i:]
        self.assertNotRegex(
            block, r"连续\s*\d+\s*个都?没过闸门\s*\*{0,2}\s*——[^\n]*停",
            "「连续 N 个没过闸门就停」又回来了 —— 那是把产出当失败")
        self.assertIn("不是停手条件", block,
                      "没写明「结论不理想不是停手条件」，下次还会照旧中止")
        # 真正的两条要还在
        self.assertIn("同一个错误连续", block, "环境类停手条件不见了")
        self.assertIn("用户喊停", block)

    def test_the_batch_still_writes_the_join_key(self):
        """批量产出必须带「职位链接」——那是材料接回职位列表的唯一键。

        这一节写着 `outreach.md`（**只含开场白 + 缺口/必问**）。「只含」被照字面
        执行，头部三行就一起省了——实测批量跑完 14 个目录全缺这一行，
        库里明明有对应的岗，面板上却全部显示「没有材料」，自检报
        「14 份材料接不回职位列表」。**产出少一行 = 整批不上屏**，
        所以这一节必须自己说清楚，不能只靠 `06` 那份模板里有。
        """
        seg = batch_section()
        self.assertIn("职位链接", seg,
                      "批量这一节没提「职位链接」—— 「只含开场白」会被照字面执行，"
                      "省掉头部，材料就接不回职位列表了")


if __name__ == "__main__":
    unittest.main()
