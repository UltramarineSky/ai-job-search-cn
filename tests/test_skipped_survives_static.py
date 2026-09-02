"""标了「不投」的岗，双击打开的单文件面板里也得是不投的。

## 实测抓到的

面板有两种打开方式，排除名单的来源不一样：跑 `python tools/serve.py` 时点「不投」
当场写盘，所以页面只认盘上那份；双击单文件 HTML 时写不回盘，只能存浏览器。

静态那条原来**只**读浏览器存储，把快照里的 `skipped` 整个无视了。实测一份真实
数据：可以投的岗位应该是 23 行，单文件面板画出 25 行——多出来的两个正是早就标了
「不投」的岗，其中一个用户还明确排除过。命令行和服务模式下做的决定，换个打开方式
就当没发生。

## 为什么不能改成「盘上的 ∪ 存的」

那样会翻出一个反向的鬼状态：静态版点「放回可以投」，存下来的集合里没有它，刷新时
又被盘上那份加回去——**页面上放回了、刷新又隐藏**，跟服务模式那条注释警告的是同一
类毛病，只是方向相反。

一个扁平集合表达不了「加」和「减」两个方向。所以浏览器里存的是**增量**（我在这里
标的不投 / 我在这里放回的），盘上的 `skipped` 当底，增量盖在上面。

## 这里怎么验

`web/` 没有 JS 测试框架（原因见 `test_web_copy.py` 开头），所以验的是推导链而不是
渲染结果。断言一律**顺着 App 自己 import 的那几个名字走**，不写死函数名——这仓库
被「断言钉在字面拼写上、一改名就红」坑过好几次。
"""

import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

APP = ROOT / "web" / "src" / "App.tsx"
STORE = ROOT / "web" / "src" / "data" / "excluded.ts"
DATA = ROOT / "web" / "public" / "data.json"


def strip_comments(s: str) -> str:
    """注释里引用要拦的写法是常事，不剥就会验到自己的说明。"""
    s = re.sub(r"\{/\*.*?\*/\}", "", s, flags=re.S)
    s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
    return re.sub(r"^\s*//.*$", "", s, flags=re.M)


def balanced(s: str, i: int) -> str:
    """`s[i]` 是左括号，返回到匹配右括号为止的内容（不含两端）。"""
    depth = 0
    for j in range(i, len(s)):
        if s[j] in "([{":
            depth += 1
        elif s[j] in ")]}":
            depth -= 1
            if depth == 0:
                return s[i + 1:j]
    raise AssertionError(f"括号不配对：{s[i:i + 80]!r}")


def ternary_arms(expr: str):
    """把 `cond ? A : B` 切成 (A, B)；不是三元就返回 None。"""
    depth = q = 0
    q = None
    for k, ch in enumerate(expr):
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        elif depth == 0 and ch == "?" and q is None:
            if expr[k + 1:k + 2] not in (".", "?"):   # 可选链 / 空值合并不算
                q = k
        elif depth == 0 and ch == ":" and q is not None:
            return expr[q + 1:k], expr[k + 1:]
    return None


def app_code() -> str:
    return strip_comments(APP.read_text(encoding="utf-8"))


def store_code() -> str:
    return strip_comments(STORE.read_text(encoding="utf-8"))


def imported_from_store(code: str) -> list:
    m = re.search(r'import\s*\{(.*?)\}\s*from\s*"\./data/excluded"', code, re.S)
    assert m, "App 不再从 data/excluded 取东西了？这条测试要重写"
    return [s.strip() for s in m.group(1).split(",") if s.strip()]


def disk_derived_names(code: str) -> set:
    """名字来自「拿 skipped 过滤出来的那份」——App 怎么叫它都行。"""
    out = set()
    for m in re.finditer(r"const (\w+) =", code):
        tail = code[m.end():m.end() + 300]
        head = tail.split(";")[0]
        if ".skipped" in head or "j.skipped" in head:
            out.add(m.group(1))
    return out


def excluded_effect_arg(code: str) -> str:
    """给 `excluded` 赋初值的那个调用的实参。"""
    m = re.search(r"setExcluded\(", code)
    assert m, "找不到 setExcluded"
    # 第一处是初始化那一处（后面 exclude() 里的是函数式更新）
    for m in re.finditer(r"setExcluded\(", code):
        arg = balanced(code, m.end() - 1)
        if "prev" not in arg:
            return arg
    raise AssertionError("找不到给 excluded 赋整份名单的那次调用")


