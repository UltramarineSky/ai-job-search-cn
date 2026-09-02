# -*- coding: utf-8 -*-
"""`--jobage` 把没有日期的卡片一起丢掉了，而且**一声不吭**。

猎聘接口的 `pubTime` 参数是哑的（传「一天内」照样返回两年前的职位），所以 CLI
在客户端按更新时间过滤。那一行是：

    return cards.filter((c) => c.date !== null && c.date >= cutoffISO)

**`c.date !== null` 这一半从来没人提过。** 而 `refreshTime` 不是每张卡都有：
实测活动用户 2026-08-23，职位库里 2232 个猎聘岗**只有 259 个带日期（12%）**。

丢掉没日期的本身是保守的选择（无从验证新鲜度），错的是**不报数**。
CLI 的 `meta` 里连解析失败都报（`skipped`，注释还写着「非 0 就是信号」），
唯独 `--jobage` 丢了多少没有出口。

## 两种被丢掉的，指向相反的动作

| | 意思 | 该做什么 |
|---|---|---|
| `droppedTooOld` | 有日期、早于截止日 | 过滤器在干活。这个词确实挖到底了 |
| `droppedNoDate` | **压根没日期** | 丢掉的可能全是新岗 —— 这一轮别传 `--jobage` |

只报一个总数会把这两件事混成一件。

## 不报的代价在下游

`query_yield` 按实测产出剪掉「挖空的词」。一个词的结果**全因缺日期被丢光**，
它会被当成挖空剪掉 —— 而那是误判，那个词可能正好命中一批没标日期的新岗。

这是这个仓库反复立的同一条规矩：**不许沉默的截断，数给出来、停不停由人定**
（`greeting_problems` 的「还有 N 条同类的」、`query_yield` 的「数给你，
停不停你定」、审计的「没查的」那一节都是它）。
"""
import json
import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / ".agents" / "skills" / "liepin-search" / "cli"
SEARCH = (CLI / "src" / "commands" / "search.ts").read_text(encoding="utf-8")
SKILL = (ROOT / ".agents" / "skills" / "liepin-search"
         / "SKILL.md").read_text(encoding="utf-8")
SCRAPE = (ROOT / "workflows" / "job-scrape.md").read_text(encoding="utf-8")


def _why() -> str:
    """`filterByAge` 上面那段 JSDoc，**先剥掉行首的 `*` 再拉平**。

    不剥的话，跨行的句子中间会夹进一个 `*`
    （`…2232 个猎聘岗只有 * 259 个带日期…`）—— 实测就是这么落空的。
    """
    i = SEARCH.index("/**\n * 按发布时间过滤。")
    raw = SEARCH[i:SEARCH.index("export function filterByAge(", i)]
    return " ".join(re.sub(r"^\s*\*+", "", raw, flags=re.M).split())


class TheFilterCountsWhatItDrops(unittest.TestCase):
    def test_it_returns_the_two_counts(self):
        self.assertIn("export interface AgeFilterResult", SEARCH)
        for f in ("tooOld: number", "noDate: number"):
            with self.subTest(f=f):
                self.assertIn(f, SEARCH)

    def test_it_no_longer_returns_a_bare_array(self):
        i = SEARCH.index("export function filterByAge(")
        sig = SEARCH[i:SEARCH.index("{", SEARCH.index("): ", i))]
        self.assertIn("AgeFilterResult", sig,
                      "还是直接返回数组 —— 丢了多少没有出口")

    def test_the_two_are_counted_separately(self):
        i = SEARCH.index("export function filterByAge(")
        body = SEARCH[i:SEARCH.index("\n}", i)]
        self.assertIn("noDate++", body)
        self.assertIn("tooOld++", body)

    def test_no_filtering_when_the_flag_is_off(self):
        """不传 `--jobage` 时一个都不该丢，两个计数也该是 0。"""
        i = SEARCH.index("export function filterByAge(")
        body = SEARCH[i:SEARCH.index("\n}", i)]
        self.assertIn("return { cards, tooOld: 0, noDate: 0 }", body)

    def test_the_reason_is_recorded_with_numbers(self):
        seg = _why()
        self.assertRegex(seg, r"2232 个猎聘岗只有\s*259 个带日期（12%）")
        self.assertRegex(seg, r"两种被丢掉的要分开数")

    def test_the_reason_names_the_downstream_cost(self):
        seg = _why()
        self.assertIn("query_yield", seg)
        self.assertRegex(seg, r"当成挖空剪掉，而那是误判")


class TheCountsReachTheCaller(unittest.TestCase):
    def test_meta_carries_both(self):
        i = SEARCH.index("meta: {")
        seg = SEARCH[i:SEARCH.index("results: cards", i)]
        self.assertIn("droppedTooOld: aged.tooOld", seg)
        self.assertIn("droppedNoDate: aged.noDate", seg)

    def test_the_existing_meta_fields_survive(self):
        i = SEARCH.index("meta: {")
        seg = SEARCH[i:SEARCH.index("results: cards", i)]
        for f in ("count: cards.length", "totalPage", "hasNext",
                  "skipped: parsed.skipped"):
            with self.subTest(f=f):
                self.assertIn(f, seg)

    def test_the_limit_still_applies_after_the_age_filter(self):
        """顺序不能反 —— 先截断再按年龄过滤会让 `--limit` 名不副实。"""
        i = SEARCH.index("const aged = filterByAge(")
        seg = SEARCH[i:i + 300]
        self.assertLess(seg.index("let cards = aged.cards"),
                        seg.index("cards.slice(0, opts.limit)"))


