"""硬门的证据规则：一票否决是最贵的判断，证据标准必须最高。

## 为什么单独钉这一组

这些规则是用 8 个错判换来的：一轮粗筛判了 26 个「硬门 FAIL」，复核 JD 原文后
31% 是错的——专业不符被当成硬门、「中英文沟通能力」模板话被判成英语 FAIL、
列表页字段说「硕士」而 JD 正文写「本科及以上」。被否掉的岗连分都不打、直接出局，
错误完全静默。

规则都写进了 `04-job-evaluation.md`，但那几节没有测试盯着——文档规则的宿命是
在某次「精简」里被删掉。评分那侧的教训（判词天花板、薪资平台化）已有
`test_verdict_cap.py`；这里补硬门这一侧。
"""

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FRAMEWORK = ROOT / "workflows" / "reference" / "04-job-evaluation.md"


def text() -> str:
    return FRAMEWORK.read_text(encoding="utf-8")


class JudgmentAllocationIsStated(unittest.TestCase):
    """确定的交给规则，拿不准的交给判断——这是用户定的工具姿态。"""

    def test_the_three_tiers_exist(self):
        t = text()
        self.assertIn("判断权的分配", t)
        self.assertIn("证据确凿", t)
        self.assertIn("不许 FAIL", t, "拿不准的一档必须明写不许 FAIL")

    def test_missing_from_profile_means_unknown_not_absent(self):
        t = text()
        self.assertIn("不要当成「没有」", t,
                      "资料里没记录 ≠ 没有——要问用户，这是猎头和扫描器的分界")

    def test_the_cost_asymmetry_is_recorded(self):
        t = text()
        self.assertIn("宁可多一条 FLAG，不可多一个错杀", t)
        self.assertIn("26 个 FAIL 错了 8 个", t,
                      "要留下实测数字——没有它，下次会觉得从严更「安全」")


class MajorMismatchIsNotAGate(unittest.TestCase):
    def test_the_rule_exists(self):
        t = text()
        self.assertIn("专业不符**不是硬门**", t)

    def test_the_reason_names_the_template_sentence_problem(self):
        t = text()
        self.assertIn("模板句", t,
                      "要写明「计算机相关专业」是国内 JD 近乎标配的模板句")


class LanguageGateNeedsExplicitWording(unittest.TestCase):
    def test_fail_wordings_are_listed(self):
        t = text()
        self.assertIn("可作为工作语言", t)

    def test_soft_wordings_are_flag_not_fail(self):
        t = text()
        self.assertIn("「英语良好」「中英文沟通能力」", t)
        self.assertIn("**FLAG**，不是 FAIL", t,
                      "软措辞只能 FLAG——一句套话让对口岗出局的实测就是这么来的")


class JdTextBeatsListingFields(unittest.TestCase):
    def test_the_rule_exists(self):
        t = text()
        self.assertIn("只认 JD 正文，不认列表页字段", t)

    def test_field_verdicts_must_be_reaudited(self):
        t = text()
        self.assertIn("抓到 JD 之后必须复核", t,
                      "字段判的硬门要在拿到正文后复核——fetch_details --recheck 就是为此存在")

    def test_unreviewed_verdicts_must_be_labeled(self):
        t = text()
        self.assertIn("未经 JD 正文复核", t,
                      "复核不了的要标注证据强度，不能和读过原文的判断一样确凿")


if __name__ == "__main__":
    unittest.main()
