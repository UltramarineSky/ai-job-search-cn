# -*- coding: utf-8 -*-
"""翻译腔换词换不掉 —— 词表管不住句子的搭法。

用户 2026-08-24 指着自己一份开场白里的一句说「这句话根本不符合中文习惯」：

    「把智能体的功能、性能指标和交互流程定清楚，是我做自己产品时天天在干的事；
     Agent 的原理和主流框架我不是听说过，是真在用。」

这句话里**没有一个词**在 `STYLE_BANS` 或 `GREETING_BANS` 上。毛病在句子怎么
搭的：先把动作卷成名词性主语（`Defining X is what I do` 的直译），再接一个
没人问过的辩解。所以判据只能是**正则**，不能是词表。

## 这一条的分量全在语料上

参照语料是同一个库里 **1486 份真人 JD**（国内 HR 与用人方写的中文，
面向同一批读者）。逐份查、按份计数：

    「…，是我…的事」        JD 0 份   236 份 outreach 里 13 份
    「正是我在做的」          JD 0 份   236 份 outreach 里  5 份
    「我不是 A，是 B」        JD 0 份   236 份 outreach 里  3 份

（审计只扫 200 字开场白那一块，所以它报的是 11 / 5 / 2。）

**在母语商务写作里 0 次、在我们这儿 13 次，那不是风格偏好，是口音。**

## 差点写成错的那一条

第一版的辩解句正则没要求主语是「我」。拿去比：**1486 份里命中 23 份**，
全是用人方给岗位划边界（`不是执行者，而是`、`不是传统销售执行岗，而是`）——
母语里好好的一个修辞。钉死主语之后 JD 归 0。**差一个「我」字，23 份误报变 0。**

这一课本仓库栽过同类：判据要拿真人语料对一遍，不能凭「读着像翻译腔」就上。
"""
import json
import pathlib
import re
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import _cli  # noqa: E402

AUDIT = (ROOT / "tools" / "audit_pipeline.py").read_text(encoding="utf-8")
WS = (ROOT / "workflows" / "reference"
      / "03-writing-style.md").read_text(encoding="utf-8")

BAD = ("把智能体的功能、性能指标和交互流程定清楚，是我做自己产品时天天在干的事；"
       "Agent 的原理和主流框架我不是听说过，是真在用。")
GOOD = ("智能体的功能、指标、交互流程我天天在定，都是自己产品上跑出来的；"
        "Coze、Dify、LangChain 是日常工具。")


def flat(s: str) -> str:
    s = " ".join(re.sub(r"^\s*(?:>|#:?)\s?", "", s, flags=re.M).split())
    return re.sub(r"(?<=[一-鿿，。；：、（）「」])"
                  r" +(?=[一-鿿，。；：、（）「」])", "", s)


class TheUsersSentenceIsCaught(unittest.TestCase):
    def test_both_patterns_fire_on_it(self):
        got = {c for c, _ in _cli.greeting_hits(BAD)}
        self.assertIn("翻译腔（动作当主语）", got)
        self.assertIn("替对方先辩解", got)

    def test_the_rewrite_is_clean(self):
        """改法要真能过 —— 否则规则只会说「不行」，不会说「那怎么写」。"""
        self.assertEqual(_cli.greeting_hits(GOOD), [])

    def test_no_word_list_would_have_caught_it(self):
        """这一条存在的全部理由：**词表看不见它**。

        换词换不掉的东西，加进词表也拦不住 —— 这里钉住那个前提，
        免得下一个人把三条正则「简化」成三个词。
        """
        words = [w for tbl in (_cli.GREETING_BANS, _cli.STYLE_BANS)
                 for ws in tbl.values() for w in ws]
        self.assertEqual([w for w in words if w in BAD], [])

    def test_it_reaches_the_user_facing_line(self):
        """面板复制按钮旁那条提示要认出来 —— 他复制的就是这段话。"""
        said = " ".join(_cli.greeting_problems(BAD))
        self.assertIn("翻译腔", said)


