"""`/job-setup` 的提问顺序，得和自检的分档是同一件事。

## 为什么会有这个文件

自检把资料的门改成了按步放行：填够搜岗的就去搜，填够排序的就去排，最费神的能力边界
和 STAR 等 `/job-apply`、`/job-interview` 真要用时再补。

**但光改门没用。** `/job-setup` 自己仍然照小节编号从 1 问到 10，而搜岗和排序真正需要的
东西（Section 10 的城市、关键词、薪资、硬门）排在最费神那一节（Section 9 能力边界的
诚实校准）**后面**。照编号问下来，用户还是先做完全部自我剖析才走到能搜岗的那一步——
门放开了，路没改，收益是零。

所以 `setup.md` 里写了一张四轮提问顺序表。而两张表分处两个文件、用两种语言（一份
Python 数据、一份中文流程），**迟早分叉**，分叉的样子是：自检说「还差『明确排除』」，
用户跑 `/job-setup`，那一轮根本不问它。

这个文件就是把两边钉在一起。

## 第三条腿 2026-08-31 才补上

上面那段写着「自检把资料的门改成了按步放行」—— **而命令自己的门没改。**
`job-rank` / `job-apply` / `job-interview` / `job-expand` / `job-resume` /
`job-offer` **六份**各抄了一句整份文件的判据（`profile_ready`：
「还剩任何一个占位符就算没填完」），照它走的结果是：

    第二轮问完 → 「够排序了 —— 跑 `/job-rank`」 → `/job-rank` 当场拒绝
    第三轮问完 → 「够出材料了」           → `/job-apply` 同样拒绝

**同一份文档一边发出邀请、一边把门关上。** 三条腿（提问顺序 / 自检分档 /
命令的门）少一条，前两条钉得再紧也没用。
"""

import re
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SETUP = REPO_ROOT / "workflows" / "job-setup.md"

sys.path.insert(0, str(REPO_ROOT / "tools"))
import doctor  # noqa: E402

#: 自检的阶段 → 顺序表里的第几轮。四轮四档，一一对应。
STAGE_ROUND = {"scrape": 1, "rank": 2, "apply": 3, "interview": 4}


def rounds() -> dict:
    """`{轮次: 那一轮的正文}`。找不到顺序表就返回空 dict，让测试报得明白。"""
    text = SETUP.read_text(encoding="utf-8")
    out, cur, buf = {}, None, []
    for line in text.splitlines():
        m = re.match(r"^####\s*第([一二三四])轮", line)
        if m:
            if cur:
                out[cur] = "\n".join(buf)
            cur = "一二三四".index(m.group(1)) + 1
            buf = [line]
            continue
        if cur:
            if re.match(r"^###\s", line):       # 顺序表结束
                out[cur] = "\n".join(buf)
                cur = None
                continue
            buf.append(line)
    if cur:
        out[cur] = "\n".join(buf)
    return out


class TheOrderExists(unittest.TestCase):

    def test_there_are_four_rounds(self):
        r = rounds()
        self.assertEqual(sorted(r), [1, 2, 3, 4],
                         f"setup.md 里的提问顺序不是四轮：{sorted(r)}")

    def test_it_says_not_to_follow_the_numbering(self):
        """这是整张表的要害：编号是给 `--section` 定位用的，不是提问顺序。"""
        text = SETUP.read_text(encoding="utf-8")
        head = text[text.index("## 路线 C"):]
        head = head[: head.index("### Section 1")]
        self.assertIn("不要照编号", head,
                      "路线 C 没说清「别按编号问」——那默认就会照编号问下来")


