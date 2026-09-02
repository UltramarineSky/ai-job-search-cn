"""共享词表与判据只许在 `_cli.py` 定义一份——盯住别再散落。

2026-08-20 用户点破「很多相关逻辑是同一个，但分成多组了」，对账坐实五组重复：

| 逻辑 | 收拢前散落在 | 实际代价 |
|---|---|---|
| 判词五档 | audit / build_dashboard / export ×2 / writeback ×2 | 改档名要动六处 |
| 来源族清单 | audit（5 项） vs test_verdict_cap（4 项） | **已分叉**：「批量」一边放行一边拦，当时还错改了数据去迁就测试 |
| 协议归一化 | audit + test_stable_job_id 各手写一遍 replace | 第三处漏写就是下一批重复入库 |
| JD 正文阈值 80 | jd_store + export 各一个字面量 | export 注释自嘲「同一条线」——注释不是机制 |
| 薪数 12–24 | audit 常量 + export 字面量 | 收紧区间只会改到一半 |

这里不测行为（行为各自的测试管），只测**定义唯一**：谁在 `_cli` 之外又写了一份
字面量，谁就红。豁免只有两类，都在断言里点名：`doctor.py`（零依赖契约，内联副本
注释里指着正本）和文档（给人读的，引用不算定义）。
"""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import _cli  # noqa: E402


def _py_sources():
    """要扫的 Python 源：tools/ 全部 + tests/ 全部，豁免 doctor 与本文件。"""
    for d in ("tools", "tests"):
        for p in (ROOT / d).glob("*.py"):
            if p.name in ("doctor.py",):          # 零依赖契约，内联副本已点名正本
                continue
            if p.name == Path(__file__).name:
                continue
            yield p


#: 每条「只许在 `_cli` 定义一次」的判据：正则 + **一个该抓的** + **一个不该抓的**。
#:
#: 三样一起放，是因为只有正则的话这一整组是可以静默失效的：把正则改成一个匹配
#: 不到任何东西的串，每条 `test_*_defined_once` 都照样绿 —— 实测 2026-08-25 变异
#: 检验当场逮到（那时只有新加的抬头判据这一条，另外三条同样躲得过）。
#: `test_the_scan_reaches_the_python_files` 管的是**够不够得到文件**，
#: 管不了**认不认得出违规**，两件事。
#:
#: 「不该抓的」那一列同样不是凑数：这组守卫的老毛病是误伤夹具
#: （见 `_offenders` 里那段），一条正则松了会把测试数据当成定义。
_PATTERNS = {
    "判词档序": (
        r'"强匹配"\s*,\s*"值得投"\s*,\s*"可以考虑"',
        '    V = ("强匹配", "值得投", "可以考虑", "不建议")',
        '        if v in ("强匹配", "值得投"):',
    ),
    "来源族": (
        r'"粗筛"\s*,\s*"预筛"\s*,\s*"深评"',
        '    FAMS = ("粗筛", "预筛", "深评", "批量")',
        '        if src.startswith("粗筛"):',
    ),
    "协议归一化": (
        r'replace\("https://"',
        '    u = raw.replace("https://", "")',
        '    u = _cli.norm_url(raw)',
    ),
    "抬头在跟谁说话": (
        r'"直招"\s+in\s+\w+\s+or\s+"非猎头"\s+in',
        '        if "直招" in h or "非猎头" in h:',
        '        t = "- 渠道判定：**有对话方（HR 直招，非猎头）**"',
    ),
}


