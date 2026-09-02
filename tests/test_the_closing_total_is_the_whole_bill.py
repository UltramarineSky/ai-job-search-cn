# -*- coding: utf-8 -*-
"""收尾那个总数得是**全部**，那句「一次补完」也得真做得到。

## 两本账

收尾里 `writeback --apply` 和 `audit_pipeline --actionable` 都会点名
「现在还改得动的那几个岗」。2026-08-30 实测：

    writeback 报「还能改的」        10 个
    审计可操作层去重后              105 个
    交集                             5
    **只在 writeback 那边**          5

也就是说那句「下面这几条去重后是 105 个岗……一次补完」**不全**：
用户照它做完，还剩 5 个岗的「依据」在总览页上解释着别的数字。

**两本账各自都对，错的是其中一本自称是总数。** 判据（`_basis_is_stale`）
只长在 `writeback` 里，而出总数的是审计 —— 所以审计里补一条检查，
**借那个函数，不重写一份**。补完 105 → 110。

## 「一次补完」也不是全包

`/job-apply 全部` 按设计**不重跑深评**（那句话本来就写着）。可总数把两类
算在了一起：

- **补一节**（缺小节、缺投前必问）—— `全部` 做得了；
- **改已有内容**（依据说错了数、开场白踩线）—— 它一个都改不了。

所以那句话后面要说清有几个属于后者。集合由 `live_tail(verb="改")` 自己攒
（`_cli.LIVE_REWRITE`），**不手写一张「哪几条属于改」的名单** ——
手写名单只盖得住已经想到的，而这份审计还在长。
"""
import contextlib
import io
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tests"))
from _srcscan import code_of  # noqa: E402
import _cli  # noqa: E402
import audit_pipeline as ap  # noqa: E402
import writeback as wb  # noqa: E402


class TheStaleBasisIsCountedToo(unittest.TestCase):

    def test_the_audit_borrows_the_writers_judgement(self):
        """判据只有一份：审计不许自己再写一遍「什么叫依据过期」。"""
        seg = code_of("tools/audit_pipeline.py",
                      "def check_basis_still_explains_the_number(")
        self.assertIn("_basis_is_stale", seg)
        self.assertNotIn("_DIM_SAID", seg, "把 writeback 那份判据抄过来了")

    def test_it_can_enter_the_actionable_tier(self):
        """进不去那一档，它就进不了收尾那个总数。"""
        seg = code_of("tools/audit_pipeline.py",
                      "def check_basis_still_explains_the_number(")
        self.assertIn("live_tail", seg)

    def test_nothing_writeback_names_is_missing_from_the_total(self):
        """控制用例：这台机器上两边真的对得齐。"""
        ptr = ROOT / ".active_user"
        if not ptr.is_file():
            self.skipTest("没有活动用户")
        user = ptr.read_text(encoding="utf-8").strip()
        if not (ROOT / "users" / user / "job_scraper" / "seen_jobs.json").is_file():
            self.skipTest("没有职位库")
        seen, _d = ap.load(user)
        where = _cli.sendable_state(user, seen)
        live = {_cli.norm_url(v.get("url") or "") for v in seen.values()
                if isinstance(v, dict) and v.get("url")
                and wb._basis_is_stale(
                    str((v.get("rank_breakdown") or {}).get("依据") or ""),
                    v.get("rank_breakdown") or {})
                and where(v["url"]) == "还能发"}
        live.discard("")
        if not live:
            self.skipTest("这台机器上没有依据过期的岗")
        _cli.LIVE_SEEN.clear()
        with contextlib.redirect_stdout(io.StringIO()):
            ap.run(user, actionable=True)
        missing = sorted(live - set(_cli.LIVE_SEEN))
        self.assertEqual(missing, [],
                         f"{len(missing)} 个岗 writeback 说还能改，"
                         f"而收尾那个「一次补完」的总数没把它们算进去")


class TheHeadlineDoesNotOverPromise(unittest.TestCase):

    def test_it_splits_backfill_from_rewrite(self):
        seg = code_of("tools/audit_pipeline.py", "def main(")
        self.assertIn("LIVE_REWRITE", seg,
                      "那句「一次补完」没把「改已有内容」的那几个分出来")

    def test_the_set_is_derived_not_hand_written(self):
        """`live_tail` 自己按 verb 攒 —— 不许在审计里列一张「哪几条属于改」。

        ⚠️ **钉的是「它把 verb 传下去」，不是「LIVE_REWRITE 这个名字出现在
        它体内」。** 记账 2026-08-31 搬进 `note_live`（手写尾巴的两条检查
        也要调它），这条当场红 —— 判据钉实现位置，重构本身就成了违规。
        这个仓库为同一件事交过好几次学费。
        """
        seg = code_of("tools/_cli.py", "def live_tail(")
        self.assertIn("note_live(", seg, "`live_tail` 不再记账了")
        self.assertIn('rewrite=(verb == "改")', seg,
                      "verb 没传下去 —— 「要改已有内容」那一批就攒不出来")
        audit = (ROOT / "tools" / "audit_pipeline.py").read_text(
            encoding="utf-8")
        self.assertNotIn("LIVE_REWRITE[", audit,
                         "审计里自己往那批里塞东西了 —— 那就是手写名单")

    def test_the_sentence_carries_no_markdown(self):
        """这句话直接上终端。本轮已经为同一件事栽过一次。"""
        seg = code_of("tools/audit_pipeline.py", "def main(")
        i = seg.index("LIVE_REWRITE")
        line = seg[i:i + 400]
        self.assertNotIn("**", line)
        self.assertNotIn("`", line)


