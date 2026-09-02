# -*- coding: utf-8 -*-
"""看已投的那些时按投递时间排，不按分数。

用户 2026-08-13：「已投岗位应该按投递时间排序」。

同一张表服务两种用途，默认排序得跟着用途走：
  - 「还能投谁」→ 按分排。要挑先投哪个。
  - 「已经投了谁」→ 按时间排。分数对已经投掉的岗没有决策价值，
    那时人要找的是「我上周投的那个」。

两个坑，都实测踩过：

1. **antd Table 把排序状态存在自己内部**，只改 `defaultSortOrder` 不会让已经
   挂载的表重排——切到「已投递」之后仍是按分数降序。要给它一个随视图变的 `key`
   逼它重挂。
2. **页面上有两张 Shortlist**（主表 + 「可以考虑」折叠区）。只给第一张传
   `byDate`，第二张照旧按分排——一半对一半错，比全错更难发现。
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SL = (ROOT / "web" / "src" / "components" / "Shortlist.tsx").read_text(encoding="utf-8")
APP = (ROOT / "web" / "src" / "App.tsx").read_text(encoding="utf-8")


class AppliedViewSortsByDate(unittest.TestCase):

    def test_shortlist_takes_the_flag(self):
        self.assertIn("byDate?: boolean", SL)

    def test_it_sorts_on_the_data_source(self):
        """投递日期不是一列（挤在职位那格的角标里），挂不上列的 sorter，
        所以排序必须在数据源上做。"""
        self.assertIn("applied?.date", SL)
        self.assertIn("dataSource={rows}", SL,
                      "还在用原始 jobs 当数据源，排序不会生效")

    def test_same_day_falls_back_to_score(self):
        """一天投十几个是常事，同日期之间还得有个稳定次序。"""
        m = re.search(r"const rows = byDate(.+?);\n", SL, re.S)
        self.assertIsNotNone(m, "找不到那段排序")
        self.assertIn("score", m.group(1), "同一天投的没有次级排序，顺序会是随机的")

    def test_the_table_remounts_when_the_view_changes(self):
        """antd 的内部排序状态不会自己清掉——实测切过去仍按分数降序。

        钉的是**「key 随 byDate 变」这件事**，不是那一行长什么样。原来这里断言的是
        字面量 `key={byDate ? "by-date" : "by-score"}`，2026-08-18 窄屏布局要求
        key 里再带一个 `narrow`（撤掉分数列之后 antd 的排序状态同样要清），
        改成模板串就红了——而重挂这件事一点没变。**判据钉行为，不钉写法。**
        """
        m = re.search(r"key=\{([^}]*)\}", SL)
        self.assertIsNotNone(m, "Table 上找不到 key 了——切视图时排序状态会留在旧视图上")
        key = m.group(1)
        self.assertIn("byDate", key,
                      f"key 不再随 byDate 变：{key}——切到「已投递」仍会按分数降序排")
        self.assertRegex(key, r"by-date", f"key 里认不出两个分支：{key}")

    def test_it_would_catch_a_constant_key(self):
        """控制用例：key 写死成常量时，上面那条必须报。"""
        m = re.search(r"key=\{([^}]*)\}", 'key={"jobs"} rowKey="id"')
        self.assertNotIn("byDate", m.group(1),
                         "判据把一个写死的 key 当成随视图变的了")

    def test_both_tables_get_it(self):
        """页面上有两张 Shortlist，只传一张 = 一半对一半错。"""
        n = APP.count('byDate={funnel === "applied"}')
        self.assertEqual(n, APP.count("<Shortlist"),
                         f"只有 {n} 处传了 byDate，而页面上有 "
                         f"{APP.count('<Shortlist')} 张 Shortlist")


if __name__ == "__main__":
    unittest.main()
