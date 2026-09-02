"""实测页面时抓到的两类「看不出来的错」。

两条都不是眼睛能可靠发现的——所以必须机械扫。

## ① 用了不存在的 CSS 变量，声明静默失效

`color: var(--muted)` 里 `--muted` 没定义时，**不会报错**：整条声明在计算值阶段
作废，属性回落到继承值。字还看得见、页面还能用，只是你想要的层次没了。

一次实测扫出 **15 处**：`--muted` ×12（面试记录与简历块的次级文字色）、
`--line` / `--hair` / `--ink` 各 1。其中 13 处早就在那儿，没人发现过。

## ② 中文之间被 JSX 塞进空格

JSX 会把源码里的换行折成**一个空格**。这在拉丁文里是对的（单词本来就用空格分），
在中文里就是往词中间插了个空格：

    上面两格的差额里有 {parked} 个是<b>降权泊车</b>的——标题看着方向
    不对，留着没结案

渲染出来是「标题看着方向 不对」。写代码时按 80 列折行是本能，而它在中文里
每次都会留下这个疤。实测抓到 3 处，其中 2 处是当天刚写的。
"""

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CSS = ROOT / "web" / "src" / "theme" / "cockpit.css"
SRC = ROOT / "web" / "src"


#: 这个仓库有**两份** CSS，两份都要扫：
#: - antd 版面板（`serve.py` / `npm run build`）
#: - 单页版（`/job-dashboard`，CSS 内嵌在 `build_dashboard.py` 的 `_CSS` 字符串里）
#: 两边**调色板不一样**。照抄另一边的变量名过来，就是下面这条要拦的事——
#: 实测就这么犯了：往单页版里写了 `var(--faint)`／`var(--surface)`，
#: 那是 antd 版的变量名，单页版叫 `--ink3`／`--sheet`。
#: 单页渲染器删除后 `build_dashboard.py` 里已经没有 `_CSS`（`var(--` 出现 0 次），
#: 原来那个条目在空输入上恒绿，是陈列品——扫描源必须真有 CSS 可扫，见下面的
#: 控制用例。
CSS_SOURCES = [
    ("cockpit.css", CSS),
]


