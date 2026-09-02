"""面板的「这个岗到底投没投」判定，以及卡片身份的稳定性。

这三条都属于同一类后果：面板对着正确的数据给出错误的状态，而用户没有任何提示。
"""

import io
import re
import sys
import unittest
from contextlib import redirect_stderr
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))
import build_dashboard as bd  # noqa: E402


def _job(title, company="澜图科技", score=88):
    return {"title": title, "company": company, "status": "ranked", "rank_score": score}


class TrackerMatchingTests(unittest.TestCase):
    """台账行已经钉在某个 URL 上时，不许再用公司+岗位的子串模糊去认领别的职位。

    `_fuzzy` 是双向子串包含，而国内平台普遍给同一岗位加（社招）/（急招）后缀：
    「后端工程师」是「后端工程师（社招）」的子串，于是一个全新职位被标成已投、从待投区
    消失，ranked_urls 随之为空，下一步退化成没有 URL 的 `/job-apply <职位URL>`。
    """

    PINNED = [{"company": "澜图科技", "role": "后端工程师",
               "source": "https://portal.example/job/111", "status": "applied"}]

    def test_new_posting_is_not_claimed_by_a_pinned_row(self):
        row = bd.match_tracker(_job("后端工程师（社招）"),
                               "https://portal.example/job/222", self.PINNED)
        self.assertIsNone(row, "钉在 job/111 的台账行不该认领 job/222")

    def test_same_url_still_matches_exactly(self):
        row = bd.match_tracker(_job("后端工程师（社招）"),
                               "https://portal.example/job/111", self.PINNED)
        self.assertIsNotNone(row)

    def test_row_without_source_still_uses_fuzzy(self):
        """手工用 /job-outcome 记的行往往没有 source——模糊兜底必须对它们保留。"""
        manual = [{"company": "澜图科技", "role": "后端工程师", "source": ""}]
        row = bd.match_tracker(_job("后端工程师（社招）"),
                               "https://portal.example/job/222", manual)
        self.assertIsNotNone(row)

    def test_stage_reflects_it_end_to_end(self):
        seen = {"https://portal.example/job/222": {
            "url": "https://portal.example/job/222", "title": "后端工程师（社招）",
            "company": "澜图科技", "status": "ranked", "rank_score": 88}}
        model = bd.build_model(seen, [], self.PINNED, True, "me", ["me"])
        self.assertEqual(model["jobs"][0]["stage"], "ranked")
        self.assertEqual(model["counts"]["applied"], 0)

    # --- 同一 URL 挂多个职位（51job 实测）---
    SHARED = "https://jobs.51job.com/all/coBGdRMVU3UmwEaQZgAmQ.html"
    ROW_A = [{"company": "某公司", "role": "岗位甲", "source": SHARED, "status": "applied"}]

    def test_shared_url_row_does_not_claim_the_other_job(self):
        """51job 实测：同一详情 URL 下挂着两个不同职位。

        source URL 精确匹配只比 URL，于是投了甲、乙也被标成已投并从待投区消失——
        与上面「钉在别的 URL」是同一类后果，只是方向相反：这次是 URL 相同而岗位不同。
        """
        row = bd.match_tracker(_job("岗位乙", company="某公司"), self.SHARED, self.ROW_A)
        self.assertIsNone(row, "投了「岗位甲」不该把同 URL 的「岗位乙」也标成已投")

    def test_shared_url_row_still_matches_its_own_job(self):
        """控制用例：同 URL 且岗位对得上时必须照旧命中（修复前后均绿）。"""
        row = bd.match_tracker(_job("岗位甲", company="某公司"), self.SHARED, self.ROW_A)
        self.assertIsNotNone(row)

    def test_shared_url_tolerates_role_suffix(self):
        """控制用例：平台给岗位加后缀（（社招）等）时，同 URL 仍应命中。"""
        row = bd.match_tracker(_job("岗位甲（社招）", company="某公司"), self.SHARED, self.ROW_A)
        self.assertIsNotNone(row)

    def test_shared_url_matches_when_row_has_no_role(self):
        """控制用例：手工记的行可能没填 role——此时退回只比 URL，不能因缺列而漏匹配。"""
        rows = [{"company": "某公司", "role": "", "source": self.SHARED, "status": "applied"}]
        row = bd.match_tracker(_job("岗位乙", company="某公司"), self.SHARED, rows)
        self.assertIsNotNone(row)


