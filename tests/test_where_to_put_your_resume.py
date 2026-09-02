"""「我的简历放哪、要什么格式」——新用户读得到的地方必须答得上。

## 这是被当场问出来的

用户的原话：「简历要什么格式，放哪里也没说啊」。查下来不是没写，是**写在了没人会
看的地方，而且指错了路**：

- README 与 SETUP 里对「简历放哪」`grep` 零命中——两份入口文档一个字没提。
- 唯一说这件事的是 `documents/README.md`，**英文**，开头写着「This folder holds
  your actual career documents」——而它在**仓库根**。
- 可 `/job-setup` 按活动用户解析，去 `users/<名>/documents/cv/` 找。
- 而那个目录**根本不存在**：脚手架那句写的是「`users/<名>/documents/`
  （applications/ 等子目录）」，含糊的「等子目录」在实现时只建了 `applications/`。
- 仓库根倒是有一整套 `cv/ linkedin/ diplomas/ references/ postings/`（上游单用户
  时代的遗留，还进了版本库）——**最显眼的那个恰好是错的落点**。

四件事叠在一起：说明藏着、语言不对、路径指错、对的目录不存在。所以这条测试盯的不是
某一句措辞，而是**这四件事各自都成立**。

## 为什么格式必须写出来

Word 是国内最常见的简历格式，而这个工具**读不了** `.docx`（它是个压缩包，不是文本）。
不写出来，用户会把 `.docx` 放进去，然后花时间排查「为什么它没读到我的简历」。
"""

import re
import sys
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
import md  # noqa: E402  —— 围栏解析的规范实现，见 tests/md.py 顶部说明

DOCS_README = ROOT / "documents" / "README.md"
ENTRY_DOCS = (ROOT / "README.md", ROOT / "SETUP.md")

#: 脚手架必须建出来的子目录。`/job-setup` 与 `documents/README.md` 都按这份清单说话。
SUBDIRS = ("cv", "linkedin", "diplomas", "references", "postings", "applications")


class TheEntryDocsAnswerTheQuestion(unittest.TestCase):
    """新用户只会读 README 和 SETUP —— 答案得在这两份里。"""

    def test_they_say_where_the_resume_goes(self):
        for doc in ENTRY_DOCS:
            with self.subTest(doc=doc.name):
                text = doc.read_text(encoding="utf-8")
                # 验的是**说清了哪个子目录**，不是某一种拼写。
                # 两份文档写法不同（一份 `documents/cv/`，一份分开写「放 `cv/`」），
                # 钉死一种拼法只会逼着两边写成一样，而那不是这条要保证的事。
                self.assertRegex(
                    text, r"users/<[^>]+>/documents",
                    f"{doc.name} 说了 documents/ 却没说是**每个人自己**那份 —— "
                    "放到仓库根会被别人看见，而且 /job-setup 不去那里找")
                self.assertRegex(
                    text, r"`cv/`|documents/cv",
                    f"{doc.name} 没说简历具体放哪个子目录")

    def test_they_say_which_formats_work(self):
        for doc in ENTRY_DOCS:
            with self.subTest(doc=doc.name):
                text = doc.read_text(encoding="utf-8")
                self.assertIn("PDF", text, f"{doc.name} 没说支持什么格式")
                self.assertRegex(
                    text, r"docx",
                    f"{doc.name} 没提 Word —— 那是国内最常见的简历格式，"
                    "而这个工具读不了它。不写出来，用户会把 .docx 放进去然后卡住")


