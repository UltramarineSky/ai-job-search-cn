# -*- coding: utf-8 -*-
"""32% 的库带着「统招本科」这个字段值，而 04 说「仅限统招全日制」算硬门。

实测 2026-08-24 一个真实职位库（2637 个岗）：

    本科        908  (34%)
    统招本科    864  (32%)   ← 全部来自同一家平台，另外几家一个都没有
    硕士        245  ( 9%)
    学历不限    225  ( 8%)

864 家用人方不会不约而同地在 JD 里加同一句限定。**那是那家平台筛选项的一个
取值**，不是这 864 家各自提的要求。而 04 那张硬门表写着「『仅限统招全日制』算」
—— 照字段判，一次杀掉三分之一的库。

## 粗筛层早就判对了，只是那条规则执行者读不到

`tools/prescreen.py` 的注释写着：

> 「统招本科」与「本科」同级：候选人是不是「统招」往往有歧义
> （境外院校、专升本、非全日制都算不清），那属于判断，不属于机械匹配，
> 这里只标注、不否掉。

**但那是 Python 注释。** 做深评的执行者读的是 `04-job-evaluation.md`，
那儿此前只有相反的那半句。一个流程两条相反的规则，而只有一条他读得到 ——
这个仓库点过名的那一类。

## 第二件事：境外学历算不算「统招」

`04` 此前**全文 0 次**提到境外学历，而它对一整类候选人（海归）是决定性的：

    字面上不算   「统招」是国内普通高考招生体系的属性
    实际意图     写「统招全日制」的 JD 要排除的是非全日制那一类
                 （自考 / 成考 / 函授 / 网络教育 / 在职研究生）
    例外         国企 / 事业单位 / 考编 / 校招网申按字段做形式审查，对不上真过不了

所以判 FLAG 不判 FAIL，那几类形式审查的除外 —— 而且要写明是形式审查卡的，
不是学历不够。两种说法对他下一步该做什么完全不同。

## 为什么不另起一节

`04` 已经有「⚠️ 判据只认 JD 正文，不认列表页字段」。那条讲的是**字段与正文冲突**
时听谁的；这两条讲的是它没覆盖的两件事，所以挂在它底下，不再开一个平级标题。
"""
import collections
import json
import pathlib
import re
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
EVAL = (ROOT / "workflows" / "reference"
        / "04-job-evaluation.md").read_text(encoding="utf-8")
PRE = (ROOT / "tools" / "prescreen.py").read_text(encoding="utf-8")


def flat(s: str) -> str:
    s = " ".join(re.sub(r"^\s*(?:>|#:?)\s?", "", s, flags=re.M).split())
    return re.sub(r"(?<=[一-鿿，。；：、（）「」])"
                  r" +(?=[一-鿿，。；：、（）「」])", "", s)


class TheFieldValueIsNotARequirement(unittest.TestCase):
    def _seg(self) -> str:
        i = EVAL.index("#### 「统招本科」这个取值**本身**就不是一条要求")
        return flat(EVAL[i:EVAL.index("#### 境外学历（含港澳台）算不算「统招」", i)])

    def test_the_section_exists(self):
        self.assertIn("#### 「统招本科」这个取值**本身**就不是一条要求", EVAL)

    def test_it_hangs_under_the_existing_rule(self):
        """那条通则讲字段与正文冲突；这条讲它没覆盖的一步 —— 别开平级标题。"""
        a = EVAL.index("### ⚠️ 判据只认 JD 正文，不认列表页字段")
        b = EVAL.index("#### 「统招本科」这个取值**本身**就不是一条要求")
        c = EVAL.index("### 竞业限制**不是硬门**")
        self.assertLess(a, b)
        self.assertLess(b, c)

    def test_it_says_what_to_do(self):
        """只说「那不是要求」，执行者还得选一个判法。"""
        self.assertRegex(self._seg(), r"按「本科」判")

    def test_it_carries_the_measurement(self):
        s = self._seg()
        self.assertRegex(s, r"864 个岗（占全库 32%）")
        self.assertRegex(s, r"全部来自同一家平台")
        self.assertIn("2026-08-24", s)

    def test_it_states_the_cost_of_getting_it_wrong(self):
        self.assertRegex(self._seg(), r"一次杀掉三分之一的库")

    def test_it_says_the_gate_needs_a_quotable_line(self):
        """判据是「引不引得出原话」，不是字段取什么值。"""
        s = self._seg()
        self.assertRegex(s, r"能原样引出来的话")
        self.assertRegex(s, r"引不出原话就不是这道门")

    def test_it_lists_what_the_real_requirement_looks_like(self):
        s = self._seg()
        for w in ("自考", "成考", "函授", "网络教育"):
            with self.subTest(w=w):
                self.assertIn(w, s)

    def test_preferred_is_never_a_gate(self):
        """「985/211 优先」不是准入 —— 同「执业资格」那条。"""
        s = self._seg()
        self.assertRegex(s, r"带「优先」二字的一律不是门")

    def test_it_names_where_the_counter_rule_was_buried(self):
        """不写这句，下一个人会以为两层本来就该各判各的。"""
        s = self._seg()
        self.assertIn("tools/prescreen.py", s)
        self.assertRegex(s, r"那是 Python 注释，做深评的执行者读不到")


