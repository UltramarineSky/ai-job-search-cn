# -*- coding: utf-8 -*-
"""判定口径变了，材料不会自己跟着变。

薪资维改成查表、专业减分补成字段、硬门名归正 —— 每一次都可能让一个岗换档，
而 `evaluation.md` 里那张表、那个综合分、那句结论**全停在出材料的那一刻**。
用户打开它，看到的是一份自洽但过时的判断。

`tools/stale_materials.py` 拿存档和职位库对。这条守卫钉三件事：

1. **判据是结构化的两个数**，不是去 grep 依据里那句「⚠️ 订正」——
   散文写法随人变，而分与判词是字段。同一课 `scoring.adjust_of` 记过一次
   （减分只写在散文里等于没减）。
2. **存档里那几代格式都要认**。实测 2026-08-30 只认第一种时 37 份读不出来，
   而读不出来就等于对这条检查隐形（`__主__` 那次栽的是同一个坑）。
3. **只比档名，不比括注**。一边写「跳过（这家的这个岗已经投过）」、另一边写
   「跳过」是同一个判定；按整串比会把它报成翻档，而「翻档」这个词的全部价值
   就在于它意味着「这份材料本来不该发」。
"""
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import stale_materials as sm  # noqa: E402

AUTO = (ROOT / "workflows" / "job-auto.md").read_text(encoding="utf-8")
APPLY = (ROOT / "workflows" / "job-apply.md").read_text(encoding="utf-8")
EXPORT = (ROOT / "tools" / "export_web_data.py").read_text(encoding="utf-8")
LOAD = (ROOT / "web" / "src" / "data" / "load.ts").read_text(encoding="utf-8")
APP = (ROOT / "web" / "src" / "App.tsx").read_text(encoding="utf-8")
LIST = (ROOT / "web" / "src" / "components"
        / "Shortlist.tsx").read_text(encoding="utf-8")


class EveryGenerationOfTheFileParses(unittest.TestCase):
    CASES = (
        ("综合得分：63/100\n\n## 结论：值得投\n", 63, "值得投"),
        ("**综合得分：59/100**\n\n### 结论：可以考虑\n", 59, "可以考虑"),
        ("## 综合 62/100 —— 可以考虑\n", 62, "可以考虑"),
        ("**综合 70/100**（61×0.3=18.3 + 85×0.25=21.25）\n\n### 结论：值得投\n",
         70, "值得投"),
        ("### 结论：值得投（72）\n综合得分：72/100\n", 72, "值得投"),
    )

    def test_all_of_them(self):
        for text, score, verdict in self.CASES:
            with self.subTest(text=text[:24]):
                self.assertEqual(sm.in_file(text), (score, verdict))

    def test_a_gate_fail_has_no_score_and_that_is_a_fact(self):
        """硬门 FAIL 那一档本来就不打分 —— `None` 是事实，不是解析失败。

        ⚠️ 判词现在是**归一后的档名**（2026-08-31 起 `in_file` 走
        `build_dashboard.parse_evaluation`，不再自己写一套正则）。
        报告那一行照旧读得通：`plain("硬门 FAIL")` 就是「不满足硬性条件」。
        """
        t = "**综合得分：不打分（硬性条件没过）**\n\n### 结论：不满足硬性条件\n"
        score, verdict = sm.in_file(t)
        self.assertIsNone(score)
        self.assertEqual(sm._band(verdict), "硬门 FAIL")
        import export_web_data as ex
        self.assertEqual(ex.plain(verdict), "不满足硬性条件",
                         "报告那一行会印出一个内部词")

    def test_the_two_parsers_are_one(self):
        """深评怎么读只有一份 —— 这里原来自己写了四条正则。

        两边学的是同一课（「解析器只认一种，一部分真实数据就静默解析成空」），
        却各自落在**另外四种写法**上。实测 2026-08-31 全库 316 份：
        综合分 3 份、结论 5 份两边读得不一样，而读不出来在这边的后果是
        `skip["评估文件读不出分或结论"] += 1; continue` —— 静默掉出重跑队列。
        （那几份今天都已经投出去或标了不投，所以没造成实际损失；
        这条守的是下一次。）
        """
        src = (ROOT / "tools" / "stale_materials.py").read_text(
            encoding="utf-8")
        # **查的是「有没有定义」，不是「有没有出现这个名字」** ——
        # 那几个名字在讲它们为什么没有了的注释里还要再出现一次
        # （`CONTRIBUTING`：删掉一条判据时在原地留一句它为什么没有了）。
        # 第一版少写了 `= re.compile`，当场被自己的解释绊倒。
        for gone in ("_SCORE = re.compile", "_VERDICT = re.compile",
                     "_VERDICT_INLINE = re.compile", "_NOSCORE = re.compile"):
            with self.subTest(gone):
                self.assertNotIn(gone, src, "又自己写了一套深评解析")
        import build_dashboard as bd
        for text, score, _v in self.CASES:
            with self.subTest(text[:20]):
                self.assertEqual(sm.in_file(text)[0], score)
                self.assertEqual(str(bd.parse_evaluation(text).get("score")),
                                 str(score), "两边读出来的分不一样")

    #: `parse_evaluation` 认、而这边原来不认的那几种（说明里记着的真实写法）。
    ONCE_MISSED = (
        "**综合得分：约 62/100 —— 可以考虑**\n### 结论：可以考虑\n",
        "**综合 = 55×0.30 + 72×0.25 + 62×0.20 + 58×0.25 = 62 → 「值得投」**\n",
        "- 综合得分：63/100\n### 结论：值得投\n",
    )

    def test_the_forms_the_other_side_already_knew(self):
        for t in self.ONCE_MISSED:
            with self.subTest(t[:24]):
                self.assertIsNotNone(sm.in_file(t)[0],
                                     "这几种面板那边一直读得出来")


