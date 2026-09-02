"""同一个阈值出现在多个工作流里时，数值必须一致。

## 为什么

`workflows/` 里有一批**跨文件共享的常数**：判词天花板的档位边界、四维权重、
业务域封顶值、开场白字数上限、预筛的乐观薪数。它们的唯一来源是
`reference/04-job-evaluation.md`（或 `06-outreach-templates.md`），
但执行侧的工作流为了让读的人不必跳文件，**把数字又抄了一遍**。

抄一遍本身是合理的取舍——跳文件读规则会让执行变慢。**不合理的是没人钉住它们相等**：
改了框架而忘了改 `rank.md`，两边不会互相报错，AI 照着 `rank.md` 执行，
框架那份就成了摆设。这与本仓库反复修过的「同一条规则两个实现」是同一个病，
只是发生在文档之间而不是代码之间。

已有的 `test_verdict_cap` 只验「框架里有这几个数」和「rank.md 提到了天花板这个概念」，
**没有验数值相等**——把框架改成 85/65/45，那条测试照样绿。

## 做法

对每个共享常数给一个抽取式；凡是**出现**该常数的工作流文件都必须抽出**同一组值**。
文件里没提到就跳过（不是每个工作流都需要复述），提到了就必须一致。
"""

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(ROOT / "tools"))
import _cli  # noqa: E402
import gap_split  # noqa: E402
import scoring as sc  # noqa: E402

WF = sorted(list((ROOT / "workflows").glob("*.md"))
            + list((ROOT / "workflows" / "reference").glob("*.md")))


def texts():
    return {p.relative_to(ROOT / "workflows").as_posix(): p.read_text(encoding="utf-8")
            for p in WF}


#: 每条：(说明, 抽取函数) —— 抽出来的东西必须可比较且能代表那个常数。
#: 天花板四档，按顺序出现：`≥A` … `B-C` … `D-E` … `<F`
_BANDS = re.compile(
    r"[≥>]\s*(\d{2}).{0,500}?(\d{2})\s*-\s*(\d{2}).{0,500}?(\d{2})\s*-\s*(\d{2})"
    r".{0,500}?[<＜]\s*(\d{2})", re.S)


def _cap_bands(t: str):
    """判词天花板的档位下界 `(A, B, D)`。

    **结构化抽，不许白名单数值。** 第一版写成「只保留 80/60/40」——那是拿要
    验证的答案去过滤输入：把框架改成 85/65/45，这三个数直接从集合里消失，
    两边都变成空集，测试照样绿。**一个自证式的守卫比没有守卫更坏**，
    因为它会让人以为这条已经被守住了（实测：改框架后守卫全绿）。

    现在按天花板表的**四行顺序**取：`≥A / B-C / D-E / <F`，并校验相邻档首尾
    咬合（C = B-1、E = D-1、F = D），咬不上说明抽错了地方，返回 None 而不是
    一个似是而非的元组。
    """
    if "判词天花板" not in t and "差一口气" not in t:
        return None
    # 全文扫，取**第一个咬合成立**的序列。不要从关键词处起手切窗口：
    # 三个文件里那张表离「判词天花板」四个字有远有近（框架里隔了 400 行），
    # 固定窗口会切空。
    for m in _BANDS.finditer(t):
        a, b, c, d, e, f = (int(x) for x in m.groups())
        # `≥A / B-C / D-E / <F`：每档的上界紧贴上一档的下界（C=A-1、E=B-1），
        # 最后一档的 `<F` 就是 D。咬不上说明抽到的是别处的数字。
        if c == a - 1 and e == b - 1 and f == d and a > b > d:
            return (a, b, d)
    return None


