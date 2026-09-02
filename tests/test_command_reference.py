"""面板必须说出命令——用户不知道该敲什么。

## 为什么这是硬要求

这个仓库的判断力全在命令行侧：找职位要浏览器扩展、评估与写材料要模型、都走用户
自己的订阅。面板只负责**看得见**（`serve.py` 开头就写着「不接大模型」）。所以面板
不说出命令，两边就是断的——用户看着一页数据，不知道自己还能做什么。

## 这次检查抓到的

**① 面板只露过 18 个工作流里的 7 个。** `/job-outcome`（投完记录结果，投递之后最该做的
一件事）、`/job-offer`、`/job-upskill`、`/job-expand` 连提都没提过。它们各自有完整的工作流文件、
有命令 stub、有测试——唯独在界面上查无此人。

**② 拿到 offer 的岗，下一步给的是 `/job-interview`。** `job_next_step` 把 offer 和
interview 合成一个分支。拿到 offer 之后该做的是算可守区间、过背调红线、和别的
offer 比——那是 `/job-offer`。这一步给错，用户会在最该谈钱的时候去背题。

**③ 三处「说了要做什么、却不说敲什么」：**
   - 硬性条件那张表为空时说「投之前你自己对一遍」，不说 `/job-apply` 就会自动核
   - 找不到 `resume/main.typ` 时只说没找到，不说怎么才会有
   - 「改简历就能补」不说改完跑 `/job-resume` 验一遍
   - 「材料就绪，还没投」整条**没有命令**——投完之后线索就断了，投递记录一直是空的

## 规则

1. 面板要有一块**命令总览**，来自 `AGENTS.md` 的索引（不在前端写死）
2. `workflows/*.md` 每一个都要在总览里出现，且落在某个**有意义的**分组里
3. 每个岗的「下一步」文案都要带命令（除非已结案）
"""

import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(ROOT / "tools"))

from jsx import FIRSTRUN, desk_entry, is_copyable  # noqa: E402
import export_web_data as ex  # noqa: E402
import build_dashboard as bd  # noqa: E402
from build_dashboard import job_next_step  # noqa: E402

WEB = ROOT / "web" / "src"


class TheCommandListComesFromTheIndex(unittest.TestCase):
    """写死在前端必然跟索引飘：加个工作流、改句说明，面板还停在上一版。"""

    def test_every_workflow_is_listed(self):
        groups = ex.parse_commands()
        listed = {it["name"] for g in groups for it in g["items"]}
        have = {p.stem for p in (ROOT / "workflows").glob("*.md")}
        self.assertEqual(sorted(have - listed), [],
                         "这些工作流在面板上查无此人，用户不会知道它们存在")

    def test_nothing_is_listed_that_does_not_exist(self):
        groups = ex.parse_commands()
        listed = {it["name"] for g in groups for it in g["items"]}
        have = {p.stem for p in (ROOT / "workflows").glob("*.md")}
        self.assertEqual(sorted(listed - have), [],
                         "面板列了不存在的命令，照着敲会撞空")

    def test_every_entry_has_a_command_and_a_description(self):
        for g in ex.parse_commands():
            for it in g["items"]:
                with self.subTest(cmd=it["name"]):
                    self.assertTrue(it["cmd"].startswith("/"), f"{it} 没有斜杠命令")
                    self.assertTrue(it["does"].strip(), f"{it['cmd']} 没说它干什么")

    def test_grouping_is_complete_not_a_dump_into_other(self):
        """「其它」是兜底，不是收纳箱。新工作流掉进去 = 它失去了上下文。"""
        allowed_in_other = {"job-reset"}
        other = next((g for g in ex.parse_commands() if g["group"] == "其它"), None)
        got = {it["name"] for it in (other or {"items": []})["items"]}
        self.assertEqual(sorted(got - allowed_in_other), [],
                         "这些工作流没归组，掉进了「其它」——给它们一个位置")

    def test_the_post_application_stage_is_covered(self):
        """投出去之后那一段是收益最大的，也是原来整段缺失的。"""
        groups = {g["group"]: {i["name"] for i in g["items"]}
                  for g in ex.parse_commands()}
        after = groups.get("投出去之后", set())
        for name in ("job-outcome", "job-interview", "job-offer"):
            with self.subTest(cmd=name):
                self.assertIn(name, after, f"/{name} 不在「投出去之后」这一组里")

    def test_every_command_carries_at_least_one_example(self):
        """只印命令名不够——这些命令的价值大半在参数上。

        实测面板第二版每条只有「命令 + 一句话」，而 `/job-apply --top 20`、
        `/job-outcome followup`、`/job-reset profile` 这些真正省事的形式，
        用户只有把 18 个工作流文件读一遍才会知道。
        """
        for g in ex.parse_commands():
            for it in g["items"]:
                with self.subTest(cmd=it["name"]):
                    self.assertTrue(it.get("examples"),
                                    f"{it['cmd']} 一个举例都没有——第三列空了？")
                    self.assertEqual(it["examples"][0], it["cmd"],
                                     "第一条举例必须就是标准形式，界面靠这一条去重")

    def test_no_example_invents_a_command_that_does_not_exist(self):
        """举例是给人照抄的。抄下去跑不了，比不给举例更糟。

        两条都钉住：斜杠举例只能是**这一行自己**的命令（别串到别人的名下），
        且那个命令必须真有工作流文件。
        """
        have = {p.stem for p in (ROOT / "workflows").glob("*.md")}
        for g in ex.parse_commands():
            for it in g["items"]:
                for e in it["examples"]:
                    if not e.startswith("/"):
                        continue          # 「投这个岗」这类自然语言触发语
                    with self.subTest(example=e):
                        # 先剥掉末尾的补充说明，再取命令名——口径同界面上的
                        # `CommandBook.splitNote`。直接 `split()` 会在
                        # 「裸命令 + 全角括号」上翻车（`/job-apply（可以投的全部备料）`
                        # 之间没有空格，整串被当成命令名），而那个写法界面渲染得好好的：
                        # 同一件事两份解析，糙的那份说了不算。
                        head = re.sub(r"（.*）$", "", e).split()[0].lstrip("/")
                        self.assertEqual(head, it["name"],
                                         f"{it['cmd']} 的举例里混进了 /{head}")
                        self.assertIn(head, have, f"/{head} 没有对应的工作流")

    def test_the_examples_reach_the_screen(self):
        """有数据没人渲染，等于没有——钉住组件真的读了这个字段。"""
        s = (WEB / "components" / "CommandBook.tsx").read_text(encoding="utf-8")
        self.assertIn("it.examples", s, "CommandBook 没读 examples，举例到不了屏幕上")

    def test_it_is_exported(self):
        src = (ROOT / "tools" / "export_web_data.py").read_text(encoding="utf-8")
        self.assertIn('"commands": parse_commands()', src, "解析了但没导出")

    def test_real_export_carries_it(self):
        data = ROOT / "web" / "public" / "data.json"
        if not data.is_file():
            self.skipTest("还没导出")
        d = json.loads(data.read_text(encoding="utf-8"))
        if not d.get("isRealData"):
            self.skipTest("这份是演示数据")
        self.assertTrue(d.get("commands"), "真实导出里没有命令表")


