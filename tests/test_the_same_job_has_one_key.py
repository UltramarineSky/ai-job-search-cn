# -*- coding: utf-8 -*-
"""跨源比链接，一律先剥协议 —— 这个仓库为「同一个岗有多把钥匙」付过五次学费。

`_cli.norm_url` 的 docstring 记着前四次，第五次是它自己修的（http vs https）。
它开头那句是：**去重前必须先过这一步**。可「先过这一步」的范围一直没被划清 ——
真正危险的不是库内部的比对（`jobs` 和 `seen` 是同一份数据，字节相同），
而是**跨源**的那几处：

    职位库（抓取器写）  ↔  台账 CSV（人手填）
    职位库（抓取器写）  ↔  材料目录里的 markdown（人写 / AI 写 / 从页面粘）

台账那条早就归一了（`match_tracker`）。材料目录那条有三处漏着：

    archive.collect_material_urls   对不上 → 出过材料的岗被归档，
                                    而那条规则的全部意思就是「花过工时的留在热库」
    doctor.orphan_materials         对不上 → 屏幕上报一个假的「材料接不回职位」，
                                    还指导用户去补一行明明存在的东西
    doctor.recoverable_link         同上，而且它返回的那个链接会被写进 outreach.md

实测 2026-08-23：284 个材料目录**当天全部原串就对得上**，所以这是潜伏缺陷、
不是现行错误。修它的理由是失败方式：静默、且都在「宁可漏认不可错认」的反面。

doctor 不许 import 仓库模块，所以那份 `norm_url` 是内联副本 —— 副本钉在这里。
"""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tests"))
import _cli  # noqa: E402
import archive as A  # noqa: E402
import doctor  # noqa: E402
from _srcscan import code_of  # noqa: E402


class TheCopyMatchesTheCanonical(unittest.TestCase):
    CASES = ("https://www.liepin.com/a/1.shtml", "http://www.liepin.com/a/1.shtml",
             "//www.liepin.com/a/1.shtml", "", None,
             "HTTPS://X/1", "https://x/1?a=1#b")

    def test_same_answer_everywhere(self):
        for u in self.CASES:
            with self.subTest(u=u):
                self.assertEqual(doctor.norm_url(u), _cli.norm_url(u))

    def test_the_two_schemes_collapse(self):
        a = doctor.norm_url("http://x/1")
        b = doctor.norm_url("https://x/1")
        self.assertEqual(a, b)
        self.assertNotIn("http", a, "协议没剥干净")

    def test_it_does_not_import_the_repo(self):
        """硬契约：doctor 要能在什么都没配好的机器上单文件裸跑。"""
        src = (ROOT / "tools" / "doctor.py").read_text(encoding="utf-8")
        self.assertNotRegex(src, r"(?m)^\s*(import|from)\s+_cli\b")


class EveryCrossSourceCompareIsNormalised(unittest.TestCase):
    """**只扫代码。** 这几段的注释里逐字引着「`http://`」「`https://`」，
    连注释一起扫等于禁止把理由写下来（本仓库栽过七次以上的坑）。"""

    SITES = [
        ("tools/archive.py", "def collect_material_urls(", "归档：材料目录那张表"),
        ("tools/doctor.py", "def orphan_materials(", "自检：接不回职位的目录"),
        ("tools/doctor.py", "def recoverable_link(", "自检：只差一行的那种"),
    ]

    def test_each_one_normalises(self):
        for rel, anchor, why in self.SITES:
            with self.subTest(where=why):
                seg = code_of(rel, anchor)
                self.assertIn("norm_url", seg, f"{why} 还在按原串比")

    def test_archive_keeps_materials_across_a_scheme_change(self):
        """出过材料的岗不许被归档 —— 哪怕材料目录记的是 http、库里是 https。"""
        keep = A.pick(
            seen={"k": {"url": "https://x/1", "status": "skipped",
                        "rank_verdict": "跳过", "skip_date": "2026-01-01"}},
            ustate={}, applied_keys=set(),
            material_urls={_cli.norm_url("http://x/1")},
            today=__import__("datetime").date(2026, 8, 23))
        self.assertEqual(keep, {}, "协议不同就把出过材料的岗归档了")

    def test_archive_still_archives_a_truly_bare_job(self):
        """**别把回退整条关掉**：没有材料的老岗照样要归。"""
        got = A.pick(
            seen={"k": {"url": "https://x/1", "status": "skipped",
                        "rank_verdict": "跳过", "skip_date": "2026-01-01"}},
            ustate={}, applied_keys=set(), material_urls=set(),
            today=__import__("datetime").date(2026, 8, 23))
        self.assertEqual(list(got), ["k"])


