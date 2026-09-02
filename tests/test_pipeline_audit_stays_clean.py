"""流水线审计不许出现 `error` 级发现。

`tools/audit_pipeline.py` 拿**真实职位库**当语料，抓的是单元测试抓不到的那一类：
代码跑得好好的，规则本身却是断的。2026-08-19 第一次跑就翻出：

- `validThrough`（抓取侧写）与 `deadline`（评分侧读）**名字不同**，中间没人对上——
  `/job-rank` 的「截止日期 7 天内标 🔥、已过期转 expired」从上线起就没生效过；
- `datePosted` 与 `date` 同一个坑的第二处；
- 三个岗的 `salaryMonths` 是 25 / 30，折出 150-550 万年包，直接顶满薪资维（25% 权重），
  而那条「薪数落在 12–24」的校验只写在解 BOSS 字体那一节、从没对存量执行过。

**分两级是关键**：`error` = 链路断了（我们的 bug）；`warn` = 源头没给数据
（平台的事，记着但不算失败）。一个永远红的审计会被当成背景噪音略过，
所以这里只钉死 `error`。
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import audit_pipeline as audit  # noqa: E402


def _user():
    p = ROOT / ".active_user"
    if not p.is_file():
        return ""
    return p.read_text(encoding="utf-8").strip()


class AuditHasNoErrors(unittest.TestCase):
    def test_no_error_level_findings(self):
        user = _user()
        if not user:
            self.skipTest("没有活动用户")
        if not (ROOT / "users" / user / "job_scraper" / "seen_jobs.json").is_file():
            self.skipTest("还没抓过职位")
        found = audit.run(user)
        errs = [f"{k}：{d}" for lvl, k, d in found if lvl == "error"]
        self.assertEqual(errs, [],
                         "流水线审计发现断链（跑 python tools/audit_pipeline.py 看全文）：\n  "
                         + "\n  ".join(errs))


class TheAuditCanActuallyFail(unittest.TestCase):
    """变异内建：审计得真的会红，否则上面那条测试只是摆设。"""

    def test_name_mismatch_detector_bites(self):
        import jd_store as st
        real = st.MERGE_RENAME
        try:
            st.MERGE_RENAME = {}                 # 假装改名映射没做
            found = audit.check_name_mismatch({}, {})
        finally:
            st.MERGE_RENAME = real
        self.assertTrue(any(lvl == "error" for lvl, _, _ in found),
                        "把改名映射拿掉，检测器居然还是绿的")

    def test_salary_months_detector_bites(self):
        found = audit.check_salary_months_sane(
            {"k": {"salaryMonths": 30, "salary": "60-90k·30薪", "title": "假岗"}})
        self.assertTrue(found, "30 薪没被检出")

    def test_verdict_vocabulary_detector_bites(self):
        found = audit.check_verdict_vocabulary({"k": {"rank_verdict": "还行吧"}})
        self.assertTrue(any(lvl == "error" for lvl, _, _ in found),
                        "自造判词没被检出")

    def test_scheme_twin_detector_bites(self):
        found = audit.check_scheme_twins({
            "a": {"url": "http://x/1", "title": "同一个岗"},
            "b": {"url": "https://x/1", "title": "同一个岗"}})
        self.assertTrue(any(lvl == "error" for lvl, _, _ in found),
                        "http/https 孪生没被检出")


class TheRenameMapIsTheOnlyPlaceNamesAreBridged(unittest.TestCase):
    """详情侧与库侧的名字对照只许有一份，写两遍必然分叉。"""

    def test_rename_map_exists_and_covers_the_measured_pairs(self):
        import jd_store as st
        self.assertIn("validThrough", st.MERGE_RENAME)
        self.assertEqual(st.MERGE_RENAME["validThrough"], "deadline")
        self.assertIn("datePosted", st.MERGE_RENAME)
        self.assertEqual(st.MERGE_RENAME["datePosted"], "date")

    def test_merge_covers_fields_that_have_consumers(self):
        """有消费者的字段必须在回填表里，否则详情抓到了也流不进职位库。"""
        import jd_store as st
        both = set(st.MERGE_FIELDS) | set(st.MERGE_RENAME.values())
        for f in ("employmentType", "recruiter", "benefits", "date", "deadline"):
            self.assertIn(f, both, f"`{f}` 有消费者却不在回填表里")


if __name__ == "__main__":
    unittest.main()
