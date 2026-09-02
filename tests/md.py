"""Markdown 围栏的规范走法 —— 测试侧共用。

## 为什么规范实现在 tests/ 而不在 tools/

`tools/lint_skills.py` 里已经有一份写对了的 `_strip_code`（按 CommonMark 规则匹配围栏，
docstring 还记录了两版被丢弃的朴素实现）。照理该抽成共用件让两边都 import——
**但那条路走不通**：`lint_skills.py` 会被 `tests/` 单独拷进临时目录跑，
`CopyableToolsStayStandalone::test_no_intra_repo_imports` 明令它不许 import 仓库里的
任何模块（拷过去的只有脚本本身，import 会 `ImportError`，而错误信息跟真因隔着好几层）。

所以只能留两份。留两份就必须钉住它们不走样——`test_markdown_fences.py` 拿同一批
刁钻输入喂两边，输出必须一致。**重复本身不是问题，无人察觉的分叉才是。**

## 围栏规则（与 lint_skills 同源）

- 开头围栏是 ≥3 个反引号的游程，其后可跟 info string（如 ```bash）
- **只有游程不短于开头、且该行除反引号外无其它内容**的行才闭合它
- 未闭合的围栏一直延伸到文件末尾

数 ``` 的个数是错的：一个 ```` 包裹、内含单行 ``` 的合法片段会数出奇数个。
"""

import re

INLINE_CODE = re.compile(r"`[^`\n]*`")


def _fence_run(line: str) -> int:
    """行首（允许缩进）连续反引号的个数；不足 3 个返回 0。"""
    s = line.lstrip()
    run = len(s) - len(s.lstrip("`"))
    return run if run >= 3 else 0


def fenced_lines(text: str):
    """产出 `(行号, 行, info)`：**所有**围栏块里的行，不看 info string 是什么。

    `info` 是开头围栏的 info string（`bash` / `powershell` / 空串…），调用方要筛
    自己筛——但默认必须是「全都给」。按 info 过滤是这个仓库栽过的坑：
    某条守卫只认 `bash`/`sh`/`powershell`，于是 SETUP.md 里 7 个裸 ``` 块
    （恰恰是它的复制粘贴块）一行都没被检查过。
    """
    opener, info = None, ""
    for i, line in enumerate(text.splitlines(), 1):
        run = _fence_run(line)
        if opener is None:
            if run:
                opener = run
                info = line.lstrip()[run:].strip()
            continue
        if run >= opener and not line.lstrip()[run:].strip():
            opener = None                     # 合法闭合
            continue
        yield i, line, info


def strip_code(text: str) -> str:
    """剥掉围栏块与行内代码，只留散文。

    与 `tools/lint_skills.py::_strip_code` **必须逐字节一致**（有差分测试盯着）。
    """
    keep, opener = [], None
    for line in text.splitlines():
        run = _fence_run(line)
        if opener is None:
            if run:
                opener = run
            else:
                keep.append(line)
        elif run >= opener and not line.lstrip()[run:].strip():
            opener = None
    return INLINE_CODE.sub("", "\n".join(keep))
