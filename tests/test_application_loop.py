"""投递闭环：从 /job-outcome 记一笔到面板认出它。

## 为什么现在才有这个测试

这是整条流水线**唯一没被真实数据跑通过**的一段——`已投递` 长期是 0，所以
下游的错谁也没撞见过。把一个岗假设成「已投」跑一遍，当场翻出三个：

1. 两个面板的「打过分」不一致（193 vs 195）。同一个量两处各写各的实现，
   而 `test_pipeline_counts.py` 里那个类叫 `CountsAgreeAcrossEntryPoints`，
   却只比了导出与盘上数据，**从没比过这两个入口**。名字承诺的比它做的多。
2. 投递记录只被数了个总数，从没回接到岗位上：面板说「已投递 1」，
   哪一个投了完全看不出来，那个岗照旧躺在可以投的列表里。
   求职最容易犯的错就是重复投同一家。
3. `next_step` 的「投了，先把这笔记下来」永不推进——判据是
   `applied > 0`（你投过东西），文案说的却是「有一笔没记的投递」。
   刚跑完 /job-outcome 它还让你去跑 /job-outcome。
"""

import csv
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import build_dashboard as bd  # noqa: E402


class CountsUseOneImplementation(unittest.TestCase):
    """同一个量只留一个实现，才谈得上跨入口一致。"""

    SEEN = {
        "a#1": {"status": "ranked", "rank_score": 70},
        "b#2": {"status": "ranked", "rank_score": None,
                "rank_verdict": "硬门 FAIL (学历院校)"},   # 已结案、按规定不给分
        "c#3": {"status": "skipped", "rank_score": 55},    # 用户手动不投，也处理过了
        "d#4": {"status": "new"},
        "e#5": {"status": "expired"},
    }

    def test_web_and_single_page_share_the_function(self):
        import export_web_data as ex
        self.assertIs(ex.n_processed, bd.n_processed,
                      "两个面板各自实现了「打过分」——迟早飘")

    def test_processed_means_dealt_with_not_scored(self):
        self.assertEqual(bd.n_processed(self.SEEN), 3,
                         "硬性条件没过的、手动不投的都已结案，该算进「打过分」")

    def test_single_page_model_uses_it(self):
        m = bd.build_model(self.SEEN, [], [], True, "张三", ["张三"])
        self.assertEqual(m["counts"]["ranked"], bd.n_processed(self.SEEN),
                         "单页面板没用共用实现")


class NextStepAdvancesAfterRecording(unittest.TestCase):
    """`applied > 0` 是「投过」，不是「有一笔没记」。"""

    def _c(self, **kw):
        base = {"scraped": 100, "ranked": 50, "materials": 0,
                "applied": 0, "interviewing": 0}
        base.update(kw)
        return base

    def test_it_does_not_loop_on_outcome_forever(self):
        txt, cmd = bd.next_step(self._c(materials=1, applied=1), True, "u")
        self.assertNotIn("先把这笔记下来", txt,
                         "全都记完了还让人去跑 /job-outcome —— 建议永远不推进")

    def test_it_points_at_the_materials_not_yet_sent(self):
        txt, _ = bd.next_step(self._c(materials=5, applied=1), True, "u")
        self.assertIn("4", txt, "没说清还剩几个材料就绪但没投")

    def test_all_sent_points_back_at_the_loop(self):
        """全发完了 → 接着抓，不是「等回复、可以催一次」。

        2026-08-29 用户裁定：跟进归他，工具不催
        （`AGENTS.md`「跟进归用户，工具不催」）。
        顺带解掉的是**「等」不是下一步**那条老规矩——
        原来那句「等回复」他动不了手。
        """
        txt, cmd = bd.next_step(self._c(materials=3, applied=3), True, "u")
        self.assertEqual(cmd, "/job-auto")
        self.assertNotIn("催", txt)

    def test_interviewing_still_wins(self):
        txt, _ = bd.next_step(self._c(materials=3, applied=3, interviewing=1),
                              True, "u")
        self.assertIn("面试", txt, "有面试时它才是最该做的一件事")


