"""预筛敢结案，是因为结果**能放回**——那个出口没了，结案权也就该收回。

`--annual-floor` 是三条规则里唯一有结案权的。它敢有，靠的是三件事同时成立：

1. 判据客观（薪资串折年包，谁算都一样）
2. 方向偏向放过（薪数未知时按 `OPTIMISTIC_MONTHS` 乐观估）
3. **结果可逆**——写的是 `status=ranked` + 判词「跳过」+ 依据，落进搁置区，
   面板给规则淘汰的岗留着「放回可以投」

第 3 条是前提，却只写在注释里。`Shortlist.tsx` 那边论证过为什么规则淘汰的
**更**要留撤销口：「谁下的结论谁最可能错」——它一个 JD 字都没读过。

哪天有人把那个按钮收掉（比如「搁置区太乱，只留手动排除的」），
这条规则就在无声无息地做不可逆的判决，而它的依据是一个**下游补不回来**的估值：
实测 615 个「列表页没标薪数、且已抓到 JD 正文」的岗，正文写了薪数的只有 2 个。

所以这条守卫把两端拴在一起：**结案权 ⇔ 放回口**。
"""

from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import _cli  # noqa: E402


class ClosingWritesARecoverableShape(unittest.TestCase):

    def test_it_does_not_set_skipped(self):
        """结案写的是判词，不是 `skipped`——后者是用户自己的决定，两码事。"""
        src = (ROOT / "tools" / "prescreen.py").read_text(encoding="utf-8")
        i = src.index("for key, e, verdict, why, score in hits:")
        body = src[i:src.index("for key, _, why in parked:", i)]
        self.assertIn('entry["status"] = "ranked"', body)
        self.assertNotIn('"skipped"', body,
                         "规则淘汰不该写成用户手动排除——那会混掉「谁下的结论」")

    def test_the_reason_is_written_down(self):
        """搁置区里要能看出凭什么被淘汰，否则放不放回全靠猜。"""
        src = (ROOT / "tools" / "prescreen.py").read_text(encoding="utf-8")
        self.assertIn('"依据": why', src, "结案没写依据")
        self.assertIn('"来源": "预筛（未抓 JD）"', src,
                      "没标明是没读 JD 判的——那正是用户判断要不要放回的关键")


class TheWayBackIsStillThere(unittest.TestCase):

    def test_rule_skipped_jobs_can_be_restored(self):
        src = (ROOT / "web" / "src" / "components" / "Shortlist.tsx").read_text(
            encoding="utf-8")
        self.assertIn("放回可以投", src, "搁置区的放回口没了")
        self.assertIn("规则淘汰", src,
                      "规则淘汰的岗不再单独给放回口了——那预筛就不该再有结案权，"
                      "它一个 JD 字都没读过")

    def test_the_restore_endpoint_exists(self):
        serve = (ROOT / "tools" / "serve.py").read_text(encoding="utf-8")
        self.assertIn('"/api/restore"', serve, "放回的后端接口没了")
        self.assertIn("is_rule_skipped", serve,
                      "服务端不再区分「规则淘汰」了——放回时撤不撤判词会走错")


class TheEstimateCannotBeFixedLater(unittest.TestCase):
    """控制测试：薪数这个估值确实补不回来，所以这一锤是终局。"""

    def test_the_jd_body_almost_never_states_months(self):
        ptr = ROOT / ".active_user"
        if not ptr.is_file():
            self.skipTest("这个 clone 里没有活动用户")
        user = ptr.read_text(encoding="utf-8").strip()
        det = ROOT / "users" / user / "job_scraper" / "details"
        sj = ROOT / "users" / user / "job_scraper" / "seen_jobs.json"
        if not det.is_dir() or not sj.is_file():
            self.skipTest("还没抓过 JD")
        import export_web_data as ex
        seen = _cli.seen_of(json.loads(sj.read_text(encoding="utf-8")))
        by_url = {e.get("url"): e for e in seen.values() if e.get("url")}
        rx = re.compile(r"(\d{1,2})\s*薪")
        n = stated = 0
        for f in det.glob("*.json"):
            try:
                d = json.loads(f.read_text(encoding="utf-8"))
            except (ValueError, OSError):
                continue
            body = d.get("description") or ""
            if len(body) < _cli.JD_MIN_BODY:
                continue
            e = by_url.get(d.get("url")) or {}
            pkg = ex.annual_package(e.get("salary") or "", e.get("salaryMonths"))
            if not pkg or not pkg.get("assumed12"):
                continue
            n += 1
            if any(12 <= int(x) <= 24 for x in rx.findall(body)):
                stated += 1
        if n < 100:
            self.skipTest("样本太小")
        self.assertLess(stated / n, 0.10,
                        f"{n} 个没标薪数的岗里，{stated} 个能从 JD 正文补出薪数"
                        f"（{stated/n:.0%}）。要是这个比例上来了，"
                        "那就该改成「先放过、抓到 JD 再判」，"
                        "而不是继续拿 OPTIMISTIC_MONTHS 一锤定音")


if __name__ == "__main__":
    unittest.main()
