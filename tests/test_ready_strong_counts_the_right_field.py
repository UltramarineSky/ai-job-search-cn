# -*- coding: utf-8 -*-
"""「备好的里面有几个能直接发」得真的数出来。

`counts["ready_strong"]` 决定面板与「下一步」说哪句话：有强档就催他去发，
一个都没有就说「备好的 N 个都是「可以考虑」这一档——先问清楚关键信息再决定，
别当群发名单」。

`build_model` 造的 job dict 里判词那一格叫 **`verdict`**（`resolve_score` 的返回，
深评优先），而这里读的是 `rank_verdict`——那是 `seen_jobs.json` 里的键名，
job dict 上没有。`.get()` 恒为 `None`，于是 `ready_strong` 恒为 0：**全是「强匹配」
也会被劝住别发**。

这条不比常量、不看注释，直接跑 `build_model` 数出来的那个数。
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import build_dashboard as bd  # noqa: E402
import export_web_data as ex  # noqa: E402


def _app(url, dirname):
    return {"dir": dirname, "url": url, "resume": None,
            "outreach": {"url": url, "greeting": "g", "email_subject": "",
                         "email_body": "", "wangshen": ""},
            "interview_preps": [], "evaluation": None}


def _model(verdicts):
    seen, apps = {}, []
    for i, v in enumerate(verdicts, 1):
        u = f"https://x/{i}"
        seen[u] = {"url": u, "title": f"岗{i}", "company": f"公司{i}",
                   "status": "ranked", "rank_score": 80, "rank_verdict": v}
        apps.append(_app(u, f"公司{i}_岗{i}"))
    return bd.build_model(seen, apps, [], True, "张三", ["张三"])


class ReadyStrongIsActuallyCounted(unittest.TestCase):

    def test_the_scan_reaches_the_tools(self):
        """对照用例：扫描真的够到了文件 —— 否则同文件里那些「没问题」是恒绿的。

        2026-08-20 实测：把 `Path.glob`/`rglob` 打成空之后本文件全绿。
        **扫不到文件时，「没有问题」和「没有检查」长得一模一样。**

        这不是假想——这个仓库真搬过目录（工作流正文从 `.claude/skills/` 搬到
        `workflows/`，`AGENTS.md` 里记着）。glob 还指着旧路径时，守卫会安静地失效。
        """
        found = list((ROOT / "tools").glob("*.py"))
        self.assertGreaterEqual(
            len(found), 12,
            f"只扫到 {len(found)} 个工具脚本 —— 判据大概是够不到文件了，"
            "而不是仓库真的只剩这么几个")

    def test_all_strong_verdicts_are_counted(self):
        m = _model(["强匹配", "强匹配", "值得投"])
        self.assertEqual(m["counts"]["ready"], 3)
        self.assertEqual(m["counts"]["ready_strong"], 3,
                         "备好的全是可以直接发的那两档，却数成 0")

    def test_consider_only_is_not_counted(self):
        m = _model(["可以考虑", "可以考虑"])
        self.assertEqual(m["counts"]["ready"], 2)
        self.assertEqual(m["counts"]["ready_strong"], 0,
                         "「可以考虑」是「先问清楚再决定」，不能算进可以直接发的")

    def test_the_coarse_prefix_does_not_hide_a_strong_verdict(self):
        """粗筛判词带「粗筛：」前缀，不能因此漏数。"""
        self.assertEqual(_model(["粗筛：强匹配"])["counts"]["ready_strong"], 1)

    def test_the_word_list_is_the_same_one_the_exporter_uses(self):
        """两处各写一份判词表，飘起来是必然的。"""
        for v in ex.STRONG_VERDICTS:
            with self.subTest(v=v):
                self.assertEqual(_model([v])["counts"]["ready_strong"], 1,
                                 f"导出器认「{v}」可以直接发，面板不认")


class TheHarnessLabelStaysTrue(unittest.TestCase):
    """`build_model` 的说明写着「这是测试夹具，不是生产路径」——那句话得一直为真。

    它值钱的地方在于**告诉下一个人「在这里改计数不会影响面板」**。哪天有人把它
    接进生产（那是撤掉这份重复的正路之一），标签就成了谎话，而谎话比没有更坏：
    读到它的人会以为改这里没有用户可见的后果，照旧改一半。
    """

    def test_no_production_module_imports_it(self):
        bad = []
        for p in sorted((ROOT / "tools").glob("*.py")):
            if p.name == "build_dashboard.py":
                continue
            for i, l in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
                s = l.strip()
                if s.startswith("#"):
                    continue
                if "build_model" in s and ("import" in s or "bd." in s or "(" in s):
                    bad.append(f"{p.name}:{i}: {s[:80]}")
        self.assertEqual(
            bad, [],
            "有生产代码用上 build_model 了——那它就不再是测试夹具，"
            "请改掉它 docstring 里那段警告，并把两份计数的重复一并了结：\n  "
            + "\n  ".join(bad))

    def test_the_warning_is_still_there(self):
        src = (ROOT / "tools" / "build_dashboard.py").read_text(encoding="utf-8")
        i = src.index("def build_model")
        head = src[i:i + 1800]
        self.assertIn("测试夹具", head, "警告没了——下一个人会把它当权威")
        self.assertIn("export_web_data", head, "没说清真正算数的是谁")


if __name__ == "__main__":
    unittest.main()
