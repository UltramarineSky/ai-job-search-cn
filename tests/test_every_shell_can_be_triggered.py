# -*- coding: utf-8 -*-
"""每个壳都要有触发词，且触发词要真的写进了 frontmatter。

18 条命令从 stub（要用户敲斜杠）搬到壳（说一句就接管）之后，多出来 18 个
「自动接管」入口。没有触发词的壳等于**只有 Claude Code 用户叫得动它**——
非 Claude 的各家没有 `.claude/commands/` 那层语法糖。而触发词写在正文里不算数：
技能匹配只看 frontmatter 的 `name` + `description`，所以本文件既验「清单里有」，
也验「壳里印着」，两件事差一次没跑的 `gen_entries.py`。

解析 `description` 的正则住在 `tools/_entries.py`（`description_block` /
`trigger_words`），不在这里抄第三条 —— 同一个判据写两处，改一处忘一处，
而忘的那一处正是缺口藏身的地方
（`AGENTS.md`「一条规则只贴在一个写手身上，另外两个照样会犯」）。

## 撞词那半：为什么精确集合交集不够（2026-09-29 Task 6 裁定）

`tests/test_entries_derivation.py::test_no_command_shell_steals_a_router_word`
判的是**精确集合交集**（词表是快照 ∪ 壳那行「触发词：…」）。而 `job-resume` 的
「看看我简历」、`job-refresh` 的「刷一下简历」、`job-cv` 的「给这个岗定制简历」
**都包含**路由词「简历」，那条判据对它们一个字都没说。

匹配是精确的还是子串/语义的，判据不能靠猜：

- **仓库里没有任何代码拿触发词去比用户的话。** 读 `MANIFEST[…]["triggers"]` 的
  只有 `render_shell()`（把它印进 `description`）与测试。**决定谁接管的是各家工具
  的模型**，它读的是 frontmatter 里那段散文。
- **逐字判据下这功能是死的。** `docs/tool-entries.md`「换个工具，哪些命令还能用」
  那一节讲的是自然语言自动触发 —— 说一句「找职位」就开跑。而真人说的是「帮我找个职位」。
  它今天确实能跑，说明命中是**语义的、按具体性排名的**，不是字符串相等。
- 实测（2026-09-29 本会话载进来的技能清单）：这些壳连同渠道技能一起以
  `name: description` 的一行行文本交给模型挑，没有关键词表。

⇒ 「刷一下简历」**同时**够得上路由壳（含「简历」）和 `job-refresh`（整条触发词）。
这是真实存在的竞争，精确交集看不见它。

## 那为什么「光名词 ⊂ 动词短语」这种重叠可以留着

- 具体性有排名：整条命中比一个光名词强，模型挑得更窄的那一个。
- 抢输了代价有界：路由壳**自己声明它不跑工作流**、到那一步把命令交回用户
  （`test_the_chat_shell_hands_over_the_command.py` 钉着这条边界）。它接管最坏是
  「多问一句」，不是「跑错流程」。
- 反过来要求「命令壳的词里不许出现『简历』」会做出**更坏**的触发词：用户说的
  就是「简历」那个词。

## 什么会让它不安全（下面各有一条守卫，不是写在文档里就算）

1. 命令壳的触发词去掉路由词之后**只剩虚词** —— 那条在模型眼里跟路由壳一样宽，
   掷硬币。实测抓到一条：`job-interview` 的英文兜底词 `interview prep for` 整段
   吞掉路由词 `interview prep`，只多一个 `for`（它还超长，`总字符 ≤14` 那条也抓它
   —— 三条长度上限各自数什么，见下面那三个常量）。
   → `test_no_trigger_is_a_router_word_wearing_a_coat`
2. 路由壳把某条命令的**整段具体说法**收进自己的词表 —— 那条命令永远竞争不过。
   → `test_no_router_word_swallows_a_command_trigger`
3. 命令壳之间互相吞词 —— 同一个形状，共用同一条检测。
   → `test_no_command_trigger_swallows_another_commands`
   （`swallowed` 与**传入顺序无关**，两个方向都查：2026-09-29 评审抓到它原来只查
   「包含者在前」那一格，而这条守卫喂的是 `generated_names()` 的顺序 ——
   包含者恰好排在后面的用例根本没查，守卫却一直绿着。变异证据在
   `test_the_swallow_detector_can_fire`。）
4. 若哪一家工具把匹配改成**确定性关键词路由**（子串命中即接管），上面「按具体性
   排名」这个缓解就不成立，两条壳会同时接管。那时要动的不是本文件，是
   `test_no_command_shell_steals_a_router_word` —— 判据得升级成「一个词都不许共享」。

### 射程之外、今天就在撞的一处：记录住在测试里，不在这里

`.agents/skills/liepin-search/SKILL.md` 是渠道技能（判据是 `cli/src/cli.ts` 在不在），
不在 MANIFEST，所以本文件其余各条与 `test_entries_derivation.py` 都扫不到它 ——
而读 `.agents/skills/` 的那几家工具，壳清单里同时躺着这两份。

**它撞的是哪两个词、为什么不在本任务里顺手改、这笔债归谁裁：正本在
`KNOWN_PORTAL_COLLISIONS` 与 `ThePortalCollisionIsRecorded`**（那里逐字比盘上、
改一个字就红）。原来这几句只写在散文里，而**散文不会红** —— 谁把渠道壳那句描述
改了、谁接了新渠道带进一个同名词，都没有任何东西会说一声；2026-09-29 评审那条
说的正是这件事。

## 长度上限：单位要与名字相符（2026-09-29 评审第二条）

这条守卫的名字是「不许是一整句话」，而它原来只量**字符数**（`≤14`）。字符数对
中文是瞎的：中文没有空格分词，一个汉字就是一个词，盘上最长的中文触发词
9 个汉字 —— 14 个字符那条永远够不着它，实际只在管拉丁文（等于「≤3 个词」）。
现在三条并存、**一条都没放宽**：汉字 ≤9、英文 ≤3 词、总字符 ≤14（第三条是
Task 6 Step 2 定的那个数，原样保留，它管中英混排与单个超长单词那两种形状）。
每条各自抓得住哪种失败形态，证据在 `test_the_length_cap_can_fire`。

## 还有一件事：`ROUTER_GENERIC_WORDS` 是手抄的，本文件把它钉回正本

那份常量抄的是路由壳里「触发词：…」那一行，而它**已经飘过**：壳里有
「这个岗能投吗」，常量里没有。后果不是报错，是守卫静默缩小 —— 谁把路由壳的词
加宽，撞词检查就少盯一个词，而它要防的那次撞车正好变成看不见的。

方向选**「常量跟着壳」**而不是「壳跟着常量」：运行时读的是壳的 frontmatter，
常量只是给守卫用的一份快照。回读由 `_entries.router_shell_words()` 做。
为什么不在 import 时就派生（实测过）：把 `tools/` 与 `workflows/INDEX.md` 复制到
临时目录（就是 `test_generated_entries_are_current.py` 喂给 `gen_entries.py --check`
的那棵树，`_entries.ROOT` 跟着模块文件走），让派生发生在模块顶层，import 走到那一行
就 `FileNotFoundError` —— 那样那棵树上跑的对照用例会从「发现漂移」变成「撞死」，
成了假对照。所以派生放在**函数**里（只有测试调它），常量留在原地，等不等由
`test_the_constant_is_the_shells_own_words` 判。

再加一道：撞词守卫（本文件的 `overlaps()` 与
`test_entries_derivation.py::test_no_command_shell_steals_a_router_word`）用的不是
常量，是 `router_generic_words_in_force()` = **快照 ∪ 壳自己那行**。只加宽壳、
常量不动时守卫立刻跟着变严，不必等那根钉先红 —— 一根钉守着「另一个人有没有跑
这条测试」，那正是本仓库反复在防的形状。
"""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import _entries  # noqa: E402