class TheBandIsWhatCounts(unittest.TestCase):
    def test_a_note_in_brackets_is_not_a_flip(self):
        self.assertEqual(sm._band("跳过（这家的这个岗已经投过）"), sm._band("跳过"))

    def test_the_triage_prefix_is_not_a_flip(self):
        self.assertEqual(sm._band("粗筛：值得投"), sm._band("值得投"))

    def test_every_gate_fail_spelling_lands_in_one_band(self):
        for v in ("硬门 FAIL (学历与院校)", "不满足硬性条件（学历）",
                  "硬门 FAIL (候选人明确排除（英语口语）)"):
            with self.subTest(v=v):
                self.assertEqual(sm._band(v), "硬门 FAIL")

    def test_an_unknown_verdict_is_not_silently_equal(self):
        """认不出的档名原样返回 —— 宁可报出来给人看，不静默当成一致。"""
        self.assertNotEqual(sm._band("某种没见过的判词"), sm._band("值得投"))


class TheSecondReasonIsAnAdmission(unittest.TestCase):
    """第二个入队理由：**评估自己招了当时没读到 JD**。

    这一档补上之前，这条检查只会问「存档和库一不一致」—— 而 2026-08-30 实测
    一致的有 40 个、翻档的 0 个，看着像「全都好着呢」。补上之后同一批材料里
    立刻出来 86 个。**一致不等于对：两边可以一起错**，那正是「拿存档和库对」
    这个判据看不见的地方。

    只认自陈，不去猜。「这份评估看着单薄」是判断，
    「本贴任职要求段未展示完」是事实 —— 后者可核，前者不可。
    """

    ADMISSIONS = (
        "JD 未写年限下限（本贴任职要求段未展示完）",
        "任职要求段页面截断未读全",
        "列表页信息，JD 未提学历",
        "详情未取，按标题判",
        "没抓到正文",
    )

    def test_every_admission_is_recognised(self):
        for t in self.ADMISSIONS:
            with self.subTest(t=t):
                self.assertTrue(sm._BLIND.search(t), f"没认出这句自陈：{t}")

    def test_an_ordinary_evaluation_is_not_swept_in(self):
        """正常评估不许被卷进来 —— 队列里混进无辜的，用户就不会再信这个数。"""
        for t in ("JD 要求 8 年以上经验，他 13 年，过",
                  "JD 写明需要零售行业背景",
                  "这一维给 65：业务领域对不上",
                  "综合得分：63/100"):
            with self.subTest(t=t):
                self.assertIsNone(sm._BLIND.search(t), f"误伤了这句：{t}")

    def test_a_finding_about_the_jd_is_not_an_admission(self):
        """**「JD 未写年限下限」是结论，不是失明。** 这条守的是一次真实的误报。

        2026-08-30 第一版把 `audit_pipeline` 那条正则抄了进来 ——
        那条问的是**反方向**的事：「你说 JD 里没写，可库里根本没有这份 JD，
        你凭什么说」。JD 在库里时它就不成立了。

        抄过来之后同一个正则在这里变成了「自陈没读到」，于是报出 **86 个**，
        逐个查下来 **0 个是真的**。抄来的正则带着原处的形状，却换了含义 ——
        「同一件事有多个住址」的另一种长相。
        """
        for t in ("JD 未写年限下限",
                  "JD 没有要求学历",
                  "JD 未提是否大小周",
                  "JD 不限行业",
                  "JD 没写薪资"):
            with self.subTest(t=t):
                self.assertIsNone(
                    sm._BLIND.search(t),
                    f"「{t}」被当成了自陈失明 —— 它是结论，不是失明")

    def test_the_two_directions_do_not_share_a_pattern(self):
        """两个方向各有各的正则，别再让它们合流。"""
        ap = (ROOT / "tools" / "audit_pipeline.py").read_text(encoding="utf-8")
        self.assertIn("_NEGATIVE_CLAIM", ap, "反方向那条正则不在了？")
        src = (ROOT / "tools" / "stale_materials.py").read_text(encoding="utf-8")
        seg = src[src.index("_BLIND = re.compile("):]
        seg = seg[:seg.index(")")]
        self.assertNotIn("要求|提|写", seg,
                         "「JD 未写…」那一支又被抄进 _BLIND 了")


