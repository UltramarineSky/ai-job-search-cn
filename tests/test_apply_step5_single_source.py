"""apply.md 第 5 步的排版口径必须单一来源：只在 5.0 决议表里解析一次。

「用哪个骨架 / 哪个引擎 / 几页 / 产出哪些文件」原本散在第 5 步的七处，口径互相矛盾
（有的按「已注册」、有的按「已激活」、有的把默认模板名和默认页数写死在指令里）。三轮
review 从这一处根因确认了 11 条缺陷：注册了自定义模板却仍按官方骨架排版、声明 1 页的
模板被 5d 的重编译循环填回 2 页、混合引擎下 LaTeX 引擎从不预检、落盘前的占位符闸门漏掉
`.tex` 产物、核对清单对着一个不存在的 `resume.typ` 报「已扫描通过」。

本测试按**位置**断言，不按全文计数：上一版用 `text.count(name) == 1` 与
`assertNotIn("注册了")`，前者把解析点整段挪出 5.0 也照样绿，后者封禁一个普通中文词组、
既误伤合理措辞又不真的验证判据。判据是否正确无法用字符串检测——能检测的是「解析点只有
一个，且在 5.0 里」，那才是这次重构真正建立的不变式。
"""

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
APPLY = REPO_ROOT / "workflows" / "job-apply.md"

# 决议表定义、下游只许引用的名字
DECISION_NAMES = ("简历骨架", "简历引擎", "简历页数上限",
                  "求职信骨架", "求职信引擎", "求职信页数上限",
                  "简历源扩展名", "求职信源扩展名", "本次产物")
# `<...源扩展名>` 这种占位式引用必须落在决议表定义过的两个名字上。只钉这一类：
# 早先用「以 骨架/引擎/页数上限/产物 结尾的反引号中文短语」做通用识别，既会因为行文里
# 一句 `默认骨架` 而误红，又漏掉 `简历模板` 这种换了后缀的真漂移——两头都不准。
_EXT_PLACEHOLDER = re.compile(r"<([一-鿿]*源扩展名)>")
# 页数字面量：阿拉伯数字与中文数字都要覆盖，否则把「恰好 2 页」改写成「恰好两页」
# 就能绕过整条检查，而那正是最自然的中文写法。
_PAGE_LITERAL = re.compile(r"[0-9一二两三四五六七八九十]+\s*页")
# 序数/方位用法不是页数预算：「翻到下一页」「第 3 页」都是合法行文，不该误红
_ORDINAL_PREFIX = "下上前后第"


def page_literals(body: str) -> list[str]:
    out = []
    for m in _PAGE_LITERAL.finditer(body):
        before = body[max(0, m.start() - 2):m.start()]
        if any(c in before for c in _ORDINAL_PREFIX):
            continue
        out.append(m.group(0))
    return out