#: 触发词要短 —— 写成一整句话，用户永远不会一字不差地说出来。
#: 但「短」得**按该文字自己怎么数**来判（2026-09-29 评审：原来只有一条 14
#: **字符**的上限，而它对中文是瞎的 —— 中文没有空格分词，汉字个数就是它的词数；
#: 盘上最长的中文触发词 9 个汉字，14 个字符那条永远够不着它，等于只管拉丁）。
#: 三条各管一种失败形态，**没有一条被放宽**：
TRIGGER_MAX_CJK = 9            # 中文：≤9 个汉字（盘上最长就是 9 —— `还有什么没写进资料`）
TRIGGER_MAX_WORDS = 3          # 拉丁：≤3 个词（一整句话是这个单位下的失败形态）
TRIGGER_MAX_CHARS = 14         # 总字符：Task 6 Step 2 定的那个数，一字没动。
                               # 它管前两条各只数到自己那半边的形状：中英混排
                               # （`两个offer怎么选`）与单个超长单词。

#: 当年超长、在 Task 6 被缩短掉的那三条（对照用例用它们证明上限不是摆设）。
WAS_TOO_LONG = ("apply to this job", "application report", "interview prep for")

#: 这些字**不增加任何具体性**：从触发词里去掉路由词之后只剩它们，那条触发词
#: 跟路由壳里那个光秃秃的名词就没有区别，两壳在模型眼里一样宽。
#: 中文那半边不查这张表，查去掉之后还剩几个汉字（见 `adds_nothing`）。
FILLER = frozenset("for to of a an the it its my me we you please how say in on and or"
                   .split())


