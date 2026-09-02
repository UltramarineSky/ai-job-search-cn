# -*- coding: utf-8 -*-
"""撞停时印的那句话，指向一份按设计排掉了刚被封那一家的名单。

`fetch_details` 只抓猎聘 CLI 那条；`--browser-list` 给的是**其余渠道**那批要人
拿浏览器开的岗，所以它排掉 `CLI_PORTAL` —— 平时对。

**撞限流之后不对**：那一刻猎聘那批恰好变成了只有浏览器够得着的活。而工具撞停时
自己印的正是这份名单：

    这段时间猎聘的浏览器那条一直是通的（自动放慢，不是停）：
      名单跑 python tools/fetch_details.py --browser-list

实测 2026-08-27 一次 `/job-auto`：CLI 抓到 24 份撞 RATE_LIMITED 停手，此时缺 JD 的
**407 个**猎聘岗一个都不在名单里 —— 照提示走等于对着空名单干活，而
`liepin-browser` 那条闸门当时是通的（放慢 ×3，不是停）。

同一课这个仓库记过一次：限流时印「还剩约 8 小时 13 分」，用户照它等了三天，
而同一时间浏览器那条一直通着没人走。**「这条路堵了」和「这批货没人能碰」是两回事。**

## 判据要点名通道

`block_state(..., lane="cli")`，不能省 `lane`：省了就是「有没有任何一条通道被封」，
于是**浏览器自己被封**时会把猎聘那批塞进浏览器名单 —— 正好反了。
那个口径差别 `block_state` 的 docstring 里已经写过（面板要不点名的，`check()` 必须点名）。
"""
import datetime as dt
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tests"))
import fetch_details as fd  # noqa: E402
import portal_budget as pb  # noqa: E402
from _srcscan import code_of  # noqa: E402


class WhoOwnsTheCliBatch(unittest.TestCase):
    """用假的 `_missing_alive` 与假的闸门跑，不碰真库。"""

    def setUp(self):
        self.rows = {
            fd.CLI_PORTAL: [{"url": "u1", "title": "猎聘岗", "first_seen": "2026-08-27"}],
            "boss-browser": [{"url": "u2", "title": "BOSS岗", "first_seen": "2026-08-20"}],
        }
        self._alive, self._state, self._load = (
            fd._missing_alive, pb.block_state, pb.load)
        fd._missing_alive = lambda user: dict(self.rows)
        pb.load = lambda user: {}

    def tearDown(self):
        fd._missing_alive, pb.block_state, pb.load = (
            self._alive, self._state, self._load)

    def _todo(self, blocked_lane=None):
        def fake(data, portal, now, lane=""):
            hit = blocked_lane is not None and lane == blocked_lane
            return {"blocked": hit, "why": "", "held_minutes": 0,
                    "where": "", "lane": lane}
        pb.block_state = fake
        return [e["title"] for e in fd.browser_todo("u")]

    def test_normally_the_cli_batch_stays_out(self):
        self.assertEqual(self._todo(), ["BOSS岗"])

    def test_when_the_cli_lane_is_blocked_its_batch_joins(self):
        self.assertEqual(sorted(self._todo("cli")), ["BOSS岗", "猎聘岗"])

    def test_a_blocked_browser_lane_does_not_pull_it_in(self):
        """浏览器自己封着时把猎聘那批塞进浏览器名单 —— 正好反了。"""
        self.assertEqual(self._todo("browser"), ["BOSS岗"])


class ItAsksTheGateRatherThanGuessing(unittest.TestCase):
    SEG = code_of("tools/fetch_details.py", "def browser_todo(", "def missing_urls(")

    def test_the_lane_is_named(self):
        self.assertIn('lane="cli"', self.SEG,
                      "省了 lane 就变成「有没有任何一条通道被封」，口径反了")

    def test_it_does_not_reimplement_the_gate(self):
        for w in ("blocked_until", "isoformat", "timedelta"):
            self.assertNotIn(w, self.SEG, f"又在这里自己解析冷却（{w}）")

    def test_the_measured_cost_is_recorded(self):
        doc = fd.browser_todo.__doc__ or ""
        self.assertIn("407", doc, "实测数没留下")
        self.assertIn("2026-08-27", doc, "实测数没带日期")


class TheMessageThatPointsHereStillPointsHere(unittest.TestCase):
    """撞停那句话改了指向，这条守卫的由头就变了 —— 一起改，别只改一头。"""

    SRC = (ROOT / "tools" / "fetch_details.py").read_text(encoding="utf-8")

    def test_the_stop_message_still_sends_people_to_this_list(self):
        i = self.SRC.index("撞风控就停，硬闯会把账号搭进去")
        self.assertIn("--browser-list", self.SRC[i:i + 1200],
                      "撞停提示不再指向这份名单了 —— browser_todo 那段特判要重新论证")


if __name__ == "__main__":
    unittest.main()
