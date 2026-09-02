# -*- coding: utf-8 -*-
"""一句话给了命令，命令选的那批得包含这句话指的那批。

2026-08-30 一天之内，同一个形状在面板与自检里撞到**五处**：

    面板「卡住了，等你一句话」  → `/job-apply --top 20`
        卡住的岗按分数不一定在前 20 里（可能是「可以考虑」，也可能排在第 45）
    面板「那批具名直招才有人可找」→ 裸 `/job-apply`
        句子指的是「可以考虑」那一档，而那条命令只取「强匹配 / 值得投」
    自检「说明和分数对不上」    → `/job-apply <名单第一个>`
        名单第一个多半已经投出去了（抽样 5 个：2 已投、1 标了不投）
    自检「深评缺小节」          → 「一次补完 `/job-apply 全部`」
        那条命令当时补不了「建议」—— 补漏表里没有它
    自检的总数行               → 同上

每一处单看都像笔误，五处放一起才看得出是同一个判据没人验：
**命令选的那批，包不包含句子指的那批。**

## 这条守的是其中机械可判的那一半

档位是可判的：裸 `/job-apply` 与 `/job-apply --top N` 按定义只取
「强匹配 / 值得投」（`job-apply.md` 第 0 步那张表），所以**一句提到
「可以考虑」的话不该配这两条**。

「按分数排在第几」「名单第一个还能不能动」那半是数据相关的，机械判不了 ——
那两处由 `test_the_run_cleans_up_after_itself` 和
`test_the_closing_only_says_what_he_can_still_do` 各自钉着。
"""
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "web" / "src"

#: 只取「强匹配 / 值得投」的那两种敲法。判据在 `job-apply.md` 第 0 步：
#: 「主批量只取「强匹配 / 值得投」。想把更弱的档也备好料，用这两个入口。」
TIER_LIMITED = re.compile(r"/job-apply(?:\s+--top[^`<}]*)?\s*$")


def _blocks():
    """(文件, 行号, 命令原文, 命令前 500 字) —— 面板上每一个命令块。"""
    for f in sorted(SRC.rglob("*.tsx")):
        t = f.read_text(encoding="utf-8")
        for m in re.finditer(r"<Cmd>\{?`?([^`<}]{2,90})", t):
            # **先剥注释再取窗口，顺序不能反。** 反过来的话，命令上面那段
            # 解释判据的长注释会把真正上屏的句子挤出窗口 —— 变异实测：
            # 把 `Shortlist` 那处的修复回退成裸 `/job-apply`，通用这条一声不吭
            # （抓到它的是下面那条钉具体位置的）。
            prose = re.sub(r"\{/\*.*?\*/\}", "", t[:m.start()], flags=re.S)
            prose = re.sub(r"//[^\n]*", "", prose)
            yield (f.name, t[:m.start()].count("\n") + 1,
                   m.group(1).strip(), prose[-500:])


class ATierLimitedCommandDoesNotAnswerAWiderSentence(unittest.TestCase):
    def test_no_maybe_tier_sentence_gets_a_strong_only_command(self):
        bad = []
        for name, ln, cmd, before in _blocks():
            if not TIER_LIMITED.match(cmd):
                continue
            # `before` 已经剥过注释了（见 `_blocks`）——只看真正上屏的字。
            if "可以考虑" in before:
                bad.append(f"{name}:{ln} 「{cmd}」")
        self.assertEqual(
            bad, [],
            "这几处的句子指着「可以考虑」那一档，而命令只取「强匹配 / 值得投」"
            "—— 他敲完发现没动，然后连带不信这一整句：\n  " + "\n  ".join(bad))

    def test_the_detector_can_fire(self):
        """对照用例：坏写法真抓得出来，好写法不许误报。"""
        self.assertTrue(TIER_LIMITED.match("/job-apply"))
        self.assertTrue(TIER_LIMITED.match("/job-apply --top 20"))
        self.assertFalse(TIER_LIMITED.match("/job-apply 可以考虑"))
        self.assertFalse(TIER_LIMITED.match("/job-apply 全部"))
        self.assertFalse(TIER_LIMITED.match("/job-apply https://x/y"))

    def test_the_comment_stripping_does_not_hide_a_real_one(self):
        """剥注释是为了不误伤解释判据的那些话，不是给坏写法开后门。"""
        fake = ('<p>下面「可以考虑」那一档里有 3 个</p>')
        self.assertIn("可以考虑",
                      re.sub(r"\{/\*.*?\*/\}", "", fake, flags=re.S))


class TheOnesAlreadyFixedStayFixed(unittest.TestCase):
    """五处里机械判不了的那几处，各自的守卫要还在。"""

    def test_the_blocked_list_names_the_job(self):
        app = (SRC / "App.tsx").read_text(encoding="utf-8")
        i = app.index("有 {blocked.length} 个岗卡住了")
        self.assertIn("/job-apply ${blocked[0].url}", app[i:i + 1800])

    def test_the_referral_line_runs_the_right_tier(self):
        sl = (SRC / "components" / "Shortlist.tsx").read_text(encoding="utf-8")
        i = sl.index("那批才有人可找")
        self.assertIn("/job-apply 可以考虑", sl[i:i + 1400])


if __name__ == "__main__":
    unittest.main()