class TheDefensivePatternNeedsTheSubject(unittest.TestCase):
    def test_a_jd_style_contrast_is_not_flagged(self):
        """`不是执行者，而是共建者` 是母语里好好的修辞，不许报。"""
        for s in ("我们要的不是执行者，而是共建者。",
                  "这不是传统销售执行岗，而是解决方案岗。",
                  "不是功能的堆砌者，而是产品的定义者。"):
            with self.subTest(s=s):
                self.assertEqual(_cli.greeting_hits(s), [])

    def test_the_first_person_one_is_flagged(self):
        self.assertIn("替对方先辩解",
                      {c for c, _ in _cli.greeting_hits("我不是听说过，是真在用。")})

    def test_the_self_certifying_one_is_flagged(self):
        """第三条单独钉一次 —— 变异测试实测：把它换成永不匹配的东西，
        整份测试仍然全绿（`our_own_copy_still_has_them` 只要任意一条命中）。"""
        self.assertIn("翻译腔（自我认证）",
                      {c for c, _ in _cli.greeting_hits("这正是我在做的。")})

    def test_the_subject_is_pinned_in_the_pattern(self):
        """去掉那个「我」就是 23 份误报 —— 钉在正则本身上，改动一眼看得见。"""
        self.assertTrue(_cli.STYLE_PATTERNS["替对方先辩解"].startswith("我不是"))


class ThePatternsCoexistWithTheWordLists(unittest.TestCase):
    def test_the_categories_do_not_collide(self):
        """撞名了审计那行分档会把两类的份数加在一起，而两类判据不同。"""
        for tbl, name in ((_cli.GREETING_BANS, "GREETING_BANS"),
                          (_cli.STYLE_BANS, "STYLE_BANS")):
            for cat in _cli.STYLE_PATTERNS:
                with self.subTest(cat=cat, tbl=name):
                    self.assertNotIn(cat, tbl)

    def test_every_pattern_compiles(self):
        for cat, pat in _cli.STYLE_PATTERNS.items():
            with self.subTest(cat=cat):
                re.compile(pat)

    def test_the_category_names_are_plain_chinese(self):
        """类别名会原样印给用户（「「…」是<类别>」）—— 别搬语言学术语进来。

        判据同 `AGENTS.md`「内部词不要搬到台面上」。
        """
        for cat in _cli.STYLE_PATTERNS:
            with self.subTest(cat=cat):
                self.assertNotIn("名词化", cat)
                self.assertNotRegex(cat, r"[A-Za-z]")

    def test_clean_text_stays_clean(self):
        """整段没毛病的话不许被这三条正则蹭到。"""
        self.assertEqual(
            _cli.greeting_hits("我在字节做过三年推荐算法，带过 6 人的团队。"), [])


class TheAuditNamesTheRightSection(unittest.TestCase):
    def test_it_cites_the_sentence_section_not_the_word_list(self):
        """句式那三条的出处是 `03` 里**另一节** —— 指到词表那节，
        他会在里面找一个查不到的东西，然后以为是误报。"""
        i = AUDIT.index("hit_pat = [k for k in by")
        seg = AUDIT[i:i + 600]
        self.assertIn("03-writing-style.md 的「句式：中文不这么说」", seg)

    def test_it_only_cites_it_when_hit(self):
        self.assertIn("if hit_pat else", AUDIT)

    def test_the_section_it_points_at_exists(self):
        self.assertIn("## 句式：中文不这么说", WS)

    def test_the_other_two_sources_survive(self):
        i = AUDIT.index("hit_pat = [k for k in by")
        seg = AUDIT[i - 400:i + 600]
        self.assertIn("06-outreach-templates.md 渠道 1 那张表", seg)
        self.assertIn("03-writing-style.md 的「AI 味清单」", seg)


class TheDocumentCarriesTheEvidence(unittest.TestCase):
    def _seg(self) -> str:
        i = WS.index("## 句式：中文不这么说")
        return flat(WS[i:WS.index("## 语气", i)])

    def test_it_shows_both_corpora(self):
        seg = self._seg()
        self.assertIn("1486 份真人 JD", seg)
        self.assertIn("236 份 outreach", seg)

    def test_it_separates_the_two_scopes(self):
        """审计只扫 200 字那一块，报的数比整份少 —— 不说清楚，
        下一个人拿审计输出对不上这张表，会以为其中一个是错的。"""
        seg = self._seg()
        self.assertIn("它只扫 200 字开场白那一块", seg)

    def test_it_states_the_conclusion(self):
        self.assertRegex(self._seg(), r"不是风格偏好，是口音")

    def test_it_records_the_near_miss(self):
        seg = self._seg()
        self.assertRegex(seg, r"1486 份真人 JD 里命中 23 份")
        self.assertRegex(seg, r"差一个「我」字，23 份误报变 0 份")

    def test_it_gives_the_rewrite_not_just_the_ban(self):
        """只说「别这么写」的规则，执行者只会换个说法再踩一次。"""
        seg = self._seg()
        self.assertIn("改成", seg)
        self.assertIn("动词打头", seg)

    def test_it_carries_the_date(self):
        self.assertIn("2026-08-24", self._seg())


