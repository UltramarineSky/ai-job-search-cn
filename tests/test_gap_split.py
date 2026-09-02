"""差距分四格：`/job-upskill` 不能把选岗问题答成学习任务。

`/job-upskill` 的默认动作是**开学习计划**。默认动作有默认动作的危险：一个只会开学习
清单的命令，必然把选岗问题也答成学习任务。

同一份评估里的两笔说的是两件事（`04-job-evaluation.md`）：专业能力低是**学得会
的**，业务域低是**要换赛道、或者干脆投错了地方**。Step 2 早就写明两笔性质不同，
但那只管取数——结论层（Step 5/6）原来无条件产出学习计划，没有任何出口。

实测某用户 96 份可回读评估：「选岗问题」20 个，「可以靠学」只有 6 个。直接出
学习计划，等于让他花几周学一批本来就够格的东西，而真正的问题一个字没提。
**跑错方向的代价是几周，比少列几个技能点大得多。**
"""

import json
import shutil
import sys
import re
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import gap_split as gs  # noqa: E402


def E(stack, domain, **kw):
    return {"status": "ranked", "title": kw.get("title", "岗"),
            "company": kw.get("company", "某公司"),
            "rank_breakdown": {"四维": f"专业能力{stack}×0.6+业务域{domain}×0.4"}}


class QuadrantBoundariesComeFromTheFramework(unittest.TestCase):
    """分界必须能说出出处，不能是从手上这份样本凑的。"""

    def test_boundaries_match_the_framework_bands(self):
        """**这条原来只把常量钉成 70，从没去框架里核过。**

        类名写着「分界来自框架」、docstring 写着「必须能说出出处」，
        而 04 那两张表的分档是 80/60/40 —— 根本没有 70。更巧的是 04 里
        有一整段专门讲这个数：判词天花板第二版定成 70/50/30，
        「依据是用实测案例校准 —— 那是过拟合」，后来撤掉了。
        一个自称验出处的测试，钉的正是被撤掉的那个数。

        现在真的去读那两张表，确认这两条线都是**某一档的下沿**。
        """
        self.assertEqual(gs.DOMAIN_OK, 60)
        import export_web_data as ex
        self.assertEqual(gs.DOMAIN_OK, ex.SWEET_SPOT_DOMAIN,
                         "业务域分界与导出器的「主场」口径不一致 —— 两处会各说各的")
        eva = (ROOT / "workflows" / "reference"
               / "04-job-evaluation.md").read_text(encoding="utf-8")
        for name, head, tail, val in (
                ("专业能力", "#### 1.1", "#### 1.2", gs.STACK_OK),
                ("业务域", "#### 1.2", "#### 1.3", gs.DOMAIN_OK)):
            with self.subTest(name=name):
                sec = eva[eva.index(head):eva.index(tail)]
                lows = {int(m) for m in
                        re.findall(r"(?m)^\| (\d+)-\d+ \|", sec)}
                self.assertTrue(lows, f"{name} 那一节读不到分档表了")
                self.assertIn(val, lows,
                              f"{name} 分界 {val} 不是框架里任何一档的下沿"
                              f"（那张表的下沿是 {sorted(lows)}）")

    def test_each_line_is_the_band_it_names(self):
        """光验「是某一档的下沿」不够 —— 80 也是下沿，照样绿（变异实测）。

        注释各自点了名是哪一档，这里就按那个名字去表里取下沿。改成 80
        而不改注释里点的那一档，这条会红。
        """
        eva = (ROOT / "workflows" / "reference"
               / "04-job-evaluation.md").read_text(encoding="utf-8")

        def low_of(head, tail, keyword):
            sec = eva[eva.index(head):eva.index(tail)]
            for lo, text in re.findall(r"(?m)^\| (\d+)-\d+ \| ([^|]+)\|", sec):
                if keyword in text:
                    return int(lo)
            return None

        self.assertEqual(gs.STACK_OK,
                         low_of("#### 1.1", "#### 1.2", "主要要求命中"),
                         "专业能力那条线不再是「主要要求命中」那一档的下沿")
        self.assertEqual(gs.DOMAIN_OK,
                         low_of("#### 1.2", "#### 1.3", "相邻域"),
                         "业务域那条线不再是「相邻域」那一档的下沿")

    def test_the_reason_for_sixty_not_eighty_is_recorded(self):
        """60 和 80 都是档位下沿 —— 选哪个要说清，否则下一版会照着另一个改。"""
        src = (ROOT / "tools" / "gap_split.py").read_text(encoding="utf-8")
        i = src.index("STACK_OK = ")
        seg = " ".join(src[max(0, i - 1600):i].replace("#:", " ").split())
        self.assertIn("值得投 —— 投，在沟通中主动补缺口", seg)
        self.assertIn("那张表根本没有 70", seg)
        self.assertIn("那是过拟合", seg)

    def test_each_corner_lands_where_expected(self):
        for st, dm, want in [(85, 70, gs.HOME), (85, 30, gs.PICK),
                             (50, 70, gs.LEARN), (50, 30, gs.OFF),
                             # 边界探针：跟着 STACK_OK 走，不写死数字
                             (gs.STACK_OK, gs.DOMAIN_OK, gs.HOME),
                             (gs.STACK_OK - 1, gs.DOMAIN_OK, gs.LEARN),
                             (gs.STACK_OK, gs.DOMAIN_OK - 1, gs.PICK)]:
            with self.subTest(stack=st, domain=dm):
                self.assertEqual(gs.quadrant(st, dm), want)


