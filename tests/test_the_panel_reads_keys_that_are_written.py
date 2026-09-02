# -*- coding: utf-8 -*-
"""面板上的「经验」一栏是空的 —— 2456 个岗，一个都没有。

抓取器存的字段叫 `workYears`（`job-scrape.md` 的 schema 里就叫这个，
89% 的岗有值），而导出那一行读的是 `e.get("experience")` —— **这个键
从来不存在**，`or ""` 把它兜成空串，一路静默到屏幕上。

## 这是第二次

同一个字典里，紧挨着下面三行就写着上一次的验尸报告：

> `viaHeadhunter` —— **别在这里读字段名**，上一版就是在这儿写
> `e.get("via_headhunter")`，而抓取器存的是 `isHeadhunter`，
> 1358 个猎头岗全被印成了「企业 HR 直招」。

**警告写完了，紧挨着它上面两行的同类错还活着。** 挨着写一条注释挡不住第三个 ——
所以这份守卫盯的不是 `experience` 这一个键，是**这一类**。

## 为什么这一栏值钱

工作年限是硬门。`04-job-evaluation.md`：

> **工作年限** | 明确要求的年限下限高于候选人实际年限 | 差 1 年以内标记为 FLAG 而非 FAIL

而活动用户的资料里写着这道门要**在两个数之间选**：

> 总工作年限 13 年 11 个月，但 AI 产品方向约 3 年 4 个月（2023/03 起）。
> 要求「产品经理 N 年」按总年限算，要求「AI 产品 N 年」按 3 年多算。

实测 2026-08-23：2638 个岗里 2361 个（89%）平台给了年限；按 AI 产品那个读数，
**1161 个岗的下限高于它**。要选哪个数、够不够，全看岗位原话 ——
而那句原话在屏幕上一直是空白。

## 判据：读的键，得有东西真的写它

白名单式的例外挡不住下一个（谁加个键就顺手加一行例外）。这里改成扫写入方：
schema 里声明的，加上 `tools/*.py` 里真有 `e["键"] = ` 赋值的。
`experience` 和 `via_headhunter` 两个都查无写入方 —— 这条规则**当年就能拦下**。
"""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
from _srcscan import strip_comments  # noqa: E402

EWD = ROOT / "tools" / "export_web_data.py"
SCRAPE = ROOT / "workflows" / "job-scrape.md"
RANK = ROOT / "workflows" / "job-rank.md"


def job_dict() -> str:
    """`main()` 里构造那个岗位字典的字面量，按花括号配对切。

    不按行号切（一改就漂），也不按函数切 —— 整个 `main()` 里还有渠道状态那段
    用的也是 `e`，连它一起扫会把 `blocked` / `silent_fail` 这些误报进来。
    """
    src = strip_comments(EWD.read_text(encoding="utf-8"))
    i = src.index('"salaryMonthsUnknown"')
    depth, j = 0, i
    while j > 0:
        j -= 1
        if src[j] == "}":
            depth += 1
        elif src[j] == "{":
            if depth == 0:
                break
            depth -= 1
    depth, k = 0, j
    while k < len(src):
        if src[k] == "{":
            depth += 1
        elif src[k] == "}":
            depth -= 1
            if depth == 0:
                break
        k += 1
    return src[j:k + 1]


def keys_read() -> set:
    return set(re.findall(r'\be\.get\("([A-Za-z_][A-Za-z0-9_]*)"', job_dict()))


def keys_written() -> set:
    """谁会往一条职位记录上写字段。

    三个来源：抓取 schema、`/job-rank` 写回的字段、`tools/*.py` 里的直接赋值。
    **`export_web_data.py` 自己不算** —— 读的人不能给自己作保，否则
    它往 `job[...]` 里写什么就等于给自己开了什么。
    """
    out = set()
    t = SCRAPE.read_text(encoding="utf-8")
    m = re.search(r'```json\s*\n\{\s*\n\s*"seen"\s*:(.*?)```', t, re.S)
    assert m, "job-scrape.md 里找不到 seen_jobs 的 schema 代码块"
    out |= set(re.findall(r'"([A-Za-z_][A-Za-z0-9_]*)"\s*:', m.group(1)))
    for block in re.findall(r"```json(.*?)```", RANK.read_text(encoding="utf-8"),
                            re.S):
        out |= set(re.findall(r'"([A-Za-z_][A-Za-z0-9_]*)"\s*:', block))
    for p in sorted((ROOT / "tools").glob("*.py")):
        if p.name == EWD.name:
            continue
        # 下标里不一定是个光秃秃的字面量，形如
        # `e["skip_date" if cond else "expired_date"] = …` 的也要认出两个名字。
        # 所以先框出「`[…] =` 的那个下标」，再从里面把带引号的名字都掏出来。
        #
        # ⚠️ 这段注释原来举的是 `_cli.fold_user_state` 里的一行，而**那个函数
        # 一个生产调用方都没有**（2026-08-25 已删）。也就是说 `expired_date`
        # 一直是靠一行从没跑过的代码充当「有人写」—— 删掉它，这条守卫当场变红，
        # 露出真正的缺口：`job-rank.md` 让执行者把岗位置为 `expired`，
        # 却从没说要记日期。**一份没人跑的实现能让守卫说谎。**
        for sub in re.findall(r"\[([^\[\]\n]+)\]\s*=(?!=)",
                              p.read_text(encoding="utf-8")):
            out |= set(re.findall(r"""["']([A-Za-z_][A-Za-z0-9_]*)["']""", sub))
    return out


