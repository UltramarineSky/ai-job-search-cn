#!/usr/bin/env python3
"""谁正在用哪个模板——注册/覆写共享模板前必须先问一句。

## 为什么要它

`templates/cv/`、`templates/cover_letters/` 是**全 clone 共享**的（只有「谁激活了
哪个模板」这个指针才按用户隔离）。于是重名注册就是覆写别人的骨架：他下次跑
`/job-apply` 出来的简历会**静默地变个样**——不报错、不提示，直到他自己看出排版不对。

`add-template.md` 的 Step 2 已经写了告诫（「重名即覆盖别人的骨架…同 clone 的其他
用户可能正激活着它」），但只给了告诫、没给手段：要确认有没有人在用，AI 只能挨个
翻 `users/*/templates/active-*.md`。**散文告诫拦不住**——本仓库在 `--off-track`
上刚栽过同一形状（`rank.md` 写着「要格外克制」，照样误杀了 9 个岗）。

所以把这一问固化：注册前跑一次，有人在用就换个名字。

## 用法

    python tools/template_usage.py                # 列出全部模板与它们的使用者
    python tools/template_usage.py --name 紧凑双列  # 只看某个模板；有人在用则退出码 1

退出码：`--name` 指定的模板**有人正在激活**时返回 1，方便在注册流程里当闸门用。
只读，不写盘。零依赖，只用标准库。
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(ROOT / "tools"))
import _cli  # noqa: E402,F401  import 即把管道输出定到 UTF-8（见 _cli.force_utf8_output）

#: 激活指针文件名 → 模板类型目录
ACTIVE_FILES = {"active-cv.md": "cv", "active-cover-letter.md": "cover_letters"}


def registered() -> dict:
    """`{(类型, 名字): 目录}`，以 TEMPLATE.md 的存在为准（那是清单文件）。"""
    out = {}
    for kind in ACTIVE_FILES.values():
        base = ROOT / "templates" / kind
        if not base.is_dir():
            continue
        for man in sorted(base.glob("*/TEMPLATE.md")):
            out[(kind, man.parent.name)] = man.parent
    return out


def active_template(user_dir: Path, fname: str) -> str | None:
    """读一个用户的激活指针，取出模板名。

    指针是 markdown，写法可能是 `- **模板：** X` 也可能是 `- **Template:** X`；
    再退一步，`templates/<type>/<name>/` 这样的路径行里也带着名字。
    宽进：认不出就返回 None，**不猜**——猜错会把「没人用」说成「有人用」，
    反过来也一样。
    """
    p = user_dir / "templates" / fname
    if not p.is_file():
        return None
    t = p.read_text(encoding="utf-8", errors="replace")
    m = (re.search(r"\*\*(?:模板|Template)[：:]\*\*\s*(\S+)", t)
         or re.search(r"templates/(?:cv|cover_letters)/([^/\s]+)/", t))
    return m.group(1).strip() if m else None


def usage() -> dict:
    """`{(类型, 名字): [用户…]}`。"""
    out: dict = {}
    users = ROOT / "users"
    if not users.is_dir():
        return out
    for u in sorted(d for d in users.iterdir() if d.is_dir()):
        for fname, kind in ACTIVE_FILES.items():
            name = active_template(u, fname)
            if name:
                out.setdefault((kind, name), []).append(u.name)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="谁正在用哪个共享模板。注册/覆写前先跑一次。")
    ap.add_argument("--name", help="只看这个模板；有人正在用则退出码 1")
    ap.add_argument("--type", choices=sorted(set(ACTIVE_FILES.values())),
                    help="限定类型（cv / cover_letters）")
    args = ap.parse_args(argv)

    regs, use = registered(), usage()

    if args.name:
        keys = [k for k in set(regs) | set(use)
                if k[1] == args.name and (not args.type or k[0] == args.type)]
        if not keys:
            print(f"没有叫「{args.name}」的模板 —— 这个名字可以用。")
            return 0
        busy = False
        for k in sorted(keys):
            who = use.get(k, [])
            here = "已注册" if k in regs else "未注册（只有人指向它）"
            print(f"templates/{k[0]}/{k[1]}/  {here}")
            if who:
                busy = True
                print(f"  ⚠ 正在用它的用户：{'、'.join(who)}")
                print("    覆写会让他们下次的产出静默改样 —— 换个名字（如 "
                      f"{k[1]}-v2）")
            else:
                print("  没有用户激活它，覆写不会影响别人")
        return 1 if busy else 0

    # `--type` 单独用时也要生效——原来只在 `--name` 分支过滤，
    # `--type cv` 照样列出 cover_letters，参数被吞还看起来像成功。
    if args.type:
        regs = {k for k in regs if k[0] == args.type}
        use = {k: v for k, v in use.items() if k[0] == args.type}
    if not regs and not use:
        print("还没有注册过自定义模板（跑 /job-add-template 注册）。"
              if not args.type else f"没有 {args.type} 类的自定义模板。")
        return 0
    print(f"共享模板库（{len(regs)} 个已注册）：\n")
    for k in sorted(set(regs) | set(use)):
        who = use.get(k, [])
        tag = "" if k in regs else "   ⚠ 有人指向它但目录不存在"
        print(f"  templates/{k[0]}/{k[1]}/{tag}")
        print(f"    使用者：{'、'.join(who) if who else '（无）'}")
    orphan = [k for k in use if k not in regs]
    if orphan:
        print("\n⚠ 有用户激活了不存在的模板，他们跑 /job-apply 会找不到骨架：")
        for k in orphan:
            print(f"  {k[1]}（{k[0]}）→ {'、'.join(use[k])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
