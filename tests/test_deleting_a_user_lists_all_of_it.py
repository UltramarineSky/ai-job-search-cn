# -*- coding: utf-8 -*-
"""删用户前那份「你会失去什么」，漏了它自己被指定要清的那几样。

`/job-user` 删用户是这个仓库破坏性最大的操作，它自己也这么写着。同意之前
要摆出会失去什么 —— 而那份清单只有四条：职位、投递记录、投递材料、
简历与求职信。

**而 `job-reset.md` 恰恰把这条命令写成了清掉其余那些的推荐做法**：

> 以下个人数据**不在本次重置范围内**，仍留在盘上：
> …`reports/` —— 已生成的总览页…`upskill/`、`gmail_sync/` —— 学习计划与邮件同步状态
> …`templates/active-cv.md`…
>
> 要连这些一起清掉，最干净的做法是删掉整个 `users/<你的用户名>/` 再跑 `/job-setup`
> （或用 `/job-user` 删除该用户后重建）。

**它指过去的命令，不列它指过去要清的东西。** 用户读到的是「删掉职位和投递记录」，
实际连简历审核报告（`reports/resume-audit-*.md`）和学习计划一起没了。

顺带第二处：那四个数原来是**手数**的（「读 `users/<名>/` 下的实际内容」）。
`doctor.py --user <名>` 报的正好就是这四项，零依赖、一行。同一条规矩
`job-outcome.md` 上已经立过（「该催哪几个 —— 用工具算，不要手算」），
而这里的静默错法更贵：**数少报了，他是按一个偏小的数点的头。**
"""
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
USER = (ROOT / "workflows" / "job-user.md").read_text(encoding="utf-8")
RESET = (ROOT / "workflows" / "job-reset.md").read_text(encoding="utf-8")
AGENTS = (ROOT / "AGENTS.md").read_text(encoding="utf-8")


def _listing() -> str:
    i = USER.index("### 第一步：列出会失去的东西")
    return USER[i:USER.index("### 第二步：确认", i)]


class TheListingCoversEverythingUnderTheUser(unittest.TestCase):
    #: `job-reset.md` 明说这条命令是清掉它们的办法 —— 那就得在同意前列出来。
    MUST_NAME = ("upskill", "reports", "gmail_sync", "templates/active")

    def test_every_category_reset_points_here_for_is_listed(self):
        seg = _listing()
        for cat in self.MUST_NAME:
            with self.subTest(cat=cat):
                self.assertIn(cat, seg, f"同意清单里没有 `{cat}`")

    def test_the_two_that_hurt_are_named_in_words(self):
        """目录名对用户没有意义 —— 「学习计划」「简历审核」才有。

        **只看那一行本身。** 下面那段 ⚠️ 里也写着这两个词（讲它们原来为什么漏），
        整段扫的话把清单里的人话删掉照样绿（变异实测）。"""
        seg = _listing()
        line = next((ln for ln in seg.splitlines() if "upskill" in ln), "")
        nxt = seg.splitlines()[seg.splitlines().index(line) + 1] if line else ""
        both = line + nxt
        self.assertIn("学习计划", both, "那一行只有目录名，没写它是什么")
        self.assertIn("简历审核", both, "同上")

    def test_the_original_four_survive(self):
        seg = _listing()
        for cat in ("job_scraper/", "job_search_tracker.csv",
                    "documents/applications", "resume/"):
            with self.subTest(cat=cat):
                self.assertIn(cat, seg)

    def test_the_profile_files_are_listed(self):
        """`profile/` 是他填了四轮问答攒出来的，漏掉它最说不过去。"""
        self.assertIn("profile/", _listing())

    def test_it_still_says_it_cannot_be_undone(self):
        seg = _listing()
        self.assertIn("删掉之后无法恢复", seg)
        self.assertIn("gitignore", seg, "没说清连版本库里也没有")

    def test_the_omission_is_written_down(self):
        """这几行看着像凑数，理由不挨着写就会被下一版「精简」掉。"""
        seg = " ".join(_listing().split())
        self.assertRegex(seg, r"它指过去的命令，不列它指过去要清的东西")
        self.assertRegex(seg, r"连简历审核报告和学习计划一起没了")


