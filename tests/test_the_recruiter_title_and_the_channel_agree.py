# -*- coding: utf-8 -*-
"""招聘者头衔写着「猎头」，而 `isHeadhunter` 记成直招 —— 两个字段互相矛盾。

`isHeadhunter` 决定话术抬头写「猎头代招」还是「企业直招」，而那半句决定
**第二轮怎么说话**（`06` 渠道判定：猎头问薪资与到岗时间要直接答，
HR 直招不主动展开）。记反了，开场白就对着用人方说话 —— 正是
「猎头岗的开场白对着顾问说「贵司」」那条报的错，只是根因在字段上。

实测活动用户 2026-08-30：两个字段都在的 152 条里 **4 条**这样，
四个都还没出材料、三个还能发。**现在改比出完材料再改便宜。**

## 判据不对称，检查也得不对称

「头衔里有『猎头』」⇒ 一定是代招，这条硬。反过来不成立：实测 6 条
`isHeadhunter=True` 的头衔是「顾问 · 某人力资源公司」「Consultant · 某某人力
资源」，甚至「人力资源/HR · 某管理咨询公司」—— **那些人确实在猎头公司里**，
字段是对的，头衔里只是没有「猎头」二字。

第一版的检测是双向的，当场把那 6 条一起报成了错。这条守卫钉住它别再变回双向。

## 2026-08-30：被守的那条检查换了问题

原来它问「盘上那个字段对不对」，收尾据此给的动作是 4 次手工 `/job-apply`。
可这件事根本不必手工 —— 硬规则搬进 `_cli.via_headhunter` 之后，
面板、`doctor`、`followups`、话术抬头四处一起跟着对，盘上那个字段错不错
已经没有消费者。检查改成问「**推导有没有覆盖住**」：真语料上恒为 0，
哪天有人把某一处的规则改回去它就红。

所以下面这几条也跟着换了口径：喂进去的样例要能让**三处推导**都答对，
而不是让「两个字段互相矛盾」这件事被报出来。上面那段不对称的实测证据
一个字没变 —— 换的是检查的问题，不是判据。
"""
import pathlib
import sys
import unittest
import unittest.mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import audit_pipeline as ap  # noqa: E402

SRC = (ROOT / "tools" / "audit_pipeline.py").read_text(encoding="utf-8")


def _run(rows):
    return ap.check_recruiter_title_contradicts_the_channel(
        {str(i): r for i, r in enumerate(rows)}, {})


class ItFiresWhenTheDerivationRegresses(unittest.TestCase):
    """真语料上恒为 0 —— 所以这里用打了补丁的判据造回退。"""

    def test_it_fires_when_via_headhunter_forgets_the_title(self):
        import unittest.mock
        import _cli
        rows = [{"url": "https://x/1", "title": "AI产品经理",
                 "recruiterTitle": "上海某某人力资源 · 猎头顾问",
                 "isHeadhunter": False}]
        with unittest.mock.patch.object(
                _cli, "via_headhunter",
                lambda e: bool(e.get("isHeadhunter"))):
            got = _run(rows)
        self.assertTrue(got, "推导把头衔那条丢了，一个字都没报")
        self.assertIn("猎头", got[0][1])

    def test_it_fires_when_counterpart_forgets_the_title(self):
        """**这一处最贵。** 头衔是「某某人力资源 · 猎头顾问」时，
        公司名里的「人力」会撞上 `COUNTERPART_HR`，把猎头判成 HR ——
        于是 `/job-apply` 第 1.5 步给猎头写 HR 直招版的话术。"""
        import unittest.mock
        import _cli
        rows = [{"url": "https://x/1", "title": "AI产品经理",
                 "recruiterTitle": "上海某某人力资源 · 猎头顾问",
                 "isHeadhunter": False}]
        with unittest.mock.patch.object(
                _cli, "counterpart_of", lambda t, hh=None: "HR"):
            got = _run(rows)
        self.assertTrue(got, "counterpart_of 判成 HR 了，一个字都没报")
        self.assertIn("counterpart_of", got[0][2])

    def test_it_names_the_field_that_decides_the_conversation(self):
        """不写这句，读的人不知道为什么值得改一个「元数据」。"""
        import unittest.mock
        import _cli
        with unittest.mock.patch.object(
                _cli, "via_headhunter",
                lambda e: bool(e.get("isHeadhunter"))):
            got = _run([{"url": "https://x/1", "title": "AI产品经理",
                         "recruiterTitle": "猎头顾问", "isHeadhunter": False}])
        self.assertIn("第二轮怎么说话", got[0][2])

    def test_it_is_silent_when_the_derivation_works(self):
        """真判据下这条恒为 0 —— 那 4 个岗不再需要任何手工动作。"""
        got = _run([{"url": "https://x/1", "title": "AI产品经理",
                     "recruiterTitle": "上海某某人力资源 · 猎头顾问",
                     "isHeadhunter": False}])
        self.assertEqual(got, [], "推导已经认得了，却还在催人改")


