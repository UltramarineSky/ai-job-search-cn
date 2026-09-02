"""每个岗都要落在某一份名单里——没有岗可以从页面上凭空消失。

面板把岗分派到四个去处，判据各不相同：

    可以投的岗位   canSell(判词)：**白名单**，不认识就不进
    不投的岗位     isOut(判词) 或 skipped 或 expired：**黑名单**，容后缀
    漏斗三格       funnels（导出侧算好的）
    重复挂法       dupOf，不单独占行（链接列在主条目详情里）

白名单和黑名单**不是彼此的反面**——这是有意的，注释里论证过：一个硬门没过但
已经投出去的岗，两边都不该进，它待在已投那边。判词认不出来的同理。

代价是中间那条缝：**一个判词既不在白名单、也不匹配黑名单、又没有漏斗落点，
那一行就从整页上消失了**，而没有任何提示。用户不会知道少了什么。

这条缝会被哪几种改动撑开：

- Python 侧给 `_cli.GATE_FAIL_PREFIXES` 加一种新说法，而 `App.tsx` 的 `isOut`
  没跟上（两份词表跨语言，import 不过去，只能靠守卫钉）
- 评分器造一个新判词（`test_verdicts_stay_in_the_vocabulary` 拦词表，
  但它**跳过 expired**，而且不检查落点）
- 有人收紧 `canSell` 或 `isOut` 的匹配，忘了另一边

所以这里不测词表，测**落点**：拿全库真实数据跑一遍分派，一个都不能掉。
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

APP = ROOT / "web" / "src" / "App.tsx"


def plain(v) -> str:
    return re.sub(r"^粗筛[：:]\s*", "", str(v or "")).strip()


class NoJobFallsThroughTheCrack(unittest.TestCase):

    def _jobs(self):
        f = ROOT / "web" / "public" / "data.json"
        if not f.is_file():
            self.skipTest("还没导出过面板数据")
        jobs = json.loads(f.read_text(encoding="utf-8")).get("jobs", [])
        if not jobs:
            self.skipTest("还没有职位")
        return jobs

    @staticmethod
    def _is_out(v: str) -> bool:
        """复刻 App.tsx 的 `isOut`。形状由下面 test_the_replica_matches_the_source 钉住。"""
        p = plain(v)
        return (p.startswith("不满足硬性条件") or p.startswith("硬门")
                or "跳过" in p or "不建议" in p)

    def test_every_job_is_reachable(self):
        sell = set(_cli.VERDICTS[:3])
        lost = []
        for j in self._jobs():
            if j.get("dupOf"):
                continue                        # 重复挂法：主条目里列着
            if plain(j.get("verdict")) in sell:
                continue                        # 可以投的岗位
            if (self._is_out(j.get("verdict") or "")
                    or j.get("skipped") or j.get("expired")):
                continue                        # 不投的岗位
            if j.get("funnels") or j.get("applied"):
                continue                        # 漏斗 / 已投
            lost.append(f"{(j.get('title') or '')[:28]}  判词「{plain(j.get('verdict'))}」")
        self.assertEqual(lost, [],
                         f"{len(lost)} 个岗四份名单都进不去，整页看不到它们，"
                         "而页面不会说少了什么：\n  " + "\n  ".join(lost[:8]))

    def test_the_replica_matches_the_source(self):
        """上面那个复刻必须跟 `App.tsx` 同形，否则守的是我想象的规矩。"""
        src = APP.read_text(encoding="utf-8")
        i = src.index("const isOut = (v: string)")
        body = src[i:src.index("\n  };", i)]
        for token in ('startsWith(GATE_FAIL)', 'startsWith("硬门")',
                      'includes("跳过")', 'includes("不建议")'):
            with self.subTest(token):
                self.assertIn(token, body,
                              f"App.tsx 的 isOut 改了形状（少了 {token}），"
                              "这里的复刻要跟着改，否则这条守卫就失效了")

    def test_ts_covers_every_python_gate_prefix(self):
        """`_cli.GATE_FAIL_PREFIXES` 每一条都要被 TS 那边认出来。

        两份词表跨语言，import 不过去。Python 侧加一种新说法而 TS 没跟上，
        那批岗就掉进缝里——不进名单、不进搁置区、整页看不见。
        """
        src = APP.read_text(encoding="utf-8")
        gate = re.search(r'export const GATE_FAIL = "(.+?)";',
                         (ROOT / "web" / "src" / "types.ts").read_text(encoding="utf-8"))
        self.assertIsNotNone(gate, "types.ts 里的 GATE_FAIL 不见了")
        for prefix in _cli.GATE_FAIL_PREFIXES:
            with self.subTest(prefix):
                self.assertTrue(self._is_out(prefix),
                                f"Python 认「{prefix}」是硬门没过，而面板的 isOut 不认——"
                                "这一档的岗会从整页上消失")
        del src

    def test_the_detector_can_fail(self):
        """变异内建：造一个掉进缝里的判词，判据必须抓得到。"""
        v = "待商榷"
        self.assertNotIn(v, _cli.VERDICTS[:3])
        self.assertFalse(self._is_out(v),
                         "判据放得太宽，连自造的新判词都当成出局了")


if __name__ == "__main__":
    unittest.main()
