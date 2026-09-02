# -*- coding: utf-8 -*-
"""导出器算了、面板不读 —— 那份数据只是在盘上，没到过任何人眼前。

仓库里早有这条规则的**另一半**：`test_the_panel_reads_keys_that_are_written`
盯的是「导出方读了没人写的键」（`or ""` 会把它兜成空串，静默印到屏幕上）。
这一份盯反方向：**写进 `data.json`、而面板一处都不提的字段**。

## 为什么这一半也要有

它不会让屏幕上出现错的东西，它让**该出现的东西不出现** —— 更难发现，因为
页面看起来一切正常。2026-08-31 实测抓到一个，而且赌注不小：

    materials.resumeStale   15 个岗有值，面板 0 处引用

那个字段的意思是「这份**已经交出去的**定制简历比主简历旧」。导出器从
2026-08-22 起就在算它，注释里把利害写得很清楚（`job-interview.md`：
「`resume.pdf` 是真正交出去的那份，面试官读的就是它们」）。而面板给这 15 个岗
渲染着「打开定制简历 PDF」的按钮，旁边一个字都没有。

读不到的原因很具体：`types.ts` 里只有**渠道那一层**的同名字段（是个天数），
材料这一层的根本没声明 —— TypeScript 那一关就过不去，于是没人发现。

## 判据与它的边界

「面板里出现过这个名字」是个**弱代理**：出现在注释里也算数。它挡不住
「声明了但没渲染」，那种要靠各字段自己的守卫（例如
`test_the_custom_resume_says_it_is_stale` 钉的是「提示挨着那个按钮」）。
这一条只负责最粗的那一层：**别让一个字段完全没人知道**。

依赖真实数据（`data.json` 不进版本库），所以 CI 上会跳过 —— 与
`test_no_maintainer_data_in_repo` 同一档，本机跑那一遍才是这条的战场。
"""
import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]

#: 允许没人读的字段：值是理由。**这张表只许变短。**
#: 空表是目标状态 —— 2026-08-31 达成。
DELIBERATE: dict = {}


def _fields() -> dict:
    """`data.json` 里**有值**的字段 → (层级, 出现条数)。"""
    p = ROOT / "web" / "public" / "data.json"
    if not p.is_file():
        return {}
    d = json.loads(p.read_text(encoding="utf-8"))
    out: dict = {}

    def bump(level, key):
        out[key] = (level, out.get(key, (level, 0))[1] + 1)

    for j in d.get("jobs") or []:
        for k, v in j.items():
            if v not in (None, "", [], {}):
                bump("job", k)
        m = j.get("materials")
        if isinstance(m, dict):
            for k, v in m.items():
                if v not in (None, "", [], {}):
                    bump("materials", k)
    for k, v in d.items():
        if k != "jobs" and v not in (None, "", [], {}):
            bump("top", k)
    return out


class EveryExportedFieldIsRead(unittest.TestCase):

    def setUp(self):
        self.fields = _fields()
        if not self.fields:
            self.skipTest("还没导出过面板数据 —— 这条这次什么都没验，不是通过")
        self.web = "\n".join(
            f.read_text(encoding="utf-8")
            for f in (ROOT / "web" / "src").rglob("*.ts*"))

    def test_the_scan_sees_the_payload(self):
        """先证明它会亮：字段少得离谱时，下面那条会在空集上永远绿。"""
        self.assertGreater(len(self.fields), 50,
                           f"只扫到 {len(self.fields)} 个字段，导出八成不完整")
        self.assertGreater(len(self.web), 50_000, "web/src 一个文件都没读到")

    #: 材料那一层**必须以 `m.` / `m?.` 的形式被访问**。
    #:
    #: 光看「名字在 web/src 里出现过」不够：渠道那一层有个同名的
    #: `resumeStale`（是个天数），于是材料层那个即使没人读也看不出来 ——
    #: **恰恰是催生这条守卫的那个案例本身**。变异当场照出来：把面板对
    #: `m.resumeStale` 的引用全改名，这条一声不响。
    #:
    #: 这条规则对现有 11 个材料字段全部成立（2026-08-31 实测），
    #: 而 `snap` 那一层有解构写法（`const { pipeline, … } = snap`），
    #: 所以只对材料层收紧，别处仍按名字判。
    def _read(self, level: str, key: str) -> bool:
        import re

        if level == "materials":
            return bool(re.search(r"\bm\??\." + re.escape(key) + r"\b", self.web))
        return key in self.web

    def test_no_field_is_written_that_nothing_reads(self):
        orphans = sorted(
            f"{lvl}.{k}（{n} 条）"
            for k, (lvl, n) in self.fields.items()
            if not self._read(lvl, k) and k not in DELIBERATE)
        self.assertEqual(
            orphans, [],
            "导出器算了这些字段，面板一处都不提 —— 数据在盘上、断在最后一层：\n  "
            + "\n  ".join(orphans))

    def test_the_ledger_only_shrinks(self):
        """例外表里的字段得还在数据里 —— 不在了就该把这一行删掉。"""
        stale = [k for k in DELIBERATE if k not in self.fields]
        self.assertEqual(stale, [],
                         f"这些例外指向的字段已经不存在了，删掉它们：{stale}")


if __name__ == "__main__":
    unittest.main()
