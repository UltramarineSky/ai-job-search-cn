# -*- coding: utf-8 -*-
"""改判定的工具，不许只改职位库那一边。

`evaluation.md` 是事实源（`job-auto.md`「什么归机器，什么永远归人」）。
只改 `seen_jobs.json` 里的 `rank_score` / `rank_verdict`，下一次
`writeback --apply` 就会从存档把旧值顶回来 —— 中间那段时间面板上是另一个数，
而且它还会留下「硬门 FAIL 配判词值得投」这种混合状态（`writeback` 不碰
`硬性条件` 与 `依据`）。

**这个不变量 2026-08-30 一天里被两个不同的工具各违反一次：**

    score.py              第一版整块跳过深评 —— 对的，但代价是 89 个查表结果
                          要用户逐个敲命令。加 `--deep` 时改成「连 evaluation.md
                          一起改」，中途一度写成「找不到文件就只写库」，
                          18 条脱了节（同一个岗在猎聘挂两处，目录里记的是另一个号）。
    name_the_exclusion.py 只改了库。整链实跑收尾时 `writeback --apply` 当场把
                          2 个岗的「（独立编码）」顶掉了。

两次都不是粗心 —— 是**这个不变量没有守卫**，只写在散文里。所以有了这一条。

## 判据

扫 `tools/` 里所有会写 `rank_score` / `rank_verdict` 的模块，每个都得三选一：

- **连存档一起改**：出现 `patch_evaluation`（`score.py --deep` 那条路）；
- **躲开有存档的**：出现 `find_applications`（拿它认出哪些岗有 evaluation.md）；
- **只处理还没评过的**：出现 `decided_status`（`prescreen` 那条路 —— 它的候选集
  只有 `status == "new"`，那一档**从定义上就不可能有存档**）。

三样都没有的，要么真的漏了，要么该进下面那张豁免表并写清理由。

> 第三条是这条守卫**自己长出来的**：第一版只认前两条，当场把 `prescreen.py`
> 报成违规 —— 而它其实安全，只是靠了另一种机制。判据太窄和真违规长得一模一样，
> 都是「红」；分清楚的唯一办法是去读那个模块。
"""
import ast
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]

#: 写这两个字段的模块必须过上面那道判据。
_WRITES = re.compile(r"""\[\s*["']rank_(?:score|verdict)["']\s*\]\s*=""")

#: 豁免：**每一条都要写清为什么它可以只改库**。
EXEMPT = {
    # 它做的正是「从存档写回库」这个动作本身 —— 存档就是它的输入。
    "writeback.py": "它是从 evaluation.md 写回库的那一方，存档是它的输入",
}


def _modules_that_write():
    out = {}
    for f in sorted((ROOT / "tools").glob("*.py")):
        src = f.read_text(encoding="utf-8")
        # 只看真代码，不看注释/文档字符串里的示例
        code = "\n".join(ln for ln in src.splitlines()
                         if not ln.lstrip().startswith("#"))
        if _WRITES.search(code):
            out[f.name] = src
    return out


class EveryWriterEitherPatchesOrSkips(unittest.TestCase):
    def test_the_scan_finds_something(self):
        """判据自身要有支点 —— 一个都没扫到就说明正则坏了，而不是全都合规。"""
        self.assertGreaterEqual(len(_modules_that_write()), 3)

    def test_each_one_handles_the_archive(self):
        for name, src in _modules_that_write().items():
            if name in EXEMPT:
                continue
            with self.subTest(module=name):
                self.assertTrue(
                    "patch_evaluation" in src or "find_applications" in src
                    or "decided_status" in src,
                    f"{name} 会改 rank_score/rank_verdict，却三条都不占："
                    f"不连 evaluation.md 一起改、不躲开有存档的岗、"
                    f"也不是只处理没评过的 —— 下一次 writeback --apply "
                    f"会把它的改动顶回去")

    def test_every_exemption_says_why(self):
        for name, why in EXEMPT.items():
            with self.subTest(module=name):
                self.assertTrue((ROOT / "tools" / name).is_file(),
                                f"豁免表里的 {name} 已经不存在了，该删掉这一行")
                self.assertGreater(len(why), 12, "豁免要写清理由，不能只留个名字")

    def test_the_exemptions_really_write_those_fields(self):
        """豁免表不许养僵尸：不再写那两个字段的，就该从表里删掉。"""
        writers = _modules_that_write()
        for name in EXEMPT:
            with self.subTest(module=name):
                self.assertIn(name, writers,
                              f"{name} 已经不写 rank_score/rank_verdict 了，"
                              f"豁免留着只会掩护下一个真问题")


class TheLessonIsWrittenDownWhereItIsBroken(unittest.TestCase):
    def test_name_the_exclusion_says_why_it_skips(self):
        src = (ROOT / "tools" / "name_the_exclusion.py").read_text(encoding="utf-8")
        self.assertIn("存档是事实源", src)
        self.assertIn("/job-apply", src)

    def test_score_says_why_it_patches(self):
        src = (ROOT / "tools" / "score.py").read_text(encoding="utf-8")
        self.assertIn("顶回来", src)


if __name__ == "__main__":
    unittest.main()
