# -*- coding: utf-8 -*-
"""接一个新招聘网站时，先判它落在取数顺位的第几层。

顺位的正本在 `AGENTS.md`「取数渠道的顺位」：

    1  平台自己的公开 API（免登录，最好）
    2  浏览器扩展（要登录态、或平台挂了反爬时的首选）
    3  web-access skill 的 CDP 代理
    4  `site:` 域名限定搜索兜底

`/job-add-portal` 脚手架出的是**第 1 层**。而它原来对两种情况的处置和顺位对不上：

- **要登录才看得到列表** → 原话「**到此为止**……建议看看该平台有没有官方 API」。
  可第 2 层正是为这种情况准备的，**BOSS 直聘、智联招聘、前程无忧现在就是这么抓的**。
  说「到此为止」会让用户以为没辙，而仓库里恰好有现成的路。
- **撞反爬 / WAF 挑战页** → 原来一个字都没有。而 `AGENTS.md` 对这一条的态度很硬：
  「绕过 WAF 或反爬挑战不做，直接进第 2 层」。为了凑「有 API」去破解反爬，
  换来的是封号和一条随时会碎的链路。
"""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADD = (ROOT / "workflows" / "job-add-portal.md").read_text(encoding="utf-8")
AG = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
RM = (ROOT / "README.md").read_text(encoding="utf-8")


class ItAsksWhichLayerFirst(unittest.TestCase):
    def test_the_step_names_the_ordering(self):
        self.assertIn("取数顺位", ADD, "侦察那一步没说它在判第几层")
        self.assertIn("AGENTS.md", ADD, "没指向顺位的正本")

    def test_it_says_which_layer_it_scaffolds(self):
        """不说清自己是第 1 层，就没法解释「够不着时落到哪」。"""
        self.assertRegex(ADD, r"脚手架出的是\*\*第 1 层\*\*|本命令脚手架出的是",
                         "没说清这条命令产出的是哪一层")


class LoginWallIsNotADeadEnd(unittest.TestCase):
    def test_it_points_at_the_browser_layer(self):
        self.assertRegex(ADD, r"这不是死路|不是「这个平台接不了」",
                         "要登录时还在说「到此为止」")
        self.assertIn("浏览器扩展", ADD, "没指出第 2 层是干这个的")

    def test_it_names_the_sites_already_done_that_way(self):
        """空口说「有别的路」不如指出三家现成的 —— 那是这条建议可执行的证据。"""
        for site in ("BOSS", "智联", "前程"):
            with self.subTest(site=site):
                self.assertIn(site, ADD, f"没举出 {site} 这个现成例子")

    def test_no_section_still_says_reject_login_walled_sites(self):
        """**改了步骤，别把总纲那句留着。**

        2026-09-01 实测：Step 2 的表、Step 5 的浏览器支、Step 6 的收尾话术
        全都按「要登录 → 第 2 层」改好了，而文件末尾「设计原则」里仍写着
        「需要登录的平台**直接拒绝**」—— 同一条访问策略在一份文件里说了两遍，
        两遍相反。

        位置还偏偏是最坏的那一处：这一段是执行者最后读到、最容易当成总纲的
        （同一段此前也藏过一条 Bun 的冲突，`test_docs_do_not_make_bun_mandatory`
        为此而立）。照它执行，等于把仓库里**已经在用的三家渠道**判成不该存在，
        并且撞上 `AGENTS.md`「浏览器不设任何自定的闸门」那条裁定 ——
        「要登录」正是那条裁定明说不该拿来关掉渠道的理由。

        禁的从来不是登录，是**绕过反爬**（`AntiBotChallengesAreNeverBypassed`
        钉的就是那一条）。
        """
        for bad in ("需要登录的平台直接拒绝", "要登录的平台直接拒绝"):
            with self.subTest(phrase=bad):
                body = "\n".join(l for l in ADD.splitlines()
                                 if not l.lstrip().startswith(">"))
                self.assertNotIn(
                    bad, body,
                    "「设计原则」又把要登录的平台判成拒绝了 —— "
                    "和 Step 2 / Step 5 / Step 6 三处相反")

    def test_the_design_principles_ban_the_right_thing(self):
        """总纲那条要禁到点子上：不为了凑第 1 层去破解反爬。"""
        i = ADD.index("## 设计原则")
        seg = ADD[i:]
        self.assertRegex(seg, r"不为了凑第 1 层去破解反爬|不为了凑.{0,6}去破解反爬",
                         "设计原则没说清真正禁的是什么")
        self.assertRegex(seg, r"落到第 2 层|第 2 层去",
                         "没说撞反爬之后该去哪一层")


class TheReadmeSaysTheSameThing(unittest.TestCase):
    """README 是入口，它那句话决定用户会不会去试。

    平台表最后一行原来写「**若该站有公开接口**，用 `/job-add-portal` 接进来」——
    暗示没接口就扩展不了。而**同一张表上面三行**（BOSS / 智联 / 前程）
    恰恰是没接口、走浏览器接进来的。README 自己就是那句话的反例。
    """

    def test_it_does_not_gate_extension_on_having_an_api(self):
        i = RM.index("| 其它招聘站 |")
        row = RM[i:].split(chr(10))[0]
        self.assertNotIn("若该站有公开接口，用", row,
                         "README 又把「能不能接」挂在「有没有接口」上了")

    def test_it_names_both_paths(self):
        i = RM.index("| 其它招聘站 |")
        row = RM[i:].split(chr(10))[0]
        self.assertIn("公开接口", row, "没说有接口时装 CLI")
        self.assertIn("浏览器", row, "没说要登录/撞反爬时走浏览器")
        self.assertRegex(row, r"不是接不了", "没否掉「接不了」这个读法")


class AntiBotChallengesAreNeverBypassed(unittest.TestCase):
    def test_the_rule_is_restated_here(self):
        self.assertRegex(ADD, r"绝不绕过挑战|绕过 WAF 或反爬挑战不做",
                         "没把「不绕反爬」这条写进接入流程")

    def test_it_says_where_such_a_site_goes_instead(self):
        # **锚详细那一条，不是摘要表。** 表格那一格写的是 `**2**`，
        # 而这条要查的是正文有没有说清「该走哪条路」——锚错了就在表格上求值。
        # 这类定位失误在本仓库的测试里已经犯过五次。
        i = ADD.index("撞反爬或 WAF 挑战页")
        self.assertIn("第 2 层", ADD[i:i + 500], "只说了不许绕，没说该走哪条路")

    def test_the_canonical_rule_still_exists(self):
        """判据的前提。AGENTS 那条没了，这里复述的就成了孤儿。"""
        self.assertRegex(AG, r"绕过 WAF\s*\n?或反爬挑战不做",
                         "AGENTS.md 里那条「不绕反爬」不见了")


if __name__ == "__main__":
    unittest.main()