class LegacyFieldNamesStillParse(unittest.TestCase):
    """「技术栈」是改名前的旧字段。一次改名不该让上百份历史评估变成读不出来的。"""

    def test_old_name_reads(self):
        e = {"rank_breakdown": {"四维": "技术栈88×0.6+业务域65×0.4"}}
        self.assertEqual(gs.read_pair(e), (88, 65))

    def test_new_name_reads(self):
        self.assertEqual(gs.read_pair(E(88, 65)), (88, 65))

    def test_separate_fields_read(self):
        e = {"rank_breakdown": {"专业能力": 80, "业务领域": 40}}
        self.assertEqual(gs.read_pair(e), (80, 40))

    def test_unreadable_returns_none_not_a_guess(self):
        """读不出就是读不出。猜一个会把整格的结论带偏。"""
        for b in [{}, {"四维": "随便写的"}, {"四维": "专业能力高，业务域低"}]:
            with self.subTest(b=b):
                self.assertIsNone(gs.read_pair({"rank_breakdown": b}))


class OneParserForTheTwoScores(unittest.TestCase):
    """回读那两个分**只许有一份实现**，而且它要读得出显示层剥得掉的一切。

    2026-08-21 扫「跨文件重复的中文字面量」时逮到：同一条正则在
    `export_web_data`、`gap_split`、`applied_jds` 各写了一份，
    **宽容度还各不相同**。当时 687 条实测三者结果一致 —— 那是运气：
    存量恰好都写成紧凑形式。哪天评估写成 `专业能力 88 × 0.6`，
    清单读得出、面板读不出，同一个岗在两处显示不同的分。
    """

    def test_only_one_implementation_left(self):
        import export_web_data as ex
        import applied_jds
        for mod in (ex, applied_jds):
            src = Path(mod.__file__).read_text(encoding="utf-8")
            self.assertIn("read_pair", src,
                          f"{Path(mod.__file__).name} 没走正本")

    def test_whatever_the_display_can_strip_the_parser_can_read(self):
        """**剥得掉的就必须读得出。** 两条正则宽容度不一致时，会出现
        「算式从屏幕上剥掉了、两个分却读不出」的岗 —— 它会安静地掉出
        所有按分统计的口径（主场、四格、中位数），而页面看着一切正常。
        """
        import export_web_data as ex
        for text in ("专业能力 88 × 0.6 + 行业经验 65 × 0.4",
                     "技术栈88×0.6+业务域65×0.4",
                     "专业能力88x0.6+业务领域65x0.4",
                     "专业能力 70 * 0.6 + 业务域 60 * 0.4"):
            with self.subTest(text=text):
                strippable = bool(ex._FORMULA.search(text))
                readable = gs.read_pair({"rank_breakdown": {"四维": text}})
                self.assertEqual(
                    strippable, bool(readable),
                    f"剥得掉={strippable} 读得出={bool(readable)} —— 两边宽容度对不上")


