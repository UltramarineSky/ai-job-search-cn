"""报错也是给用户看的字：不许出现开发词，而且要说下一步。

## 这些话会印在哪

页面上任何一次写盘失败，`serve.py` / `tracker.py` 返回的 `error` 会原样显示成
「没写进去：X」「没记上：X」。用户看到的就是这一句，没有别的线索。

## 实际撞到过一次

改完 `serve.py` 没重启，页面显示：

    没记上：没有这个接口

「接口」是开发词，而且这句什么都没说明白。真实原因永远是同一个——**页面比正在
跑的服务新**。现在它说的是「到终端按 Ctrl+C 停掉，再跑一次 python tools/serve.py」。

## 两条规矩

1. **不许开发词**：token / JSON / id / 请求体 / 越界 / 接口 / API。
   规则同 AGENTS.md「给用户看的措辞」——用户不该为了看懂报错先学一套词。
2. **要说下一步**，除非它是纯安全拒绝（那种情况用户什么也做不了，
   说清「为什么不给」就够）。
"""

import ast
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import _cli  # noqa: E402
import tracker  # noqa: E402

#: 这些文件的 `error` 会原样显示给用户
SOURCES = ["tools/serve.py", "tools/tracker.py"]

#: 开发词。用户不该在报错里读到它们。
DEV_WORDS = ["token", "Token", "JSON", "json", "请求体", "越界", "接口",
             "API", "endpoint", "id 无效", "参数错误"]

#: 说了下一步的标志。命中任一即算「告诉了他怎么办」。
NEXT_STEP = ["刷新", "重启", "再跑", "跑一次", "Ctrl+C", "改", "再试", "先跑"]

#: 纯安全拒绝——用户做不了什么，说清「为什么不给」就够，不要求给下一步。
SECURITY_ONLY = "安全限制"


def error_messages() -> list:
    """`(文件, 行号, 文案)`。取字典字面量里的 `error` 值。"""
    out = []
    for rel in SOURCES:
        path = ROOT / rel
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Dict):
                continue
            for k, v in zip(node.keys, node.values):
                if not (isinstance(k, ast.Constant) and k.value == "error"):
                    continue
                if isinstance(v, ast.Constant) and isinstance(v.value, str):
                    out.append((path.name, k.lineno, v.value))
                elif isinstance(v, ast.JoinedStr):
                    out.append((path.name, k.lineno, "".join(
                        x.value if isinstance(x, ast.Constant) else "…"
                        for x in v.values)))
    return out


class ErrorsAreWrittenForTheUser(unittest.TestCase):

    def test_there_is_something_to_check(self):
        """判据自检：真取到了文案，不是空跑一遍报绿。"""
        msgs = error_messages()
        self.assertGreaterEqual(len(msgs), 8, f"只取到 {len(msgs)} 条报错文案")

    def test_no_developer_words(self):
        bad = []
        for name, ln, msg in error_messages():
            for w in DEV_WORDS:
                if w in msg:
                    bad.append(f"{name}:{ln}  「{w}」  {msg[:44]}")
        self.assertEqual(
            bad, [],
            "报错会原样印给用户，里面不该有开发词（规则见 AGENTS.md"
            "「给用户看的措辞」）：\n" + "\n".join(bad))

    def test_every_error_says_what_to_do_next(self):
        bad = []
        for name, ln, msg in error_messages():
            if SECURITY_ONLY in msg:
                continue                      # 纯拒绝，用户做不了什么
            if not any(w in msg for w in NEXT_STEP):
                bad.append(f"{name}:{ln}  {msg[:52]}")
        self.assertEqual(
            bad, [],
            "这些报错只说了「不行」，没说接下来怎么办——而页面上除了这一句，"
            "用户没有别的线索：\n" + "\n".join(bad))

    def test_the_same_situation_uses_the_same_words(self):
        """同一件事在两处发生，就该用同一句话说。

        `set_status` 与 `undo` 都会遇到「盘上没有这一行」。原来一处写
        「投递记录里找不到这一行了」、另一处多了「——刷新页面再试」，
        后来又差在「刷新」与「刷新一下」。同一个动作在流程里只能有一个名字。
        """
        # **2026-09-01 起这句话只有一份**（`tracker.ROW_GONE`），
        # 于是按源码数字面量的老写法数到 0，报「只找到一处，无从比对」——
        # 而它要防的事已经**按构造**不可能了。判据改成现算：让两条路
        # 各撞一次那个情形，比它们回给面板的话。
        import tempfile
        row = {"company": "查无此家", "role": "查无此岗"}
        with tempfile.TemporaryDirectory() as d:
            csvp = Path(d) / "job_search_tracker.csv"
            csvp.write_text("company,role,status,date,notes\n",
                            encoding="utf-8")
            said = [tracker.set_status(csvp, row, {}, "interview",
                                       "2026-09-01")["error"],
                    tracker.undo(csvp, row, "applied", "2026-09-01")["error"]]
        self.assertEqual(len(set(said)), 1,
                         f"同一件事用了不同说法：{sorted(set(said))}")
        self.assertIn("找不到这一行", said[0])


