# -*- coding: utf-8 -*-
"""同一份文档里，同一批开场白既是 234 份又是 236 份。

`06-outreach-templates.md` 第 24 行写「234 份开场白里 71 份…」，
第 152 行写「那 236 份开场白」—— 同一天、同一个语料、同一个文件，两个数。

顺着扫下去，那个 234 被抄进了 **7 处**（`_cli` ×2、`audit_pipeline`、
`export_web_data`、这份模板 ×3、两个测试），而 2026-08-23 现算的真值是：

    开场白       236 份      （文档写 234）
    踩线         37 份 16%   （文档写 24 份 10%）
    共           49 处       （文档写 28 处）
    超 200 字     0 份        （文档写 1 份 0.4%）

三个数全飘了。**这不是抄错，是抄了**：一个会随语料变的数被写死在七个地方，
每生成一批新材料就全部作废一次，而没有任何东西会红。

## 这条守卫怎么防

**现算，不钉死。** 拿真语料跑一遍 `_cli.greeting_hits`，把算出来的数
和文档里写的那几个比。语料不在（别人的 clone、CI）→ `skipTest`，
不拿构造数据假装验过。

顺带把 `test_the_five_rules_are_actually_checked` 里钉死「0.4%」「10%」的
两条断言松成「有一个对照组的数 / 有一个踩线率」—— 钉死具体数只会让下一个人
去改断言，不是去改文档。
"""
import collections
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import _cli  # noqa: E402
import audit_pipeline as AP  # noqa: E402

TPL = (ROOT / "workflows" / "reference"
       / "06-outreach-templates.md").read_text(encoding="utf-8")

#: 所有抄了这个数的地方。少一处，这条就漏一处。
CITERS = ("tools/_cli.py", "tools/audit_pipeline.py", "tools/export_web_data.py",
          "workflows/reference/06-outreach-templates.md",
          "tests/test_the_five_rules_are_actually_checked.py",
          "tests/test_the_send_hint_knows_the_channel.py")


#: **只认分母位的那个数。** 「97 份开场白都这么开头」「65 份是同一个句式」
#: 是**子集**，不是总数 —— 第一版把它们也扫了进来，当场报「97 != 236」。
#: 分母后面跟的是「里 / 按 / ，」（「N 份开场白里 M 份…」「N 份开场白按 … 分布」），
#: 子集后面跟的是动词（「都这么开头」「是同一个句式」）。
_DENOM = re.compile(r"(\d{2,5})\s*份(?:已出的)?开场白(?=[里按，,])")


def _live():
    """现算：(总份数, 踩线份数, 踩线处数, 超字数份数)。没有语料返回 None。"""
    p = ROOT / ".active_user"
    if not p.is_file():
        return None
    apps = (ROOT / "users" / p.read_text(encoding="utf-8").strip()
            / "documents" / "applications")
    if not apps.is_dir():
        return None
    gs = []
    for f in sorted(apps.glob("*/outreach.md")):
        g = AP._greeting_of(f.read_text(encoding="utf-8", errors="replace"))
        if g:
            gs.append(g)
    if len(gs) < 30:
        return None
    files = spots = 0
    for g in gs:
        h = _cli.greeting_hits(g)
        if h:
            files += 1
        spots += len(h)
    over = sum(1 for g in gs
               if len(re.sub(r"\s", "", g)) > _cli.GREETING_MAX)
    return len(gs), files, spots, over