class ThePanelRendersIt(unittest.TestCase):

    def test_component_exists_and_is_wired(self):
        self.assertTrue((WEB / "components" / "CommandBook.tsx").is_file())
        app = (WEB / "App.tsx").read_text(encoding="utf-8")
        self.assertIn("<CommandBook groups=", app, "组件没被渲染")

    def test_each_command_is_copyable(self):
        s = (WEB / "components" / "CommandBook.tsx").read_text(encoding="utf-8")
        # 问意图，不问拼法：`copyable=…` 那段标记已经收进 `<Cmd>` 组件了
        self.assertTrue(is_copyable(s, "{it.cmd}"),
                        "命令不能复制——让人对着屏幕手打是在制造错字")

    def test_it_says_where_the_work_happens(self):
        """面板不干活这件事要说出来，否则用户会在页面上找那些按钮。"""
        s = (WEB / "components" / "CommandBook.tsx").read_text(encoding="utf-8")
        self.assertIn("命令行", s)

    def test_no_hardcoded_command_table_in_the_frontend(self):
        """前端不许自带一份命令清单——它会和 AGENTS.md 飘开。"""
        s = (WEB / "components" / "CommandBook.tsx").read_text(encoding="utf-8")
        code = "\n".join(ln for ln in s.splitlines()
                         if not ln.strip().startswith(("*", "/*", "//")))
        # 组件里出现三个以上写死的斜杠命令，就说明它在自己维护一份表
        hard = set(re.findall(r'"(/[a-z-]{3,})"', code))
        self.assertLessEqual(len(hard), 2,
                             f"前端写死了命令：{sorted(hard)}——应该从导出的数据渲染")

    def test_first_time_user_gets_it_open(self):
        """还没建过档的人最需要这张表，不能让他先学会点开什么。

        **2026-08-24 换了实现，守的事没变。** 折叠时代靠
        `defaultActiveKey={activeUser ? [] : ["cmds"]}`；现在那一档进了
        「设置/统计/说明」那一排按钮，而按钮的前提是「你已经知道自己在看什么」。
        所以这类用户改成**内联摊开**——为它自动弹一个 Modal 比不弹更糟。

        **2026-08-24 再改一次：内联的只剩「日常就这三条」那个脊梁块。**
        全集 20 条摊给还没建档的人，能敲的只有 `/job-setup` 和 `/job-user`
        两条（实测拿空快照渲染：那张表从 220px 一直铺到页面底部）。
        守的事仍然没变 —— 他不用先学会点开什么就能看到该敲的；
        变的是「该敲的」此刻只有三条。
        全集因此也不再和内联的重复，那颗按钮对他跟着放开（见下）。
        """
        app = (WEB / "App.tsx").read_text(encoding="utf-8")
        self.assertIn(FIRSTRUN, app, "没建过档的人看不到命令表了")
        i = app.index(FIRSTRUN)
        self.assertIn("!activeUser", app[max(0, i - 160):i],
                      "这一块不再只给没建过档的人")
        seg = app[i:i + 1200]
        self.assertIn("<CommandBook groups={snap.commands ?? []} spineOnly />", seg,
                      "那一支渲染的不是脊梁那三条")
        # 反过来：全集要有地方进 —— 内联的既然只剩三条，按钮就不能再挡着他
        self.assertNotIn("activeUser", desk_entry(app, "cmds"),
                         "内联只剩三条了，全集却还挡着没建档的人")