class TheFolderGuideIsUsableByItsAudience(unittest.TestCase):
    """`documents/README.md` 是唯一讲细节的那份，它得中文、得指对路。"""

    def test_it_is_written_in_chinese(self):
        text = DOCS_README.read_text(encoding="utf-8")
        han = len(re.findall(r"[一-鿿]", text))
        self.assertGreater(
            han, 200,
            f"这份说明只有 {han} 个汉字 —— 整个仓库是为中文求职者本地化的，"
            "唯独这份还是上游的英文原文")

    def test_it_points_at_the_per_user_path(self):
        text = DOCS_README.read_text(encoding="utf-8")
        self.assertRegex(
            text, r"users/<[^>]+>/documents",
            "它没写清材料要放进**每个人自己**的目录")

    def test_it_says_not_to_use_the_repo_root(self):
        """它自己就躺在仓库根，不写明白的话，那儿就是最像的落点。"""
        head = DOCS_README.read_text(encoding="utf-8")[:400]
        self.assertRegex(
            head, r"不要放|别放|不放",
            "开头没说明白「文件不要放在这个目录下」—— 说明躺在哪儿，"
            "用户就会往哪儿放")

    def test_it_lists_what_cannot_be_read(self):
        text = DOCS_README.read_text(encoding="utf-8")
        self.assertIn("docx", text, "没说 Word 读不了")
        self.assertRegex(text, r"PDF", "没说该转成什么")


class TheRootDoesNotOfferAWrongPlaceToDropFiles(unittest.TestCase):
    """仓库根不该再留一套同名的空目录 —— 那是上游单用户时代的遗留。

    留着它的代价很具体：它比正确的路径显眼得多（就在根目录，且唯一那份说明就在
    它旁边），而放进去的东西 `/job-setup` 永远读不到，多人共用时还互相可见。
    """

    def test_no_document_subdirs_are_tracked_at_the_repo_root(self):
        tracked = subprocess.run(
            ["git", "ls-files", "documents/"], cwd=ROOT,
            capture_output=True, text=True).stdout.split()
        stray = [f for f in tracked if f != "documents/README.md"]
        self.assertEqual(
            stray, [],
            f"仓库根的 documents/ 下还跟踪着这些：{stray} —— "
            "新 clone 会拿到一套看起来正确、实际读不到的空目录")

    def test_the_readme_itself_is_still_there(self):
        """控制用例：上面那条不能靠「把说明也删了」来满足。"""
        self.assertTrue(DOCS_README.is_file(), "documents/README.md 不见了")


class TheScaffoldCreatesEveryFolderItPromises(unittest.TestCase):
    """`/job-setup` 建用户时要把六个子目录**逐个**建出来。

    原来那句写的是「（applications/ 等子目录）」，实现时就只建了 `applications/`。
    目录不存在，对用户来说就等于「这里不收东西」。
    """

    def test_setup_names_each_subdir_explicitly(self):
        text = (ROOT / "workflows" / "job-setup.md").read_text(encoding="utf-8")
        i = text.find("脚手架出")
        self.assertNotEqual(i, -1, "setup.md 里找不到建目录那段")
        seg = text[i:i + 700]
        missing = [d for d in SUBDIRS if f"{d}/" not in seg]
        self.assertEqual(
            missing, [],
            f"脚手架那段没逐个点名这些子目录：{missing} —— "
            "含糊的「等子目录」正是 cv/ 一直没被建出来的原因")

    def test_no_vague_etc_in_that_paragraph(self):
        """含糊的枚举不许再出现在**指令**里。

        引文块（`>` 开头）要先剥掉：那一段正是在解释「原来写的是『等子目录』」，
        不剥的话断言会匹配到自己的说明——本轮已经踩到第四次同一个形状了。
        """
        text = (ROOT / "workflows" / "job-setup.md").read_text(encoding="utf-8")
        i = text.find("脚手架出")
        # `find()` 找不到会返回 -1，而 `text[-1:i+700]` 只剩最后一个字符——
        # 断言仍会红，但报的是「里面没有『等子目录』」，跟真因（锚点没了）差着几层。
        self.assertNotEqual(i, -1, "setup.md 里找不到「脚手架出」那段，锚点变了")
        seg = text[i:i + 700]
        seg = "\n".join(l for l in seg.splitlines()
                        if not l.lstrip().startswith(">"))
        self.assertNotRegex(
            seg, r"等子目录",
            "又写回「等子目录」了 —— 枚举写含糊，实现就会漏")


