# -*- coding: utf-8 -*-
"""收尾那份「要改的」印给人看，卡在 12 条 —— 而排队的是 `/job-auto`。

`--actionable` 收尾会印一段「其中 N 个要改已有内容，这几个一个一个跑」，
后面跟 `_REWRITE_SHOWN = 12` 条命令，再接一句：

> 另有 22 个，改完这批再跑一次自检就会列出来：
>     python tools/audit_pipeline.py --actionable

**那句话是对人说的**，而且对人是对的（`_REWRITE_SHOWN` 上面写着：再多就是
一屏命令，读的人不会一条条敲）。可 `/job-auto` 照它走，一轮只改得动 12 个，
剩下的等下一轮 —— 等于把排队这件事交回给了用户，而这条命令的全部承诺
就是「中途不用你盯着」。实测 2026-09-01：手上 34 个。

所以另开一个不截断的出口 `--rewrite-list`：一行一个链接，给机器排队用。
两份输出**同一个集合**（`_cli.LIVE_REWRITE`），不另立名单。
"""
import contextlib
import io
import pathlib
import sys
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tests"))
import _cli  # noqa: E402
import audit_pipeline as ap  # noqa: E402

#: 比上限多一截，好让「截没截断」看得出来。
MANY = [f"https://x/{i}.html" for i in range(ap._REWRITE_SHOWN + 9)]


def _run_flag(*argv):
    """喂一批「要改」的岗，跑一次 CLI → `(退出码, 打印出来的话)`。

    `run` 换成桩：真跑一遍要读职位库，而这里要钉的是**这个出口印什么**。
    """
    def _stub(user, only="", actionable=False):
        if actionable:                       # 只有这一档才会攒到名单
            for u in MANY:
                _cli.note_live([u], rewrite=True)
        return [("warn", "某检查", "某说明")]

    keep_seen, keep_rw = set(_cli.LIVE_SEEN), dict(_cli.LIVE_REWRITE)
    _cli.LIVE_SEEN.clear()
    _cli.LIVE_REWRITE.clear()
    buf = io.StringIO()
    try:
        with mock.patch.object(ap, "run", _stub), \
                mock.patch.object(ap._cli, "pick_user", lambda *a, **k: "u"), \
                contextlib.redirect_stdout(buf):
            code = ap.main(list(argv))
    finally:
        _cli.LIVE_SEEN.clear()
        _cli.LIVE_SEEN.update(keep_seen)
        _cli.LIVE_REWRITE.clear()
        _cli.LIVE_REWRITE.update(keep_rw)
    return code, buf.getvalue()


class TheMachineReadableListIsWhole(unittest.TestCase):

    def test_it_prints_every_one(self):
        """不截断 —— 这一条就是它存在的理由。"""
        _code, out = _run_flag("--rewrite-list")
        got = [ln for ln in out.splitlines() if ln.strip()]
        self.assertEqual(len(got), len(MANY),
                         f"印了 {len(got)} 条，手上有 {len(MANY)} 条")
        self.assertEqual(got, MANY)

    def test_it_prints_links_not_prose(self):
        """给机器排队的东西里不许混人话 —— 混了就得先解析一遍。"""
        _code, out = _run_flag("--rewrite-list")
        self.assertNotIn("/job-apply", out)
        self.assertNotIn("另有", out)

    def test_it_turns_the_actionable_tier_on_by_itself(self):
        """**不进那一档，`live_tail` 一次都不会被调到，这里恒为空。**

        少了这一下，它是一条永远印零行的命令 —— 而零行读起来就是「没活」。
        """
        _code, out = _run_flag("--rewrite-list")
        self.assertTrue(out.strip(), "这个出口什么也没印 —— 那一档没打开")

    def test_the_human_facing_one_still_stops_at_twelve(self):
        """反向支点：人看的那份不许跟着放开 —— 一屏命令没人一条条敲。"""
        lines = ap.rewrite_commands(MANY)
        cmds = [l for l in lines if "/job-apply" in l]
        self.assertEqual(len(cmds), ap._REWRITE_SHOWN)
        self.assertTrue(any("另有" in l for l in lines), "截断了却不说")


