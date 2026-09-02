# -*- coding: utf-8 -*-
"""「可以考虑」那条检查，分母数错了、而且用存量把当下的问题稀释掉了。

两个毛病，一个比一个要紧：

**一、分母是「正文里出现过这四个字」，不是「结论是这一档」。**

原来写的是 `if "可以考虑" not in t: continue` —— 而评估正文里提一句
「上一轮给了 63『可以考虑』」「比另一个岗更可以考虑」都会命中。
实测活动用户 2026-08-23：命中 144 份，结论真是这一档的只有 130 份，
另外那些里有「值得投」6 份、「不建议」3 份 —— **那两档本来就不要求写
「投前必问」，进分母就是假阳性**。

而这条检查在缺失率 ≥50% 时**升级成 `error`**，`test_pipeline_audit_stays_clean`
又钉死零 error —— 分母口径直接决定整套测试红不红，不能靠一个子串。
判词解析走正本 `build_dashboard.parse_evaluation`（它自己的 docstring
记着为「只认一种写法」踩过三次坑）。

**二、那个「最近 N 份」的分母是错的（2026-08-23 更正）。**

这份文件第一版按**文件 mtime** 切了一刀，报出：

    全部 130 份   缺 61   46%
    最近 30 份    缺 22   73%   ← 「新出的更差」

**那句话是假的。**「投前必问」是 `_ASK_RULE_SINCE`（2026-08-22）才补进 04 输出
格式的，而「可以考虑」那一档最新的一份深评写于 **08-17** —— 130 份**全部产于
规则之前**。拿生效前的产出算一条规则的执行率，算出来的只能是存量，
而那句断语会让读的人去重写一条**还没被执行过**的规则。

所以分母按规则生效日切：生效后一份都没有就直说「这个数说的是存量，跑一批新的
才有得比」；有了 ≥10 份才谈执行率，且只用那一批当分母。原来那句「总数说规模」
仍然成立 —— 变的是第二个数该拿什么算。

**没有改升级门槛。** 46% 仍在 50% 以下，仍是 `warn`。按最近那批算的话
今天就是 error，而这条检查没有机械修法（改法是重写评估）——
本仓库的「要修」都配一个 `--apply`，而一个永远红的审计会被当噪音略过。
报出来让人看见，不劫持构建。
"""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(ROOT / "tests"))
from _live import user_or_skip  # noqa: E402
import audit_pipeline as A  # noqa: E402
from _srcscan import strip_comments  # noqa: E402
from _srcscan import code_of  # noqa: E402

_HEAD = "# 职位评估\n\n"


def _eval(verdict, ask=True, extra=""):
    ask_sec = "\n## 投前必问\n\n- 这个岗带多少人？\n" if ask else ""
    return f"{_HEAD}## 结论：{verdict}\n\n打分说明。{extra}\n{ask_sec}"


