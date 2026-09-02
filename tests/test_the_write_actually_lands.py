# -*- coding: utf-8 -*-
"""写盘的那一步**真的落了盘**——判据自己失效的又一种形状。

## 怎么发现的

2026-08-21 拿变异扫了一遍全部 14 处写盘点：**把那一行换成 `pass`，再跑全套**。
绿 = 这条写路径可以静默空转而无人发现。结果 11 红 3 绿，三个绿是：

| 处 | 静默不写的后果 |
|---|---|
| `portal_budget.py` 的 `--block` | **冷却从来没被记下**，下一条命令直接撞进限流／风控。账号是用户的 |
| `query_yield.py --apply` | `/job-auto` 每轮补货后都要跑它；不落盘就用同一批挖空的词反复抓十几轮 |
| `applied_jds.py --apply` | 说「清单已写到 …」，而那个文件不存在 |

三处此前都有测试，**测的全是它算得对不对**：`query_yield` 有 15 条判据盯 schema、
归并、格式、城市不写死；`test_writes_are_atomic` 盯的是「写得原不原子」。
**没有一条盯「写没写」。** 算对了却没落盘，对用户是纯粹的静默失败——
命令报成功，下次打开什么都没变。

> 同一天在面板解封按钮上栽过同一个形状，而且更隐蔽：那条判据本来是活的，
> 是换存储字段名之后**静默变成恒真**的（见 `test_status_from_the_page`
> 里那段注释）。**「换掉一个字段名」和「删掉一条判据」后果相同。**

## 这个文件只做一件事

每条都：搭一个临时用户 → 跑真正的命令行入口 → **从盘上重新读回来**。
不看返回值、不看打印，只看盘。
"""

import datetime as dt
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import portal_budget as pb  # noqa: E402


class _TempUser(unittest.TestCase):
    """每条判据自己一套临时目录 —— 绝不碰真实用户的数据。

    `tools/fetch_details.py` 的说明里记着这一课的反面：测试造出一个
    `users/张三/`，下一次跑测试时它还在。
    """

    USER = "写盘判据"

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "users" / self.USER / "job_scraper").mkdir(parents=True)
        (self.tmp / "users" / self.USER / "profile").mkdir(parents=True)
        (self.tmp / ".active_user").write_text(self.USER, encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)


class BlockingASiteLandsOnDisk(_TempUser):
    def test_block_persists(self):
        """**这是仓库里最要命的一处写盘。**

        不落盘 = 冷却从来没被记下 = 下一条命令直接撞进限流。
        而撞的是用户的账号，封号后果他担。
        """
        saved = pb.ROOT
        pb.ROOT = self.tmp
        try:
            rc = pb.main(["--block", "liepin-search", "--why", "撞了限流",
                          "--user", self.USER])
            self.assertEqual(rc, 0)
            # **重新从盘上读**——`main()` 手里那份内存对象说了不算。
            st = pb.block_state(pb.load(self.USER), "猎聘", dt.datetime.now())
            self.assertTrue(st["blocked"], "说封了，盘上没有——下一条命令会直接撞上去")
            self.assertEqual(st["why"], "撞了限流")
        finally:
            pb.ROOT = saved

    def test_clear_persists_too(self):
        """解封同理：说解开了而盘上还封着，用户会一直以为工具坏了。"""
        saved = pb.ROOT
        pb.ROOT = self.tmp
        try:
            pb.main(["--block", "liepin-search", "--why", "x", "--user", self.USER])
            pb.main(["--clear", "liepin-search", "--user", self.USER])
            st = pb.block_state(pb.load(self.USER), "猎聘", dt.datetime.now())
            self.assertFalse(st["blocked"], "说解开了，盘上还封着")
        finally:
            pb.ROOT = saved