def cjk_chars(word: str) -> list:
    return [ch for ch in word if "\u4e00" <= ch <= "\u9fff"]


def ascii_words(word: str) -> list:
    return [w for w in re.split(r"[^A-Za-z0-9]+", word) if w]


def why_over_cap(word: str) -> str:
    """这条触发词超了哪个单位（空串 = 三条都没超）。单位见上面三个常量。"""
    if len(cjk_chars(word)) > TRIGGER_MAX_CJK:
        return f"{len(cjk_chars(word))} 个汉字，超过上限 {TRIGGER_MAX_CJK}"
    if len(ascii_words(word)) > TRIGGER_MAX_WORDS:
        return f"{len(ascii_words(word))} 个词，超过上限 {TRIGGER_MAX_WORDS}"
    if len(word) > TRIGGER_MAX_CHARS:
        return f"{len(word)} 个字符，超过上限 {TRIGGER_MAX_CHARS}"
    return ""


def over_cap(word: str) -> bool:
    return bool(why_over_cap(word))


def adds_nothing(trigger: str, router_word: str) -> bool:
    """`trigger` 含住 `router_word`，却没比它多说出「要干的那件事」。"""
    left = re.sub(re.escape(router_word), "", trigger, flags=re.I)
    cjk = cjk_chars(left)
    if cjk:
        return len(cjk) < 2                 # 「刷一下简历」去掉「简历」还剩「刷一下」
    return not [w for w in ascii_words(left) if w.lower() not in FILLER]


def swallowed(pairs):
    """`(名字, 词)` 里所有「一条**整段包住**另一条」的关系 —— 撞词方向检测只写一份。

    **与传入顺序无关**（2026-09-29 评审抓的洞）：原来只查 `w2 in w1`，也就是
    「包含者恰好排在前面」那一种顺序，而喂给它 `generated_names()` 的那条守卫
    是按命令名排序的 —— 包含者排在后面的那一半用例**根本没查**，守卫却一直是绿的。
    现在每一对都查两个方向，并把**包住的那条**摆在元组前面，所以输出形状只取决于
    谁包谁，不取决于谁先出现在列表里。方向（哪一边算撞）留给调用方按名字筛，
    两条调用各自写着为什么只数自己那一边。
    """
    out = set()
    for i, (a, w1) in enumerate(pairs):
        for b, w2 in pairs[i + 1:]:
            if a == b or w1.lower() == w2.lower():
                continue
            if w2.lower() in w1.lower():
                out.add((a, w1, b, w2))
            if w1.lower() in w2.lower():
                out.add((b, w2, a, w1))
    return sorted(out)


