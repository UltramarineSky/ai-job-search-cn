# -*- coding: utf-8 -*-
"""15 份定制简历全比主简历旧，而「打开定制简历 PDF」旁边一个字都没有。

导出器从 2026-08-22 起就在算这件事（`materials.resumeStale`），它自己的注释把
利害写得很清楚：

> `job-interview.md` Step 1 自己写着「`resume.pdf` 是**真正交出去的那份**，
> 面试官读的就是它们，这里准备的每一个论点都必须和它们的说法一致」。旧版意味着
> 他按现行资料准备的说法，和对方手上那张纸对不上 —— 而「说法前后一致」正是
> 背调和交叉面在查的东西。

**而面板一直没读它。** `types.ts` 里只有渠道那一层的 `resumeStale`（在线简历
多久没刷，是个天数），材料这一层的根本没声明 —— 所以按钮照常只写「打开定制
简历 PDF」，旁边什么都没有。实测 2026-08-31：15 个带定制 PDF 的岗，
**15 个全部**带着这个字段。

这和开场白那条警告是同一个道理：审计/导出算得出来的事，要报在**他要用这份
东西的那一下**，不是事后的一份清单。

## 两个 `resumeStale` 不是一件事

| 在哪 | 类型 | 说的是 |
|---|---|---|
| `Portal.resumeStale` | 天数 | 招聘网站上挂着的那份多久没刷 |
| `Materials.resumeStale` | 日期串 | **已经交出去的**那张纸比主简历旧，主简历改于哪天 |

混起来会让人以为「刷一下在线简历」就解决了 —— 而要重出的是定制 PDF。
"""
import json
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

EX = (ROOT / "tools" / "export_web_data.py").read_text(encoding="utf-8")
TYPES = (ROOT / "web" / "src" / "types.ts").read_text(encoding="utf-8")
SHEET = (ROOT / "web" / "src" / "components"
         / "JobReadout.tsx").read_text(encoding="utf-8")


class TheExporterStillComputesIt(unittest.TestCase):
    def test_it_compares_against_the_master_resume(self):
        self.assertIn('mats["resumeStale"]', EX, "导出器不再算这件事")
        i = EX.index('mats["resumeStale"]')
        seg = EX[max(0, i - 600):i]
        self.assertIn('"resume" / "main.typ"', seg,
                      "比的不是主简历 —— 那这个「旧」没有参照物")

    def test_the_reason_is_recorded_next_to_it(self):
        """不写下来，下一个人会把它当成可有可无的装饰删掉。"""
        i = EX.index('mats["resumeStale"]')
        seg = " ".join(EX[max(0, i - 1400):i].split())
        self.assertIn("面试官读的就是它们", seg)


class ThePanelSaysItWhereThePdfIs(unittest.TestCase):
    def test_the_type_declares_the_materials_one(self):
        """材料那一层是**日期串**，渠道那一层是天数 —— 两个都要在，且不混。"""
        self.assertIn("resumeStale?: string;", TYPES,
                      "材料层的没声明 —— 面板读不到")
        self.assertIn("resumeStale?: number;", TYPES,
                      "渠道层的那个被误删了")

    def test_it_renders_next_to_the_button(self):
        # **锚代码构造，不锚显示串。** 第一版用「打开定制简历 PDF」当锚，
        # 而那几个字在**我自己写的那段注释里**又出现了一次 ——
        # 「断言撞上解释自己的文字」是这个仓库的常客，上面那条唯一性
        # 断言当场把它拦下了。
        anchor = "href={m.resumePdf}"
        self.assertEqual(SHEET.count(anchor), 1, "锚点不唯一，断言会落在别处")
        i = SHEET.index(anchor)
        self.assertIn("m?.resumeStale", SHEET[i:i + 900],
                      "过时提示没挨着那个按钮")

    def test_it_is_conditional_not_always_on(self):
        """一条永远显示的提醒等于没有提醒（本仓库反复论证过的那个形状）。"""
        self.assertIn("{m?.resumeStale && (", SHEET,
                      "没按字段有没有值决定显不显示")

    def test_it_gives_the_command_to_fix_it(self):
        """`AGENTS.md`「每一处引导都要写出该敲的命令」：说「旧了」不够。"""
        i = SHEET.index("m?.resumeStale")
        self.assertIn("/job-cv", SHEET[i:i + 500],
                      "只说旧了，没说该敲什么")


class TheSignalIsReal(unittest.TestCase):
    """有语料时验一次 —— 这条提示不是凭空加的。"""

    def _jobs(self):
        p = ROOT / "web" / "public" / "data.json"
        if not p.is_file():
            self.skipTest("还没导出过面板数据")
        return json.loads(p.read_text(encoding="utf-8"))["jobs"]

    def test_some_custom_resumes_are_actually_stale(self):
        pdfs = [j for j in self._jobs() if (j.get("materials") or {}).get("resumePdf")]
        if not pdfs:
            self.skipTest("这份语料里没有定制简历 PDF")
        stale = [j for j in pdfs if (j.get("materials") or {}).get("resumeStale")]
        self.assertTrue(
            stale,
            f"{len(pdfs)} 份定制简历一份都不算旧 —— 要么真都跟上了（那很好），"
            "要么算它的那段坏了。这条报出来是为了让人去看一眼，不是失败。")

    def test_the_value_is_a_date_not_a_count(self):
        for j in self._jobs():
            v = (j.get("materials") or {}).get("resumeStale")
            if v is None:
                continue
            with self.subTest(str(j.get("title"))[:16]):
                self.assertRegex(str(v), r"^\d{4}-\d{2}-\d{2}$",
                                 "材料层这个是主简历的修改日期，不是天数")
            break


if __name__ == "__main__":
    unittest.main()