class TrackerRowsLinkBackToJobs(unittest.TestCase):
    """只报总数、不报是哪个的计数器，帮不上「别重复投」这个忙。"""

    def test_matching_is_normalized_but_never_guessed(self):
        """对**真实的 match_tracker** 做行为断言，不再本地复刻归一规则。

        原来这里的 `norm` 是测试自己的 lambda（而且规则还与产品不一样：它把
        括号后整段截掉，产品的 `normalize_key` 保留括号内容做子串匹配）——
        改坏 `normalize_key`/`_fuzzy` 它照样绿，唯一的产品断言是 hasattr。
        """
        # 带编号后缀的岗位名要匹配上（平台常在岗位名后挂编号）。
        # **公司名不用「某…」当占位**：那是脱敏串，`match_tracker` 按
        # `_cli.is_anonymous_employer` 把它排除在模糊回退之外，
        # 用它做夹具会让这条测试测不到它想测的东西。
        job = {"title": "智能体产品经理（J00001）", "company": "云枢运营商研究院"}
        rows = [{"company": "云枢运营商研究院", "role": "智能体产品经理",
                 "source": "", "date": "2026-08-01", "status": "applied"}]
        self.assertIsNotNone(
            bd.match_tracker(job, "https://x/1", rows),
            "带括号编号的岗位名匹配不上台账行——归一没生效")
        # 不同岗位不能被匹配成同一个：台账记的是「AI产品经理」，
        # 「AI体验设计师」不该蹭上这一行
        other = {"title": "AI体验设计师", "company": "云枢运营商研究院"}
        rows2 = [{"company": "云枢运营商研究院", "role": "AI产品经理",
                  "source": "", "date": "2026-08-01", "status": "applied"}]
        self.assertIsNone(
            bd.match_tracker(other, "https://x/2", rows2),
            "完全不同的岗位被匹配到了同一条台账行——归一放得太宽")

    def test_real_tracker_row_reaches_the_dashboard(self):
        """控制测试：盘上真有投递记录时，对应岗位必须带上标记。"""
        import json
        ptr = ROOT / ".active_user"
        if not ptr.is_file():
            self.skipTest("没有活动用户")
        user = ptr.read_text(encoding="utf-8").strip()
        t = ROOT / "users" / user / "job_search_tracker.csv"
        data = ROOT / "web" / "public" / "data.json"
        if not t.is_file() or not data.is_file():
            self.skipTest("还没有投递记录或还没导出")
        with t.open(encoding="utf-8-sig", newline="") as f:
            rows = [r for r in csv.DictReader(f) if (r.get("company") or "").strip()]
        if not rows:
            self.skipTest("投递记录是空的")
        jobs = json.loads(data.read_text(encoding="utf-8"))["jobs"]
        marked = [j for j in jobs if j.get("applied")]
        self.assertTrue(
            marked,
            f"tracker 里有 {len(rows)} 条投递记录，面板上却没有一个岗带「已投」标记")


if __name__ == "__main__":
    unittest.main()


class InterviewStageIsNotHardcodedToZero(unittest.TestCase):
    """流水线第 5 格曾经写死 0，把整条分支变成死代码。

    网页版两处都写 `"interviewing": 0`（counts 里一处、pipeline 里一处），
    于是「面试中」永远是零；而 `next_step` 的**第一条**分支判的正是
    `interviewing > 0`——「有面试了，去备面 → /job-interview」在网页版**永远触发不到**。
    单页面板那边一直是真算的（`match_tracker` + `_INTERVIEW_STATUSES`），
    两个入口又一次不一致。

    这个错藏得住，只因为「已投递」长期是 0，没人走到过第五格。
    """

    def test_export_does_not_hardcode_zero(self):
        src = (ROOT / "tools" / "export_web_data.py").read_text(encoding="utf-8")
        self.assertNotIn('"interviewing": 0', src,
                         "面试中又被写死成 0 —— next_step 的备面分支会变成死代码")
        self.assertNotIn('"label": "面试中", "count": 0', src)

    def test_it_reuses_the_shared_matcher(self):
        """别再写第二套匹配。共享那份知道 51job 同 URL 挂两个岗的陷阱。"""
        import export_web_data as ex
        self.assertTrue(hasattr(ex, "match_tracker"),
                        "没复用 build_dashboard.match_tracker")
        self.assertIs(ex.match_tracker, bd.match_tracker)

    def test_interview_statuses_come_from_one_place(self):
        import export_web_data as ex
        self.assertIs(ex.INTERVIEW_STATUSES, bd._INTERVIEW_STATUSES)

    def test_doctors_private_copy_agrees(self):
        """doctor 不 import 仓库模块，只能持一份副本——那这份副本就必须有人钉。

        它头上的注释原来写着「test_display_wording.py 会检查两边一致」，
        而那个文件里**根本没有**相关断言——虚构的守卫比没有守卫更坏，
        它让人以为这条已经被守住了。现在真钉在这里。
        """
        import doctor
        self.assertEqual(doctor.INTERVIEW_STATUSES, bd._INTERVIEW_STATUSES,
                         "doctor 的 INTERVIEW_STATUSES 副本与面板权威值分叉了")

    def test_real_data_reflects_an_interview_row(self):
        """控制测试：tracker 里有 interview 行时，流水线第 5 格必须 > 0。"""
        import json
        ptr = ROOT / ".active_user"
        data = ROOT / "web" / "public" / "data.json"
        if not ptr.is_file() or not data.is_file():
            self.skipTest("没有活动用户或还没导出")
        t = ROOT / "users" / ptr.read_text(encoding="utf-8").strip() / "job_search_tracker.csv"
        if not t.is_file():
            self.skipTest("还没有投递记录")
        with t.open(encoding="utf-8-sig", newline="") as f:
            n = sum(1 for r in csv.DictReader(f)
                    if (r.get("status") or "").strip().lower() in bd._INTERVIEW_STATUSES)
        if not n:
            self.skipTest("投递记录里没有进入面试的行")
        d = json.loads(data.read_text(encoding="utf-8"))
        got = next(s["count"] for s in d["pipeline"] if s["label"] == "面试中")
        self.assertGreater(got, 0,
                           f"tracker 里有 {n} 行已进面试，面板第 5 格却是 {got}")


