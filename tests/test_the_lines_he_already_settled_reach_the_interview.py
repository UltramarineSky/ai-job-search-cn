# -*- coding: utf-8 -*-
"""他在聊天框里定过稿的那几句，备面命令看不见 —— 而它们正是被交叉验证的那几句。

`profile/hr-answers.md` 是 2026-08-24 加的：HR 反复问的九句，事先写好、总览页上
能改。存在的理由写在它自己的抬头里：「**临场编的代价不是慢，是口径不一致** ——
同一个问题在打招呼、HR 初面、背调三处说法对不上，是面试官最容易抓的点」。

而这份文件**在 `workflows/` 里一处引用都没有**（实测 2026-08-25 全仓搜过）。
`tools/`、`web/src/`、`tests/` 三处都有 —— 面板读它、显示它、能改它，
**而没有任何命令读它**。

最要命的是 `/job-interview`：它 Step 1 读 `candidate.md` / `behavioral.md` /
`interview-star.md`，唯独不读这一份。于是备面时它会**重新起草**离职原因、
期望薪资那几条 —— 亲手造出这份文件要防的那种不一致。

## 缺口正好是「口径对照单」那一节的大小

Step 3.3 原文只有一句：「把交出去的**简历和求职信**里最可能被追问的那些具体说法
列成一张短单」。**只有纸上的那一半。** 而 `07-interview-prep.md` 点名会被交叉
验证的是「离职原因」，那条不写在简历上 —— 它在打招呼和 HR 初面的对话里；
07 的阶段地图里 HR 初面考的正是「稳定性、离职原因、薪资摸底」，背调那一行
是整张表里唯一一条红线。

实测活动用户 2026-08-25：那九条**九条全填了**，一条占位符都不剩。
也就是说他已经把答案备好了，而备面命令看不见。
"""
import json
import pathlib
import re
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import _cli  # noqa: E402

IV = (ROOT / "workflows" / "job-interview.md").read_text(encoding="utf-8")
PREP = (ROOT / "workflows" / "reference"
        / "07-interview-prep.md").read_text(encoding="utf-8")
TPL = (ROOT / "profile.example" / "hr-answers.md").read_text(encoding="utf-8")
AGENTS = (ROOT / "AGENTS.md").read_text(encoding="utf-8")


def flat(s: str) -> str:
    s = " ".join(re.sub(r"^\s*(?:>|#:?)\s?", "", s, flags=re.M).split())
    return re.sub(r"(?<=[一-鿿，。；：、（）「」])"
                  r" +(?=[一-鿿，。；：、（）「」])", "", s)


def seg() -> str:
    i = IV.index("### 3.3 口径对照单")
    return flat(IV[i:IV.index("### 3.4 难题，按这一家定制", i)])