class OneSituationOneSentence(unittest.TestCase):
    """「还没抓过职位」——同一件事横跨九个工具，原来九处五种说法。

        archive / audit_pipeline / prescreen / writeback / jd_store
                            没有 {p} —— 先跑 /job-scrape
        build_dashboard     未找到 {p} —— 请先运行 /job-scrape 抓取职位
        export_web_data     还没有职位数据（{p} 不存在）——先跑 /job-scrape
        fetch_details       没有 {p} —— 先跑 /job-scrape 抓一轮职位
        gap_split           {user} 还没有职位数据 —— 先跑 /job-scrape 与 /job-rank

    上面那条 `test_the_same_situation_uses_the_same_words` 立的就是这条判据，
    可它只看 `SOURCES` 那两个文件里的一种情形。**这一件一直在网外。**

    ⚠️ **怎么失败不归这条管。** 各家分别是 `SystemExit` / `print`+`return 1` /
    `print`+`return 0` —— 流水线里「还没抓过」是**正常起点**不是异常
    （`fetch_details` 那条注释写着这条约定）。统一的只有那句话。
    """

    #: 该走 `_cli.no_store` 的那几个。缺一个就是又有人自己写了一句。
    USERS = ("archive.py", "audit_pipeline.py", "prescreen.py", "writeback.py",
             "jd_store.py", "build_dashboard.py", "export_web_data.py",
             "fetch_details.py", "gap_split.py", "query_yield.py",
             "serve.py")

    def test_every_one_of_them_calls_it(self):
        for name in self.USERS:
            with self.subTest(name=name):
                src = (ROOT / "tools" / name).read_text(encoding="utf-8")
                self.assertIn("_cli.no_store(", src,
                              f"{name} 又自己写了一句「还没抓过职位」")

    def test_nobody_writes_their_own_any_more(self):
        """**这一条才是网。** 上面那条只认已经登记的九个；这一条按内容捞，
        谁新写一句都逃不掉。
        """
        import re
        bad = []
        # ⚠️ **「文件在、里面一个岗都没有」是另一件事，不许一起捞。**
        # 它可能是**老格式没认出来**（`_cli.seen_of` 那段注释记着这一课：
        # 写成 `.get("seen") or {}` 会在老库上报「里面没有职位」）——
        # 用户的下一步一样，而诊断不一样，合并说法等于把那个线索抹掉。
        # 判据：只捞「找不到这份文件」那一类。
        pat = re.compile(r"(没有|未找到|还没有)[^\n\"']{0,40}先跑 /job-scrape"
                         r"|请先运行 /job-scrape")
        empty = re.compile(r"里没有职位|里面没有职位")
        for p in sorted((ROOT / "tools").glob("*.py")):
            if p.name == "_cli.py":
                continue                       # 正本住在那儿
            for i, ln in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
                code = ln.split("#")[0]
                if pat.search(code) and not empty.search(code):
                    bad.append(f"{p.name}:{i}  {ln.strip()[:60]}")
        self.assertEqual(bad, [], "这几处又各写了一句「还没抓过职位」，"
                                  "改走 `_cli.no_store`：\n  " + "\n  ".join(bad))

    def test_the_sentence_says_what_to_do(self):
        said = _cli.no_store("某路径")
        self.assertIn("某路径", said, "不说是哪份文件，用户不知道该看哪儿")
        self.assertIn("/job-scrape", said)

    def test_a_different_next_step_is_still_possible(self):
        """`gap_split` 要的是评过分的岗 —— 光抓完还不够，那条得能改。"""
        self.assertIn("/job-rank",
                      _cli.no_store("p", then="/job-scrape 与 /job-rank"))


class TheStaleServerCaseIsNamed(unittest.TestCase):
    """撞到过的那一次要留在代码里，不然下次还会写回「没有这个接口」。"""

    def test_unknown_endpoint_tells_you_to_restart(self):
        msgs = [m for _, _, m in error_messages()]
        hit = [m for m in msgs if "serve.py" in m]
        self.assertTrue(
            hit,
            "没有一条报错提到重启 serve.py —— 页面比服务新时（改了代码没重启），"
            "用户会看到一句什么都没说明白的话")
        self.assertTrue(any("Ctrl+C" in m or "再跑" in m for m in hit),
                        "提到了 serve.py 但没说怎么重启")


if __name__ == "__main__":
    unittest.main()
