# -*- coding: utf-8 -*-
"""每条命令都必须写清「什么都不给时干什么」，而且那件事得是最常用的。

用户 2026-08-12：「所有命令的默认效果是什么。默认效果应该是最常用的」。
查下来 20 条里 9 条正文根本没写裸命令的行为，两条写了但**和它自己的说明相反**：

- `/job-add-template` 说明写「换一套简历 / 求职信模板」，裸命令却直接进
  「登记一套新模板」的访谈——用户想换，工具在收表。默认对着的是命令名
  （`add-`）而不是说明，而用户读的是说明。
- `/job-cv` 压根没定义没给目标时怎么办。

裸命令是**最常被敲的形式**：不知道该给什么参数的时候，人就是先敲一下看看。
没定义就等于每次由模型现场发挥，同一条命令两次跑出两种结果。
"""

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import export_web_data as ex  # noqa: E402

#: 正文里表达「没给参数时」的写法。中英两套都收——`workflows/` 是中英混写的。
DEFAULT_PAT = re.compile(
    r"(Nothing\s*(?:→|->)"
    r"|No\s+argument\s*(?:→|->)"
    r"|[Ww]ithout\s+an\s+argument"
    r"|with\s+no\s+argument"
    r"|Otherwise\s*[:：]"
    r"|无参"
    r"|没给任何(?:参数|目标|输入)"
    r"|什么都不给"
    r"|不带参数"
    r"|不给\s*N\s*就是"
    r"|什么都没有)")

#: 目标本来就唯一、裸命令没有第二种解释的命令。豁免要写理由。
OBVIOUS = {
    "job-setup": "唯一动作就是建档，没有第二种解释",
    "job-dashboard": "唯一动作就是把面板起起来",
    "job-refresh": "不收参数——唯一动作就是把网页刷得了的那几家刷一遍，今天刷过的由 resume_refresh.py 自己挡掉",
    "job-expand": "唯一动作就是扫资料挖经历",
    "job-resume": "唯一动作就是审那份主简历（只有一份）",
    "job-reset": "裸命令进的是确认流程，Step 里逐字写了要问什么",
    "job-scrape": "裸命令抓默认的前 3 个方向并自动评分，Step 0 与 --no-rank 那条已写明",
    # 这条理由原来写「--target 缺省取 SHORTLIST_FLOOR」—— 那是 2026-08-13 之前的
    # 行为，正文当天就改成「不给就是不设目标，跑到挖不动为止」。豁免理由说的是
    # 一件已经不存在的事，而下面那条判据只查理由长度，查不出真假。
    # 2026-09-03 通读时发现；`test_the_auto_exemption_is_still_true` 现在钉着它。
    "job-auto": "裸命令跑完整循环到挖不动为止——--target 不给就是不设目标，正文写明了",
    "job-offer": "裸命令列 offer 状态的岗，Step 0 第 3 条写明了空表怎么办",
}


class EveryCommandSaysWhatBareDoes(unittest.TestCase):

    def setUp(self):
        self.names = [it["name"] for g in ex.parse_commands() for it in g["items"]]
        self.assertGreaterEqual(len(self.names), 15, "索引像是没解析出来")

    def test_bare_behaviour_is_documented(self):
        missing = []
        for n in self.names:
            f = ROOT / "workflows" / f"{n}.md"
            if not f.is_file() or n in OBVIOUS:
                continue
            if not DEFAULT_PAT.search(f.read_text(encoding="utf-8")):
                missing.append(f"{n}：正文没写「什么都不给时干什么」")
        self.assertEqual(missing, [],
                         "裸命令是最常被敲的形式，没定义就每次现场发挥：\n  "
                         + "\n  ".join(missing))

    def test_exemptions_are_justified_and_real(self):
        for n, why in OBVIOUS.items():
            with self.subTest(cmd=n):
                self.assertGreater(len(why), 8, f"{n} 的豁免理由太短")
                self.assertIn(n, self.names, f"{n} 已经不在索引里了，豁免该删")

    def test_add_template_defaults_to_switching_not_registering(self):
        """说明写「换一套」，默认就不能是「登记一套新的」。"""
        t = (ROOT / "workflows" / "job-add-template.md").read_text(encoding="utf-8")
        self.assertIn("没给任何参数", t)
        self.assertIn("换一套，还是加一套新的", t,
                      "裸命令又变回直接进登记访谈了")

    def test_the_auto_exemption_is_still_true(self):
        """豁免理由引的事实要真。

        只查「理由够长、命令还在索引里」拦不住理由过期：`job-auto` 那条曾写着
        「--target 缺省取 SHORTLIST_FLOOR」，而正文 2026-08-13 就改成了不设目标 ——
        一条假理由在绿灯下活了三周。这里钉正文里那句话本身。
        """
        t = (ROOT / "workflows" / "job-auto.md").read_text(encoding="utf-8")
        i = t.index("--target <N>")
        seg = t[i:i + 400]
        self.assertIn("不设目标", seg, "正文里 --target 不给时的行为变了，豁免理由要跟着改")
        self.assertNotIn("SHORTLIST_FLOOR", OBVIOUS["job-auto"],
                         "豁免理由又把 --target 说成缺省取 SHORTLIST_FLOOR 了")

    def test_the_detector_can_actually_fail(self):
        self.assertTrue(DEFAULT_PAT.search("- Nothing → rank all new jobs"))
        self.assertTrue(DEFAULT_PAT.search("- **无参** → 列出所有用户"))
        self.assertTrue(DEFAULT_PAT.search("**没给任何目标** → 先复述那三条"))
        self.assertTrue(DEFAULT_PAT.search("**什么都不给 → 把 new 的岗全部评完**"),
                        "「什么都不给」也是正常中文写法，词表漏了它会误报")
        self.assertFalse(DEFAULT_PAT.search("这条命令会读 profile/candidate.md"),
                         "普通正文被误判成写了默认行为")


if __name__ == "__main__":
    unittest.main()
