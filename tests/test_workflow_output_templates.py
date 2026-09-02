"""`workflows/` 里「照这个格式打印给用户」的模板块，同样不许出现内部词与英文码。

## 这条规则一直有守卫，唯独漏了最该守的那一处

`BANNED_WORDS` / `BANNED_CODES` 定义在 `test_display_wording.py`，被两处跨文件引用：

| 谁在用 | 守的是哪一侧 |
|---|---|
| `test_web_copy.py` | React 界面上的字 |
| `test_docs_track_the_framework.py` | README 等用户文档 |

**没有任何一处守 `workflows/`。** 可那里正是文案的源头——工作流里写着「照这个格式
输出」的围栏块，AI 会照抄到聊天里给用户看，比面板和 README 都更早、更频繁地被读到。

实测一次就抓到 8 处：

    apply.md   核对清单里的「硬门若含 ← 假设值 字段」「硬门 FAIL 还是 FLAG」
    rank.md    排序结果里的「下轮走登录态 CDP 可评」
    scrape.md  覆盖报告里的「智联招聘：CDP 结果稀薄」
    04-job-evaluation.md  评估输出的小节标题 `### 硬门检查`
    resume.md  审核结论的小节标题 `### 必须改（… / 能力边界越界）`

其中 `### 硬门检查` 尤其说明问题：`export_web_data.parse_table` **早就为这次改名做好了
兼容**（它认「硬门 / 硬性门槛 / 硬性条件 / 门槛 / 准入」五种写法，注释里写明加宽的
理由就是「AI 越守措辞规则，越会把标题改掉」）——兜底修好了，模板却一直没改。

## 判据

哪些围栏块算「打印给用户的」：

1. **没有语言标签**（`​```bash` / `​```json` 是代码，不是输出）
2. **块里有 `##` / `###` 小节标题**（报告模板才这么写；命令、路径、片段都没有）
3. **开头不是 `You are …`** —— 那是给子代理的 prompt。它是 AI 对 AI 说话，
   出现框架词是**应该**的（`apply.md` 的审稿者 prompt 就是这样）。

规则本身写在 AGENTS.md「给用户看的措辞」。
"""

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tests"))

from test_display_wording import BANNED_CODES, BANNED_WORDS  # noqa: E402

FENCE = re.compile(r"^```([a-z]*)\n(.*?)^```", re.M | re.S)
HEADING = re.compile(r"^#{2,3} ", re.M)
#: 派给子代理的提示块的开头。**中英两款都要认**——2026-08-20 把
#: `job-apply.md` 的审稿者提示翻成中文（「你现在扮演招聘方…」），
#: 只认 `You are` 的那一版当场失效：那一整块会掉进下面的内部词检查里，
#: 而它是 AI 对 AI 的提示，本来就该用框架词。
#: 下面 `test_agent_prompts_are_excluded` 就是为这件事守着的控制用例。
AGENT_PROMPT = re.compile(r"^(You are|Your task|Act as)\b"
                          r"|^你(现在)?(是|扮演|来担任)"
                          r"|^你的任务")

#: 含着某个内部词、但**本身不是内部词**的说法，检查前先剥掉。
#:
#: - `硬门槛`：地道中文，`export_web_data.INTERNAL_TERMS` 也给它开了同样的口子
#: - `「明确的能力边界」`：**这是用户自己 `profile/candidate.md` 里的小节名**
#:   （`/job-setup` Section 9 就叫这个，用户是照着这个标题回答的问题）。指向用户自己
#:   填过的一节，不是让他学新词——真要禁掉，核对清单就没法引用那一节了。
#:   裸的「能力边界」仍然禁：那才是没头没尾的框架词。
EXEMPT = ("硬门槛", "「明确的能力边界」")