class EveryCitationAgreesWithTheCorpus(unittest.TestCase):
    def setUp(self):
        self.live = _live()
        if self.live is None:
            self.skipTest("这台机器上没有足够的开场白语料 —— 不拿构造数据假装验过")

    def test_the_total_is_right_everywhere(self):
        total = self.live[0]
        for rel in CITERS:
            text = (ROOT / rel).read_text(encoding="utf-8")
            for m in _DENOM.finditer(text):
                with self.subTest(where=rel, cited=m.group(1)):
                    self.assertEqual(int(m.group(1)), total,
                                     f"{rel} 写的是 {m.group(1)} 份，真值 {total}")

    def test_no_two_citations_disagree(self):
        """**这才是当初露出来的那一头。** 同一个文件里 234 和 236 并存。"""
        seen = collections.defaultdict(set)
        for rel in CITERS:
            for m in _DENOM.finditer((ROOT / rel).read_text(encoding="utf-8")):
                seen[m.group(1)].add(rel)
        self.assertEqual(len(seen), 1,
                         f"同一批开场白被写成了几个数：{dict(seen)}")

    def test_the_offence_count_is_right_wherever_it_is_cited(self):
        """**分母被守住了，分子没有。** 2026-08-23 把 `greeting_problems`
        的分母从 234 更正到 236 时，同一句的「24 份至少犯一条」忘了改
        （现算 37）—— 分母对得上，读的人不会再去查后半句。
        变异实测：把它退回 24，整套测试全绿。"""
        _total, files, _spots, _over = self.live
        pat = re.compile(r"份开场白里 \*\*(\d+) 份至少犯一条\*\*")
        found = 0
        for rel in CITERS:
            for m in pat.finditer((ROOT / rel).read_text(encoding="utf-8")):
                found += 1
                with self.subTest(where=rel):
                    self.assertEqual(int(m.group(1)), files,
                                     f"{rel} 写 {m.group(1)}，现算 {files}")
        self.assertGreater(found, 0, "那句「N 份至少犯一条」不见了")

    def test_the_last_rung_of_the_ladder_is_the_live_number(self):
        """`greeting_problems` 里那串「37 → 51 → 80 → 95」的**最后一格**
        就是现在这个数 —— 它和上面那句「95 份至少犯一条」是同一个数，
        写在同一段里的两处。

        变异实测：只改末格（`80 → 96`），整套测试全绿 —— 台阶接得上、
        抬头的次数也对，没有任何东西看那一格的值。而它一飘，下一个人
        读到的就是「这两天从 80 涨到 96」，去查一个不存在的 1 份。
        """
        _total, files, _spots, _over = self.live
        src = (ROOT / "tools" / "_cli.py").read_text(encoding="utf-8")
        i = src.index("def greeting_problems(")
        # **取整个函数，不要固定字符窗口。** 这道台阶每加一格就往后推一截 ——
        # 2026-08-31 加到第十格时 2400 字已经够不着末格，这条当场红在
        # 一个「上一格」上。同一课兄弟测试
        # `test_the_padding_survives_a_job_title` 里 2026-08-27 就记过一次，
        # 这一条没跟上。
        _end = src.find(chr(10) + "def ", i + 10)
        steps = re.findall(r"(\d+) → (\d+)（20\d\d-\d\d-\d\d）",
                           src[i:_end if _end > 0 else len(src)])
        self.assertTrue(steps, "那串台阶不见了")
        self.assertEqual(int(steps[-1][1]), files,
                         f"末格写 {steps[-1][1]}，现算 {files}")

    def test_the_offence_rate_is_right(self):
        total, files, spots, _over = self.live
        seg = TPL[TPL.index("字数必须实际统计后填写"):][:1800]
        m = re.search(r"(\d+) 处踩线、涉及 (\d+) 份（(\d+)%）", seg)
        self.assertTrue(m, "模板里那句踩线统计的写法变了")
        self.assertEqual(int(m.group(1)), spots, "处数不对")
        self.assertEqual(int(m.group(2)), files, "份数不对")
        self.assertEqual(int(m.group(3)), round(files / total * 100), "百分比不对")

    def test_the_control_group_is_right(self):
        """字数那条有自检行、其余五条没有 —— 对照组的数一起飘了
        （文档写「1 份超 200（0.4%）」，现算是 0 份）。"""
        over = self.live[3]
        seg = TPL[TPL.index("字数必须实际统计后填写"):][:1800]
        m = re.search(r"(\d+) 份里 (\d+) 份超 200", seg)
        self.assertTrue(m, "对照组那句的写法变了")
        self.assertEqual(int(m.group(1)), self.live[0])
        self.assertEqual(int(m.group(2)), over)

    def test_the_no_chat_box_count_is_right(self):
        """`sendVia` 那条铁律靠的就是这个数（「71 份被指去找一个不存在的入口」）。"""
        import json
        p = ROOT / "web" / "public" / "data.json"
        if not p.is_file():
            self.skipTest("还没导出面板数据")
        jobs = json.loads(p.read_text(encoding="utf-8"))["jobs"]
        n = sum(1 for j in jobs
                if (j.get("materials") or {}).get("greeting")
                and "多半没有聊天框" in ((j.get("materials") or {}).get("sendVia") or ""))
        if not n:
            self.skipTest("这份快照里没有这一类")
        for rel in ("workflows/reference/06-outreach-templates.md",
                    "tools/export_web_data.py"):
            text = (ROOT / rel).read_text(encoding="utf-8")
            m = re.search(r"(\d+) 份(?:被指去找|\*\*属于「多半没有聊天框」)", text)
            with self.subTest(where=rel):
                self.assertTrue(m, f"{rel} 里那个数不见了")
                self.assertEqual(int(m.group(1)), n,
                                 f"{rel} 写 {m.group(1)}，真值 {n}")


