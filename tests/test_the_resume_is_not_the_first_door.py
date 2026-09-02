# -*- coding: utf-8 -*-
"""零回音时它让人去审简历，而 93% 的投递里简历还没到对方手上。

`job-apply.md` 那条「简历不是第一道门」写得很清楚：

> **猎聘/BOSS 是先打招呼、对方有兴趣才要简历**

它写在**出材料那一侧**，用来解释「为什么不做定制简历」。而**诊断那一侧**
（自检的「下一步」、面板的同一句）零回音时一律说「回头审一遍简历」——
**同一个仓库，两个相反的模型**。

## 实测（活动用户 2026-08-24）

    已决出结果的投递                76 个
    其中走会话打招呼发出去的        71 个（93%）
    已发出的开场白里踩线的          72/80（90%）
    其中第一行就是铺垫的            68 条

那 68 条第一行长这样：「你好，看到 AI 提效专家这个岗」「您好，我想应聘 AI
高级产品经理」。**在猎聘和 BOSS 的会话列表里，第一行是对方唯一看得见的东西**，
而它的信息量是零。

所以「0 回音」的第一诊断不是简历，是那一行。指向简历不只是次优——它指向的是
**一份对方还没看过的文件**，照它去改是照着错的诊断动刀。

## 什么时候「审简历」仍然是对的

走网申、公共邮箱、校招系统的那批，简历确实一次性提交了。所以这条按**比例**
分流（`CHAT_FIRST_SHARE`），不是无条件把简历那句话删掉——删掉的话，
`test_both_next_steps_agree` 里那条「该指向简历时要指」就成了摆设。
"""
import pathlib
import re
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import build_dashboard as bd  # noqa: E402
import doctor  # noqa: E402

BD = (ROOT / "tools" / "build_dashboard.py").read_text(encoding="utf-8")
DR = (ROOT / "tools" / "doctor.py").read_text(encoding="utf-8")
EX = (ROOT / "tools" / "export_web_data.py").read_text(encoding="utf-8")
APPLY = (ROOT / "workflows" / "job-apply.md").read_text(encoding="utf-8")


def flat(s: str) -> str:
    s = " ".join(re.sub(r"^\s*(?:>|#:?)\s?", "", s, flags=re.M).split())
    return re.sub(r"(?<=[一-鿿，。；：、（）「」])"
                  r" +(?=[一-鿿，。；：、（）「」])", "", s)


BASE = {"applied": 85, "ready": 62, "ready_strong": 4, "interviewing": 0,
        "ranked": 300, "replied": 0, "decided": 76, "applied_months": [],
        "direct_decided": 33, "direct_replied": 0}


def panel(**over):
    c = dict(BASE); c.update(over)
    return bd.next_step(c, True, top_ranked_url="u", n_sellable=9)[0]


def selfcheck(**over):
    st = {"in_repo": True, "user": "u", "gaps": {}, "scraped": 500,
          "ranked": 300, "materials": 60, "offers": 0, **BASE}
    st.update(over)
    return "\n".join(doctor.next_step({"node": True, "web_build": True}, st))


class TheRuleAlreadyExistsUpstream(unittest.TestCase):
    def test_job_apply_says_the_resume_is_not_the_first_door(self):
        """这一整条建立在它上面——它没了，这条就成了我们自己发明的说法。"""
        self.assertIn("简历不是第一道门", APPLY)
        self.assertRegex(flat(APPLY), r"猎聘/BOSS 是先打招呼、对方有兴趣才要简历")










class TheFieldReachesBothConsumers(unittest.TestCase):
    def test_the_export_counts_it(self):
        self.assertIn('"chatDecided": chat[0],', EX)
        self.assertIn('counts["chat_decided"] = ostats.get("chatDecided", 0)', EX)

    def test_it_only_counts_decided_ones(self):
        """还在等的不算 —— 同这一整条流水线对「已决出」的口径。"""
        i = EX.index("chat[0] += 1")
        self.assertIn("if decided and", EX[max(0, i - 200):i])

    def test_the_selfcheck_collects_it_too(self):
        self.assertIn('st["chat_decided"] = n_chat_decided', DR)
        self.assertIn("n_chat_decided += 1", DR)

    def test_the_selfcheck_undercount_is_deliberate(self):
        """两边差 1 是有意的（自检只认写了「职位链接：」那一行的目录）。
        没记下来的话，下一个人会把面板的解析抄一份过去对齐。"""
        i = DR.index("greeted = set()")
        seg = flat(DR[max(0, i - 1400):i])
        self.assertRegex(seg, r"少认一个的方向是安全的")
        self.assertRegex(seg, r"别为了对齐这一个数把面板的解析抄一份过来")


class TheSignalItLeansOnIsReal(unittest.TestCase):
    """现算一遍：这批投递真的大多走的是聊天框。"""

    def _live(self):
        p = ROOT / "web" / "public" / "data.json"
        if not p.is_file():
            self.skipTest("还没导出过面板数据")
        import json
        d = json.loads(p.read_text(encoding="utf-8"))
        o = d.get("outcomeStats") or {}
        if not o.get("buckets"):
            self.skipTest("还没有投递记录")
        return d, o

    def test_most_applications_went_through_a_chat_box(self):
        d, o = self._live()
        bk = {b["k"]: b["n"] for b in o["buckets"]}
        decided = bk.get("约面或更远", 0) + bk.get("被拒", 0) + bk.get("大概率没戏", 0)
        if decided < 10:
            self.skipTest("投递太少，比不出来")
        chat = o.get("chatDecided")
        self.assertIsNotNone(chat, "导出里没有这个字段——链子断在导出这一层")
        self.assertGreater(
            chat, decided * bd.CHAT_FIRST_SHARE,
            f"{chat}/{decided} 走聊天框 —— 这一节的前提不成立了，"
            f"该回头看「审简历」是不是又变成对的建议")

    def test_the_panel_actually_says_it(self):
        """**这一条守的是「别先劝人审简历」，不是「必须出现那句解释」。**

        2026-08-25 这里一度为「先扫收件箱」那一支让过路（那一支后来撤了：
        国内回音不走邮箱）。让路的写法留着没用 —— 零回音只剩一支，
        那句解释就该无条件出现。
        """
        d, _ = self._live()
        txt = ((d.get("nextStep") or {}).get("text") or "")
        cmd = ((d.get("nextStep") or {}).get("command") or "")
        if "一个回音都没有" not in txt:
            self.skipTest("现在不在零回音那一支")
        self.assertNotIn("审一遍简历", txt)
        self.assertNotEqual(cmd, "/job-resume")
        self.assertIn("开场白第一行", txt)


if __name__ == "__main__":
    unittest.main()