class EveryKeyReadIsAKeyWritten(unittest.TestCase):
    """这一条是本文件的正题。上面那两个函数只为它服务。"""

    def test_no_key_is_read_that_nothing_writes(self):
        read, written = keys_read(), keys_written()
        orphans = sorted(read - written)
        self.assertEqual(orphans, [],
                         f"导出方读了没人写的键：{orphans} —— "
                         f"`or \"\"` 会把它兜成空串，静默印到屏幕上")

    def test_the_scan_actually_finds_the_keys(self):
        """扫空了会让上一条永远绿。切错位置、正则写错都是这么静默失效的。"""
        read = keys_read()
        self.assertGreaterEqual(len(read), 8, f"只扫到 {len(read)} 个键，切错了")
        for k in ("workYears", "salary", "location", "portal"):
            with self.subTest(k=k):
                self.assertIn(k, read)

    def test_the_writer_side_is_not_a_catch_all(self):
        """写入方扫太宽，上面那条就成了摆设 —— 它得挡得住这两个真实的错键。"""
        written = keys_written()
        for k in ("experience", "via_headhunter"):
            with self.subTest(k=k):
                self.assertNotIn(k, written,
                                 f"`{k}` 被算成了「有人写」，规则失效")

    def test_the_exporter_cannot_vouch_for_itself(self):
        """读的人不能给自己作保。它往 `job[...]` 里写的每个键都会变成白名单，
        而那些键正是要被检查的东西 —— 规则会退化成恒真。"""
        out = keys_written()
        # 这几个只有 `export_web_data.py` 自己往 `job[...]` 里写。
        # 它要是被算进写入方，读什么都算「有人写」。
        for k in ("gates", "gatesNotJudged", "dimensions"):
            with self.subTest(k=k):
                self.assertNotIn(k, out, f"`{k}` 来自导出方自己，不该算写入方")


class BothWaysOutRecordWhen(unittest.TestCase):
    """出局有两条路——「不投」和「已下线」——**两条都得记日期**。

    实测 2026-08-25：`job-rank.md` 对 `skipped` 写了 `skip_date`，对 `expired`
    只说「把 `status` 置为 `expired`」。执行者照做，然后自己发明了
    `expired_date` 写进去（库里 19 条有、1 条没有），而 `export_web_data` 与
    `archive` 都在读它。**没人声明、下游在读，靠的是执行者每次都想到同一个名字。**

    上面那条孤儿键守卫此前没报，是因为一个从没跑过的函数（`_cli.fold_user_state`，
    零生产调用方）里正好有一行写它 —— 删掉它，这条当场变红。
    """

    RANK = (ROOT / "workflows" / "job-rank.md").read_text(encoding="utf-8")

    def _out_block(self, marker: str) -> str:
        i = self.RANK.index(marker)
        return self.RANK[i:i + 400]

    def test_the_skipped_path_records_a_date(self):
        self.assertIn('"skip_date": "YYYY-MM-DD"',
                      self._out_block('"status": "skipped"'))

    def test_the_expired_path_records_a_date(self):
        """这一条是这次补的。**两条路不对称，下游就得靠猜。**"""
        self.assertIn('"expired_date": "YYYY-MM-DD"',
                      self._out_block('"status": "expired"'))

    def test_the_date_is_not_optional(self):
        """写成「可以顺手记一下」等于没写 —— 执行者会跳过它。"""
        self.assertIn("**日期不是可选的**", self._out_block('"status": "expired"'))

    def test_it_says_what_breaks_without_it(self):
        """理由要写出来：没有日期时归档会把这个岗算老，提前埋掉。

        **这条 2026-08-26 改过。** 原来它钉的是「退到 `first_seen`」——
        而 `_age_days` 取的是所有日期里**最晚**的一个，退到的通常是 `rank_date`
        （评分那天），不是抓到那天。守卫钉着一句和代码对不上的话，就是把它固定住。
        同一句错话在 `audit_pipeline` 的自检文案里也有一份，同日一并改的。
        """
        seg = self._out_block('"status": "expired"')
        self.assertIn("最晚", seg, "没说清它退到哪 —— 「退到 first_seen」是错的")
        self.assertIn("提前埋掉", seg)

    def test_that_fallback_really_is_the_behaviour(self):
        """上一条引的是 `archive._age_days` 的实际写法 —— 它变了这句话就成谎话。"""
        src = (ROOT / "tools" / "archive.py").read_text(encoding="utf-8")
        i = src.index("def _age_days(")
        # 取整个函数，不是前 N 个字符 —— 中文 docstring 一占位，
        # 固定窗口（原来是 500）就够不着 `return` 那一行。
        end = src.find("\ndef ", i + 10)
        seg = src[i:end if end > 0 else len(src)]
        self.assertIn('entry.get("expired_date")', seg)
        self.assertIn('entry.get("first_seen")', seg)
        self.assertIn("max(known)", seg,
                      "取的不是最晚那个了 —— 文档里「退到最晚的一个」就成了谎话")
        self.assertLess(seg.index('entry.get("expired_date")'),
                        seg.index('entry.get("first_seen")'),
                        "出局日期要排在 first_seen 前面，否则「取最晚」也救不回来")

    def test_the_archive_bias_it_leans_on_is_still_written_down(self):
        src = (ROOT / "tools" / "archive.py").read_text(encoding="utf-8")
        self.assertIn("宁可少归一轮，不可早埋", src)

    def test_the_key_is_now_declared_not_invented(self):
        """收口：`expired_date` 进了写入方名单，不再是执行者临时发明的键。"""
        self.assertIn("expired_date", keys_written())