class EachRoundCollectsWhatThatStepNeeds(unittest.TestCase):
    """自检说某一步还差什么，`/job-setup` 对应那一轮就得真的问它。

    两边分处两个文件、写成两种东西（一份 Python 数据、一份中文流程），
    不钉住就会分叉——分叉的样子是自检报了一项，而那一轮根本不问。
    """

    def test_every_blocking_item_is_asked_by_its_round(self):
        rs = rounds()
        self.assertTrue(rs, "setup.md 里找不到提问顺序表")
        for stage, n in STAGE_ROUND.items():
            body = rs.get(n, "")
            for fname, title in doctor.STAGE_NEEDS[stage]["block"]:
                name = title or fname
                # 整份文件的那几项在表里按文件名写（`profile/interview-star.md`）
                needle = title if title else fname
                with self.subTest(stage=stage, item=name):
                    self.assertIn(
                        needle, body,
                        f"自检会拦着说「要{doctor.STAGE_LABEL[stage]}还差『{name}』」，"
                        f"而 setup 的第 {n} 轮不问它 —— 用户照做也补不上")

    def test_the_heavy_section_is_not_in_the_first_two_rounds(self):
        """能力边界是最费神的一节，放进前两轮就把这次改动的收益抵消掉了。"""
        rs = rounds()
        early = rs.get(1, "") + rs.get(2, "")
        self.assertNotIn(
            "Section 9", early,
            "能力边界那一节又被挪回搜岗/排序之前了 —— "
            "那用户还是得先做完自我剖析才能搜第一个岗")

    def test_each_round_tells_the_user_what_he_can_do_now(self):
        """每一轮都要给出停点和该敲的命令，否则他不知道自己已经能去搜岗了。"""
        rs = rounds()
        want = {1: "/job-scrape", 2: "/job-rank", 3: "/job-apply"}
        for n, cmd in want.items():
            with self.subTest(round=n):
                self.assertIn(cmd, rs.get(n, ""),
                              f"第 {n} 轮问完没告诉他现在能跑 {cmd}")


#: 每条命令的资料守卫该按哪一档判。值是 `STAGE_NEEDS` 的键。
#:
#: ⚠️ **`job-expand` 守 `rank`，不是 `apply` —— 2026-09-01 改的。**
#: `apply` 档 `block` 的两节是「明确的能力边界」和「职业目标」，而
#: `/job-expand` **自己就往前一节里写**（Step 4 那张表：具体的项目 / 作品 /
#: 案子 → 「明确的能力边界」下的「作品与项目的分层」）。守 `apply` 等于
#: 让填它的命令等自己的产出先到位 —— `AGENTS.md` 开头就把它列为写
#: `candidate.md` 的三个写手之一。完整判据见
#: `test_a_writer_is_not_locked_out_of_its_own_section`。
GATE_STAGE = {"job-rank.md": "rank", "job-apply.md": "apply",
              "job-interview.md": "interview",
              "job-expand.md": "rank", "job-resume.md": "apply",
              "job-offer.md": "rank", "job-scrape.md": "scrape"}