def shell_texts(name: str):
    """一个壳在两族里的盘上正文：`(族, 文本)`；文件不存在时文本是 None。"""
    for fam in _entries.SHELL_FAMILIES:
        path = ROOT / fam / "skills" / name / "SKILL.md"
        yield fam, (path.read_text(encoding="utf-8") if path.is_file() else None)


class EveryShellCanBeTriggered(unittest.TestCase):
    def test_every_generated_shell_has_trigger_words(self):
        missing = [n for n in _entries.generated_names()
                   if not _entries.MANIFEST.get(n, {}).get("triggers")]
        self.assertEqual(missing, [], f"这些壳没有触发词，非 Claude 工具叫不动：{missing}")

    def test_the_router_shell_has_trigger_words_too(self):
        """路由壳不在 MANIFEST 的触发词里（它手写），但它是**最**自动接管的那一个。

        只扫 `generated_names()` 会把它整个漏掉：它那一行被删短、删没，
        「聊到求职就自动接管」这条招牌就断了，而没有一条测试会说。
        """
        bad = []
        for name in _entries.HANDWRITTEN_NAMES:
            for fam, text in shell_texts(name):
                if text is None or not _entries.trigger_words(text):
                    bad.append(f"{fam}/{name}")
        self.assertEqual(bad, [], f"这些壳的 frontmatter 里没有触发词：{bad}")

    def test_the_trigger_words_reach_the_frontmatter(self):
        """对照用例：触发词真的写进了 `description` —— 清单里有不等于壳里有。

        技能匹配只看 frontmatter 的 name + description，正文里写多少触发词都没用。
        比**整条序列**而不是「每个词都在里面」：少一个、多一个、顺序换了，都是壳
        与清单已经不一致 —— 那正是一次忘了跑的 `gen_entries.py` 的形状。
        """
        for name in _entries.generated_names():
            expected = tuple(_entries.MANIFEST[name]["triggers"])
            for fam, text in shell_texts(name):
                with self.subTest(shell=f"{fam}/{name}"):
                    self.assertIsNotNone(text, f"{fam}/{name} 不在盘上")
                    self.assertEqual(_entries.trigger_words(text), expected,
                                     f"{fam}/{name}: 壳里的触发词与 MANIFEST 不一致"
                                     "（description 结构不对时解析出来是空，同样红）")

    def test_each_shell_points_at_its_own_workflow(self):
        """壳名 = 命令名 = 工作流名。三者不一致，那条命令在别的工具里叫不动。"""
        for name in _entries.generated_names():
            for fam, text in shell_texts(name):
                with self.subTest(shell=f"{fam}/{name}"):
                    self.assertIsNotNone(text, f"{fam}/{name} 不在盘上")
                    self.assertIn(f"name: {name}", text)
                    self.assertIn(f"workflows/{name}.md", text,
                                  f"{fam}/{name}: 壳没有指向它的工作流正文")

    def test_a_trigger_word_is_not_a_whole_sentence(self):
        """触发词要短。写成一整句话，用户永远不会一字不差地说出来。

        量的单位按文字分（汉字个数 / 英文词数 / 总字符兜底），三个常量的来由
        写在它们自己那一段。
        """
        for name in _entries.generated_names():
            for word in _entries.MANIFEST[name]["triggers"]:
                why = why_over_cap(word)
                self.assertFalse(why, f"{name}: 触发词「{word}」{why}")

    def test_the_length_cap_can_fire(self):
        """变异内建：三条上限都不是摆设，而且**两条新单位抓得住旧单位抓不到的**。

        `WAS_TOO_LONG` 那三条是当年真被 shorten 的（对照 `MANIFEST` 的注释）；
        下面两条合成对是这次评审那条「单位与名字不符」的洞 —— 一句 12 个汉字的
        中文只有 12 个字符，旧的 14 字符上限看不见它；`give it a shot` 四个词
        正好贴着 14 个字符，同一句里那条也一样看不见。
        """
        for was in WAS_TOO_LONG:
            with self.subTest(word=was):
                self.assertTrue(over_cap(was), f"「{was}」{len(was)} 字符却没被判超长")
        self.assertTrue(over_cap("给这些岗都打一遍分行不行"),
                        "12 个汉字是一句话，而它只有 12 个字符")
        self.assertTrue(over_cap("give it a shot"),
                        "四个词是一句话，而它正好 14 个字符")
        # 盘上现役的那些贴着每条上限，谁把它们改短了会在这里红
        for ok in ("还有什么没写进资料",   # 9 汉字 = 汉字上限
                   "reset my data",       # 3 词 = 词数上限
                   "open dashboard",      # 14 字符 = 字符上限
                   "mock interview"):
            with self.subTest(word=ok):
                self.assertFalse(over_cap(ok), f"「{ok}」是盘上现役的形状，不该红")


