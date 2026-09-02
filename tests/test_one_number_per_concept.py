# -*- coding: utf-8 -*-
"""同一个概念只能有一个数。

2026-08-13 全面检查命令逻辑时扫出来的：**「投出去多久没动静算没戏」有三个数**。

    tools/followups.py            10 天  ← 催办按它判
    tools/export_web_data.py      14 天  ← 投后统计的「大概率没戏」（我 8-13 写死的）
    workflows/job-gmail-sync.md   30 天  ← 报表里「N 天没动静的投递」

后果不是「不精确」，是**同一时刻给出互相矛盾的话**：面板催你「这个该催了」，
统计却把它算在「还在等」里，而 gmail 报表两个都不认。

这个仓库为同类问题吃过好几次亏，`SHORTLIST_FLOOR` 的注释里写着
「要改就改这里，别在流程文件里另写一个」——那条教训当时只贴在了那一个常量上。
"""

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))


class QuietDaysHasOneDefinition(unittest.TestCase):

    def test_no_chinese_numeral_ten_days_anywhere(self):
        """**中文数字写死的「十天」躲得过所有查数字的判据。**

        `followups.QUIET_DAYS` 的说明里点名了那句话：「面板的
        『超过十天没动静可以催一次』……都以它为准」——**而它以前不是**：
        面板上有三处写着中文数字「十天」，和常量之间没有任何连接。
        把 `QUIET_DAYS` 改成 14，面板照样说「十天」，
        而且这个仓库为「同一个概念三个数」立的判据一条都拦不住它 ——
        它们查的是 `10`、`14`、`30` 这些**阿拉伯数字**。

        （2026-08-21 通读逐岗「下一步」时发现，同时改了三处。）
        """
        bad = []
        for p in sorted((ROOT / "tools").glob("*.py")):
            body = p.read_text(encoding="utf-8")
            for i, line in enumerate(body.splitlines(), 1):
                st = line.strip()
                if st.startswith("#") or st.startswith("#:"):
                    continue          # 注释里讲这条规则要引用它，放行
                if "十天" in line:
                    bad.append(f"{p.name}:{i}  {st[:60]}")
        self.assertEqual(
            bad, [],
            "中文数字写死的天数（改常量它不会跟着变，查数字的判据也拦不住）：\n  "
            + "\n  ".join(bad))


    def test_the_scan_reaches_the_workflows(self):
        """对照用例：扫描真的够到了文件 —— 否则同文件里那些「没问题」是恒绿的。

        2026-08-20 实测：把 `Path.glob`/`rglob` 打成空之后本文件全绿。
        **扫不到文件时，「没有问题」和「没有检查」长得一模一样。**

        这不是假想——这个仓库真搬过目录（工作流正文从 `.claude/skills/` 搬到
        `workflows/`，`AGENTS.md` 里记着）。glob 还指着旧路径时，守卫会安静地失效。
        """
        found = list((ROOT / "workflows").rglob("*.md"))
        self.assertGreaterEqual(
            len(found), 20,
            f"只扫到 {len(found)} 个工作流 —— 判据大概是够不到文件了，"
            "而不是仓库真的只剩这么几个")

    def test_the_owner_declares_itself(self):
        src = (ROOT / "tools" / "followups.py").read_text(encoding="utf-8")
        self.assertIn("QUIET_DAYS", src)
        self.assertIn("唯一的定义", src,
                      "常量没声明自己是唯一来源，下次还会有人另写一个")

    def test_the_stats_reuse_it(self):
        import followups, export_web_data
        self.assertEqual(export_web_data.SILENT_DAYS, followups.QUIET_DAYS,
                         "投后统计和催办用了两个不同的天数")

    def test_no_workflow_hardcodes_its_own(self):
        """流程文件里不许再写死一个天数。"""
        bad = []
        pat = re.compile(r"(\d+)\s*天[^。\n]{0,14}没(?:有)?(?:任何)?动静")
        for f in (ROOT / "workflows").rglob("*.md"):
            t = f.read_text(encoding="utf-8")
            for i, ln in enumerate(t.splitlines(), 1):
                if ln.lstrip().startswith(">"):
                    continue          # 说明块里讲历史可以提旧数
                m = pat.search(ln)
                if m:
                    bad.append(f"{f.name}:{i} 写死了 {m.group(1)} 天 —— {ln.strip()[:60]}")
        self.assertEqual(bad, [],
                         "流程里另写了天数，会和 followups.QUIET_DAYS 飘：\n  "
                         + "\n  ".join(bad))

    def test_the_detector_can_fail(self):
        pat = re.compile(r"(\d+)\s*天[^。\n]{0,14}没(?:有)?(?:任何)?动静")
        self.assertTrue(pat.search("### 30 天没动静的投递"))
        self.assertFalse(pat.search("阈值取 followups.py 的 QUIET_DAYS"))


