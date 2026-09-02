# -*- coding: utf-8 -*-
"""「催一条把几个岗一次问全，别发 2 条」—— 而那两个岗在两个 app 里。

`/job-outcome followup` 把同一家公司的多笔投递归成一组，提示合并成一条催。
理由是对的（同一个人在同一个对话里刷五条，对面看到的就是刷屏），
但归组的键**只有公司名**。

实测活动用户 2026-08-23，4 家有多笔投递的公司里 **3 家跨平台**：

    甲公司   5 笔   猎聘 4 · 智联招聘 1
    乙公司   2 笔   猎聘 1 · BOSS 直聘 1
    丙公司   2 笔   猎聘 1 · BOSS 直聘 1
    丁公司   2 笔   猎聘 2                ← 只有这家能合并

（公司名是他的投递记录，不进版本库 —— `test_no_maintainer_data_in_repo` 盯着。）

11 笔里 9 笔落在跨平台的那三家上。**猎聘和 BOSS 是两个 app、两个对话、
多半是两个人** —— 一条消息物理上发不到两边，那句建议对它们做不到。

（猎头/直招那一维本来就分开了：清单先按它切成两组，提示只在组内说。
平台是漏掉的第三维。）

顺带一件国内投递里真会咬人的事：**同一家公司走了两条渠道**（被猎头报备过、
自己又直投）在用人方那边会撞成重复候选人，谁来推、推荐费算谁的要掰扯，
处理不好两条都卡住。原来这件事在清单上完全看不见 —— 现在报出来，
但不替他决定先撤哪一条。
"""
import csv
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tests"))
import followups as F  # noqa: E402
from _srcscan import strip_comments  # noqa: E402

HEADER = ["date", "company", "sector", "role", "role_type", "channel", "status",
          "contact_person", "fit_rating", "notes", "cv_file",
          "cover_letter_file", "source"]


def _run(rows, today="2026-08-23"):
    """造一份台账跑真流程，抓 stdout。行里给 `source`，渠道靠它推。"""
    import contextlib
    import io
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        d = root / "users" / "u"
        d.mkdir(parents=True)
        with (d / "job_search_tracker.csv").open("w", encoding="utf-8",
                                                 newline="") as fh:
            w = csv.DictWriter(fh, HEADER)
            w.writeheader()
            for r in rows:
                w.writerow({k: r.get(k, "") for k in HEADER})
        (root / ".active_user").write_text("u", encoding="utf-8")
        buf = io.StringIO()
        old = F.ROOT
        try:
            F.ROOT = root
            with contextlib.redirect_stdout(buf):
                F.main(["--today", today])
        finally:
            F.ROOT = old
        return buf.getvalue()


def _row(company, role, url, date="2026-08-10"):
    return {"date": date, "company": company, "role": role,
            "status": "applied", "source": url}


LP = "https://www.liepin.com/job/{}.shtml"
BOSS = "https://www.zhipin.com/job_detail/{}.html"


class OneMessageCannotReachTwoApps(unittest.TestCase):
    def test_same_company_two_portals_is_not_one_cluster(self):
        out = _run([_row("示例科技", "AI产品经理", LP.format(1)),
                    _row("示例科技", "AI产品专家", BOSS.format("a"))])
        self.assertNotIn("投了 2 个岗", out,
                         "猎聘和 BOSS 上的两个岗被说成能一条催完")

    def test_same_company_same_portal_still_merges(self):
        """归组本身是对的，别把它一起改没了。"""
        out = _run([_row("示例科技", "AI产品经理", LP.format(1)),
                    _row("示例科技", "AI产品专家", LP.format(2))])
        self.assertIn("投了 2 个岗", out)
        self.assertIn("别发 2 条", out)

    def test_the_merge_note_names_the_portal(self):
        """「在这一组里」说不清是哪个对话框。说出平台名，他才知道去哪儿发。"""
        out = _run([_row("示例科技", "A", LP.format(1)),
                    _row("示例科技", "B", LP.format(2))])
        self.assertIn("这家你在猎聘上投了 2 个岗", out)

    def test_a_portal_split_counts_each_side_separately(self):
        """上表第一家那个形状：一边 4 个、另一边 1 个。"""
        rows = [_row("示例科技", f"岗{i}", LP.format(i)) for i in range(4)]
        rows.append(_row("示例科技", "岗X", "https://www.zhaopin.com/job/9"))
        out = _run(rows)
        self.assertIn("投了 4 个岗", out)
        self.assertNotIn("投了 5 个岗", out, "跨平台的被算进了同一条")

    def test_a_single_job_per_portal_gets_no_merge_note(self):
        out = _run([_row("示例科技", "A", LP.format(1)),
                    _row("示例科技", "B", BOSS.format("a"))])
        self.assertNotIn("别发", out)