class EveryPlaceYouAreToldToPutAFileIsPerUser(unittest.TestCase):
    """凡是叫用户「把某个文件放到 X」的地方，X 都得写成按用户解析的形式。

    这不是简历一处的事，是**同一个陷阱的模板**：仓库根同时存在一个同名目录
    （`resume/` 放共享模板、`documents/` 放这份说明），而真正生效的是
    `users/<名>/…` 下那份。路径写成裸的，最像的落点就是错的那个。

    实测第二处：**简历照片**。README、SETUP、`resume/README.md` 三处都写着
    「把照片放到 `resume/photo.jpg`」，而 Typst 要求它和**用户自己那份**
    `main.typ` 同目录（`image()` 不许越出入口文件所在目录）。放进仓库根的
    `resume/`，Typst 直接找不到——而中文简历里照片恰恰是常见要求。
    """

    #: (要放的东西, 出现它的文档)。加一处新的「放文件」指引就往这里加一行。
    DROP_POINTS = [
        ("photo.jpg", (ROOT / "README.md", ROOT / "SETUP.md",
                       ROOT / "resume" / "README.md")),
    ]

    def test_the_path_shown_is_the_per_user_one(self):
        """**逐行**判定，不开上下文窗口。

        第一版取了前后各两行。而正确写法里 `main.typ` 的完整路径就在旁边，
        于是把落点改回裸路径**照样绿**——窗口把答案借给了错误答案。

        只看**写成路径的那些行**（含 `/photo.jpg`）；`照片: "photo.jpg"` 那种是
        参数值，按 Typst 的规定就该是不带路径的同目录文件名，不在此列。
        """
        # **先证明它会亮。** `if not paths: continue` 会把循环体清空：
        # 那几份文档一旦改写、不再把落点写成路径，这条就一次断言都不做地绿着。
        # 判据是「写成路径的那些行必须带 users/<你>/」—— 一行都扫不到时，
        # 「没有违规」和「没有可查的」长得一模一样。
        checked = 0
        for what, docs in self.DROP_POINTS:
            for doc in docs:
                text = doc.read_text(encoding="utf-8")
                paths = [l.strip() for l in text.splitlines() if f"/{what}" in l]
                if not paths:
                    continue
                checked += 1
                with self.subTest(what=what, doc=doc.name):
                    bad = [l for l in paths if not re.search(r"users/<[^>]+>/", l)]
                    self.assertEqual(
                        bad, [],
                        f"{doc.name} 里这些行给出了 {what} 的路径，却不是 "
                        f"users/<你>/… —— 仓库根有同名目录，最像的落点恰好是错的：\n  "
                        + "\n  ".join(bad))
        self.assertTrue(checked,
                        "一处写成路径的落点都没扫到 —— 判据失效了，不是没有违规")

    def test_it_warns_that_the_repo_root_is_the_wrong_one(self):
        """光写对路径还不够——根目录那个同名的太像了，得点明它不是。"""
        for what, docs in self.DROP_POINTS:
            for doc in docs:
                text = doc.read_text(encoding="utf-8")
                if what not in text:
                    continue
                with self.subTest(what=what, doc=doc.name):
                    self.assertRegex(
                        text, r"不是仓库根|不是你现在读的这个目录|不是仓库根的",
                        f"{doc.name} 没点明仓库根那个同名目录不是落点")