class DuplicateAppDirTests(unittest.TestCase):
    """同一职位跑过两次 /job-apply（公司名归一化不同：腾讯 vs 腾讯科技）会产出两个目录。

    字典推导是「后者胜出」，会把前一个目录里已生成的 resume.pdf 与面试准备链接静默
    藏起来，且 unmatched_apps 也不报——面板声称材料存在，而它自己生成的 PDF 打不开。
    """

    def _app(self, dir_name, *, resume, preps=()):
        return {"dir": dir_name, "url": "https://a.example/1", "resume": resume,
                "outreach": {"url": "https://a.example/1", "greeting": "g",
                             "email_subject": "", "email_body": "", "wangshen": ""},
                "evaluation": None, "interview_preps": list(preps)}

    def test_richer_directory_wins_and_collision_is_reported(self):
        seen = {"https://a.example/1": {
            "url": "https://a.example/1", "title": "后端工程师",
            "company": "腾讯", "status": "ranked", "rank_score": 80}}
        apps = [self._app("腾讯_后端工程师", resume=True, preps=["interview_prep_1.md"]),
                self._app("腾讯科技_后端工程师", resume=False)]
        err = io.StringIO()
        with redirect_stderr(err):
            model = bd.build_model(seen, apps, [], True, "me", ["me"])
        self.assertTrue(model["jobs"][0]["app"]["resume"],
                        "带简历的那个目录应当胜出，否则 PDF 链接消失")
        self.assertIn("同一职位链接", err.getvalue())


if __name__ == "__main__":
    unittest.main()


class SchemeDoesNotBreakTheMatch(unittest.TestCase):
    """台账与职位库的 URL 协议不同，仍要认出是同一个岗。

    同一个岗在台账里存 `https://`、在库里存 `http://` 是真实会发生的——
    智联的页面锚点给 `http://`，而早前入库的同一批岗是 `https://`。

    **认不出的后果是把已投的岗重新摆回可投名单**，而重复投同一家正是求职
    最容易犯的错（`job-apply.md` 与那批「同岗重复挂牌」指路文件反复强调这条）。

    这个仓库为「同一个岗有多把钥匙」付过四次学费：裸 URL vs `url#职位名`（30 条重复）、
    同公司同职位名撞进一个材料目录（催办清不掉）、`validThrough` vs `deadline`
    （🔥 规则从没生效）、http vs https（20 个新岗里 4 个重复入库）。
    2026-08-20 查出这是第五处——`match_tracker` 的精确比对用的是原始 URL。
    """

    ROW = {"source": "https://www.zhaopin.com/jobdetail/CC1.htm",
           "company": "某公司", "role": "AI产品经理", "status": "applied"}

    def test_https_tracker_matches_http_job(self):
        job = {"company": "某公司", "title": "AI产品经理",
               "url": "http://www.zhaopin.com/jobdetail/CC1.htm"}
        self.assertIsNotNone(bd.match_tracker(job, job["url"], [self.ROW]),
                             "协议不同就认不出——已投的岗会被摆回可投名单")

    def test_http_tracker_matches_https_job(self):
        row = dict(self.ROW, source="http://www.zhaopin.com/jobdetail/CC1.htm")
        job = {"company": "某公司", "title": "AI产品经理",
               "url": "https://www.zhaopin.com/jobdetail/CC1.htm"}
        self.assertIsNotNone(bd.match_tracker(job, job["url"], [row]))

    def test_different_urls_still_do_not_cross(self):
        """归一化只抹协议，别把同公司的另一个岗也吃进来。"""
        job = {"company": "某公司", "title": "AI产品经理",
               "url": "https://www.zhaopin.com/jobdetail/CC2.htm"}
        self.assertIsNone(bd.match_tracker(job, job["url"], [self.ROW]),
                          "不同的岗被串成同一条投递记录了")

    def test_it_uses_the_canonical_normaliser(self):
        """别再手写 replace——归一化正本在 `_cli.norm_url`。"""
        src = (REPO_ROOT / "tools" / "build_dashboard.py").read_text(encoding="utf-8")
        seg = src.split("def match_tracker")[1].split("\ndef ")[0]
        self.assertIn("_cli.norm_url", seg)
        self.assertNotIn('replace("https://"', seg)
