# -*- coding: utf-8 -*-
"""境外学历要办中留服认证，而这件事全流程一次都没被提过。

实测 2026-08-24：全库搜 `离职证明` / `学信网` / `学历认证` / `身份证` ——
`离职证明` 只在 `job-offer.md` Step 4 出现一次，其余三个 **0 命中**。

## 为什么这一件值得单独占一格

内地学历在学信网上查得到，一份《学历证书电子注册备案表》当场就能下。
**境外学历（含港澳台）学信网收录不到**，国内单位普遍要教育部留学服务中心
出的《国外学历学位认证书》—— 入职、落户、考编与事业单位报名都可能卡在它上面。

而它和「接之前先确认这几件」里别的条目**不是一回事**：

    别的条目   问清楚就行（竞业签没签、offer 是不是书面的、入职日期谈没谈）
    这一条     **要排队** —— 按工作日算，不是拿到 offer 当天能补的

等 HR 要材料时才开始办，入职日期就得往后推 —— **而那时候他已经辞职了**。
这是这份资料里少数几个**越早知道越值钱**的事实。

## 触发条件是现成的，不用新造

`profile.example` 的「教育背景」表里本来就有「层次」一栏，取值里写着
`境外院校`。所以这一条是**按资料触发**的，不是给某一个人写死的 ——
内地学历的用户从头到尾看不到它（凭空多一问，等于把内地用户都拉去答一个
与他无关的问题）。

## 三处一起接，缺一处就断

    profile.example   存这个事实（`学历认证` 那一行）
    job-setup.md      层次是境外时多问一句
    job-offer.md      点头之前查一遍
"""
import contextlib
import pathlib
import re
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import audit_pipeline as ap  # noqa: E402
TPL = (ROOT / "profile.example" / "candidate.md").read_text(encoding="utf-8")
SETUP = (ROOT / "workflows" / "job-setup.md").read_text(encoding="utf-8")
OFFER = (ROOT / "workflows" / "job-offer.md").read_text(encoding="utf-8")


def flat(s: str) -> str:
    s = " ".join(re.sub(r"^\s*(?:>|#:?)\s?", "", s, flags=re.M).split())
    return re.sub(r"(?<=[一-鿿，。；：、（）「」])"
                  r" +(?=[一-鿿，。；：、（）「」])", "", s)


@contextlib.contextmanager
def _profile(text):
    """临时把活动用户的资料换成 `text`（`None` = 当作没建过档），跑完还原。

    不写用户真实资料 —— 造一个只在本次测试里存在的用户名，测完删掉。
    """
    name = "_t_foreign_degree"
    d = ROOT / "users" / name / "profile"
    old = list(ap._USER)
    try:
        if text is not None:
            d.mkdir(parents=True, exist_ok=True)
            (d / "candidate.md").write_text(text, encoding="utf-8")
        ap._USER[:] = [name]
        yield d
    finally:
        ap._USER[:] = old
        f = d / "candidate.md"
        if f.is_file():
            f.unlink()
        for x in (d, d.parent):
            if x.is_dir() and not any(x.iterdir()):
                x.rmdir()


class TheTemplateStoresIt(unittest.TestCase):
    def test_the_field_exists(self):
        self.assertIn("**学历认证：** [CREDENTIAL_STATUS]", TPL)

    def test_it_sits_in_the_education_section(self):
        """它是学历的属性，放别处 `/job-setup` 那一步就问不到它。"""
        i = TPL.index("[CREDENTIAL_STATUS]")
        self.assertLess(TPL.index("## 教育背景"), i)
        self.assertLess(i, TPL.index("## 工作经历"))

    def test_it_is_conditional_on_a_foreign_degree(self):
        """内地学历的用户不该看到这一行 —— 凭空多一问就是噪音。"""
        i = TPL.index("[CREDENTIAL_STATUS]")
        seg = flat(TPL[i:i + 1200])
        self.assertRegex(seg, r"只有「层次」是境外院校（含港澳台）时才需要这一行")
        self.assertRegex(seg, r"内地学历跳过")

    def test_it_names_the_three_values(self):
        """取值不定死，下游读到的就是各写各的自由文本。"""
        seg = flat(TPL[TPL.index("[CREDENTIAL_STATUS]"):][:1200])
        for v in ("已认证", "未办理", "不适用（内地学历）"):
            with self.subTest(v=v):
                self.assertIn(v, seg)

    def test_it_says_why_it_deserves_a_line(self):
        seg = flat(TPL[TPL.index("[CREDENTIAL_STATUS]"):][:1200])
        self.assertRegex(seg, r"学信网收录不到")
        self.assertRegex(seg, r"前置周期")

    def test_it_names_the_consumer(self):
        """没有消费者的字段会静静躺着 —— 这仓库为它付过学费。"""
        seg = flat(TPL[TPL.index("[CREDENTIAL_STATUS]"):][:1200])
        self.assertIn("job-offer.md", seg)

    def test_it_is_marked_as_a_fact_not_an_exclusion(self):
        """写进「## 明确排除」就会变成一道硬门 —— 它不是。"""
        seg = flat(TPL[TPL.index("[CREDENTIAL_STATUS]"):][:1200])
        self.assertRegex(seg, r"它不进硬门，别写进「## 明确排除」")


