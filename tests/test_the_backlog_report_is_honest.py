# -*- coding: utf-8 -*-
"""「补不了的那批」和「各家现在能不能抓」这两份报告，要真的算得对。

2026-08-21 量行覆盖率时抓到的两个函数：都有测试**提到**它们的名字，
但那些断言做的是 `hasattr` 加源码文本比对——**函数体一次都没被执行过**。

| 函数 | 它回答什么 | 现有断言 |
|---|---|---|
| `fetch_details.missing_by_portal` | 缺 JD 的岗按渠道怎么分布 | `hasattr(fd, "missing_by_portal")` + 源码里有没有那句话 |
| `portal_budget.status_lines` | 各家现在能不能抓、今天用了几轮 | 无（那个同名命中是别的测试里的**局部变量**） |

第一个尤其要紧，它的实现里写着存在的理由：

> 「不报出来的话，跑完这个工具会显得『缺 JD 的都补了』，而实际差着三分之一。」

也就是说**它本身就是一条反「静默全覆盖」的守卫**——而这条守卫自己没人守。
算错了不会报错，只会让报告看起来更好看。
"""

import datetime as dt
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import _cli  # noqa: E402
import fetch_details as fd  # noqa: E402
import jd_store as st  # noqa: E402
import portal_budget as pb  # noqa: E402

BODY = "岗位职责：" + "把这件事做好并持续迭代。" * 40      # 够长，算「有正文」


def _job(url, portal, status="new"):
    return {"url": url, "title": "岗位", "company": "某公司",
            "portal": portal, "status": status}


class TheOutOfReachBacklogIsCountedRight(unittest.TestCase):
    """`missing_by_portal`：**真造一份职位库数一遍**，不是看它在不在。"""

    def _run(self, seen: dict, with_body: list[str]):
        tmp = Path(tempfile.mkdtemp())
        (tmp / "users" / "张三" / "job_scraper").mkdir(parents=True)
        (tmp / "users" / "张三" / "job_scraper" / "seen_jobs.json").write_text(
            json.dumps({"seen": seen}, ensure_ascii=False), encoding="utf-8")
        saved = (fd.ROOT, st.ROOT)
        fd.ROOT, st.ROOT = tmp, tmp
        try:
            for url in with_body:
                st.save("张三", {"url": url, "title": "岗位", "description": BODY})
            return fd.missing_by_portal("张三")
        finally:
            fd.ROOT, st.ROOT = saved

    def test_only_live_jobs_without_a_stored_body_are_counted(self):
        seen = {
            "u1": _job("https://x/1", "liepin"),                 # 缺正文 → 数
            "u2": _job("https://x/2", "liepin"),                 # 有正文 → 不数
            "u3": _job("https://x/3", "boss"),                   # 缺正文 → 数
            "u4": _job("https://x/4", "zhaopin", "expired"),     # 已下线 → 不数
            "u5": _job("https://x/5", "zhaopin", "skipped"),     # 不投 → 不数
        }
        got = self._run(seen, with_body=["https://x/2"])
        self.assertEqual(got, {"liepin": 1, "boss": 1},
                         f"按渠道分布算错了：{got}。"
                         "多算会把「补不了的」说多，少算会把它说成已经补齐")

    def test_a_store_with_bodies_everywhere_reports_nothing(self):
        """全都抓过时要**空**，而不是把它们照数一遍。"""
        seen = {"u1": _job("https://x/1", "liepin")}
        self.assertEqual(self._run(seen, with_body=["https://x/1"]), {})

    def test_a_short_stub_does_not_count_as_fetched(self):
        """只有 URL 和标题不算抓过 —— 否则 `/job-rank` 会拿一句话去打分。"""
        tmp = Path(tempfile.mkdtemp())
        (tmp / "users" / "张三" / "job_scraper").mkdir(parents=True)
        (tmp / "users" / "张三" / "job_scraper" / "seen_jobs.json").write_text(
            json.dumps({"seen": {"u1": _job("https://x/1", "liepin")}},
                       ensure_ascii=False), encoding="utf-8")
        saved = (fd.ROOT, st.ROOT)
        fd.ROOT, st.ROOT = tmp, tmp
        try:
            st.save("张三", {"url": "https://x/1", "title": "岗位",
                            "description": "招产品经理。"})     # 远短于 JD_MIN_BODY
            self.assertEqual(fd.missing_by_portal("张三"), {"liepin": 1},
                             f"几十个字的占位被当成抓过了"
                             f"（下限 {_cli.JD_MIN_BODY} 字）")
        finally:
            fd.ROOT, st.ROOT = saved

    def test_no_store_file_is_empty_not_a_crash(self):
        tmp = Path(tempfile.mkdtemp())
        saved = (fd.ROOT, st.ROOT)
        fd.ROOT, st.ROOT = tmp, tmp
        try:
            self.assertEqual(fd.missing_by_portal("查无此人"), {})
        finally:
            fd.ROOT, st.ROOT = saved


class TheSiteStatusLinesSayWhatIsBlocked(unittest.TestCase):
    """`status_lines`：每家一行，封着的那家要看得出来是封着的。"""

    NOW = dt.datetime(2026, 8, 21, 12, 0, 0)

    def test_every_site_gets_a_line_and_the_blocked_one_reads_blocked(self):
        data = {}
        pb.block(data, "猎聘", "撞了风控", self.NOW)
        lines = pb.status_lines(data, self.NOW)

        # 平台行一家一条；通道子行（`└`开头）另算 —— 见
        # `test_the_footnote_says_the_block_cleared` 里那条同名守卫的说明。
        top = [l for l in lines if not l.strip().startswith("└")]
        self.assertEqual(len(top), len(pb.PORTALS),
                         "少了一家就等于那家的状态没人报")
        lines = top
        blocked = [l for l in lines if "猎聘" in l]
        self.assertTrue(blocked, "封着的那家整行都不见了")
        self.assertIn("停", blocked[0], f"封着却读起来像能抓：{blocked[0]!r}")

        others = [l for l in lines if "猎聘" not in l]
        self.assertTrue(others, "只有一家？PORTALS 像是被清空了")
        self.assertTrue(all("可以抓" in l for l in others),
                        f"封一家把别家也说成停了：{others}")

    def test_a_clean_slate_reads_all_clear(self):
        lines = pb.status_lines({}, self.NOW)
        self.assertTrue(all("可以抓" in l for l in lines),
                        f"什么都没发生却说不能抓：{lines}")
        # 轮次那一栏 2026-08-26 随固定额度删了，换成「今天已发几次」——
        # 那是**读数**不是闸门，但它仍然要在，否则状态行看不出这家动过没有。
        self.assertTrue(all("今天已发 0 次" in l for l in lines),
                        f"今天一次都没发，读数却不是 0：{lines}")


if __name__ == "__main__":
    unittest.main()