class TheRouterWordListIsPinned(unittest.TestCase):
    """`ROUTER_GENERIC_WORDS` 必须等于路由壳自己那行「触发词：…」。"""

    def test_the_constant_is_the_shells_own_words(self):
        for fam in _entries.SHELL_FAMILIES:
            with self.subTest(fam=fam):
                got = _entries.router_shell_words(fam)
                self.assertEqual(
                    _entries.ROUTER_GENERIC_WORDS, got,
                    f"{fam} 的路由壳与常量已经不一致 —— 壳里多 "
                    f"{sorted(got - _entries.ROUTER_GENERIC_WORDS)}，常量多 "
                    f"{sorted(_entries.ROUTER_GENERIC_WORDS - got)}。\n"
                    "要么把常量补上（路由壳确实加宽了，守卫要跟着变严），"
                    "要么把那一行改回去。让两者不等 = 撞词守卫按更窄的那份算，"
                    "而它要防的那次撞车正好看不见。")

    def test_the_pin_holds_the_word_the_hand_copy_missed(self):
        """已知答案：「这个岗能投吗」在壳里、旧常量里没有（2026-09-29 实测的漂移）。

        这条不是复述上面那条 —— 它钉的是**方向**（正本在壳）。哪天有人把常量删回
        去、同时把那行也删短（两边一起错），上面那条会绿，这条红。
        """
        self.assertIn("这个岗能投吗", _entries.ROUTER_GENERIC_WORDS)
        self.assertIn("这个岗能投吗", _entries.router_shell_words())

    def test_the_parser_reads_a_wrapped_trigger_line(self):
        """变异内建：「触发词：」那一段会折行（手写路由壳实测折在顿号后面）。

        只按换行切的话 `job posting、CV` 会变成一个词，常量↔壳那根钉永远对不上，
        于是守卫从「能红」退化成「恒不匹配」。
        """
        text = ('---\nname: x\ndescription: >\n  说明一句\n'
                '  触发词：甲、乙、\n  丙、job posting、CV\n'
                'allowed-tools: Read\n---\n\n正文\n')
        self.assertEqual(_entries.trigger_words(text),
                         ("甲", "乙", "丙", "job posting", "CV"))

    def test_the_parser_says_none_when_there_is_nothing(self):
        """对照用例：没写触发词返回空，而不是把 description 里的顿号当词。"""
        text = '---\nname: x\ndescription: >\n  说明、还有一句\nallowed-tools: Read\n---\n'
        self.assertEqual(_entries.trigger_words(text), ())

    def test_a_trailing_period_is_not_part_of_a_word(self):
        """渠道壳写成「…、job openings。」时，句号不属于词。

        留着它，`job openings。` 与命令壳的 `job openings` 就比不出相等 ——
        而比不出相等的那种解析，正好把要抓的撞词说成「没撞」。
        """
        text = ('---\nname: x\ndescription: >\n  说明\n'
                '  触发词：甲、job openings。\nallowed-tools: Read\n---\n')
        self.assertEqual(_entries.trigger_words(text), ("甲", "job openings"))


