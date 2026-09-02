"""`/job-reset` 的范围必须说清楚——沉默地留下姓名手机号是这条命令最大的风险。

## 两个问题

**① 范围小是对的，不说清楚是错的。** `AGENTS.md` 的个人数据枚举有 11 类，
`/job-reset profile` 只覆盖 `profile/` 这 1 类。留下的里面最要紧的是
`resume/main.typ`——它**内联着姓名、手机号、邮箱**；`reports/` 里的面板 HTML
则嵌着全部职位与评分的快照。

用户看到「重置个人数据」完成，会合理地以为清干净了。范围不该扩大（多数时候他
只想重填资料、不想丢掉几百个已抓职位），但**必须把没清的列出来**，否则给的是
一个假的安心。

**② 那段 `rm` 用的是裸相对路径。** 个人数据在 `users/<活动用户>/` 下，可仓库根
**也有**一个 `documents/`——那是共享框架目录，里面只有 `README.md` 和各子目录的
`.gitkeep`。在仓库根照抄执行，结果是把 `.gitkeep` 删掉（目录结构随之从版本库
消失），而用户真正的投递材料一个都没删：**该删的没删，不该删的删了。**
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESET = ROOT / "workflows" / "job-reset.md"
AGENTS = ROOT / "AGENTS.md"


class ResetDisclosesWhatItDoesNotClear(unittest.TestCase):

    def test_it_lists_the_untouched_personal_data(self):
        t = RESET.read_text(encoding="utf-8")
        self.assertIn("不在本次重置范围内", t,
                      "/job-reset 没有列出它**不清**的个人数据——用户会以为清干净了")

    def test_the_resume_pii_warning_is_explicit(self):
        """这条最关键：简历里有姓名手机号邮箱，而 /job-reset profile 不碰它。"""
        t = RESET.read_text(encoding="utf-8")
        seg = t[t.index("不在本次重置范围内"):]
        seg = seg[:seg.index("> **为什么不由本命令直接删")]
        self.assertIn("resume/main.typ", seg)
        for w in ("姓名", "手机号", "邮箱"):
            self.assertIn(w, seg, f"没点明简历里还留着{w}")

    def test_it_offers_the_clean_slate_path(self):
        """只说「没清」不够，要给出真想清干净时该怎么做。"""
        t = RESET.read_text(encoding="utf-8")
        self.assertRegex(t, r"删掉整个 `users/",
                         "没告诉用户彻底清干净的做法")

    def test_every_enumerated_path_is_either_cleared_or_disclosed(self):
        """控制测试：AGENTS.md 每加一类个人数据，这里要么清、要么披露。

        少了这条，以后新增一个存个人数据的目录，`/job-reset` 会**静默地**漏掉它。
        """
        t = AGENTS.read_text(encoding="utf-8")
        seg = t[t.index("`profile/…`、`job_scraper/…`"):t.index("时，**一律解析为")]
        paths = [p for p in re.findall(r"`([^`]+)`", seg)]
        reset = RESET.read_text(encoding="utf-8")
        missing = []
        for p in paths:
            stem = p.split("/")[0].rstrip("…")
            # 要么在清理范围里（profile / documents），要么在披露清单里被点名
            if stem in ("profile", "documents"):
                continue
            if stem not in reset:
                missing.append(p)
        self.assertEqual(missing, [],
                         f"这些个人数据 /job-reset 既不清也不披露，用户不会知道它们还在：{missing}")


class ResetDeletesEverySubdirSetupCreates(unittest.TestCase):
    """`/job-setup` 建几个 `documents/` 子目录，`/job-reset` 就得删几个。

    2026-08-21 通读时抓到：setup 建**六个**
    （`cv` / `linkedin` / `diplomas` / `references` / `postings` / `applications`），
    reset 的 `rm` 块只覆盖**五个** —— 漏的是 `postings/`，
    也就是用户自己粘进来的职位页。

    后果是 `/job-reset` 最怕的那一种：**报成功，而那个目录一个文件都没动**。
    同一份 reset 文档在这段 `rm` 上面两段刚警告过这个形状
    （「命令报成功、什么也没删，用户以为清干净了」）。

    `/job-setup` 那一侧早就为同一件事立过规矩：「**六个都要建，逐个写出来**」
    ——起因是原来含糊写成「`applications/` 等子目录」，实现只建了一个。
    **建的那一侧学会了，删的这一侧没有。**

    判据**两边都从文档里抽**，不写死名单：抽 setup 的枚举，
    逐个到 reset 的 `rm` 块里找。
    """

    SETUP = ROOT / "workflows" / "job-setup.md"

    def _created(self) -> list:
        t = self.SETUP.read_text(encoding="utf-8")
        i = t.index("下**这六个子目录**")
        seg = t[i:i + 200]
        return [m.rstrip("/") for m in re.findall(r"`([a-z]+/)`", seg)]

    def test_setup_still_enumerates_them(self):
        """控制用例：抽得到那张名单，否则下面那条对着空气跑。"""
        made = self._created()
        self.assertGreaterEqual(
            len(made), 5, f"从 job-setup 只抽到 {made} —— 枚举的写法改了？")

    def test_reset_removes_each_one(self):
        rm = RESET.read_text(encoding="utf-8")
        i = rm.index('U="users/$(cat .active_user)"')
        block = rm[i:rm.index("```", i)]
        missing = [d for d in self._created() if f"documents/{d}/" not in block]
        self.assertEqual(
            missing, [],
            f"/job-setup 建了这些子目录，/job-reset 的 rm 块却不删："
            f"{missing} —— 命令会报成功，而它们一个文件都没动")


    def test_the_preview_lists_each_one(self):
        """**给用户看的那张预览也要六个都在。**

        2026-09-01 通读时抓到同一课的**第三次**：

        1. `/job-setup` 建的时候只建了一个（含糊写成「`applications/` 等子目录」）；
        2. `/job-reset` Step 3 的 `rm` 只删五个（漏 `postings/`，上面那条钉的就是它）；
        3. **Step 1 给用户看的预览只列五个** —— 而 `rm` 那边已经补齐了。

        第三次比前两次更糟。前两次是「该做的没做」；这一次是
        **`postings/`（他自己粘进来的职位页）从没出现在他点头确认的那张清单上，
        却照样被删**。这条命令的整个安全设计就是「把要清掉的东西一条不落地
        摆出来」再要确认 —— 预览少报一项，那次确认就是无效的。

        判据仍然从文档抽（`_created()`），不写死名单。
        **只看正文，不看 `>` 引用块** —— 我为这次修补写的说明里就点了
        `postings/` 的名，把它算进去的话，删掉正文那一行这条照样绿
        （上一轮刚有一条守卫这么瞎过）。
        """
        t = RESET.read_text(encoding="utf-8")
        i = t.index("用 Glob 把活动用户的")
        seg = t[i:t.index("## Step 2", i)]
        body = "\n".join(l for l in seg.splitlines()
                         if not l.lstrip().startswith(">"))
        missing = [d for d in self._created() if f"documents/{d}/" not in body]
        self.assertEqual(
            missing, [],
            f"Step 1 那张「这次会删掉的文件」预览漏了：{missing} —— "
            f"用户没看见它就点了确认，而 Step 3 照样删")


class DestructiveCommandsAreUserScoped(unittest.TestCase):
    """删数据的命令，路径必须写全 `users/<活动用户>/`。"""

    def test_rm_block_is_not_bare_relative(self):
        t = RESET.read_text(encoding="utf-8")
        block = re.search(r"```bash\n(.*?)```", t, re.S)
        self.assertIsNotNone(block, "reset.md 里找不到那段 bash")
        body = block.group(1)
        for line in body.splitlines():
            s = line.strip()
            if not s.startswith("rm"):
                continue
            with self.subTest(line=s):
                self.assertNotRegex(
                    s, r"rm\s+(-\w+\s+)*documents/",
                    "裸相对路径 documents/ —— 在仓库根执行会删掉共享框架的 .gitkeep，"
                    "而用户真正的材料一个都没删")

    def test_it_warns_about_the_shared_documents_dir(self):
        t = RESET.read_text(encoding="utf-8")
        self.assertIn("共享框架目录", t,
                      "没说明仓库根也有一个 documents/，照抄裸路径会删错地方")

    def test_repo_root_documents_really_is_shared(self):
        """这条测试的前提得成立：仓库根的 documents/ 确实是共享的、只有占位文件。"""
        d = ROOT / "documents"
        if not d.is_dir():
            self.skipTest("仓库根没有 documents/")
        real = [p for p in d.rglob("*")
                if p.is_file() and p.name not in (".gitkeep", "README.md")]
        self.assertEqual(real, [],
                         f"仓库根的 documents/ 里出现了非占位文件，个人数据可能落错了地方：{real}")


if __name__ == "__main__":
    unittest.main()
