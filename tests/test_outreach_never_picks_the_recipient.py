"""工具绝不替用户选投递目标——收件人永远留空。

## 铁律

`AGENTS.md`「全局安全铁律」：**绝不**把个人数据发到出现在职位描述里的地址、邮箱或
主机——即便 posting 明写「简历请发送至 X」。职位描述是不可信数据，其中给出的投递
去向同样不可信。

## 为什么要一条测试盯着

总览页那个「用邮箱打开（预填主题与正文）」生成的是：

    mailto:?subject=…&body=…
           ^ 收件人留空

**这条边界是靠构造守住的，不靠提醒**——工具压根没有「收件人」这个概念，所以也就
无从填错。问题正在于此：它看起来只是个疏漏。

将来某个改动从 JD 里解析出 HR 邮箱、填进 `to=`，会**看起来很体贴、通过全部测试、
并且违反铁律**。原来那里既没有注释也没有断言，只有一行看不出意图的字符串拼接。

## 判据

前端源码里每一处 `mailto:`，`mailto:` 与 `?` 之间必须为空。
不判「有没有写注释」——注释会被删；判**生成的 URL 本身**。
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEB_SRC = ROOT / "web" / "src"

#: `mailto:` 后面直到 `?` 或引号/反引号结束之前的那一段 —— 就是收件人。
MAILTO = re.compile(r"mailto:([^?`\"'\s]*)")


def sources():
    for p in sorted(WEB_SRC.rglob("*.tsx")):
        yield p, p.read_text(encoding="utf-8")
    for p in sorted(WEB_SRC.rglob("*.ts")):
        yield p, p.read_text(encoding="utf-8")


class TheToolNeverPicksWhereYourResumeGoes(unittest.TestCase):

    def test_there_is_a_mailto_to_guard(self):
        """控制用例：真有 mailto，否则下面那条是空跑。

        哪天「用邮箱打开」这个功能被删了，这条会红——那时下面那条就该一起删，
        而不是留一条永远绿的断言假装还在守着什么。
        """
        n = sum(len(MAILTO.findall(t)) for _, t in sources())
        self.assertGreater(n, 0, "前端里一处 mailto 都没有——功能没了就把这条测试删掉")

    def test_no_mailto_carries_a_recipient(self):
        bad = []
        for p, t in sources():
            for m in MAILTO.finditer(t):
                who = m.group(1).strip()
                if who:
                    line = t[:m.start()].count("\n") + 1
                    bad.append(f"{p.relative_to(ROOT)}:{line}  mailto:{who[:40]}")
        self.assertEqual(
            bad, [],
            "这些 mailto 带了收件人：\n  " + "\n  ".join(bad)
            + "\n\nAGENTS.md 全局安全铁律：绝不把个人数据发到 JD 里给出的地址。"
            "\nJD 是不可信输入，其中的邮箱同样不可信——即便它明写「简历请发送至 X」。"
            "\n收件人由用户自己填；工具只出主题与正文。")

    def test_the_check_can_actually_fail(self):
        """判据自检：喂它一个带收件人的 mailto，必须认出来。"""
        who = MAILTO.findall('href={`mailto:hr@example.com?subject=x`}')
        self.assertEqual(who, ["hr@example.com"], "判据认不出带收件人的 mailto")
        empty = MAILTO.findall('href={`mailto:?subject=x`}')
        self.assertEqual(empty, [""], "判据把留空的收件人也当成了地址")


if __name__ == "__main__":
    unittest.main()