class TheSetupAsksForIt(unittest.TestCase):
    def _seg(self) -> str:
        i = SETUP.index("### Section 2：教育经历")
        return flat(SETUP[i:SETUP.index("### Section 3", i)])

    def test_it_asks_only_for_foreign_schools(self):
        seg = self._seg()
        self.assertRegex(seg, r"学校在境外（含港澳台）时，多问一句")
        self.assertRegex(seg, r"只在层次填了境外院校时问")

    def test_it_says_where_the_answer_goes(self):
        """不说落点，答案问到了也没地方放。"""
        seg = self._seg()
        self.assertRegex(seg, r"写进 `## 教育背景` 的「学历认证」那一行")

    def test_it_says_why_it_is_worth_one_more_question(self):
        seg = self._seg()
        self.assertRegex(seg, r"越早知道越值钱")
        self.assertRegex(seg, r"那时候他已经辞职了")

    def test_the_original_questions_survive(self):
        """这一段是插在中间的，别把原来那几问挤掉。"""
        seg = self._seg()
        self.assertIn("层次（博士 / 硕士 / 本科 / 大专等）", seg)
        self.assertIn("毕业论文题目", seg)


class TheOfferChecklistReadsIt(unittest.TestCase):
    def _seg(self) -> str:
        i = OFFER.index("## Step 4: 接之前先确认这几件")
        return flat(OFFER[i:OFFER.index("### 谈好的数", i)])

    def test_the_item_exists(self):
        self.assertRegex(self._seg(), r"境外学历（含港澳台）：中留服认证办了吗？")

    def test_it_is_conditional(self):
        self.assertRegex(self._seg(),
                         r"只在资料的「教育背景」里层次写着境外院校时才问")

    def test_it_reads_the_profile_value(self):
        """清单里别的条目也是这么做的 —— 把资料里那格的值念出来，不让人再去翻。"""
        self.assertIn("{{`profile` 教育背景的「学历认证」取值}}", OFFER)

    def test_it_says_this_one_is_a_queue_not_a_question(self):
        """**这才是它和清单里别的条目的区别。** 混在一起看，它就只是又一条待问。"""
        seg = self._seg()
        self.assertRegex(seg, r"别的都是「问清楚」，这一条是「要排队」")

    def test_it_refuses_to_state_a_lead_time(self):
        """办理时限以官网当期公告为准 —— 抄一个数进来，过期了比不写更糟。

        这句话的**正本**在这儿；别处只许指过来，不许各写一份
        （`NoOneQuotesALeadTime` 盯着「别处不许出现一个具体的数」）。
        """
        seg = self._seg()
        self.assertRegex(seg, r"以中留服官网当期公告为准，别照抄任何转述")

    def test_the_no_employer_case_is_covered(self):
        """上一家是自己的公司时，「离职证明能不能开」这一问答不出来。"""
        seg = self._seg()
        self.assertRegex(seg, r"上一家是自己的公司 / 自由职业 / 长期空窗")
        self.assertRegex(seg, r"不是「能」也不是\s*「不能」——是「没有这份东西」")

    def test_the_routine_papers_are_not_over_asked(self):
        """身份证体检银行卡缺了只是耽误几天 —— 逐条问会把真正要排队的那条淹掉。"""
        seg = self._seg()
        self.assertRegex(seg, r"不必逐条问")

    def test_the_existing_items_survive(self):
        seg = self._seg()
        for k in ("离职证明", "竞业限制", "入职日期", "三方协议", "offer 的书面形式"):
            with self.subTest(k=k):
                self.assertIn(k, seg)

    def test_the_ordering_rule_survives(self):
        """「先拿纸再提离职」是这一节最贵的一条，别被新条目挤掉。"""
        self.assertRegex(self._seg(), r"书面 offer 到手、背调过了，再提离职")