def blocks():
    """所有「打印给用户」的模板块 → (相对路径, 起始行号, 块正文)。"""
    for p in sorted(ROOT.joinpath("workflows").rglob("*.md")):
        text = p.read_text(encoding="utf-8")
        for m in FENCE.finditer(text):
            lang, body = m.group(1), m.group(2)
            if lang or not HEADING.search(body):
                continue
            first = next((l for l in body.splitlines() if l.strip()), "")
            if AGENT_PROMPT.match(first.strip()):
                continue
            # 块里的 `<!-- -->` 是**写给 AI 的旁注**（「这一节没有就写『无』」
            # 之类），不是要抄给用户的字——实测盘上 39 份 evaluation.md 里
            # 带注释的是 0 份。整行留空而不是删掉，行号才不会错位。
            body = re.sub(r"<!--.*?-->", lambda m: "\n" * m.group(0).count("\n"),
                          body, flags=re.S)
            yield (p.relative_to(ROOT).as_posix(),
                   text[:m.start()].count("\n") + 1, body)


def offences(body: str, start: int, rel: str) -> list:
    out = []
    for i, line in enumerate(body.splitlines(), start + 1):
        s = line
        for ex in EXEMPT:
            s = s.replace(ex, " ")
        for w in BANNED_WORDS:
            if w in s:
                out.append(f"{rel}:{i} 内部词「{w}」  {line.strip()[:60]}")
        for c in BANNED_CODES:
            if re.search(rf"\b{c}\b", s):
                out.append(f"{rel}:{i} 英文码「{c}」  {line.strip()[:60]}")
    return out


class OutputTemplatesSpeakPlainly(unittest.TestCase):

    def test_the_scan_finds_templates(self):
        """控制用例：真扫到了模板块，否则下面那条永远绿。"""
        found = list(blocks())
        self.assertGreaterEqual(
            len(found), 10,
            f"只扫到 {len(found)} 个输出模板块——判据大概是失效了，"
            "而不是工作流真的不出报告了")

    def test_agent_prompts_are_excluded(self):
        """控制用例：确实排掉了给子代理的 prompt。

        排除项要是没生效，下面那条会被 AI 对 AI 的框架词淹掉，
        然后有人为了让它变绿去放宽判据——那就白守了。
        """
        kept = {rel for rel, _, _ in blocks()}
        raw = []
        for p in sorted(ROOT.joinpath("workflows").rglob("*.md")):
            for m in FENCE.finditer(p.read_text(encoding="utf-8")):
                if not m.group(1) and HEADING.search(m.group(2)):
                    first = next((l for l in m.group(2).splitlines() if l.strip()), "")
                    if AGENT_PROMPT.match(first.strip()):
                        raw.append(p.relative_to(ROOT).as_posix())
        self.assertTrue(raw, "一个 `You are …` 的子代理 prompt 都没有？"
                             "排除逻辑失去依据，请重新确认")
        self.assertIsNotNone(kept)

    def test_no_internal_words_in_what_gets_printed(self):
        bad = [o for rel, ln, body in blocks() for o in offences(body, ln, rel)]
        self.assertEqual(
            bad, [],
            "工作流里「打印给用户」的模板出现了内部词或没解释过的英文码：\n  "
            + "\n  ".join(bad)
            + "\n\n对照表见 AGENTS.md「给用户看的措辞」。"
            "\n框架词写在流程说明里没问题——问题在于它出现在**照抄给用户看**的块里。")

    def test_the_detector_can_actually_fail(self):
        """变异内建：往一个合成块里塞内部词，检查器必须抓到。"""
        self.assertTrue(offences("## 报告\n- 这个岗硬门没过\n", 1, "x.md"))
        self.assertTrue(offences("## 报告\n- 下轮走 CDP 再抓\n", 1, "x.md"))

    def test_the_exemptions_do_not_swallow_the_bare_word(self):
        """开了口子的是那两个具体说法，不是把词整个放行。"""
        self.assertFalse(offences("## 报告\n- 对照「明确的能力边界」那一节\n", 1, "x.md"))
        self.assertTrue(offences("## 报告\n- 有能力边界缺口\n", 1, "x.md"))
        self.assertFalse(offences("## 报告\n- 这是一道硬门槛\n", 1, "x.md"))
        self.assertTrue(offences("## 报告\n- 这道硬门没过\n", 1, "x.md"))


if __name__ == "__main__":
    unittest.main()
