"""代码读的每一个 `rank_breakdown` 子键，产出方的规范里都得写明。

## 产出方的清单里根本没有这个字段

`rank.md` 的 Step 4「Update State」原来只列三项：`rank_score` / `rank_verdict` /
`rank_date`。**`rank_breakdown` 一个字没提。** 而它有五个消费方：

| 谁 | 读什么 | 读不到会怎样 |
|---|---|---|
| `export_web_data` | `技能与经验`、`依据`、`来源` | 面板的技能分整列空白、没有依据可看 |
| `gap_split` | `四维`（或单列的 `专业能力`/`业务领域`） | 四格分布全空 |
| `fetch_details` | `证据`、`来源` | 「依据来自列表页、未经 JD 复核」的复核规则永不触发 |
| `serve.py` | `来源` | 预筛淘汰的岗在页面上标不出来 |
| `/job-upskill` | 整个第 2 层数据源 | **没有数据**，学习计划无从谈起 |

现有数据里之所以有这个字段，是执行时顺手写的——不是规范要求的。照着原来那份
Step 4 清单跑一轮，上面五项全部静默失效。

## 还有一处形状差

Step 2 让子代理回传的是 `"技能与经验": {"总分": 55, "专业能力": 88, …}`（**字典**），
而 `export_web_data` 按 `isinstance(..., int)` 取——是字典就**静默丢弃**。
两处形状不同，中间却没有任何一句说要拍平。实测这份真实数据里 112 条是 int、
17 条是 null（没打分的岗），没有字典——执行时自己拍平了，规范没说。

## 判据

从 `tools/*.py` 里**现抽**被读到的子键，逐个要求 `rank.md` 提到。
不抽「只写不读」的（`prescreen.py` 自己写的 `本轮规则` 之类）——那不是 `/job-rank` 的产出契约。
"""

import ast
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RANK = ROOT / "workflows" / "job-rank.md"

#: 内联式：`(e.get("rank_breakdown") or {}).get("KEY")`
_INLINE = re.compile(r'get\("rank_breakdown"\)\s*or\s*\{\}\)\s*\.get\("([^"]+)"')
#: 先赋值：`b = e.get("rank_breakdown")` …… 之后 `b.get("KEY")`
_ASSIGN = re.compile(r'(\w+)\s*=\s*\w+\.get\("rank_breakdown"\)')


def _scopes(text: str):
    """按函数切段 —— 变量名会跨函数重用。

    ⚠️ **这一层是 2026-08-30 补的，补之前它会认错键。**
    先赋值那一支原来从赋值处一路扫到**文件末尾**：`audit_pipeline` 里
    `b = v.get("rank_breakdown")` 之后几千行，`_same_job(a, b)` 里的
    `b.get("title")` 就被算成了 `rank_breakdown` 的子键 ——
    那个 `b` 是一条职位记录，不是拆解。

    同一课这个仓库在 `test_an_assertion_does_not_dump_the_profile` 里
    记过一次：「变量名会跨函数重用，要按函数分域」。
    """
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return [text]
    src = text.splitlines()
    out = []
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out.append(chr(10).join(src[n.lineno - 1:(n.end_lineno or n.lineno)]))
    return out or [text]


def keys_read() -> dict:
    """被读到的子键 → 哪些文件在读。**现抽，不在这里另抄一份清单。**"""
    out: dict = {}
    for p in sorted((ROOT / "tools").glob("*.py")):
        text = p.read_text(encoding="utf-8")
        if "rank_breakdown" not in text:
            continue
        for m in _INLINE.finditer(text):
            out.setdefault(m.group(1), set()).add(p.name)
        for seg in _scopes(text):
            for vm in _ASSIGN.finditer(seg):
                var = vm.group(1)
                for m in re.finditer(rf'\b{var}\.get\("([^"]+)"', seg[vm.end():]):
                    out.setdefault(m.group(1), set()).add(p.name)
    return out


class RankDocumentsTheFieldItsConsumersRead(unittest.TestCase):

    def test_the_scan_finds_consumers(self):
        """控制用例：真抽到了消费方，否则下面那条永远绿。"""
        found = keys_read()
        self.assertGreaterEqual(
            len(found), 4,
            f"只抽到 {len(found)} 个被读的子键：{sorted(found)}——"
            "抽取逻辑大概失效了，而不是真的没人读 rank_breakdown 了")

    def test_the_write_step_is_where_it_is_documented(self):
        """必须写在 **Step 4（落盘那一步）**里，不能只在别处顺带提一句。

        第一版写的是「全文里有 `rank_breakdown` 就算」——变异验证当场证明它空转：
        把 Step 4 的整段规范删掉，全文别处（预筛那行 `rank_breakdown.来源`）
        仍然提着这个词，断言照样绿。**规范写在哪一步是有意义的**：
        执行者做到 Step 4 才去写盘，写在 Step 1 的旁注里等于没写。
        """
        text = RANK.read_text(encoding="utf-8")
        i = text.index("## Step 4：")
        j = text.index("\n## ", i)
        self.assertIn(
            "rank_breakdown", text[i:j],
            "Step 4（落盘）里没有 rank_breakdown，而五个消费方在读它——"
            "\n照这份规范跑一轮，/job-upskill 没有数据、面板技能分整列空白，且全程不报错")

    def test_every_key_read_is_documented(self):
        doc = RANK.read_text(encoding="utf-8")
        bad = [f"`{k}`（{'、'.join(sorted(v))} 在读）"
               for k, v in sorted(keys_read().items()) if k not in doc]
        self.assertEqual(
            bad, [],
            "这些 rank_breakdown 子键有人读、但产出方的规范里没写：\n  "
            + "\n  ".join(bad)
            + "\n产出方不写，执行时就不会写盘，而消费方失效是**静默**的："
            "\n没有报错，只是那一格永远空着。")

    def test_the_flattening_rule_is_stated(self):
        """Step 2 回传字典、面板要整数——中间那句「拍平」不能少。"""
        doc = RANK.read_text(encoding="utf-8")
        self.assertRegex(
            doc, r"总分那个整数|不是 Step 2 那个",
            "rank.md 没说 `技能与经验` 落盘要写总分那个整数。"
            "\nStep 2 回传的是 {\"总分\":…} 字典，而 export_web_data 按 isinstance(int) 取——"
            "\n是字典就静默丢弃，面板上那一格空白且不报错。")


if __name__ == "__main__":
    unittest.main()
