# -*- coding: utf-8 -*-
"""判词只写了「明确排除」四个字的，把理由从依据里提出来补进括注。

    python tools/name_the_exclusion.py            # 只看，不写盘
    python tools/name_the_exclusion.py --apply    # 写回 seen_jobs.json

## 它替执行者做什么

`04-job-evaluation.md` 那一节写得没有余地：**写不出是哪一条，那就不该判 FAIL**。
而实测活动用户 2026-08-30，342 个岗的判词只写了「明确排除」四个字 ——
这道门一共判死 310 个，写清了是哪条的只有 118 个。

**但理由多半没丢，只是没抄进判词。** 同一批里 303 个的「依据」那一格里
写着理由，有的甚至原文就写着「候选人明确排除（行业背景硬要求）」。
所以这不是重判，是**提取**：从依据里认出它命中的是他资料里哪一条排除，
补进判词的括注。

## 它不碰什么

- **认不出的不猜**，如实跳过并报数 —— 括注写错比不写更坏：
  「哪一条排除最贵」那张表会把它算进错的那一档，而那是他决定放宽哪条的依据。
- **有 `evaluation.md` 的不碰。** 那份文件是事实源，而门名与理由是 `writeback`
  从它的硬性条件表推出来的 —— 只改库那一边，下一次 `writeback --apply` 就会
  把光秃秃的那版顶回来。实测 2026-08-30 当场撞上：整链跑一遍收尾，
  2 个岗的「（独立编码）」被顶掉了。这一档要走 `/job-apply <职位链接>` 重出深评。
- **判定一个不改**：FAIL 还是 FAIL，分数不动。变的只是「说清是哪一条」。
- 括注里已经写了理由的（`候选人明确排除（英语口语）`）本来就合格，不进名单。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import _cli  # noqa: E402

#: 他资料里那几条排除 → 在依据里怎么认出来。
#: **按具体到笼统排**，第一个命中的就是它 —— 一条依据常常同时提到好几件事
#: （「行业背景写成硬性要求，另外还要求独立编码」），取最像主因的那个。
#: 判据来自 `candidate.md`「明确排除」与「明确的能力边界」两节（04 把两者同权）。
REASONS = (
    ("行业背景硬要求", r"行业背景.{0,6}硬(性)?要求|行业核心流程|行业背景/行业核心流程"
                       r"|把.{0,10}行业背景.{0,8}写成硬|行业/形态背景硬要求"
                       r"|[一-龥]{2,6}背景硬要求|这一行的核心开发流程写成硬"),
    ("职能是营销/销售", r"职能是营销|营销\s*/\s*市场\s*/\s*销售|拉新|投放|渠道拓展"
                        r"|扛销售|营收指标|BD\s*的岗位"),
    ("跨城市搬迁", r"跨城(市)?搬迁|需要搬迁|base\s*(?!上海)[一-龥]{2,4}"),
    ("英语口语", r"英语面试|口语沟通|英文会议|口语不行|英语.{0,10}日常工作语言"
                 r"|英语可作为工作语言(?!.{0,6}优先)"),
    # 「不写代码」那条边界的各种说法。**「独立开发」不能单列** —— 它也会出现在
    # 「独立开发产品原型」这种他做得到的语境里；要和「编程/语言/代码」同现才算。
    ("独立编码", r"不写代码|独立编码|熟练掌握编程|亲自写代码|手写代码"
                 r"|精通[^。；]{0,20}(语言|Java|Python|C\+\+)"
                 r"|软件工程能力|独立(开发|完成)[^。；]{0,16}(开发|交付|编码|代码)"),
    ("数据标注", r"数据标注|标注规范|标注体系|标注流程"),
    ("工程化评测", r"评测集|badcase\s*回流|自动化评测指标|MOS"),
    ("模型训练", r"\bSFT\b|RLHF|微调|LORA|LoRA|模型训练|训练、优化及部署"),
    ("大小周", r"大小周"),
)

_BARE = re.compile(r"[（(]")


def bare_exclusions(verdict: str) -> bool:
    """判词里有没有一个「光秃秃的明确排除」（没带括注的）。"""
    known, _off = _cli.gates_in_verdict(verdict)
    return any(_cli.gate_of(g) == "候选人明确排除" and not _BARE.search(g)
               for g in known)


def reason_of(basis: str) -> str:
    """依据里说的是哪一条排除。认不出返回空串 —— **不猜**。"""
    t = re.sub(r"\s+", "", basis or "")
    for name, pat in REASONS:
        if re.search(pat, t, re.I):
            return name
    return ""


def rewrite(verdict: str, reason: str) -> str:
    """把判词里那个光秃秃的门名换成带括注的。"""
    def sub(m):
        inner = m.group(1)
        parts = [p.strip() for p in re.split(r"\s*\+\s*", inner)]
        out = []
        for p in parts:
            if _cli.gate_of(p) == "候选人明确排除" and not _BARE.search(p):
                out.append(f"{p}（{reason}）")
            else:
                out.append(p)
        return "(" + " + ".join(out) + ")"
    return re.sub(r"\(([^()]*(?:（[^）]*）[^()]*)*)\)", sub, verdict, count=1)


def plan(user: str) -> tuple[list, dict]:
    p = ROOT / "users" / user / "job_scraper" / "seen_jobs.json"
    seen = _cli.seen_of(json.loads(p.read_text(encoding="utf-8")))
    import build_dashboard as bd
    apps = ROOT / "users" / user / "documents" / "applications"
    docs = {_cli.norm_url(a["url"]) for a in bd.find_applications(apps)
            if a.get("url") and a.get("dir")
            and (apps / a["dir"] / "evaluation.md").is_file()}
    rows, skip = [], {"认不出是哪一条": 0, "依据里没话": 0,
                      "有 evaluation.md（要走 /job-apply）": 0}
    for key, v in seen.items():
        if not isinstance(v, dict):
            continue
        verdict = str(v.get("rank_verdict") or "")
        if not bare_exclusions(verdict):
            continue
        # **存档是事实源。** 门名与理由是 `writeback` 从 evaluation.md 的
        # 硬性条件表推出来的；只改库那一边，下一次 `writeback --apply`
        # 就把光秃秃那版顶回来（2026-08-30 整链实跑当场撞上 2 个）。
        if _cli.norm_url(v.get("url") or "") in docs:
            skip["有 evaluation.md（要走 /job-apply）"] += 1
            continue
        basis = str((v.get("rank_breakdown") or {}).get("依据") or "")
        if len(re.sub(r"\s+", "", basis)) < 20:
            skip["依据里没话"] += 1
            continue
        reason = reason_of(basis)
        if not reason:
            skip["认不出是哪一条"] += 1
            continue
        new = rewrite(verdict, reason)
        if new == verdict:
            continue
        rows.append({"key": key, "entry": v, "reason": reason,
                     "old": verdict, "new": new})
    return rows, skip


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--apply", action="store_true", help=_cli.help_apply())
    ap.add_argument("--user", default="", help=_cli.HELP_USER)
    a = ap.parse_args(argv)
    user = _cli.pick_user(a.user or "", root=ROOT)
    rows, skip = plan(user)
    print(f"结论只写了「明确排除」的，把理由补进括注（用户：{user}）")
    print(f"  要改 {len(rows)} 个；跳过：" +
          "、".join(f"{k} {n}" for k, n in skip.items() if n))
    by = {}
    for r in rows:
        by[r["reason"]] = by.get(r["reason"], 0) + 1
    for k, n in sorted(by.items(), key=lambda kv: -kv[1]):
        print(f"    {k} {n} 个")
    for r in rows[:6]:
        print(f"  {(r['entry'].get('title') or '')[:24]:<26}{r['old'][:26]} → {r['new'][:40]}")
    if len(rows) > 6:
        print(f"  …另有 {len(rows) - 6} 个")
    if not a.apply:
        print(chr(10) + _cli.DRY_RUN_NOTE)
        return 0
    p = ROOT / "users" / user / "job_scraper" / "seen_jobs.json"
    store = json.loads(p.read_text(encoding="utf-8"))
    seen = _cli.seen_of(store)
    for r in rows:
        seen[r["key"]]["rank_verdict"] = r["new"]
    _cli.atomic_write(p, json.dumps(store, ensure_ascii=False, indent=1))
    print(f"\n已写回 {len(rows)} 个")
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli.run_cli(main))