class TheCommandReadsIt(unittest.TestCase):
    def test_it_is_in_the_read_list(self):
        i = IV.index("**框架只读一次**")
        self.assertIn("`profile/hr-answers.md`",
                      IV[i:IV.index("这三份可选输入", i)])

    def test_the_read_list_says_what_it_is(self):
        """只给个路径，执行者不知道那里面装的是什么、能拿它干什么。"""
        i = IV.index("- `profile/hr-answers.md`（")   # 读取清单那一条带括注
        s = flat(IV[i:i + 400])
        self.assertRegex(s, r"他在聊天框里已经定过稿的那几句")
        self.assertRegex(s, r"总览页上「HR 常问的」那一块就是它")

    def test_the_optional_count_was_updated(self):
        """原来写「这**两份**可选输入」—— 加了一份不改数，下一个人就少读一份。"""
        self.assertIn("**这三份可选输入常常没填", IV)
        self.assertNotIn("**这两份可选输入常常没填", IV)

    def test_it_has_a_fallback_branch(self):
        i = IV.index("- `profile/hr-answers.md` **不存在 / 仍是占位符**")
        s = flat(IV[i:i + 700])
        self.assertRegex(s, r"「口径对照单」只出纸面那半")
        self.assertRegex(s, r"面试里现编，和背调对不上的风险自己知道")

    def test_the_fallback_says_where_to_write_it(self):
        """空态也要给出口 —— AGENTS「每一处引导都要写出该敲的命令」。"""
        i = IV.index("- `profile/hr-answers.md` **不存在 / 仍是占位符**")
        s = IV[i:i + 700]
        self.assertIn("总览页", s)
        # 给斜杠命令，不给裸 `python tools/serve.py`：那既不是用户学过的敲法，
        # 也会让「用 Python 的命令」那份清单凭空多出一条（实测当场被守卫拦下）。
        self.assertIn("/job-dashboard", s)
        self.assertNotIn("python tools/serve.py", s)

    def test_the_fallback_refuses_to_invent(self):
        """占位符推说法、或替他现编一版冒充定稿 —— 两条都要拦。"""
        i = IV.index("- `profile/hr-answers.md` **不存在 / 仍是占位符**")
        s = flat(IV[i:i + 700])
        self.assertRegex(s, r"绝不拿占位符 `\[YOUR_WHY_LOOKING\]` 之类去推")
        self.assertRegex(s, r"不要替他现编一版塞进准备包冒充「已定稿」")

    def test_the_sibling_fallbacks_survive(self):
        """这一条是照着那两条的形状加的，它们一个字不许动。"""
        s = flat(IV)
        self.assertRegex(s, r"`behavioral\.md` 未填，本轮不做语域校准")
        self.assertRegex(s, r"准备包只出题目与考点、\*\*不编造案例\*\*")


class TheCheckListCoversBothHalves(unittest.TestCase):
    def test_it_says_there_are_two_halves(self):
        self.assertRegex(seg(), r"\*\*两半，缺一半就漏掉被查得最凶的那几条。\*\*")

    def test_the_paper_half_is_unchanged(self):
        """原来那一句是对的，加的是另一半 —— 别把它改掉。"""
        s = seg()
        self.assertRegex(s, r"\*\*纸上没有的，当场别说；纸上有的，每一条都要经得起深挖。\*\*")
        self.assertRegex(s, r"简历和求职信里\*\*最可能被追问\*\*")

    def test_the_chat_half_names_the_file(self):
        self.assertIn("`profile/hr-answers.md`", seg())

    def test_it_says_why_paper_alone_misses_them(self):
        """离职原因、薪资不写在简历上 —— 这就是为什么只查纸面漏得掉。"""
        s = seg()
        self.assertRegex(s, r"离职原因、期望薪资、当前薪资\*\*不写在简历上\*\*")
        self.assertRegex(s, r"是在打招呼和 HR 初面的对话里说的")

    def test_it_quotes_the_cross_check_rule(self):
        self.assertRegex(seg(), r"面试官对同一个问题（比如离职原因）\s*反复问，是在交叉验证一致性")

    def test_that_rule_really_exists(self):
        self.assertRegex(flat(PREP), r"面试官对同一个问题（比如离职原因）反复问，是在交叉验证一致性")

    def test_it_cites_the_stage_map_row(self):
        s = seg()
        self.assertRegex(s, r"HR 初面考的就是「稳定性、离职原因、薪资摸底」")
        self.assertRegex(s, r"背调那一行更是整张表里唯一一条红线")

    def test_the_stage_map_really_says_that(self):
        row = next(l for l in PREP.splitlines() if l.startswith("| **HR 初面**"))
        for w in ("稳定性", "离职原因"):
            with self.subTest(w=w):
                self.assertIn(w, row)


