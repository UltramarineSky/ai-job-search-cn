"""`/job-scrape` 存下来的字段，必须覆盖打分要用的字段。

## 为什么有这个测试

`scrape.md` Step 4 的 schema 原来只列到 `portal` 为止（7 个字段）。而
`liepin-search` CLI 实际返回 15 个，多出来的 `salary` / `salaryMonths` /
`location` / `workYears` / `eduLevel` / `compScale` / `compIndustry` /
`compStage` / `isHeadhunter` 全被丢弃。

**实测：55 个猎聘职位，有薪资的 0 个、有地点的 0 个。**

> ⚠️ 这段原本还写着「同期 CDP 渠道的 55 个几乎全有」——**那句是错的**。全量复核：
> CDP 三家只有 `salary` 53/55、`location` 54/55，其余六项各 0/55。这句没复核的话
> 让上一轮修复只盯着猎聘，浏览器渠道的洞又留了下来。清单对齐由
> `tests/test_portal_fields_match_schema.py` 盯住。

后果不是少显示几个字段，是**打分建立在空数据上**：薪资与职级（25% 权重）变成
「信息缺失」、强度与公司性质（20%）没有判据、硬门里的学历/年限/通勤全都无从判断。
一半职位的分数有 45% 的权重是从没有数据的地方算出来的。

这个测试盯住三件事：
1. schema 里必须有这些字段；
2. CLI 的输出字段名与 schema 保持一致（别各起各的名）；
3. 打分框架引用的字段名，schema 里都能找到。
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRAPE = ROOT / "workflows" / "job-scrape.md"
EVAL = ROOT / "workflows" / "reference" / "04-job-evaluation.md"
CLI_SKILL = ROOT / ".agents" / "skills" / "liepin-search" / "SKILL.md"

#: 打分与硬门真正会用到的字段。少任何一个，就有一块权重没有依据。
SCORING_FIELDS = {
    "salary": "薪资与职级 25%",
    "salaryMonths": "年包 = 月薪 × 薪数，只比月薪会严重误判",
    "location": "硬门「通勤」",
    "workYears": "硬门「工作年限」",
    "eduLevel": "硬门「学历院校」",
    "compScale": "强度与公司性质 20%",
    "compStage": "强度与公司性质 20%",
}


def schema_block() -> str:
    """Step 4 里那段 json 代码块。"""
    t = SCRAPE.read_text(encoding="utf-8")
    m = re.search(r'```json\s*\n\{\s*\n\s*"seen"\s*:(.*?)```', t, re.S)
    assert m, "scrape.md 里找不到 seen_jobs 的 schema 代码块"
    return m.group(1)


class SchemaCoversScoringFields(unittest.TestCase):
    def test_every_scoring_field_is_in_the_schema(self):
        block = schema_block()
        missing = [f"{k}（{why}）" for k, why in SCORING_FIELDS.items()
                   if f'"{k}"' not in block]
        self.assertFalse(
            missing,
            "scrape.md 的 seen_jobs schema 没有这些字段，抓到也不会存 → "
            f"打分时无依据：{missing}")

    def test_schema_still_has_the_bookkeeping_fields(self):
        """补字段不能把原有的记账字段挤掉。"""
        block = schema_block()
        for k in ("title", "company", "url", "first_seen", "status", "portal"):
            self.assertIn(f'"{k}"', block, f"schema 丢了 {k}")

    def test_the_loss_is_documented_so_it_is_not_re_introduced(self):
        """光加字段不够——要写清为什么，否则下次精简 schema 时又会被删掉。"""
        t = SCRAPE.read_text(encoding="utf-8")
        self.assertIn("打分要用的字段", t)
        self.assertRegex(
            t, r"薪资与职级.*25%",
            "要写明丢掉这些字段会让哪一块权重失去依据")


class FieldNamesMatchTheCli(unittest.TestCase):
    """字段名以 CLI 的输出为准，各渠道别各起各的名。"""

    def test_cli_documents_the_same_field_names(self):
        if not CLI_SKILL.is_file():
            self.skipTest("liepin-search skill 不在这个 clone 里")
        doc = CLI_SKILL.read_text(encoding="utf-8")
        # CLI 文档里至少要出现这几个核心字段名，schema 才有「以它为准」的依据
        for k in ("salary", "location"):
            self.assertIn(k, doc, f"CLI 文档里找不到字段名 {k}")

    def test_schema_names_are_camel_case_like_the_cli(self):
        """CLI 用 salaryMonths / compScale 这种驼峰，schema 不能改成下划线。"""
        block = schema_block()
        for wrong, right in (("salary_months", "salaryMonths"),
                             ("comp_scale", "compScale"),
                             ("work_years", "workYears")):
            self.assertNotIn(f'"{wrong}"', block,
                             f"字段名与 CLI 不一致：应为 {right}")


class EvaluationFrameworkFieldsExist(unittest.TestCase):
    """打分框架点名引用的字段，schema 里必须存在。"""

    def test_referenced_fields_are_stored(self):
        t = EVAL.read_text(encoding="utf-8")
        block = schema_block()
        # 框架正文里以 `field` 形式点名的字段
        referenced = set(re.findall(r"`(salary|salaryMonths|location|compScale|"
                                    r"compStage|workYears|eduLevel)`", t))
        self.assertTrue(referenced, "框架里应当点名这些字段，否则这条测试失去意义")
        missing = sorted(f for f in referenced if f'"{f}"' not in block)
        self.assertFalse(
            missing,
            f"04-job-evaluation.md 用到但 scrape 不存的字段：{missing}")


if __name__ == "__main__":
    unittest.main()