class TheCountsComeFromTheTool(unittest.TestCase):
    def test_it_runs_doctor(self):
        self.assertIn("python tools/doctor.py --user", _listing(),
                      "四个数还在手数")

    def test_it_says_why_not_by_hand(self):
        seg = " ".join(_listing().split())
        self.assertRegex(seg, r"用工具算，不要手数|用工具算，不要手算")
        self.assertRegex(seg, r"按一个偏小的数点的头",
                         "没说清手数错了会怎样")

    def test_it_cites_the_same_rule_elsewhere(self):
        """同一条规矩在 `job-outcome.md` 上立过 —— 引它，别自己发明一条。"""
        self.assertIn("job-outcome.md", _listing())
        self.assertIn("该催哪几个 —— 用工具算，不要手算", RESET + USER + AGENTS
                      + (ROOT / "workflows" / "job-outcome.md")
                      .read_text(encoding="utf-8"))

    def test_a_bad_user_never_reports_someone_elses_numbers(self):
        """**这才是要紧的那一条。** 删除清单拿这个数去让人点头 ——
        名字打错时若静默回落到活动用户，他会按**别人的数**同意删自己的目录。

        （第一版验的是「退出码非 0」，而自检**本来就任何状态都跑完再报**，
        那是拿别的工具的契约来要求它。它做对的是：明说这个用户不存在，
        且一个数都不报。）"""
        r = subprocess.run(
            [sys.executable, "-X", "utf8", str(ROOT / "tools" / "doctor.py"),
             "--user", "这个用户肯定不存在_zzz"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=90)
        out = (r.stdout or "") + (r.stderr or "")
        self.assertNotIn("Traceback", out)
        self.assertIn("不存在", out, "没说清这个用户不存在")
        self.assertNotIn("已抓", out, "报了别人的进度")

    def test_doctor_reports_the_four_numbers(self):
        p = ROOT / ".active_user"
        if not p.is_file():
            self.skipTest("没有活动用户")
        u = p.read_text(encoding="utf-8").strip()
        r = subprocess.run(
            [sys.executable, "-X", "utf8", str(ROOT / "tools" / "doctor.py"),
             "--user", u],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=90)
        line = next((ln for ln in (r.stdout or "").splitlines()
                     if "已抓" in ln), "")
        self.assertTrue(line, "自检没报那一行进度")
        for word in ("已抓", "已评", "已出材料", "投递记录"):
            with self.subTest(word=word):
                self.assertIn(word, line, f"自检那一行没有「{word}」")


class ItDoesNotWriteAThirdCopyOfTheEnumeration(unittest.TestCase):
    """`AGENTS.md` 那张枚举是唯一的解析来源，`job-reset.md` 已经有一份派生清单。
    这里再手写一份，三处迟早各长各的。"""

    def test_it_points_at_the_canonical_enumeration(self):
        seg = _listing()
        self.assertIn("AGENTS.md", seg)
        self.assertIn("活动用户与多用户", seg)

    def test_it_says_not_to_hand_write_another(self):
        self.assertRegex(" ".join(_listing().split()), r"别在这里手写第三份清单")

    def test_the_canonical_enumeration_still_covers_them(self):
        """引它就得它真的全。`test_multiuser_paths` 盯完整性，这里只确认这几项在。"""
        i = AGENTS.index("## 活动用户与多用户")
        seg = AGENTS[i:i + 1400]
        for cat in ("upskill/", "reports/", "gmail_sync/", "templates/active-cv.md"):
            with self.subTest(cat=cat):
                self.assertIn(cat, seg, f"权威枚举里没有 {cat}")


class TheOtherSideOfTheCrossReferenceIsIntact(unittest.TestCase):
    """`job-reset.md` 那句「最干净的做法是用 /job-user 删除该用户」是这条的前提。"""

    def test_reset_still_points_here(self):
        self.assertRegex(" ".join(RESET.split()),
                         r"用 `/job-user` 删除该用户后重建")

    def test_reset_still_enumerates_what_it_leaves_behind(self):
        i = RESET.index("以下个人数据**不在本次重置范围内**")
        seg = RESET[i:i + 700]
        for cat in ("reports/", "upskill/", "gmail_sync/"):
            with self.subTest(cat=cat):
                self.assertIn(cat, seg)

    def test_the_confirmation_strength_rule_survives(self):
        """原有的规矩：删用户的确认强度不该弱于 `/job-reset`。"""
        self.assertIn("删除 <名>", USER)
        self.assertRegex(" ".join(USER.split()), r"确认强度不该更弱")

    def test_deleting_the_only_user_is_still_supported(self):
        """单用户是绝大多数人的情形 —— 这条不许被这次改动带掉。"""
        self.assertRegex(" ".join(USER.split()), r"「唯一的用户」这条必须支持")


if __name__ == "__main__":
    unittest.main()
