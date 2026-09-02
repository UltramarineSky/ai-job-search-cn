#!/usr/bin/env python3
"""把**投过的那些岗**聚到一处：一份可翻的清单，给 `/job-upskill` 当语料。

## 为什么要它

`/job-upskill` 的汇总模式算的是**全部评过分的岗**（几百上千个），
理由写在它正文里，是站得住的：投递记录只有投过的岗，新用户那里往往是空的。

但那回答不了另一个问题：**「我真正投出去的那些岗，合起来在要求什么，
我反复缺的是哪几项。」** 投出去意味着你判断它值得花这份力气 ——
这批语料的信号比「所有评过分的」干净得多，也是「找薄弱点」最直接的入口。

用户 2026-08-21 的原话：「所有已经投了的 jd 应该在一个地方，或随时可以聚合，
我希望可以分析这些 jd，找到自己的薄弱点，或提升点」。

## 机械的归工具，判断的归工作流

**这里只做机械的那一半**：哪些岗算投过的、它们的字段与当时的评分拆解在哪、
JD 正文有没有。**归并成主题、判断缺口该不该补，是 `/job-upskill` 的事** ——
那需要读 JD 正文和候选人资料，不是数数能得出的。

「哪些岗算投过的」**不另写匹配规则**：复用 `archive.collect_applied_keys`，
它用的又是面板同一个 `build_dashboard.match_tracker`。这个仓库为
「同一个岗有多把钥匙」付过五次学费，不再添第六把。

## 用法

    python tools/applied_jds.py              # 只报覆盖情况，不写盘
    python tools/applied_jds.py --apply      # 写清单到 upskill/applied-jds-<日期>.md

零依赖，只用标准库。不加 `--apply` 时只读。
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _cli  # noqa: E402
from archive import collect_applied_keys  # noqa: E402  复用面板同一套匹配
from build_dashboard import load_tracker, match_tracker  # noqa: E402
from gap_split import read_pair  # noqa: E402  回读那两个分只有这一份实现
import jd_store  # noqa: E402  「算不算抓到了正文」的正本
import tracker  # noqa: E402  状态说人话的正本，别另写一张表

ROOT = Path(__file__).resolve().parent.parent


def _dig(e: dict) -> dict:
    """从条目里取出评分拆解 —— 字段缺了就空着，不猜。"""
    b = e.get("rank_breakdown") or {}
    if not isinstance(b, dict):
        return {}
    return b


def _pair(b: dict):
    """回读 `专业能力 N×0.6+业务域 M×0.4` 那两笔。取不到返回 None。

    **直接调 `gap_split.read_pair`。** 这里原来自己写了一个宽容度不同的正则，
    注释还写着「与 `gap_split.read_pair` 同一个来源」—— 那句话当时就是假的：
    同一个来源指的是同一个字段，不是同一份实现。两份实现读同一个字段，
    迟早在某种写法上分道扬镳（2026-08-21 扫重复字面量时发现，
    当时全库 687 条三份实现结果一致 —— 那是运气，不是设计）。
    """
    return read_pair({"rank_breakdown": b})


def gather(user: str) -> dict:
    """投过的岗 + 它们手上有的每一层数据。只读。"""
    sj = ROOT / "users" / user / "job_scraper" / "seen_jobs.json"
    if not sj.is_file():
        return {"user": user, "rows": [], "reason": "还没有职位库"}
    seen = _cli.seen_of(_cli.read_json(sj))
    keys = collect_applied_keys(user, seen)
    # **别叫 `tracker`。** 模块顶上 `import tracker` 是给 `render()` 用的
    # （`tracker.say(...)`），局部同名会把整个函数里的模块名遮住 ——
    # `export_web_data.py:44` 为这个坑专门 `import tracker as tk`，
    # 这个新文件又把它踩了一遍，只是暂时还没人在 `gather()` 里用到模块。
    trows = load_tracker(ROOT / "users" / user / "job_search_tracker.csv")
    details = ROOT / "users" / user / "job_scraper" / "details"

    import export_web_data as ex          # 只为 plain()，别造第二套换词表

    def _has_body(url: str, title: str) -> bool:
        """这个岗的 JD 正文抓到了没有。

        **判据借 `jd_store.has_body`，路径走本模块的 `ROOT`。**
        直接调 `jd_store.load` 会绕到 `jd_store.ROOT` 去——测试把
        `applied_jds.ROOT` / `archive.ROOT` 指到临时目录时，它照样去读
        真实仓库，那正是本文件顶上「两个 ROOT 都要改」那段注释在治的坑。
        文件名规则也不自己写，用 `jd_store.key_for`。
        """
        p = details / f"{jd_store.key_for(url, title)}.json"
        if not p.is_file():
            return False
        try:
            return jd_store.has_body(json.loads(p.read_text(encoding="utf-8")))
        except (ValueError, OSError):
            return False

    rows = []
    for k in sorted(keys):
        e = seen.get(k) or {}
        url = e.get("url") or ""
        title = e.get("title") or ""
        row = match_tracker(
            {"company": e.get("company") or "", "title": title, "url": url},
            url, trows) or {}
        b = _dig(e)
        rows.append({
            "key": k, "url": url, "title": title,
            "company": e.get("company") or "",
            # 缺 JD 时要按渠道分开说「补得回来 / 补不了」—— 猎聘有免登录接口，
            # 浏览器那几家的正文只能在抓取当次取（见 `fetch_details.missing_urls`）。
            # 不带这个字段，那句提示只能笼统地说「都补不了」，而那是错的。
            "portal": e.get("portal") or "",
            "location": e.get("location") or "",
            "salary": e.get("salary") or "",
            "score": e.get("rank_score"),
            # 「粗筛：」是框架内部词，而这份 markdown 用户直接打开、
            # 下游没有任何显示层 —— 剥它的正本在 `export_web_data.bare_verdict`。
            "verdict": ex.bare_verdict(e.get("rank_verdict") or ""),
            "skill": b.get("技能与经验"),
            "pair": _pair(b),
            # 依据是从评估里抄来的，会带「判词」「硬门」这类框架词。
            # `plain()` 是把它们换成人话的**唯一**一处，这里复用它。
            "why": ex.plain((b.get("依据") or "").strip()),
            "applied_on": (row.get("date") or "").strip(),
            "status": (row.get("status") or "").strip(),
            "notes": (row.get("notes") or "").strip(),
            # **「有 JD 正文」的判据走 `jd_store.has_body`，不是「文件在不在」。**
            # 详情库里存得下只有 url + 标题的空壳（列表页就有那两样），
            # `has_body` 的说明写着「只有 URL 和标题不算『抓过』」，门槛是
            # `_cli.JD_MIN_BODY`。用 `is_file()` 会让这份清单的封面数虚高，
            # 而 `/job-upskill --applied` 正是照着那个数决定值不值得去读正文的。
            "jd": _has_body(url, title),
        })
    return {"user": user, "rows": rows, "reason": ""}


def coverage(rows: list) -> dict:
    return {
        "总数": len(rows),
        "有 JD 正文": sum(1 for r in rows if r["jd"]),
        "有评分拆解": sum(1 for r in rows if r["why"] or r["skill"] is not None),
        "有结果（不只是「已投递」）": sum(
            1 for r in rows if r["status"] and r["status"] != "applied"),
    }


def render(user: str, rows: list, today: _dt.date) -> str:
    """清单本体。**逐条列原文，不归并** —— 归并是 `/job-upskill` 的判断。"""
    cov = coverage(rows)
    out = [f"# 投过的岗 · 聚合清单（{user}，{today.isoformat()}）", ""]
    out += [
        "> 这份是**机械聚合**：把投过的岗连同它们当时的评分拆解摆到一处，",
        "> 供 `/job-upskill --applied` 读。**归并成主题、判断缺口该不该补不在这里** ——",
        "> 那要读 JD 正文和你的资料。",
        "",
        "## 这批语料手上有什么",
        "",
        "| 项 | 数 |", "|---|---|",
    ]
    out += [f"| {k} | {v} |" for k, v in cov.items()]
    out += [""]
    if cov["有结果（不只是「已投递」）"] == 0:
        out += [
            "> ⚠️ **没有一条记过结果**（约面 / 挂了 / 没下文）。",
            "> 所以「什么样的岗会回我」这一问**今天答不了** —— 没有结果差异可比。",
            "> 在总览页每个岗那一行点一下就能记，记够几条之后这份清单会自己多一节。",
            "",
        ]
    out += ["## 逐条", ""]
    for i, r in enumerate(rows, 1):
        head = f"### {i}. {r['company']} · {r['title']}"
        out.append(head)
        bits = [x for x in (r["location"], r["salary"]) if x]
        line = " · ".join(bits)
        if line:
            out.append(f"- {line}")
        if r["score"] is not None:
            p = r["pair"]
            extra = f"（专业能力 {p[0]} · 行业经验 {p[1]}）" if p else ""
            out.append(f"- 当时评分：{r['score']} 分 {r['verdict']}{extra}")
        if r["skill"] is not None:
            out.append(f"- 技能与经验：{r['skill']}")
        if r["applied_on"] or r["status"]:
            # 状态码是机器词汇，**这份文件是给人看的** —— 走 `tracker.say`，
            # 别把 `applied` 原样端上去（AGENTS.md「给用户看的措辞」）。
            out.append(f"- 投于 {r['applied_on'] or '未记日期'}"
                       f"，现在是「{tracker.say(r['status'])}」")
        if r["why"]:
            out.append(f"- 当时写下的依据：{r['why']}")
        out.append(f"- JD 正文：{'在详情库里' if r['jd'] else '**没有**（当时没抓到）'}")
        if r["url"]:
            out.append(f"- {r['url']}")
        out.append("")
    return "\n".join(out) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="把投过的岗聚成一份清单，给 /job-upskill 当语料")
    ap.add_argument("--apply", action="store_true",
                    help="写清单到 upskill/applied-jds-<日期>.md（不给就只报覆盖）")
    ap.add_argument("--user", help=_cli.HELP_USER)
    ap.add_argument("--today", help="覆盖今天的日期（测试用，YYYY-MM-DD）")
    args = ap.parse_args(argv)
    # **在任何一条早退之前就验。** 这几个工具都有「只报不写」的那条路，
    # 验证挪到写盘那一步的话，敲错日期的人会先拿到一份看着正常的输出
    # （实测 2026-09-01：`applied_jds --today 不是日期` 退出码 0）。
    _today = _cli.parse_today(args.today)

    _cli.force_utf8_output()
    user = _cli.pick_user(args.user or "", root=ROOT)
    data = gather(user)
    if data["reason"]:
        print(f"{user}：{data['reason']} —— 先跑 /job-scrape 与 /job-rank")
        return 0
    rows = data["rows"]
    if not rows:
        print(f"{user} 还没有投出去的岗 —— 先投几个，"
              "在总览页点「我投了」或跑 /job-outcome 记一笔")
        return 0

    cov = coverage(rows)
    for k, v in cov.items():
        print(f"  {k}：{v}")

    # **缺 JD 正文时要说怎么补。** 这份清单是给 `/job-upskill` 当语料的，
    # 而没有正文的那些在里面只是一行标题 —— 报一个「46/85」然后停住，
    # 读的人不知道那 39 个是补得回来还是本来就没有。
    #
    # 猎聘那批补得回来（免登录接口）；浏览器三家的 JD 只能在抓取当次取，
    # 回头补要重开页面（判据见 `fetch_details.missing_urls`），所以两类要分开说，
    # 别端一条对一半岗位无效的命令出去。
    gap = cov.get("总数", 0) - cov.get("有 JD 正文", 0)
    if gap:
        fixable = sum(1 for r in rows if not r["jd"]
                      and (r.get("portal") or "").startswith("liepin"))
        print(f"\n  {gap} 个没存职位描述 —— 它们在清单里只有一行标题，"
              f"算能力差距时等于不存在。")
        if fixable:
            print(f"  其中 {fixable} 个是猎聘的，补得回来："
                  f"python tools/fetch_details.py --recheck --apply")
        if gap - fixable:
            print(f"  另外 {gap - fixable} 个来自要登录的那几家，"
                  f"只能在下次抓取当次顺手存，回头补不了。")

    if not args.apply:
        print("\n只报覆盖情况。要出清单加 --apply")
        return 0

    today = _today or _dt.date.today()
    out = ROOT / "users" / user / "upskill" / f"applied-jds-{today.isoformat()}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    _cli.atomic_write(out, render(user, rows, today))
    print(f"\n清单已写到 {out.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
