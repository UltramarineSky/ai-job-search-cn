"""outreach.md 的两种合法写法都必须解析得出来。

## 这个测试为什么存在

`apply.md` 既写「## 打招呼开场白（≤200 字…）」也写「### 渠道 4：求职信」——**「渠道 N：」
这个前缀是它自己规定的格式**，所以 AI 产出两种标题都合法。而 `_section()` 原来要求
关键词紧跟在 `## ` 之后，于是带「渠道 1：」前缀的那份文件整体解析为空：面板上
「三渠道话术」点开是空的，邮件按钮没有内容，导出给 web 的开场白也是空字符串。

实测发现：4 个真实投递目录里 3 个能解析（223/221/200 字），第 4 个全部为 0 ——
而它恰好是分最高、材料最全的那个岗。

主题行同理有两种写法：`**主题**：xxx`（冒号在加粗外）和 `**主题：** xxx`（冒号在加粗内）。
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import build_dashboard as bd  # noqa: E402

# 写法 A：关键词紧跟 ##，主题冒号在加粗外
STYLE_A = """# 投递话术 — 某岗 @ 某公司

- 职位链接：https://www.liepin.com/job/1.shtml

## 打招呼开场白（≤200 字，猎聘/BOSS 聊天框）

您好，看到贵司在招这个岗位，我的方向与它一致。

## 邮件

**主题**：应聘 某岗 - 张三

您好，附上简历。

## 网申自评（纯文本）

自评内容甲。
"""

# 写法 B：标题带「渠道 N：」前缀，主题冒号在加粗内
STYLE_B = """# 投递话术 — 某岗 @ 某公司

- 职位链接：https://www.zhaopin.com/jobdetail/CC1.htm?refcode=4089

## 渠道 1：打招呼开场白（智联「立即沟通」聊天框）

您好，看到贵司在招这个岗位，我的方向与它一致。

## 渠道 2：邮件正文

**主题：** 应聘 某岗 - 张三

**正文：**

您好，附上简历。

## 渠道 3：网申自评 / 求职动机

自评内容甲。
"""


class BothHeadingStylesParse(unittest.TestCase):
    def test_style_a(self):
        r = bd.parse_outreach(STYLE_A)
        self.assertIn("看到贵司在招", r["greeting"])
        self.assertIn("应聘 某岗", r["email_subject"])
        self.assertIn("附上简历", r["email_body"])
        self.assertIn("自评内容甲", r["wangshen"])
        self.assertEqual(r["url"], "https://www.liepin.com/job/1.shtml")

    def test_style_b_with_channel_number_prefix(self):
        """「渠道 N：」前缀是 apply.md 自己规定的格式，不能解析成空。"""
        r = bd.parse_outreach(STYLE_B)
        self.assertIn("看到贵司在招", r["greeting"],
                      "带「渠道 1：」前缀的开场白解析成空 → 面板上话术是空的")
        self.assertIn("自评内容甲", r["wangshen"])
        self.assertEqual(r["url"],
                         "https://www.zhaopin.com/jobdetail/CC1.htm?refcode=4089")

    def test_style_b_subject_colon_inside_bold(self):
        """`**主题：** xxx` 与 `**主题**：xxx` 都要认。"""
        r = bd.parse_outreach(STYLE_B)
        self.assertIn("应聘 某岗", r["email_subject"],
                      "冒号在加粗内时主题解析失败 → 邮件没有主题")
        self.assertNotIn("主题", r["email_body"],
                         "主题行不该又出现在正文里")

    def test_email_body_present_in_style_b(self):
        r = bd.parse_outreach(STYLE_B)
        self.assertIn("附上简历", r["email_body"])

    def test_greeting_not_polluted_by_next_section(self):
        """开场白不能把下一节的内容吞进来。"""
        for style in (STYLE_A, STYLE_B):
            g = bd.parse_outreach(style)["greeting"]
            self.assertNotIn("附上简历", g)
            self.assertNotIn("自评内容甲", g)


class GreetingIsSendableAsIs(unittest.TestCase):
    """开场白是**要直接粘进聊天框发出去**的文本，不能混进任何元数据。

    真实产出里出现过两种尾巴：
      - `（字数：199）`          —— 老的字数标注
      - `> 字数校验：**192 字**（去空白字符计），≤200 ✓；第一句即为最硬匹配点 ✓`
        后面还跟一条 `---`
    第二种 `_strip_wordcount` 抓不到，于是面板和 web 页都把自检备注当成正文显示 ——
    用户一键复制粘贴，就把「字数校验…✓✓✓」一起发给 HR 了。
    """

    BODY = "您好，看到贵司在招这个岗位，我的方向与它一致。"

    def _greeting(self, tail):
        doc = (
            "## 打招呼开场白（≤200 字）\n\n"
            + self.BODY + "\n\n"
            + tail
            + "\n## 邮件\n\n**主题**：应聘\n\n正文。\n"
        )
        return bd.parse_outreach(doc)["greeting"]

    def test_paren_wordcount_stripped(self):
        g = self._greeting("（字数：199）\n")
        self.assertNotIn("字数", g)
        self.assertTrue(g.endswith("一致。"), g)

    def test_blockquote_selfcheck_stripped(self):
        """`> 字数校验：…✓` 这种自检行必须剥掉——它不是要发出去的内容。"""
        g = self._greeting("> 字数校验：**192 字**（去空白字符计），≤200 ✓；含真问题 ✓\n")
        self.assertNotIn("字数校验", g)
        self.assertNotIn("✓", g)
        self.assertTrue(g.endswith("一致。"), g)

    def test_trailing_rule_stripped(self):
        g = self._greeting("> 字数校验：**192 字**，≤200 ✓\n\n---\n")
        self.assertNotIn("字数校验", g)
        self.assertFalse(g.rstrip().endswith("-"), f"尾部留了分隔线：{g!r}")

    def test_body_is_untouched(self):
        """正文里的内容一个字都不能少。"""
        g = self._greeting("（字数：199）\n")
        self.assertIn(self.BODY, g)

    def test_real_greetings_carry_no_metadata(self):
        """控制测试：仓库里若有真实投递目录，它们的开场白也不许带元数据。"""
        root = Path(__file__).resolve().parent.parent
        files = sorted(root.glob("users/*/documents/applications/*/outreach.md"))
        if not files:
            self.skipTest("这个 clone 里没有真实投递目录")
        bad = []
        for f in files:
            g = bd.parse_outreach(f.read_text(encoding="utf-8", errors="replace"))["greeting"]
            if "字数" in g or g.rstrip().endswith(("---", "***")):
                bad.append(f.parent.name)
        self.assertFalse(bad, f"这些开场白里混了元数据，复制粘贴会一起发出去：{bad}")


class RealFilesAllParse(unittest.TestCase):
    """兜底：仓库里若存在真实投递目录，每一个都必须解析出非空开场白。

    这条是控制测试——没有真实数据时自动跳过，不会在别人的 clone 上失败。
    """

    def test_every_real_outreach_yields_a_greeting(self):
        root = Path(__file__).resolve().parent.parent
        files = sorted(root.glob("users/*/documents/applications/*/outreach.md"))
        if not files:
            self.skipTest("这个 clone 里没有真实投递目录")
        empty = []
        for f in files:
            r = bd.parse_outreach(f.read_text(encoding="utf-8", errors="replace"))
            if not r["greeting"].strip():
                empty.append(f.parent.name)
        self.assertFalse(empty, f"这些投递目录的开场白解析成空：{empty}")


if __name__ == "__main__":
    unittest.main()
