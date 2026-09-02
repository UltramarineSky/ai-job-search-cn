"""深评产出之后，库必须跟着改——evaluation.md 与 seen_jobs.json 不许各说各话。

## 为什么

`04-job-evaluation.md` 规定「深评一旦产出，必须覆盖粗筛分」，`resolve_score` 还额外
兜了一道（导出时有 evaluation.md 就以它为准）。**兜底反而把病藏住了**：面板显示的
是对的，库里躺着错的，而 `/job-rank` 的「已评过就跳过」、预筛、`/job-upskill` 读的全是库。

实测体检抓出 4 个 7 月底的老投递目录深评从没写回：

    某央企运营商研究院_智能体产品经理   库 44/不建议  ← 深评 62/值得投
    某科技上市公司_AI智能体解决方案负责人  库 76/强匹配  ← 深评 62/值得投

第二个正是「全库唯一 76 强匹配」——用户看着面板上的 62 做判断，AI 读库时却按
76 强匹配引用它。**两套真相，各自都显得对。**

## 三条不变量（全部跑在真实数据上，没有就跳过）

1. 有 evaluation.md 的岗：库里 `rank_score`/`rank_verdict`/`evaluated` 与文件一致；
2. `evaluated` 的条目判词不带「粗筛：」前缀（深评结论没有粗筛这回事）；
3. 已评分（`status != "new"`）的条目不许残留 `deprioritized` 降权标记——
   那是「待评时排队尾」用的，评完还挂着会误导下一轮抓取排序。
"""

import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import build_dashboard as bd  # noqa: E402


def _user_root():
    au = ROOT / ".active_user"
    if not au.is_file():
        return None
    u = ROOT / "users" / au.read_text(encoding="utf-8").strip()
    return u if (u / "job_scraper" / "seen_jobs.json").is_file() else None


class DeepEvalAndStoreAgree(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        u = _user_root()
        if u is None:
            raise unittest.SkipTest("没有活动用户或职位库")
        cls.seen = json.loads(
            (u / "job_scraper" / "seen_jobs.json").read_text(encoding="utf-8"))["seen"]
        cls.by_url = {}
        for v in cls.seen.values():
            cls.by_url.setdefault(v.get("url") or "", v)
        cls.apps = u / "documents" / "applications"

    def test_every_evaluation_md_is_written_back(self):
        if not self.apps.is_dir():
            self.skipTest("还没有投递目录")
        bad = []
        for d in sorted(self.apps.iterdir()):
            ev_f, po_f = d / "evaluation.md", d / "posting.md"
            if not (ev_f.is_file() and po_f.is_file()):
                continue
            m = re.search(r"链接[：:]\s*(\S+)", po_f.read_text(encoding="utf-8"))
            e = self.by_url.get(m.group(1) if m else "")
            if e is None:
                continue          # 链接接不上是另一个测试的事
            pe = bd.parse_evaluation(ev_f.read_text(encoding="utf-8"))
            try:
                score = int(str(pe.get("score")).strip())
            except (ValueError, TypeError):
                continue          # 文件里没有可解析的分（如已下线岗的残档）
            verdict = (pe.get("verdict") or "").strip()
            if not verdict:
                continue
            if e.get("rank_score") != score:
                bad.append(f"{d.name[:30]}: 文件 {score} ≠ 库 {e.get('rank_score')}")
            if (e.get("rank_verdict") or "").replace("粗筛：", "") != verdict:
                bad.append(f"{d.name[:30]}: 文件判词 {verdict!r} ≠ 库 {e.get('rank_verdict')!r}")
            if not e.get("evaluated"):
                bad.append(f"{d.name[:30]}: 深评过却没标 evaluated")
        self.assertEqual(bad, [],
                         "深评没写回库 —— 面板靠 resolve_score 兜底显示是对的，"
                         "但 /job-rank、预筛、/job-upskill 读的是库：\n  " + "\n  ".join(bad))

    def test_deep_evaluated_entries_carry_no_triage_prefix(self):
        bad = [v.get("title") for v in self.seen.values()
               if v.get("evaluated")
               and (v.get("rank_verdict") or "").startswith("粗筛：")]
        self.assertEqual(bad, [],
                         f"深评过的条目还挂着「粗筛：」前缀：{bad}")

    def test_ranked_entries_carry_no_parking_marker(self):
        bad = [v.get("title") for v in self.seen.values()
               if v.get("deprioritized") and v.get("status") != "new"]
        self.assertEqual(bad, [],
                         "已评分的条目还留着降权标记 —— 那是「待评时排队尾」用的，"
                         f"评完还挂着会误导下一轮抓取排序：{bad}")


if __name__ == "__main__":
    unittest.main()
