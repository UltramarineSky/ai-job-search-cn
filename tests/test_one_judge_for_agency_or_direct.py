# -*- coding: utf-8 -*-
"""「猎头还是直招」这件事，第三处又是自己写的 —— 又是同一个错法。

`export_web_data.via_headhunter` 是三态判据（猎头 / 直招 / **没判过**），
它自己的文档专门警告过一种写法：

> **没判过 ≠ 判过是「不是」。** 抓取器没给这个字段时（实测 2638 个岗里 66 个），
> 返回 `False` 会让面板照着印「企业 HR 直招」—— 那是**给错误的信息**，
> 不是少一条信息。

`doctor.py` 栽过这个坑，已经修好，并把经过写进了 docstring。
而 `followups.agency_map` 一直写着 `bool(e.get("isHeadhunter"))` —— **同一个错法**：
不看 `recruiter`，且把「没判过」塌成「直招」。

实测 2026-08-23：全库 2630 个岗里 **66 个**两处判定相反，其中 **5 个**是他真投过的。
那 5 条被 `/job-outcome followup` 放进【企业直招 —— 催 HR】，
而那一组的建议正是「具名的公司还能同时找人内推」——
对一个可能是猎头挂的岗做这件事是白费力气，也正是那段警告点名的害处。

## 为什么这次不是「再修一处」

它已经被各自修过一遍了（doctor 一次），然后在第三处重新长出来。
判据散在各消费方里就会这样。所以这次把**正本搬进 `_cli`** ——
`followups` 和 `export_web_data` 都 import 它，从此共用一份。
`export_web_data` 那两个名字改成转出的别名（本模块内十几处在用）。

`doctor.py` 那份副本留着：它的硬契约是「不 import 仓库任何模块」，
两边相等由 `test_both_next_steps_agree` 钉住 —— 那是**有理由的**副本，
和上面那种不一样。
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tests"))
from _srcscan import strip_comments  # noqa: E402
import _cli  # noqa: E402
import doctor  # noqa: E402
import export_web_data as ex  # noqa: E402
import followups as fu  # noqa: E402

FU = (ROOT / "tools" / "followups.py").read_text(encoding="utf-8")
EX = (ROOT / "tools" / "export_web_data.py").read_text(encoding="utf-8")


class TheJudgeLivesInTheSharedModule(unittest.TestCase):
    def test_cli_owns_it(self):
        self.assertTrue(hasattr(_cli, "via_headhunter"))
        self.assertTrue(hasattr(_cli, "_AGENCY_WORDS"))

    def test_export_reexports_it(self):
        self.assertIs(ex.via_headhunter, _cli.via_headhunter)
        self.assertIs(ex._AGENCY_WORDS, _cli._AGENCY_WORDS)

    def test_export_does_not_redefine_it(self):
        """转出是一行赋值。再写一个 `def` 就是又一份判据。"""
        self.assertNotIn("def via_headhunter(", EX)
        self.assertIn("via_headhunter = _cli.via_headhunter", EX)

    def test_the_move_is_explained(self):
        i = EX.index("_AGENCY_WORDS = _cli._AGENCY_WORDS")
        seg = " ".join(EX[max(0, i - 700):i].split())
        self.assertRegex(seg, r"import 不动这个模块")
        self.assertRegex(seg, r"66 个\*\*两处判定相反")


class TheThreeStatesSurvive(unittest.TestCase):
    """三态是这条判据的全部价值。塌成两态就等于回到那个 bug。"""

    def test_true_when_the_field_says_so(self):
        self.assertIs(_cli.via_headhunter({"isHeadhunter": True}), True)

    def test_false_when_the_field_says_no(self):
        self.assertIs(_cli.via_headhunter({"isHeadhunter": False}), False)

    def test_none_when_the_field_is_absent(self):
        self.assertIsNone(_cli.via_headhunter({}),
                          "没判过被塌成了某一态 —— 那正是要防的")

    def test_the_recruiter_line_wins(self):
        """招聘方名字带中介词时，不管字段怎么写都是中介。"""
        for name in ("某某猎头顾问", "某某人力资源", "某某人才服务", "某某咨询"):
            with self.subTest(name=name):
                self.assertIs(_cli.via_headhunter({"recruiter": name}), True)

    def test_the_recruiter_line_beats_a_false_field(self):
        self.assertIs(_cli.via_headhunter(
            {"recruiter": "某某猎头", "isHeadhunter": False}), True)


class TheFollowupsSideUsesIt(unittest.TestCase):
    def test_it_calls_the_shared_judge(self):
        self.assertIn("_cli.via_headhunter(e)", FU,
                      "催进度那边还在自己判")

    def test_it_no_longer_reads_the_field_raw(self):
        """**先剥注释。** 改动理由里逐字引了旧写法（说明它错在哪），
        整文件扫会撞上自己的解释 —— 这个坑本仓库踩过不止一次。"""
        self.assertNotIn('bool(e.get("isHeadhunter"))', strip_comments(FU))

    def test_the_map_is_three_state(self):
        """`.get()` 取不到也是 None —— 两种「不知道」并成一组是有意的。"""
        self.assertIn("猎头代招 / 企业直招 / 没判过", FU)

    def test_the_unknown_group_covers_both_reasons(self):
        i = FU.index("拿不准是猎头还是直招 —— 按平台形态自己判断")
        seg = " ".join(FU[i:i + 400].split())
        self.assertRegex(seg, r"在职位库里找不到对应记录")
        self.assertRegex(seg, r"抓取器没给「是不是猎头」这个字段")

    def test_the_unknown_group_refuses_to_join_direct(self):
        i = FU.index("拿不准是猎头还是直招")
        seg = " ".join(FU[max(0, i - 500):i + 400].split())
        self.assertRegex(seg, r"没判过不等于判过是「不是」")
        self.assertRegex(seg, r"不能塞进直招")

    def test_the_reason_is_recorded_with_numbers(self):
        i = FU.index("**判据走 `_cli.via_headhunter`，不要在这里读字段。**")
        seg = " ".join(FU[i:i + 900].split())
        self.assertRegex(seg, r"2630 个岗里 66 个")
        self.assertRegex(seg, r"85 条投递里 \*\*5 条\*\*受影响")
        self.assertIn("2026-08-23", seg)

    def test_the_two_real_groups_survive(self):
        for g in ('(True, "猎头代招 —— 催顾问"', '(False, "企业直招 —— 催 HR"'):
            with self.subTest(g=g):
                self.assertIn(g, FU)

    def test_the_referral_advice_is_still_on_the_direct_group(self):
        """那句「具名的公司还能找人内推」正是不能给没判过的岗的那句。

        **窗口只到这一组的 `why` 结束。** 下一组的注释里也写着「找人内推」
        （在解释为什么不能给没判过的岗这条建议）—— 取固定长度会读到它，
        于是把这一组的原句删掉照样绿（变异实测）。"""
        i = FU.index('(False, "企业直招 —— 催 HR"')
        # 到这一组的元组闭合为止。**不能切到下一个 `(None,`** ——
        # 那之前还夹着第三组的注释块，「找人内推」就在那里面（第二版仍绿）。
        j = FU.index('"),', i) + 3
        seg = FU[i:j]
        self.assertLess(len(seg), 400, f"切过头了：{seg[:120]}")
        self.assertIn("找人内推", seg)


class TheDoctorCopyIsTheLegitimateOne(unittest.TestCase):
    """`doctor` 不许 import 仓库模块 —— 它那份副本有理由，且被钉着。"""

    #: 手写的边界样例 —— **只放真数据里不出现的那几种**。
    #: 真数据能覆盖的一律交给下面那条全库比对，别在这儿再列一遍。
    EDGE = ({"isHeadhunter": True}, {"isHeadhunter": False}, {},
            {"recruiter": "某某猎头"},
            {"recruiter": "某某猎头", "isHeadhunter": False},
            # 头衔在另一个字段里（BOSS 的 `recruiter` 是空的）
            {"recruiterTitle": "某某企业管理咨询 · 猎头顾问",
             "isHeadhunter": False},
            # 头衔像用人方 —— 反方向不成立，不许翻
            {"recruiterTitle": "人力资源总监", "isHeadhunter": False},
            {"recruiterTitle": "人才招聘经理"},
            # 显式 null（真数据 0 个，但判据得对）
            {"isHeadhunter": None},
            {"isHeadhunter": None, "url": "https://www.liepin.com/a/1.shtml"},
            {"url": "https://www.liepin.com/a/1.shtml"},
            {"url": "https://www.liepin.com/job/1.shtml"})

    def test_doctor_agrees_on_the_edges(self):
        for entry in self.EDGE:
            with self.subTest(entry=entry):
                self.assertIs(doctor._via_headhunter(entry),
                              _cli.via_headhunter(entry))

    def test_doctor_agrees_on_every_job_in_the_store(self):
        """**手写名单只盖得住已经想到的。**

        这条原来只有五个手写样例，而正本 2026-08-30 一次加了三条规则
        （头衔里的「猎头」二字、猎聘 `/a/` 路径、显式 `null` 算没判过）——
        五个样例一条都没碰到，于是副本落后了三条规则，守卫照样是绿的。
        改成拿真语料整个跑一遍：形状由数据给，不由我想。
        """
        import json
        p = ROOT / ".active_user"
        if not p.is_file():
            self.skipTest("没有活动用户")
        f = (ROOT / "users" / p.read_text(encoding="utf-8").strip()
             / "job_scraper" / "seen_jobs.json")
        if not f.is_file():
            self.skipTest("没有职位库")
        seen = _cli.seen_of(json.loads(f.read_text(encoding="utf-8")))
        bad = [e.get("url") for e in seen.values() if isinstance(e, dict)
               and doctor._via_headhunter(e) is not _cli.via_headhunter(e)]
        self.assertEqual(
            len(bad), 0,
            f"{len(bad)}/{len(seen)} 个岗两边判得不一样 —— "
            "doctor 那份副本落后了。它不 import 仓库模块是硬契约，"
            "所以规则要手抄过去；这条守卫就是抄漏的报警器")

    def test_the_word_lists_match(self):
        self.assertEqual(tuple(doctor.AGENCY_WORDS), tuple(_cli._AGENCY_WORDS))

    def test_doctor_points_at_the_new_home(self):
        src = (ROOT / "tools" / "doctor.py").read_text(encoding="utf-8")
        self.assertIn("与 `_cli._AGENCY_WORDS` 同值", src)
        self.assertIn("判据与 `_cli.via_headhunter` 同源", src)

    def test_doctor_still_imports_nothing_from_the_repo(self):
        """这条契约是那份副本存在的唯一理由。"""
        src = (ROOT / "tools" / "doctor.py").read_text(encoding="utf-8")
        self.assertIn("只用标准库，不 import 本仓库的任何模块", src)


class TheLiveCorpusStillDisagreesTheSameWay(unittest.TestCase):
    """有语料时确认那 66 个真的存在 —— 否则上面全是空谈。"""

    def test_the_raw_truthiness_would_differ(self):
        import json
        p = ROOT / ".active_user"
        if not p.is_file():
            self.skipTest("没有活动用户")
        f = (ROOT / "users" / p.read_text(encoding="utf-8").strip()
             / "job_scraper" / "seen_jobs.json")
        if not f.is_file():
            self.skipTest("没有职位库")
        seen = _cli.seen_of(json.loads(f.read_text(encoding="utf-8")))
        n = sum(1 for e in seen.values()
                if isinstance(e, dict)
                and bool(e.get("isHeadhunter")) is not _cli.via_headhunter(e))
        self.assertGreater(n, 0,
                           "裸真值和正本现在给出一样的结果 —— "
                           "语料变了的话，上面那些实测数要重新量")


if __name__ == "__main__":
    unittest.main()