class EnoughToKeepGoingHasOneDefinition(unittest.TestCase):
    """「手上够不够投一轮」也只能有一个数——它跨了 Python 和 TS 两边。

        tools/build_dashboard.py  SHORTLIST_FLOOR = 5   面板催补货：少于 5 个就提醒
        web/src/App.tsx           MATERIALS_FLOOR = 5   材料缺口：前 20 里不足 5 份就提示

    Python 那边的注释白纸黑字写着「取 5 的理由与前端 `App.tsx` 的 `MATERIALS_FLOOR`
    同源（那边是同一个 5）」——**而在 2026-08-13 之前没有任何测试钉住它们相等**。
    改一个、另一个不动，用户就会在同一页上遇到两个「够了」的门槛。

    讽刺的是本文件顶上那段文档已经引用了 `SHORTLIST_FLOOR` 的注释当反面教材
    （「要改就改这里，别在流程文件里另写一个」），却没把这个常量本身纳进来。
    **引用一条教训，不等于执行它。**
    """

    def _ts_const(self, name: str) -> int:
        src = (ROOT / "web" / "src" / "App.tsx").read_text(encoding="utf-8")
        m = re.search(rf"const {name}\s*=\s*(\d+)", src)
        self.assertIsNotNone(m, f"前端的 {name} 找不到了")
        return int(m.group(1))

    def test_both_sides_use_the_same_number(self):
        import build_dashboard as bd
        self.assertEqual(
            self._ts_const("MATERIALS_FLOOR"), bd.SHORTLIST_FLOOR,
            "面板催补货的门槛和材料缺口提示的门槛不是同一个数了——"
            "它们描述的是同一件事：手上够不够投一轮")

    def test_the_owner_points_at_the_other_side(self):
        """两边都要写明对方在哪，否则改的人根本不知道还有一处。"""
        src = (ROOT / "tools" / "build_dashboard.py").read_text(encoding="utf-8")
        self.assertIn("MATERIALS_FLOOR", src,
                      "Python 侧没提到前端那份，改的人不会知道要同步")
        app = (ROOT / "web" / "src" / "App.tsx").read_text(encoding="utf-8")
        self.assertIn("SHORTLIST_FLOOR", app,
                      "前端侧没提到 Python 那份，改的人不会知道要同步")


class TheWhitelistMatchesBothWays(unittest.TestCase):
    """判词白名单跨 Python/TS 两份，**两个方向都要比**。

    原来只验「Python 的每个词都在 TS 列表里」。反向没查——TS 那边多出一个词，
    后果正是白名单最想避免的那件事：**多放行一个岗到最显眼的表里**，
    而且是静默的。白名单的全部价值就在「不认识就不进」，多一个就破功。
    """

    def _ts_list(self):
        app = (ROOT / "web" / "src" / "App.tsx").read_text(encoding="utf-8")
        m = re.search(r"const SELLABLE = \[(.+?)\];", app, re.S)
        self.assertIsNotNone(m, "前端的 SELLABLE 找不到了")
        return set(re.findall(r'"([^"]+)"', m.group(1)))

    def test_neither_side_has_an_extra_verdict(self):
        import export_web_data as ex
        self.assertEqual(self._ts_list(), set(ex.SELLABLE_VERDICTS),
                         "两边的可投白名单不一致——行集会不一样")


if __name__ == "__main__":
    unittest.main()


# 「台账里的每个状态都要能说成中文」原来是这里的一个类
# （`EveryStatusSaysSomethingHuman`，2026-08-13 从「状态机有 4 个状态
# 面板进不去」顺出来的）。2026-08-31 并进 `test_every_status_can_be_said`
# —— 那一份的状态是从四个源头汇的（按钮表、终结态表、`/job-outcome`
# 正文、真实投递记录），这一份只汇两个，而**两份守卫会各自长出对方
# 没有的一条**，正是本文件开头那条规矩说的事。


class WeightIsHonestlyDeclared(unittest.TestCase):
    """`Dimension.weight` 多半是 0，类型注释不许承诺「四维相加为 100」。

    2026-08-20 拿真实导出验：2632 个岗里 **180 个的四维权重之和是 0**——
    `parse_dims` 按表头找「权重」列，而 238 张评分明细表里 180 张没有那一列。

    这不是 bug（面板从不渲染权重，`sample.ts` 之外没有任何消费者），
    但**注释写着「四维相加为 100」就是假承诺**：照它写消费代码的人会拿到 0，
    而且不会有任何守卫拦住他。要么有人读，要么说清没人读——两者之间的
    「像是有人读」最危险。
    """

    def test_type_comment_does_not_promise_a_sum(self):
        t = (ROOT / "web" / "src" / "types.ts").read_text(encoding="utf-8")
        seg = t.split("weight: number;")[0][-900:]
        self.assertNotIn("四维相加为 100 */", seg, "又写回「相加为 100」那句假承诺了")
        self.assertIn("实际取值多半是 0", seg, "没说清它多半是 0")
        self.assertIn("面板不渲染", seg, "没说清没有消费者")

    def test_no_component_reads_weight(self):
        """一旦有组件开始读它，上面那条注释就得跟着改——这里盯住这个前提。"""
        import re
        hits = []
        for p in (ROOT / "web" / "src").rglob("*.tsx"):
            for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
                if re.search(r"\bweight\b", line) and "fontWeight" not in line:
                    hits.append(f"{p.name}:{i}")
        self.assertEqual(hits, [],
                         "有组件开始读 weight 了，而它真实取值多半是 0——"
                         f"要么让导出真的填它，要么别读：{hits}")
