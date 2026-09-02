# -*- coding: utf-8 -*-
"""「同岗重复挂牌.md」写了 16 份，而没有任何一处读它。

自动去重的键是「公司名 + JD 正文前 300 字」，所以**同文不同名**的一律不并——
那条裁定是对的，导出器自己写着理由：机器分不清「一个岗两家猎头代招」和
「两家公司套同一份模板」，而这两种的下一步正好相反。它只把同组的标出来（`sameJd`）。

**人这一环早就有答案。** 认出是重复挂牌时，那个目录里只留 `posting.md` +
一份 `同岗重复挂牌.md`（指向主贴），不出评估也不出话术 —— `job-apply.md` 对
重复挂法给的就是这个形状，语料里已经有 16 份。

写下来了，却没人读。于是那些目录在面板上仍各占一行，还挂着「没材料」：
实测活动用户 2026-08-26，「可以投的岗位」5 行里 **2 行是这种**，
用户直接问「为什么还是出现没资料的情况」。**材料在主贴那边，一份都没少。**

读了之后：5 行 → 3 行，全部有材料。

## 判据收得很紧

只认那一个形状：目录里**既没有 `evaluation.md` 也没有 `outreach.md`**，
**且**指路文件里那个 `` `<目录名>/evaluation.md` `` 解析得到、指向另一个真实的岗。
任一条不满足就不动 —— 自己有评估的那几份（语料里 3 份）是有人**特意**分开评的，
归并等于把他做过的判断抹掉。
"""
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import _cli  # noqa: E402
from build_dashboard import find_applications  # noqa: E402

EXP = (ROOT / "tools" / "export_web_data.py").read_text(encoding="utf-8")


class TheExporterReadsTheNote(unittest.TestCase):
    def test_it_looks_for_the_file(self):
        self.assertIn("同岗重复挂牌.md", EXP, "导出器根本没找这份文件")

    def test_it_only_merges_the_bare_shape(self):
        """自己有评估或话术的不许并 —— 那是有人特意分开评的。"""
        i = EXP.index("人已经判过的那批")
        seg = EXP[i:i + 2600]
        self.assertIn('(d / "evaluation.md").is_file()', seg, "没排除自带评估的目录")
        self.assertIn('(d / "outreach.md").is_file()', seg, "没排除自带话术的目录")

    def test_it_refuses_to_point_at_itself_or_a_dup(self):
        """自指会让这一行凭空消失；接到另一条重复挂牌上会成环。"""
        i = EXP.index("人已经判过的那批")
        seg = EXP[i:i + 2600]
        self.assertIn("cand is not me", seg, "没挡住自指")
        self.assertIn('not cand.get("dupOf")', seg, "没挡住接到另一条重复挂牌上")

    def test_the_automatic_rule_is_untouched(self):
        """**上面那条「同文不同名不归并」一个字都不改。** 这里加的是人的判断，
        不是把机器的判据放宽。"""
        self.assertIn("不归并 —— 可能是同一个岗两家猎头在代招", EXP)
        self.assertIn('j["sameJd"]', EXP, "sameJd 那条被顺手删了")


class OnRealDataItPointsSomewhereUseful(unittest.TestCase):
    """现算：每一条被归并的，主贴都得真的有材料 —— 否则只是把问题藏起来。"""

    def _load(self):
        f = ROOT / "web" / "public" / "data.json"
        au = ROOT / ".active_user"
        if not f.is_file() or not au.is_file():
            self.skipTest("还没导出过面板数据")
        jobs = json.loads(f.read_text(encoding="utf-8")).get("jobs") or []
        apps = (ROOT / "users" / au.read_text(encoding="utf-8").strip()
                / "documents" / "applications")
        if not apps.is_dir():
            self.skipTest("还没有投递目录")
        return jobs, apps

    def _noted(self, apps):
        out = set()
        for a in find_applications(apps):
            d = apps / a["dir"]
            if ((d / "同岗重复挂牌.md").is_file()
                    and not (d / "evaluation.md").is_file()
                    and not (d / "outreach.md").is_file() and a.get("url")):
                out.add(_cli.norm_url(a["url"]))
        return out

    def test_every_merged_one_has_a_primary_with_materials(self):
        jobs, apps = self._load()
        noted = self._noted(apps)
        if not noted:
            self.skipTest("这个用户还没标过重复挂牌")
        by_id = {j["id"]: j for j in jobs}
        bad = []
        for j in jobs:
            if not j.get("dupOf"):
                continue
            if _cli.norm_url(j.get("url") or "") not in noted:
                continue
            p = by_id.get(j["dupOf"])
            if p is None:
                bad.append(f"{j.get('company')} 的主贴 id 在快照里查无此岗")
            elif not p.get("materials"):
                bad.append(f"{j.get('company')} 归到了一个自己也没材料的主贴上")
        self.assertEqual(bad, [], "归并把问题藏起来了：\n  " + "\n  ".join(bad))

    def test_the_sellable_list_has_no_materials_gap_from_duplicates(self):
        """**用户看见的那个症状。** 「可以投的岗位」里不许再有重复挂牌占位。"""
        jobs, apps = self._load()
        noted = self._noted(apps)
        if not noted:
            self.skipTest("这个用户还没标过重复挂牌")
        rows = [j for j in jobs
                if not j.get("dupOf") and not j.get("skipped")
                and not j.get("expired") and not j.get("applied")
                and any(k in (j.get("verdict") or "") for k in ("强匹配", "值得投"))]
        leaked = [j.get("company") for j in rows
                  if _cli.norm_url(j.get("url") or "") in noted]
        self.assertEqual(leaked, [], f"标过的重复挂牌还在可投名单里占行：{leaked}")


if __name__ == "__main__":
    unittest.main()