class OverlapIsRankedBySpecificity(unittest.TestCase):
    """含路由词的触发词必须**比那个路由词更具体**（判据的来由见模块 docstring）。"""

    def overlaps(self):
        """盘上真实存在的 (命令, 触发词, 被它包住的路由词)。

        词表取 `router_generic_words_in_force()`（快照 ∪ 壳自己那行）而不是常量 ——
        守卫不能只信快照，否则「壳加宽、常量没跟上」这一格要靠另一条测试才看得见。
        """
        wide = _entries.router_generic_words_in_force()
        for name in _entries.generated_names():
            for word in _entries.MANIFEST[name]["triggers"]:
                for router in wide:
                    if router.lower() in word.lower():
                        yield name, word, router

    def test_no_trigger_is_a_router_word_wearing_a_coat(self):
        bad = []
        for name, word, router in self.overlaps():
            if word.lower() == router.lower() or adds_nothing(word, router):
                bad.append(f"{name}「{word}」= 路由词「{router}」+ 虚词")
        self.assertEqual(
            bad, [],
            "这几条跟路由壳的词一样宽，用户说到那个词时是掷硬币：\n  " + "\n  ".join(bad))

    def test_the_overlap_it_allows_is_the_verb_phrase(self):
        """正例：现在允许的重叠全是「动词 + 简历/面试」那种更窄的说法。

        这条同时是本仓库那条判据的**记录**：下面这几条**故意**含「简历」，
        别下一个人把它们当成撞词删掉（删了就得到更坏的触发词）。
        """
        seen = {(n, w) for n, w, _ in self.overlaps()}
        for n, w in (("job-resume", "看看我简历"), ("job-refresh", "刷一下简历"),
                     ("job-cv", "给这个岗定制简历"), ("job-add-template", "换个简历模板")):
            self.assertIn((n, w), seen,
                          f"{n} 不再有含路由词的「{w}」—— 词表或判据变了，"
                          "本条与模块 docstring 要一起改")

    def test_the_specificity_detector_can_fire(self):
        """变异内建：`adds_nothing` 不是恒假。"""
        self.assertTrue(adds_nothing("interview prep for", "interview prep"))
        self.assertTrue(adds_nothing("简历", "简历"))
        self.assertTrue(adds_nothing("面试吧", "面试"))
        self.assertFalse(adds_nothing("刷一下简历", "简历"))
        self.assertFalse(adds_nothing("准备面试", "面试"))
        self.assertFalse(adds_nothing("custom cv", "CV"))
        self.assertFalse(adds_nothing("apply to a job", "apply"))

    def test_no_router_word_swallows_a_command_trigger(self):
        """反方向：路由壳不许把某条命令的**整段具体说法**收进自己的词表。

        那样的话用户说出那句话时两壳同样宽，而赢的是**更宽**的那个 ——
        那条命令永远叫不动。

        只数「路由词包住命令词」这一边，是因为**另一边是本文件开头裁定允许的形状**：
        命令词里出现路由词（「刷一下简历」含「简历」）= 光名词 ⊂ 动词短语，
        具体性有排名、且路由壳自己声明它不跑工作流，代价有界；它的正确出路是
        「再具体一点」而不是「删掉」，所以那条判据住在
        `test_no_trigger_is_a_router_word_wearing_a_coat`，不在这里报。
        ⚠️ 这个方向是由**下面那个 `== "router"` 筛子**表达的，不是由「把路由词
        prepend 进列表」凑出来的 —— 后者正是 2026-09-29 评审抓到的那个假象
        （`swallowed` 当时只查「包含者在前」，命令↔命令那条守卫因此少查一半用例）。
        """
        pairs = ([("router", r) for r in _entries.router_generic_words_in_force()]
                 + [(n, w) for n in _entries.generated_names()
                    for w in _entries.MANIFEST[n]["triggers"]])
        bad = [f"路由词「{word}」整段吞掉了 {name} 的「{inner}」"
               for _, word, name, inner in swallowed(pairs) if _ == "router"]
        self.assertEqual(bad, [], "路由壳的词比命令壳还具体：\n  " + "\n  ".join(bad))

    def test_no_command_trigger_swallows_another_commands(self):
        """命令壳之间同一个形状：一条词整段包住另一条，两条撞在同一句话上。

        这一条**两个方向都算**（不像上面那条只数一边），因为命令壳没有路由壳那个退路：
        两边都会真跑工作流，「按具体性排名」在这里谁也没让给谁，用户说出那句长话时
        短的那条同样够格 —— 谁接管还是看运气。
        精确相同的那对不在这里报（`swallowed` 按定义要两条不同的字符串才谈得上包住），
        由下面那条单独数。
        """
        pairs = [(n, w) for n in _entries.generated_names()
                 for w in _entries.MANIFEST[n]["triggers"]]
        bad = [f"{a}「{w1}」整段包住 {b} 的「{w2}」"
               for a, w1, b, w2 in swallowed(pairs)]
        seen, dup = {}, []
        for n, w in pairs:
            other = seen.get(w.lower())
            if other and other != n:
                dup.append(f"{n} 与 {other} 共用同一条触发词「{w}」")
            seen.setdefault(w.lower(), n)
        self.assertEqual((bad, dup), ([], []),
                         "两条命令壳的触发词互相吞或完全相同：\n  "
                         + "\n  ".join(bad + dup))

    def test_the_swallow_detector_can_fire(self):
        """变异内建：`swallowed` 不是恒空，而且**与传入顺序无关**。

        这里同时是那次评审的更正记录：原来第二条断言写着「反过来的那对返回空」、
        注释是「被别人包住不算」—— 那不是规则，那是 `w2 in w1` 只看「包含者在前」
        留下的洞被当成判据记了下来。现在两个方向都查，输出把**包住的那条**排在前面，
        所以同一对不管谁先进列表都报出同一个形状。
        """
        trio = [("job-a", "刷一下简历"), ("job-b", "简历"), ("job-c", "看看我台账")]
        want = [("job-a", "刷一下简历", "job-b", "简历")]
        self.assertEqual(swallowed(trio), want)
        self.assertEqual(swallowed(list(reversed(trio))), want,
                         "判定不该随传入顺序变 —— 反过来的那半以前是空的")
        # 合成对：包含者排在**后面**（就是原来漏掉的那一格）与排在**前面**，两次同一结果
        late = [("job-x", "打分"), ("job-y", "给这些岗打分")]
        early = [("job-y", "给这些岗打分"), ("job-x", "打分")]
        want2 = [("job-y", "给这些岗打分", "job-x", "打分")]
        self.assertEqual(swallowed(early), want2)
        self.assertEqual(swallowed(late), want2,
                         "「包含者恰好排在后面」那一格 2026-09-29 之前恒返回空")