class ItReusesInsteadOfRewriting(unittest.TestCase):
    """**这是整条的要害。** 另写一版就是亲手制造那种不一致。"""

    def test_it_says_do_not_redraft(self):
        s = seg()
        self.assertRegex(s, r"照抄进对照单，不重新起草")
        self.assertRegex(s, r"备面时另写一版，就是亲手制造 07 说的那种不一致")

    def test_it_stops_star_from_redrafting_them_either(self):
        """Step 3.2 起草 STAR 那一步同样会撞上这几题。"""
        self.assertRegex(seg(), r"`hr-answers\.md` 已经答过的题不再新起一版")

    def test_the_star_step_still_exists(self):
        self.assertIn("### 3.2 STAR 案例怎么对上题", IV)

    def test_expanding_is_not_rewriting(self):
        s = seg()
        self.assertRegex(s, r"是「展开」不是「改写」")
        self.assertRegex(s, r"骨架用他那一版，细节从")

    def test_it_quotes_the_files_own_statement_of_that_relation(self):
        """两者的关系是那份文件自己定的，别在这儿另立一套。"""
        self.assertRegex(seg(), r"两者不是重复，是两个渠道两种长度")

    def test_the_template_really_says_that(self):
        self.assertRegex(flat(TPL), r"两者不是重复，是两个渠道两种长度 —— 别把它们合并")

    def test_it_says_to_declare_what_was_expanded(self):
        self.assertRegex(seg(), r"展开了哪几条，在准备包里说一句")


class TheSalaryLinesKeepTheirOwnRule(unittest.TestCase):
    """薪资那两条的答案「不该是一个数字」—— 在这儿另立规矩最贵。"""

    def test_it_defers_to_the_file(self):
        s = seg()
        self.assertRegex(s, r"按它写的办，别在这里另立规矩")
        self.assertRegex(s, r"「不该是一个数字」，是「怎么把话接回去」")

    def test_the_template_really_says_that(self):
        self.assertRegex(flat(TPL), r"这一条的答案\*\*不该是一个数字\*\*")

    def test_it_routes_a_forced_number_to_the_right_command(self):
        s = seg()
        self.assertIn("/job-offer", s)
        self.assertRegex(s, r"不在这里现想一个数")

    def test_that_command_really_does_it(self):
        offer = (ROOT / "workflows" / "job-offer.md").read_text(encoding="utf-8")
        self.assertIn("## Step 1: 算可守区间（单个 offer）", offer)
        self.assertRegex(flat(offer), r"解耦话术")


class AConflictIsSurfacedNotResolved(unittest.TestCase):
    """两处都是他写的，工具没有资格裁定哪个是真的。"""

    def test_it_says_to_ask(self):
        s = seg()
        self.assertRegex(s, r"摆出来问他以哪个为准，\*\*别自己挑一个\*\*")

    def test_it_says_why(self):
        self.assertRegex(seg(), r"工具没有资格裁定哪个是真的")


class TheFileIsOnTheRegister(unittest.TestCase):
    """`AGENTS.md` 那份枚举是每个 AI 工具用来知道 `profile/` 里有什么的。"""

    def test_agents_lists_it(self):
        i = AGENTS.index("需要时再读 `profile/behavioral.md`")
        self.assertIn("`profile/hr-answers.md`", AGENTS[i:i + 400])

    def test_agents_says_what_it_is(self):
        i = AGENTS.index("`profile/hr-answers.md`")
        self.assertRegex(flat(AGENTS[i:i + 200]),
                         r"HR 反复问的那几句，他在总览页上定过稿的那一版")

    def test_the_other_three_are_still_listed(self):
        i = AGENTS.index("需要时再读 `profile/behavioral.md`")
        seg_ = AGENTS[i:i + 400]
        for f in ("behavioral.md", "interview-star.md", "search-queries.md"):
            with self.subTest(f=f):
                self.assertIn(f, seg_)

    def test_the_template_ships_with_the_others(self):
        d = ROOT / "profile.example"
        self.assertTrue((d / "hr-answers.md").is_file())

    def test_setup_still_copies_the_whole_folder(self):
        """`/job-setup` 是整目录拷 —— 靠的就是这一条，新用户才拿得到它。"""
        setup = (ROOT / "workflows" / "job-setup.md").read_text(encoding="utf-8")
        self.assertRegex(flat(setup),
                         r"先\*\*把 `profile\.example/` 里每个文件都拷成 `profile/`")