class TheHintStillReturnsAUsableLink(unittest.TestCase):
    def test_it_gives_back_the_original_not_the_stripped_form(self):
        """归一只用来比。返回剥了协议的地址，写进 `outreach.md` 就点不开。"""
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            ud = Path(td)
            d = ud / "documents" / "applications" / "示例科技_产品经理"
            d.mkdir(parents=True)
            (d / "posting.md").write_text("原始链接：http://x/1\n", encoding="utf-8")
            got = doctor.recoverable_link(ud, "示例科技_产品经理",
                                          {"k": {"url": "https://x/1"}})
        self.assertEqual(got, "https://x/1", f"返回的链接不可用：{got!r}")

    def test_two_candidates_still_mean_no_guess(self):
        """对上多个时不猜 —— 归一之后更容易撞上，这一条要留着。"""
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            ud = Path(td)
            d = ud / "documents" / "applications" / "示例科技_产品经理"
            d.mkdir(parents=True)
            (d / "posting.md").write_text(
                "原始链接：https://x/1\n另见 https://x/2\n", encoding="utf-8")
            got = doctor.recoverable_link(
                ud, "示例科技_产品经理",
                {"a": {"url": "https://x/1"}, "b": {"url": "https://x/2"}})
        self.assertEqual(got, "")


class OnRealDataNothingBroke(unittest.TestCase):
    def test_the_material_links_still_all_resolve(self):
        p = ROOT / ".active_user"
        if not p.is_file():
            self.skipTest("没有活动用户")
        ud = ROOT / "users" / p.read_text(encoding="utf-8").strip()
        sj = ud / "job_scraper" / "seen_jobs.json"
        if not sj.is_file():
            self.skipTest("还没抓过职位")
        raw = json.loads(sj.read_text(encoding="utf-8"))
        seen = raw.get("seen", raw)
        # 归一之后**只能匹配得更多**，绝不该更少。
        n = len(doctor.orphan_materials(ud, seen))
        self.assertEqual(n, 0, f"归一之后反而多出 {n} 个接不回的目录")


if __name__ == "__main__":
    unittest.main()


class FiftyOneJobPathPrefixesCollapse(unittest.TestCase):
    """同一个 51job 职位号的两种挂法要归到一个键。

    历史入库的是 `/all/<id>.html`，而 `cdp-portals.md` 记的浏览器抓取形态是
    `/shanghai-<区码>/<id>.html` —— 于是每跑一轮前程无忧，已经在库里的岗
    就再插一遍。实测 2026-08-28：热库加存档 2950 条里撞出 9 组，
    其中 8 组是当轮新插的。

    和 `norm_url` 原来记的那一课（`http://` vs `https://`，20 个新岗里 4 个
    重复入库）是同一个形状，只是换了个变量。
    """

    A = "https://jobs.51job.com/all/171700088.html"
    B = "https://jobs.51job.com/shanghai-mhq/171700088.html"

    def test_both_prefixes_give_one_key(self):
        self.assertEqual(_cli.norm_url(self.A), _cli.norm_url(self.B))

    def test_the_id_survives(self):
        """归一化不能把职位号也吃掉 —— 那是这个键唯一的身份。"""
        self.assertIn("171700088", _cli.norm_url(self.A))

    def test_different_ids_stay_apart(self):
        other = "https://jobs.51job.com/all/171700089.html"
        self.assertNotEqual(_cli.norm_url(self.A), _cli.norm_url(other))

    def test_other_sites_are_untouched(self):
        """只动 51job —— 别家的路径段是有意义的，收敛了会错并。"""
        for u in ("https://www.liepin.com/a/77587449.shtml",
                  "https://www.zhipin.com/job_detail/abc.html",
                  "https://www.zhaopin.com/jobdetail/CC1.htm"):
            with self.subTest(url=u):
                self.assertEqual(_cli.norm_url(u), u.replace("https://", "//"))

    def test_doctor_keeps_the_same_copy(self):
        import doctor
        for u in (self.A, self.B, "https://www.liepin.com/a/1.shtml"):
            with self.subTest(url=u):
                self.assertEqual(_cli.norm_url(u), doctor.norm_url(u))