class EveryCssVarIsDefined(unittest.TestCase):

    @staticmethod
    def _undefined_in(t: str) -> dict:
        """{变量名: [行号…]}。带兜底值的 `var(--x, #fff)` 不算——那是有意的可选变量。

        找定义时**不能**用 `^\\s*(--x)\\s*:`：那样每行只认得第一个。单页版把
        `--ink:#17212b; --ink2:#4a5a68; --ink3:#8a97a3;` 写在同一行，于是
        `--ink2`／`--ink3` 全被当成没定义——一次误报 13 个，差点去"修"本来是对的代码。
        改成在任意位置找 `--x:`，并用后顾排除 `var(--x)` 里的那个冒号。
        """
        defined = set(re.findall(r"(?<!var\()(--[a-z0-9-]+)\s*:", t))
        bad: dict = {}
        for m in re.finditer(r"var\((--[a-z0-9-]+)\s*(,)?", t):
            if m.group(1) not in defined and not m.group(2):
                bad.setdefault(m.group(1), []).append(t[:m.start()].count("\n") + 1)
        return bad

    def test_every_source_actually_contains_css_vars(self):
        """控制用例：扫描源里必须真扫得到 var() 引用，空输入上的全绿不算数。"""
        for name, path in CSS_SOURCES:
            with self.subTest(css=name):
                n = path.read_text(encoding="utf-8").count("var(--")
                self.assertGreater(n, 10,
                                   f"{name} 里只有 {n} 处 var() —— 这个扫描源"
                                   "怕是已经不含 CSS 了，留着就是陈列品")

    def test_no_undefined_vars(self):
        for name, path in CSS_SOURCES:
            with self.subTest(css=name):
                bad = self._undefined_in(path.read_text(encoding="utf-8"))
                self.assertEqual(
                    bad, {},
                    f"{name} 用了没定义的 CSS 变量——不报错，但整条声明作废、"
                    "属性静默回落到继承值：\n"
                    + "\n".join(f"  {v} 在第 {ls} 行" for v, ls in sorted(bad.items())))

    def test_multiple_vars_on_one_line_are_all_seen(self):
        """解析器自检：一行里写多个变量，全都要认出来。"""
        t = ":root{ --a:#111; --b:#222; }\n.x{ color: var(--b); }\n"
        self.assertEqual(self._undefined_in(t), {},
                         "同一行的第二个变量没被认出来——会误报一堆本来正确的代码")

    def test_the_scan_can_actually_fail(self):
        """判据自检：塞一个假变量进去，上面那条必须能认出来。

        走的是**同一个** `_undefined_in`，不是另抄一份正则——抄一份就变成在验
        「我抄对了没有」。第一版正是两处各写各的，而且自检用例还用了中文变量名
        `--这个不存在`，被 `[a-z0-9-]+` 直接漏掉，自检自己先假了。
        """
        t = CSS.read_text(encoding="utf-8") + "\n.x { color: var(--no-such-var); }\n"
        self.assertIn("--no-such-var", self._undefined_in(t),
                      "扫描判据失效，上一条检查是空的")

    def test_a_var_with_a_fallback_is_not_flagged(self):
        """`var(--x, #fff)` 是有意的可选变量，不该误报。"""
        t = CSS.read_text(encoding="utf-8") + "\n.x { color: var(--opt, #fff); }\n"
        self.assertNotIn("--opt", self._undefined_in(t))

    def test_palette_is_documented_as_the_whole_list(self):
        """`:root` 上要写着「只有这些」，否则下一个人还会再编一个。"""
        t = CSS.read_text(encoding="utf-8")
        root = t[t.index(":root"):t.index("}", t.index(":root"))]
        self.assertIn("只有上面这些", root, ":root 没说清可用变量就这些")

    def test_nobody_re_checks_this_per_block(self):
        """按块再抄一份 —— 这件事已经发生过五次。

        实测 2026-08-31 一共**五份**，各自缩到自己那一块上：
        `test_a_local_zero_is_not_a_global_zero`、`test_headers_wrap_on_a_phone`、
        `test_the_header_does_not_reassure_falsely`、
        `test_the_home_turf_count_is_inventory`、
        `test_the_ready_pile_is_a_list_not_a_sentence`。
        全库都没有未定义的变量时，某一块自然也没有 —— 五份都是多余的。

        **后两份是这条守卫自己找出来的。** 手工 grep 只翻出三份 —— 那次
        搜索的正则写在 shell 的 heredoc 里，反斜杠被吃掉了一层。
        判据一跑就把漏的两份点了出来。

        **而它们抄的是正本已经修掉的那个写法**：`(?m)^\\s*--x\\s*:` 找定义，
        一行里写多个变量时只认得第一个（上面 `_undefined_in` 的说明记着
        那次误报 13 个）。抄件不会跟着正本一起被修，这才是删它们的理由 ——
        不是「重复」这三个字，是**重复的那一份带着已经修好的 bug**。
        （2026-08-31 五份一起删。）
        """
        here = Path(__file__).resolve().parent
        bad, seen = [], 0
        for f in sorted(here.glob("test_*.py")):
            if f.name == Path(__file__).name:
                continue
            seen += 1
            t = f.read_text(encoding="utf-8")
            if re.search(r"\{re\.escape\(v\)\}\\s\*:", t) or \
                    "def test_every_var_it_uses_is_defined" in t:
                bad.append(f.name)
        # **先证明真扫到了文件。** 空集上 `bad == []` 永远成立 —— 变异把
        # 循环整个短路掉时这条守卫一声不响（当场照出来的）。
        self.assertGreater(seen, 300, f"只扫到 {seen} 份测试，扫描多半没跑起来")
        self.assertEqual(
            bad, [],
            "这几份又把「变量定义了没」抄成了按块扫："
            + repr(bad) + "，全库那一份已经盖住了")