class TheTierIsReadFromTheConclusion(unittest.TestCase):
    def _run(self, files):
        import tempfile
        import unittest.mock as mock
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            apps = root / "users" / "u" / "documents" / "applications"
            for i, text in enumerate(files):
                d = apps / f"示例科技{i}_产品经理"
                d.mkdir(parents=True)
                (d / "evaluation.md").write_text(text, encoding="utf-8")
            with mock.patch.object(A, "ROOT", root), \
                 mock.patch.object(A._cli, "pick_user", lambda *a, **k: "u"):
                return A.check_maybe_tier_has_questions({}, {})

    def test_a_mention_in_prose_is_not_this_tier(self):
        """「值得投」的评估里提一句「上一轮给了 63『可以考虑』」—— 不该进分母。"""
        out = self._run([_eval("值得投", ask=False,
                               extra="上一轮给了 63「可以考虑」，这次上调。")])
        self.assertEqual(out, [], f"按子串把别的档位算进来了：{out}")

    def test_the_real_tier_without_the_section_is_caught(self):
        out = self._run([_eval("可以考虑", ask=False)])
        self.assertEqual(len(out), 1)
        self.assertIn("1/1", out[0][2])

    def test_the_real_tier_with_the_section_is_clean(self):
        self.assertEqual(self._run([_eval("可以考虑", ask=True)]), [])

    def test_other_tiers_are_never_required_to_have_it(self):
        for v in ("强匹配", "值得投", "不建议"):
            with self.subTest(verdict=v):
                self.assertEqual(self._run([_eval(v, ask=False)]), [])

    def test_it_uses_the_canonical_parser(self):
        """**只扫代码** —— docstring 里逐字引着旧写法 `"可以考虑" not in t`。

        判据 2026-08-30 从这条检查里搬进了 `ask_before_missing`（写盘时那道
        闸门 `--sections` 要用同一份），所以这里改成两段一起看：
        检查体不许再自己判档位，正本里必须是 `parse_evaluation`。
        **钉的是「判据只有一份且不按子串」，不是它住在哪个函数里。**
        """
        seg = code_of("tools/audit_pipeline.py",
                      "def check_maybe_tier_has_questions(")
        self.assertIn("ask_before_missing(t)", seg, "检查体又自己判了一遍")
        self.assertNotIn('"可以考虑" not in t', seg)
        judge = code_of("tools/audit_pipeline.py", "def ask_before_missing(")
        self.assertIn("parse_evaluation(text)", judge, "又按子串判档位了")
        self.assertNotIn('"可以考虑" not in ', judge)

    def test_the_gate_before_disk_uses_the_same_judge(self):
        """写盘那道闸门和全量审计问的必须是同一件事。

        「可以考虑」缺这一节，`--sections` 也要报 —— 这一档的定义就是
        「先问清楚再决定投不投」，而实测规则生效后的 10 份里仍缺 3 份，
        说明它靠散文提示提醒不住。
        """
        seg = code_of("tools/audit_pipeline.py", "def _sections_cli(")
        self.assertIn("ask_before_missing", seg,
                      "写盘那道闸门不查这一节")
        self.assertIn("投前必问", seg, "查了却没说缺的是哪一节")


class TheRecentRateIsReportedToo(unittest.TestCase):
    SRC = (ROOT / "tools" / "audit_pipeline.py").read_text(encoding="utf-8")

    def _seg(self):
        i = self.SRC.index("def check_maybe_tier_has_questions(")
        return self.SRC[i:self.SRC.index("\ndef ", i + 10)]

    def test_the_window_exists(self):
        self.assertTrue(hasattr(A, "RECENT_EVALS"))
        self.assertIn("RECENT_EVALS", self._seg())

    def test_it_sorts_by_the_evaluation_date_not_by_file_time(self):
        """原来这条要求的是 `st_mtime` —— **要求反了**。mtime 会被重新归档、
        批量改权限、同步工具推到今天，那时候「最近 N 份」就是随机 N 份，
        而报告仍会照它下断语（2026-08-23 实测：同一份数据，mtime 口径 13%、
        评估日期口径 90%）。日期取深评抬头自己写的那一行。

        「不按天切」那半仍然成立：抓取节奏时密时疏，按天窗口会在停跑几天之后
        拿到一个空样本，然后这半句静默消失。"""
        seg = self._seg()
        self.assertNotIn("st_mtime", seg, "又按文件时间排了")
        self.assertIn("_eval_date(t)", seg, "没按深评自己写的评估日期排")
        self.assertNotRegex(seg, r"timedelta\(days=", "改成按日期窗口了")

    def test_the_minimum_sample_is_written_down(self):
        """门槛要在代码里，不能只靠行为测试碰巧覆盖到。"""
        seg = self._seg()
        self.assertRegex(seg, r"len\(tail\) >= \d+", "没有最小样本量")

    def test_the_report_really_carries_it(self):
        """**行为断言。** 只查源码里有那几个片段的话，把整段包进
        `if False:` 照样绿 —— 变异实测漏过一次。

        造的这批不带评估日期，落在「全部产于规则之前」那一支：
        「投前必问」是 `_ASK_RULE_SINCE` 才进 04 输出格式的，拿生效前的产出
        算它的执行率会得出一句假话，所以那一支报的是存量口径，不是「最近 N 份」。
        分档口径见 `test_a_trend_needs_something_to_trend_over.py`。"""
        files = [_eval("可以考虑", ask=False) for _ in range(12)]
        files += [_eval("可以考虑", ask=True) for _ in range(3)]
        out = TheTierIsReadFromTheConclusion()._run(files)
        self.assertEqual(len(out), 1)
        self.assertIn("12/15", out[0][2])
        self.assertIn("全部产于规则之前", out[0][2], "存量那一支的口径没进消息")
        self.assertNotIn("新出的更差", out[0][2])

    def test_a_sample_under_ten_stays_quiet(self):
        """样本太小时一两份就能把比例带到 100% —— 那不是趋势，是噪音。"""
        files = [_eval("可以考虑", ask=False) for _ in range(3)]
        out = TheTierIsReadFromTheConclusion()._run(files)
        self.assertNotIn("最近", out[0][2], "样本才 3 份也报趋势")

    def test_the_message_carries_both_numbers(self):
        """总数说规模，第二个数说当下 —— 第二个数按规则生效日切出来。"""
        seg = self._seg()
        self.assertIn("{miss}/{n}", seg, "总数不见了")
        self.assertIn("_ASK_RULE_SINCE", seg, "第二个数不再按规则生效日切")

    def test_it_never_blames_a_rule_it_cannot_see(self):
        """**剥注释再查。** 「新出的更差」那句话现在仍留在注释里
        （讲的正是它为什么被删）—— 连注释一起扫，这条就是空转的，
        第一版实测就是这样绿的。"""
        code = strip_comments(self.SRC)
        i = code.index("def check_maybe_tier_has_questions(")
        seg = code[i:code.index("\ndef ", i + 10)]
        for phrase in ("不是存量遗留", "新出的更差"):
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, seg, "又把一句方向断语写死进消息了")

    def test_the_false_premise_is_corrected_in_place(self):
        """两个前提都被实测推翻过：先是「存量里缺很正常」，
        后是「按 mtime 算出来的 73%」。**改正要写在检查自己的 docstring 里** ——
        只写在测试里，下一个人读代码时看不到，会照着旧前提再放宽一次。"""
        seg = self._seg()
        self.assertIn("规则之后一份都还没产出", seg, "没记下那次更正")
        self.assertRegex(seg, r"73%", "没把那个被推翻的数留下")