class TheOverseasDegreeCaseIsAnswered(unittest.TestCase):
    def _seg(self) -> str:
        i = EVAL.index("#### 境外学历（含港澳台）算不算「统招」")
        return flat(EVAL[i:EVAL.index("### 竞业限制**不是硬门**", i)])

    def test_the_section_exists(self):
        self.assertIn("#### 境外学历（含港澳台）算不算「统招」", EVAL)

    def test_it_answers_the_literal_question(self):
        """含糊过去，执行者只能自己猜 —— 而它对一整类人是决定性的。"""
        self.assertRegex(self._seg(), r"字面上不算")

    def test_it_says_what_the_credential_does_and_does_not_do(self):
        """中留服认证书解决层次等同，不解决「统招」这个属性。"""
        s = self._seg()
        self.assertRegex(s, r"层次等同")
        self.assertRegex(s, r"不会、也不能把一份境外学历变成「统招」")

    def test_it_names_the_real_intent(self):
        self.assertRegex(self._seg(), r"实际要排除的是非全日制那一类")

    def test_the_default_is_flag_not_fail(self):
        """FAIL 是永久出局。默认判死等于替他做了他自己没做的决定。"""
        self.assertRegex(self._seg(), r"判 FLAG，不判 FAIL")

    def test_it_reads_the_profile_value(self):
        self.assertIn("`profile` 教育背景的「学历认证」取值", EVAL)

    def test_the_formal_review_exception_is_named(self):
        """这才是真会卡的那一类 —— 只给「都判 FLAG」会让他白投一批。"""
        s = self._seg()
        for w in ("国企", "事业单位", "考编", "校招网申"):
            with self.subTest(w=w):
                self.assertIn(w, s)
        self.assertRegex(s, r"这一类判 FAIL")

    def test_the_exception_must_say_why(self):
        """「学历不够」和「形式审查过不了」，他下一步该做的事完全不同。"""
        s = self._seg()
        self.assertRegex(s, r"写明是\*\*形式审查\*\*卡的，不是学历不够")


class TheTableRowPointsAtIt(unittest.TestCase):
    """规则写在下面，而执行者先读到的是那张表 —— 不指过去就等于没写。"""

    def _row(self) -> str:
        return next(l for l in EVAL.splitlines() if l.startswith("| **学历与院校**"))

    def test_the_row_points_at_the_field_section(self):
        """引的那串要和小节标题的纯文本一字不差 —— 差一个引号样式，
        指路就落在一个不存在的名字上（第一版用了嵌套的『』，当场对不上）。"""
        cited = "「统招本科」这个取值本身就不是一条要求"
        self.assertIn(cited, self._row())
        # 小节标题带着强调星号，指路那句里没有 —— 剥掉再比，比的是那串字。
        titles = [ln.lstrip("# ").replace("**", "")
                  for ln in EVAL.splitlines() if ln.startswith("#### ")]
        self.assertIn(cited, titles, f"指向了一个不存在的小节名：{cited}")

    def test_the_row_mentions_the_overseas_case(self):
        self.assertIn("境外学历", self._row())

    def test_the_row_still_says_what_it_used_to(self):
        """指路是加的，原来那两条判据一个字不许动。"""
        r = self._row()
        self.assertIn("「本科及以上」这类通用要求不算硬卡", r)
        self.assertIn("**专业不符不算**", r)