class TheCommandsGateByStageToo(unittest.TestCase):
    """命令的门 = 这一步真要的那几节，不是整份文件。"""

    def _text(self, name):
        return (REPO_ROOT / "workflows" / name).read_text(encoding="utf-8")

    def test_no_command_gates_on_the_whole_file(self):
        """整份文件那条判据一个字都不许再出现在工作流里。

        它是面板判「这个用户建过档没有」用的，比这里严得多 ——拿它当门，
        `/job-setup` 第二、三轮发出的邀请当场被挡在外面。"""
        bad = [f.name for f in sorted((REPO_ROOT / "workflows").rglob("*.md"))
               if "还剩任何一个就算没填完" in f.read_text(encoding="utf-8")]
        self.assertEqual(bad, [], "这几份又拿整份文件当门：" + repr(bad))

    def test_every_gate_names_a_real_stage(self):
        """门上写的档名要真在 `STAGE_NEEDS` 里 ——写错一个字，执行者只能自己猜。"""
        import re as _re
        seen = set()
        for f in sorted((REPO_ROOT / "workflows").rglob("*.md")):
            for st in _re.findall(r'profile_gaps\(udir, "([a-z]+)"\)', f.read_text(encoding="utf-8")):
                seen.add(st)
                with self.subTest(f=f.name, stage=st):
                    self.assertIn(st, doctor.STAGE_NEEDS,
                                  f"{f.name} 的门写了一个不存在的档名")
        # **先证明真扫到了门。** 一个都没有时上面那层循环整个不跑。
        self.assertGreaterEqual(len(seen), 2,
                                f"只扫到 {seen} —— 门八成没写档名")

    def _stage_in(self, name):
        """这份工作流的门**实际**写着哪一档；没写就 None。

        从文件里读，不从 `GATE_STAGE` 读 —— 变异实测：把 job-rank 的门
        改成按 apply 判，而下面那条照着自己那张表比，一声不响。
        判据要问真实的文件。"""
        import re as _re
        m = _re.search(r'profile_gaps\(udir, "([a-z]+)"\)', self._text(name))
        return m.group(1) if m else None

    def test_each_gated_command_names_its_own_stage(self):
        for name, st in GATE_STAGE.items():
            with self.subTest(name=name):
                self.assertEqual(
                    self._stage_in(name), st,
                    f"{name} 的资料守卫没按 {st} 那一档判")

    def test_the_rule_has_one_home(self):
        """规则写在 `AGENTS.md`，六份工作流指过去 ——不是各写一遍。"""
        ag = (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("资料没填完是分档的，不是一个整体判断", ag)
        for st in doctor.STAGE_NEEDS:
            with self.subTest(stage=st):
                self.assertIn(st, ag, f"那一节没列 {st} 这一档")

    def test_the_invitation_and_the_gate_agree(self):
        """第 N 轮请他去跑的那条命令，门不能比第 N 档更严。

        判据是**它写的档名不许比这一轮更靠后** ——靠后就意味着它在等
        用户还没被问到的东西。"""
        order = ["scrape", "rank", "apply", "interview"]
        rs = rounds()
        self.assertTrue(rs, "顺序表都没解析到，下面这条是空转")
        want = {1: "job-scrape.md", 2: "job-rank.md",
                3: "job-apply.md"}
        for n, name in want.items():
            with self.subTest(round=n):
                self.assertIn(want[n].split(".")[0], rs.get(n, ""),
                              f"第 {n} 轮没请他去跑 {name}")
                st = self._stage_in(name)
                self.assertIsNotNone(st, f"{name} 的门没写档名")
                self.assertLessEqual(
                    order.index(st), n - 1,
                    f"第 {n} 轮请他跑 {name}，而它按 {st} 那一档判 ——"
                    "那一档要的东西这一轮还没问到，他会被挡在门外")


class TheFirstScreenDoesNotPromiseAllOrNothing(unittest.TestCase):
    """「一次性，15-30 分钟」这句话不能再留着。

    分轮问的全部意义就是**不必一次答完**。而新用户读到的第一句仍然写着
    「它会问你一串问题（15-30 分钟，一次性）」——那句话会让人以为必须坐下来
    一口气做完自我剖析才准往下走，收益当场归零：他不会知道答三分钟就能去搜岗。

    这句话同时出现在自检的第一屏和 README 的快速开始里，两处都要说同一件事。
    """

    SURFACES = [
        ("自检第一屏", REPO_ROOT / "tools" / "doctor.py"),
        ("README 快速开始", REPO_ROOT / "README.md"),
    ]

    def test_no_surface_still_says_it_is_one_sitting(self):
        for label, path in self.SURFACES:
            text = path.read_text(encoding="utf-8")
            with self.subTest(surface=label):
                self.assertNotIn(
                    "一串问题（15-30 分钟，一次性）", text,
                    f"{label} 还在说一次性 —— 用户不会知道答三分钟就能去搜岗")

    def test_they_say_you_can_stop_early(self):
        for label, path in self.SURFACES:
            text = path.read_text(encoding="utf-8")
            with self.subTest(surface=label):
                self.assertIn("不必一次答完", text,
                              f"{label} 没说可以先答一部分")
                self.assertIn("/job-scrape", text,
                              f"{label} 说了可以早停，却没说停下来之后能干什么")


class TheSectionNamesAreRealOnes(unittest.TestCase):
    """顺序表里点到的 candidate.md 小节名，模板里必须真有这一节。

    写错一个字，上面那条一致性检查照样绿（两边都写着同一个错名），而 `/job-setup` 去填
    一个不存在的小节，自检永远等不到它被填上——用户会卡在同一句提示上出不去。
    """

    def test_sections_named_in_the_order_exist_in_the_template(self):
        tmpl = (REPO_ROOT / "profile.example" / "candidate.md"
                ).read_text(encoding="utf-8")
        have = {ln.lstrip("# ").strip() for ln in tmpl.splitlines()
                if re.match(r"^##\s+", ln)}
        named = {t for _, t in
                 (n for s in doctor.STAGE_NEEDS.values() for n in s["block"] + s["warn"])
                 if t}
        self.assertTrue(named, "自检一个小节都不点名了？那这条没有意义")
        for t in sorted(named):
            with self.subTest(section=t):
                self.assertIn(t, have,
                              f"自检按「{t}」这一节判断填没填，而模板里没有这一节 —— "
                              "它会永远算作「已填」")


if __name__ == "__main__":
    unittest.main()
