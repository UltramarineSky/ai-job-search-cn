"""`/job-gmail-sync` 的匹配规则必须认得中文邮件——它是给国内求职者用的。

## 两处匹配规则原来只认英文

这条命令的全部价值在于**认出邮件说了什么**。可它的两张匹配表原来都只有英文：

| 在哪 | 原来写的 | 后果 |
|---|---|---|
| 发件域名 OR 组 | `greenhouse.io` `lever.co` `myworkday.com` `ashbyhq.com` `smartrecruiters.com` `icims.com` `bamboohr.com` | **一个国内平台都没有**。这组域名存在的理由正是兜住「邮件由平台发出、正文不带公司名」的情况——猎聘/BOSS/智联/前程的通知只能靠公司名那组碰运气 |
| 信号短语表 | `"moving forward with other candidates"` `"schedule a call"` `"pleased to offer"` …… | **一封中文拒信永远匹配不上**。那条投递会一直显示成「还开着」，`followups.py` 接着催，`/job-html-report` 的拒绝率一直失真 |

中文拒信尤其难认：往往整封两三句，不带「拒绝」二字，标志词是
**「很遗憾」「暂不合适」「未能进入下一轮」「另作安排」**。

这与 `(BR, MX, GT)`、`Jens Jensen`、`Coursera/edX/Udemy` 是同一类——**上游仓库的
本地化残留**，只是这一处不是措辞问题，是**功能失效**。

## 判据

- 发件域名组里要有本仓库自己接入的那几个平台（猎聘在 CLI 源码里，另三家在
  `add-portal.md` / `cdp-portals.md`——控制用例扫这两处，不看 gmail-sync 自己）。
- 信号短语表里要有中文拒信的标志词——那是最容易漏、代价也最大的一类。
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOC = ROOT / "workflows" / "job-gmail-sync.md"

#: 本仓库已接入的招聘平台域名。
#:
#: ⚠️ 控制用例要**去别处**核这几个域名真的在用，而且不能只看一个文件：
#: 第一版只查 `search-queries.md`，当场红——猎聘走的是 CLI 不是 `site:` 兜底，
#: 它的域名在 `.agents/skills/liepin-search/cli/` 的源码里；另三家在
#: `add-portal.md` 与 `cdp-portals.md`。**也必须排除 `gmail-sync.md` 自己**，
#: 否则「它写了所以它对」是循环论证。
PORTAL_DOMAINS = ("liepin.com", "zhipin.com", "zhaopin.com", "51job.com")

#: 中文拒信的标志词。只要求命中其中几个，不要求全对——措辞可以调，
#: 但「一个中文拒信标志词都没有」一定是漏了。
REJECTION_ZH = ("很遗憾", "暂不合适", "未能进入下一轮", "另作安排")

#: 中文约面的标志词。
INTERVIEW_ZH = ("面试邀请", "面试通知", "初试", "复试", "终面")


class ItRecognisesChineseMail(unittest.TestCase):

    def setUp(self):
        self.text = DOC.read_text(encoding="utf-8")

    def test_the_portal_domains_are_the_ones_we_actually_search(self):
        """控制用例：这几个域名确实是仓库在用的，否则本测试拦的是我编的清单。

        扫 `workflows/` 与 `.agents/`，**排除 gmail-sync.md 自己**——
        「它写了所以它对」不成立。
        """
        blob = ""
        for base, pat in ((ROOT / "workflows", "**/*.md"),
                          (ROOT / ".agents", "**/*.ts")):
            for f in base.glob(pat):
                if f.name == "job-gmail-sync.md":
                    continue
                blob += f.read_text(encoding="utf-8", errors="replace")
        for d in PORTAL_DOMAINS:
            with self.subTest(domain=d):
                self.assertIn(
                    d, blob,
                    f"`{d}` 在 gmail-sync.md 之外找不到了——这个平台还接着吗？"
                    "平台清单变了就把 PORTAL_DOMAINS 一起改。")

    def test_sender_group_includes_domestic_portals(self):
        missing = [d for d in PORTAL_DOMAINS if f"from:{d}" not in self.text]
        self.assertEqual(
            missing, [],
            f"发件域名 OR 组里缺这几个国内平台：{missing}"
            "\n这组的作用是兜住「邮件由平台发出、正文不带公司名」的情况；"
            "\n只列海外 ATS，等于国内用户完全没有这层兜底。")

    def test_rejection_phrases_cover_chinese(self):
        hit = [w for w in REJECTION_ZH if w in self.text]
        self.assertGreaterEqual(
            len(hit), 2,
            f"拒信的中文标志词只命中 {hit}（在 {list(REJECTION_ZH)} 里找）。"
            "\n中文拒信往往整封两三句、不带「拒绝」二字——只按英文匹配，"
            "\n国内投递的拒信一封都认不出来，那条投递会永远显示成「还开着」。")

    def test_interview_phrases_cover_chinese(self):
        hit = [w for w in INTERVIEW_ZH if w in self.text]
        self.assertGreaterEqual(
            len(hit), 2,
            f"约面的中文标志词只命中 {hit}（在 {list(INTERVIEW_ZH)} 里找）")

    def test_the_classification_table_is_still_there(self):
        """控制用例：那张表还在，否则上面几条对着空气跑。"""
        self.assertRegex(
            self.text, r"\|\s*信号\s*\|.*\|\s*台账 `status`",
            "gmail-sync.md 里找不到信号分类表了——判据可能失效了")


class TheLabelHelpsFindMailInsteadOfExcludingIt(unittest.TestCase):
    """求职标签是**信号**，不是**约束**。

    Gmail 搜索式里**空格就是 AND**。Step 3 原来把「找到了求职标签的话，
    加上 `label:<id>`」和回溯边界、`in:inbox` 并排列在同一张单子里 ——
    照字面拼出来它就是 AND，**整轮结果被限死在那个标签内**，
    底下辛苦列的公司名组和发件域名组一条都用不上。

    而标签在真实邮箱里几乎都是**过滤器打上去的、只覆盖一部分发件人**：
    于是有标签的用户反而比没标签的漏得更多 —— 没标签的至少还走另外两组。

    这和同一步里域名那条记着的是同一种病（「只列海外的，等于国内用户完全
    没有这层兜底」）：**一个本意是「帮你找到」的东西，摆错位置就成了
    「替你排除」。** 底下那个例子一直是对的（信号用显式 `OR` 连、
    `newer_than` 与 `in:inbox` 才是 AND）—— **例子对、规则错，
    而执行者读的是规则。** 2026-09-02 通读时发现。
    """

    def setUp(self):
        self.text = DOC.read_text(encoding="utf-8")
        i = self.text.index("## Step 3")
        self.step3 = self.text[i:self.text.index("## Step 4", i)]

    def _body(self):
        """只看规则正文，不看讲经过的引用块 —— 我为这次修补写的说明里
        就点了「标签是信号」，算进去的话删掉规则那行照样绿。"""
        return "\n".join(l for l in self.step3.splitlines()
                         if not l.lstrip().startswith(">"))

    def test_the_query_separates_constraints_from_signals(self):
        b = self._body()
        self.assertIn("空格就是 AND", b, "没说清 Gmail 里空格的含义")
        for word in ("约束", "信号"):
            with self.subTest(word=word):
                self.assertIn(word, b, f"没把「{word}」这一类说出来")

    def _line_with(self, needle: str) -> str:
        """含某个串的**那一行**（不含 `>` 引用）。

        **不能取「附近 N 个字符」** —— 变异当场照出来：`OR` 在下一行的
        公司名组里本来就有，于是「附近有 OR」在旧写法上照样成立，这条
        断言整个是瞎的。第 8、14 轮各栽过一次同样的形状。
        """
        for l in self._body().splitlines():
            if needle in l:
                return l
        return ""

    def test_the_label_goes_into_the_or_group(self):
        line = self._line_with("label:<id>")
        self.assertTrue(line, "找不到写 `label:<id>` 的那一行")
        self.assertIn(
            "OR", line,
            f"`label:<id>` 那一行没说它是 OR 组里的一项，照字面拼就是 AND，"
            f"整轮结果被限死在那个标签内：{line.strip()!r}")

    def test_the_label_keywords_cover_chinese(self):
        """这份文档的用户是中文求职者，他的标签八成是中文的。

        原来只列了 `job` / `application` / `career`，中文那半只写一句
        「同理」—— 而同一步的域名那条早就吃过「只列海外的」的亏。
        """
        line = self._line_with("list_labels")
        self.assertTrue(line, "找不到调 `list_labels` 的那一行")
        hit = [w for w in ("求职", "投递", "面试", "招聘") if w in line]
        self.assertGreaterEqual(
            len(hit), 2,
            f"找标签那一行只认英文词（中文只命中 {hit}）—— "
            f"中文邮箱里的标签会整个找不到：{line.strip()[:80]!r}")


if __name__ == "__main__":
    unittest.main()