class NoStraySpacesInsideChinese(unittest.TestCase):
    """中文之间不该有空格。几乎每一处都是 JSX 源码换行折出来的。

    ## 判据要连中文标点一起认

    第一版的 `CJK` 只有 `[一-鿿]`（汉字本身）。可**中文最自然的折行位置恰恰是标点
    之后**——「命令行里跑，」换行、「找职位——」换行、「打开的是上一版。」换行。
    全角逗号（U+FF0C）、破折号（U+2014）都不在那个区间里，于是这一整类**一处也
    抓不到**：实测放宽之后当场冒出 10 处，而窄判据报的是 0。

    渲染出来就是「找职位—— 这一页」「里跑， 跑完」——全角标点自带的间距后面又多
    一个空格，缝比字还宽。
    """

    #: 汉字 + 中文标点（全角标点、书名号/引号、破折号）。空格出现在**它们之间**
    #: 才算错；中英交界处的空格是正常的，不在这个集合里。
    CJK = r"[一-鿿　-〿！-･—‘’“”]"

    def _files(self):
        return sorted(SRC.rglob("*.tsx"))

    @staticmethod
    def _strip_code(s: str) -> str:
        """只看 JSX **文本**，不看代码。

        代码里的空格是正常的（`const a = 1`），拿去比对会全是误报。做法是先去掉
        注释与 `{...}` 表达式，再只取标签之间那些含中文的片段。
        """
        s = re.sub(r"\{/\*.*?\*/\}", " ", s, flags=re.S)
        s = re.sub(r"/\*.*?\*/", " ", s, flags=re.S)
        s = "\n".join(ln for ln in s.splitlines()
                      if not ln.strip().startswith(("//", "*")))
        return s

    #: 插值（`{parked}`、`{ss.count}`）在渲染时就是一段文字，**不该把整句排除掉**。
    #: 原来的取法是 `>([^<>{}]*?)<` —— 只要句子里有一处插值，这一整段就看不见了。
    #: 实测漏掉的正是这样一句：
    #:
    #:     上面两格的差额里有 {parked} 个只看了标题、还没细看——标题显示方向不对，
    #:     留着没结案，抓详情时排在队尾。
    #:
    #: 「不对，」后面那个换行渲染成一个空格，而它一直绿着。含插值的句子在这一页
    #: 很常见（计数、用户名、日期），把它们整段跳过等于放掉一大片。
    EXPR = re.compile(r"\{[^{}]*\}")

    def _renderable(self, s: str) -> str:
        """把插值换成一个占位符，好让含插值的整句仍然被当作文本看待。"""
        return self.EXPR.sub("\x01", s)

    def test_no_space_between_cjk_in_jsx_text(self):
        bad = []
        for f in self._files():
            s = self._renderable(self._strip_code(f.read_text(encoding="utf-8")))
            # `>文本<` 之间的片段就是渲染出去的字
            for m in re.finditer(r">([^<>]*?)<", s, re.S):
                seg = m.group(1)
                if not re.search(self.CJK, seg):
                    continue
                # 换行 + 缩进 = JSX 会折成一个空格，正是要抓的
                for mm in re.finditer(rf"({self.CJK})\s*\n\s*({self.CJK})", seg):
                    # 行号要落在**原文件**上。第一版算在剥离后的文本上，报出来的
                    # 行号跟文件对不上——那种报错信息比不报还费时间。
                    frag = seg[max(0, mm.start() - 6):mm.start() + 2]
                    orig = f.read_text(encoding="utf-8")
                    at = orig.find(frag)
                    ln = orig[:at].count("\n") + 1 if at >= 0 else "?"
                    ctx = re.sub(r"\s+", "␣", seg[max(0, mm.start() - 12):
                                                  mm.start() + 14])
                    bad.append(f"{f.name}:{ln}  …{ctx}…")
        self.assertEqual(
            bad, [],
            "中文在 JSX 里跨行，会被折成一个空格插进词中间。\n"
            "折行改成把整句包进 {\"…\"}，或让换行落在标点/标签边界上：\n"
            + "\n".join(bad))

    def test_the_detector_can_actually_fail(self):
        """判据自检——拿一段确实有问题的 JSX 喂它，必须命中。"""
        sample = '<p className="x">标题看着方向\n              不对，留着没结案</p>'
        hits = list(re.finditer(rf"({self.CJK})\s*\n\s*({self.CJK})", sample))
        self.assertTrue(hits, "检测器认不出跨行的中文，上一条检查是空的")

    #: 拍平标签用的哨兵。挑一个**不含尖括号**的字符，保留「这里原本有个标签」
    #: 这个事实，同时不干扰正则。
    SENTINEL = "\x00"

    @classmethod
    def _flat(cls, s: str) -> str:
        """把所有标签拍平成哨兵——渲染出去的字就是这个样子。"""
        return re.sub(r"<[^>]*>", cls.SENTINEL, cls._strip_code(s))

    @classmethod
    def _hand_typed(cls, s: str):
        """产出「中文 + 真空格 + 中文」的位置。走 `_flat`，不另抄一份。"""
        pat = rf"{cls.CJK}{cls.SENTINEL}*[ \t]+{cls.SENTINEL}*{cls.CJK}"
        return list(re.finditer(pat, cls._flat(s)))

    def test_no_hand_typed_space_between_cjk(self):
        """上一条只认**换行折出来的**空格，认不出同一行里手打的那个。

        实测漏了一处，而且是屏幕上一眼能看见的：

            点任意一行展开详情 · <b className="lg-up">技能</b> 高于总分＝活对口

        `</b>` 后面那个空格是手打的，渲染出来就是「技能 高于总分」。上一条扫的是
        一个个 `>文本<` 片段，而这个空格落在片段的**开头**、它前面的中文在另一个
        片段里——两个片段各自都干净，合起来才是错的。

        所以这条把标签整个拍平，按**渲染后的样子**看。只认真空格与制表符、不认
        单纯的换行：块级兄弟元素（`<li>甲</li>` 换行 `<li>乙</li>`）拍平后也挨着，
        但它们本来就分行显示，认换行会把对的写法误报成错。
        """
        bad = []
        for f in self._files():
            flat = self._flat(f.read_text(encoding="utf-8"))
            for m in self._hand_typed(f.read_text(encoding="utf-8")):
                ln = flat[:m.start()].count("\n") + 1
                ctx = flat[max(0, m.start() - 16):m.start() + 18]
                bad.append(f"{f.name}:{ln}  …"
                           + ctx.replace(self.SENTINEL, "§").replace("\n", "⏎") + "…")
        self.assertEqual(
            bad, [],
            "中文之间手打了空格（§ 是被拍平的标签，它不产生断字）。\n"
            "把空格挪到标点或中英交界处，或者整句包进 {\"…\"}：\n" + "\n".join(bad))

    def test_the_flattening_detector_can_actually_fail(self):
        """判据自检——走的是**同一个** `_hand_typed`，不另抄一份。"""
        self.assertTrue(
            self._hand_typed('<span>详情 · <b className="x">技能</b> 高于总分</span>'),
            "跨标签的手打空格没被认出来")
        self.assertFalse(
            self._hand_typed("<ul>\n  <li>甲</li>\n  <li>乙</li>\n</ul>"),
            "块级兄弟元素之间的换行被误报成中文空格")
        self.assertFalse(self._hand_typed("<span>技能 82 分</span>"),
                         "中文与数字之间的空格是对的，不该报")