class TheTwoQueuesStayInStep(unittest.TestCase):
    """出材料第 0 步排两队，收尾就得验两队。

    2026-09-01 加第二队（`--rewrite-list`）时**只加了排、没加验** ——
    而收尾对第一队的验收写得很硬（「不是 0 就当场查是哪一种，别留到下一轮」），
    两队一硬一软，软的那队没人会发现它没排空。

    同一次还留下一处自相矛盾：收尾写着「存量照报不改」，而第 0 步每轮都在
    排两队存量、不问。那句话本来只管收尾那一格（收工之后再开一批深评，
    等于把这一轮无限拖下去），读起来却像「存量一概不动」。
    """

    AUTO = (ROOT / "workflows" / "job-auto.md").read_text(encoding="utf-8")

    #: 两队各自的名字。加第三队时这里加一行，下面三条自动跟上。
    QUEUES = ("python tools/stale_materials.py",
              "python tools/audit_pipeline.py --rewrite-list")

    def _phase(self, head: str, until: str) -> str:
        i = self.AUTO.index(head)
        return self.AUTO[i:self.AUTO.index(until, i)]

    def test_both_are_queued_at_the_start(self):
        seg = self._phase("出材料（**无条件**", "收尾（无条件）")
        for q in self.QUEUES:
            with self.subTest(q=q):
                self.assertIn(q, seg, "这一队没进出材料第 0 步")

    def test_both_are_checked_at_the_end(self):
        """**排了不验，等于没排。** 第一队的验收一直在，第二队 2026-09-01 才补。"""
        seg = self._phase("收尾（无条件）", "**收尾那条 `trim_opening.py`")
        for q in self.QUEUES:
            with self.subTest(q=q):
                self.assertIn(q, seg, "这一队收尾没人验，排没排空没人知道")

    def test_a_non_zero_recheck_is_not_just_noted(self):
        """两队的验收都要说清「不是 0 怎么办」，否则那一行只是装饰。"""
        seg = self._phase("收尾（无条件）", "**收尾那条 `trim_opening.py`")
        self.assertGreaterEqual(
            seg.count("不是 0"), len(self.QUEUES),
            "有一队的验收没写「不是 0 就怎样」——那行等于只印个数")

    def test_the_backlog_rule_does_not_read_as_absolute(self):
        """「存量照报不改」只管收尾那一格 —— 说满了就和第 0 步打架。"""
        i = self.AUTO.index("照报不改")
        seg = " ".join(self.AUTO[max(0, i - 40):i + 200].split())
        self.assertIn("这一步", seg,
                      "那句话又说满了，而第 0 步每轮都在排两队存量")


class TheRunnerIsToldToFinishTheList(unittest.TestCase):

    def test_job_auto_takes_both_queues(self):
        md = (ROOT / "workflows" / "job-auto.md").read_text(encoding="utf-8")
        i = md.index("出材料（**无条件**")
        seg = md[i:i + 1800]
        # **要那条敲得出来的命令，不是提一嘴。** 第一版写的是
        # `assertIn("--rewrite-list", seg)` —— 而下面那段 ⚠️ 里也有这个词，
        # 于是把命令行整行删掉它照样绿（变异当场逮到）。
        self.assertIn("python tools/stale_materials.py", seg)
        self.assertIn("python tools/audit_pipeline.py --rewrite-list", seg,
                      "第二份名单没进出材料那一步")

    def test_it_says_not_to_stop_at_the_printed_dozen(self):
        """光给命令不够 —— 收尾那句「改完这批再跑一次」还在屏幕上，
        执行者会照它停手。这里要明说那句是对人说的。
        """
        md = (ROOT / "workflows" / "job-auto.md").read_text(encoding="utf-8")
        i = md.index("--rewrite-list")
        seg = " ".join(md[i:i + 700].split())
        self.assertIn("跑完", seg)
        self.assertIn("不是跑前 12 个", seg)


if __name__ == "__main__":
    unittest.main()
