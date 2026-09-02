# -*- coding: utf-8 -*-
"""在线简历刷新：这一天哪几家刷过了，哪几家网页版根本没有这个按钮。

`/job-refresh` 的账本一侧。**页面动作不在这里**——那要浏览器，写在
`workflows/job-refresh.md` 里；这个工具只回答两个问题：

1. 今天还该刷哪几家（刷过的不再刷——平台按「最近活跃」排序，一天刷第二次
   不会再往上顶，只是白跑一趟登录态）；
2. 哪几家**网页版没有刷新入口**——这是 2026-09-01 逐家点过一遍的实测结果，
   不是推测。BOSS 与前程无忧整页搜不到「刷新」二字：前者的排序看在线活跃与
   打招呼、后者把它收进了 APP 与付费的「简历快投」。**对这两家如实说没有，
   不要去点别的按钮凑数**——「同步至在线简历」会改简历内容，
   「自动刷新」是常驻设置且在付费语境里，两者都不是刷新。

零依赖，只用标准库；不写 `seen_jobs.json`，只写
`users/<用户>/job_scraper/` 底下那份刷新台账（`export_web_data` 管着）。
"""
from __future__ import annotations

import argparse
import datetime as _dt
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import _cli  # noqa: E402
import export_web_data as ex  # noqa: E402

#: 网页版有没有「刷新简历」这个按钮。2026-09-01 四家逐个开页面点过。
#: 值是 `(能不能在网页上刷, 点哪里, 怎么算成功)`。**改这张表之前先去页面上看一眼**——
#: 平台改版会让它过期，而过期的「没有」会让人白白少刷两家。
#:
#: **这是唯一一份。** `job-refresh.md` Step 1 原来另画了一张同样的表，
#: 一轮之内两边就对不上了（一边写「四个图标里第二个」、一边写「四个图标里的
#: 「刷新简历」」）。现在工作流让执行者跑这个工具、把印出来的交给用户，
#: 不再自己抄一份。
WEB_REFRESH = {
    "猎聘": (True,
             "https://www.liepin.com/resume/（会跳到 c.liepin.com 个人首页）"
             "→ 右侧四个图标里第二个「刷新简历」",
             "弹窗写「简历刷新成功」"),
    "智联": (True,
             "https://i.zhaopin.com/ → 右上角用户卡片上的「刷新简历」",
             "它不弹提示。去 https://i.zhaopin.com/resume，"
             "右侧「我的在线简历」那一行的日期变成今天才算成功"),
    "BOSS": (False,
             "网页版整页没有「刷新」二字",
             "它的排序看在线活跃与打招呼，不是简历刷新。要刷只能在 APP 里"),
    "前程无忧": (False,
                 "简历中心整页没有「刷新」二字",
                 "网页版把它收进了 APP，以及付费的「简历快投」"),
}


def status(user: str, today: _dt.date | None = None) -> list[dict]:
    """每家一行：今天刷过没有、上次哪天、网页上刷不刷得了。"""
    t = today or _dt.date.today()
    done = ex.resume_refreshed(user)
    out = []
    for name in ex.PORTAL_FACTS:
        web, how, ok = WEB_REFRESH.get(name, (False, "没测过", ""))
        day = done.get(name)
        out.append({
            "渠道": name,
            "网页能刷": web,
            "入口": how,
            "怎么算成功": ok,
            "上次": day,
            "今天刷过": day == t.isoformat(),
            "多久没刷": (t - _dt.date.fromisoformat(day)).days if day else None,
        })
    return out


def todo(user: str, today=None) -> list[str]:
    """今天还该刷的（网页刷得了 + 今天没刷过）。空列表就是这一天已经做完了。"""
    return [r["渠道"] for r in status(user, today)
            if r["网页能刷"] and not r["今天刷过"]]


