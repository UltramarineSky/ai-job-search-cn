# -*- coding: utf-8 -*-
"""四家平台的名字，原来住在四张表里，其中两张已经分叉。

## 分叉长什么样

`tracker._HOSTS` 与 `outreach_header.PORTALS` 都在答同一个问题——「这个链接
是哪家平台」——而一份写「智联招聘」，另一份写「智联」。两个答案都要进用户
眼睛：前者是投递记录里那一笔的渠道（面板上「投在哪个网站，那边回不回」
那张表按它分组），后者是话术抬头那句「…的聊天框」，用户整段粘出去。

`export_web_data.PORTAL_NAMES` 与 `query_yield.PORTAL_ALIAS` 则是另一对：
**键域完全相同**（都在问「这个内部键是哪一家」），值一个是长名、一个是短名。
分头维护已经漏过两次，两处注释各自记着：

    2026-08-19  用浏览器扩展抓的 115 个岗 portal 写成 `*-browser`，不在表里，
                面板上全显示成「某招聘网站」
    历史写法    直接写中文名的那几个，`query_yield` 早就认了，export 那边漏了

**两次都是一边补、一边没补。**

## 现在的分工

- `_cli.PORTAL_DISPLAY`：短名 → 给用户看的名字。短名留作键（`PORTAL_FACTS`
  的键落在 `job_scraper/portals.json` 里，是用户勾选的偏好，改不得），
  长名留给屏幕。
- `_cli.PORTAL_HOSTS` + `portal_of_url`：链接 → 长名。
- `query_yield.PORTAL_ALIAS`：内部键 → 短名。
- `export_web_data.PORTAL_NAMES`：上面两张**合成**出来，自己不存键。
"""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import _cli  # noqa: E402
import export_web_data as ex  # noqa: E402
import outreach_header as oh  # noqa: E402
import query_yield as qy  # noqa: E402
import tracker as tk  # noqa: E402


class OneTableForTheKeys(unittest.TestCase):

    def test_the_display_map_covers_every_producer(self):
        """两个上游都只能归到登记过的家。

        别名那一半其实**塌不下来**：`PORTAL_NAMES` 的合成会在 import 期就
        KeyError，比这条早、也比这条响（变异实测：删掉一家，整个模块加载失败）。
        真正要这条盯的是**域名那一半** —— `portal_of_url` 只在真有那个域名的
        链接进来时才查表，加一条归到没登记的家，要等到那天才炸。"""
        homes = (set(qy.PORTAL_ALIAS.values())
                 | {s for _h, s in _cli.PORTAL_HOSTS})
        self.assertEqual(homes - set(_cli.PORTAL_DISPLAY), set(),
                         "归到了一个没登记显示名的家")

    def test_the_names_are_not_a_second_key_table(self):
        """`PORTAL_NAMES` 的键域**就是** `PORTAL_ALIAS` 的，一个不多一个不少。

        钉的是这个等式，不是「它那一行长什么样」——换个写法合成照样过，
        而手抄一个键进去当场红。
        """
        self.assertEqual(set(ex.PORTAL_NAMES), set(qy.PORTAL_ALIAS),
                         "内部键又分了两处住址：" + repr(
                             sorted(set(ex.PORTAL_NAMES)
                                    ^ set(qy.PORTAL_ALIAS))))

    def test_every_key_maps_to_the_same_family_both_ways(self):
        for k, short in qy.PORTAL_ALIAS.items():
            with self.subTest(k=k):
                self.assertEqual(ex.PORTAL_NAMES[k],
                                 _cli.PORTAL_DISPLAY[short])

    def test_the_families_are_spelled_one_way_on_screen(self):
        """短名与长名各自只有一套 —— 短名当键，长名上屏。"""
        self.assertEqual(sorted(_cli.PORTAL_DISPLAY),
                         sorted(qy.PORTALS))
        self.assertEqual(len(set(_cli.PORTAL_DISPLAY.values())),
                         len(_cli.PORTAL_DISPLAY),
                         "两家平台共用了一个显示名")


class OneTableForTheHosts(unittest.TestCase):

    def test_the_two_readers_agree(self):
        """同一个链接，投递记录那侧与抬头那侧必须给同一个名字。

        这一条原来不成立：`zhaopin.com` 一边「智联招聘」、一边「智联」。
        """
        for host, _short in _cli.PORTAL_HOSTS:
            with self.subTest(host=host):
                u = f"https://www.{host}/job/1.html"
                self.assertEqual(tk.channel_of({"source": u}),
                                 oh.portal_of(u))

    def test_it_answers_with_the_screen_name(self):
        self.assertEqual(_cli.portal_of_url("https://www.zhaopin.com/x"),
                         "智联招聘")
        self.assertEqual(_cli.portal_of_url("HTTPS://WWW.ZHIPIN.COM/x"),
                         "BOSS 直聘", "域名要不分大小写")
        self.assertEqual(_cli.portal_of_url("https://example.com/x"), "",
                         "认不出就交回空串，别猜一家")

    def test_a_hand_written_channel_still_wins(self):
        """`channel` 列填过的以用户为准 —— 推只是兜底。"""
        self.assertEqual(
            tk.channel_of({"channel": "内推", "source": "https://liepin.com/a"}),
            "内推")

    def test_no_module_keeps_its_own_host_table(self):
        """两份副本别再长回来。判据是**构造**，不是某一行的样子。"""
        for name in ("tracker.py", "outreach_header.py"):
            src = (ROOT / "tools" / name).read_text(encoding="utf-8")
            with self.subTest(name=name):
                for host, _s in _cli.PORTAL_HOSTS:
                    self.assertNotIn(f'"{host}"', src,
                                     f"{name} 又自己写了一份域名表")


class TheLibraryResolves(unittest.TestCase):
    """库里真出现过的 portal 取值，一个都不许落进「某招聘网站」。"""

    def setUp(self):
        f = ROOT / ".active_user"
        if not f.is_file():
            self.skipTest("没有活动用户")
        user = f.read_text(encoding="utf-8").strip()
        self.vals = set()
        for base in ("seen_jobs.json", "archive.json"):
            p = ROOT / "users" / user / "job_scraper" / base
            if not p.is_file():
                continue
            seen = _cli.seen_of(json.loads(p.read_text(encoding="utf-8")))
            for e in seen.values():
                v = (e.get("portal") or "").strip()
                if v:
                    self.vals.add(v)
        if not self.vals:
            self.skipTest("库里一条 portal 都没有")

    def test_the_scan_sees_data(self):
        """**先证明扫到了东西。** 空集上「全都认得」永远为真。"""
        self.assertGreater(len(self.vals), 3,
                           f"只扫到 {len(self.vals)} 种取值，八成没读对")

    def test_every_stored_value_is_known(self):
        unknown = sorted(self.vals - set(ex.PORTAL_NAMES))
        self.assertEqual(unknown, [],
                         "库里这些 portal 值两张表都不认，面板上会显示成"
                         "「某招聘网站」：" + repr(unknown))


if __name__ == "__main__":
    unittest.main()
