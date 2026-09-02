# -*- coding: utf-8 -*-
"""抓取器没给猎头标记时，**别印成「企业直招」**。

`via_headhunter` 原来是 `bool(entry.get("isHeadhunter"))` —— 字段不在就是 `False`。
实测活动用户 2026-08-22：2638 个岗里 **66 个没有这个字段**（集中在浏览器抓的
BOSS / 智联 / 前程），它们全被印成「企业 HR 直招」。

**缺数据只是少一条信息，印反了是给错误的信息** —— 这句话就写在 `via_headhunter`
自己的文档里，记的是 1358 个猎头岗被印成直招的那次事故。同一个函数，同一类错，
换了个入口。

而这枚标记现在是有分量的：

- 短名单上「（企业直招）」是**内推够得着**的信号（「标少数不标多数」那一档）；
- 零回音诊断拿它分猎头/直招的分母（「直招那 22 个也是 0 回音，这批才是信号」）；
- `namedDirectInRest` 拿它数「下面那一档里有几个找得到人」。

把一个没判过的岗算进直招，等于让他去一个可能是猎头挂的岗上找内部人。
"""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import export_web_data as X  # noqa: E402


def _code(path: str) -> str:
    t = (ROOT / path).read_text(encoding="utf-8")
    return re.sub(r"\{/\*[\s\S]*?\*/\}|/\*[\s\S]*?\*/|^\s*//.*$", "", t, flags=re.M)


class TheFlagIsTriState(unittest.TestCase):
    def test_missing_field_is_unknown_not_false(self):
        self.assertIsNone(X.via_headhunter({"title": "某岗"}),
                          "没这个字段却给了确定的答案")

    def test_present_field_still_decides(self):
        self.assertIs(X.via_headhunter({"isHeadhunter": True}), True)
        self.assertIs(X.via_headhunter({"isHeadhunter": False}), False)

    def test_the_recruiter_words_still_win(self):
        """招聘方名字里带中介词的，不管字段在不在都算猎头 —— 这条判据不能弱。"""
        self.assertIs(X.via_headhunter({"recruiter": "某某猎头顾问"}), True)


class NobodyTreatsUnknownAsDirect(unittest.TestCase):
    def test_the_row_marker_stays_silent(self):
        s = _code("web/src/components/Shortlist.tsx")
        self.assertIn('job.viaHeadhunter === false && "（企业直招）"', s,
                      "又拿真值判断给没判过的岗贴「企业直招」了")
        self.assertIn('job.viaHeadhunter === true && "（猎头代招）"', s)

    def test_the_header_count_excludes_unknown(self):
        s = _code("web/src/components/Shortlist.tsx")
        self.assertIn("j.viaHeadhunter === true", s, "表头计数把没判过的算进去了")

    def test_the_readout_says_it_did_not_judge(self):
        """逐岗详情里要如实说「没判」，不是二选一硬选一个。"""
        s = _code("web/src/components/JobReadout.tsx")
        self.assertIn("job.viaHeadhunter == null", s, "详情页还在二选一")
        self.assertIn("没判是猎头还是直招", s, "没说出「没判过」这个状态")

    def test_the_referral_count_excludes_unknown(self):
        """「找得到人的岗」必须确定不是猎头挂的 —— 那正是没判的那件事。"""
        s = _code("web/src/App.tsx")
        self.assertIn("j.viaHeadhunter === false && !j.anonymousEmployer", s,
                      "内推那个数把没判过的算成了具名直招")

    def test_the_split_counts_skip_unknown(self):
        src = (ROOT / "tools" / "export_web_data.py").read_text(encoding="utf-8")
        i = src.index('n_agency[0] += 1')
        self.assertIn('j.get("viaHeadhunter") is None', src[i:i + 400],
                      "猎头/直招的分母把没判过的算进了直招那边")


if __name__ == "__main__":
    unittest.main()