class ThePrescreenLayerStillAgrees(unittest.TestCase):
    """这一节把粗筛的判据搬了上来。粗筛改了，两层又会分叉。"""

    def test_the_ladder_treats_them_as_equal(self):
        import sys
        sys.path.insert(0, str(ROOT / "tools"))
        import prescreen as ps
        self.assertEqual(ps.edu_rank("统招本科"), ps.edu_rank("本科"))

    def test_the_reason_is_still_recorded_there(self):
        i = PRE.index("EDU_LADDER = [")
        seg = flat(PRE[max(0, i - 700):i])
        self.assertRegex(seg, r"「统招本科」与「本科」同级")
        self.assertRegex(seg, r"只标注、不否掉")

    def test_the_generic_rule_it_hangs_under_survives(self):
        seg = flat(EVAL[EVAL.index("### ⚠️ 判据只认 JD 正文，不认列表页字段"):][:1200])
        self.assertRegex(seg, r"有 JD 正文时，一律以正文为准")
        self.assertRegex(seg, r"抓到 JD 之后必须复核")


class TheSignalItLeansOnIsReal(unittest.TestCase):
    """现算：那个取值真的占三分之一，真的只有一家平台给。"""

    def _seen(self):
        p = ROOT / ".active_user"
        if not p.is_file():
            self.skipTest("没有活动用户")
        f = (ROOT / "users" / p.read_text(encoding="utf-8").strip()
             / "job_scraper" / "seen_jobs.json")
        if not f.is_file():
            self.skipTest("还没有职位库")
        seen = json.loads(f.read_text(encoding="utf-8"))["seen"]
        if len(seen) < 500:
            self.skipTest("库太小，说不出话")
        return [e for e in seen.values() if isinstance(e, dict)]

    def test_the_value_is_a_large_share(self):
        rows = self._seen()
        n = sum(1 for e in rows if (e.get("eduLevel") or "") == "统招本科")
        self.assertGreater(
            n, len(rows) * 0.1,
            f"「统招本科」只剩 {n}/{len(rows)} —— 这一节引的 32% 过时了，去更新")

    def test_it_comes_from_exactly_one_portal(self):
        """**这是「它是平台取值不是要求」全部的证据。** 多家都给就要重看。

        ⚠️ **按平台数，不按 `portal` 字段的字面值数。** 一个平台可以有多条通道
        （猎聘就是 `liepin-search` + `liepin-browser`），同一家的两条通道给出
        同一个取值**恰恰是它属于平台字段的证据**，而原来那句 `Counter(portal)`
        会把它读成「两家平台都在给」，反过来推翻这一节。
        2026-08-25 撞上：猎聘浏览器通道第一次进常规轮次，这条当场红了，
        而证据本身一点没变（`liepin-search` 765 + `liepin-browser` 13，全是猎聘）。
        """
        rows = self._seen()
        sys.path.insert(0, str(ROOT / "tools"))
        from portal_budget import site_of
        c = collections.Counter(site_of(e.get("portal") or "?") for e in rows
                                if (e.get("eduLevel") or "") == "统招本科")
        self.assertEqual(
            len(c), 1,
            f"这个取值现在有多家平台在给：{c.most_common()} —— "
            f"那它可能真是要求，这一节的判据要重看")

    def test_the_deep_evals_did_not_mass_kill_on_it(self):
        """**现在没杀，是运气不是规则。** 哪天真开始杀，这条会红。"""
        rows = [e for e in self._seen()
                if (e.get("eduLevel") or "") == "统招本科"]
        killed = sum(1 for e in rows
                     if "FAIL" in str(e.get("rank_verdict") or "")
                     and "统招" in json.dumps(e.get("rank_breakdown") or {},
                                            ensure_ascii=False))
        self.assertLess(
            killed, len(rows) * 0.05,
            f"{killed}/{len(rows)} 个岗因为「统招」被判死 —— "
            f"04 这一节没被执行，去看 /job-rank 的提示里带没带它")


if __name__ == "__main__":
    unittest.main()
