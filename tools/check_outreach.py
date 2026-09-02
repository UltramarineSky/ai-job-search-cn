#!/usr/bin/env python3
"""落盘前查一份话术：开场白与另外几个渠道踩没踩规则。

    python tools/check_outreach.py <outreach.md>       # 查一份
    python tools/check_outreach.py --stdin             # 从标准输入读开场白
    python tools/check_outreach.py                     # 活动用户的全部话术
    python tools/check_outreach.py --user <名字>        # 换个人的
    python tools/check_outreach.py --dir <目录>         # 指定目录

命中就以退出码 1 结束，并逐条印出踩了什么、原话是哪一句。

## 为什么要有这个东西

`_cli.greeting_hits` 这套判据 2026-08 就在了，可它此前只有**三个事后**的消费方：
面板（用户按「复制开场白」那一下）、`audit_pipeline`（全库扫一遍）、
`trim_opening`（事后机械修补两类）。**生成的那一刻一个都没有。**

代价在 2026-09-02 一天里付了两次：

- 上午按新规则查存量，308 份里 **129 份**踩线。那些文件都带着自检小节、
  逐条打着勾，其中一份原话是「无 JD 原文照抄（引用那半句是刻意的，且加了引号）✓」
  —— **写手自己把规则说服掉了，还给它记了个合格。**
- 下午发现新加的两条正则写窄了，又漏 **24 份**；而那 24 份同样是自检打过勾的。

结论不是「自检没用」，是**自检不是闸门**：它逼写手把判据说出来（说出来的东西
可以被反驳），但拦不住他给自己开例外。`06-outreach-templates.md`「结尾怎么收」
那节末尾记的就是这一课。

所以这个工具只干一件事：**把已有的判据搬到写盘之前**，让 `/job-apply`
第 6 步那道闸门（原来只扫占位符）也能扫话术规则。判据一个字都不新写 ——
新写就又是两套标准了（`_cli.GREETING_BANS` 顶上那段注释记着这个前科）。

## 它查什么，不查什么

- **开场白** → `_cli.greeting_problems`：渠道 1 那五类禁区 + `03` 的风格铁律
  + 200 字上限 + 缺口位置。
- **邮件 / 网申自评 / 求职信 / 内推请托** → `_cli.style_problems`：只有 `03`
  那几条（渠道 1 的五类禁区对它们不适用，`06` 那段 ⚠️ 明说的）。
- **简历正文不查** —— 那一处至今没有机械查，判据见 `_cli.STYLE_BANS` 顶上那段
  （要拿渲染出来的文本当输入）。**说出来，别让「查过了」被读成「全查过了」。**
"""

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import _cli  # noqa: E402
import audit_pipeline as _ap  # noqa: E402

#: 各渠道用哪个检查器。**开场白和别的渠道不是一套判据**，见模块 docstring。
SECTIONS = (("打招呼", _cli.greeting_problems),
            ("邮件", _cli.style_problems),
            ("网申自评", _cli.style_problems),
            ("求职信", _cli.style_problems),
            ("内推请托", _cli.style_problems))


def _raw_section(text: str, keyword: str) -> str:
    """没剥过的那一节 —— 只用来判「剥完还剩多少」，不拿去查规则。"""
    lines = text.splitlines()
    start = next((i for i, ln in enumerate(lines)
                  if ln.startswith("#") and keyword in ln), None)
    if start is None:
        return ""
    out = []
    for ln in lines[start + 1:]:
        if ln.startswith("#"):
            break
        out.append(ln)
    return "\n".join(out).strip()


def _dense(s: str) -> int:
    return len(re.sub(r"\s", "", s or ""))


#: 剥完只剩不到这个比例 → 这一节其实没被查。
#: 判据不取 0：`_strip_wordcount` 正常也会剥掉字数行、`**正文**` 标签这些，
#: 剩九成是常态；剩不到三成就只有一种可能 —— 整段正文本身被当成标记剥掉了。
_VACUOUS_RATIO = 0.3