#: 判词五档：强匹配 75+ / 值得投 60-74 / 可以考虑 45-59 / 不建议 30-44 / 跳过 <30。
#: 锚点用判词**名字**（它们是框架的稳定词），数字全抽出来验咬合——不预设数值。
#: 五个判词名从 `_cli.VERDICTS` 取，**不在这里再写一份**。
#:
#: 写死的代价见 `test_the_ai_flavour_list_is_actually_checked` 里那条实测：
#: 抽取式把类名写死，等于**拿要验证的答案去过滤输入** —— 文档那一侧先被
#: 裁成代码已有的那几项，多出来的一项永远进不了比较，而守卫一直是绿的。
#:
#: 这两处本来各另有一句数量断言兜着（`len(rows) == 4`、咬合校验），
#: 所以不是空转；改成派生是把「第二个住址」也一并去掉。
_V = _cli.VERDICTS       # (强匹配, 值得投, 可以考虑, 不建议, 跳过)
_VERDICT = re.compile(
    _V[0] + r"\s*[（(]\s*(\d{2})\s*\+.{0,80}?"
    + _V[1] + r"\s*[（(]?\s*(\d{2})\s*-\s*(\d{2}).{0,80}?"
    + _V[2] + r"\s*[（(]?\s*(\d{2})\s*-\s*(\d{2}).{0,80}?"
    + _V[3] + r"\s*[（(]?\s*(\d{2})\s*-\s*(\d{2}).{0,80}?"
    + _V[4] + r"\s*[（(]?\s*[<＜]\s*(\d{2})", re.S)


def _verdict_bands(t: str):
    """判词五档的档位下界 `(75, 60, 45, 30)`。

    这组数与判词天花板（`_cap_bands` 的 80/60/40）**不是同一组**：那边是技能维
    自己的分档，这边是综合分的档。`rank.md` 与框架各写了一份，此前没人钉住。
    """
    for m in _VERDICT.finditer(t):
        a, b, c, d, e, f, g, h = (int(x) for x in m.groups())
        # 咬合：值得投上界 = 强匹配下界-1，依次类推；跳过的 <H 即不建议下界
        if c == a - 1 and e == b - 1 and g == d - 1 and h == f and a > b > d > f:
            return (a, b, d, f)
    return None


def _weights(t: str):
    """四维权重 30/25/20/25。"""
    m = re.search(r"技能与经验[：: ]*\**\s*(\d{2})%.{0,120}?薪资与职级[：: ]*\**\s*(\d{2})%"
                  r".{0,120}?强度与公司性质[：: ]*\**\s*(\d{2})%"
                  r".{0,120}?发展与风险[：: ]*\**\s*(\d{2})%", t, re.S)
    return tuple(int(x) for x in m.groups()) if m else None


def _domain_cap(t: str):
    """业务域 < 40 时技能封顶 65。"""
    m = re.search(r"业务(?:领域|域)\s*[<＜]\s*(\d{2}).{0,20}?封顶\s*(\d{2})", t, re.S)
    return tuple(int(x) for x in m.groups()) if m else None


def _greeting_limit(t: str):
    """开场白字数上限。"""
    got = {int(x) for x in re.findall(r"≤\s*(\d{3})\s*字", t)}
    return got or None


def _optimistic_months(t: str):
    """预筛薪数未知时的乐观估值。"""
    m = re.search(r"(?:最乐观的?\s*(\d{2})\s*薪|(\d{2})\s*薪乐观估)", t)
    if not m:
        return None
    return int(m.group(1) or m.group(2))


def _sub_weights(t: str):
    """技能与经验这一维内部的子加权：`专业能力 × 0.6 + 业务领域 × 0.4`。

    **必须带上下文抽**，不能只找 `×0.数`：`cdp-portals.md` 里那个 `×0.2` 是
    限流倍率，跟打分毫无关系 —— 第一版不带上下文，把它当成了「子加权分叉」。
    """
    m = re.search(r"(?:专业能力|技术栈|专业)[^\n]{0,20}?[×xX*]\s*(0\.\d)"
                  r"[^\n]{0,40}?(?:业务域|业务领域|行业经验)[^\n]{0,20}?"
                  r"[×xX*]\s*(0\.\d)", t)
    return (float(m.group(1)), float(m.group(2))) if m else None


PROBES = [
    ("判词天花板的档位边界", _cap_bands),
    ("判词五档的档位边界", _verdict_bands),
    ("四维权重", _weights),
    ("业务域封顶", _domain_cap),
    ("开场白字数上限", _greeting_limit),
    ("预筛乐观薪数", _optimistic_months),
    ("技能维的子加权", _sub_weights),
]


