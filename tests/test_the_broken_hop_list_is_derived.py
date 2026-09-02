# -*- coding: utf-8 -*-
"""「详情库有、职位库没有」的观察名单要算出来，不能手写。

## 手写名单只盖得住已经想到的字段

这个坑犯过两次，**两次的字段都不在那张手写名单上**：

    recruiterTitle    详情库 31 份有值、职位库 0 条   （2026-08-27 撞见）
    recruiterSurname  详情库  6 份有值、职位库 0 条   （2026-08-30 撞见）

两次都是靠人顺手比对才发现的 —— 一次是查「对面是 HR 还是用人方」，
一次是查「自检让用户去取的那个字段为什么是空的」。
而断链恰恰发生在**没想到**的字段上，所以名单必须是算出来的。

## 判据的四个条件，缺一不可

1. 详情库里有**真值**（`null` / 空串 / `"None"` 都不算）；
2. 职位库里 **0 条**有值；
3. **`MERGE_FIELDS` / `MERGE_RENAME` 没带它**（带了就是通的，只是源头还没出值）；
4. **有人读** —— 字段名出现在 `workflows/` `tools/` `web/src` 任一处。

第 4 条是 `MERGE_FIELDS` 自己的准入规矩（「它们的共同点是有消费者」）。
少了它就会报噪音：`fetched_by` / `fetched_date` 详情库各 151 份有值、
零消费者，搬过去只是多两列。

实测 2026-08-30：这样算出来**今天 0 条**（没有误报）。
"""
import pathlib
import sys
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tests"))
from _live import user_or_skip  # noqa: E402
import audit_pipeline as ap  # noqa: E402
import outreach_header as oh  # noqa: E402
import _cli  # noqa: E402

#: 造样例用的换行。写成常量而不是字面量，是因为这份文件被补丁脚本改过好几轮。
LF = chr(10)
import jd_store as st  # noqa: E402


def _hops(details, seen=None):
    return ap._broken_hops(seen or {}, details)


class ItCatchesTheOnesTheHandListMissed(unittest.TestCase):
    """两次真事故的形状，各回放一次。

    两个字段现在都**在**回填表里了，所以直接喂进去会被条件 3 正确排除。
    回放要把它从表里临时拿掉 —— 那正是 2026-08-27 / 08-30 当时的状态。
    """

    def _replay(self, field):
        saved = st.MERGE_FIELDS
        try:
            st.MERGE_FIELDS = tuple(f for f in saved if f != field)
            return _hops({"a": {"url": "u", field: "猎头顾问"}})
        finally:
            st.MERGE_FIELDS = saved

    def test_recruiter_title_shape(self):
        got = self._replay("recruiterTitle")
        self.assertTrue(got, "详情库有值、职位库没有、回填表没带 —— 一个字都没报")
        self.assertIn("recruiterTitle", got[0][2])
        self.assertIn("回填这一跳断了", got[0][2])

    def test_recruiter_surname_shape(self):
        got = self._replay("recruiterSurname")
        self.assertTrue(got, "第二次事故的形状同样抓不到")
        self.assertIn("recruiterSurname", got[0][2])

    def test_it_says_what_to_type(self):
        got = self._replay("recruiterTitle")
        self.assertIn("jd_store.py --merge --apply", got[0][2])


class TheFourConditionsAllHold(unittest.TestCase):
    def test_a_carried_field_is_not_a_broken_hop(self):
        """在回填表里就是通的 —— 源头还没出值是另一回事。"""
        self.assertIn("eduLevel", st.MERGE_FIELDS)
        self.assertEqual(_hops({"a": {"url": "u", "eduLevel": "本科"}}), [])

    def test_a_field_already_in_the_store_is_not_reported(self):
        got = _hops({"a": {"url": "u", "recruiterTitle": "猎头顾问"}},
                    seen={"k": {"url": "u", "recruiterTitle": "HR"}})
        self.assertEqual(got, [], "职位库里已经有了，还报断链")

    def test_a_field_nobody_reads_is_not_reported(self):
        """没有消费者的字段搬过去只是多一列噪音。"""
        got = _hops({"a": {"url": "u", "zzz_没人读过的字段名": "x"}})
        self.assertEqual(got, [])

    def test_a_null_is_not_a_value(self):
        """详情库里大量的键是 `null` —— 那不算「有值」。"""
        for v in (None, "", "None", [], {}):
            with self.subTest(v=v):
                self.assertEqual(_hops({"a": {"url": "u", "recruiterTitle": v}}), [])

    def test_fetch_provenance_is_not_reported(self):
        """`fetched_by` / `fetched_date` 详情库各 151 份有值、零消费者。"""
        for k in ("fetched_by", "fetched_date"):
            with self.subTest(k=k):
                self.assertEqual(_hops({"a": {"url": "u", k: "2026-08-30"}}), [])

    def test_the_stores_own_fields_are_not_reported(self):
        """详情里出现 `rank_score` 是导入残留，不是断链。"""
        for k in ("rank_score", "status", "first_seen"):
            with self.subTest(k=k):
                self.assertEqual(_hops({"a": {"url": "u", k: 60}}), [])


class ItIsQuietOnTheRealData(unittest.TestCase):
    def test_no_broken_hop_right_now(self):
        """今天 0 条 —— 一个永远红的审计会被当噪音略过。"""
        import _cli
        user = user_or_skip()
        ap._USER[:] = [user]
        try:
            seen, details = ap.load(user)
        except SystemExit:
            self.skipTest("没有职位库")
        got = ap._broken_hops(seen, details)
        self.assertEqual([r[2][:40] for r in got], [])