def problems_in(text: str) -> list:
    """一份 `outreach.md` 里所有踩线的 `(小节, 那句话)`。

    ## 扫了个空不许印 ✓

    `_named_section` 走 `_strip_wordcount`，它会剥掉整段 `> 引用块` ——
    那层兜底是为「照模板抄的人把引用符号一起粘给 HR」准备的。而 `06` 的
    「产出格式」明文规定话术小节里**不许**写成 `> 引用块`：一旦写成了，
    剥完什么都不剩，**检查器查的是空字符串，印出来是一个 ✓**。

    实测 2026-09-02：全库 1 节这样（一份邮件正文整段用 `>` 写的），
    而那一节里真躺着一处「拿年头自证」。**这是第三次栽在「0 和坏了长得一样」上**
    （前两次：新加的正则写窄了漏 24 份；控制组语料清干净后恒为空）。
    所以这里宁可报出来：它同时是一条格式违规，改了两头都好。
    """
    out = []
    for keyword, checker in SECTIONS:
        raw = _raw_section(text, keyword)
        body = _ap._named_section(text, keyword)
        if _dense(raw) >= 30 and _dense(body) < _dense(raw) * _VACUOUS_RATIO:
            out.append((keyword,
                        f"这一节剥完只剩 {_dense(body)}/{_dense(raw)} 字 —— "
                        f"正文多半整段写成了 `> 引用块`，检查器扫了个空。"
                        f"`06-outreach-templates.md`「产出格式」明文不许这么写"
                        f"（引用符号会跟着粘给对方）：去掉每行行首的 `> ` 再跑一次"))
            continue
        if body:
            out += [(keyword, p) for p in checker(body)]
    return out


def _report(label: str, probs: list) -> None:
    print(f"✗ {label}")
    for section, p in probs:
        print(f"    [{section}] {p}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__.splitlines()[0],
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("path", nargs="*", help="要查的 outreach.md")
    ap.add_argument("--dir", default="", help="查这个目录下所有 outreach.md")
    ap.add_argument("--stdin", action="store_true",
                    help="从标准输入读一段开场白（还没落盘时用这条）")
    # 它碰的是每用户数据，所以照仓库另外八个工具的约定收 `--user`
    # （`tests/test_cli_contract.py` 的原话：「肌肉记忆会直接把它喂进来」）。
    ap.add_argument("--user", default="", help=_cli.HELP_USER)
    a = ap.parse_args(argv)

    bad = 0
    if a.stdin:
        text = sys.stdin.read()
        probs = [("打招呼", p) for p in _cli.greeting_problems(text)]
        if probs:
            _report("（标准输入）", probs)
            bad += 1
        else:
            print("✓ （标准输入）")

    files = [Path(p) for p in a.path]
    if a.dir:
        files += sorted(Path(a.dir).glob("*/outreach.md"))
    # 什么都没给（也没走 --stdin）→ 查活动用户的全部话术。
    # **`--user` 只在这条路上有意义**：显式给了文件就按文件走，别偷偷改成别人的。
    if not files and not a.stdin:
        user = _cli.pick_user(a.user or "", root=ROOT)
        files = sorted((ROOT / "users" / user / "documents" / "applications")
                       .glob("*/outreach.md"))
        print(f"用户：{user} · {len(files)} 份话术")
    for f in files:
        if not f.is_file():
            print(f"✗ {f}：找不到这个文件")
            bad += 1
            continue
        probs = problems_in(f.read_text(encoding="utf-8", errors="replace"))
        if probs:
            _report(str(f), probs)
            bad += 1
        else:
            print(f"✓ {f}")

    if bad:
        # **说清楚下一步该敲什么**（`AGENTS.md`「每一处引导都要写出该敲的命令」）。
        # 走 `--stdin` 时 `files` 是空的 —— 直接拼上去会印出一条尾巴空着的
        # 命令，那正是那条规则要防的东西（指了个方向，没给能敲的东西）。
        again = (" ".join(str(f) for f in files) if files
                 else "--stdin   # 把改完的那段话再喂一次")
        print(f"\n{bad} 份踩线 —— 改完再跑一次这条：")
        print("  python tools/check_outreach.py " + again)
        print("判据见 workflows/reference/06-outreach-templates.md（渠道 1 那五类）"
              "与 03-writing-style.md（AI 味清单、句式）")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(_cli.run_cli(main))