class AppliedListLandsOnDisk(_TempUser):
    def test_the_list_file_really_appears(self):
        """`--apply` 打印「清单已写到 …」，那个文件就必须真的在那儿。"""
        import applied_jds

        # **字段名照真实文件抄，别照记忆写。** `seen_jobs.json` 有 `seen` 外层；
        # tracker 的列是 `date,company,…,role,…,source`——链接在 `source`、
        # 岗位名在 `role`。第一版凭印象写成 `company,title,url,…`，
        # 匹配不上、一个投过的岗都找不到，判据于是「通过」了个空集。
        seen = {"seen": {"https://x.example/1": {
            "url": "https://x.example/1", "title": "某岗", "company": "某公司",
            "status": "ranked", "rank_score": 70, "rank_verdict": "值得投"}}}
        sj = self.tmp / "users" / self.USER / "job_scraper" / "seen_jobs.json"
        sj.write_text(json.dumps(seen, ensure_ascii=False), encoding="utf-8")
        (self.tmp / "users" / self.USER / "job_search_tracker.csv").write_text(
            "date,company,sector,role,role_type,channel,status,contact_person,"
            "fit_rating,notes,cv_file,cover_letter_file,source\n"
            "2026-08-01,某公司,,某岗,,,applied,,,,,,https://x.example/1\n",
            encoding="utf-8")

        # **两个 ROOT 都要改。** `applied_jds.gather()` 拿投过的键走的是
        # `archive.collect_applied_keys`，而那个函数按 **`archive.ROOT`** 找
        # tracker —— 只改 `applied_jds.ROOT` 的话，它照样去读真实仓库里那份，
        # 匹配不上，判据「通过」了个空集。
        import archive
        saved, saved_arc = applied_jds.ROOT, archive.ROOT
        applied_jds.ROOT = archive.ROOT = self.tmp
        try:
            rc = applied_jds.main(["--apply", "--user", self.USER,
                                   "--today", "2026-08-21"])
            self.assertEqual(rc, 0)
            out = (self.tmp / "users" / self.USER / "upskill"
                   / "applied-jds-2026-08-21.md")
            self.assertTrue(out.is_file(), "说清单写好了，盘上没有这个文件")
            body = out.read_text(encoding="utf-8")
            self.assertIn("某公司", body, "文件在，内容却是空的")
        finally:
            applied_jds.ROOT, archive.ROOT = saved, saved_arc


class QueryYieldWriteBackLands(_TempUser):
    def test_the_query_table_is_really_written(self):
        """`/job-auto` 每轮补货后都要跑它。不落盘，下一轮又用同一批挖空的词。

        写回的是 `search-queries.md` 里的**自动维护块**，其余部分
        （用户亲手校准的优先级）必须原样留着 —— 这一条一并盯。
        """
        import query_yield as qy

        sq = self.tmp / "users" / self.USER / "profile" / "search-queries.md"
        sq.write_text("# 搜索词\n\n## 我自己排的优先级\n\n- 手写的一行，不许动\n",
                      encoding="utf-8")
        sj = self.tmp / "users" / self.USER / "job_scraper" / "seen_jobs.json"
        # `found_by` 是**纯字符串**（那个搜索词本身），平台在另一个字段 `portal`。
        # 写成 `{"query":…, "portal":…}` 会让 `collect()` 在 `.strip()` 上直接炸。
        sj.write_text(json.dumps({"seen": {"https://x.example/1": {
            "url": "https://x.example/1", "title": "某岗", "company": "某公司",
            "status": "ranked", "rank_score": 70, "rank_verdict": "值得投",
            "found_by": "某搜索词", "portal": "猎聘"}}},
            ensure_ascii=False), encoding="utf-8")

        saved = qy.ROOT
        qy.ROOT = self.tmp
        try:
            before = sq.read_text(encoding="utf-8")
            rc = qy.main(["--apply", "--user", self.USER])
            self.assertEqual(rc, 0)
            after = sq.read_text(encoding="utf-8")
            self.assertNotEqual(after, before,
                                "说写回了，文件一个字没变——下一轮还会用挖空的词")
            self.assertIn("手写的一行，不许动", after,
                          "写回把用户亲手校准的部分吃掉了")
        finally:
            qy.ROOT = saved


if __name__ == "__main__":
    unittest.main()
