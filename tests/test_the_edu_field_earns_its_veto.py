# -*- coding: utf-8 -*-
"""「学历字段够不够格结案」那道门槛，一条测试都没有。

`audit_pipeline.EDU_KILL_CEILING = 0.20` 决定 `check_edu_field_cannot_close`
什么时候开口。它的极性和别的检查相反 —— **误杀率低于门槛时才报**，报的是
「当初定『只降权』的依据变了，该重新裁定」。

定义处记着两次实测：「12 个样本时是 58%，1485 份 JD 复核后是 60%；两次都远超
阈值。」也就是说这条今天是沉默的，而它沉默得对。

## 没人钉它的话

    调到 0.9  → 这条永远开口，说「误杀率降下来了」，而实测是 60% ——
                一句和事实相反的话，还带着「该重新裁定」的动作
    调到 0    → 它永远闭嘴；哪天误杀率真降下来了，也没人会知道

变异实测（2026-09-01）：把 0.20 改成 0.9，全量 7107 条测试**一条都不红**。

## 判据

喂构造语料，比例和个数**写死**（不从常量现算 —— 那等于让它自己给自己出题，
`test_archive_keeps_walls_down` 刚踩过这一脚）：

    40 个命中里误杀  8（20%，正好在门槛上）→ 开口
    40 个命中里误杀  9（22%）              → 闭嘴
    20 个命中里误杀  4（20%，门槛之内）    → 闭嘴（样本不够 30，说不出话）

最后那一条的比例**必须落在门槛之内**，否则它测的还是门槛、不是样本闸门 ——
第一版写的是 20 个里误杀 10（50%），把 `fires < 30` 整条撤掉它照样闭嘴。
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import audit_pipeline as ap  # noqa: E402

#: 够长的 JD 正文（要过 `_cli.JD_MIN_BODY` 那道门，否则这一条整个跳过）。
_BODY = "岗位职责：" + "负责产品设计与落地。" * 12
#: 正文里明写硬性硕士要求 —— 这种不算误杀。
_HARD = _BODY + "学历要求：硕士及以上。"


def _corpus(n, killed):
    """`n` 个「字段写着硕士」的岗，其中 `killed` 个正文并没有硬性要求。"""
    seen, details = {}, {}
    for i in range(n):
        url = f"https://x/{i}"
        seen[f"k{i}"] = {"url": url, "title": f"岗{i}", "company": "c",
                         "eduLevel": "硕士"}
        details[url] = {"description": _BODY if i < killed else _HARD}
    return seen, details


class TheCeilingDecidesWhenItSpeaks(unittest.TestCase):

    def _fires(self, n, killed):
        return bool(ap.check_edu_field_cannot_close(*_corpus(n, killed)))

    def test_exactly_at_the_ceiling_it_speaks(self):
        """20% 正好在门槛上 —— 边界要算「降下来了」。"""
        self.assertTrue(self._fires(40, 8),
                        "误杀率降到门槛了却不吭声 —— 规则和它的理由脱节没人知道")

    def test_just_above_the_ceiling_it_stays_quiet(self):
        self.assertFalse(self._fires(40, 9),
                         "22% 还高于门槛，却说「降下来了」—— 那是句假话")

    def test_a_small_sample_says_nothing(self):
        """20 个样本、误杀率正好 20%，照样闭嘴 —— 样本不够 30 说不出话来。

        这一条和门槛是**两道**闸：少了它，一个只命中 3 个岗的库
        就能得出「误杀率 0%」并催人重新裁定。

        ⚠️ **样本要落在门槛之内才测得出这道闸。** 第一版用的是 20 个里误杀 10
        （50%）—— 那本来就超门槛，把样本闸门整个撤掉它照样闭嘴，变异当场
        证明这一条空转。
        """
        self.assertFalse(self._fires(20, 4))

    def test_it_says_the_number_it_compared_against(self):
        """报文里要有那两个数，否则读的人没法判断这个结论可不可信。"""
        rows = ap.check_edu_field_cannot_close(*_corpus(40, 8))
        msg = rows[0][2]
        self.assertIn("40 个命中", msg)
        self.assertIn("20%", msg)
        self.assertIn("58%", msg, "没说当初定规则时那个数是多少")


class TheReasonIsWrittenDown(unittest.TestCase):

    def test_the_two_measurements_are_recorded(self):
        src = (ROOT / "tools" / "audit_pipeline.py").read_text(encoding="utf-8")
        i = src.index("EDU_KILL_CEILING = ")
        seg = " ".join(src[max(0, i - 300):i].split())
        self.assertIn("1485", seg, "那个数没留下第二次复核的样本量")
        self.assertIn("58%", seg, "没留下当初定规则时的那个数")


if __name__ == "__main__":
    unittest.main()