#: 今天真实存在的「渠道壳 ↔ 路由壳/命令壳撞词」，逐条记死。
#: **这份记录的正本在这里，不在 docstring 里** —— 记成散文的话，谁改了渠道壳
#: 那句描述、谁接了新渠道带进一个同名词，都没有任何东西会说一声（2026-09-29 评审）。
#: 元组形状：`(哪一族, 哪个渠道壳, 哪个词, 与它逐字相同的那一边)`。
#:
#: **谁还这笔债：用户，在本分支收尾时裁定。**
#: 不是 Task 9 —— 那条改的是 `tools/security_guards.py` 认各家的**权限文件**
#: （`allowed-tools` 的 schema），跟触发词撞车没有一条测试能互相接手；把债挂在它名下
#: 等于挂错人（`AGENTS.md`「跟进归用户，工具不催」那一节记的就是「一条规则只活在
#: 一次会话里、换个名字就整条丢掉」这类代价）。收尾那一次要裁的是二选一：
#: ① 渠道壳的词表也进撞词检查；② 在文档里写明「渠道壳只在该平台被点名时接管」。
#:
#: **不在这里顺手改 `liepin-search`**：那是可插拔渠道技能自己的描述（哪些目录算
#: 渠道的判据是 `cli/src/cli.ts` 在不在，见 `AGENTS.md`「工具特化」），
#: 而 ① 与 ② 还没裁 —— 裁之前改它，等于替用户做那个决定。
KNOWN_PORTAL_COLLISIONS = frozenset({
    (".agents", "liepin-search", "求职", "router"),
    (".agents", "liepin-search", "find jobs", "job-scrape"),
})