class UserFacingPathsAlwaysCarryTheUserPrefix(unittest.TestCase):
    """按用户解析的路径，出现在**会被照做**的地方时必须带 `users/<某个名字>/`。

    ## 两条规则，边界不一样

    文档有一条成文约定（`SETUP.md` 开头那段说明）：**正文写到个人文件时一律用简写**，
    由那一段统一解释映射。所以「每处提及都要写全」是错的规则——那会把作者的用意
    判成错误。但**命令是照着敲的**，简写在那里不成立。于是：

    - **规则 A**：围栏里的每个路径都要写全。**任何 info string 都算。**
    - **规则 B**：没有说明段覆盖的地方，正文里也不许用简写。

    ## 这个类被两轮代码审查各拆过一次，教训都写在下面

    第一版只扫标了 `bash`/`sh`/`powershell` 的围栏，漏掉三条**活缺陷**（行内代码里的
    `pdftotext`、没进清单的 `cover_letter/README.md`、散文里的
    `documents/applications/`），还有六个判据洞。

    第二版（这一版之前）修掉了那些，却引入七个新的：锚点找不到时窗口塌成整份文件、
    豁免标记不成对就静默豁免到文件尾、`#` 剥离把 Typst 代码当注释、
    删掉的覆盖控制没人替补、规则 B 既无发火控制又手抄词表、
    `_qualified` 允许前缀与路径之间夹任意内容。

    **共同的形状是「判据自己失效时没人喊」。** 所以这一版的控制用例不再只问
    「扫到了几行」，而是逐条钉住：词表非空且真取自枚举、标记必须成对且区段里真有
    说明、每份文档都真的被扫到、判据对四种确凿违规必须报错。
    """

    #: `AGENTS.md` 里那份枚举的两个端点。**必须两个都找到**——只找一个然后开窗口，
    #: 是上一版最狠的一个洞：`find()` 返回 -1 时 `text[max(0,i-700):i]` 塌成
    #: `text[0:-1]`，也就是整份文件，词表从 18 项暴涨到 61 项（含裸 `users/`），
    #: 于是**每一条写对了的路径反而被判违规**，而控制用例照样绿。
    ENUM_HEAD = "本仓库任何命令/技能里提到"
    ENUM_TAIL = "一律解析为"

    @classmethod
    def per_user_things(cls) -> set:
        text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        i, j = text.find(cls.ENUM_HEAD), text.find(cls.ENUM_TAIL)
        assert i != -1 and j != -1 and i < j, (
            f"AGENTS.md 里那份枚举的端点找不到（{cls.ENUM_HEAD!r} / "
            f"{cls.ENUM_TAIL!r}）—— 端点变了就必须改这里，"
            "而不是让窗口悄悄扩到整份文件")
        out = set()
        for raw in re.findall(r"`([A-Za-z_][\w./*-]*)(?:…|\.\.\.)?`", text[i:j]):
            v = raw.rstrip("…./")
            if not v:
                continue
            tail = v.split("/")[-1]
            out.add(v if "." in tail else v + "/")
        out |= {t.replace(".typ", ".pdf") for t in out if t.endswith(".typ")}
        return {t for t in out if "/" in t or "." in t}

    #: 共享框架文件留在仓库根，**不**按用户解析（`AGENTS.md` 的例外清单）。
    SHARED = ("resume/template.typ", "resume/example.typ", "cover_letter/template.typ",
              "cover_letter/example.typ", "documents/README.md", "templates/README.md",
              "templates/cv/", "templates/cover_letters/", "profile.example/",
              "workflows/", "tools/", ".agents/")

    DOCS = (ROOT / "README.md", ROOT / "SETUP.md",
            ROOT / "resume" / "README.md", ROOT / "cover_letter" / "README.md",
            ROOT / "documents" / "README.md")

    EXEMPT_OPEN = "<!-- per-user-path-explainer -->"
    EXEMPT_CLOSE = "<!-- /per-user-path-explainer -->"

    #: 只有这些 info string 的围栏里，`#` 才是注释。
    #: **Typst 的 `#` 是代码前缀**（`#import`、`#show:`、`#cover_letter(`）——
    #: 上一版对所有围栏一律按注释剥，于是两份 README 里 18 个 typst 块的
    #: `#` 开头行整行被丢，那些块里的路径从没被检查过。
    SHELL_INFO = ("", "bash", "sh", "shell", "zsh", "console", "powershell", "ps1")

    @classmethod
    def _exempt_lines(cls, text: str):
        """`(豁免的行号集合, 未闭合的 OPEN 行号列表)`。

        不成对**不是**「豁免到文件尾」，而是要被 `test_exemption_markers_are_balanced`
        当场报出来：漏一个 CLOSE 就静默关掉整份文档剩下的检查，是上一版最容易被
        无意触发的失效方式（编辑那张表时删掉一行注释就够了）。
        """
        out, open_at, dangling = set(), None, []
        for n, line in enumerate(text.splitlines(), 1):
            if cls.EXEMPT_OPEN in line:
                # **已经开着又来一个 OPEN** 也算不成对：前一个的 CLOSE 丢了，
                # 而后一个的 CLOSE 会把它一并关掉，于是漏标这件事被掩盖。
                # 突变实测：删掉第一对的 CLOSE，检查照样绿。
                if open_at is not None:
                    dangling.append(open_at)
                open_at = n
            if open_at is not None:
                out.add(n)
            if cls.EXEMPT_CLOSE in line:
                if open_at is None:
                    dangling.append(n)          # 孤立的 CLOSE
                open_at = None
        if open_at is not None:
            dangling.append(open_at)
        return out, dangling

    @classmethod
    def _qualified(cls, norm: str, thing: str) -> bool:
        """`users/<某个名字>/` 必须**紧挨在这一处出现的前面**。

        上一版允许前缀与路径之间夹任意非空白内容，于是
        `users/张三/resume/main.typ,resume/main.pdf` 里那条**裸的输出路径被前面
        那条写对的洗白**——正是「一条命令两个路径」那个洞在 token 粒度上的复活。
        """
        pat = re.compile(r"users/[^/\s]+/$")
        idx = norm.find(thing)
        while idx != -1:
            if pat.search(norm[:idx]):
                return True
            idx = norm.find(thing, idx + 1)
        return False

    @classmethod
    def _bare_in(cls, tok: str, things) -> str:
        """这个 token 里有没有**没写全**的按用户解析路径；有就返回它。

        两条规则都走这一个判据——上一版规则 B 自己又写了一遍循环，于是
        `test_the_check_can_still_fire` 验的是规则 A 的判据，规则 B 那份从没被验过。
        """
        norm = tok.replace(chr(92), "/")          # 反斜杠也是路径分隔符
        if any(s in norm for s in cls.SHARED):
            return ""
        for thing in sorted(things, key=len, reverse=True):
            if thing in norm and not cls._qualified(norm, thing):
                return thing
        return ""

    #: 切 token 的分隔符。**逗号/分号/箭头也要切**：不切的话两条路径粘在一个
    #: token 里，写对的那条会把裸的那条洗白。
    SPLIT = re.compile(r"[\s\"'`,;（）()\[\]、，。|]+|->|→")

    @classmethod
    def _scan_line(cls, line: str, things):
        for tok in cls.SPLIT.split(line):
            hit = cls._bare_in(tok, things)
            if hit:
                return tok
        return ""

    # ---------- 控制用例：判据自己失效时必须有人喊 ----------

    def test_the_watchlist_comes_from_the_enumeration(self):
        things = self.per_user_things()
        for must in ("profile/", "documents/", "job_search_tracker.csv",
                     "resume/main.typ", "resume/main.pdf"):
            with self.subTest(item=must):
                self.assertIn(must, things, f"没从枚举里取到「{must}」")
        # 取多了同样是坏的：窗口一旦越界，写对的路径会被判违规
        self.assertLess(len(things), 30,
                        f"词表膨胀到 {len(things)} 项，窗口多半越界了：{sorted(things)}")

    def test_the_check_fires_on_all_four_known_shapes(self):
        """四种确凿违规都要报，写全的不能报。少一种，对应那个洞就是敞开的。"""
        t = self.per_user_things()
        self.assertTrue(self._bare_in("resume/main.typ", t), "裸路径不报")
        self.assertFalse(self._bare_in("users/张三/resume/main.typ", t), "写全的反而报")
        self.assertTrue(self._bare_in("documents" + chr(92) + "applications" + chr(92) + "x", t),
                        "反斜杠写法绕过")
        self.assertTrue(self._bare_in("users/resume/main.typ", t),
                        "`users/` 后面少了名字那一段，仍被当成写全了")
        self.assertTrue(
            self._scan_line("users/张三/resume/main.typ,resume/main.pdf", t),
            "同一行里写对的那条把裸的那条洗白了")

    def test_exemption_markers_are_balanced(self):
        """漏一个 CLOSE 就静默关掉整份文档剩下的检查 —— 必须当场报出来。"""
        bad = []
        for doc in self.DOCS:
            if not doc.is_file():
                continue
            _, dangling = self._exempt_lines(doc.read_text(encoding="utf-8"))
            bad += [f"{doc.name}:{n}" for n in dangling]
        self.assertEqual(bad, [],
                         "豁免标记没成对：\n  " + "\n  ".join(bad)
                         + "\n单独一个 OPEN 会把它之后的每一行都豁免掉")

    def test_every_exempt_region_really_explains_the_shorthand(self):
        """光有标记不够 —— 那是个**绕过机制**，得证明那一段真的在讲映射。

        否则任何人只要在一段裸路径上下加一对注释，检查就不再看它，
        而评审从 diff 里只会看到两行 HTML 注释。
        """
        for doc in self.DOCS:
            if not doc.is_file():
                continue
            text = doc.read_text(encoding="utf-8")
            lines = text.splitlines()
            skip, _ = self._exempt_lines(text)
            if not skip:
                continue
            with self.subTest(doc=doc.name):
                seg = "\n".join(lines[n - 1] for n in sorted(skip))
                self.assertRegex(
                    seg, r"简写|实际位置|旧布局|升级前|→",
                    f"{doc.name} 有豁免区段，但那一段看不出是在讲「简写→实际位置」"
                    "或旧布局 —— 豁免不能只凭一句注释就成立")

    def test_every_doc_is_really_scanned(self):
        """每份文档都得**真的**被扫到，而不是因为不存在或全被豁免而跳过。

        上一版把「扫到几行」那条控制删了，于是 `DOCS` 全指向不存在的文件、
        围栏解析返回空、或标记把整份豁免掉，四条测试**全绿**（突变证实）。
        """
        things = self.per_user_things()
        for doc in self.DOCS:
            with self.subTest(doc=doc.name):
                self.assertTrue(doc.is_file(), f"{doc} 不存在 —— 扫描会静默跳过它")
                text = doc.read_text(encoding="utf-8")
                skip, _ = self._exempt_lines(text)
                live = [n for n, _ in enumerate(text.splitlines(), 1) if n not in skip]
                self.assertTrue(live, f"{doc.name} 整份都被豁免了")
        self.assertTrue(things, "词表是空的 —— 扫描等于没做")

    # ---------- 两条规则 ----------

    def test_rule_a_every_path_in_a_fence_is_qualified(self):
        things = self.per_user_things()
        bad, scanned = [], 0
        for doc in self.DOCS:
            if not doc.is_file():
                continue
            text = doc.read_text(encoding="utf-8")
            skip, _ = self._exempt_lines(text)
            for n, line, info in md.fenced_lines(text):
                if n in skip:
                    continue
                # `#` 只在 shell 系围栏里是注释；Typst 的 `#` 是代码前缀
                # 三元写法在这里踩过一次：`a if cond else "" in X` 会被解析成
                # `a if cond else ("" in X)`，于是 `typst` 求值为真、照样剥 `#`。
                # 拆成两行，不要在条件里省括号。
                lang = info.split()[0].lower() if info.split() else ""
                if lang in self.SHELL_INFO:
                    line = re.split(r"(?:^|\s)#", line, maxsplit=1)[0]
                if not line.strip():
                    continue
                scanned += 1
                tok = self._scan_line(line, things)
                if tok:
                    bad.append(f"{doc.relative_to(ROOT).as_posix()}:{n}  {tok[:60]}")
        self.assertGreater(scanned, 10, f"只扫到 {scanned} 行围栏内容，扫描多半失效了")
        self.assertEqual(
            sorted(set(bad)), [],
            "围栏里的这些路径是照着敲的，却写成了简写 —— 照抄会报 "
            "`input file not found`：\n  " + "\n  ".join(sorted(set(bad))))

    #: 规则 B 只盯这几样：**读者会照着去找的产出与记录**。
    #:
    #: 正文不能一律要求写全 —— `SETUP.md` 开头明说「本文写到个人文件时一律用简写」，
    #: 而且有些句子是**在说那个裸路径是错的**（「`documents/` 下不行：…」）。
    #: 把整份枚举套到正文上，实测 5 处全是误报，其中一处正是那句警告本身。
    #:
    #: 但窄不等于可以手抄：下面 `test_rule_b_watchlist_is_derived` 断言它是
    #: `per_user_things()` 的**真子集**——写错一个名字、或枚举里删掉一项，当场红。
    PROSE_WATCH = ("documents/applications/", "resume/main.typ", "resume/main.pdf",
                   "cover_letter/main.typ", "cover_letter/main.pdf",
                   "job_search_tracker.csv")

    def test_rule_b_watchlist_is_derived(self):
        """窄词表必须是枚举的子集，且非空、且判据对它确实会触发。

        上一版这份表既不与枚举关联（`documents/applications/` 甚至不在枚举里），
        也没有任何发火控制：`ACTED_ON = ()` 之后四条测试全绿。
        """
        things = self.per_user_things()
        self.assertTrue(self.PROSE_WATCH, "正文词表是空的 —— 规则 B 等于没跑")
        stray = [w for w in self.PROSE_WATCH
                 if not any(w in t or t in w for t in things)]
        self.assertEqual(stray, [], f"这些词不在 AGENTS.md 的枚举里：{stray}")
        for w in self.PROSE_WATCH:
            with self.subTest(item=w):
                self.assertTrue(self._bare_in(w, self.PROSE_WATCH),
                                f"判据对裸的「{w}」不报错 —— 规则 B 已经空转")

    def test_rule_b_prose_outside_an_explainer_is_qualified(self):
        """规则 B 与规则 A **共用同一个判据**（`_bare_in`）。

        上一版这里自己又写了一遍循环，于是那条「判据还能触发吗」的控制用例验的是
        规则 A 的判据，规则 B 那份从没被验过。
        """
        things = self.PROSE_WATCH
        bad = []
        for doc in self.DOCS:
            if not doc.is_file():
                continue
            text = doc.read_text(encoding="utf-8")
            skip, _ = self._exempt_lines(text)
            fenced = {n for n, _, _ in md.fenced_lines(text)}
            for n, line in enumerate(text.splitlines(), 1):
                if n in skip or n in fenced:      # 围栏归规则 A
                    continue
                tok = self._scan_line(line, things)
                if tok:
                    bad.append(f"{doc.relative_to(ROOT).as_posix()}:{n}  {tok[:60]}")
        self.assertEqual(
            sorted(set(bad)), [],
            "这些正文用了简写，而所在位置没有「简写→实际位置」的说明段覆盖 —— "
            "读者无从知道要补 users/<你>/：\n  " + "\n  ".join(sorted(set(bad))))


