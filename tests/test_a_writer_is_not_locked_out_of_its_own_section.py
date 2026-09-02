# -*- coding: utf-8 -*-
"""填资料的命令，不许被挡在「资料填完了没」外面。

`AGENTS.md`「往 `candidate.md` 里写东西：小节名以模板为准」开头列了三个写手：

    /job-setup   建档
    /job-expand  挖经历
    /job-rank    待问清单的答案

而 `/job-expand` 的 Step 0 守卫原来守 `apply` 档 —— 那一档 `block` 的两节是
「明确的能力边界」和「职业目标」，**而这条命令自己就往前一节里写**
（Step 4 那张表：具体的项目 / 作品 / 案子 → 「明确的能力边界」下的
「作品与项目的分层」）。

也就是说：**填它的命令被挡在「它填完了没」外面。** 一个新用户答完
`/job-setup` 第二轮（那时工具对他说「够排序了」），想先从文档里挖一轮再回答
第三轮的「你明确不做/不会什么」—— `/job-expand` 会拒绝他，理由是第三轮没答。

改成守 `rank` 档：那是它**真正要的东西**（技能、工作经历、执业资格都在，
它才认得出哪些已经写进资料、不重复提）。「职业目标」它一个字都不读。

## 为什么不是一条一次性的措辞修正

四档的取值正本在 `doctor.STAGE_NEEDS`，七条工作流各自声明自己守哪一档 ——
声明错了不会有任何一处报错，只会在某个新用户身上变成一句「先去跑 /job-setup」。
这一条现算：**答完第二轮的人进不进得去 `/job-expand`**。

⚠️ **「档名存不存在」不归这里管。** `test_setup_asks_in_useful_order` 的
`TheCommandsGateByStageToo` 已经逐条验过了（还带自检），那张 `GATE_STAGE`
登记表也在那儿 —— 本文件第一版另写了一遍，当场就是第二个住址。
"""
import pathlib
import re
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import doctor  # noqa: E402

WF = ROOT / "workflows"
STAGE = re.compile(r'doctor\.profile_gaps\(udir,\s*"([a-z]+)"\)')


def declared() -> dict:
    """每条工作流声明自己守哪一档。"""
    out = {}
    for f in sorted(WF.glob("*.md")):
        m = STAGE.search(f.read_text(encoding="utf-8"))
        if m:
            out[f.stem] = m.group(1)
    return out


class AProfileWriterOpensAtItsOwnTier(unittest.TestCase):
    """`/job-expand` 往「明确的能力边界」里写，就不能等它先填好。"""

    #: 只填到第二轮（rank 档齐了），第三轮那两节还是占位符。
    ROUND_TWO_DONE = None

    def _udir(self, filled: bool):
        """造一份资料：`filled=False` 时 apply 档那两节留占位符。"""
        tmpl = (ROOT / "profile.example" / "candidate.md").read_text(
            encoding="utf-8")
        d = tempfile.mkdtemp()
        udir = pathlib.Path(d) / "users" / "甲"
        (udir / "profile").mkdir(parents=True)
        # 把每个占位符换成真值；`filled=False` 时留下 apply 档要的那两节。
        keep = set()
        if not filled:
            for _f, sec in doctor.STAGE_NEEDS["apply"]["block"]:
                keep.add(sec)
        out = []
        cur = ""
        for ln in tmpl.splitlines():
            if ln.startswith("## "):
                cur = ln[3:].strip()
            if cur not in keep:
                ln = re.sub(r"\[[A-Z_0-9]+\]", "真值", ln)
            out.append(ln)
        (udir / "profile" / "candidate.md").write_text(
            "\n".join(out), encoding="utf-8")
        return udir

    def test_the_fixture_really_splits_the_two_tiers(self):
        """**先证明夹具造对了。** 造不出「第二轮齐、第三轮没答」这个状态，
        下面两条就是在一个不存在的情形上断言。
        """
        udir = self._udir(filled=False)
        self.assertEqual(doctor.profile_gaps(udir, "rank")["block"], [],
                         "第二轮那几节没填满 —— 夹具没造对")
        self.assertTrue(doctor.profile_gaps(udir, "apply")["block"],
                        "第三轮那两节没留成占位符 —— 夹具没造对")

    def test_expand_opens_after_round_two(self):
        """这就是那个死锁：填它的命令被它自己挡住。"""
        udir = self._udir(filled=False)
        stage = declared()["job-expand"]
        self.assertEqual(
            doctor.profile_gaps(udir, stage)["block"], [],
            "答完第二轮还进不去 /job-expand —— 而它正是往第三轮那一节里写的")

    def test_it_still_needs_round_two(self):
        """反向支点：什么都没填时它照样该拦 —— 不然它认不出哪些是已有的。"""
        with tempfile.TemporaryDirectory() as d:
            udir = pathlib.Path(d) / "users" / "甲"
            (udir / "profile").mkdir(parents=True)
            (udir / "profile" / "candidate.md").write_text(
                (ROOT / "profile.example" / "candidate.md").read_text(
                    encoding="utf-8"), encoding="utf-8")
            stage = declared()["job-expand"]
            self.assertTrue(doctor.profile_gaps(udir, stage)["block"],
                            "一个字没填也放它进去了")

    def test_the_reason_is_written_next_to_the_gate(self):
        """改这一档的人要看得见为什么 —— 不然下次又被改回 apply。"""
        md = (WF / "job-expand.md").read_text(encoding="utf-8")
        head = md[:md.index("## Step 1")] if "## Step 1" in md else md[:6000]
        # **先剥引用标记再拼。** 那句话跨了行，中间隔着一个 `> ` ——
        # 直接 `" ".join(split())` 拼出来是「填它的命令 > 被挡在」，
        # 断言红在一个其实写着的句子上（第一版就是这么红的）。
        seg = " ".join(re.sub(r"^\s*>\s?", "", head, flags=re.M).split())
        seg = re.sub(r"(?<=[一-鿿]) +(?=[一-鿿])", "", seg)
        self.assertIn("填它的命令被挡在", seg, "那道门为什么在这一档，没写")


if __name__ == "__main__":
    unittest.main()