class AnonymousEmployerIsFlaggedOnRealData(unittest.TestCase):
    """字段声明了、界面用着、演示数据里是 true，**唯独真实数据从没设过**。

    这正是 `export_web_data.py` 开头警告的那种坑：「虚构数据的问题不是不够真，
    而是它长得像真的」——功能在 demo 上看着能用，真实数据里永远不亮。
    实测 195 个岗里 77 个（约四成）是脱敏串。
    """

    def test_exporter_sets_the_flag(self):
        src = (ROOT / "tools" / "export_web_data.py").read_text(encoding="utf-8")
        self.assertIn('"anonymousEmployer"', src,
                      "导出器仍未设置这个字段，界面上那句「（公司未公开）」永远不亮")

    def test_masked_names_are_caught_and_real_ones_are_not(self):
        """调**产品自己的判据**，不再本地复刻一个 lambda 自测自。

        原来这里 `flag = lambda s: bool(re.search(r"某|保密|未公开", s))`——
        六正五反全部喂给测试自己的复刻品，把导出器的真实正则改回历史上错过的
        `^某`（「某」不在开头漏 3 条，docstring 里记着的那个 bug），本测试照绿。
        判据为此抽成了 `is_anonymous_employer`。
        """
        import export_web_data as ex
        flag = ex.is_anonymous_employer
        for s in ["某大型互联网电商平台上市公司", "某上海大型游戏公司",
                  "某国内新能源上市公司", "公司名保密",
                  # 「某」不一定在开头——平台常写「城市 + 某大型…」，实测漏过 3 条
                  "上海某大型物流/仓储公司", "上海某二级医院"]:
            self.assertTrue(flag(s), f"没认出脱敏串「{s}」")
        # 反例用**虚构**公司名。真名在这里没有额外说服力，却会说出
        # 「维护者投过这几家」——那是第三方数据（`test_no_maintainer_data_in_repo`
        # 的 `applied_companies` 盯着这件事）。判据看的是「有没有脱敏痕迹」，
        # 与名字是真是假无关，所以换掉不损失任何覆盖。
        for s in ["星岚互娱", "澜图科技", "北辰新能源", "常青财产保险",
                  "上海知微网络科技有限公司"]:
            self.assertFalse(flag(s), f"把真名「{s}」误判成脱敏")

    def test_masked_names_never_enter_the_applied_company_set(self):
        """脱敏串不是公司名，不能拿它去认「这家投过」。

        2026-08-19 实测（2440 个岗）：全站 437 个岗被标「这家投过」，
        **344 个（79%）来自脱敏串**——「某知名公司」一个名字底下挂着 146 个岗，
        它们互不相干，却因为字符串相等被判成同一家。

        标错只是噪音；真正的代价在「不想看什么」的「投过的公司不再显示」——
        同一个集合，勾上就把这 344 个岗**藏掉**。两个调用方共用
        `appliedCompanySet`，所以守在集合上，不守在两个用它的地方。
        """
        src = (ROOT / "web" / "src" / "data" / "hidden.ts").read_text(encoding="utf-8")
        i = src.index("export function appliedCompanySet")
        body = src[i:src.index(chr(10) + "}", i)]
        self.assertTrue(body, "找不到 appliedCompanySet")
        self.assertIn("anonymousEmployer", body,
                      "脱敏串又进了已投公司集合——「某知名公司」会把几十家不相干的"
                      "公司认成同一家，标错、还会被「不想看什么」整批藏掉")

    def test_interview_workflow_has_an_anonymous_branch(self):
        """Step 2 要求核实每条公司主张；雇主匿名时那一步没有合法路径。

        评分框架早有「雇主匿名——按未知打，不按坏打」，/job-interview 却没有对应分支，
        于是「为什么这家公司」只能空着或者编。
        """
        t = (ROOT / "workflows" / "job-interview.md").read_text(encoding="utf-8")
        self.assertIn("雇主匿名", t, "/job-interview 仍没有匿名雇主分支")
        self.assertIn("不要按行业描述去猜", t, "没写明不许猜是哪家公司")