class TheQueueCanBeDrained(unittest.TestCase):
    """重跑过的要能出队 —— 判据是评估里那行 `重跑日期：`。

    **不能靠「说明里还提不提那句自陈」判。** 重跑时按 `job-apply.md` 要写清
    「凭 JD 里哪一句改的」，那段说明一般会引用原来那句「本贴任职要求段未展示完」
    —— 于是同一个岗永远命中，面板上那个数永远不降。
    **排不空的队列就成了「等」**，而「等」不是下一步（`AGENTS.md`）。
    """

    def test_a_stamped_evaluation_leaves_the_queue(self):
        stamped = ("硬性条件表原写着「本贴任职要求段未展示完」，现已读全。\n"
                   "重跑日期：2026-08-30\n")
        self.assertTrue(sm._BLIND.search(stamped), "自陈还在（本来就该在）")
        self.assertTrue(sm._REREAD.search(stamped), "有戳却没认出来 —— 队列排不空")

    def test_a_vague_stamp_does_not_count(self):
        for t in ("重跑日期：昨天", "重跑过了", "重跑日期："):
            with self.subTest(t=t):
                self.assertIsNone(sm._REREAD.search(t))

    def test_the_stamp_lives_in_the_evaluation_not_the_store(self):
        """写它的是 `/job-apply`，而那条命令不依赖 Python —— 让它改 JSON 就毁约了。"""
        src = (ROOT / "tools" / "stale_materials.py").read_text(encoding="utf-8")
        seg = src[src.index("def plan("):]
        self.assertIn("_REREAD.search(text)", seg,
                      "出队判据要从评估正文读，不是从职位库读")
        self.assertIn("重跑日期", APPLY, "apply.md 没告诉执行者要留这个戳")


class WhetherTheJdIsCachedIsNotAGate(unittest.TestCase):
    """JD 没抓回来的**照样入队** —— 那不是排除条件，是「重跑时先抓一下」。

    第一版拿它当排除（理由写的是「重跑也读不到新东西」），实测挡掉了 7 个岗。
    那是一道自己发明的闸门：`/job-apply` 本来就会去抓 JD，
    而「你不该因为任何原因限制浏览器的使用」是 2026-08-27 的用户裁定。
    """

    def test_the_row_says_whether_it_needs_a_fetch(self):
        src = (ROOT / "tools" / "stale_materials.py").read_text(encoding="utf-8")
        self.assertIn("jdReady", src, "行里没说要不要先抓 —— 那是重跑前要知道的事")

    def test_it_is_not_used_to_exclude(self):
        src = (ROOT / "tools" / "stale_materials.py").read_text(encoding="utf-8")
        seg = src[src.index("def plan("):src.index("def main(")]
        self.assertNotIn("JD 至今没入库", seg,
                         "又把「JD 没抓回来」当成排除条件了")