class ApplyStep5SingleSourceTests(unittest.TestCase):
    def setUp(self):
        self.text = APPLY.read_text(encoding="utf-8")
        # 边界必须真的找到：切分标记一旦改名，`split` 会静默返回整篇剩余内容，
        # self.table 吞掉全文、self.rest 只剩引言，下面的不变式测试全部空转通过。
        self.assertIn("### 5.0 决议表", self.text, "5.0 决议表整节不见了")
        self.assertIn("### 5a.", self.text,
                      "找不到 `### 5a.` 边界——切分会失效并让本模块空转，先修标题")
        self.table = self.text.split("### 5.0 决议表")[1].split("### 5a.")[0]
        self.rest = self.text.replace(self.table, "")
        # 决议表应该是一小节，不该是全文：这条挡住「边界存在但顺序被调换」的情形
        self.assertLess(len(self.table), len(self.text) // 3,
                        "5.0 小节异常地大——切分边界可能已失效")
        # 第 5 步正文与核对清单是页数口径的作用域
        self.step5 = self.text.split("## 第 5 步")[1].split("## 第 6 步")[0]
        self.checklist = self.text.split("### 核对清单")[-1]

    def test_criterion_is_stated_in_the_table(self):
        self.assertIn("判据一律是**已激活**", self.table)

    def test_activation_files_resolved_only_inside_the_table(self):
        """两个激活文件名只许出现在 5.0 里。

        它们出现在别处 = 那里有第二个独立判断点，也就是下一次「改了一处漏一处」的落点。
        按位置断言而不是全文计数：整段挪出 5.0 时计数不变，位置断言才会红。
        """
        for name in ("templates/active-cv.md", "templates/active-cover-letter.md"):
            with self.subTest(name=name):
                self.assertIn(name, self.table, f"{name} 应在 5.0 决议表里解析")
                self.assertNotIn(name, self.rest,
                                 f"{name} 出现在 5.0 之外——那里有第二个判断点")
                # 位置断言看不见「重复项也落在 5.0 内」的情形——在决议表里再写一条
                # 基于「注册过」的备用解析同样是第二个判断点，所以计数也要钉住。
                self.assertEqual(self.text.count(name), 1,
                                 f"{name} 出现了不止一次：解析点必须唯一")

    def test_no_page_count_restated_in_step5_or_checklist(self):
        """页数字面量只许出现在决议表里，第 5 步其余部分与核对清单一律引用决议表的名字。

        作用域限定在第 5 步与核对清单：早先按「全文减去决议表」检查，别处一句
        「JD 超过 3 页时截断」就会以「应改为引用决议表的名字」失败，而那跟简历排版无关。
        """
        for label, body in (("第 5 步", self.step5.replace(self.table, "")),
                            ("核对清单", self.checklist)):
            with self.subTest(scope=label):
                found = page_literals(body)
                self.assertFalse(
                    found, f"{label} 里出现页数字面量 {found}，应改为引用决议表的名字")

    def test_every_decision_name_is_defined_and_referenced(self):
        """定义了却没人引用 = 死名字；被引用却没定义 = 下游得自己重新推导一遍。"""
        for name in DECISION_NAMES:
            with self.subTest(name=name):
                self.assertIn(name, self.table, f"`{name}` 未在 5.0 决议表里定义")
                self.assertIn(name, self.rest, f"`{name}` 定义了却从未被引用")

    def test_extension_placeholders_are_defined(self):
        """`<...源扩展名>` 占位只许用决议表定义过的那两个名字。

        这是实际发生过的漂移：决议表定义了 `源扩展名`（0 引用），下游却写
        `<简历源扩展名>`/`<求职信源扩展名>`（9 引用、0 定义），于是每处用到的地方都得
        自己从引擎重新推导一次——正是 5.0 要消除的第二解析点。
        """
        referenced = set(_EXT_PLACEHOLDER.findall(self.text))
        self.assertTrue(referenced, "没有任何 `<...源扩展名>` 占位——检查是否被改名了")
        unknown = referenced - {"简历源扩展名", "求职信源扩展名"}
        self.assertFalse(unknown, f"引用了 5.0 未定义的扩展名占位：{sorted(unknown)}")

    def test_leak_scan_is_not_keyed_to_typst_extensions(self):
        """落盘前的占位符闸门按决议表的产物清单枚举，不许按 typst 扩展名写死——
        写死会让 LaTeX 分支产出的 cover-letter.tex 整个绕过这道闸门，而模板骨架
        按设计就带着 [YOUR_NAME] 这类占位符。"""
        scan = self.text.split("### 落盘前成品扫描")[1].split("### 落盘")[0]
        self.assertIn("本次产物", scan)
        self.assertNotIn("cover-letter.typ", scan)

    def test_delivery_checklist_does_not_hardcode_typst_products(self):
        """核对清单是打印给用户看的自检项：写死 `resume.typ` 会让 LaTeX 分支对着一个
        本次根本不存在的文件报「已扫描通过」。"""
        checklist = self.text.split("### 核对清单")[-1]
        for literal in ("resume.typ", "cover-letter.typ"):
            with self.subTest(literal=literal):
                self.assertNotIn(literal, checklist)