class MonospaceLetterSpacingIsLatinOnly(unittest.TestCase):
    """`.mono-label` 里不许有中文——这条规则**就写在那个 class 上面**。

    `cockpit.css` 自己的注释：「等宽小标签只给数字和拉丁文用：0.17em 字距 +
    uppercase 是拉丁排版的做法，套在中文上会拉成散架的一串」。`AGENTS.md` 也写了
    同一条：「等宽字体加大字距只适用于拉丁文……等宽只留给纯数字」。

    实测一打开页面就看到 4 处 `.mono-label` 里有 3 处塞了中文：
    「PDF 是旧的」（中英混排，注释里点名最糟的那种）、「简历待补 3」、
    「18 条」——最后一个是当天刚写的。规则写了三年没人扫，就会这样。

    改法不是删掉等宽，是**拆开**：数字留在 `.mono-label`，中文走 `.kicker`。
    """

    CJK = r"[一-鿿]"

    @classmethod
    def _mono_bodies(cls, s: str):
        """产出每个带 `mono-label` 的元素的**自身**内容。

        闭合标签要按**这个元素自己的标签名**找。第一版一律找 `</span>`，于是
        `<b className="mono-label">18</b>{" 条"}</span>` 里，`<b>` 的内容被算到了
        外层 `</span>`，把本来正确拆开的写法误报成违规——而那正是修好之后的样子。
        """
        for m in re.finditer(r'className="mono-label"', s):
            open_lt = s.rfind("<", 0, m.start())
            tag = re.match(r"<(\w+)", s[open_lt:])
            if not tag:
                continue
            gt = s.find(">", m.end())
            end = s.find(f"</{tag.group(1)}>", gt)
            if gt < 0 or end < 0:
                continue
            yield s[:m.start()].count("\n") + 1, s[gt + 1:end]

    def test_no_chinese_inside_mono_label(self):
        bad = []
        for f in sorted(SRC.rglob("*.tsx")):
            s = re.sub(r"\{/\*.*?\*/\}", " ",           # 注释里引用规则不算
                       f.read_text(encoding="utf-8"), flags=re.S)
            for ln, body in self._mono_bodies(s):
                # 只看文字，标签与表达式里的不算
                text = re.sub(r"<[^>]*>", "", re.sub(r"\{[^{}]*\}", "", body))
                if re.search(self.CJK, text):
                    bad.append(f"{f.name}:{ln}  "
                               f"{re.sub(chr(10) + r'\s*', ' ', body.strip())[:40]}")
        self.assertEqual(
            bad, [],
            "等宽 + 0.17em 字距是拉丁排版，中文套上去会散架、中英混排还会在接缝"
            "炸出大间隙。数字留 .mono-label，中文拆到 .kicker：\n" + "\n".join(bad))

    def test_the_rule_is_still_written_next_to_the_class(self):
        """这条检查的依据是 CSS 里那段注释。注释没了，检查就成了无源之水。"""
        t = CSS.read_text(encoding="utf-8")
        self.assertIn("只给数字和拉丁文用", t, ".mono-label 上的排版规则说明没了")

    def test_the_detector_can_actually_fail(self):
        """走同一个 `_mono_bodies`，不另抄一份——抄一份就是在验「我抄对了没有」。"""
        bad = '<span className="mono-label">PDF 是旧的</span>'
        self.assertTrue(any(re.search(self.CJK, b) for _, b in self._mono_bodies(bad)),
                        "检测器认不出等宽标签里的中文")

    def test_the_correct_split_is_not_flagged(self):
        """修好之后的写法——数字在内层 `<b class=mono-label>`、中文在外层——
        不该被误报。第一版正是在这里翻车的。"""
        ok = ('<span className="kicker">'
              '<b className="mono-label">18</b>{" 条"}</span>')
        for _, body in self._mono_bodies(ok):
            text = re.sub(r"<[^>]*>", "", re.sub(r"\{[^{}]*\}", "", body))
            self.assertFalse(re.search(self.CJK, text),
                             f"把正确的拆分写法误报了：{body!r}")