class TheNumbersAreRecomputedNotRemembered(unittest.TestCase):
    """文里那几个数是**现算**的 —— 语料变了它就该跟着变，别成为化石。"""

    def _corpus(self):
        p = ROOT / ".active_user"
        if not p.is_file():
            self.skipTest("没有活动用户")
        base = ROOT / "users" / p.read_text(encoding="utf-8").strip()
        det = base / "job_scraper" / "details"
        if not det.is_dir():
            self.skipTest("这位用户还没有 JD 语料")
        jds = []
        for f in det.glob("*.json"):
            try:
                d = json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                continue
            for e in (d if isinstance(d, list) else [d]):
                t = (e.get("jd") or e.get("description") or e.get("text") or "")
                if t.strip():
                    jds.append(t)
        outs = [q.read_text(encoding="utf-8") for q in base.rglob("outreach.md")]
        if len(jds) < 200 or len(outs) < 50:
            self.skipTest("语料太少，比不出来")
        return jds, outs

    def test_the_patterns_are_absent_from_native_writing(self):
        """真人 JD 里出现得多，就说明它是正常中文，这条规则该撤或该收窄。"""
        jds, _ = self._corpus()
        for cat, pat in _cli.STYLE_PATTERNS.items():
            r = re.compile(pat)
            n = sum(1 for t in jds if r.search(t))
            with self.subTest(cat=cat):
                self.assertLessEqual(
                    n, len(jds) * 0.005,
                    f"「{cat}」在 {len(jds)} 份真人 JD 里命中 {n} 份 —— "
                    f"那它多半是正常中文，不是毛病")

    def test_every_pattern_is_still_alive(self):
        """**逐条查，不是「任意一条命中」。**

        第一版写成 `any(...)`，于是把其中一条换成永不匹配的字符串，
        整份测试照样全绿 —— 一条死正则可以在库里躺着不被发现。

        ## 判据 2026-09-02 换过：从「语料里还踩着」换成「正则还咬得动」

        原来断的是「这条句式在我们自己的开场白里命中 > 0」，理由写着
        「一条不再命中时它就是死代码」。**那个推理在语料会被清干净之前成立。**

        那天先后清掉了 129 + 24 + 20 处，`替对方先辩解` 和 `翻译腔（自我认证）`
        当场归零，这条测试红在 `0 not greater than 0` 上 —— 而它们一个都没死，
        是**语料变干净了**。同一天 `/job-auto` 还接上了写盘前的闸门
        （`tools/check_outreach.py`），从此干净是常态，按旧判据这条会一直红。

        兄弟条目 `test_a_partial_check_says_so.py::test_the_word_list_is_not_dead`
        当天为同一件事改过一次 —— **两个 0 的来源不一样**：一个是查过并改干净了，
        一个是压根没查。分不开的时候，就别拿语料当对照组。

        所以改成直接验**接线还通**：拿这条正则自己文档里的反例喂进去，
        它必须咬得住。语料那个数仍然算，但只印出来当观察，不做断言。
        """
        _, outs = self._corpus()
        #: 每条句式在 `03-writing-style.md`「句式」那张表里逐字列过的反例。
        #: **必须抄那张表，不许自己编** —— 编一个「看着不对」的句子，
        #: 测的是我的语感，不是规则有没有在执行。
        SPECIMEN = {
            "翻译腔（动作当主语）": "把智能体的指标定清楚，是我天天在干的事。",
            "替对方先辩解": "Agent 的主流框架我不是听说过，是真在用。",
            "翻译腔（自我认证）": "平台横向对比，这正是我在做的。",
            "拿年头自证": "Agent 产品定义是我这三年一直在做的事。",
        }
        self.assertEqual(sorted(SPECIMEN), sorted(_cli.STYLE_PATTERNS),
                         "STYLE_PATTERNS 加减过条目，反例表要跟着改")
        for cat, pat in _cli.STYLE_PATTERNS.items():
            with self.subTest(cat=cat):
                self.assertRegex(SPECIMEN[cat], pat,
                                 f"「{cat}」连自己文档里的反例都咬不住 —— 接线断了")
                n = sum(1 for t in outs if re.search(pat, t))
                print(f"    {cat}：语料里现命中 {n}/{len(outs)}")


if __name__ == "__main__":
    unittest.main()