class TheThresholdWasNotTouched(unittest.TestCase):
    def test_it_never_becomes_a_permanent_error(self):
        """**这条钉的是意图，不是当时那行代码。**

        原来断言的是 `"warn" if rate < 0.5 else "error"` 还在，理由写在
        docstring 里：「那样今天就是 error，而这条检查没有机械修法……
        一个永远红的审计会被当噪音略过。」

        **2026-08-24 它自己走到了那一步。** 那一轮让这条检查把「整节只写一条
        『无』」也算缺（此前只看标题在不在），缺失率 61/130 → 100/130（77%），
        当场越过 50% 升成 error —— 和这条 docstring 要防的是同一个结局，
        只是走的不是「换分母」那条路。

        而同一份文件里 `check_greeting_keeps_the_five_rules` 的
        「为什么判留意而不是要修」**逐字点了这条的名**，说它属于「留意」那一级。
        两处一直对立，只是 46% 卡在门槛下面没人撞见。

        所以升级整个撤了，这里跟着改成钉意图：**这条检查不许返回 error**。
        比原来那行字面更宽，也更结实 —— 换一种写法再升级也拦得住。
        """
        import _cli
        import audit_pipeline as ap
        seen, details = ap.load(user_or_skip())
        bad = [(t, m[:50]) for lvl, t, m
               in ap.check_maybe_tier_has_questions(seen, details) if lvl != "warn"]
        self.assertEqual(bad, [], f"这条检查升级了：{bad}")

    def test_the_rate_is_still_the_full_corpus_one(self):
        """报出来的那个百分比要是全量口径 —— 拿最近那批算会把存量说成趋势。"""
        seg = (ROOT / "tools" / "audit_pipeline.py").read_text(encoding="utf-8")
        i = seg.index("def check_maybe_tier_has_questions(")
        body = seg[i:seg.index(chr(10) + "def ", i + 10)]
        self.assertRegex(body, r"rate = miss / n", "rate 不再是全量口径")
        self.assertIn("{rate:.0%}", body, "算了却没报出来 —— 那它就是死变量")


if __name__ == "__main__":
    unittest.main()