class OnlyTheOutcomePathWritesTheTracker(unittest.TestCase):
    """投递记录只由「记一笔」那条路写 —— 搜索命令不许自己加行。

    2026-09-02 实测：`job-scrape.md` 的 Step 6 写着「用户决定投某个岗时，
    往 `job_search_tracker.csv` 里加一行」，而**同一份文件**的 Step 0 第 2 条
    就写着「文件不存在（刚 clone 下来 —— **只有 `/job-outcome` 会创建它**）」。
    同一份文档里两句话对着干。

    链上的邻居也都不是这么做的：`/job-rank` 明写「不要动
    `job_search_tracker.csv`」，`/job-auto` 的铁律写着自己一个字不动它，
    `AGENTS.md` 那张衔接图里写回投递记录的是 `/job-outcome` 与 `/job-gmail-sync`。
    **只有这条搜索命令留着一个自己加行的口子。**

    代价不是「多一行」：`/job-outcome` 那条路要问清发生了什么、归档材料、
    写 `job-outcome.md`、再刷面板；从搜索里直接塞一行进去，那几样一样都没有，
    而 `job-scrape` 的 Step 0 与 Step 4 又拿这张表去重 ——
    一个半成品行会让这个岗**再也搜不到**。

    判据从正文推导，登记表只列**该写的**那几条并写明各自写什么。
    """

    #: 允许写投递记录的，值是「它写什么、凭什么」。
    ALLOWED = {
        "job-outcome": "这张表就是它的产出：新建表头、改状态、记跟进",
        "job-gmail-sync": "认出面试邀请/拒信后回写 status 与 notes —— "
                          "`AGENTS.md` 那张衔接图点名的两条之一",
        "job-offer": "只往那一行的 `notes` 里写一句 offer 答复期，"
                     "它的「记在哪儿」那一节说明了为什么不新开一列",
    }

    _WRITE = re.compile(
        r"(往|向|把).{0,30}job_search_tracker\.csv.{0,20}(加|写|追加)|"
        r"job_search_tracker\.csv.{0,40}(加一行|写入|更新|追加|新建)|"
        r"写进 `job_search_tracker\.csv`")

    #: 「**不要**往里加行」也含同样的词 —— 判据要分得清「做 X」和「不要做 X」，
    #: 否则改完之后那句禁令自己会把守卫喂饱（第 16 轮栽过一次同样的形状）。
    #:
    #: **只认紧贴在写动作前面的否定词。** 整行扫一遍否定词太粗：
    #: `job-gmail-sync` 那条真写指令的行尾还跟着「**绝不重排 CSV、不调整行序**」
    #: —— 否定的是别的事，而按整行判它会被当成禁令放过去（当场红过一次）。
    _DONT = re.compile(r"(不要|不许|不得|绝不|不会|别)[^。；\n]{0,12}$")

    def _writers(self) -> list:
        out = []
        for wf in sorted((ROOT / "workflows").glob("job-*.md")):
            for line in wf.read_text(encoding="utf-8").splitlines():
                if line.lstrip().startswith(">"):
                    continue          # 引用块是记事，不是指令
                m = self._WRITE.search(line)
                if m and not self._DONT.search(line[:m.start()]):
                    out.append(wf.stem)
                    break
        return out

    def test_the_scan_finds_the_legit_writers(self):
        """控制用例：该写的那几条推得出来，否则下面那条对着空气跑。"""
        got = self._writers()
        for w in ("job-outcome", "job-gmail-sync"):
            with self.subTest(w=w):
                self.assertIn(w, got, f"{w} 明明在写投递记录，判据没认出来")

    def test_no_unregistered_writer(self):
        extra = [w for w in self._writers() if w not in self.ALLOWED]
        self.assertEqual(
            extra, [],
            f"这些命令在指示往投递记录里写，而它们不该写：{extra}。"
            "\n正路是 `/job-outcome <公司>`（或总览页那一行的按钮）—— "
            "它要问清经过、归档材料、写 job-outcome.md、再刷面板，"
            "从别处塞一行进去这几样一样都没有")

    def test_the_exemptions_are_justified(self):
        for name, why in self.ALLOWED.items():
            with self.subTest(cmd=name):
                self.assertTrue((ROOT / "workflows" / f"{name}.md").is_file())
                self.assertGreater(len(why), 10, "豁免要写清它写什么")