class TheActiveUserHasThoseFolders(unittest.TestCase):
    """控制用例：这个 clone 里的活动用户，六个目录得真的在。

    上面几条都是在验**说法**；这条验**现状**。说法对了而目录没建，用户照做仍然
    找不到地方放。
    """

    def test_they_exist_for_the_active_user(self):
        au = ROOT / ".active_user"
        if not au.is_file():
            self.skipTest("这个 clone 里还没有活动用户")
        base = ROOT / "users" / au.read_text(encoding="utf-8").strip() / "documents"
        if not base.is_dir():
            self.skipTest("活动用户还没有 documents/ —— /job-setup 还没跑过")
        missing = [d for d in SUBDIRS if not (base / d).is_dir()]
        self.assertEqual(
            missing, [],
            f"活动用户的 documents/ 下缺这些目录：{missing} —— "
            "文档说了放哪儿，那个地方却不存在")


class TheOutcomeArchiveHasOneName(unittest.TestCase):
    """投递归档里那份结果文件只许有一个名字：`job-outcome.md`。

    ## 它曾经有两个

    2026-08-21 实测：同一个文件在仓库里被写成两种拼法——

    | 写成 `job-outcome.md` | 写成 `outcome.md` |
    |---|---|
    | `job-outcome.md` ×6、`job-gmail-sync` ×11、`job-interview` ×3、`job-setup` ×2、`07-interview-prep` ×1 | `documents/README.md` 的布局树、`job-gmail-sync` 第 3 行、`job-html-report` 的读取步骤 |

    最能说明问题的两处：`job-gmail-sync.md` **同一份文件里两种都在用**；
    `job-outcome.md` 自己第 150 行写一种、第 219 行的输出模板写另一种。

    **没有任何代码碰这个文件**——写它的是照着工作流做的 AI，读它的也是。
    纯散文契约里出现两个名字，等于写的人和读的人永远碰不上头：
    `/job-outcome` 存下 `job-outcome.md`，`/job-html-report` 去找 `outcome.md`，
    **读到空，然后一声不吭地少一块内容**。

    今天没咬到人，只因为 285 个投递目录里两个名字都是 0 份
    （用户一直用面板按钮记状态，那条路只写台账 CSV——这是设计如此，
    `AGENTS.md` 写着「要写清楚经过仍然走 `/job-outcome`」）。
    第一次有人跑完 `/job-outcome` 再跑 `/job-html-report`，就会撞上。

    ## 为什么归到 `job-outcome.md` 而不是 `outcome.md`

    25:3 的现有惯例；写它的与多数读它的已经一致；而且 `tools/` 与 `tests/` 里
    「`outcome.md`」这个简称一直指**工作流本身**（`workflows/job-outcome.md`）——
    归档若也叫 `outcome.md`，那个简称当场变成歧义。
    """

    #: 只认**当成路径写**的那几种形状。散文里把工作流简称成「outcome.md」不算
    #: （`tools/followups.py` 与几份测试一直这么写，指的是那条命令的正文）。
    BAD = (
        "applications/*/outcome.md",
        "岗位>/outcome.md",
        "└── outcome.md",
        "/outcome.md",
    )

    def _shipped_docs(self):
        out = sorted(ROOT.joinpath("workflows").rglob("*.md"))
        out += [ROOT / "documents" / "README.md", ROOT / "AGENTS.md",
                ROOT / "CLAUDE.md", ROOT / "README.md"]
        return [p for p in out if p.is_file()]

    def test_no_doc_spells_it_the_other_way(self):
        bad = []
        for f in self._shipped_docs():
            for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
                if any(b in line for b in self.BAD):
                    bad.append(f"{f.relative_to(ROOT).as_posix()}:{i}")
        self.assertEqual(
            bad, [],
            "归档结果文件被写成了 `outcome.md`。全仓统一叫 `job-outcome.md` —— "
            "两个名字意味着写它的命令和读它的命令永远碰不上头，"
            "而且读到空是**无声**的：\n  " + "\n  ".join(bad))

    def test_the_layout_doc_still_lists_it(self):
        """`documents/README.md` 是归档结构的正本，它得真的列着这个文件。"""
        t = (ROOT / "documents" / "README.md").read_text(encoding="utf-8")
        self.assertIn("job-outcome.md", t,
                      "布局正本里没有这个文件了 —— 写它的命令没了落点")

    def test_the_writer_and_the_readers_agree(self):
        """写它的与读它的必须用同一个名字。"""
        writer = (ROOT / "workflows" / "job-outcome.md").read_text(encoding="utf-8")
        self.assertIn("job-outcome.md", writer, "写它的那条命令不提这个文件名了？")
        for reader in ("job-html-report.md", "job-gmail-sync.md", "job-setup.md"):
            f = ROOT / "workflows" / reader
            if not f.is_file():
                continue
            with self.subTest(reader=reader):
                self.assertIn("job-outcome.md", f.read_text(encoding="utf-8"),
                              f"{reader} 读的是另一个名字，会读到空")

    def test_the_detector_can_fire(self):
        """变异内建：写成另一种拼法必须被认出来。"""
        line = "2. **`documents/applications/*/outcome.md`** —— 读它的归档"
        self.assertTrue(any(b in line for b in self.BAD), "另一种拼法没被认出来")
        ok = "2. **`documents/applications/*/job-outcome.md`** —— 读它的归档"
        self.assertFalse(any(b in ok for b in self.BAD), f"正确写法被误报：{ok}")


if __name__ == "__main__":
    unittest.main()