def todo_app(user: str, today=None) -> list[str]:
    """今天**要他自己开 APP 刷**的（网页刷不了 + 今天没记过）。

    **这一支不能省。** 只报「网页能刷的都刷过了」，读起来就是「今天做完了」，
    而 BOSS 与前程无忧一次都没刷 —— 它们进不了台账，于是也永远进不了
    `doctor.resume_refresh_note`（那条按设计只说「记过、且超过阈值」的家，
    没记过算「没查」不算「没做」）。两条规则各自都对，叠在一起就成了一个
    **谁也不会提醒的盲区**，而这两家恰恰是最容易忘的（要开手机）。
    2026-09-01 本人问「检查签到逻辑」时查出来的。
    """
    return [r["渠道"] for r in status(user, today)
            if not r["网页能刷"] and not r["今天刷过"]]


def _render(rows: list[dict]) -> str:
    lines = []
    for r in rows:
        if not r["网页能刷"]:
            lines.append(f"  —  {r['渠道']}：网页版没有这个按钮。"
                         f"{r['入口']}——{r['怎么算成功']}")
        elif r["今天刷过"]:
            lines.append(f"  ✓ {r['渠道']}：今天刷过了")
        else:
            # **该刷的那一行必须自带入口。** 原来这里只印「几天没刷」，
            # 而入口只写在 `job-refresh.md` 的表里 —— 也就是说读了这行的人
            # 还得再去翻一份文档才知道点哪儿。它同时是那张表存在的唯一理由。
            when = (f"{r['多久没刷']} 天没刷了（上次 {r['上次']}）"
                    if r["上次"] else "还没记过刷新")
            lines.append(f"  ! {r['渠道']}：{when}\n"
                         f"       点哪里：{r['入口']}\n"
                         f"       怎么算成功：{r['怎么算成功']}")
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="在线简历刷新的账本。页面动作见 workflows/job-refresh.md。")
    ap.add_argument("--done", metavar="渠道",
                    help=f"记一笔「今天在这家刷过了」，可选：{'、'.join(ex.PORTAL_FACTS)}")
    ap.add_argument("--undo", metavar="渠道", help="撤销今天那一笔（记错了）")
    ap.add_argument("--todo", action="store_true",
                    help="只打印今天还该刷哪几家（一行一个，没有就什么都不打印）")
    ap.add_argument("--user", help=_cli.HELP_USER)
    a = ap.parse_args(argv)

    # **`pick_user(a.user or "")` 的顺序不能反**：写成 `a.user or pick_user("")`
    # 时，一个不存在的用户名会直接穿过去，工具照常往下跑、报 0 份 ——
    # 「查无此人」和「这个人还没开始」就长得一模一样了（`test_cli_contract` 盯着）。
    try:
        user = _cli.pick_user(a.user or "", root=ROOT)
    except SystemExit:
        raise
    except Exception as exc:
        print(exc)
        return 2
    if not user:
        return 2

    if a.done or a.undo:
        name = a.done or a.undo
        r = ex.set_resume_refreshed(user, name, day="" if a.undo else None)
        if not r.get("ok"):
            print(r.get("error"))
            return 1
        print(f"记下了：{name} —— {'撤销' if a.undo else r['day']} 刷过在线简历")
        return 0

    rows = status(user)
    if a.todo:
        for n in todo(user):
            print(n)
        return 0

    print(f"在线简历刷新（用户：{user}）")
    print(_render(rows))
    left, app = todo(user), todo_app(user)
    if left:
        names = "、".join(left)
        print(f"\n下一步：去刷 {names} —— 页面上点哪里见 "
              "`workflows/job-refresh.md`，刷完回来跑")
        print(f"    python tools/resume_refresh.py --done {left[0]}")
    else:
        print("\n网页能刷的两家（猎聘、智联）今天都刷过了。")
    if app:
        # 不说这一句，「今天都刷过了」就是半个真话 —— 判据见 `todo_app` 的注解。
        names = "、".join(app)
        print(f"\n⚠ 还有 {names} 今天没刷 —— 网页上刷不了，要开手机 APP。")
        print("  刷完回来记一笔，否则没有任何地方会提醒你它们多久没刷了：")
        print(f"    python tools/resume_refresh.py --done {app[0]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