class TheStaticPanelStillHonorsWhatDiskSaid(unittest.TestCase):
    """双击打开的那份，也得读快照里的 `skipped`。"""

    def test_both_modes_start_from_disk(self):
        code = app_code()
        arg = excluded_effect_arg(code)
        names = disk_derived_names(code)
        self.assertTrue(
            names,
            "App 里找不到「拿 skipped 过滤出来的那份」——盘上标的不投没人读了")

        arms = ternary_arms(arg)
        self.assertIsNotNone(
            arms, f"排除名单不再按运行方式分两路了：{arg.strip()!r}")
        live_arm, static_arm = arms
        for label, arm in (("有服务", live_arm), ("静态", static_arm)):
            self.assertTrue(
                any(n in arm for n in names) or "skipped" in arm,
                f"{label}那条没读盘上标的不投：{arm.strip()!r}\n"
                "静态那条漏掉它，就是实测里那个「23 行画成 25 行」——"
                "早就标了不投的岗又回到「可以投的岗位」里")

    def test_the_static_arm_also_reads_the_browser(self):
        """反过来也要有：只读盘上的，等于这个浏览器标的不投全丢。"""
        code = app_code()
        _, static_arm = ternary_arms(excluded_effect_arg(code))
        used = [n for n in imported_from_store(code) if n in static_arm]
        self.assertTrue(
            used,
            f"静态那条没读浏览器存的：{static_arm.strip()!r} —— "
            "静态版写不回盘，浏览器存储是它唯一记得住的地方")


class TheStoredShapeCanSayRestoredToo(unittest.TestCase):
    """存的必须是增量：能说「我标的不投」，也能说「我把它放回了」。"""

    def test_applying_it_can_both_add_and_remove(self):
        code = app_code()
        store = store_code()
        _, static_arm = ternary_arms(excluded_effect_arg(code))
        fns = [n for n in imported_from_store(code) if n in static_arm]
        bodies = ""
        for fn in fns:
            m = re.search(rf"function {fn}\b[^{{]*", store)
            if m:
                bodies += balanced(store, store.index("{", m.end() - 1))
        self.assertTrue(bodies, f"在 excluded.ts 里找不到 {fns} 的实现")
        self.assertIn(
            ".add(", bodies,
            "增量盖不上「我在这里标的不投」")
        self.assertIn(
            ".delete(", bodies,
            f"{fns} 只会往上加、不会减 —— 那静态版点「放回可以投」就白点了："
            "刷新时盘上那份又把它加回来，页面上放回了、刷新又隐藏")

    def test_what_gets_written_is_not_a_bare_id_list(self):
        """扁平的 id 数组表达不了两个方向——它正是坏掉的那个形状。"""
        store = store_code()
        # 键那一格现在是 `userKey(KEY, user)`（按活动用户分开，见
        # `test_browser_prefs_do_not_cross_users.py`），不再是一个裸标识符。
        # 这条守卫查的是**写进去的值**，键长什么样与它无关。
        m = re.search(r"setItem\(.+?,\s*JSON\.stringify\((.+?)\)\s*\)", store, re.S)
        self.assertIsNotNone(m, "找不到写浏览器存储的地方")
        self.assertNotRegex(
            m.group(1), r"^\s*\[\s*\.\.\.",
            f"存的还是一份扁平 id 列表：{m.group(1).strip()!r} —— "
            "它说不出「这个岗盘上标了不投、但我放回了」")


class OldBrowsersDoNotLoseWhatTheyMarked(unittest.TestCase):
    """换了存储格式，之前标过的不能凭空消失。"""

    def test_the_previous_key_is_still_read(self):
        store = store_code()
        keys = re.findall(r'"(jobSearchExcluded\.v\d+)"', store)
        self.assertGreaterEqual(
            len(set(keys)), 2,
            f"只认得一个存储键 {set(keys)} —— 换格式没带迁移，"
            "老浏览器里标过的「不投」会一声不响地全丢")


class RealDataConfirmsTheBoundaryExists(unittest.TestCase):
    """上面几条防的是真事，不是假想——真实数据里确实有标了不投的岗。"""

    def test_some_jobs_are_marked_skipped(self):
        if not DATA.is_file():
            self.skipTest("这个 clone 里还没导出数据")
        jobs = json.loads(DATA.read_text(encoding="utf-8")).get("jobs", [])
        if not jobs:
            self.skipTest("这份数据里没有职位")
        skipped = [j for j in jobs if j.get("skipped")]
        if not skipped:
            self.skipTest("这份数据里还没有标过「不投」的岗——这条边界暂时验不出真伪")
        self.assertTrue(
            all(j.get("id") for j in skipped),
            "标了不投的岗没有 id，页面按 id 对不上，排除会张冠李戴")


if __name__ == "__main__":
    unittest.main()