class TheBehaviourIsRight(unittest.TestCase):
    """光看源码不够 —— 真跑一遍 TS 侧那份守卫。"""

    def test_the_bun_suite_covers_it(self):
        f = CLI / "tests" / "age-filter-reports-what-it-drops.test.ts"
        self.assertTrue(f.is_file(), "TS 侧没有对应的守卫")
        src = f.read_text(encoding="utf-8")
        for w in ("noDate", "tooOld", "全被丢光时仍然报得出为什么"):
            with self.subTest(w=w):
                self.assertIn(w, src)

    def test_the_old_timezone_test_was_updated(self):
        """返回类型变了，那份既有测试要跟着改 —— 否则它测的是旧契约。"""
        src = (CLI / "tests" / "timezone.test.ts").read_text(encoding="utf-8")
        self.assertIn("result.cards.length", src)
        self.assertNotIn("expect(result.length)", src)

    def test_it_actually_runs(self):
        """**这一条是真跑。** 上面几条只读源码，读不出「它跑不跑得对」。
        没有 bun 就跳过 —— 本仓库不把 bun 做成必需（见
        `test_docs_do_not_make_bun_mandatory`）。"""
        import shutil
        # **要用 `which` 解析出的完整路径。** Windows 上 bun 装成 `bun.CMD`，
        # 直接给 `"bun"` 时 `shutil.which` 找得到、`subprocess` 起不来
        # （WinError 2）—— 实测就是这么红的。
        exe = shutil.which("bun")
        if not exe:
            self.skipTest("没有 bun")
        r = subprocess.run(
            [exe, "test", "tests/age-filter-reports-what-it-drops.test.ts",
             "tests/timezone.test.ts"],
            shell=False if not exe.lower().endswith((".cmd", ".bat")) else True,
            cwd=CLI, capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=300)
        self.assertEqual(r.returncode, 0,
                         f"TS 守卫没过：\n{(r.stdout or '') + (r.stderr or '')}")
        self.assertRegex((r.stdout or "") + (r.stderr or ""), r"0 fail")


class TheDocsSayIt(unittest.TestCase):
    def test_the_skill_explains_both_counts(self):
        """**要各自的解释，不是名字出现过。** `droppedNoDate` 在这一段里
        出现两次（一次定义、一次给建议）—— 只验名字的话，把定义那半删掉
        照样绿（变异实测）。"""
        i = SKILL.index("**`--jobage` 是客户端过滤。**")
        seg = " ".join(SKILL[i:i + 900].split())
        self.assertRegex(seg, r"`droppedTooOld`（有日期、太旧")
        self.assertRegex(seg, r"`droppedNoDate`（没日期，被一起丢了")
        self.assertRegex(seg, r"没有更新时间的卡片也会被丢掉")

    def test_the_skill_says_what_to_do_about_it(self):
        i = SKILL.index("**`--jobage` 是客户端过滤。**")
        seg = " ".join(SKILL[i:i + 900].split())
        self.assertRegex(seg, r"这一轮考虑\*\*别传 `--jobage`\*\*")

    def test_the_scrape_step_tells_the_reader_to_look(self):
        i = SCRAPE.index("把范围收到**最近 14 天**")
        seg = " ".join(SCRAPE[i:i + 900].split())
        self.assertIn("droppedNoDate", seg)
        # **要那句「看第二个」。** 整段的要害就是「两个数里看哪一个」——
        # 没有它，读的人会以为随便看看就行（变异实测：删掉它照样绿）。
        self.assertRegex(seg, r"\*\*看第二个\*\*")
        self.assertRegex(seg, r"这个词这一轮别传 `--jobage` 再跑一次")

    #: **按锚点截，不按字符数截。** 这两条原来取「把范围收到 14 天」之后的
    #: 固定 900 字符 —— 2026-08-27 那一段中间插了一次「结论被推翻」的说明，
    #: 它俩要找的话就被挤出了窗口，两条一起变红，而文里其实一个字没少。
    #: 固定长度的窗口是个会被无关改动踩响的判据。
    def _step3(self) -> str:
        i = SCRAPE.index("把范围收到**最近 14 天**")
        return " ".join(SCRAPE[i:SCRAPE.index(chr(10) + "4.", i)].split())

    def test_the_scrape_step_names_the_downstream_misjudgement(self):
        self.assertRegex(self._step3(), r"会被当成挖空剪掉，而那是误判")

    def test_other_portals_without_the_counts_must_say_so(self):
        """别的渠道给不出这两个数时，不能当成 0 —— 那是另一种沉默。"""
        seg = self._step3()
        self.assertRegex(seg, r"如实说「这一轮丢了多少不知道」，不要当成 0")

    def test_the_pruning_rule_it_protects_still_exists(self):
        qy = (ROOT / "tools" / "query_yield.py").read_text(encoding="utf-8")
        self.assertRegex(" ".join(qy.split()), r"数给你，停不停你定")


if __name__ == "__main__":
    unittest.main()