class SharedConstantsAgreeAcrossWorkflows(unittest.TestCase):

    def test_each_shared_constant_has_one_value(self):
        docs = texts()
        problems = []
        for label, extract in PROBES:
            seen = {}
            for name, t in docs.items():
                v = extract(t)
                if v is not None:
                    seen[name] = v
            # **集合要归一再比。** `repr({40,80,60})` 与 `repr({80,40,60})` 不同，
            # 但两者相等——直接比 repr 会把「完全一致」报成分叉，那种假警报
            # 比不报更浪费时间（第一次跑本文件就中招）。
            def _norm(v):
                if isinstance(v, (set, frozenset)):
                    return tuple(sorted(v))
                return v
            if len({_norm(v) for v in seen.values()}) > 1:
                detail = "；".join(f"{n}={_norm(v)}" for n, v in sorted(seen.items()))
                problems.append(f"{label} 在不同文件里不一致 —— {detail}")
        self.assertEqual(
            problems, [],
            "工作流之间的共享阈值分叉了。改了框架就要改复述它的那几份，"
            "两边不会互相报错，AI 照着执行侧那份跑，框架那份就成了摆设：\n  "
            + "\n  ".join(problems))

    def test_the_probes_actually_find_something(self):
        """控制用例：抽取式全都抓不到时，上面那条会在空集上永远绿。

        这是本仓库反复吃过亏的形状（词表被清空 → 循环一次不跑 → 断言恒绿），
        所以每条抽取式至少要在一个文件里命中。
        """
        docs = texts()
        dead = [label for label, extract in PROBES
                if not any(extract(t) is not None for t in docs.values())]
        self.assertEqual(dead, [],
                         f"这些抽取式一个文件都没匹配到，等于空转：{dead}")

    def test_the_ceiling_is_restated_where_it_is_executed(self):
        """框架定规则，执行侧要复述——否则读的人得跳文件才知道怎么算。

        这一条与上面那条是一对：允许复述（可读性），但复述必须一致（正确性）。
        """
        docs = texts()
        # 框架自己也必须抽得出来。原来只钉执行侧两份：把 04 的天花板表改成
        # **不咬合**的错值（85/64/45 这类），抽取式解析失败返回 None，框架从
        # 比较里静默消失——分叉不可见，全绿。抽不出 = 表被改坏了，本身就该红。
        for name in ("job-rank.md", "job-upskill.md", "reference/04-job-evaluation.md"):
            with self.subTest(doc=name):
                self.assertIsNotNone(
                    _cap_bands(docs[name]),
                    f"{name} 的判词天花板档位边界抽不出来 —— "
                    "要么没复述，要么那张表被改成了首尾不咬合的错值")