class EveryNextStepCarriesItsCommand(unittest.TestCase):
    """「下一步该做什么」不给命令，等于没说。"""

    CASES = [
        ("拿到 offer", {"company": "甲", "applied": {"status": "offer"}}, "/job-offer"),
        ("进面试", {"company": "乙", "applied": {"status": "interview"}}, "/job-interview"),
        ("已投等回复", {"company": "丙", "applied": {"status": "applied"}}, "/job-outcome"),
        ("材料就绪未投", {"company": "丁", "materials": {"resume": 1}, "score": 80},
         "/job-outcome"),
        ("还没出材料", {"company": "戊", "score": 75, "url": "https://x/1"}, "/job-apply"),
    ]

    def test_each_stage_gives_a_command(self):
        for name, job, want in self.CASES:
            with self.subTest(stage=name):
                r = job_next_step(job)
                self.assertIsNotNone(r, f"{name} 没有下一步")
                self.assertTrue(r.get("command"), f"{name} 说了要做什么却不给命令")
                self.assertTrue(r["command"].startswith(want),
                                f"{name} 给的是 {r['command']}，该给 {want}")

    def test_offer_does_not_send_you_back_to_interview_prep(self):
        """这是抓到的原 bug：offer 与 interview 合在一个分支，都给 /job-interview。

        拿到 offer 之后该谈钱、过背调红线、比 offer——不是再练一轮面试题。
        """
        r = job_next_step({"company": "甲", "applied": {"status": "offer"}})
        self.assertNotIn("/job-interview", r["command"],
                         "拿到 offer 了还让人去背题")
        self.assertIn("背调", r["text"], "没提背调红线——那一节不该跳过")

    def test_closed_cases_have_no_next_step(self):
        """已结案的不该有下一步——硬凑一条会让人做无用功。"""
        for st in ("hired", "rejected", "no response", "withdrawn"):
            with self.subTest(status=st):
                self.assertIsNone(job_next_step({"company": "甲",
                                                 "applied": {"status": st}}))


class GuidanceTextAlwaysNamesTheCommand(unittest.TestCase):
    """各组件里「告诉你该做什么」的地方，附近必须有可复制的命令。"""

    #: (文件, 那句话的锚点, 附近应出现的命令)
    SPOTS = [
        ("components/GateStamp.tsx", "硬性条件还没核对过", "/job-apply"),
        ("components/ResumeRead.tsx", "没找到", "/job-apply"),
        ("components/ResumeRead.tsx", "改完", "/job-resume"),
        ("components/BaseResume.tsx", "PDF 比源文件旧", "typst compile"),
        ("components/Shortlist.tsx", "还没有职位可以看", "/job-scrape"),
    ]

    @staticmethod
    def _strip_comments(s: str) -> str:
        """注释里提到命令**不算数**——用户看不到注释。

        这条是变异测试逼出来的：把 GateGrid 那个可复制命令块整个换掉，测试照样
        绿——因为解释「为什么要有这句」的注释里正好写着 `/job-apply`。判据必须只看
        真正渲染出去的东西。
        """
        s = re.sub(r"\{/\*.*?\*/\}", " ", s, flags=re.S)     # JSX 注释
        s = re.sub(r"/\*.*?\*/", " ", s, flags=re.S)         # 块注释
        return "\n".join(ln for ln in s.splitlines()
                         if not ln.strip().startswith(("//", "*")))

    def test_each_spot_names_a_command(self):
        for rel, anchor, cmd in self.SPOTS:
            with self.subTest(where=f"{rel}:{anchor}"):
                s = self._strip_comments((WEB / rel).read_text(encoding="utf-8"))
                i = s.find(anchor)
                self.assertNotEqual(i, -1, f"{rel} 里找不到锚点「{anchor}」")
                # 锚点往后 900 字符内要出现命令。范围要够大——命令通常在
                # 下一个 JSX 元素里，不在同一行。
                self.assertIn(cmd, s[i:i + 900],
                              f"{rel} 说了「{anchor}」却没给出 {cmd}（注释里的不算）")


if __name__ == "__main__":
    unittest.main()
