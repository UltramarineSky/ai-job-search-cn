# -*- coding: utf-8 -*-
"""判词和材料要对得上：值得投的必须有话术，不投的不该留着话术。

2026-08-13 继续检查命令逻辑时做的一遍对账。三种正当形态，别混为一谈：

  ① `posting + evaluation + outreach`  —— 可以投，材料齐
  ② `posting + evaluation`（无话术）    —— 深评过但判定不投，闸门表规定只落评估
  ③ `posting + outreach + 同岗重复挂牌` —— 同一个岗的镜像挂牌，评估在主条目下

**判词要从「结论」里读，不能从全文里搜。** 第一版就栽在这里：
`某大型游戏公司_AI FDE` 的评估是一次「重跑翻案」，正文写着
「上一轮 63 分『值得投』→ 本轮硬性条件没过」——全文搜「值得投」会命中
那句**历史叙述**，把一个正确撤掉话术的目录报成缺陷。

差点按这个误报去给一个硬门没过的岗补开场白。
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def apps_dir():
    ptr = ROOT / ".active_user"
    if not ptr.is_file():
        return None
    u = ptr.read_text(encoding="utf-8").strip()
    d = ROOT / "users" / u / "documents" / "applications"
    return d if d.is_dir() else None


def final_verdict(text: str):
    """只认**结论**，不认正文里提到的历史判词。

    结论的写法有几种：`### 结论：X`、`**判词：X**`、`## 综合 N/100 —— X`。
    都找不到就返回 None——宁可不判，也别拿历史叙述当结论。
    """
    for pat in (r"^#+\s*结论[:：]\s*([^\n（(]{2,10})",
                r"\*\*判词[:：]\s*([^\n*（(]{2,10})",
                r"##\s*综合\s*\d+/100\s*——\s*([^\n（(]{2,10})"):
        m = re.search(pat, text, re.M)
        if m:
            return m.group(1).strip()
    return None


class MaterialsMatchTheVerdict(unittest.TestCase):

    def setUp(self):
        self.apps = apps_dir()
        if not self.apps:
            self.skipTest("这个 clone 里没有真实投递目录")
        self.dirs = [d for d in self.apps.iterdir() if d.is_dir()]
        self.assertGreater(len(self.dirs), 3, "像是扫空了")

    def test_sellable_jobs_have_a_greeting(self):
        """**两类不算缺**：
        · 已经投出去的——话术发完就归档，目录里留不留是历史问题，不是待办；
        · 同岗镜像——评估在主条目下，这里再放一份话术反而会误发第二遍。
        实测这两类占了 6 个，全部是正当形态。

        **「可以考虑」不在必须出话术的档里。** 这条原来把它一起要求了，
        和 `job-apply.md` 的闸门表正面冲突——那张表写着「可以考虑 → **停在这里**，
        只把 `evaluation.md` 落盘，**不出开场白**」，理由也写了：深评说不该投的岗，
        开场白写得再准也没用。同一份文件的小结项还专门列「几个**卡在**『可以考虑』」，
        说明那是**预期形态**不是漏做。实测 2026-08-17 一轮撞出 5 个，全是照闸门表停的。
        要把这一档也出齐是另一条命令（`/job-apply 可以考虑`）的事，
        而目录里看不出是哪条命令产的——看不出就不该按最严的那条判。
        """
        sent, dup = self._applied_and_dup()
        bad = []
        for d in self.dirs:
            ev = d / "evaluation.md"
            if not ev.is_file() or (d / "outreach.md").is_file():
                continue
            if d.name in sent or d.name in dup:
                continue
            v = final_verdict(ev.read_text(encoding="utf-8"))
            if v in ("值得投", "强匹配"):
                bad.append(f"{d.name[:44]} 结论「{v}」却没有 outreach.md")
        self.assertEqual(bad, [],
                         "判词能投却没出话术：\n  " + "\n  ".join(bad))

    def _applied_and_dup(self):
        """哪些目录对应的岗**已经投了 / 是重复挂牌**。

        快照里**没有目录名字段**（第一版猜了个 `materialsDir`，不存在）——
        它按 URL 关联，目录名只活在文件系统里。所以反过来走：
        从目录的 `posting.md` / `outreach.md` 里读「链接」，拿 URL 去快照里查。
        那一行链接是全仓库唯一把材料目录和岗位连起来的键。
        """
        import json
        f = ROOT / "web" / "public" / "data.json"
        if not f.is_file():
            return set(), set()
        d = json.loads(f.read_text(encoding="utf-8"))
        by_url = {(j.get("url") or "").split("#")[0]: j for j in d.get("jobs", [])}
        sent, dup = set(), set()
        for dd in self.dirs:
            url = ""
            for fn in ("outreach.md", "posting.md", "同岗重复挂牌.md"):
                f2 = dd / fn
                if not f2.is_file():
                    continue
                m = re.search(r"(?:职位)?链接\s*[：:]\s*(\S+)",
                              f2.read_text(encoding="utf-8"))
                if m:
                    url = m.group(1).split("#")[0]
                    break
            j = by_url.get(url)
            if not j:
                continue
            if j.get("applied"):
                sent.add(dd.name)
            elif j.get("dupOf"):
                dup.add(dd.name)
        return sent, dup

    def test_every_dir_has_a_posting_snapshot(self):
        """`posting.md` 是快照留档——职位下线后 URL 就失效了，没有它就查不回原文。"""
        bad = [d.name[:44] for d in self.dirs if not (d / "posting.md").is_file()]
        self.assertEqual(bad, [], "缺 posting.md：\n  " + "\n  ".join(bad))

    def test_mirror_dirs_point_at_their_main_entry(self):
        """**镜像目录**（同一个岗的另一处挂牌）必须有指针文件说明材料在谁那儿，
        否则同一个岗会被联系两次。

        判据是**目录里没有 evaluation.md**，不是名字里有没有「同岗」二字：
        `<公司>（两贴同岗）_…` 名字带「同岗」，但它是**主条目**——评估和话术
        都在自己这儿，「两贴同岗」说的是这家公司发了两贴。
        第一版按名字判，把一个主条目报成了缺指针的镜像。
        """
        bad = []
        for d in self.dirs:
            if (d / "evaluation.md").is_file():
                continue                      # 有评估 = 主条目，不是镜像
            if not (d / "outreach.md").is_file():
                continue                      # 连话术也没有 = 只落评估那一档
            if not (d / "同岗重复挂牌.md").is_file():
                bad.append(f"{d.name[:44]} 有话术、没评估、也没指针——它指向谁？")
        self.assertEqual(bad, [],
                         "镜像目录缺指针，同一个岗可能被联系两次：\n  " + "\n  ".join(bad))

    def test_the_verdict_reader_ignores_history(self):
        """变异内建：重跑翻案的那种写法不能被读成旧判词。"""
        flipped = ("## 职位评估\n\n> ⚠️ **重跑翻案：上一轮 63 分「值得投」→ 本轮硬性条件没过。**\n"
                   "\n### 结论：不满足硬性条件\n")
        self.assertEqual(final_verdict(flipped), "不满足硬性条件")
        self.assertEqual(final_verdict("## 综合 70/100 —— 值得投\n"), "值得投")
        self.assertIsNone(final_verdict("这里只是提到了值得投这三个字"))


if __name__ == "__main__":
    unittest.main()