class NoOneQuotesALeadTime(unittest.TestCase):
    """讲中留服的地方有四处，而「别照抄一个时限」只钉在其中一处。

    `job-offer.md` 那一条自己写着「具体时限以中留服官网当期公告为准，
    别照抄任何转述（含本文）」，守卫也钉着它。而**同一件事另外三处在讲**：
    `job-setup.md` 问那一句、`04-job-evaluation.md` 讲层次等同、
    `audit_pipeline` 那条自检印给用户看 —— 三处都没有任何东西拦着
    「大约 15 个工作日」被写进去。

    这正是本仓库反复栽的形状：**一条规则只贴在一个写手身上，
    另外几个照样会犯**（`AGENTS.md` 那句话就是为这个写的）。
    所以判据升成一条性质：讲中留服的地方，一个具体的天数都不许出现。

    为什么这个数特别不能拍：它按工作日算、随当期公告变，而用户会照着它
    排离职与入职的日子。写错的代价是**他已经辞职了，而纸还没下来**。
    """

    #: 一个「多久」的数，长成什么样都算。
    LEAD_TIME = re.compile(r"\d+\s*(?:个)?\s*(?:工作日|个?月|周|天)")

    #: 讲这件事时用到的几种叫法。**只盯「中留服」够不着**：自检印给用户的
    #: 那句写的是「教育部留学服务中心」，一次都不出现「中留服」——
    #: 变异当场照出来，那一处怎么改都不红。
    NAMES = re.compile(r"中留服|留学服务中心|国外学历学位认证书|学历认证")

    @staticmethod
    def _block(text: str, pos: int) -> str:
        """关键词所在的那一**块**。

        窗口按字符数取会两头不是：往短了取够不着同一段的下半截
        （`job-setup` 那条引用块十几行），往长了取会伸进隔壁条目
        （`job-offer` 的清单里紧跟着「离职周期（通常 30 天）」——
        那个数是对的，报它就是噪音）。

        所以按结构取：从关键词那行往两边扩，遇到空行、顶格的 `- ` 新条目、
        或 markdown 标题就停。列表项的续行是缩进的，会跟着留在块里。
        """
        lines = text.splitlines()
        at = text.count("\n", 0, pos)

        def edge(i):
            s = lines[i]
            return (not s.strip() or s.startswith("#")
                    or re.match(r"[-*] |\d+\. ", s))

        lo = at
        while lo > 0 and not edge(lo):
            lo -= 1
        hi = at + 1
        while hi < len(lines) and not edge(hi):
            hi += 1
        return "\n".join(lines[lo:hi])

    def _places(self):
        for name in TheSignalItLeansOnIsReal.OWNERS:
            f = next(x for x in (ROOT / "workflows").rglob("*.md")
                     if x.name == name)
            yield name, f.read_text(encoding="utf-8", errors="replace")
        yield ("audit_pipeline.py",
               (ROOT / "tools" / "audit_pipeline.py").read_text(
                   encoding="utf-8"))

    def test_the_scan_reaches_every_place(self):
        """尺子先证明自己够得着 —— 少一处，下面那条就在那一处永远绿。"""
        got = [n for n, t in self._places() if self.NAMES.search(t)]
        self.assertEqual(len(got), 4, f"只够着 {got}")

    def test_the_ruler_would_light_up(self):
        """判据自己也要能红：块取对了、数认得出来。"""
        md = ("> 学校在境外时问一句中留服认证办了没有。\n"
              "> 一般 15 个工作日。\n\n- 离职周期（通常 30 天）\n")
        blk = self._block(md, md.index("中留服"))
        self.assertRegex(blk, self.LEAD_TIME, "同一块里的数没认出来")
        self.assertNotIn("30 天", blk, "块伸进了隔壁条目")

    def test_nobody_writes_a_number(self):
        for name, t in self._places():
            for m in self.NAMES.finditer(t):
                blk = flat(self._block(t, m.start()))
                with self.subTest(name=name, at=m.group(0)):
                    self.assertNotRegex(
                        blk, self.LEAD_TIME,
                        f"{name} 在讲这件事的那一块里写了一个具体时限 —— "
                        f"它以官网当期公告为准，抄一个数进来过期了比不写更糟")

    def test_the_rule_itself_is_written_down_once(self):
        """性质挡得住新写的数，挡不住「下一个人不知道为什么」——
        所以那句解释要在，且只在一处。"""
        n = sum(1 for _n, t in self._places()
                if "以中留服官网当期公告为准" in t)
        self.assertEqual(n, 1, f"那句话有 {n} 份 —— 正本只该有一份")


