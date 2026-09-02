# -*- coding: utf-8 -*-
"""扫源码时**只看代码，别看注释**。

## 为什么要有这个文件

有一类检查查的是「某个词还在不在代码里」——「分界线有没有被抄一份」
「有没有又去读那个折过行的字段」「阶段判定里有没有掺进年龄学历」。

而**注释里恰恰要写「为什么不抄」「为什么不读」「为什么不看」**。连着注释一起扫，
等于禁止把理由写下来 —— 而这个仓库的做法正好相反：判据和它的代价都要留在原地。

2026-08-22 一天之内在同一个坑里栽了**七次**（`applied_fit` 的分界线、
`_fit_of` 的搬家、诊断链的旧文案、`ResumeRead` 的文件头 JSDoc、
`job-add-portal` 的摘要表、`candidate_stage` 的「不去猜」那句……）。
每次的修法都一样，每次都是现写一遍。所以收成一处。

## 用法

    from _srcscan import code_of, strip_comments

    code = code_of("tools/export_web_data.py", "def applied_fit(")
    self.assertNotIn("70", code)        # 只看代码，docstring 里可以照常解释
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

#: Python 的 `#`、JS/TS 的 `//` 与 `/* */`、JSX 的 `{/* */}`。
#: **`{/* */}` 要排在 `/* */` 前面**：后者会先吃掉内部，留下一对孤立的花括号。
_COMMENT = re.compile(
    r"\{/\*[\s\S]*?\*/\}"      # JSX
    r"|/\*[\s\S]*?\*/"         # JS 块注释（含 /** JSDoc */）
    r"|^[ \t]*//.*$"           # JS 行注释（整行）
    r"|^[ \t]*#.*$",           # Python 行注释（整行）
    re.M)

#: 三引号 docstring。行内 `#` 与 `//` 不剥 —— 它们可能是字符串的一部分
#: （URL 里的 `//`、markdown 里的 `#`），剥了会改变代码本身的含义。
_DOCSTRING = re.compile(r'"""[\s\S]*?"""' r"|'''[\s\S]*?'''")


def strip_comments(text: str) -> str:
    """剥掉注释与 docstring，留下代码。"""
    return _DOCSTRING.sub("", _COMMENT.sub("", text))


def code_of(rel: str, *anchors: str) -> str:
    """取若干个函数/块的**代码**部分（剥掉注释与 docstring）。

    `anchors` 是每一段的起点（例 `"def applied_fit("`）；每段取到下一个
    顶层 `def ` 为止。**给多个 anchor** 是为了应对代码搬家：判据搬进了新函数时，
    两个都扫 —— 只盯一个的话，代码一搬这条检查就静默失效
    （2026-08-22 实测栽过一次）。

    **一个 anchor 都不给是错用，这里直接抛。** 原来那种写法返回空串，于是
    `assertNotIn("st_mtime", code_of(path))` 之类**永远绿**——查的是空字符串。
    实测 2026-08-23 一次扫出 4 处这么写的（`test_a_second_resume_is_not_invisible`
    那条从 08-23 起就一直在空转）。想整份文件只剥注释，用 `strip_comments`。
    """
    if not anchors:
        raise TypeError(
            "code_of 至少要一个 anchor；整份文件请用 strip_comments(text)。"
            "不给 anchor 时它返回空串，断言会永远通过。")
    src = (ROOT / rel).read_text(encoding="utf-8")
    out = []
    for a in anchors:
        i = src.index(a)
        seg = src[i:]
        j = seg.find("\ndef ", 1)
        out.append(strip_comments(seg if j < 0 else seg[:j]))
    return "\n".join(out)