class TheCrossChannelFactIsReported(unittest.TestCase):
    def test_it_says_the_other_portal(self):
        out = _run([_row("示例科技", "A", LP.format(1)),
                    _row("示例科技", "B", BOSS.format("a"))])
        self.assertIn("这家你还在BOSS 直聘上投过", out)
        self.assertIn("这家你还在猎聘上投过", out)

    def test_it_says_they_are_two_people(self):
        """光说「你还投过」不够 —— 要说清为什么不能合并。"""
        out = _run([_row("示例科技", "A", LP.format(1)),
                    _row("示例科技", "B", BOSS.format("a"))])
        self.assertIn("两边是两个联系人，各催各的", out)

    def test_it_warns_about_the_duplicate_candidate_problem(self):
        """这才是它值得占一行的理由：国内同一家走两条渠道会撞成重复候选人。"""
        out = _run([_row("示例科技", "A", LP.format(1)),
                    _row("示例科技", "B", BOSS.format("a"))])
        self.assertIn("撞成重复候选人", out)

    def test_it_does_not_decide_for_him(self):
        """先撤哪一条是他的事（涉及推荐费和已经建立的联系）。"""
        out = _run([_row("示例科技", "A", LP.format(1)),
                    _row("示例科技", "B", BOSS.format("a"))])
        for word in ("撤掉", "退掉", "应该先"):
            with self.subTest(word=word):
                self.assertNotIn(word, out)

    def test_one_portal_only_says_nothing(self):
        """绝大多数公司只投过一个平台 —— 那种情况下这一行必须不出现。"""
        out = _run([_row("示例科技", "A", LP.format(1)),
                    _row("示例科技", "B", LP.format(2))])
        self.assertNotIn("上投过", out)

    def test_it_is_said_once_per_side(self):
        """两边各说一次（他读到哪一行都该知道），但一边不许重复。"""
        rows = [_row("示例科技", f"岗{i}", LP.format(i)) for i in range(3)]
        rows.append(_row("示例科技", "岗X", BOSS.format("a")))
        out = _run(rows)
        self.assertEqual(out.count("这家你还在"), 2, "同一边说了不止一次")


class TheAnonymousGuardSurvives(unittest.TestCase):
    """脱敏串不是公司身份 —— 「某知名公司」在库里 158 次，是 158 家。
    这次改键不许把那道守卫带掉。"""

    def test_masked_names_never_cluster(self):
        out = _run([_row("某知名公司", "A", LP.format(1)),
                    _row("某知名公司", "B", LP.format(2))])
        self.assertNotIn("别发", out)
        self.assertNotIn("上投过", out)

    def test_the_key_still_asks_cluster_key(self):
        src = strip_comments((ROOT / "tools" / "followups.py")
                             .read_text(encoding="utf-8"))
        i = src.index("def _k(g, i):")
        self.assertIn("cluster_key(g[", src[i:i + 400])


class TheHeadhunterSplitIsStillTheOuterGrouping(unittest.TestCase):
    """平台是第三维。猎头/直招那一维由分组本身隔开，不该被搬进键里 ——
    搬进去就多切一刀，同一个猎头挂的两个岗会被拆开。"""

    def test_the_two_groups_still_exist(self):
        src = (ROOT / "tools" / "followups.py").read_text(encoding="utf-8")
        self.assertIn("猎头代招 —— 催顾问", src)
        self.assertIn("企业直招 —— 催 HR", src)

    def test_the_key_is_company_and_channel_only(self):
        code = strip_comments((ROOT / "tools" / "followups.py")
                              .read_text(encoding="utf-8"))
        i = code.index("def _k(g, i):")
        seg = code[i:i + 400]
        self.assertNotRegex(seg, r"headhunter|agency|猎头",
                            "猎头那一维被搬进了归组键")

    def test_the_reason_is_written_down(self):
        """一个多出来的元组元素，下一个人会当成手滑删掉。"""
        src = (ROOT / "tools" / "followups.py").read_text(encoding="utf-8")
        i = src.index("def _k(g, i):")
        seg = src[i:i + 1200]
        self.assertIn("平台必须进键", seg)
        self.assertRegex(seg, r"两个 app|物理上发不到两边")
        self.assertRegex(seg, r"3 家跨平台", "没留下实测的量")


