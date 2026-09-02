# -*- coding: utf-8 -*-
"""被删掉的额度数，不许再被当成现行约束引用。

2026-08-26 本人裁定删掉四个**我们自己拍出来的**抓取额度（每轮 10 次动作、
每天 2 轮、轮间隔 10 分、每天 60 次请求）—— 原话：「你为什么直接限制了额度，
没有固定额度的，你应该等撞到才算到了额度，我们当前应该是控制单渠道每次访问的
间隙时间」。留下的是**动作间隔**（`GAP_S`：navigate 8 秒 / fetch 4 秒 /
click 3 秒）和「撞了才冷却 24 小时」。

`CONTRIBUTING.md` 记着那次删除让 **39 条测试当场变红** —— 那 39 条都改了。
**没改的是散文**：注释与 docstring 里那句「每家每天 ≤60 次请求」不参与断言，
于是一条被推翻的规则安静地活了下来。实测 2026-08-27 全量审计扫出 **13 处**
仍把它当现行约束在引，其中两处更糟 —— `prescreen.py` 与 `fetch_details.py`
把 `portal_budget` 点成出处，**而那个文件里已经没有这个数了**。

代价不是措辞：这几处都在解释「额度花在哪儿最值」，是下一个人做取舍时读的依据。
按一个不存在的日上限去权衡，权衡的是个假约束。

判据：提到那几个数时，附近必须有「删掉 / 裁定 / 曾经」这类历史标记。
讲历史当然可以 —— 这个仓库的规矩本来就是把撤掉的决定留在原地当证据。
"""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

#: 本文件自己满篇都是那几个数（它在解释它们为什么不能再用），扫的时候跳过。
_SELF = "tests/test_a_deleted_quota_is_not_still_quoted.py"

#: 被删掉的那几个数的说法。写宽一点：漏报比误报贵。
DEAD = re.compile(r"≤\s*60\s*次|每天\s*60\s*次|60\s*次请求|每轮\s*10\s*[个次]动作|每天\s*2\s*轮")

#: 历史标记。有它就说明这段是在讲「这条规则被撤了」，不是在拿它当依据。
#:
#: ⚠️ **第一版把「原来」和「不再」也算进来，结果整条守卫是哑的。**
#: 那两个词在这个仓库里到处都是（复盘文风就爱写「原来写的是…」），
#: 700 字窗口内几乎必然命中 —— 变异检查当场证明：往 `jd_store.py` 的
#: docstring 里塞一句裸引用，守卫照样全绿，因为同一段里有「抓过的就**不再**抓」。
#: 判据只留**真正指向「这条被删了」**的词。
HISTORICAL = re.compile(
    r"删[掉了除]|全删|撤[掉销]|裁定|曾经|变红|2026-08-26|不是闸门|只是读数")

#: 往前后各看多少字找历史标记。
#:
#: **250，不是 700。** 第一版给 700，变异检查当场露馅：往 `job-cv.md` 开头塞一句
#: 裸引用，守卫不响 —— 因为 347 字外有个「裁定」，而那说的是**另一件事**
#: （2026-08-12 定「定制简历不进 /job-apply」）。窗口越宽，越容易蹭到一个
#: 不相干的标记然后放行。
#:
#: 250 是实测选的：120 / 180 / 250 / 350 四个值下，五处合法的历史记述**都不误报**、
#: 三个注入点**都抓得到**；到 500 就开始漏。取区间中段，两边都留余量。
WINDOW = 250


def _files():
    """扫哪些文件 —— 走**共享那份**，不自己维护跳过清单。

    这里原来手写着 `.private/ · users/ · web/dist/ · node_modules/` 一串前缀，
    而那正是 `.gitignore` 的抄件：新增一个被 ignore 的目录，这份清单就落后，
    而它**不会报错，只会开始扫不该扫的东西**。

    `tracked_text_files()` 是已跟踪的 + **未跟踪但没被 ignore 的**。后半截很要紧：
    新文件在第一次提交之前 `git ls-files` 里看不见，而那正是「刚写好、还带着
    旧说法」的那一刻 —— 那份 docstring 里记着它就是这么被绿着提交过一次的。
    """
    from test_no_maintainer_data_in_repo import tracked_text_files
    return tracked_text_files()


def _scan():
    bad = []
    for p in _files():
        rel = p.relative_to(ROOT).as_posix()
        if p.suffix not in (".py", ".md") or rel == _SELF:
            continue
        try:
            t = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for m in DEAD.finditer(t):
            seg = t[max(0, m.start() - WINDOW):m.end() + WINDOW]
            if not HISTORICAL.search(seg):
                line = t[:m.start()].count(chr(10)) + 1
                bad.append(f"{rel}:{line}  「{m.group(0)}」")
    return bad


class ADeletedQuotaIsNotStillQuoted(unittest.TestCase):
    def test_nothing_cites_it_as_a_live_gate(self):
        bad = _scan()
        self.assertEqual(
            bad, [],
            "这些地方还在把 2026-08-26 删掉的抓取额度当现行约束引用。\n"
            "现在真正的闸门是**动作间隔**（GAP_S：8/4/3 秒）+ 撞了才冷却 24 小时。\n"
            "要讲那段历史没问题，但要带上「删掉 / 裁定 / 曾经」之类的标记：\n  "
            + "\n  ".join(bad))

    def test_the_historical_passages_still_exist(self):
        """控制用例：真有几处在讲这段历史，否则上面那条是在空集上恒绿。

        这个仓库反复吃过「词表被清空 → 循环一次不跑 → 断言恒绿」的亏。
        """
        src = (ROOT / "tools" / "portal_budget.py").read_text(encoding="utf-8")
        self.assertRegex(src, DEAD, "portal_budget 里那段删除记录没了")
        self.assertRegex(src, HISTORICAL, "历史标记认不出来了，判据会全线误报")

    def test_the_detector_would_catch_a_bare_citation(self):
        """变异检查：一句不带历史标记的引用必须被认出来。"""
        self.assertRegex("抓取额度最稀缺（每家每天 ≤60 次请求）", DEAD)
        self.assertNotRegex("抓取额度最稀缺（每家每天 ≤60 次请求）", HISTORICAL)

    def test_the_real_gate_is_written_down_somewhere(self):
        """替代品要有出处 —— 不然下一个人只能再拍一个数出来。"""
        src = (ROOT / "tools" / "portal_budget.py").read_text(encoding="utf-8")
        self.assertIn("GAP_S = {", src, "动作间隔那张表没了")
        self.assertRegex(src, r"BLOCK_COOLDOWN_H\s*=\s*24", "冷却小时数没了")


if __name__ == "__main__":
    unittest.main()