class TheRetractedConditionStaysRetracted(unittest.TestCase):
    """「而那份 JD 现在已经入库」这个入队条件 2026-08-30 撤了 —— 别让它回来。

    撤的理由：那是一道自己发明的闸门。`/job-apply` 本来就会去抓职位描述，
    而「你不该因为任何原因限制浏览器的使用」是 2026-08-27 的用户裁定。
    JD 在不在库里只影响**重跑时要不要先抓**，不影响该不该重跑。

    ⚠️ 撤的时候正文改了，**而收尾那段代码块的注释没跟上** ——
    它一直停在旧条件上（「或当时没读到 JD、而那份 JD 现在已经入库」）。
    同一节被反复小改就是这么留下自相矛盾的：正文和它旁边的注释各说各的。
    """

    FILES = ("workflows/job-auto.md", "workflows/job-apply.md",
             "tools/stale_materials.py")

    def test_no_copy_still_carries_it(self):
        for name in self.FILES:
            with self.subTest(name=name):
                t = (ROOT / name).read_text(encoding="utf-8")
                for phrase in ("而那份 JD 现在已经入库",
                               "JD 现在已经在详情库里了"):
                    self.assertNotIn(phrase, t,
                                     f"{name} 里那个撤掉的入队条件又回来了")

    def test_the_current_rule_is_stated(self):
        t = (ROOT / "workflows" / "job-auto.md").read_text(encoding="utf-8")
        self.assertIn("只影响重跑时要不要先抓", t)


class TwoReportsOnTheSameJobsSayWhichActionDiffers(unittest.TestCase):
    """收尾里有两份「该修什么」，而它们点的多半是同一批岗。

    实测 2026-08-30：这里报的 7 个里 **6 个自检那一档也点到了**
    （缺小节 / 没写投前必问）。而两边给的动作**不是一件事**：

        自检收尾   「一次补完：/job-apply 全部」   走补漏那条路，只补缺的那一节
        这里       「/job-apply --stale」        把职位描述读回来，整份重判

    跑完前者的人会以为这 6 个也处理了 —— 而判断原样留着。
    差别不是措辞，所以要说破。
    """

    def test_it_says_the_other_report_is_not_enough(self):
        src = (ROOT / "tools" / "stale_materials.py").read_text(encoding="utf-8")
        i = src.index("/job-apply --stale")
        seg = " ".join(src[i:i + 900].split())
        self.assertIn("只补缺的那一节", seg)
        self.assertIn("整份重跑", seg)

    def test_no_placeholder_leaks_into_the_output(self):
        """占位符漏到屏幕上过一次（`@N`），钉住别再来。"""
        src = (ROOT / "tools" / "stale_materials.py").read_text(encoding="utf-8")
        self.assertNotIn("@N", src)