class TheRealDataStillShowsIt(unittest.TestCase):
    """这条规矩是从他自己的台账里量出来的。哪天不成立了，这份判据要重写。"""

    def test_the_active_user_has_a_cross_portal_company(self):
        import tracker as T
        p = ROOT / ".active_user"
        if not p.is_file():
            self.skipTest("没有活动用户")
        u = p.read_text(encoding="utf-8").strip()
        csvp = ROOT / "users" / u / "job_search_tracker.csv"
        if not csvp.is_file():
            self.skipTest("这个用户还没有投递记录")
        by: dict = {}
        with csvp.open(encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                k = F.cluster_key(r.get("company", ""))
                if k:
                    by.setdefault(k, set()).add(T.channel_of(r))
        spread = {k: v for k, v in by.items() if len(v) > 1}
        if not spread:
            self.skipTest("这份台账里没有跨平台的公司了")
        # 跳过条件只保证「有公司跨了平台」。该断言的是**跟进真的分得开**：
        # `channel_of` 认不出时返回空串，而空串那一路不知道该往哪发 ——
        # 一家公司两笔投递里有一笔是空串，`len(v) > 1` 照样成立，
        # 于是这条会拿一个假的跨平台当支点。（判据见 `test_no_assertion_is_dead_on_arrival.py` 第 6 种）
        blind = {k: sorted(v) for k, v in spread.items() if "" in v}
        self.assertEqual(
            blind, {},
            f"{len(blind)} 家跨了平台，其中有一笔认不出是从哪投的 —— "
            f"那一笔的跟进没法定形态")


class CodeOfWithoutAnAnchorIsAnError(unittest.TestCase):
    """顺手堵上一个会让断言**永远绿**的坑（2026-08-23 扫出 4 处）。

    `code_of(rel, *anchors)` 要的是**相对路径字符串 + 至少一个锚点**。
    给它一个 `Path`、不给锚点，它照样返回 —— 返回空串。于是

        self.assertNotIn("st_mtime", code_of(ROOT / "tools" / "x.py"))

    查的是空字符串，无论源码怎么改都通过。这一族和
    `test_test_anchors_are_unambiguous` 同类：**不会红，所以最贵**。
    其中 `test_a_second_resume_is_not_invisible` 那条从写下那天起就一直空转。
    """

    def test_it_raises_instead_of_returning_empty(self):
        from _srcscan import code_of
        with self.assertRaises(TypeError):
            code_of("tools/followups.py")

    def test_the_message_points_at_the_replacement(self):
        from _srcscan import code_of
        try:
            code_of("tools/followups.py")
        except TypeError as e:
            self.assertIn("strip_comments", str(e))

    def test_it_still_works_with_an_anchor(self):
        from _srcscan import code_of
        seg = code_of("tools/followups.py", "def cluster_key(")
        self.assertIn("is_anonymous_employer", seg)
        self.assertNotIn("158 次", seg, "docstring 没剥掉")

    def test_no_test_calls_it_without_one(self):
        """新写的测试也不许这么用 —— 抛异常只在跑到那一行时才现形，
        而一个从没被执行到的分支照样能藏着它。"""
        # **本文件自己排除。** 上面那两条断言要真的这么调一次才验得了它抛不抛，
        # 而扫描器认得的正是那个形状 —— 连自己一起扫就是指着示范说「这里有 bug」。
        # 同 `test_test_anchors_are_unambiguous` 里那条「先剥注释」的理由。
        pat = re.compile(r"code_of\(([^,)]*)\)")
        bad = []
        for f in sorted((ROOT / "tests").glob("test_*.py")):
            if f.name == Path(__file__).name:
                continue
            for m in pat.finditer(strip_comments(f.read_text(encoding="utf-8"))):
                bad.append(f"{f.name}: code_of({m.group(1)})")
        self.assertEqual(bad, [],
                         "这些 code_of 没给锚点，返回空串，断言永远通过；"
                         "整份文件只剥注释请用 strip_comments(text)")


if __name__ == "__main__":
    unittest.main()