class OnlyCliDefinesTheVocabulary(unittest.TestCase):

    def _offenders(self, pattern: str):
        """扫「谁又定义了一遍」。注释与断言参数不算。

        `assertNotIn('replace("https://"', seg)` 这种行本身就是在**禁止**这么写，
        把它算成违规是守卫误伤自己人——2026-08-20 加 match_tracker 的守卫时当场撞上。
        判据：出现在 `assert*(` 调用里的字面量，是在描述规则、不是在定义词表。
        """
        rx = re.compile(pattern)
        out = []
        for p in _py_sources():
            if p.name == "_cli.py":
                continue
            for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
                s = line.lstrip()
                if s.startswith("#") or "assert" in s:
                    continue
                if rx.search(line):
                    out.append(f"{p.parent.name}/{p.name}:{i}  {line.strip()[:70]}")
        return out

    def test_the_scan_reaches_the_python_files(self):
        """对照用例：扫描真的够到了文件 —— 否则同文件里那些「没问题」是恒绿的。

        2026-08-20 实测：把 `Path.glob`/`rglob` 打成空之后本文件全绿。
        **扫不到文件时，「没有问题」和「没有检查」长得一模一样。**

        这不是假想——这个仓库真搬过目录（工作流正文从 `.claude/skills/` 搬到
        `workflows/`，`AGENTS.md` 里记着）。glob 还指着旧路径时，守卫会安静地失效。
        """
        found = list((ROOT / "tools").glob("*.py")) + list((ROOT / "tests").glob("*.py"))
        self.assertGreaterEqual(
            len(found), 100,
            f"只扫到 {len(found)} 个Python 文件 —— 判据大概是够不到文件了，"
            "而不是仓库真的只剩这么几个")

    def test_every_pattern_can_actually_fire(self):
        """四条正则各喂一个该抓的和一个不该抓的 —— 缺哪一样都不行。

        少了这条，把任何一条正则改成匹配不到东西的串，上面那几条全绿：
        **「没有违规」和「认不出违规」长得一模一样**（同本文件
        `test_the_scan_reaches_the_python_files` 那一课，只是换了一层）。
        """
        for name, (pat, hit, miss) in _PATTERNS.items():
            rx = re.compile(pat)
            with self.subTest(name=name, side="该抓"):
                self.assertTrue(rx.search(hit),
                                f"「{name}」这条认不出违规了：{hit.strip()}")
            with self.subTest(name=name, side="不该抓"):
                self.assertFalse(rx.search(miss),
                                 f"「{name}」这条把夹具当成了定义：{miss.strip()}")

    def test_five_band_tuple_defined_once(self):
        """判词档序的**连写序列**（≥3 档）只许出现在 _cli。

        两档的字面量放行：`is_strong` 的行为测试要拿「强匹配/值得投 + 带前缀变体」
        当具体输入，那是夹具不是定义。第一版连两档也抓，扫出 5 处，其中 2 处
        正是这种夹具——守卫抓「又定义了一遍词表」，不抓「拿两个词当测试数据」。
        """
        bad = self._offenders(_PATTERNS["判词档序"][0])
        self.assertEqual(bad, [],
                         "判词档序又被抄了一份——用 _cli.VERDICTS（切片即子集）：\n  "
                         + "\n  ".join(bad))

    def test_source_families_defined_once(self):
        bad = self._offenders(_PATTERNS["来源族"][0])
        self.assertEqual(bad, [],
                         "来源族清单又被抄了一份——它分叉过一次（「批量」一边认一边不认），"
                         "用 _cli.SOURCE_FAMILIES：\n  " + "\n  ".join(bad))

    def test_the_addressee_rule_defined_once(self):
        """抬头「在跟谁说话」的判据只许在 `_cli.addressee_said` 里写一遍。

        实测 2026-08-25 扫出三份，全都同字同序：`audit_pipeline` 里一份、
        两条测试里各一份。**同字同序才是它危险的地方** —— 谁也不红，
        而两边判的是同一批 outreach 文件：面板走 `_cli.addressee_problem`
        报警告，审计走自己那份出清单。规则一变，用户会在面板上看到一条
        警告，而审计说这份没问题。

        判据抓的是「`直招` 与 `非猎头` 用 `in` 连成一句」，不是「出现了
        `非猎头` 这四个字」—— 夹具里那句
        `- 渠道判定：**…（HR 直招，非猎头）**` 是数据，不是定义。
        """
        bad = self._offenders(_PATTERNS["抬头在跟谁说话"][0])
        self.assertEqual(bad, [],
                         "抬头判据又被写了一遍——用 _cli.addressee_said：\n  "
                         + "\n  ".join(bad))

    def test_scheme_stripping_defined_once(self):
        bad = self._offenders(_PATTERNS["协议归一化"][0])
        self.assertEqual(bad, [],
                         "协议归一化又被手写了——用 _cli.norm_url：\n  " + "\n  ".join(bad))

    def test_consumers_actually_import_the_canon(self):
        """收拢不是删字面量就完了——消费方得真的引用正本，否则下次照抄回去。"""
        expect = {
            "tools/writeback.py": ("_cli.CAP_BANDS", "_cli.VERDICTS"),
            "tools/build_dashboard.py": ("_cli.VERDICTS",),
            "tools/export_web_data.py": ("_cli.VERDICTS", "_cli.SALARY_MONTHS_SANE",
                                         "_cli.JD_MIN_BODY", "_cli.GATE_FAIL_PREFIXES"),
            "tools/jd_store.py": ("_cli.JD_MIN_BODY",),
            "tools/audit_pipeline.py": ("_cli.VERDICTS", "_cli.SOURCE_FAMILIES",
                                        "_cli.SALARY_MONTHS_SANE", "_cli.norm_url",
                                        "_cli.GATE_FAIL_PREFIXES"),
        }
        for rel, names in expect.items():
            src = (ROOT / rel).read_text(encoding="utf-8")
            for n in names:
                self.assertIn(n, src, f"{rel} 没有引用 {n}——正本白立了")

    def test_block_state_parsing_lives_in_portal_budget_only(self):
        """冷却状态的**读**只许在 portal_budget——export 那份此前是手抄的第二遍。"""
        import portal_budget as pb
        self.assertTrue(hasattr(pb, "block_state"))
        exp = (ROOT / "tools" / "export_web_data.py").read_text(encoding="utf-8")
        self.assertIn("pb.block_state", exp, "export 没走 portal_budget 的解析")
        # export 里不许再出现自己解析时间戳的痕迹
        self.assertNotIn("fromisoformat", exp.split("def _block_state")[1].split("\ndef ")[0],
                         "export 的 _block_state 又开始自己解析时间戳了")

    def test_the_other_lane_sentence_has_one_source(self):
        """「另一条怎么办」那句话只许有一份 —— 它是**关于账号安全的断言**。

        2026-08-21 实测：这句在 `check()` 和 `main()` 各写了一遍。
        当天给 `check()` 那份补了「先看看 CLI 是不是也封着」，
        **`main()` 那份没跟上**，间隔两小时。后果是 CLI 已经在冷却里、
        浏览器又撞风控时，命令行照样打印「CLI 那条不受影响，照常可以抓」——
        用户照它去抓，撞的是一条封着的路。

        判据盯的是**句子的骨架**，不是整句原文：措辞可以改，
        「同一句话出现两次」不行。
        """
        raw = (ROOT / "tools" / "portal_budget.py").read_text(encoding="utf-8")
        # **只数代码里的，不数注释和 docstring。**
        # 第一版没剥，于是在变异之前就红了 —— 因为上面那段说明**自己引用了这句话**。
        # 「断言撞上解释自己的文字」这个形状今天已经出现第六次：
        # 判据一旦禁止某个字符串，讲这条规则的文字就没法引用它，规则也就没法解释自己。
        src = re.sub(r'"""[\s\S]*?"""|#[^\n]*', "", raw)
        # 2026-08-26：第二个骨架跟着措辞换了一次。原来钉的是
        # 「浏览器那条不停、但放慢」，而本人当天指出 CLI 那条封的是 IP、
        # 等不掉，这段时间**浏览器就是该走的那条**（不是备胎），
        # 于是那句改写成了「这段时间走浏览器那条（放慢：…）」。
        #
        # 这条守卫本来就允许换措辞（见上面 docstring：「措辞可以改，
        # 『同一句话出现两次』不行」），换的时候把钉子挪过来即可 ——
        # 它要守的是**一份出处**，不是某一版遣词。
        for frag in ("CLI 那条不受影响", "这段时间走浏览器那条"):
            with self.subTest(frag=frag):
                self.assertEqual(
                    src.count(frag), 1,
                    f"「{frag}」在 portal_budget.py 里出现了 {src.count(frag)} 次 —— "
                    "两份就会各自演化，而这句说的是「现在能不能抓」")
        self.assertIn("def other_lane_note", src, "正本函数没了")

    def test_clearing_the_cooldown_lives_in_portal_budget_only(self):
        """冷却状态的**写**同理，而这一头才是真出过事的地方。

        解冷却原来在三处各写一遍同一个三字段清空
        （`portal_budget.main()`、`serve.apply_unblock`、测试）。
        2026-08-21 封控改成按通道存，三处一起坏 —— 而它们干的是同一件事。
        收进 `portal_budget.clear()` 之后，这条盯着别再散开：
        面板那一侧只许调它，不许自己动 `blocks` / `blocked_until`。
        """
        import portal_budget as pb
        self.assertTrue(hasattr(pb, "clear"), "clear() 正本没了")
        sv = (ROOT / "tools" / "serve.py").read_text(encoding="utf-8")
        body = sv.split("def apply_unblock")[1].split("\ndef ")[0]
        self.assertIn("pb.clear", body, "面板解封没走 portal_budget.clear")
        for field in ("blocked_until", '"blocks"', "'blocks'"):
            self.assertNotIn(field, body,
                             f"面板又开始自己动 {field} 了——换存储结构时它会独自坏掉")

    def test_the_canon_itself_is_sane(self):
        """正本自身的形状钉一眼：档序、天花板边界、区间。"""
        self.assertEqual(_cli.VERDICTS,
                         ("强匹配", "值得投", "可以考虑", "不建议", "跳过"))
        self.assertEqual([b for b, _ in _cli.CAP_BANDS],
                         list(_cli.VERDICTS[:4]), "天花板档名必须与档序一致")
        self.assertEqual(_cli.SALARY_MONTHS_SANE, (12, 24))
        self.assertEqual(_cli.norm_url("https://a/1"), _cli.norm_url("http://a/1"))


if __name__ == "__main__":
    unittest.main()