class TheMobileSiteIsTheSameJob(unittest.TestCase):
    """`m.` / `wap.` 前缀是同一个岗，不是另一个。

    用户 2026-09-02 拿来一条要单独评的链接，是从微信里点开再复制的：

        //m.liepin.com/job/<id>.shtml?mscid=wx_h5_001

    埋点参数上一课已经剥掉了（2026-09-01 抓智联那次），**`m.` 没人管**。

    ## 后果不是重复入库，是材料成孤儿

    对着粘贴的 URL 跑 `/job-apply` 本来就不往库里新增条目
    （`job-apply.md` 收尾那条），所以不会多一行。真正的代价在**接不回去**：
    材料目录靠 `原始链接：<URL>` 认岗，而认的时候两边过的都是 `norm_url` ——
    库里 `//www.…`、目录里 `//m.…`，于是深评、开场白、邮件全出好了，
    总览页上那个岗还是「没有材料」，他也不知道为什么。

    ## 为什么收敛成 `www.` 而不是把子域剥掉

    照库里实测的形态：`www.liepin.com` 1127 条、`www.zhipin.com` 192、
    `www.zhaopin.com` 172 —— 三家的正规形态都带 `www.`。剥成裸主机反而
    谁也对不上。**51job 是例外**（正规形态 `jobs.51job.com`），所以它被
    排除在这条之外，维持现状。
    """

    WWW = "https://www.liepin.com/job/1982422325.shtml"
    MOBILE = "https://m.liepin.com/job/1982422325.shtml?mscid=wx_h5_001"

    def test_the_mobile_link_lands_on_the_same_key(self):
        self.assertEqual(_cli.norm_url(self.WWW), _cli.norm_url(self.MOBILE))

    def test_wap_too(self):
        self.assertEqual(_cli.norm_url("https://www.zhaopin.com/job/1.htm"),
                         _cli.norm_url("https://wap.zhaopin.com/job/1.htm"))

    def test_the_id_survives(self):
        """收敛主机不能顺手把职位号吃掉。"""
        self.assertIn("1982422325", _cli.norm_url(self.MOBILE))

    def test_different_jobs_stay_apart(self):
        other = "https://m.liepin.com/job/1982422326.shtml"
        self.assertNotEqual(_cli.norm_url(self.MOBILE), _cli.norm_url(other))

    def test_51job_is_deliberately_left_alone(self):
        """它的正规形态是 `jobs.`，收敛成 `www.` 会落到谁也不用的主机上。

        维持现状（各算各的键）**不是这次改动带来的退步** —— 改之前也是这样。
        """
        self.assertEqual(_cli.norm_url("https://m.51job.com/job/9.html"),
                         "//m.51job.com/job/9.html")

    def test_doctor_keeps_the_same_copy(self):
        """doctor 持的是副本（它不 import 仓库），两边必须一起改。"""
        import doctor
        for u in (self.WWW, self.MOBILE, "https://wap.zhaopin.com/job/1.htm",
                  "https://m.51job.com/job/9.html"):
            with self.subTest(url=u):
                self.assertEqual(_cli.norm_url(u), doctor.norm_url(u))