def _media_blocks(t: str):
    """每个 `@media {...}` 的 (起, 止) 偏移。按花括号配对找块尾，不靠缩进。"""
    out = []
    for m in re.finditer(r"@media", t):
        i = t.index("{", m.start())
        depth, j = 0, i
        while j < len(t):
            if t[j] == "{":
                depth += 1
            elif t[j] == "}":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        out.append((m.start(), j + 1))
    return out


class BreakpointsStayTogether(unittest.TestCase):
    """断点分处两地，改的人只会看到其中一个。

    ## 量的是「中间夹了多少别的 CSS」，不是首尾跨度

    原来量的是第一个 `@media` 到最后一个之间有多少行，上限 40。那个数把**分散**
    和**注释长**混成了一件事：断点全都紧挨着、只是其中一块写了 30 行原委，它照样
    红；反过来两块之间塞 39 行不相干的规则，它放行——而后者才是这条守卫要拦的。

    实测（2026-08-18）：给 620px 那块补窄屏表格的原委（为什么要多挂一层 `.cockpit`
    ——媒体查询不提升特异性，同形选择器在文件下方，写在这里一行都不生效），
    跨度从 40 涨到 64，守卫当场变红，而断点一块都没搬。

    现在量相邻两块 `@media` **之间**隔了多少行：块内怎么写不关它的事，
    只要中间没夹别的规则，就还是「在一处」。
    """

    #: 相邻两块之间允许的空行/短注释行数。超过就是夹了别的东西。
    MAX_GAP = 6

    def test_all_media_queries_are_in_one_place(self):
        t = CSS.read_text(encoding="utf-8")
        blocks = _media_blocks(t)
        self.assertTrue(blocks, "一个断点都没有？")
        bad = []
        for (_, a_end), (b_start, _) in zip(blocks, blocks[1:]):
            gap = t[a_end:b_start].count("\n")
            if gap > self.MAX_GAP:
                bad.append((t[:a_end].count("\n") + 1, t[:b_start].count("\n") + 1, gap))
        self.assertEqual(
            bad, [],
            f"这几对相邻断点之间夹着别的 CSS（起行, 止行, 夹了几行）：{bad}"
            "——断点分处两地，改响应式的人只会看到其中一个。集中到「响应式」那一段")

    def test_it_would_catch_a_scattered_breakpoint(self):
        """控制用例：把一块断点搬到别处去，上面那条必须报。"""
        t = CSS.read_text(encoding="utf-8")
        blocks = _media_blocks(t)
        self.assertGreaterEqual(len(blocks), 2, "只有一块断点，这条控制用例无从构造")
        first = t[blocks[0][0]:blocks[0][1]]
        # 把第一块搬到文件末尾——中间隔着全文，判据必须认出来
        moved = t[:blocks[0][0]] + t[blocks[0][1]:] + "\n" + first + "\n"
        b2 = _media_blocks(moved)
        gaps = [moved[a_end:b_start].count("\n")
                for (_, a_end), (b_start, _) in zip(b2, b2[1:])]
        self.assertTrue(any(g > self.MAX_GAP for g in gaps),
                        "断点被搬到文件另一头，判据却没报——它已经不认得「分散」了")


