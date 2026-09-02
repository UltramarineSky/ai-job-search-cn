"""自动模式的停手条件必须是「跑不下去」，不能是「结果不理想」。

## 为什么单独钉这一条

`/job-apply` 的批量规则里有一句用血换来的话：「**「结论不理想」不是停手条件。**
用户说 `--top 20` 就跑满 20 个……它把**产出**误当成了**失败**」。当时那条第三停手
条件（「深评连续 5 个没过闸门就停」）已经被删掉。

`/job-auto` 把 rank 与 apply 串起来自动跑，**同一个诱惑会以三种新形态回来**：

| 会被写成 | 为什么是错的 |
|---|---|
| 「这批一个能投的都没有，停」 | 那批岗已经落了分、出了待评堆，正是要的东西 |
| 「已经找到不少好岗了，停」 | 剩下的岗不会因为前面有好岗就不值得评 |
| 「跑太久了，停」 | 用户要的就是不用盯着；要控规模该调 `--target` |

自动模式没有人在旁边看，早停是**静默**的——队列没排空，而报告说「跑完了」。
所以停手条件写成机制、并在这里逐条钉住。
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AUTO = ROOT / "workflows" / "job-auto.md"
RANK = ROOT / "workflows" / "job-rank.md"


class TheAutoWorkflowIsWired(unittest.TestCase):

    def test_it_exists_and_has_a_stub(self):
        self.assertTrue(AUTO.is_file(), "workflows/job-auto.md 不见了")
        self.assertTrue((ROOT / ".claude" / "commands" / "job-auto.md").is_file(),
                        "没有 stub —— 用户敲 /job-auto 会敲空")

    def test_it_is_listed_in_the_index(self):
        """索引是权威来源，也是面板那份帮助的正文（见 AGENTS.md 那张表）。"""
        t = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("workflows/job-auto.md", t,
                      "/job-auto 没进工作流索引 —— 面板上查无此人")

    def test_it_chains_the_two_real_workflows(self):
        t = AUTO.read_text(encoding="utf-8")
        for cmd in ("/job-rank", "/job-apply"):
            self.assertIn(cmd, t, f"{cmd} 没被串进来，那这条命令没有存在意义")


class StopConditionsAreAboutBeingBlockedNotDisappointed(unittest.TestCase):

    #: 必须明写的停手条件——缺一条，执行时就只能临场判断。
    REQUIRED = ["风控", "连续 2 次", "队列排空", "用户喊停"]

    #: 明令**不是**停手条件的三种诱惑。
    FORBIDDEN_AS_STOP = ["一个能投的都没有", "已经找到不少好岗", "跑得有点久"]

    def test_every_real_stop_condition_is_written_down(self):
        t = AUTO.read_text(encoding="utf-8")
        for c in self.REQUIRED:
            with self.subTest(c=c):
                self.assertIn(c, t, f"停手条件「{c}」没写进去")

    def test_the_three_temptations_are_named_and_refused(self):
        """光不写还不够——要**点名说它们不是**，否则下一个人会自己加回来。

        这正是 apply.md 的做法：它没有默默删掉那条第三停手条件，而是留了一段
        说明它为什么错。规则删了会被重新发明，理由写下来才不会。
        """
        t = AUTO.read_text(encoding="utf-8")
        for c in self.FORBIDDEN_AS_STOP:
            with self.subTest(c=c):
                self.assertIn(c, t, f"没有点名拒绝「{c}」这条假停手条件")

    def test_there_is_a_runaway_backstop(self):
        """允许无限循环的自动模式迟早会跑飞。要有上限，且说明它是兜底不是正常出口。"""
        t = AUTO.read_text(encoding="utf-8")
        self.assertTrue(re.search(r"跑满\s*\d+\s*轮", t), "没有防跑飞的轮数上限")
        self.assertIn("不是正常出口", t, "上限没说清它是兜底，会被当成设计意图")


class AutoNeverActsOnTheUsersBehalf(unittest.TestCase):
    """自动模式最危险的地方不是跑得久，是**替用户做了不该它做的事**。"""

    def test_it_never_submits(self):
        t = AUTO.read_text(encoding="utf-8")
        self.assertIn("不投递", t, "没写清自动模式只出材料、不投递")
        self.assertTrue("不发邮件" in t or "不填表单" in t,
                        "没排除自动投递/发邮件——那是用户自己点的那一下")

    def test_scraping_defaults_follow_the_channel_not_the_word(self):
        """补货的默认值按**渠道风险**分，不按「抓取」这个动作名一刀切。

        **这条 2026-08-19 改过两次，方向相反。**

        第一版是「抓取默认关着，该由人明确点头」。那句话只对浏览器渠道成立——
        猎聘 CLI 免登录直连、一次都不碰账号——于是改成「免登录默认开、浏览器
        默认关（`--browser-scrape` 才开）」。

        第二版（本人裁定「默认应该是勾选」）连浏览器三家也跟着面板勾选走。
        触发它的是一个数：**全库 85% 的岗来自猎聘，而命中率最高的 BOSS
        （13.5% vs 猎聘 4.8%）只抓到 126 个。** 根因是「勾选 AND flag」——
        用户在面板把四家勾上，命令行侧仍然只跑猎聘：**勾选框只有否决权、
        没有启动权**，且没有任何地方提示他还差一个 flag。

        所以现在盯的是：只有一个开关（面板勾选），风险由额度闸门管而不是由
        「默认关掉」管，以及要留一个临时不碰账号的出口。
        """
        t = AUTO.read_text(encoding="utf-8")
        self.assertIn("--no-browser", t, "没留「这一轮别碰我账号」的出口")
        self.assertIn("portals.json", t, "没写清唯一的开关是面板那份勾选")
        self.assertIn("portal_budget", t,
                      "默认放开了却没指向额度闸门——风险就真的没人管了")
        self.assertNotIn("**与**的关系", t,
                         "「勾选 AND --browser-scrape」又写回去了：勾了不生效，"
                         "用户会以为四家都在抓")

    def test_the_word_list_is_written_back_every_scrape(self):
        """自动循环会把「用挖空的词反复抓」放大成十几轮无效请求。"""
        t = AUTO.read_text(encoding="utf-8")
        self.assertIn("query_yield.py --apply", t,
                      "补货后没写回词表，下一轮还会用同一批挖空的词")

    def test_a_dry_scrape_run_is_a_stop_condition_but_a_bad_batch_is_not(self):
        """「连续 2 轮零新增」是「走不动了」，与「产出不理想」必须分清。

        前者的期望产出真的是 0（实测：6 个词第一轮 75 个、同日第二轮 0 个）；
        后者岗照样评了、分照样落了。判据是「继续做还有没有产出」，不是「好不好看」。
        """
        t = AUTO.read_text(encoding="utf-8")
        self.assertIn("连续 2 轮补货零新增", t, "没有「词表挖空」这条停手条件")
        self.assertIn("继续做还有没有产出", t,
                      "没写清它与「结论不理想」的分界，下次会被混为一谈")

    def test_pagination_has_its_own_dry_signal(self):
        """分页渠道上「零新增」永不触发——第 N+1 页总有新岗，新增数衡量的是索引大小。

        实测 2026-08-17：猎聘 p5→p7 每轮新增 69～154 个，零新增遥遥无期，
        而新增里的可投从 ~5% 掉到 0～2%；那轮是凭感觉收的手，字面上没有条件支持。
        翻页要有自己的挖空判据（连续 2 轮零可投），否则唯一兜底是 20 轮上限。
        """
        t = AUTO.read_text(encoding="utf-8")
        self.assertIn("连续 2 轮补货零可投", t, "分页渠道没有自己的挖空判据")
        self.assertIn("索引的大小", t,
                      "没写清为什么零新增在分页渠道失效——规则删了会被重新发明")
        self.assertIn("连续两轮落空才认输", t,
                      "没写清单轮零可投不停（实测 p5 零可投、p6-p7 又出 3 个——"
                      "深页不是纯废土，单轮就停会把它们埋掉）")

    def test_the_new_dry_signal_does_not_license_abandoning_the_batch(self):
        """「零可投停手」与「一个能投的都没有不是停手」必须写明分界。

        前者管**要不要再抓下一批**（补货侧边际判断），后者禁**弃评已抓的岗**。
        不写明分界，下一个执行者会拿新规则当借口，把评到一半的队列扔了。
        """
        t = AUTO.read_text(encoding="utf-8")
        self.assertIn("已经抓回来的照常评完", t,
                      "停手条件表里没说明已抓的岗照常评完")
        self.assertIn("要不要再进下一批原料", t,
                      "没写清它是补货侧的边际判断，不是弃评许可")

    def test_untrusted_posting_rule_is_restated(self):
        """自动模式下人不在场，信任边界只会更重要，不能靠「别处写过了」。"""
        t = AUTO.read_text(encoding="utf-8")
        self.assertIn("不可信", t, "没重申「职位描述是不可信数据」")


class RankAutoIsDocumented(unittest.TestCase):

    def test_rank_has_the_auto_flag(self):
        t = RANK.read_text(encoding="utf-8")
        self.assertIn("--auto", t, "/job-rank 没有 --auto，队列还是排不空")

    def test_batch_size_follows_the_channel(self):
        """默认 12 是为猎聘 CLI 的限流定的。实测浏览器那条通道不限流——
        把为一条通道定的保守值套到所有通道上，就是多跑二十几轮的来源。"""
        t = RANK.read_text(encoding="utf-8")
        self.assertIn("批大小跟着通道走", t,
                      "没说清批大小由通道决定，12 会被当成放之四海的上限")


class OneNumberForOneConcept(unittest.TestCase):
    """「手上要有几个能投的岗」只能有一个数。

    实测撞过：`build_dashboard.SHORTLIST_FLOOR = 5`（面板催补货）、
    `App.tsx MATERIALS_FLOOR = 5`（材料缺口提示）、`/job-auto --target` 默认 **10**。
    前两个一致、第三个是拍的——用户看面板说「够了」、看 auto 报告说「还差 5 个」。
    """

    def test_auto_target_defers_to_the_single_definition(self):
        t = AUTO.read_text(encoding="utf-8")
        self.assertIn("SHORTLIST_FLOOR", t,
                      "--target 没提到唯一定义，又会被拍一个数出来")
        # 边界匹配，别用子串：`assertNotIn("默认 10")` 会被「默认 100」命中
        # ——2026-08-13 正文里引用用户原话「auto 是不是直接默认 100」时当场误报。
        # 拿数字做子串检查，早晚撞上一个更长的数字。
        self.assertIsNone(re.search(r"默认\s*10(?!\d)", t), "还留着写死的默认 10")

    def _usage_block(self) -> list:
        t = AUTO.read_text(encoding="utf-8")
        i = t.index("## 用法")
        return t[i:t.index("###", i)].splitlines()

    def test_the_bare_command_does_not_name_a_number(self):
        """用法块里裸 `/job-auto` 那行不许出现「N 个」—— 那就是在给它一个默认目标。

        ## 判据为什么从「措辞」改成「形状」

        上一条只认死一个词：`默认 10`。2026-08-21 像执行者一样通读时，
        同一个数换个说法就绕过去了，而且**一次绕过两处**：

        - 用法块：`# 目标：凑齐 10 个材料就绪的岗` —— 和 6 行之下的
          「不给就是不设目标」当场自相矛盾；
        - 示例输出：`[N] 可投的岗位已达 10 个，转出材料` —— 把 2026-08-13
          撤掉的那个默认**原样演了一遍**，照着做的执行者会真攒到 10 就停。

        **一个数漂移时不会带着原来的措辞一起漂。** 所以判据改认形状：
        裸命令（整行不带任何 `--`）的注释里出现 `N 个`，就是在写一个收工数。
        带 `--target 20` 的那行不管 —— 它本来就该有数。
        """
        bare = [l for l in self._usage_block()
                if l.strip().startswith("/job-auto") and "--" not in l]
        self.assertTrue(bare, "用法块里找不到裸 `/job-auto` 那一行了")
        for l in bare:
            with self.subTest(line=l.strip()):
                self.assertIsNone(
                    re.search(r"\d+\s*个", l),
                    "裸 `/job-auto` 的注释里写了个收工数，而 `--target` 那条说的是"
                    "「不给就是不设目标」。两处打架时用户信的是用法块 —— 它在最上面："
                    + l.strip())

    def test_the_sample_run_does_not_demo_a_default_target(self):
        """示例输出同样不许演「达到 N 个就转材料」—— 示例比散文更容易被照抄。"""
        t = AUTO.read_text(encoding="utf-8")
        self.assertIsNone(
            re.search(r"可投的岗位已达\s*\d+\s*个", t),
            "示例把撤掉的默认目标又演了一遍；没给 --target 时收尾的是停手条件")

    def test_the_shape_check_can_fire(self):
        """变异内建：换个说法的默认目标也要被认出来，正确写法不许误报。"""
        for bad in ("/job-auto   # 目标：凑齐 10 个材料就绪的岗",
                    "/job-auto   # 攒够 5 个就收工",
                    "/job-auto   # 默认 10 个"):
            with self.subTest(bad=bad):
                self.assertIsNotNone(re.search(r"\d+\s*个", bad),
                                     "这种写法没被认出来：" + bad)
        for ok in ("/job-auto   # 不设目标：跑到挖不动为止",
                   "/job-auto --target 20         # 要 20 个"):
            with self.subTest(ok=ok):
                bare = ok.strip().startswith("/job-auto") and "--" not in ok
                self.assertFalse(bare and re.search(r"\d+\s*个", ok),
                                 "正确写法被误报：" + ok)

    def test_the_definition_says_it_is_the_only_one(self):
        src = (ROOT / "tools" / "build_dashboard.py").read_text(encoding="utf-8")
        self.assertIn("唯一的「够不够」定义", src,
                      "常量没声明自己是唯一来源，下次还会有人另写一个")


class ScrapingReportsTheImbalanceButNeverGatesOnIt(unittest.TestCase):
    """**这条 2026-08-27 被用户裁定翻掉了一半，翻掉的正是「拦」那一半。**

    原来 Step 0.5 是一道判据：按「可投的岗够不够 5 个」「待评队列空不空」分三种
    情况，其中一种是**先别抓**（队列还堆着时说「缺的不是岗，是评」）。
    它的立论是 2026-08-12 那次实测：一轮抓回 210 个新岗、同日只评掉 12 个，
    待评堆到 589。

    用户原话（2026-08-27）：「job-scrape.md Step 0.5 的判据是假的，去除。
    **你不该因为任何原因限制浏览器的使用**。」

    立论确实已经不成立：它的前提是「评比抓慢得多」，而那来自「抓完停在待评」的
    旧流程；现在抓完自动评（`job-scrape.md` Step 5.5）、`/job-auto` 把三段接成了循环。
    同日实测：一轮抓回 140 个，当天全部评完、出了 7 份材料。

    而它的实际损害是可见的：同一天执行者照那张表判定「队列还有一堆 → 先别抓」，
    于是 BOSS、智联、前程三家整轮一个新岗都没抓 —— **而那三家只有浏览器这一条路**。
    一道为「防积压」写的判据，实际效果是关掉了三家渠道。

    所以这条守卫现在验两件事：**那道门真的没了**，以及**报数那一半还在**
    （它不拦人，只让用户看见比例失衡）。
    """

    SCRAPE = ROOT / "workflows" / "job-scrape.md"

    def test_the_gate_is_gone(self):
        """**验的是那张表没了，不是那几个字不许出现。**

        文里现在仍然会引到「先别抓」「缺的不是岗，是评」—— 那是在解释为什么撤掉它，
        引用不等于生效。所以判据取那张表的结构：三行判据表里的那一行。
        （同一形状 `test_a_deleted_quota_is_not_still_quoted` 里记过：
        「删掉的东西还被当规则引用」和「作为历史被引用」要分开。）
        """
        t = self.SCRAPE.read_text(encoding="utf-8")
        self.assertNotIn("| 可投的岗 < 5 **但**待评队列还有一堆 |", t,
                         "那道「先别抓」的判据表又回来了 —— 2026-08-27 用户裁定去除")
        self.assertNotIn("| 现在的状态 | 该做什么 |", t)
        # 剩下的那几处必须都在裁定说明的引号里，不能是祈使句
        for line in t.splitlines():
            if "先别抓" in line:
                self.assertTrue(line.lstrip().startswith(">"),
                                f"这一行不在裁定说明的引用块里：{line.strip()[:40]}")

    def test_the_ruling_is_recorded_where_the_gate_used_to_be(self):
        """裁定要留在原地，否则下一个人会照旧把它加回来。"""
        t = self.SCRAPE.read_text(encoding="utf-8")
        self.assertIn("2026-08-27 用户裁定去掉", t)
        self.assertIn("你不该因为任何原因限制浏览器的使用", t)

    def test_it_records_what_the_gate_actually_cost(self):
        """撤一条规则要写清它当时的代价，不然看起来像随手删的。"""
        t = self.SCRAPE.read_text(encoding="utf-8")
        self.assertIn("BOSS、智联、前程三家整轮一个新岗都没抓", t)
        self.assertIn("只有浏览器这一条路", t, "没写清那三家为什么被这道门关掉")

    def test_it_reports_the_imbalance_instead_of_silently_piling_up(self):
        """**报数那一半保留** —— 它不拦人，只是把失衡说出来。"""
        t = self.SCRAPE.read_text(encoding="utf-8")
        self.assertIn("评的速度跟不上抓的速度", t,
                      "比例失衡不说出来，用户看不见积压是怎么形成的")
        self.assertIn("说出来比拦住更重要", t)


class AutoFinishesTheJob(unittest.TestCase):

    def test_it_refreshes_the_panel_at_the_end(self):
        """跑完不刷新，用户打开面板看到的是跑之前的状态，会以为什么都没发生。"""
        t = AUTO.read_text(encoding="utf-8")
        self.assertIn("export_web_data.py", t, "收尾没刷新面板")

    def test_per_batch_bookkeeping_is_not_a_one_off(self):
        """每批深评都产生新的写回；不补账，下一批排序读的是旧账。"""
        t = AUTO.read_text(encoding="utf-8")
        self.assertIn("每批都要跑，不是整个 auto 只跑一次", t,
                      "没说清 Step 0 那三条是每批跑")

    def test_thresholds_come_from_the_profile_not_from_asking(self):
        t = AUTO.read_text(encoding="utf-8")
        self.assertIn("不要停下来问用户", t,
                      "预筛阈值没说明从资料读——会变成每批问一次")


class TheHumanBoundaryIsWrittenDown(unittest.TestCase):
    """「哪些环节归人」必须是一张明确的表，不能靠临场判断。"""

    #: 这几件事碰到就得停下来问，一条都不能少。
    HUMAN = ["投出去那一下", "待问清单", "撞风控", "预筛结案的复核"]

    def test_the_table_exists_and_states_its_criterion(self):
        t = AUTO.read_text(encoding="utf-8")
        self.assertIn("什么归机器，什么永远归人", t)
        self.assertIn("只有用户知道、或后果是不是只有用户承担", t,
                      "没写判据，这张表就只是一份会过期的清单")

    def test_every_human_only_step_is_listed(self):
        t = AUTO.read_text(encoding="utf-8")
        for h in self.HUMAN:
            with self.subTest(h=h):
                self.assertIn(h, t, f"「{h}」没列进「永远归人」")

    def test_the_criterion_is_not_importance(self):
        """判据句与反例**两样都要在**。

        这条测试自己漏检过一次：它原来只查反例那句在不在，于是把判据句
        「不是「重要不重要」」改成「按重要程度分」之后，反例还留着，测试照绿。
        **守卫只钉住论据、没钉住论点**——而会被改坏的恰恰是论点。
        """
        t = AUTO.read_text(encoding="utf-8")
        self.assertIn("不是「重要不重要」", t,
                      "判据句被改掉了——这张表会退化成「重要的都问一下」")
        self.assertIn("不是按「重不重要」分的", t, "缺少那条反例")


class ScrapeDeliversScoredJobsNotABacklog(unittest.TestCase):
    """抓取的交付标准是「打过分的岗」，不是「待评的岗」。

    `/job-scrape` 原来在结尾写「新岗多（8+）时**也建议** `/job-rank`」。
    可**待评的岗不是可用产物**——没有分、没过硬门、不知道该不该投，在面板上只是
    一个计数。用户要的从来是「可以投的岗位」。停在待评就是交付半成品，然后靠人
    记得再敲一条命令把它做完；漏一次就多积压一批。

    实测：2026-08-12 一轮抓回 210 个新岗、评掉 12 个，待评堆到 589。

    判它归机器的依据在 `job-auto.md` 那张表里：抓多少、评几批、先评哪个
    **全部有明确判据、没有需要人判断的输入**。
    """

    SCRAPE = ROOT / "workflows" / "job-scrape.md"

    def test_scrape_chains_into_rank_by_default(self):
        """钉住**那条祈使句**，不是钉住 `/job-rank --auto` 这个词出现过。

        这条测试漏检过一次：它原来只查 `"/job-rank --auto" in t`，而那串字符在
        `--no-rank` 的参数说明里也出现。把 `job-scrape.md` Step 5.5 的指令句改回「也建议去跑」之后，
        字符串还在别处，测试照绿——**守卫钉住了词，没钉住指令**。
        本轮同一形状的漏洞出现了两次（另一次是只钉反例、没钉判据句）。
        """
        t = self.SCRAPE.read_text(encoding="utf-8")
        self.assertIn("就接着跑 `/job-rank --auto`", t,
                      "`job-scrape.md` Step 5.5 的祈使句不见了——抓完不会自动接评分")
        self.assertIn("--no-rank", t, "没有留只抓不评的出口")

    def test_it_no_longer_merely_suggests(self):
        """「建议用户去跑」就是这条摩擦本身，不能留在文件里。"""
        t = self.SCRAPE.read_text(encoding="utf-8")
        self.assertNotIn("also suggest `/job-rank`", t,
                         "还留着「建议去跑 /job-rank」——摩擦没去掉")

    def test_the_reason_is_written_down(self):
        """规则删了会被重新发明，理由写下来才不会。"""
        t = self.SCRAPE.read_text(encoding="utf-8")
        self.assertIn("交付了半成品", t, "没写清为什么不能停在待评")
        self.assertIn("可用的产物", t, "没说清「待评的岗」不是可用产物")

    def test_it_does_not_invent_its_own_stop_conditions(self):
        """评分的停手条件只有一处定义，抓取这边不许另立一套。"""
        t = self.SCRAPE.read_text(encoding="utf-8")
        self.assertIn("这里不另立一套", t,
                      "没声明沿用 job-rank 的停手条件——两处定义迟早会分叉")


# 「投哪几个要问一次」的旧守卫已删（2026-08-12 用户裁定撤闸门）：出材料花的是
# AI 的工时不是用户的，按分数取也没有只有用户知道的输入。新规则由
# `test_commands_chain_automatically.MaterialsFollowScoresWithoutAGate` 钉住
#（那个类名 2026-08-31 之前**一直不存在** —— 声称有守卫比没有更糟，现在它真的在了），
# 裁定轨迹写在 `workflows/job-rank.md` Step 5——别按「材料很贵所以要问」把闸门加回来。


class TheTargetCheckComesBeforeTheRefill(unittest.TestCase):
    """`--target` 的判据必须排在「补货」之前，否则它永远够不着。

    ## 通读才看得出来的一处

    循环原来是这么写的：

        1. 队列里还有待评的 → 跑 /job-rank
        2. 队列空了：
             允许补货 → 抓一轮，回到 1
             不允许   → 跳出
        3. 给了 --target 且 可投 ≥ target → 跳出

    **`/job-rank` 会评到排空**，所以第 1 步跑完队列必空 → 第 2 步必然触发 →
    允许补货时那一支以「回到 1」收尾。**第 3 步够不着。**
    结果是 `/job-auto --target 20` 攒够 20 个照样继续抓下一轮，
    而停手条件表里明写着「达到 `--target` → 正常结束」——**伪代码与表自相矛盾**。

    八把机械尺子都没扫出这一处：它不是拼写、不是缺字、不是没人调用，
    是**步骤顺序**。2026-08-21 像执行者一样通读时发现。

    ## 判据

    在循环那个围栏块里比两处的行号：出现 `--target` 判据的那一行，
    必须早于出现「允许补货」的那一行。**比的是顺序，不是措辞。**
    """

    def _loop_block(self) -> list:
        t = (ROOT / "workflows" / "job-auto.md").read_text(encoding="utf-8")
        i = t.index("## 循环")
        seg = t[i:t.index("### 每批都要跑的机械步骤", i)]
        return seg.splitlines()

    def test_target_is_checked_before_the_refill_branch(self):
        lines = self._loop_block()
        tgt = next((i for i, l in enumerate(lines)
                    if "--target" in l and "跳出" in l), None)
        refill = next((i for i, l in enumerate(lines) if "允许补货" in l), None)
        self.assertIsNotNone(tgt, "循环里找不到 --target 的跳出判据了")
        self.assertIsNotNone(refill, "循环里找不到补货那一支了")
        self.assertLess(
            tgt, refill,
            "`--target` 的判据排在补货之后 —— 而 rank 会评到排空、补货那一支以"
            "「回到 1」收尾，所以它永远够不着：`--target 20` 攒够了照样继续抓")

    def test_the_stop_table_still_lists_target(self):
        """停手条件表里那一行也要在 —— 两处说的是同一件事，缺一处就又对不上。"""
        t = (ROOT / "workflows" / "job-auto.md").read_text(encoding="utf-8")
        self.assertRegex(
            t, r"达到\s*`?--target`?\s*\|",
            "停手条件表里没有「达到 --target」那一行了")



class StoppingDoesNotSkipTheMaterials(unittest.TestCase):
    """停手停的是「再进新原料」，不是「把手上的做完」。

    `出材料` 写在循环之外、停手之后。而这一节原来有一句
    「任一子流程停手，**整个自动模式就停**」—— 它把出材料整个短路掉了。

    实测代价（2026-08-26 一次 `/job-auto`）：队列里 63 个待评，`/job-rank`
    抓 JD 撞额度停手 → 照那句话整个 auto 停 → **同一轮刚评出来的 4 个
    「可以投」的岗一份材料都没出**。用户当场问「进入可以投的岗位应该自动
    读 JD、准备资料，流程哪里出了问题」。

    对的说法本来就在同一个文件里，只是只挂在「连续 2 轮补货零可投」那一条上
    （「已经抓回来的照常评完、该出的材料照出」）。现在提成通则。

    判据也在文件里现成：**收尾三条标着「无条件」，而出材料没标** —— 写盘对账
    无条件跑、产出用户真正要的东西反而可跳过，顺序反了。
    """

    def test_materials_are_unconditional(self):
        t = AUTO.read_text(encoding='utf-8')
        i = t.index("出材料（")
        j = t.index("收尾（无条件）", i)
        seg = t[i:j]
        self.assertIn("无条件", seg, "出材料这一步没标成无条件")
        self.assertRegex(seg, r"不管循环是怎么退出的|每条退出路径",
                         "没写清「怎么退出的都要跑」")

    def test_the_short_circuit_sentence_is_gone(self):
        """这句话是那个 bug 本身，不许写回来。"""
        t = AUTO.read_text(encoding='utf-8')
        body = chr(10).join(l for l in t.splitlines()
                            if not l.lstrip().startswith(">"))
        self.assertNotIn("整个自动模式就停", body,
                         "「任一子流程停手，整个自动模式就停」写回来了 —— "
                         "它会把循环之外的出材料整个跳过")

    def test_the_budget_stops_say_materials_still_run(self):
        """会撞额度/风控的那几条，各自都要点明材料照出。"""
        t = AUTO.read_text(encoding='utf-8')
        i = t.index("## 停手条件")
        # 表尾用「循环跑满 20 轮」那一行定位 —— 它是最后一条，且不会被改写。
        j = t.index("| **循环跑满 20 轮**", i)
        seg = t[i:j]
        self.assertGreaterEqual(
            seg.count("照常出材料"), 3,
            "撞验证码/撞限流/连续 2 次错 这三条里，没有都写明材料照出")

if __name__ == "__main__":
    unittest.main()