class TheDocAndTheScorerAgree(unittest.TestCase):
    """`04` 那张阈值表和 `tools/scoring.py` 是同一组数的两个住址。

    上面那条守的是**工作流之间**（一份数被几个文档各抄一遍）。`04` 与**代码**
    之间那道缝，两边的守卫都够不着：`test_verdict_cap` 只验「框架里有这几个
    数」，`tools/` 内部只验 `audit_pipeline` 与 `scoring` 用的是同一个对象。

    实测 2026-08-31：把 04 的「强匹配（75+）」改成 85+，**全量 6800 条一条都
    不红**。

    裂开的后果不是崩溃，是**两套判断同时在跑**：执行者照 04 的表写「值得投」，
    而 `score.py` 重算成「可以考虑」—— 面板显示一个、评估文件写另一个。
    这个仓库为「同一条规则两个实现」修过很多次，这一处只是发生在文档与代码之间。

    判据钉**数**，不钉措辞：表怎么写、行怎么排都随它，抽出来的那组数要一样。
    """

    FRAMEWORK = (ROOT / "workflows" / "reference"
                 / "04-job-evaluation.md").read_text(encoding="utf-8")

    @classmethod
    def _bands(cls):
        """从 04 抽「判词（下限-上限）」。返回 [(下限, 判词), …] 与「跳过」的上限。"""
        rows, skip_below = [], None
        for m in re.finditer(
                r"\*\*(" + "|".join(_cli.VERDICTS)
                + r")（(<?)(\d+)(?:\+|-(\d+))?）\*\*",
                cls.FRAMEWORK):
            name, lt, lo, hi = m.group(1), m.group(2), int(m.group(3)), m.group(4)
            if lt == "<":
                skip_below = lo
            else:
                rows.append((lo, name, int(hi) if hi else None))
        return rows, skip_below

    def test_the_probe_finds_the_table(self):
        """用仪器之前先证明它会亮 —— 抽不到就静默全绿。"""
        rows, skip_below = self._bands()
        self.assertEqual(len(rows), 4, f"04 的阈值表抽出来是 {rows}，不是四档")
        self.assertIsNotNone(skip_below, "04 里没抽到「跳过（<N）」那一行")

    def test_the_verdict_bands_match(self):
        rows, _ = self._bands()
        doc = tuple((lo, name) for lo, name, _hi in rows)
        self.assertEqual(doc, sc.VERDICT_BANDS,
                         "04 的档位表和 scoring.VERDICT_BANDS 对不上 —— "
                         "执行者照文档判，score.py 照代码算，两边会给出不同的判词")

    def test_the_bands_are_contiguous(self):
        """顺带验 04 自己：每一档的上限必须正好接住下一档的下限，不许有缝。"""
        rows, skip_below = self._bands()
        # rows 是从高到低。判据：**下一档的上限 + 1 = 上一档的下限**。
        # 第一版拿的是同一行的上下限（`hi + 1 == lo`），三条 subTest 全红 ——
        # 而表本身没错。判据自己写错时报出来的话是「表有缝」，很容易顺着它去改表。
        for (hi_lo, hi_name, _), (lo_lo, lo_name, lo_hi) in zip(rows, rows[1:]):
            with self.subTest(lo_name):
                self.assertIsNotNone(lo_hi, f"「{lo_name}」没写上限")
                self.assertEqual(
                    lo_hi + 1, hi_lo,
                    f"「{lo_name}」（{lo_lo}-{lo_hi}）和「{hi_name}」（{hi_lo}+）"
                    "之间有缝或重叠")
        self.assertEqual(skip_below, rows[-1][0],
                         "「跳过（<N）」那个 N 不等于最低一档的下限")

    def _weight_statements(self):
        """全仓每一处**用数字写出四维权重**的地方 → `[(文件名, {维名: 小数})]`。

        判据：一个段落里出现 ≥3 个维名、每个后面跟着两位数，就算一次「陈述」。
        按**块**切（空行分段）—— `04` 那一处是四行列表，另外两处是一句话。

        维名从 `_cli.WEIGHTED_DIMS` 取，不在这里另抄一份。
        """
        import re as _re
        import _cli
        dims = _cli.WEIGHTED_DIMS
        pat = _re.compile("(" + "|".join(dims) + r")[^\n]{0,4}?(\d{2})")
        out = []
        files = sorted((ROOT / "workflows").rglob("*.md"))
        files += sorted((ROOT / "tools").glob("*.py"))
        for f in files:
            text = f.read_text(encoding="utf-8", errors="replace")
            for block in _re.split(r"\n\s*\n", text):
                got = {m.group(1): int(m.group(2)) / 100
                       for m in pat.finditer(block)}
                # **四维齐全、且加起来正好 1.0 才算「权重陈述」。**
                #
                # 只按「凑够三个维名」判会把**分数样例**也捞进来：
                # `job-rank.md` 里有一段 `技能与经验 63 / 薪资与职级 60 /
                # 强度与公司性质 50 / 发展与风险 70`（那是四维的分，不是权重），
                # 加起来 2.43。权重的和永远是 1（`job-setup.md` 那句甚至明写
                # 「和必须是 100」）。
                if len(got) == 4 and abs(sum(got.values()) - 1.0) < 1e-9:
                    out.append((f.name, got))
        return out

    def test_every_written_weight_agrees(self):
        """**四处写着这组数，此前只有一处被钉着。**

        `scoring.DIM_WEIGHTS` 是正本；散文里另有三处：

            04「默认权重是**技能与经验 30 / …**」那一句   ← 只有它被钉着
            04「## 权重」那张四行列表
            job-rank.md Step 3「按 04 的权重算总分：**技能与经验 30%…**」
            job-setup.md Section 4c，正文里同样那句默认权重

        最后那一处是写这条守卫时才冒出来的 —— 我按「三处」下笔，抽取器报了四处。

        最后那一处最要命：它就在执行者打分那一步的正文里。
        改一处忘三处的样子，这个仓库见过太多次。
        """
        got = self._weight_statements()
        self.assertGreaterEqual(
            len(got), 3, f"只找到 {len(got)} 处权重陈述，抽取器八成坏了")
        for name, doc in got:
            with self.subTest(name=name):
                for dim, w in doc.items():
                    self.assertEqual(
                        w, sc.DIM_WEIGHTS[dim],
                        f"{name} 写的「{dim} {int(w * 100)}」和 "
                        f"scoring.DIM_WEIGHTS 对不上")

    def test_the_weights_match(self):
        m = re.search(r"默认权重是\*\*([^*]+)\*\*", self.FRAMEWORK)
        self.assertIsNotNone(m, "04 里找不到那句「默认权重是…」")
        doc = {}
        for part in m.group(1).split("/"):
            name, _sp, num = part.strip().rpartition(" ")
            doc[name.strip()] = int(num) / 100
        self.assertEqual(doc, sc.DIM_WEIGHTS,
                         "04 的默认权重和 scoring.DIM_WEIGHTS 对不上")
        self.assertAlmostEqual(sum(doc.values()), 1.0, msg="04 的权重加起来不是 1")

    def test_the_greeting_limit_matches(self):
        """开场白字数上限：`06` 里那个数要等于 `_cli.GREETING_MAX`。

        **这一道原来只有一个方向有人拦。** `test_the_five_rules_are_actually_
        checked` 里写着 `assertEqual(_cli.GREETING_MAX, 200)` —— 那是测试里一个
        写死的字面量，钉的是**代码别乱动**：把 `_cli` 改成 250 会红。

        反过来那条路是通的：把 `06` 改成 250 而代码不动，**没有任何东西会红**，
        于是执行者照文档写到 250 字，而 `trim_opening` / 审计按 200 判它超了。
        对称地钉住两边，这个方向才关上。

        用的是 `_greeting_limit`（上面 `PROBES` 里那条），所以「06 与别的文档
        之间一致」和「06 与代码之间一致」共用同一个抽取式 —— 抽取式改了，
        两边一起跟着走。
        """
        doc = _greeting_limit(
            (ROOT / "workflows" / "reference"
             / "06-outreach-templates.md").read_text(encoding="utf-8"))
        self.assertIsNotNone(doc, "06 里抽不到开场白字数上限")
        self.assertEqual(doc, {_cli.GREETING_MAX},
                         "06 写的开场白上限和 _cli.GREETING_MAX 对不上 —— "
                         "执行者照文档写，工具照代码判，超没超两边说法不一样")

    def test_the_sub_weights_match_the_parser(self):
        """技能维的子加权还有**第五个住址**：`gap_split.FORMULA` 把它写死在正则里。

        `专业能力 N × 0.6 + 业务域 M × 0.4` 这个式子由执行者写进评估，再由
        `gap_split.read_pair` 回读 —— 而那个正则里的 `0.6` / `0.4` 是字面量。

        **失败方式是静默的**：口径若改成 0.7/0.3，新评估写 `×0.7`，正则配不上，
        `read_pair` 按设计返回 `None`（它的说明第一句就是「读不出返回 None ——
        不猜」），面板「对口的地方」那一栏就空了，没有任何报错。

        同一个形状那个文件自己记过一次（2026-08-27）：三份深评的拆解静默停在
        粗筛旧值，报出来的话是「算式算出 64 却写 61」—— 看着像评估算错了，
        其实是没读进去。

        文档那四份彼此一致由上面 `PROBES` 里的「技能维的子加权」那条管，
        这里只管**文档与正则**这一道。
        """
        doc = _sub_weights(self.FRAMEWORK)
        self.assertIsNotNone(doc, "04 里抽不到那个子加权式子")
        pat = gap_split.FORMULA.pattern
        for w in doc:
            with self.subTest(w):
                self.assertIn("0" + chr(92) + "." + str(w).split(".")[1], pat,
                              f"`gap_split.FORMULA` 里没有 {w} —— "
                              "口径改了而正则没跟，新写法会被静默读不出来")

    def test_the_coarse_levels_match(self):
        """粗筛那两维只许取的四档同理 —— 它决定的是分数的可信精度。"""
        m = re.search(r"只允许取\s*([\d\s/、]+?)\s*四档", self.FRAMEWORK)
        self.assertIsNotNone(m, "04 里找不到粗筛四档那句")
        doc = tuple(int(x) for x in re.findall(r"\d+", m.group(1)))
        self.assertEqual(doc, sc.COARSE_LEVELS,
                         "04 的粗筛四档和 scoring.COARSE_LEVELS 对不上")



if __name__ == "__main__":
    unittest.main()