class AnOddGridDoesNotLeaveAnEmptyCell(unittest.TestCase):
    """流水线换成多列时，落单的那一格要占满整行。

    `.rail` 自己的底色就是分隔线（`--edge` 打底 + 1px gap 描出格线），所以格子少
    一个不是「留白」，而是**画出一个带边框的空卡片**——看着像坏掉了。

    实测：798px 窗口下，5 步排成 2 列 → 1,2 / 3,4 / 5+空，右边那半行就是这么一块。

    这条钉的是**两条规则必须成对**：只要 `.rail` 在某个断点改成多列，就必须有一条
    处理落单格的规则。少了后者，缺陷会在改断点的人完全看不见的地方复现。
    """

    def test_a_multi_column_rail_handles_the_lone_last_cell(self):
        t = CSS.read_text(encoding="utf-8")
        multi = re.findall(r"\.rail\s*\{[^}]*grid-template-columns:\s*repeat\((\d+)",
                           t)
        multi = [n for n in multi if int(n) > 1]
        self.assertTrue(multi, "找不到 .rail 的多列规则？这条要重写")
        if all(int(n) == 5 for n in multi):
            self.skipTest("现在只有 5 列这一种，5 步刚好填满，没有落单格")
        self.assertRegex(
            t, r"\.rail-cell:last-child:nth-child\(odd\)[^}]*grid-column",
            "`.rail` 有多列断点，却没处理落单的最后一格 —— "
            "格数是奇数时右边会画出一个带边框的空卡片")

    def test_the_step_count_is_actually_odd(self):
        """控制用例：真是奇数格，上面那条才有意义。

        数的是**页面实际渲染出几格**（导出的 `pipeline` 数组），不是源码里某个常量
        ——`.rail-cell` 是照它一条条铺的。第一版这里去数 `FUNNEL_STEPS`，而那是个
        `{阶段: 序号}` 的 dict、根本不是步数清单，当场就红了。
        """
        data = ROOT / "web" / "public" / "data.json"
        if not data.is_file():
            self.skipTest("还没导出 data.json")
        n = len(json.loads(data.read_text(encoding="utf-8")).get("pipeline") or [])
        self.assertTrue(n, "导出的 pipeline 是空的")
        self.assertEqual(n % 2, 1,
                         f"流水线现在是 {n} 格（偶数）——两列排得满，"
                         "上面那条落单格的规则可以撤了")