class TheArgumentTheseNumbersCarryStillHolds(unittest.TestCase):
    """这些数不是装饰，它们撑着一条规则：**有自检行的那条被遵守了，没有的没有。**
    哪天两边倒过来，那条规则就该重写，而不是把数改一改。"""

    def test_the_self_check_rule_is_still_there(self):
        self.assertIn("字数必须实际统计后填写", TPL)

    def test_the_five_rules_still_have_a_self_check_line(self):
        """那五条后来也加了自检行 —— 加它的理由就是这组对照。"""
        self.assertRegex(TPL, r"五类禁语|不许出现的五类")

    def test_the_word_list_is_still_shared(self):
        import export_web_data as E
        self.assertIs(E.GREETING_BANS, _cli.GREETING_BANS)

    def test_the_control_never_falls_behind(self):
        """对照组（有自检行的字数那条）**不许比那五条更差**。

        原来断的是严格小于 —— 那是 2026-08 的实情：字数 0 份超，
        五条 129 份踩线。2026-09-02 逐份改完之后两边都是 0，
        `assertLess` 当场红在 `0.0 not less than 0.0` 上。

        **这一红是对的，只是它指的不是数字而是结论**（本类的 docstring
        写着「哪天两边倒过来，那条规则就该重写」）。所以两件事一起做：
        `06` 那段论证改成「两边都归零了，而清零五条的不是自检行，
        是机械查」，这里的断言相应松成「不许落后」。

        **仍然抓得住真事故**：五条重新踩线而字数那条没有 —— 那时
        `over/total` 会小于 `files/total`，照旧通过（本来就该通过，
        那是原论证成立）；反过来字数那条烂了、五条干净，才是要红的。
        """
        live = _live()
        if live is None:
            self.skipTest("没有语料")
        total, files, _spots, over = live
        self.assertLessEqual(over / total, files / total,
                             "有自检行的那条反而更差了 —— 那段论证要重写")

    def test_the_doc_records_the_zero_and_who_earned_it(self):
        """归零这件事**必须连着「是什么把它清零的」一起写**。

        只写「现在 0 份」，下一个人会读成「自检行管用」—— 而那 129 份
        的自检里逐条打着勾。功劳记错了，下次就会靠自检行去防同类问题。
        """
        live = _live()
        if live is None:
            self.skipTest("没有语料")
        if live[1]:
            self.skipTest("还有踩线的，这条不适用")
        self.assertIn("清零那五条的不是自检行", TPL)


if __name__ == "__main__":
    unittest.main()
