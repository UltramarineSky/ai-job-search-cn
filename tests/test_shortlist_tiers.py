"""「可以投的岗位」按判词切一刀：值得投以上默认展开，可以考虑收起来。

## 为什么切

工具**已经知道**这些岗分三档——实测一份真实数据：强匹配 1 · 值得投 22 ·
可以考虑 31。而页面把三档摊平成一个数「可以投的岗位 54」，新用户读到的是
「有 54 个要看」，于是往下滚 4391px（占全页 85%）。

它告诉了你先投哪个，**却没告诉你什么时候可以停。**

这一页别处都很克制：不投的岗位折叠、命令表折叠、简历块没内容就不渲染。
唯独最长的那张表没有停止点。切完整页 5195px → 2903px。

## 三条边界，坏了都不显眼

1. **判词带「粗筛：」前缀。** 实测 34 个「可以考虑」**全部**写作
   `粗筛：可以考虑`。切分写成 `j.verdict === "可以考虑"` 会一行都匹配不到，
   于是切分静默失效——**页面看起来跟没改一样**，最难发现的那种坏法。
2. **没有「值得投」以上的岗时不能切。** 那时主表会空着、内容全躲进折叠里，
   而主表的空状态说的是「还没有职位可以看——下一步是去找岗」，那是错的：
   岗有的是，只是都在「可以考虑」这一档。
3. **空的折叠不渲染。** 标题写着「还有 N 个」，点开却是空的。
"""

import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

APP = ROOT / "web" / "src" / "App.tsx"
SHORTLIST = ROOT / "web" / "src" / "components" / "Shortlist.tsx"
DATA = ROOT / "web" / "public" / "data.json"

MAYBE = "可以考虑"


def app_code() -> str:
    """App.tsx，剥掉注释——注释里引用要拦的写法是常事，不剥就会验到自己的说明。"""
    s = APP.read_text(encoding="utf-8")
    s = re.sub(r"\{/\*.*?\*/\}", "", s, flags=re.S)
    s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
    return re.sub(r"^\s*//.*$", "", s, flags=re.M)


class TheVerdictInTheDataCarriesAPrefix(unittest.TestCase):
    """这条不是在验界面，是在**证明上面那条边界真的存在**。"""

    def test_rank_writes_the_prefix(self):
        """`/job-rank` 的粗筛判词带前缀——所以任何判词比较都必须先剥。"""
        src = (ROOT / "tools" / "build_dashboard.py").read_text(encoding="utf-8")
        src += (ROOT / "tools" / "export_web_data.py").read_text(encoding="utf-8")
        self.assertIn("粗筛", src,
                      "粗筛前缀没了？那这一整条边界要重新想")

    def test_real_data_confirms_it(self):
        if not DATA.is_file():
            self.skipTest("这个 clone 里还没导出数据")
        jobs = json.loads(DATA.read_text(encoding="utf-8")).get("jobs", [])
        maybes = [j for j in jobs if MAYBE in (j.get("verdict") or "")]
        if not maybes:
            self.skipTest("这份数据里没有「可以考虑」的岗")
        exact = [j for j in maybes if (j.get("verdict") or "").strip() == MAYBE]
        self.assertLess(
            len(exact), len(maybes),
            "这份数据里的「可以考虑」全是不带前缀的裸值——那下面那条"
            "「必须过 plainVerdict」就暂时验不出真伪了，换一份带粗筛结果的数据再看")


class TheCutGoesThroughPlainVerdict(unittest.TestCase):

    def test_the_split_strips_the_prefix_first(self):
        code = app_code()
        m = re.search(rf"const maybeOnly = \(j: Job\) =>\s*(.+?);", code, re.S)
        self.assertIsNotNone(m, "找不到切分判断 maybeOnly")
        expr = m.group(1)
        self.assertIn("plainVerdict", expr,
                      f"切分没过 plainVerdict：{expr.strip()!r} —— 真实判词写作"
                      "「粗筛：可以考虑」，裸比一行都匹配不到，切分会**静默失效**")
        self.assertIn(MAYBE, expr)


class NoCutWhenThereIsNothingAboveTheLine(unittest.TestCase):
    """主表空着、内容全躲进折叠里，而空状态还在说「还没有职位可以看」。

    这里只能验结构：`web/` 没有 JS 测试框架（见 `test_web_copy.py` 开头）。
    验的是「主表既引用了切出来的那半，也留了整份名单当兜底」——
    两个引用少任何一个，这条边界就没了。
    """

    def test_main_list_falls_back_to_the_whole_shortlist(self):
        code = app_code()
        m = re.search(r"const mainList = (.+?);", code, re.S)
        self.assertIsNotNone(m, "找不到 mainList")
        expr = m.group(1)
        self.assertIn("worth", expr, "主表没用切出来的那半")
        # 兜底可以是 `shortlist`，也可以是它屏蔽之后的 `visible`
        # （2026-08-13 加了「不想看什么」，被藏起来的不该因为兜底又冒出来）。
        # 判的是**有没有兜底**，不是兜到哪个变量名上。
        self.assertTrue(("shortlist" in expr) or ("visible" in expr),
                        f"主表没有兜底：{expr.strip()!r} —— 没有「值得投」以上的岗时，"
                        "主表会空着、岗全躲进折叠里，而空状态会说「还没有职位可以看」")

    def test_the_cut_is_conditioned_on_there_being_something_above(self):
        code = app_code()
        m = re.search(r"const cut = (.+?);", code, re.S)
        self.assertIsNotNone(m, "找不到 cut")
        self.assertIn("worth.length", m.group(1),
                      "切不切的条件跟「有没有值得投以上的岗」脱钩了")


class AnEmptyFoldIsNotRendered(unittest.TestCase):
    """标题写着「还有 N 个」，点开是空的——这一页别处（不投的岗位、简历块、
    要装的工具）都已经守住了这条，新加的这块不能破例。"""

    def test_the_maybe_fold_needs_something_in_it(self):
        code = app_code()
        i = code.index('key: "maybe"')
        head = code[:i]
        self.assertRegex(
            head[-400:], r"restList\.length > 0 && \(",
            "「可以考虑」那块没有「有内容才渲染」的判断")

    def test_the_label_says_how_many_and_how_good(self):
        """不点开也要知道这一堆大概什么水平，否则它只是又一个未知的抽屉。"""
        code = app_code()
        i = code.index('key: "maybe"')
        label = code[i:i + 420]
        self.assertIn("restList.length", label, "标题没说有几个")
        self.assertIn("restScores", label, "标题没给分数区间")


if __name__ == "__main__":
    unittest.main()