class MultiLineDataKeepsItsLineBreaks(unittest.TestCase):
    r"""来自文件的多行正文，**一律 pre-wrap**——换行的语义由取数层负责。

    面板上有三块正文是原样从 markdown 搬来的：打招呼开场白（`outreach.md`）、
    面试的答案与反馈（`interview_log.md`）。CSS 分不出「作者要断行」和「80 列
    排版折的行」——它看到的都只是 \n，只能一视同仁地全留。软折行在
    `build_dashboard.unwrap_soft_wraps` 里就已经接回去了。

    **反过来修过一次，是错的**：只给 `.ilog-fb` 加 `pre-line`，让所有 \n 都成硬
    换行。真实记录里 4 个换行有 3 个是 80 列折行，于是句子被从中间劈开——
    「升级成 / 可用产品」还是断的，只是从「中间多个空格」换成了「中间硬换行」。

    **这个类只管 CSS 这一半。**走数据那条路的断言在 `test_interview_log.py` 的
    `SoftWrapsAreJoinedRealBreaksSurvive`——「检查建在源码上、漏了数据」的正解
    是那个，不是这个。
    """

    #: 类名 → 必须的 white-space。三个值一样不是巧合，是同一条规矩。
    MULTILINE = {"greeting": "pre-wrap", "ilog-a": "pre-wrap", "ilog-fb": "pre-wrap"}

    @staticmethod
    def _rules(css: str) -> list:
        r"""`[(选择器, 规则体)]`，按出现顺序。剥注释、按大括号配对，所以分组、
        缩进、一行式、`@media` 里的嵌套都认。

        上一版是一条正则 `^\.cls\s*\{(.*?)^\}`，五种写法逐个骗过它——见 `PROBES`。
        """
        css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)      # 注释不是声明
        out, stack, start = [], [], 0
        for i, ch in enumerate(css):
            if ch == "{":
                stack.append((css[start:i], i + 1))
                start = i + 1
            elif ch == "}":
                if stack:
                    sel, body_at = stack.pop()
                    out.append((sel.strip(), css[body_at:i]))
                start = i + 1
        return out

    @classmethod
    def _blocks(cls, css: str, name: str) -> list:
        """选择器里带 `.name` 的规则体。`.ilog-fb` 不会被 `.ilog-fbx` 顶包。"""
        pat = re.compile(rf"\.{re.escape(name)}(?![\w-])")
        return [body for sel, body in cls._rules(css) if pat.search(sel)]

    @classmethod
    def _value(cls, css: str, name: str, prop: str):
        """`.name` 上 `prop` 的**生效值**，没写这个属性则 None。

        同名规则出现多次时取**最后一条**——层叠就是最后一条赢。只近似到「后面
        覆盖前面」，不算优先级：守卫宁可严一点。
        """
        hit = None
        for body in cls._blocks(css, name):
            for m in re.finditer(rf"(?:^|;)\s*{re.escape(prop)}\s*:\s*([^;{{}}]*)",
                                 body):
                hit = m.group(1).strip()
        return hit

    def test_they_keep_every_line_break_and_space(self):
        css = CSS.read_text(encoding="utf-8")
        bad = []
        for name, want in self.MULTILINE.items():
            if not self._blocks(css, name):
                bad.append(f".{name} 这个类不见了")
                continue
            got = self._value(css, name, "white-space")
            if got != want:
                bad.append(f".{name} 的 white-space 是 {got!r}，要 {want!r}")
        self.assertEqual(
            bad, [],
            "来自文件的多行正文要原样保留换行与缩进，否则文件里的换行会被折成"
            "空格、中文之间还会多出空格：\n" + "\n".join(bad))

    #: 判据自检。上一版守卫就是被这几种写法逐个骗过去的，每种留一条。
    PROBES = [
        ("一行式", ".x { white-space: pre-wrap; }", "pre-wrap"),
        ("分组选择器", ".a,\n.x {\n  white-space: pre-wrap;\n}", "pre-wrap"),
        ("@media 里缩进",
         "@media (max-width:720px) {\n  .x { white-space: pre-wrap; }\n}", "pre-wrap"),
        ("注释里的假值", ".x {\n  /* 原来是 pre-wrap */\n  white-space: normal;\n}",
         "normal"),
        ("后面又写了一条",
         ".x { white-space: pre-wrap; }\n.x { white-space: normal; }", "normal"),
        ("值拼错了", ".x { white-space: pre-warp; }", "pre-warp"),
        ("没写这个属性", ".x { color: red; }", None),
    ]

    def test_the_detector_is_not_fooled(self):
        """走的是**同一个** `_value`，不另抄一份正则——抄一份就是在验「我抄对了没有」。"""
        for label, css, want in self.PROBES:
            with self.subTest(label):
                self.assertEqual(self._value(css, "x", "white-space"), want)

    def test_a_longer_class_name_is_not_mistaken_for_it(self):
        self.assertEqual(self._blocks(".xy { white-space: normal; }", "x"), [])
        self.assertEqual(len(self._blocks(".x:hover { color: red; }", "x")), 1)


if __name__ == "__main__":
    unittest.main()


class SpacingLivesInCss(unittest.TestCase):
    """块间距写在 class 上，不写内联 style。

    2026-08-13 实测：三处 `style={{ marginTop: 26 }}` 各给各的，而 margin
    **只推上不推下**——命令表和紧跟它的「可以投的岗位」段头间距为 0，
    两个不同层级的东西贴在一起（其它相邻块都是 26px，只有这一处 0）。

    用户原话：「dashboard 收起的条目和旁边边界紧贴」。

    散在三处的好处一个也没有，坏处是**改一处不会影响另外两处**，
    而节奏是全页的事，不是某一块的事。
    """

    def test_panel_collapse_spacing_is_in_css(self):
        css = (ROOT / "web" / "src" / "theme" / "cockpit.css").read_text(encoding="utf-8")
        import re as _re
        m = _re.search(r"\.panel-collapse\.ant-collapse \{([^}]*)\}", css)
        self.assertIsNotNone(m, "找不到 .panel-collapse 的样式")
        self.assertIn("margin-block", m.group(1),
                      "间距没写在 class 上——写内联 style 会让三处各给各的")

    def test_no_inline_margin_on_collapses(self):
        app = (ROOT / "web" / "src" / "App.tsx").read_text(encoding="utf-8")
        self.assertNotIn("marginTop: 26", app,
                         "又出现内联 marginTop 了——它只推上不推下，下一块会贴上来")


