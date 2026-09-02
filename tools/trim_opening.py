# -*- coding: utf-8 -*-
"""开场白里能**机械删掉**的那两类，删掉。

    python tools/trim_opening.py            # 只看，不写盘
    python tools/trim_opening.py --apply    # 改 outreach.md 里的开场白

两类：

1. **开头那句铺垫**（「看到贵司这个岗」）—— 见下面「为什么」。
2. **抢答到岗时间**（「我目前离职随时到岗」）—— 主动透露的信息，
   删了什么都不丢。它和「先谈钱」不一样：后者（「30-50k 是按几薪算？」）
   **是该问的问题，只是问错了地方**（属于评估里的「投前必问」，
   不属于打招呼），所以这个工具只把它报出来、不删 ——
   实测 2026-08-30 那 3 份里只有 2 份的「投前必问」已经收了同类问题，
   自动删掉会真的丢掉一个他想问的事。

## 为什么

`06-outreach-templates.md` 把「开场铺垫」列进五类禁区，理由写在那儿：
**「看到贵司这个岗」说的是对方已经知道的事** —— JD 是他写的，消息是你发的。
它平均吃掉 15 个字，而这段话一共只有 200 字的预算，会话列表里对方先看到的
也就是这一行。实测活动用户 2026-08-30：280 份开场白里 **71 份**开头是铺垫，
是五类禁区里最大的一类。

## 判据：删完必须更干净，不许更差

删词是在改**他要发出去的字**，比改一个抬头字段风险高。所以不靠「正则删干净了」
自证，而是**拿检查器当验收**：`_cli.greeting_hits` 在改前改后各跑一遍，
新结果必须是旧结果的真子集（少了铺垫，且没多出任何一条）。达不到就整条跳过、
报出来给人看。字数、`您好，` 开头这些也一并复查。

## 它不碰什么

- **铺垫之后不是一个完整句子的**（后面接的是「，」而不是「。」「：」）：
  删了会剩下半句，那种要人重写，工具不动。
- **「我想应聘…」这类整句都是铺垫的**：删完开头就空了，同样跳过。
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import _cli  # noqa: E402
import audit_pipeline as _ap  # noqa: E402

#: 铺垫和正文之间的分隔。**只认句号和冒号** —— 逗号意味着后面那半句
#: 是跟着铺垫走的，删了会剩下半截话。
_SEP = re.compile(r"^[。：:]\s*")

#: 第一句的收尾。整句都是铺垫时按它切。
_SENT_END = re.compile(r"[。！？]")

#: 「整句都是铺垫」允许的最长长度。
#:
#: 实测活动用户 2026-08-31：那 16 份里最长的是「看到贵司招 AI 智能体开发
#: 产品经理。」17 字；
#: 34 字留了一倍余量，再长基本意味着这一句里已经带上了正文
#: （「看到岗位写「不要求编程基础，重点是让 AI 工具真正解…」」那一类）。
_PAD_SENTENCE_MAX = 34

#: 按句切开。中文句末三种收尾都认；分号不算 —— 分号两边常常是一句话的两半。
_SENT = re.compile(r"[^。？！]*[。？！]|[^。？！]+$")

#: 「抢答到岗时间」在句子里长什么样。正本判据是 `_cli.GREETING_BANS`，
#: 这里只是**定位到哪一句**，不重新定义什么算违规。
_WHEN = ("到岗", "入职时间", "可入职")


def drop_when_available(greeting: str) -> tuple[str, str]:
    """删掉「抢答到岗时间」那一整句。删不动返回 `("", 原因)`。

    **整句删，不做句内手术。** 「我目前离职随时到岗，期望 45-60k、16 薪。」
    这种一句里塞了两类违规的，切一半会留下不通的残句；整句删掉之后
    再让检查器验收，干净就收、不干净就整条跳过。
    """
    g = (greeting or "").strip()
    sents = [s for s in _SENT.findall(g) if s.strip()]
    keep = [s for s in sents
            if not (any(w in s for w in _WHEN)
                    and any((h[0] if isinstance(h, (tuple, list)) else str(h))
                            == "抢答到岗时间" for h in _cli.greeting_hits(s)))]
    if len(keep) == len(sents):
        return "", "没有抢答到岗时间那一句"
    out = "".join(keep).strip()
    if len(re.sub(r"\s", "", out)) < 40:
        return "", "删完剩下的太短"
    if "？" not in out and "？" in g:
        return "", "删完就没有问句了 —— 打招呼要留一个问题给对方"
    before = {h[0] if isinstance(h, (tuple, list)) else str(h)
              for h in _cli.greeting_hits(g)}
    after = {h[0] if isinstance(h, (tuple, list)) else str(h)
             for h in _cli.greeting_hits(out)}
    if not after < before:
        return "", f"删完没变干净（{sorted(before)} → {sorted(after)}）"
    return out, "抢答到岗时间"


def trim(greeting: str) -> tuple[str, str]:
    """返回 `(删完的开场白, 删掉的那句)`。删不动返回 `("", 原因)`。"""
    g = (greeting or "").strip()
    m = _cli._GREETING_OPENING.match(g)
    hello = m.group(0) if m else ""
    body = g[len(hello):]
    pad = _cli.opening_padding(g)
    if not pad:
        return "", "开头没有铺垫"
    rest = body[len(pad):]
    ms = _SEP.match(rest)
    if ms:
        rest = rest[ms.end():].lstrip()
    else:
        # **整句就是铺垫时，删整句。**
        #
        # 实测 2026-08-30：23 份「开场铺垫」里 **22 份**后面不是句号或冒号 ——
        # 也就是说匹配到的那一截几乎都不是独立的铺垫句，而是**真句子的开头**。
        # 那 22 份里两类：
        #
        #     我想应聘 + 智能体平台资深产品经理。   ← 整句都是铺垫，该删整句
        #     看到岗   + 位写「不要求编程基础…」    ← 有内容，一个字都不该删
        #
        # 只删掉匹配那一截会把话截成半句 —— `_SEP` 那条判据挡的就是这个，
        # 它是对的。而**整句删掉**之后剩下的正是该占第一行的东西：实测那
        # 16 份删完从「Claude、Cursor、Dify 这些平台我每天…」
        # 「JD 那句「技术是门票…」」起头。
        #
        # 三道闸门保着：这一句要短（`_PAD_SENTENCE_MAX`，长了多半带着正文）、
        # 后面要真有正文、以及下面那道**检查器验收**（新的必须是旧的真子集）。
        e = _SENT_END.search(body)
        if not e:
            return "", "铺垫后面不是句号或冒号，删了会剩半句"
        sent, rest = body[:e.end()], body[e.end():].lstrip()
        if len(sent) > _PAD_SENTENCE_MAX:
            return "", "开头那句太长，多半带着正文，不敢整句删"
        if not rest:
            return "", "删完剩下的太短"
        pad = sent.strip()
    if len(rest) < 20:
        return "", "删完剩下的太短"
    out = (hello or "您好，") + rest
    # ── 拿检查器当验收：新的必须是旧的真子集 ──
    before = {h[0] if isinstance(h, (tuple, list)) else str(h)
              for h in _cli.greeting_hits(g)}
    after = {h[0] if isinstance(h, (tuple, list)) else str(h)
             for h in _cli.greeting_hits(out)}
    if not after < before:
        return "", f"删完没变干净（改前 {sorted(before)} → 改后 {sorted(after)}）"
    if len(re.sub(r"\s", "", out)) > _cli.GREETING_MAX:
        return "", "删完仍然超字数"
    return out, pad


def plan(user: str) -> tuple[list, dict]:
    apps = ROOT / "users" / user / "documents" / "applications"
    rows, skip = [], {}
    for f in sorted(apps.glob("*/outreach.md")):
        text = f.read_text(encoding="utf-8")
        g = _ap._greeting_of(text)
        if not g or not _cli.opening_padding(g):
            continue
        new, note = trim(g)
        if not new:
            skip[note.split("（")[0]] = skip.get(note.split("（")[0], 0) + 1
            continue
        rows.append({"file": f, "dir": f.parent.name, "old": g, "new": new,
                     "pad": note, "text": text.replace(g, new, 1)})

    # ── 第二遍：抢答到岗时间 ──
    done = {r["file"] for r in rows}
    for f in sorted(apps.glob("*/outreach.md")):
        if f in done:
            continue          # 这一轮已经改过，下一轮再看第二类
        text = f.read_text(encoding="utf-8")
        g = _ap._greeting_of(text)
        if not g:
            continue
        new, note = drop_when_available(g)
        if not new:
            if note != "没有抢答到岗时间那一句":
                skip[note.split("（")[0]] = skip.get(note.split("（")[0], 0) + 1
            continue
        rows.append({"file": f, "dir": f.parent.name, "old": g, "new": new,
                     "pad": note, "text": text.replace(g, new, 1)})
    return rows, skip


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--apply", action="store_true", help=_cli.help_apply())
    ap.add_argument("--user", default="", help=_cli.HELP_USER)
    a = ap.parse_args(argv)
    user = _cli.pick_user(a.user or "", root=ROOT)
    rows, skip = plan(user)
    print(f"开场白里能机械删掉的那两类（用户：{user}）")
    print(f"  能删的 {len(rows)} 份" +
          ("；跳过：" + "、".join(f"{k} {n}" for k, n in skip.items()) if skip else ""))
    # 省出多少字按**真的少了多少**算。第一版拿 `r["pad"]` 的长度求和 ——
    # 而第二遍那一支的 `pad` 是标签「抢答到岗时间」，不是删掉的那句话，
    # 于是 5 份报成「省出 30 个字」（6×5），实际省了三倍不止。
    saved = sum(len(re.sub(r"\s", "", r["old"])) - len(re.sub(r"\s", "", r["new"]))
                for r in rows)
    if rows:
        print(f"  省出 {saved} 个字，平均一份 {saved / len(rows):.0f} 个"
              f"（一份的预算是 {_cli.GREETING_MAX} 字）")
    for r in rows[:5]:
        print(f"  [{r['pad'][:22]}]  {r['new'][:56]}…")
    if len(rows) > 5:
        print(f"  …另有 {len(rows) - 5} 份")
    # 「先谈钱」不删 —— 那是该问的问题，只是问错了地方。报出来让人挪。
    money = []
    for f in sorted((ROOT / "users" / user / "documents" / "applications")
                    .glob("*/outreach.md")):
        g = _ap._greeting_of(f.read_text(encoding="utf-8", errors="replace"))
        if g and any((h[0] if isinstance(h, (tuple, list)) else str(h)) == "先谈钱"
                     for h in _cli.greeting_hits(g)):
            money.append(f.parent.name)
    if money:
        print(f"\n另有 {len(money)} 份在打招呼里谈钱 —— 不自动删："
              f"「30-50k 按几薪算」是该问的问题，只是不该问在这里"
              f"（`06` 渠道 1：打招呼里一个字都不提薪资）。"
              f"把它挪进评估的「投前必问」，跑 /job-apply <职位链接> 重出：")
        for d in money[:3]:
            print(f"    {d[:44]}")
        if len(money) > 3:
            print(f"    …另有 {len(money) - 3} 份")

    if not a.apply:
        print(chr(10) + _cli.DRY_RUN_NOTE)
        return 0
    for r in rows:
        _cli.atomic_write(r["file"], r["text"])
    print(f"\n已改 {len(rows)} 份")
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli.run_cli(main))