class VerdictSteersAwayFromTheWrongAnswer(unittest.TestCase):
    """结论那句话是这个工具存在的理由——分错了就等于没有。"""

    def _box(self, **counts):
        seen = {}
        i = 0
        for kind, n in counts.items():
            st, dm = {"home": (85, 70), "pick": (85, 30),
                      "learn": (50, 70), "off": (50, 30)}[kind]
            for _ in range(n):
                i += 1
                seen[f"u{i}"] = E(st, dm)
        return gs.split(seen)

    def test_pick_heavy_warns_against_a_study_plan(self):
        v = gs.verdict(self._box(pick=20, learn=6, home=5, off=10))
        self.assertIn("先别急着开学习清单", v)
        # 原来验的是文件名 `search-queries` —— 而用户不知道该拿那个文件怎么办。
        # 2026-08-23 改成命令（`AGENTS.md`「面板每处引导都要写出命令」）。
        self.assertIn("/job-setup --section search", v, "没给出该敲哪条命令")

    def test_learn_heavy_proceeds(self):
        v = gs.verdict(self._box(learn=15, pick=3, home=4, off=5))
        self.assertIn("照常出学习计划", v)

    def test_mostly_off_track_suggests_rescoping(self):
        """整批都不相干时，学习计划会照着一堆不相干的岗开出来。"""
        v = gs.verdict(self._box(off=65, pick=20, learn=6, home=5))
        self.assertIn("收窄", v)

    def test_empty_corpus_says_so(self):
        self.assertIn("没有可回读", gs.verdict(gs.split({})))

    def test_unscored_entries_are_ignored(self):
        """**「已打分」由 `read_pair` 判，不由 status 判。**

        这条原来钉的是「`status: new` 的要被忽略」，而那句 status 过滤
        在偷偷多干两件事（见 `split` 的 docstring）。真正要保的是这一句：
        读不出两笔分数的岗不进四格 —— 而那正是 `read_pair` 的职责。
        """
        for st in ("new", "ranked", "expired"):
            with self.subTest(status=st):
                seen = {"a": {"status": st, "title": "示例"}}
                self.assertEqual(sum(len(v) for v in gs.split(seen).values()), 0,
                                 "没有分数的岗被算进四格了")

    def test_what_he_marked_not_interested_is_left_out(self):
        """学习计划不该照着他明确拒绝的岗开 —— 这是那句 status 过滤
        唯一真正想做的事（实测活动用户 80 个）。"""
        seen = {"a": {**E(85, 30), "status": "skipped"}}
        self.assertEqual(sum(len(v) for v in gs.split(seen).values()), 0,
                         "他点了不投的岗还在给他开学习计划")

    def test_a_closed_job_still_counts(self):
        """**岗位关了不等于那份技能需求消失。** 上个月招 Dify 的岗今天下线了，
        市场依然在要 Dify。原来那句 status 过滤把这一类一起排掉了
        （实测 14 个）—— 为一个「还能不能投」的状态丢掉市场信号。"""
        seen = {"a": {**E(85, 30), "status": "expired"}}
        self.assertEqual(sum(len(v) for v in gs.split(seen).values()), 1,
                         "已下线的岗被排出了学习语料")