class TheSignalItLeansOnIsReal(unittest.TestCase):
    """现算：这件事此前真的一次都没被提过。"""

    #: 允许讲中留服的文件，以及**各自负责的那一句**。
    #:
    #: 2026-08-24 加进第三处（`04`）时这条红过一次 —— 那正是它的用处：
    #: 每多一处都要当场说清它讲的是不是同一件事。这三处不重叠：
    #:
    #:     job-setup.md   问一句：办了没有（层次是境外时才问）
    #:     job-offer.md   接 offer 前查一遍 —— 它**要排队**，不是问一句就有
    #:     04-…           它**不**把境外学历变成「统招」（只管层次等同）
    #:
    #: 第三条是前两条都没说、也不该说的：那是打分时的判据，不是待办事项。
    OWNERS = {
        "job-setup.md": "办了没有",
        "job-offer.md": "要排队",
        "04-job-evaluation.md": "层次等同",
    }

    def test_only_the_registered_files_talk_about_it(self):
        """多一处就要当场裁定它讲的是不是同一件事，别让几份说法慢慢漂开。"""
        hits = []
        for f in sorted((ROOT / "workflows").rglob("*.md")):
            if f.name in self.OWNERS:
                continue
            if "中留服" in f.read_text(encoding="utf-8", errors="replace"):
                hits.append(f.name)
        self.assertEqual(hits, [], f"这几处也讲了中留服，判据可能已经分叉：{hits}")

    def test_each_owner_still_says_its_own_half(self):
        """登记了却不讲自己那一半，等于把这张表变成一份豁免名单。"""
        for name, must in self.OWNERS.items():
            with self.subTest(name=name):
                f = next(x for x in (ROOT / "workflows").rglob("*.md")
                         if x.name == name)
                t = f.read_text(encoding="utf-8", errors="replace")
                self.assertIn("中留服", t)
                self.assertIn(must, t, f"{name} 不再讲「{must}」了")

    def test_the_scoring_file_does_not_turn_it_into_a_todo(self):
        """**04 是打分判据，不是待办。** 它一旦也说「去办」，就和 `/job-offer`
        抢同一件事，而用户会在两个地方各被催一次。"""
        t = (ROOT / "workflows" / "reference"
             / "04-job-evaluation.md").read_text(encoding="utf-8")
        i = t.index("中留服")
        seg = flat(t[max(0, i - 300):i + 300])
        self.assertRegex(seg, r"不会、也不能把一份境外学历变成「统招」")
        self.assertNotRegex(seg, r"提前办|去办|要排队|工作日")


    def test_the_active_user_would_trigger_it(self):
        """他是境外学历 —— 这一条对他是真会触发的，不是纸上规则。"""
        p = ROOT / ".active_user"
        if not p.is_file():
            self.skipTest("没有活动用户")
        f = (ROOT / "users" / p.read_text(encoding="utf-8").strip()
             / "profile" / "candidate.md")
        if not f.is_file():
            self.skipTest("这位用户还没有资料")
        t = f.read_text(encoding="utf-8")
        if "境外院校" not in t:
            self.skipTest("这位用户是内地学历 —— 这一条对他不触发，是对的")
        # 跳过条件已经保证「他是境外学历」了。**该断言的是它驱动了什么** ——
        # 那一行缺着，审计就得喊；补上了就该闭嘴。两条路都要能红。
        #
        # 原来这里写 `assertIn("境外院校", t)`：上一行刚判过的东西再判一遍，
        # 不成立就跳过、成立才断言 —— 恒绿。（判据见 `test_no_assertion_is_dead_on_arrival.py` 第 6 种）
        ap._USER[:] = [p.read_text(encoding="utf-8").strip()]
        got = ap.check_foreign_degree_has_no_credential_row({}, {})
        self.assertEqual(
            bool(got), "学历认证" not in t,
            "境外学历缺着认证那一行而审计没喊（或反过来）—— "
            "那条清单项对唯一该触发的人是静默的")