class ThreeJargonListsDifferOnPurpose(unittest.TestCase):
    """框架词表有三份（显示层 / 抬头 / 正文），两两不同 —— **那是有意的**。

    2026-08-30 一扫就把差异挑了出来，最扎眼的是 `业务域`：显示层有
    （→「行业经验」），正文那张没有，全库 **146 次**。看着像漏了一个词、
    一夜之间少报 145 个文件。

    逐条看过那 146 处：**145 处是地道中文**（「充换电运营这个业务域」
    「售后与车主服务这个业务域他没做过」），只有 1 处在打分算式里。
    加进来是报一个不存在的问题。

    判据是**各自的误伤代价**：

        显示层  最宽   换错了顶多把「业务领域」说成「行业经验」，意思还在
        抬头    次之   结构化字段，「能力边界」在那儿没有别的读法
        正文    最窄   散文，误报一次这条检查就会被整条忽略

    这条守卫钉住那几句理由 —— 没有它们，下一个人一扫又会把三份「统一」掉。
    """

    def test_the_doc_list_stays_narrow(self):
        for w in ("业务域", "能力边界", "信息质量"):
            with self.subTest(w=w):
                self.assertNotIn(w, [k for k, _p, _f in ap._DOC_JARGON],
                                 f"「{w}」在中文里读得通，收进正文表就是误报")

    def test_the_header_list_may_be_stricter(self):
        self.assertIn("能力边界", ap._HEAD_JARGON)

    def test_the_header_list_covers_the_doc_list(self):
        """正文表里的词，抬头那张一个都不该少 —— 抬头只会更严。"""
        doc = {k for k, _p, _f in ap._DOC_JARGON}
        missing = sorted(doc - set(ap._HEAD_JARGON))
        self.assertEqual(missing, [], f"抬头表漏了：{missing}")

    def test_the_reasons_are_written_down(self):
        src = (ROOT / "tools" / "audit_pipeline.py").read_text(encoding="utf-8")
        i = src.index("_DOC_EXCLUDE = {")
        seg = " ".join(src[max(0, i - 2000):i].split())
        self.assertIn("145 处是地道中文", seg)
        self.assertIn("三份词表不一样是有意的", seg)


class TheCheckerAndTheFixerShareOneList(unittest.TestCase):
    """**同一层的检查器和修理工分叉 = 把能自动做的事退回给人。**

    抬头这一层有两个消费者：`audit_pipeline` 报（`_HEAD_JARGON`）、
    `outreach_header` 改（`INTERNAL`）。2026-08-30 之前两张表各写各的，
    检查器八个词、修理工五对 —— 差的三个（`驾驶舱`、`读数`、`能力边界`）
    报得出来改不了。当天的收尾就是这样：审计说「1 份用了内部词（驾驶舱）」，
    修理工同一刻说「要改 0 份」，那一份只好落到人手上。

    正本合并到 `_cli.HEAD_JARGON` 之后，这条守卫钉住的是**行为**，
    不是两张表的字面相等：凡是检查器会报的词，修理工都得真能改掉。
    """

    def test_both_derive_from_the_shared_table(self):
        self.assertEqual(tuple(w for w, _rx, _f in _cli.HEAD_JARGON),
                         tuple(ap._HEAD_JARGON))
        self.assertEqual(tuple(w for w, _f in oh.INTERNAL),
                         tuple(ap._HEAD_JARGON))

    def test_the_doc_list_is_the_header_list_minus_a_named_set(self):
        """两张表的差集是代码里的一个常量，不是靠对着读看出来的。"""
        head = {w for w, _rx, _f in _cli.HEAD_JARGON}
        doc = {w for w, _rx, _f in ap._DOC_JARGON}
        self.assertEqual(head - doc, set(ap._DOC_EXCLUDE))

    def test_everything_the_checker_reports_the_fixer_can_fix(self):
        """逐词造一份抬头：检查器报得出来，修理工就得改得掉。"""
        for word, rx, fix in _cli.HEAD_JARGON:
            with self.subTest(word=word):
                head = LF.join(["# 岗 投递话术", "",
                                "- 渠道判定：**HR 直招**",
                                "- 备注：" + word, ""])
                self.assertTrue(re.search(rx, head), "匹配式扫不到「%s」" % word)
                new, notes = oh.fix_header(head, {})
                self.assertNotIn(word, new,
                                 "检查器报「%s」，修理工改不掉" % word)
                self.assertIn(fix, new)
                self.assertTrue(notes)

    def test_it_does_not_eat_a_real_chinese_word(self):
        """`硬门槛` 是中文本来就有的词（实测 7 处），不许被换成「硬性条件槛」。

        原来修理工用的是字面 `out.replace("硬门", "硬性条件")`，正踩这一脚；
        检查器那边也是字面 `in`。两处一起改成按主表的匹配式跑。
        """
        head = LF.join(["# 岗 投递话术", "", "- 备注：这个岗硬门槛很高", ""])
        new, notes = oh.fix_header(head, {})
        self.assertIn("硬门槛", new)
        self.assertEqual(notes, [])
        self.assertEqual([w for w, rx, _f in _cli.HEAD_JARGON
                          if re.search(rx, head)], [])


class TheReasonIsRecorded(unittest.TestCase):
    def test_the_two_incidents_are_named(self):
        src = (ROOT / "tools" / "audit_pipeline.py").read_text(encoding="utf-8")
        i = src.index("def _broken_hops(")
        seg = " ".join(src[i:i + 1800].split())
        self.assertIn("两次的字段都不在", seg)
        self.assertIn("手写名单只盖得住已经想到的字段", seg)


if __name__ == "__main__":
    unittest.main()
