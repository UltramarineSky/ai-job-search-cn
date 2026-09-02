# -*- coding: utf-8 -*-
"""「一个回音都没有」是**投递记录**的零，不是平台的零。

投递记录只有两个入口喂：他自己在总览页点，和 `/job-gmail-sync` 回写。
而**国内的回音基本不走邮箱** —— `job-gmail-sync.md` 开头就写着「在国内，
面试邀请多数不走邮件」，那张渠道表里 BOSS 是「完全看不见」、猎聘企业直招
「多半看不见」，末尾写着「这条命令不是回音的总入口」。

也就是说：**这个工具一条回音渠道都读不到。** 那个零永远只是台账的零。

实测活动用户 2026-08-25：88 条投递里 `channel` 全空、联系人一个没填、
备注提到邮件/邮箱的 **0 条**；过静默线的 76 个里 71 个是在会话里打的招呼。

## 这条测试是一次撤销的守卫

2026-08-25 这里一度接过一支「先跑 `/job-gmail-sync` 再决定催谁」。判据引的是
那张表里「猎头代招 → 看得见」那一行，**跳过了同一份文档开头那句相反的结论**。
对国内用户那是一条走不通的路，摆在页面最显眼的位置 —— 比它要修的问题更坏。
用户当场纠正：「job-gmail-sync 在中文里基本不用的」。

所以这里钉两件事：**口径要说出来**，而**动作不许再指向那条命令**。
"""
from __future__ import annotations

import importlib
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
bd = importlib.import_module("build_dashboard")

SYNC = (ROOT / "workflows" / "job-gmail-sync.md").read_text(encoding="utf-8")


def counts(**kw) -> dict:
    base = {
        "applied": 88, "ranked": 2200, "decided": 76, "replied": 0,
        "direct_decided": 33, "direct_replied": 0, "chat_decided": 70,
        "viewed_direct": 0, "unviewed_direct": 0,
        "interviewing": 0, "offers": 0, "waiting": 0,
        "applied_months": [8], "stage": "离职", "ready": 55,
        "expired_unsent": 0, "ready_old": 0, "off_supply": None,
    }
    base.update(kw)
    return base


def step(**kw):
    return bd.next_step(counts(**kw), True, [], n_unranked=0, n_sellable=9)






class TheDocumentAlreadySaidSo(unittest.TestCase):
    """**现拿原文来对。** 这次的错不是文档错了，是只读了一行。"""

    def test_the_headline_says_email_is_not_the_main_channel(self):
        """钉的是**渠道表之前**那句开场白，不是全文任意一处。

        变异检验逮到：把开场那句改掉之后，底下那段教训里我自己
        引的一遍照样喂饱了断言。同一个毛病这会话第六次：
        **断言被窗口里别处的同一个词喂饱** —— 而这一次喂它的正是
        我写下的「文档开头写着……」那句引用。
        """
        head = SYNC[:SYNC.index("| 渠道 |")]
        self.assertIn("在国内，面试邀请多数不走邮件", head,
                      "渠道表之前那句开场白没了")

    def test_the_table_says_boss_is_invisible(self):
        rows = [l for l in SYNC.splitlines()
                if l.lstrip().startswith("|") and "BOSS" in l]
        self.assertTrue(rows)
        self.assertTrue(any("看不见" in r for r in rows), rows)

    def test_it_says_it_is_not_the_main_entrance(self):
        self.assertIn("不是「回音的总入口」", SYNC)

    def test_the_misreading_is_on_record(self):
        """把这次怎么读错的记下来 —— 那一行还在，下一个人照样会挑它。"""
        self.assertIn("别拿这张表里某一行去推翻上面那句话", SYNC)
        self.assertRegex(SYNC, r"基本不用")


class NoLeftoverMachinery(unittest.TestCase):
    """撤销要撤干净：那套标记与状态文件的判据不该还留在代码里。"""

    def test_no_inbox_flags_remain(self):
        for f in ("build_dashboard.py", "doctor.py", "export_web_data.py"):
            src = (ROOT / "tools" / f).read_text(encoding="utf-8")
            for name in ("inbox_never_read", "inbox_unreadable", "inbox_path"):
                with self.subTest(f=f, name=name):
                    self.assertNotIn(name, src)

    def test_the_workflow_no_longer_asks_for_a_marker(self):
        i = SYNC.index("## Step 0")
        seg = SYNC[i:SYNC.index("## Step 1", i)]
        self.assertNotIn("unavailable", seg)


if __name__ == "__main__":
    unittest.main()