class TheQueueReachesTheUser(unittest.TestCase):
    """算出来了、没送到屏幕上，等于没算。

    此前这条队列只在 `/job-auto` 收尾的终端输出里一闪而过 —— 而终端日志没人看，
    同一课 `staleCode` 那条注释里记着（2026-08-13 一天撞三次）。
    """

    def test_the_exporter_tags_each_job(self):
        self.assertIn("def mark_restale(", EXPORT)
        self.assertIn('"restaleCount"', EXPORT)

    def test_the_normalizer_lets_it_through(self):
        """`normalize` 是手写白名单 —— 漏在那儿的话 `/data.json` 里有、页面就是不渲染。"""
        self.assertIn("restaleCount: d.restaleCount", LOAD)

    def test_the_list_marks_which_ones(self):
        """**顶上给了数，名单上就要认得出是哪几个。**

        同一个形状这一页修过一次：「其中 N 个排了两周以上，从它们开始」那句
        一直在印，而名单按分数排、没有任何东西标出是哪几个 —— 照它做，
        他得逐个点开 60 次，而点开也看不到（那个数当时根本没上过屏）。
        判据写在 `Shortlist.tsx` 那条注释里，这里钉住它别再重演。

        逐岗那个字段（`restale`）此前只有命令行侧在用（`/job-apply --stale`
        从快照选岗），面板一个字都没显示 —— 实测扫「导出了没人用的字段」时
        它是全库唯一一个。
        """
        self.assertIn("job.restale", LIST,
                      "顶上说了「N 个岗该重跑」，名单上却认不出是哪几个")

    def test_the_fold_says_how_many_are_inside(self):
        """**章在折叠后面等于没标。**

        那 7 个实测（2026-08-30）全部落在「可以考虑」那一档，而那一档在总览页上
        是**折叠**的 —— 顶上说「N 个岗的判断该重跑一遍」，首屏一个都看不到。

        折叠标签那行字**是他决定「要不要点开」时唯一读到的东西**，同一位置
        已经为「还没读过 JD」补过一次同样的数。这条钉住这一次别再漏。
        """
        self.assertIn("个的判断该重跑", APP,
                      "折叠标签里没说这一档藏着几个该重跑的")
        self.assertIn("nRestStale", APP)

    def test_the_fold_count_uses_the_same_field_as_the_chip(self):
        """标题说 7、点开数出来是别的数 —— 那比不说更坏。"""
        i = APP.index("const nRestStale")
        self.assertIn("j.restale", APP[i:i + 200])

    def test_the_chip_does_not_invent_its_own_wording(self):
        """理由直接用字段的值 —— 判据只有一个住址。"""
        i = LIST.index("{job.restale && (")
        self.assertIn("{job.restale}", LIST[i:i + 700])

    def test_the_chip_says_what_to_type(self):
        i = LIST.index("{job.restale && (")
        self.assertIn("/job-apply", LIST[i:i + 700])

    def test_the_panel_prints_the_command(self):
        """按钮做不成（serve.py 不接大模型），命令必须印 —— `AGENTS.md` 那条铁律。"""
        self.assertIn("restaleCount", APP)
        self.assertIn("/job-apply --stale", APP)


class ApplySelectsFromTheSnapshot(unittest.TestCase):
    """`--stale` 的选岗走快照字段，不许在 apply.md 里跑 Python。

    两条约束在这里撞上：
    - **选岗只能有一个实现** —— `dupOf` / `materials` / `applied` 都是快照字段，
      散文口径实测第一次跑就漏了两类（同一个岗挂三个价、目录名去过括号）。
    - **`/job-apply` 不依赖 Python** —— README 与 SETUP 都这么承诺。

    第一版写成了 `python tools/stale_materials.py --urls`，两条一起违。
    改走快照字段之后那个开关就没人用了 —— 它自己的 help 还写着「喂给
    `/job-apply --stale`」，而那条路已经不经过它。**留着比删掉更坏**：
    照它敲一次会以为选岗该这么来。2026-08-30 删。
    """

    def test_the_abandoned_flag_is_gone(self):
        """弃用的开关要删掉，不是留在那儿等人照着敲。"""
        src = (ROOT / "tools" / "stale_materials.py").read_text(encoding="utf-8")
        self.assertNotIn('add_argument("--urls"', src)

    def test_the_flag_is_documented(self):
        self.assertIn("--stale", APPLY,
                      "工具把 `/job-apply --stale` 印给用户看了，而 apply.md 里没这个开关")

    def test_it_picks_by_the_snapshot_field(self):
        self.assertIn('j["restale"]', APPLY)

    def test_no_python_sneaks_in(self):
        import re
        self.assertNotRegex(APPLY, r"python\s+tools/",
                            "apply.md 里出现了 python 命令 —— 没装 Python 的人就用不了它了")

    def test_it_says_applied_ones_are_out(self):
        seg = APPLY[APPLY.index("#### 重跑不该再信的判断"):]
        self.assertIn("已投的", seg[:2000])


class TheAutoRunReportsIt(unittest.TestCase):
    def test_job_auto_runs_it_in_the_closing_steps(self):
        self.assertIn("tools/stale_materials.py", AUTO)

    def test_it_says_why_the_panel_cannot_have_a_button(self):
        """用户问过「能不能做个按钮」——答不能，要说清为什么，不然会再问一次。"""
        self.assertIn("serve.py", AUTO)
        self.assertIn("不接大模型", AUTO)

    def test_it_says_applied_ones_are_out_of_scope(self):
        self.assertIn("已投的不算", AUTO)


if __name__ == "__main__":
    unittest.main()