class TheYearsRequirementReachesTheScreen(unittest.TestCase):
    """类级规则之外，这一个键本身也钉一下 —— 它是硬门，值得单独有名字。"""

    def test_it_reads_the_field_the_scraper_stores(self):
        self.assertIn('"experience": e.get("workYears")', job_dict())

    def test_the_schema_really_calls_it_workyears(self):
        self.assertIn("workYears", keys_written())

    def test_the_gate_still_depends_on_it(self):
        """这一栏值钱是因为它是硬门。哪天不是了，这几条要重写。"""
        ev = (ROOT / "workflows" / "reference"
              / "04-job-evaluation.md").read_text(encoding="utf-8")
        self.assertIn("| **工作年限** |", ev)
        self.assertIn("明确要求的年限下限高于候选人实际年限", ev)

    def test_the_receipt_is_written_down(self):
        """没有理由的一行赋值，下一版会照着别处的写法「统一」回去。"""
        # 理由是跨行注释，拉平时每行都还带着 `#` —— 先把注释标记去掉再比，
        # 否则「下面那条警告说的**#**就是这一行」永远对不上。
        seg = " ".join(EWD.read_text(encoding="utf-8")
                       .replace("#", " ").replace("*", "").split())
        i = seg.index('"experience": e.get("workYears")')
        why = seg[max(0, i - 700):i]
        self.assertIn("下面那条警告说的 就是这一行", why,
                      "没写清它就是上次那条警告的漏网者")
        self.assertRegex(why, r"2456 个全是空的")


class BothConsumersStillRenderIt(unittest.TestCase):
    """字段能生产出来，还得有人显示。两个消费方各写各的，别只顾一个。"""

    JR = ROOT / "web" / "src" / "components" / "JobReadout.tsx"
    SL = ROOT / "web" / "src" / "components" / "Shortlist.tsx"

    def test_the_readout_shows_it(self):
        """**要它真的门控着那一行，不能只验字符串出现过。**
        `job.experience &&` 换成 `false &&` 之后，三元里那两处 `job.experience`
        还在文件里，光 `assertIn` 照样绿 —— 变异实测就是这么漏的。"""
        src = self.JR.read_text(encoding="utf-8")
        i = src.index('className="readout-facts"')
        facts = src[i:src.index(".join(", i)]
        self.assertIn("job.experience &&", facts,
                      "年限没有进详情那一行的事实列表")

    def test_the_shortlist_shows_it(self):
        self.assertIn("job.experience", self.SL.read_text(encoding="utf-8"))

    def test_the_readout_does_not_say_it_twice(self):
        """平台原话里有 213 个是「经验不限」，加前缀就成了「经验 经验不限」。"""
        src = self.JR.read_text(encoding="utf-8")
        i = src.index("job.experience")
        seg = " ".join(src[i:i + 260].split())
        self.assertIn('job.experience.startsWith("经验")', seg,
                      "「经验不限」那 200 多个岗会被印成「经验 经验不限」")

    def test_the_shortlist_needs_no_prefix(self):
        """短名单那边是裸值（`· 上海 · 5-10年`），所以只有详情那处要判。
        它哪天也加了前缀，上面那条就得跟着搬过去。"""
        src = self.SL.read_text(encoding="utf-8")
        i = src.index("job.experience")
        self.assertNotIn("经验 ", src[max(0, i - 120):i + 120])

    def test_the_type_declares_it(self):
        self.assertRegex((ROOT / "web" / "src" / "types.ts")
                         .read_text(encoding="utf-8"), r"experience: string")


if __name__ == "__main__":
    unittest.main()