class TheSignalItLeansOnIsReal(unittest.TestCase):
    """现算：那九条真的填满了，而且那些问题真的和 07 重叠。"""

    def test_no_workflow_owned_it_before(self):
        """**修好之后仍然只有 `job-interview.md` 这一条命令读它。**

        哪天第二个命令也开始读它，两处对「怎么用」的说法就该合并 ——
        这条会红，那正是该合并的时候。

        **范围是命令，不是 `reference/`。** 原来扫的是 `rglob`，把参考资料
        一起算了进去，于是 2026-08-25 往 `05-cv-templates.md` 里加一句
        「这一条也管聊天框那份答案」当场变红 —— 那是一句**交叉引用**，
        不是第二个消费者，它没有带来第二份「怎么用」。判据跟着自己的措辞收窄：
        命令在 `workflows/*.md`，参考资料在 `workflows/reference/`。
        """
        hits = [f.name for f in sorted((ROOT / "workflows").glob("*.md"))
                if "hr-answers" in f.read_text(encoding="utf-8", errors="replace")]
        self.assertEqual(hits, ["job-interview.md"], f"还有这几条命令也引了：{hits}")

    def test_reference_may_cross_reference_but_not_re_explain(self):
        """`reference/` 里可以提它，但**不许再写一份「怎么用」**。

        上面那条收窄之后，`reference/` 就成了盲区。这条把盲区补上：交叉引用
        （提一句它是什么、判据也管它）没问题；把那份文件的用法在别处重讲一遍
        不行 —— 「一个概念两处各写一份」正是这个仓库反复治的病。
        """
        for f in sorted((ROOT / "workflows" / "reference").glob("*.md")):
            t_ = f.read_text(encoding="utf-8", errors="replace")
            if "hr-answers" not in t_:
                continue
            with self.subTest(f=f.name):
                i = t_.index("hr-answers")
                seg_ = t_[max(0, i - 300):i + 300]
                self.assertNotIn("总览页上有「HR 常问的」", seg_,
                                 "把「怎么用」在参考资料里又讲了一遍")

    def test_the_questions_overlap_with_the_stage_map(self):
        """重叠不是我说的 —— 现拿模板里的问题去 07 的阶段地图里找。"""
        qs = re.findall(r"^## (.+)$", TPL, re.M)
        self.assertGreaterEqual(len(qs), 6, "模板里的问题太少，判据要重看")
        hit = [q for q in qs
               if any(k in PREP for k in re.findall(r"[一-鿿]{2,4}", q))]
        self.assertGreater(len(hit), len(qs) * 0.5,
                           f"只有 {len(hit)}/{len(qs)} 条在 07 里找得到影子")

    def test_the_active_user_really_filled_them(self):
        """一条没填时这一节还成立（缺口照样在），但实测数要更新。"""
        p = ROOT / "web" / "public" / "data.json"
        if not p.is_file():
            self.skipTest("还没导出过面板数据")
        qa = json.loads(p.read_text(encoding="utf-8")).get("hrAnswers") or []
        if not qa:
            self.skipTest("这个用户没有这份文件")
        done = sum(1 for x in qa if not x.get("empty"))
        self.assertGreater(done, 0,
                           "一条都没写 —— 那这一条防的东西还没开始发生")

    def test_the_panel_still_owns_the_editing(self):
        """写它的地方仍然是面板，不是某条命令 —— 这一条只加了「读」。"""
        qa = (ROOT / "web" / "src" / "components"
              / "HrAnswers.tsx").read_text(encoding="utf-8")
        self.assertIn("不生成、不润色", qa)


if __name__ == "__main__":
    unittest.main()