class EveryCheckThatKnowsRegistersWhatItKnows(unittest.TestCase):
    """自己拼尾巴的检查会绕过记账，于是那个「总数」不是总数。

    收尾那两个集合原来只由 `live_tail` 填。而有两条检查**自己拼尾巴**：

        开场白有不该出现的写法   要报完整的状态分布（已投 21 / 不投 12 /
                                下线 3），`live_tail` 把那半压掉了
        可投档却没材料           要按状态分桶，不做「还能不能发」的二分

    两条的岗因此既不进「去重后 N 个岗」那个总数，也不进「其中 M 个要改已有
    内容」那一批 —— 而重写一份开场白正是 `/job-apply 全部` **不做**的事。
    实测 2026-08-31：开场白那条报「还发得出去的 15 份」，15 份全在两集合外；
    接上之后「要改已有内容」从 25 涨到 34。

    ## 判据是派生的

    「调了 `sendable_state`」就是 `run()` 判它进不进 `--actionable` 的口径。
    进了那一档、又不走 `live_tail` 的，就必须自己调 `note_live` ——
    不必登记，加一条新检查时这里当场红。
    """

    def _bodies(self) -> dict:
        import ast
        src = (ROOT / "tools" / "audit_pipeline.py").read_text(encoding="utf-8")
        out = {}
        for n in ast.parse(src).body:
            if not isinstance(n, ast.FunctionDef):
                continue
            rest = n.body[1:] if ast.get_docstring(n) else n.body
            out[n.name] = "\n".join(ast.get_source_segment(src, x) or ""
                                    for x in rest)
        return out

    def test_the_scan_sees_the_checks(self):
        seg = self._bodies()
        self.assertGreater(len(seg), 40, "函数一个都没扫到")
        # **光数键不够。** 取空时字典照样有四十多个键，只是值全是空串 ——
        # 下面那条于是在「没有一条调 sendable_state」上永远绿（变异照出来的）。
        self.assertGreater(sum(len(v) for v in seg.values()), 50_000,
                           "扫到的函数体加起来太短 —— 抽取多半塌了")
        # 直接调 `sendable_state` 的**就是那两条自己拼尾巴的**（其余都走
        # `live_tail`）—— 也正是这条守卫要盯的那一档。扫不到它们，
        # 下面那条就没有对象。
        self.assertGreaterEqual(
            sum(1 for v in seg.values() if "sendable_state" in v), 2,
            "自己拼尾巴的那两条一条都没扫到")

    def test_every_hand_rolled_tail_registers(self):
        import audit_pipeline as ap
        seg = self._bodies()
        bad = []
        for label, fn in ap.CHECKS:
            body = seg.get(fn.__name__, "")
            if "sendable_state" not in body:
                continue                      # 进不了 --actionable 那一档
            if "live_tail" in body or "note_live" in body:
                continue
            bad.append(label)
        self.assertEqual(
            bad, [],
            "这几条进了收尾那一档、却自己拼尾巴，于是它们的岗从「去重后 N 个岗」"
            "里整批漏掉：" + repr(bad) + "。调一次 `_cli.note_live`")

    def test_the_two_sets_have_one_writer(self):
        """两个集合只许 `note_live` 写 —— 第二个写入点就是第二本账。"""
        src = (ROOT / "tools" / "_cli.py").read_text(encoding="utf-8")
        i = src.index("def note_live(")
        j = src.index("def live_tail(")
        inside = src[i:j]
        outside = src[:i] + src[j:]
        for tok in ("LIVE_SEEN.add", "LIVE_REWRITE["):
            with self.subTest(tok):
                self.assertIn(tok, inside, f"`note_live` 不再写 {tok}")
                self.assertNotIn(tok, outside, f"{tok} 有第二个写入点")

    def test_note_live_fills_both_sets(self):
        keep_s, keep_r = set(_cli.LIVE_SEEN), dict(_cli.LIVE_REWRITE)
        try:
            _cli.LIVE_SEEN.clear()
            _cli.LIVE_REWRITE.clear()
            _cli.note_live(["https://x.com/a", "", None], rewrite=True)
            self.assertEqual(_cli.LIVE_SEEN, {_cli.norm_url("https://x.com/a")},
                             "空链接不该进去，真链接要归一化")
            self.assertEqual(list(_cli.LIVE_REWRITE.values()),
                             ["https://x.com/a"], "值要留原样，好敲得出来")
            _cli.LIVE_REWRITE.clear()
            _cli.note_live(["https://x.com/b"])
            self.assertEqual(_cli.LIVE_REWRITE, {},
                             "没说要改的不该进「要改已有内容」那一批")
        finally:
            _cli.LIVE_SEEN.clear()
            _cli.LIVE_SEEN.update(keep_s)
            _cli.LIVE_REWRITE.clear()
            _cli.LIVE_REWRITE.update(keep_r)


if __name__ == "__main__":
    unittest.main()