class ThePortalCollisionIsRecorded(unittest.TestCase):
    """射程之外那处撞词：现在有测试**记着它**，不再只是 docstring 里的一句话。

    渠道壳不在 `MANIFEST` 里，所以本文件其余各条与 `test_entries_derivation.py`
    都扫不到它 —— 而 `.agents/skills/` 正是 agy / Codex / Qoder / Qwen / MiMo
    那几家读的那一族，它们的壳清单里同时躺着路由壳与这份渠道壳。「求职」两边逐字相同，
    「find jobs」与 `job-scrape` 逐字相同（实测 2026-09-29，`_entries.trigger_words()`
    读出来比）。

    这条是**记录现状**，不是「红着等人来修」：今天它绿。它红只有两种样子，
    两种都说明这份记录该改了 ——
      - 少了一条：有人改了渠道壳/命令壳/路由壳的词（**修好了**，那就把这一节
        与模块 docstring 一起更新，并确认那次改动是有意的）；
      - 多了一条：接了新渠道、或新写的英文兜底词撞上了谁 —— 那是真的撞车，
        先解决再补记录。
    「记录过期就红」本身就是这条的价值；它同时证明判据不是恒空 ——
    解析器读不到词时这条集会空，而空集不等于记录里那两条。
    """

    def current_collisions(self):
        """按判据现算：有 `cli/src/cli.ts` 的目录 = 渠道，它的词逐字撞上谁。"""
        wide = {w.lower() for w in _entries.router_generic_words_in_force()}
        commands = {n: {w.lower() for w in _entries.MANIFEST[n]["triggers"]}
                    for n in _entries.generated_names()}
        out = set()
        for fam in _entries.SHELL_FAMILIES:
            skills = ROOT / fam / "skills"
            for cli in sorted(skills.glob("*/cli/src/cli.ts")):
                name = cli.relative_to(skills).parts[0]
                text = (skills / name / "SKILL.md").read_text(encoding="utf-8")
                for word in _entries.trigger_words(text):
                    if word.lower() in wide:
                        out.add((fam, name, word, "router"))
                    for cmd, words in commands.items():
                        if word.lower() in words:
                            out.add((fam, name, word, cmd))
        return frozenset(out)

    def test_the_record_is_exactly_what_is_on_disk(self):
        got = self.current_collisions()
        self.assertEqual(
            got, KNOWN_PORTAL_COLLISIONS,
            f"渠道壳的撞词记录与盘上不一致。\n"
            f"  盘上有、记录里没有（新撞车，先解决）：{sorted(got - KNOWN_PORTAL_COLLISIONS)}\n"
            f"  记录里有、盘上没了（撞词被修掉了 → 更新本条与模块 docstring 那一节）："
            f"{sorted(KNOWN_PORTAL_COLLISIONS - got)}\n"
            "还这笔债的是**用户、在本分支收尾时裁定**（理由与那两个选项见本文件上面"
            " `KNOWN_PORTAL_COLLISIONS` 那段）；不是 Task 9，那条只管权限文件。")


if __name__ == "__main__":
    unittest.main()