class ScrollContainersDoNotShowTheirBars(unittest.TestCase):
    """把一个盒子设成横滚容器，就要顺手把滚动条关掉。

    2026-08-19 实测（2560px 视口、DPR 1.5）：命令 chip 每一个都挂着**两条**
    Windows 经典滚动条——横的一条、竖的一条，各 15px，而 chip 本身才 26px 高。
    命令块展开后 60 个 chip 无一幸免。用户原话：「位置足够，为什么还有滚动条」。

    真实溢出是 **0.01px**：内容右缘 839.79，内边距右缘 839.78。盒子的每一个数
    都是 0.85 倍缩放出来的小数（12.75px 字号 / 5.1px 内边距 / 0.667px 边框），
    `clientWidth` 向下取整、`scrollWidth` 向上取整，报出来就成了 2px。

    竖的那条**谁都没写**：规范规定一轴非 `visible` 时，另一轴的 `visible` 计算成
    `auto`。于是横条吃掉 15px 高 → 纵向溢出 → 竖条出现 → 又吃掉 15px 宽 →
    横向更溢出。两条互相锁死，谁都退不出去。

    所以 `overflow-x: auto` 不是错的（窄屏上真放不下时还得靠它），
    **错的是让这种 2px 的假溢出长出真滚动条**。
    """

    def test_chip_scroll_container_hides_its_scrollbars(self):
        css = CSS.read_text(encoding="utf-8")
        m = re.search(
            r"\.cockpit \.cmdbook-row \.ant-typography code,.*?\{([^}]*)\}",
            css, re.S)
        self.assertIsNotNone(m, "找不到命令 chip 那条规则")
        block = m.group(1)
        self.assertIn("overflow-x: auto", block, "窄屏兜底没了")
        self.assertIn("scrollbar-width: none", block,
                      "设了横滚容器却没关滚动条——2px 的假溢出会长出两条 15px 的真条")

    def test_the_webkit_fallback_covers_the_same_selectors(self):
        """`scrollbar-width` 要 Chrome 121+ / Safari 18.2+，旧内核只认伪元素。"""
        css = CSS.read_text(encoding="utf-8")
        m = re.search(r"([^{}]*::-webkit-scrollbar\s*\{[^}]*display:\s*none[^}]*\})", css)
        self.assertIsNotNone(m, "没有 ::-webkit-scrollbar 兜底")
        for chain in ("cmdbook-row", "rail-cell", "nextstep", "readout"):
            self.assertIn(chain, m.group(1), f"{chain} 的 chip 没进兜底选择器")


class BreakpointsInTsMatchTheCss(unittest.TestCase):
    """TS 里的 `matchMedia` 断点必须是 CSS 里真实存在的那几个。

    `Shortlist.useNarrow` 的注释写着「620px 跟 CSS 里已有的断点对齐，不另立一个」
    ——**而这个对齐没有任何守卫**。CSS 改了断点，TS 这边照旧用 620：
    于是在 560-620 这一段里，布局按新断点走、而表格按旧断点决定撤不撤列，
    两者错位。这类错只在特定宽度区间显形，测不到就永远发现不了。

    这条只管「TS 用的断点 CSS 里有没有」，不要求反向——CSS 可以有纯样式断点，
    那些 TS 本来就不需要知道。
    """

    def _bps(self, path, pattern):
        import re
        return set(re.findall(pattern, path.read_text(encoding="utf-8")))

    def test_every_ts_breakpoint_exists_in_css(self):
        import re
        css = set(re.findall(r"@media[^{]*max-width:\s*(\d+)px",
                             (ROOT / "web" / "src" / "theme" / "cockpit.css")
                             .read_text(encoding="utf-8")))
        self.assertTrue(css, "CSS 里一个媒体查询都没解析到")
        bad = []
        for p in (ROOT / "web" / "src").rglob("*.tsx"):
            for bp in re.findall(r"matchMedia\?\?\(|max-width:\s*(\d+)px",
                                 p.read_text(encoding="utf-8")):
                if bp and bp not in css:
                    bad.append(f"{p.name}: {bp}px")
        self.assertEqual(bad, [],
                         f"这些断点只在 TS 里存在，CSS 没有对应的媒体查询——"
                         f"布局和列的撤留会在某段宽度里错位：{bad}\n"
                         f"CSS 现有断点：{sorted(css)}")

    def test_narrow_hook_and_its_comment_agree(self):
        """注释说的数字必须就是代码里用的那个。"""
        import re
        src = (ROOT / "web" / "src" / "components" / "Shortlist.tsx").read_text(encoding="utf-8")
        seg = src.split("function useNarrow")[0][-500:] + src.split("function useNarrow")[1][:400]
        used = set(re.findall(r"max-width:\s*(\d+)px", seg))
        self.assertEqual(len(used), 1, f"useNarrow 里用了多个断点：{used}")
        bp = used.pop()
        self.assertIn(bp, seg, "注释里没提这个断点")
        self.assertIn("跟 CSS 里已有的断点对齐", seg, "没写清为什么是这个数")