class WorkflowWiresIt(unittest.TestCase):
    """写了工具不接线等于没写——本仓库反复出现的那一类。"""

    def test_upskill_has_the_gate_and_calls_the_tool(self):
        t = (ROOT / "workflows" / "job-upskill.md").read_text(encoding="utf-8")
        self.assertIn("Step 4.5", t, "/job-upskill 仍然无条件产出学习计划")
        self.assertIn("gap_split.py", t, "没接上分格工具，还得手数")

    def test_the_gate_is_a_prompt_not_a_block(self):
        """用户说「还是要学习计划」就该照出——这是提示，不是拦截。"""
        t = (ROOT / "workflows" / "job-upskill.md").read_text(encoding="utf-8")
        seg = t[t.index("## Step 4.5"):t.index("## Step 5：")]
        self.assertIn("提示，不是拦截", seg)

    def test_applied_mode_can_narrow_the_corpus(self):
        """`/job-upskill --applied` 下这一步**不能用错语料**。

        2026-08-21 通读时抓到：`--applied` 换掉了报表其余部分的语料，
        而 Step 4.5 的四格分布照旧拿**全部评过分的岗**算 ——
        同一份报表里两个语料，而且没有任何地方提醒。

        差别是实打实的（2026-08-21 拿真实数据实测）：全量 593 份里「两样都差」
        占 372（宽泛抓取的噪音把信号淹了）；只算投过的 78 份，
        「两样都差」掉到 7，「选岗问题」升到 49 —— **他自己已经把不对路的筛掉了。**
        """
        src = (ROOT / "tools" / "gap_split.py").read_text(encoding="utf-8")
        self.assertIn("collect_applied_keys", src,
                      "另写了一套「哪些算投过的」——这个仓库为多把钥匙付过五次学费")
        t = (ROOT / "workflows" / "job-upskill.md").read_text(encoding="utf-8")
        seg = t[t.index("## Step 4.5"):t.index("## Step 5：")]
        self.assertIn("--applied", seg, "工作流里没说这一步也要跟着换语料")

    def test_applied_really_narrows_it(self):
        """**真跑一次**，别只 grep 有没有那个 flag。

        grep 只能证明字符串在，证明不了它真的过滤了 —— 而「过滤没生效」
        恰恰是最难看出来的一种：四格照样打印，数字看着也合理。
        """
        import archive
        import gap_split

        user = "四格判据"
        tmp = Path(tempfile.mkdtemp())
        (tmp / "users" / user / "job_scraper").mkdir(parents=True)
        # 两个岗，只有一个投过。投过的那个落「选岗问题」，没投的落「可以靠学」。
        seen = {"seen": {
            "https://x.example/1": {**E(85, 30), "url": "https://x.example/1",
                                    "title": "投过的", "company": "甲公司"},
            "https://x.example/2": {**E(50, 70), "url": "https://x.example/2",
                                    "title": "没投的", "company": "乙公司"}}}
        (tmp / "users" / user / "job_scraper" / "seen_jobs.json").write_text(
            json.dumps(seen, ensure_ascii=False), encoding="utf-8")
        (tmp / "users" / user / "job_search_tracker.csv").write_text(
            "date,company,sector,role,role_type,channel,status,contact_person,"
            "fit_rating,notes,cv_file,cover_letter_file,source\n"
            "2026-08-01,甲公司,,投过的,,,applied,,,,,,https://x.example/1\n",
            encoding="utf-8")

        saved, saved_arc = gap_split.ROOT, archive.ROOT
        gap_split.ROOT = archive.ROOT = tmp
        try:
            import contextlib
            import io as _io
            buf = _io.StringIO()
            with contextlib.redirect_stdout(buf):
                gap_split.main(["--applied", "--user", user])
            out = buf.getvalue()
            self.assertIn("1 份", out, f"没有只剩投过的那 1 个：{out}")
            self.assertIn("只算投过的", out, "没告诉用户这次换了语料")

            buf2 = _io.StringIO()
            with contextlib.redirect_stdout(buf2):
                gap_split.main(["--user", user])
            self.assertIn("2 份", buf2.getvalue(), "不加 --applied 该是全部 2 个")
        finally:
            gap_split.ROOT, archive.ROOT = saved, saved_arc
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