class TheOverrideBlockDoesNotResurrectExactPageCount(unittest.TestCase):
    """`/job-add-template` 写的激活块，不许把「恰好 N 页」装回来。

    那个块自己声明：

    > Where this block conflicts with the stock guidance in `05-cv-templates.md`,
    > **this block wins**.

    而它的页数行原来写着 `Page limit: **exactly** <N> page(s)`——于是**凡是用了
    自定义模板的用户**，框架早就撤掉的「恰好」规则又被原样装了回去。

    撤它的理由写在 `05-cv-templates.md`：三个不同职业的独立审阅同时指出，
    对内容量本来只有半页到一页的人（应届生、蓝领技工、刚转行的），「恰好」
    **主动引导他违反本仓库的诚实底线**——要么编内容，要么删掉诚实标注的缺口。

    一个声明自己优先的块，最不该是旧规则的最后藏身处。
    """

    ADD_TEMPLATE = REPO_ROOT / "workflows" / "job-add-template.md"
    CV = REPO_ROOT / "workflows" / "reference" / "05-cv-templates.md"

    def test_the_framework_still_says_at_most(self):
        """控制用例：框架那条规则还在，否则本测试失去依据。"""
        self.assertIn(
            "不是「恰好」", self.CV.read_text(encoding="utf-8"),
            "05-cv-templates.md 里那句「校验按『不超过』上限判，不是『恰好』」"
            "不见了")

    def test_the_activation_block_is_found(self):
        """控制用例：真抽到了那个块。"""
        t = self.ADD_TEMPLATE.read_text(encoding="utf-8")
        self.assertIn("页数上限：", t, "add-template.md 里找不到激活块的页数行了")

    def test_no_exact_page_count_in_the_override(self):
        bad = []
        for i, line in enumerate(
                self.ADD_TEMPLATE.read_text(encoding="utf-8").splitlines(), 1):
            if "原来写的是" in line or "旧规则" in line:
                continue          # 讲这条规则本身的说明，要引用反例
            if "页数上限" not in line:
                continue
            # ⚠️ 判据是「主张恰好」，不是「出现了这个词」。
            #
            # 第一版写成「行里有 exactly 或 恰好 就算违规」——当场撞上**改对之后的
            # 那一行**：它写的正是「判的是上限，**不是「恰好」**」。断言撞上解释
            # 自己的文字，这个仓库里反复出现（本轮第三次），解法一律是：
            # **同一行里有错的说法、且没有对的说法**才算违规。
            says_exact = "exactly" in line.lower() or "恰好" in line
            says_cap = "不超过" in line or "不是「恰好」" in line or "at most" in line.lower()
            if says_exact and not says_cap:
                bad.append(f"add-template.md:{i}  {line.strip()[:70]}")
        self.assertEqual(
            bad, [],
            "激活块又把「恰好 N 页」写回来了：" + chr(10) + "  " + (chr(10) + "  ").join(bad)
            + chr(10) + "这个块声明自己优先于框架指引——写「恰好」，等于对每个用了"
            + chr(10) + "自定义模板的用户恢复那条已被撤掉的规则。判的是**上限**。")


class Step5bWritesWhatStep5cCompiles(unittest.TestCase):
    """5b 落盘的文件名，必须就是 5c 拿去编译的那个。

    2026-08-21 通读时抓到：5b 写的是
    `documents/applications/<公司>_<岗位>/**job-resume**.<简历源扩展名>`，
    而 5c 编译的是 `.../resume.typ` → `.../resume.pdf`。

    **照着做，5c 的输入根本不存在** —— 而且 `job-resume.` 这个写法全仓
    只出现那一次（落盘表、`/job-cv`、导出器 `export_web_data.py` 找的
    统统是 `resume.pdf`）。孤例是最好的信号：一处与其余全部不一致时，
    多半是那一处错。

    判据不比措辞，比**两步里出现的文件名**。
    """

    APPLY = REPO_ROOT / "workflows" / "job-apply.md"

    def _step(self, name: str, nxt: str) -> str:
        t = self.APPLY.read_text(encoding="utf-8")
        i = t.index(name)
        return t[i:t.index(nxt, i)]

    def test_the_stem_is_the_same_in_both_steps(self):
        import re

        write = self._step("### 5b.", "### 5c.")
        build = self._step("### 5c.", "### 5d.")
        stems_w = set(re.findall(r"applications/<公司>_<岗位>/([A-Za-z-]+)\.", write))
        stems_b = set(re.findall(r"applications/<公司>_<岗位>/([A-Za-z-]+)\.", build))
        self.assertTrue(stems_w, "5b 里找不到落盘文件名了")
        self.assertTrue(stems_b, "5c 里找不到编译文件名了")
        self.assertIn(
            "resume", stems_w,
            f"5b 落盘的简历文件名不是 `resume.*`：{sorted(stems_w)}")
        # **只比简历那一个名字**。5b 里还会出现 `photo.jpg`（从基简历拷过去的
        # 照片，不参与编译）、`cover-letter.*`（5g 自己编译）—— 第一版拿集合差
        # 去比，当场把 `photo` 报成「5c 的输入不存在」。
        self.assertIn(
            "resume", stems_b,
            f"5c 编译的不是 `resume.*` 了：{sorted(stems_b)}")
        self.assertNotIn(
            "job-resume", stems_w,
            "5b 又把定制版写成 `job-resume.*` 了 —— 5c 编译的是 `resume.typ`，"
            "照着做那一步的输入根本不存在（落盘表、/job-cv、导出器一律用 `resume.pdf`）")


if __name__ == "__main__":
    unittest.main()
