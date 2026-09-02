# -*- coding: utf-8 -*-
"""「可投 + 材料备好 + 库里没 JD」是最危险的一档，而两条现有检查都不管它。

已经有两条在管 JD：

    check_no_jd_but_sellable        来源明说「未抓 JD」却给了可投档位
    check_jd_read_but_not_stored    来源自称读过、而详情库查不到

**两条都不管这个交集**：前者把「自称读过」的排除在外（它只认老实承认没读的），
后者不看有没有出材料。而这一批是风险最高的那一档 —— 材料已经躺在那儿，
用户随时可能复制开场白发出去，**而支撑这个判定的 JD 正文没有任何人能再看一眼**。
判错了没人拦；岗位下线之后连复核的机会都没有。

实测活动用户 2026-08-30：**37 个**。抽查最高分那个（80 分「强匹配」，全库最高）
—— JD 的硬性要求写着「具备真实的公司级 AI 变革主导经验」「筹建并领导公司 AI
核心团队」，而他是独立开发者、没带过团队。**那个 80 分是在看不见这段话的
情况下给的。**

这条守卫钉三件事：这条检查在、它给的修法不是「降档」、以及它给的命令是能敲的。
"""
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tests"))
from _live import user_or_skip  # noqa: E402
import audit_pipeline as ap  # noqa: E402

NAME = "JD：可投的材料备好了，依据却不在库里"


class TheCheckExists(unittest.TestCase):
    def test_it_is_registered(self):
        self.assertIn(NAME, [n for n, _fn in ap.CHECKS])

    def test_it_is_not_one_of_the_two_that_already_existed(self):
        """三条各管一段，名字不许撞 —— 撞了就有人以为改一条就够。"""
        names = [n for n, _ in ap.CHECKS]
        for other in ("JD：没读就给了可投档位", "JD：读了没落库"):
            with self.subTest(other=other):
                self.assertIn(other, names)
                self.assertNotEqual(other, NAME)

    def test_it_says_why_the_two_others_miss_it(self):
        doc = ap.check_material_ready_without_a_stored_jd.__doc__ or ""
        self.assertIn("两条都不管这个交集", doc)

    def test_it_refuses_to_auto_downgrade(self):
        """没有 JD 就没有依据 —— 换个数字仍然是猜（同兄弟那条的原话）。"""
        doc = ap.check_material_ready_without_a_stored_jd.__doc__ or ""
        self.assertIn("换个数字仍然是猜", doc)


class TheFixItNamesIsRunnable(unittest.TestCase):
    def _msg(self):
        seen, details = ap.load(user_or_skip())
        ap._USER[:] = [user_or_skip()]
        out = ap.check_material_ready_without_a_stored_jd(seen, details)
        if not out:
            self.skipTest("这一档已经清空了 —— 好事")
        return out[0][2]

    def test_it_names_a_command(self):
        """至少给出一条敲得动的命令。

        ⚠️ **别同时钉两条。** 2026-08-30 起补法是**按渠道选出来的**：
        全是猎聘就只给 `fetch_details --recheck`（那条只走猎聘 CLI），
        含别家就给 `--browser-list` + `jd_store --save`。两条都钉的话，
        这一档清到只剩猎聘时它会莫名其妙地红，而那时消息是对的。
        """
        m = self._msg()
        self.assertTrue("fetch_details.py" in m or "jd_store.py --save" in m,
                        "报了问题却没说该敲什么")

    def test_it_reports_the_portals(self):
        """猎聘那批和浏览器那批修法不同 —— 是哪几家要说出来。

        原来这条钉的是「按渠道：」四个字。2026-08-30 那一格改成了跟在
        还能补的那几个名字后面的括注（`Agent产品Leader、…（BOSS 3）`），
        因为**整条消息的规模改成跟着「他现在动得了什么」走**，不再跟着总数走。
        钉字面量会把一次正当的收口弄红，所以改钉「有没有报出渠道名」。
        """
        m = self._msg()
        self.assertTrue(any(k in m for k in ("猎聘", "BOSS", "智联", "前程无忧")),
                        "没说这几个岗在哪几家 —— 而修法按家分")

    def test_the_fix_matches_the_portals_it_named(self):
        """**给的补法要对得上它刚点名的那几家。**

        猎聘那条（`fetch_details --recheck`）只走猎聘 CLI；别家只能开页面。
        列一条对方用不上的路径，等于让他敲一次再发现白敲。
        """
        m = self._msg()
        others = [k for k in ("BOSS", "智联", "前程无忧") if k in m]
        if others:
            self.assertIn("--browser-list", m,
                          f"点了 {others}，却没给开页面那条路")

    def test_no_markdown_reaches_the_terminal(self):
        self.assertNotIn("**", self._msg())

    def test_no_markdown_reaches_the_terminal(self):
        self.assertNotIn("**", self._msg())


if __name__ == "__main__":
    unittest.main()
