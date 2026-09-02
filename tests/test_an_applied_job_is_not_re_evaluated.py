# -*- coding: utf-8 -*-
"""投过的岗不重复评 —— 这条规则原来只写在文档里，没有任何工具执行它。

`job-rank.md` Step 1 第 2 条一直写着：

> 投递记录里已有的「公司 + 岗位」一律不在范围内，**任何参数都不能覆盖这一条**

而 2026-08-26 之前**没有一行代码在做这件事**，全靠执行者手工比对台账。
当天就漏了一个：台账 2026-08-13 记着「蓝湾智投科技 / AI应用产品经理」，
同一天 `/job-auto` 又把同一家的「AI应用产品经理（**agent**）」当新岗评了一遍——
标题只多了三个字，精确比对就认不出来了。代价是一次 JD 读取 + 一份深评 + 一份话术。

本人当场指出：「蓝湾智投科技 之前投过的吧，这类信息也该落盘，避免后面重复获取」。

## 为什么不能靠 `build_dashboard.match_tracker`

那个函数**故意**不让「已经钉在另一个 URL 上的投递记录行」去认同公司的新岗，
它的注释里记着「后端工程师」被「后端工程师（社招）」吞掉那次事故。
**那条设计是对的**——它防的是把新岗**静默标成已投**、从待投区消失。

这里要的是相反的一件事：不静默、不标已投，而是**结案并把原投递写进依据**，
用户在总览页看得见、也翻得回来。两件事共存，不冲突。
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import prescreen  # noqa: E402

APPLIED = [
    {"date": "2026-08-13", "company": "蓝湾智投科技", "role": "AI应用产品经理",
     "status": "applied",
     "source": "https://www.zhipin.com/job_detail/95ec10f0a740797c0nJ70t2_EVZZ.html"},
    {"date": "2026-08-10", "company": "川流互联", "role": "大模型平台产品经理",
     "status": "interview", "source": ""},
]


class TheSameRoleAtTheSameCompanyIsClosed(unittest.TestCase):
    def test_the_incident_itself(self):
        """**当天那一个。** 标题多了「（agent）」，精确比对认不出，模糊比对认得出。"""
        job = {"company": "蓝湾智投科技", "title": "AI应用产品经理（agent）"}
        why = prescreen.rule_applied_same_role(job, APPLIED)
        self.assertTrue(why, "标题多三个字就认不出来了——那正是当天漏掉的那个形状")
        self.assertIn("2026-08-13", why, "没写清是哪天投的")
        self.assertIn("95ec10f0", why, "没给原投递的链接，用户没法回去核对")

    def test_a_different_role_at_the_same_company_is_only_parked(self):
        """同一家开几个不同的岗是常态，**不能因为投过一个就把其余的全毙掉**。"""
        job = {"company": "蓝湾智投科技", "title": "数据分析师"}
        self.assertIsNone(prescreen.rule_applied_same_role(job, APPLIED),
                          "不同的岗被当成同一个结案了")
        park = prescreen.rule_applied_same_company(job, APPLIED)
        self.assertTrue(park, "同公司这条信息丢了——它是真实的排序依据")
        self.assertIn("先排队尾", park)

    def test_a_different_company_is_untouched(self):
        job = {"company": "某某科技", "title": "AI应用产品经理"}
        self.assertIsNone(prescreen.rule_applied_same_role(job, APPLIED))
        self.assertIsNone(prescreen.rule_applied_same_company(job, APPLIED))

    def test_an_anonymous_employer_never_matches(self):
        """**脱敏串不构成公司身份。**

        「某知名公司」在这个库里出现过 158 次，那是 158 家不同的用人方。
        拿它当键做模糊匹配，一条投递记录就能把一批岗一起判死。
        判据与 `build_dashboard.match_tracker` 里那段同源。
        """
        rows = [{"date": "2026-08-01", "company": "某知名公司",
                 "role": "AI产品经理", "status": "applied", "source": ""}]
        for name in ("某知名公司", "某上海人工智能上市公司", "某杭州IT服务公司"):
            with self.subTest(company=name):
                job = {"company": name, "title": "AI产品经理"}
                self.assertIsNone(prescreen.rule_applied_same_role(job, rows))
                self.assertIsNone(prescreen.rule_applied_same_company(job, rows))

    def test_the_loader_drops_anonymous_rows_too(self):
        """两头都要挡：规则里挡一次，读台账时也挡一次。

        只挡一头是不够的——`applied_rows` 是别处也会用的公共入口，
        它交出去的每一行都该是能当键用的。
        """
        src = (ROOT / "tools" / "prescreen.py").read_text(encoding="utf-8")
        seg = src.split("def applied_rows(")[1].split("def ")[0]
        self.assertIn("is_anonymous_employer", seg, "读台账时没挡脱敏行")
        self.assertIn('r.get("status")', seg, "没挡「还没投出去」的行")

    def test_rows_without_a_status_are_not_applications(self):
        """`status` 空的行不是投递 —— 台账里也存只记了岗位、还没投的行。"""
        import csv
        import io
        raw = ("date,company,role,status,source\n"
               "2026-08-01,蓝湾智投科技,AI应用产品经理,,\n")
        rows = [r for r in csv.DictReader(io.StringIO(raw))
                if (r.get("status") or "").strip()]
        self.assertEqual(rows, [], "没有状态的行被当成投过了")


class TheRuleIsWiredIntoPrescreen(unittest.TestCase):
    """规则光存在不够 —— 它得真的挂在预筛的规则表上，而且是「客观」那一档。"""

    def test_both_rules_are_registered(self):
        src = (ROOT / "tools" / "prescreen.py").read_text(encoding="utf-8")
        body = src.split("OBJECTIVE, INFERRED")[1]
        self.assertIn("rule_applied_same_role", body, "同岗那条没挂上规则表")
        self.assertIn("rule_applied_same_company", body, "同公司那条没挂上规则表")

    def test_the_same_role_rule_is_objective_not_inferred(self):
        """台账是**客观事实**，不是推断——所以它结案，不只是泊车。

        挂错档的后果很具体：推断只降权，那个岗还留在 `new` 里，
        下一轮照样会被抓 JD，「避免重复获取」就没做到。
        """
        src = (ROOT / "tools" / "prescreen.py").read_text(encoding="utf-8")
        seg = src.split("rule_applied_same_role(e, _applied)")[0]
        tail = seg[-260:]
        self.assertIn("OBJECTIVE", tail,
                      "同岗那条挂成了推断档 —— 那样只泊车不结案，还是会再花一次额度")

    def test_it_needs_no_parameters(self):
        """这一条不吃任何命令行参数：不填资料的新用户也该有它。"""
        src = (ROOT / "tools" / "prescreen.py").read_text(encoding="utf-8")
        i = src.index("_applied = applied_rows(user)")
        self.assertNotIn("args.", src[i:i + 400].split("rules.append")[0],
                         "这条规则被某个参数挡住了")


if __name__ == "__main__":
    unittest.main()