class ItDoesNotFireTheOtherWay(unittest.TestCase):
    """**这几条是实测里的真实形状，一条都不许被报成错。**"""

    OK = ("顾问 · 普仕英才（北京）管理咨询有限公司",
          "Consultant · 伯揽人力资源（上海）有限公司",
          "人力资源/HR · 湖北格尔企业管理咨询有限公司",
          "高级顾问 · 艺寻人力资源管理（上海）有限公司")

    def test_agency_titles_without_the_word_are_not_flagged(self):
        for t in self.OK:
            with self.subTest(t=t):
                got = _run([{"url": "https://x/1", "title": "岗",
                             "recruiterTitle": t, "isHeadhunter": True}])
                self.assertEqual(got, [], f"把「{t}」报成了矛盾")

    def test_a_plain_hr_title_on_a_direct_job_is_fine(self):
        for t in ("HR", "HRBP", "招聘经理", "人力资源总监"):
            with self.subTest(t=t):
                got = _run([{"url": "https://x/1", "title": "岗",
                             "recruiterTitle": t, "isHeadhunter": False}])
                self.assertEqual(got, [])

    def test_a_missing_field_is_handled_by_the_title(self):
        """字段缺席时头衔自己就够了 —— 判得出来，就没什么可报的。

        这条原来叫「缺不是错」：那时检查问的是「两个字段矛不矛盾」，
        一边缺席自然谈不上矛盾。现在它问的是「推导覆盖住没有」，
        而 `via_headhunter` 认得头衔里的「猎头」二字，所以照样是 0 ——
        **同一个断言，理由换了一个。**
        """
        for hh in (None,):
            with self.subTest(hh=hh):
                got = _run([{"url": "https://x/1", "title": "岗",
                             "recruiterTitle": "猎头顾问", "isHeadhunter": hh}])
                self.assertEqual(got, [], "把「判不了」报成了「记反了」")

    def test_no_title_no_claim(self):
        got = _run([{"url": "https://x/1", "title": "岗", "isHeadhunter": False}])
        self.assertEqual(got, [])


class TheAdviceOnlyPromisesWhatIsThere(unittest.TestCase):
    """「岗库里就有，直接取」—— 这句话得先是真的。

    自检的「投递记录里有人读、没人写的列」原来无条件写着
    「猎聘的岗库里就有（`recruiterSurname`），直接取」。实测 2026-08-30：
    岗库 1839 条里有值的 **0 条**（详情库里真有值的 6 份，而 `jd_store` 的
    回填表里没有这个字段，搬不过去 —— 同日已补进 `MERGE_FIELDS`）。

    让人去「直接取」一个空字段，他取不到、以为自己弄错了，
    **下次连这条建议一起不信**。现在按库里实际有几个说。
    """

    def test_it_says_none_when_there_are_none(self):
        got = ap._surname_note({"a": {"url": "u"}})
        self.assertIn("一个姓都没有", got)
        self.assertNotIn("直接取", got)

    def test_it_says_how_many_when_there_are_some(self):
        """**不给台账时只说库里那个数，并且明说它是库里的。**

        措辞 2026-09-01 改过：原来无论如何都写「有姓的 N 个直接取」，
        而这句话接在「台账 88 行一个都没填」后面 —— 读的人会当成
        「这 88 行里有 N 行能补」。实测那两个数差 6 倍
        （库里 6 个姓，台账里对得上 1 行）。判据见
        `test_count_what_he_can_actually_fill`。
        """
        got = ap._surname_note({"a": {"url": "u", "recruiterSurname": "杨"},
                                "b": {"url": "v"}})
        self.assertIn("1 个姓", got)
        self.assertNotIn("行能从", got, "没给台账还敢说「几行能补」")

    def test_a_null_is_not_a_surname(self):
        """详情库里 44 份那个键是 `null` —— 那不算「有」。"""
        got = ap._surname_note({"a": {"url": "u", "recruiterSurname": None},
                                "b": {"url": "v", "recruiterSurname": "  "}})
        self.assertIn("一个姓都没有", got)

    def test_the_backfill_hop_is_connected(self):
        """字段搬得过去，那句话才有可能变成真的。"""
        import jd_store
        self.assertIn("recruiterSurname", jd_store.MERGE_FIELDS,
                      "详情库里有、职位库里搬不过去 —— 这一跳还断着")


class TheCheckStaysOneDirectional(unittest.TestCase):
    def test_the_source_only_tests_one_direction(self):
        i = SRC.index("def check_recruiter_title_contradicts_the_channel(")
        seg = SRC[i:SRC.index(chr(10) + "def ", i)]
        body = seg[seg.index('"""', seg.index('"""') + 3) + 3:]
        self.assertIn('"猎头" not in title', body)
        self.assertNotIn("HRBP", body, "又加了反方向的判据")

    def test_the_reason_for_one_direction_is_recorded(self):
        i = SRC.index("def check_recruiter_title_contradicts_the_channel(")
        seg = " ".join(SRC[i:i + 2200].split())
        self.assertIn("那些人确实在猎头公司里", seg)
        self.assertIn("判据不对称的时候，检查也得不对称", seg)


if __name__ == "__main__":
    unittest.main()