class TheAuditCatchesTheOnesFiledBefore(unittest.TestCase):
    """这一问比资料晚 —— 已经建过档的人不会再被问一遍，得有东西喊。"""

    def _fn(self):
        return ap.check_foreign_degree_has_no_credential_row

    def test_the_check_is_registered(self):
        self.assertIn(self._fn(), [f for _n, f in ap.CHECKS],
                      "写了检查却没挂进 CHECKS —— 它一次都不会跑")

    def test_it_fires_on_a_foreign_degree_without_the_row(self, ):
        with _profile("- 学校层次：境外院校（澳门）\n") as _:
            got = self._fn()({}, {})
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0][1], "资料：境外学历没写认证进度")

    def test_it_shuts_up_once_the_row_is_there(self):
        with _profile("- 学校层次：境外院校（澳门）\n**学历认证：** 未办理\n") as _:
            self.assertEqual(self._fn()({}, {}), [])

    def test_未办理_still_counts_as_answered(self):
        """**判的是问没问过，不是办没办。** `未办理` 是最该早知道的那个答案。"""
        with _profile("- 学校层次：境外院校\n**学历认证：** 未办理\n") as _:
            self.assertEqual(self._fn()({}, {}), [])

    def test_a_mainland_degree_is_never_asked(self):
        with _profile("- 学校层次：普通本科\n") as _:
            self.assertEqual(self._fn()({}, {}), [])

    def test_no_profile_at_all_is_silent(self):
        """没建档的人不该收到这条 —— 那是 /job-setup 的事。"""
        with _profile(None) as _:
            self.assertEqual(self._fn()({}, {}), [])

    def test_no_active_user_is_silent(self):
        """`_USER` 是空的时候别炸 —— 审计要能在任何状态下跑完。

        实测 2026-08-25：第一版没抄这道守卫，
        `test_a_bullet_saying_none_is_not_a_question` 那条「审计不许抛异常」
        当场把它抓了。别的读资料的检查全都有这一行，它是漏的那个。
        """
        old = list(ap._USER)
        try:
            ap._USER[:] = []
            self.assertEqual(self._fn()({}, {}), [])
        finally:
            ap._USER[:] = old

    def test_it_says_which_command_fixes_it(self):
        """`AGENTS.md`「每一处引导都要写出该敲的命令」。"""
        with _profile("- 学校层次：境外院校\n") as _:
            msg = self._fn()({}, {})[0][2]
        self.assertIn("/job-setup --section 2", msg)

    def test_that_section_number_is_the_education_one(self):
        """指错节号比不指还坏 —— 他会照着去重填别的东西。"""
        self.assertIn("### Section 2：教育经历", SETUP)

    def test_the_section_flag_accepts_a_bare_number(self):
        """`--section 2` 这种敲法得真被支持，不是我编的。"""
        self.assertRegex(flat(SETUP), r"纯数字，如 `9` \| 对应编号的 Section")

    def test_it_says_why_it_cannot_wait(self):
        with _profile("- 学校层次：境外院校\n") as _:
            msg = self._fn()({}, {})[0][2]
        self.assertIn("工作日", msg)
        self.assertIn("入职日期就得往后推", msg)

    def test_the_message_speaks_plain_chinese(self):
        """终端上的字，别搬内部词（`AGENTS.md`「给用户看的措辞」）。"""
        with _profile("- 学校层次：境外院校\n") as _:
            msg = self._fn()({}, {})[0][2]
        for w in ("硬门", "台账", "四维", "判词", "短名单"):
            with self.subTest(word=w):
                self.assertNotIn(w, msg)

    def test_the_reason_is_recorded_in_the_code(self):
        """为什么会缺 —— 不写下来，下一个人会以为是漏写了。"""
        doc = self._fn().__doc__ or ""
        self.assertIn("先建档、后加问", doc)
        self.assertIn("2026-08-25", doc)


if __name__ == "__main__":
    unittest.main()
