# -*- coding: utf-8 -*-
"""硬门要按七道正规门名写——而且判词得先解析得出来才谈得上查。

两件事绑在一起，因为它们是同一次实测里连着掉出来的（2026-08-23）：

**一、解析。** 硬门判词有两套写法：粗筛写 `硬门 FAIL (工作年限)`，深评写
`不满足硬性条件（学历）`（全角括号，且前缀不同）。两个消费方各自手写了一遍
解析，两份**各只认半角、只认粗筛那个前缀**：

    面板那张分档表    25 个岗的门名明明写着，全落进「没说是哪道」
    audit_pipeline   40 个深评判死的岗，对下面每一条检查都是隐形的
                     —— 不是查过没问题，是从来没查过

这就是本仓库记了多次的「N 个消费方里漏了一个」。正本现在是
`_cli.gate_in_verdict()`，前缀族用 `GATE_FAIL_PREFIXES`（那也早有正本）。

**二、七道之外的门名。** 解析通了才看得见：19 个岗写在七道之外 ——
技术栈 7、地点 4、英语 4、语言 2、行业经验 1、专业 1。

多数其实是真门、只是名字写错：他资料里写着「跨城市搬迁才是硬门」
「要求英语口语沟通的按硬门处理」，那两类照其余 393 个的写法应当写成
`候选人明确排除（跨城搬迁）`。剩下的技术栈、行业经验**本来就是要打分的两维**
（专业能力、业务领域），提成门等于用「有一项对不上」替掉整套加权。

处置不一样（改名 / 重评 / 该不该加第八道门），所以判「留意」不判「要修」——
本仓库的「要修」都配一个 `--apply` 的机械修法，这条没有，而一个永远红的审计
会被当成背景噪音略过。

对用户那一面则是另一回事：这 19 个是**实打实的挡门理由**，在面板上叫
「其它原因」。它和「没说是哪道」（漏填，量的是数据缺陷）不能并成一档——
并了就等于说这 31 个全是脏数据，而其中 18 个不是。
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import _cli  # noqa: E402
import audit_pipeline as A  # noqa: E402
import export_web_data as X  # noqa: E402


class TheParserHandlesBothWritings(unittest.TestCase):
    def test_full_width_brackets_are_read(self):
        """深评那批写全角。只认半角的话它们整批变成「没说是哪道」。"""
        self.assertEqual(_cli.gate_in_verdict("不满足硬性条件（学历）")[0],
                         "学历与院校")

    def test_both_prefixes_are_read(self):
        """粗筛和深评前缀不同，两套都要认。"""
        for v in ("硬门 FAIL (工作年限)", "硬门FAIL (工作年限)",
                  "不满足硬性条件（年限）"):
            with self.subTest(v=v):
                self.assertEqual(_cli.gate_in_verdict(v)[0], "工作年限")

    def test_the_prefix_family_is_not_re_listed(self):
        """前缀族有正本。再抄一份就等着它们分叉。"""
        src = (ROOT / "tools" / "_cli.py").read_text(encoding="utf-8")
        seg = src[src.index("def gate_in_verdict("):][:1800]
        self.assertIn("GATE_FAIL_PREFIXES", seg, "没用前缀族的正本")

    def test_a_non_verdict_yields_nothing(self):
        """不是硬门判词的，两格都空——不能把「值得投」也拆出个门来。"""
        for v in ("值得投", "", None, "可以考虑（薪资未标）"):
            with self.subTest(v=v):
                self.assertEqual(_cli.gate_in_verdict(v), ("", ""))

    def test_two_gates_on_one_job_count_as_the_first(self):
        """拆开会让合计大于岗数，那一行就不再是「几个岗被挡住」。"""
        self.assertEqual(
            _cli.gate_in_verdict("硬门 FAIL (工作年限 + 学历)")[0], "工作年限")


class BothConsumersUseThatOneParser(unittest.TestCase):
    """两处都手写过一遍，两份各修一半——这条盯着它们别再各写各的。"""

    def test_the_audit_delegates(self):
        src = (ROOT / "tools" / "audit_pipeline.py").read_text(encoding="utf-8")
        seg = src[src.index("def _gate_of_verdict("):][:1200]
        self.assertIn("gate_in_verdict", seg, "审计又自己解析了一遍")
        self.assertNotIn('v.find("(")', seg, "还留着手写的半角切片")

    def test_the_audit_defines_no_parser_of_its_own(self):
        """**上面那条只看 `_gate_of_verdict` 往后 1200 字。**

        实测 2026-08-23：`audit_pipeline` 里另有一份**完整的**
        `gate_in_verdict`，就在 140 行之下 —— 委托改好之后忘了删，
        从此没有调用方，也没人维护。两份逻辑逐字相同，而注释已经飘了：
        `_cli` 那份记着「一条挂两道门的**按第一道算**，拆成两条会让计数
        大于岗数」，副本把这个理由丢了。

        死掉的判据副本比活的更危险：下一个人 grep 到两份，改错一份不会红。
        所以这条不看窗口，看**整个模块**。
        """
        src = (ROOT / "tools" / "audit_pipeline.py").read_text(encoding="utf-8")
        self.assertNotIn("\ndef gate_in_verdict(", src,
                         "审计又长出了自己那份解析器（哪怕没人调）")

    def test_the_shared_one_keeps_the_two_gate_rule(self):
        """那条飘掉的注释就是这一条 —— 它没了，`split(\"+\")` 会被当成手滑删掉。"""
        src = (ROOT / "tools" / "_cli.py").read_text(encoding="utf-8")
        seg = src[src.index("def gate_in_verdict("):][:1400]
        self.assertIn("按第一道算", seg)
        self.assertIn("会让计数大于岗数", seg)

    def test_the_panel_tally_delegates(self):
        src = (ROOT / "tools" / "export_web_data.py").read_text(encoding="utf-8")
        seg = src[src.index("def gate_fail_tally("):][:3600]
        self.assertIn("gate_in_verdict", seg, "面板那张表又自己解析了一遍")
        self.assertNotIn('raw.find("(")', seg, "还留着手写的半角切片")

    def test_the_audit_now_sees_the_deep_eval_batch(self):
        """回归：这一批此前对每条检查都是隐形的。"""
        self.assertEqual(A._gate_of_verdict("不满足硬性条件（学历）"),
                         "学历与院校")


def _tally(*verdicts):
    return {r["gate"]: r["n"] for r in
            X.gate_fail_tally([{"gateFailReason": v} for v in verdicts])}


class WroteSomethingElseIsNotWroteNothing(unittest.TestCase):
    def test_a_non_gate_gets_its_own_bucket(self):
        t = _tally("不满足硬性条件（技术栈）")
        self.assertEqual(t, {"其它原因": 1}, f"没单列：{t}")

    def test_the_panel_label_does_not_accuse(self):
        """台面上的词说的是**对他的意思**，不是内部归类状态。
        「不在七道门里」是框架自己的话，用户没有七道门这个概念。"""
        for name in _tally("不满足硬性条件（技术栈）"):
            self.assertNotIn("七道", name, f"内部词上了台面：{name}")

    def test_a_blank_one_stays_where_it_was(self):
        """漏填门名是另一件事——去查执行时为什么没写，不是回炉重评。"""
        self.assertEqual(_tally("不满足硬性条件"), {"没说是哪道": 1})

    def test_they_are_never_merged(self):
        t = _tally("不满足硬性条件（技术栈）", "不满足硬性条件")
        self.assertEqual(len(t), 2, f"两件事并成了一档：{t}")


class TheAuditNamesTheRuleThatWasBroken(unittest.TestCase):
    """报什么、判几级、给不给命令。"""

    def _run(self, *verdicts):
        seen = {str(i): {"rank_verdict": v, "title": "示例岗位"}
                for i, v in enumerate(verdicts)}
        return A.check_gate_is_one_of_the_seven(seen, {})

    def test_it_fires_on_a_non_gate(self):
        out = self._run("不满足硬性条件（技术栈）")
        self.assertEqual(len(out), 1)

    def test_it_is_a_warning_not_an_error(self):
        """「要修」在这个仓库意味着有机械修法。这条的处置要人判断，
        而 `test_pipeline_audit_stays_clean` 钉死了零 error ——
        判错级别的代价是那条测试从此长红，然后整个审计被当噪音略过。"""
        self.assertEqual(self._run("不满足硬性条件（技术栈）")[0][0], "warn")

    def test_it_is_quiet_on_the_seven(self):
        self.assertEqual(self._run("硬门 FAIL (学历院校)",
                                   "不满足硬性条件（年限）", "值得投"), [])

    def test_the_note_after_a_reason_does_not_split_the_bucket(self):
        """`地点（跨城搬迁）`和`地点（需迁往郑州）`是同一类。
        分开算的话这一行全是 1，读不出哪一类被当成门用得最多。"""
        msg = self._run("不满足硬性条件 (地点（跨城搬迁）)",
                        "不满足硬性条件 (地点（需迁往郑州）)")[0][2]
        self.assertIn("地点 2", msg, f"同一类被切成两档：{msg}")

    def test_it_says_what_the_cost_is(self):
        """不说这句，读者会以为这只是个拼写不规范的问题。"""
        msg = self._run("不满足硬性条件（技术栈）")[0][2]
        self.assertRegex(msg, r"隐形", "没说清写错名字的真实代价")
        self.assertRegex(msg, r"打分的维度", "没说清技术栈这类不该当门用")

    def test_it_gives_the_command(self):
        """面板与终端每处引导都要写出命令。"""
        self.assertIn("/job-rank --all", self._run("不满足硬性条件（技术栈）")[0][2])

    def test_it_is_registered(self):
        self.assertIn(A.check_gate_is_one_of_the_seven,
                      [fn for _n, fn in A.CHECKS], "写了没挂上去")


if __name__ == "__main__":
    unittest.main()
