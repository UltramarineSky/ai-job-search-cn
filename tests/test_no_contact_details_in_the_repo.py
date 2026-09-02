# -*- coding: utf-8 -*-
"""手机号、邮箱、个人域名 —— 最该拦的那一类，一个守卫都没有。

`test_no_maintainer_data_in_repo` 拦三类：`identifiers()`（用户名 / 姓名 /
雇主 / 院校）、`personal_figures()`（薪资取值）、作品成果。三个抽取器读的都是
**`profile/candidate.md`**。

**而联系方式不在那儿，在 `resume/main.typ` 的抬头里。** 于是这一类整个在所有
守卫的视野之外 —— 而它恰恰是最该拦的：公开仓库里的手机号和邮箱会被爬走，
后果是骚扰与诈骗，不是尴尬。

实测活动用户 2026-08-24：手机 1 个、邮箱 1 个（真实）、个人域名 4 个，
已跟踪文件里命中 **0** —— **今天没有泄漏，但也没有任何东西在看。**

## 这个文件自己的教训，正好是同一个形状

它开头记着：`identifiers()` 曾经因为照着模板形状写正则，在真实资料上
**只取到 1 个词**，而控制用例只验「非空」，于是**它一直是绿的**。
一层之外的这一类连抽取器都没有 —— 那是同一个病更彻底的版本。

## 要排掉三样，否则守卫必红

- **占位符**：模板里的 `test@example.com` 出现在 9 个已跟踪文件里，它就该在。
- **项目的公开身份**：`PUBLIC_IDENTITY` 那条 —— README 的徽章、365 开源计划的
  链接是**有意公开的**（那份注释原话：「列在这里是为了让下一个人一眼看出
  边界在哪，不要顺手把它们也『清掉』」）。
- **公共域名**：简历里会提 `github.com` 这类，它们不识别任何人。
"""
import pathlib
import re
import subprocess
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
#: 要从兄弟守卫里取 `PUBLIC_IDENTITY` 与 `tracked_text_files`，
#: 而 pytest 从仓库根跑时 `tests/` 不在路径上。**退回默认值会让这条
#: 守卫误报**：取不到公开身份那张表，README 里的项目域名就被当成泄漏。
import sys
sys.path.insert(0, str(ROOT / "tests"))

#: 抽联系方式的地方。**不只 `candidate.md`** —— 那正是这条守卫存在的理由。
_SOURCES = ("resume/main.typ", "resume/main-长版.typ",
            "cover_letter/main.typ", "profile/candidate.md")

#: 占位符：模板与示例本来就该带着它们。
_PLACEHOLDER = re.compile(r"example|test|placeholder|your|你的|某某", re.I)

#: 谁都在用的域名，不识别任何人。
_PUBLIC_DOMAINS = {
    "github.com", "gitlab.com", "npmjs.com", "python.org", "nodejs.org",
    "anthropic.com", "claude.ai", "openai.com", "example.com", "test.com",
    "liepin.com", "zhipin.com", "zhaopin.com", "51job.com", "typst.app",
}


def _public_identity() -> set:
    """项目自己有意公开的那几样 —— 从既有守卫里取，不另抄一份。"""
    try:
        from test_no_maintainer_data_in_repo import PUBLIC_IDENTITY
    except Exception:                                   # pragma: no cover
        return set()
    return set(PUBLIC_IDENTITY)


def contacts() -> dict:
    """活动用户的联系方式 → `{类别: {值}}`。取不到就返回空。"""
    au = ROOT / ".active_user"
    if not au.is_file():
        return {}
    user = au.read_text(encoding="utf-8").strip()
    src = ""
    for rel in _SOURCES:
        p = ROOT / "users" / user / rel
        if p.is_file():
            src += p.read_text(encoding="utf-8", errors="replace") + "\n"
    if not src:
        return {}
    mails = {m for m in re.findall(r"[\w.+-]+@[\w-]+\.[\w.]+", src)
             if not _PLACEHOLDER.search(m)}
    doms = {d for d in re.findall(
        r"(?<![\w/@.])((?:[\w-]+\.)+(?:top|com|cn|io|dev|me|net|org))(?![\w])", src)
        if d.lower() not in _PUBLIC_DOMAINS
        and d not in _public_identity()
        and not _PLACEHOLDER.search(d)
        and not any(d in m for m in mails)}
    return {
        "手机": set(re.findall(r"(?<!\d)1[3-9]\d{9}(?!\d)", src)),
        "邮箱": mails,
        "域名": doms,
    }


def _scan_targets():
    """和既有守卫看同一批文件 —— 含**未跟踪但没被 ignore 的**。

    只看 `git ls-files` 会漏掉「下一次 commit 才会带上」的新文件，而那正是
    泄漏最常发生的时刻（那条教训写在 `tracked_text_files` 的 docstring 里）。
    """
    try:
        from test_no_maintainer_data_in_repo import tracked_text_files
        return tracked_text_files()
    except Exception:                                   # pragma: no cover
        out = subprocess.run(["git", "ls-files"], cwd=ROOT,
                             capture_output=True, text=True).stdout.split()
        return [ROOT / r for r in out if (ROOT / r).is_file()]


_BINARY = {".pdf", ".webp", ".png", ".jpg", ".jpeg", ".ico", ".woff", ".woff2",
           ".ttf", ".otf", ".zip", ".gz"}


class TheExtractorIsNotRunningEmpty(unittest.TestCase):
    """这个仓库为「抽取器悄悄取到 0 个、测试一直绿」栽过一次，别再来一次。"""

    def test_there_is_an_active_user_to_check(self):
        if not (ROOT / ".active_user").is_file():
            self.skipTest("没有活动用户 —— 无从比对")
        self.assertTrue(contacts(), "抽不到任何联系方式 —— 多半是简历写法变了，"
                                    "回去看 `_SOURCES` 与那几条正则")

    def test_it_reads_more_than_the_profile(self):
        """联系方式在简历抬头里，不在 `candidate.md` —— 这是整条守卫的前提。"""
        self.assertIn("resume/main.typ", _SOURCES)
        self.assertGreater(len(_SOURCES), 1)

    def test_every_kind_present_in_the_source_is_found(self):
        """**每一类分开验，不许用「或」。**

        第一版写的是 `手机 or 邮箱` —— 变异实测：把手机那条正则挖空，邮箱还
        撑着，测试照绿；反过来也一样。而这条守卫的意义正是**两类都盯着**。

        判据不写死「应该有几个」，而是**回原文对**：原文里明显有这一类，
        抽取器就必须抽到。换个用户、换份简历，它跟着变。
        """
        if not (ROOT / ".active_user").is_file():
            self.skipTest("没有活动用户")
        c = contacts()
        if not c:
            self.skipTest("这个用户还没填简历")
        user = (ROOT / ".active_user").read_text(encoding="utf-8").strip()
        raw = ""
        for rel in _SOURCES:
            f = ROOT / "users" / user / rel
            if f.is_file():
                raw += f.read_text(encoding="utf-8", errors="replace")
        looks = {
            "手机": bool(re.search(r"(?<!\d)1[3-9]\d{9}(?!\d)", raw)),
            "邮箱": bool(re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", raw)),
            # 域名这一支也要绑住 —— 变异实测：把它挖空，上面两条还撑着，
            # 整份测试照绿。粗判即可：原文里有不在公共表里的域名形状。
            "域名": any(
                d.lower() not in _PUBLIC_DOMAINS and d not in _public_identity()
                for d in re.findall(
                    r"(?<![\w/@.])((?:[\w-]+\.)+(?:top|me|dev|io))(?![\w])", raw)),
        }
        self.assertTrue(any(looks.values()),
                        "原文里手机和邮箱都没有 —— 那这份简历没有联系方式？")
        for kind, present in looks.items():
            if not present:
                continue
            with self.subTest(kind=kind):
                self.assertTrue(c[kind],
                                f"原文里有「{kind}」，抽取器却一个都没取到")


class NoTrackedFileCarriesThem(unittest.TestCase):
    def test_no_leak(self):
        c = contacts()
        if not c:
            self.skipTest("抽不到联系方式 —— 无从比对")
        vals = {(k, v) for k, s in c.items() for v in s if len(v) >= 6}
        if not vals:
            self.skipTest("没有够长的值可查")
        bad = []
        for p in _scan_targets():
            if p.suffix.lower() in _BINARY or not p.is_file():
                continue
            if p.name == pathlib.Path(__file__).name:
                continue
            try:
                text = p.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for kind, v in vals:
                if v in text:
                    bad.append(f"{p.relative_to(ROOT).as_posix()}（{kind}）")
                    break
        # **不打印具体值** —— 报告里带上手机号，等于把它又写进一处。
        self.assertEqual(sorted(set(bad)), [],
                         "这些要提交的文件里出现了活动用户的联系方式"
                         "（只报文件与类别，不打印值）：\n  " + "\n  ".join(bad))


class ItAlsoSeesFilesNotYetCommitted(unittest.TestCase):
    """新文件在**第一次提交之前** `git ls-files` 里看不见 —— 而那正是泄漏发生的时刻。

    既有守卫的 `tracked_text_files` 为此栽过一次，原话：「拦截发生在泄漏之后，
    等于没拦」。这条守卫沿用它，所以也要验它**真的**沿用了 —— 变异实测：
    把那个 import 换成失败、退回 `git ls-files`，光看当下（本来就干净）
    是照绿的。种一个未跟踪的文件才试得出来。
    """

    def test_a_brand_new_untracked_file_is_scanned(self):
        c = contacts()
        vals = [v for s in c.values() for v in s if len(v) >= 6] if c else []
        if not vals:
            self.skipTest("抽不到联系方式 —— 无从比对")
        victim = ROOT / "_leak_probe_tmp.md"
        if victim.exists():
            self.skipTest("探针文件已存在，不覆盖")
        victim.write_text(f"<!-- {vals[0]} -->\n", encoding="utf-8")
        try:
            seen = {p.resolve() for p in _scan_targets()}
            self.assertIn(victim.resolve(), seen,
                          "未跟踪但没被 ignore 的新文件没有进扫描范围 —— "
                          "泄漏会在提交那一刻才被发现")
        finally:
            victim.unlink(missing_ok=True)


class TheExclusionsAreDeliberate(unittest.TestCase):
    def test_placeholders_are_allowed(self):
        """模板里的 `test@example.com` 出现在 9 个已跟踪文件里 —— 它就该在。"""
        self.assertTrue(_PLACEHOLDER.search("test@example.com"))
        self.assertFalse(_PLACEHOLDER.search("zhangsan@qq.com"))

    def test_the_projects_public_identity_is_allowed(self):
        """README 的徽章、365 开源计划的链接是有意公开的。"""
        pub = _public_identity()
        self.assertTrue(pub, "取不到 `PUBLIC_IDENTITY` —— 排除项失效了")
        self.assertIn("365.aishort.top", pub)

    def test_it_does_not_copy_the_public_identity_list(self):
        """从既有守卫里取，不另抄一份 —— 抄一份就等着两边分叉。

        **判据是「这里没有第二份定义」，不是「这里不出现那几个值」** ——
        后者写出来，断言字符串自己就会命中自己（第一版实测顶红）。
        """
        src = pathlib.Path(__file__).read_text(encoding="utf-8")
        self.assertIn("from test_no_maintainer_data_in_repo import "
                      "PUBLIC_IDENTITY", src)
        # 针要拼出来 —— 写成完整字面量，它自己就会命中自己（栽了两次）。
        needle = "PUBLIC_IDENTITY" + " = ("
        self.assertNotIn(needle, src, "又在这里抄了一份")

    def test_common_domains_do_not_identify_anyone(self):
        self.assertIn("github.com", _PUBLIC_DOMAINS)

    def test_a_real_domain_is_not_excluded(self):
        c = contacts()
        if not c:
            self.skipTest("抽不到联系方式")
        self.assertNotIn("github.com", c["域名"])


class TheNeighbouringGuardsStillCoverTheirOwn(unittest.TestCase):
    """这条只补联系方式那一类，别把既有三类顶掉。"""

    def test_the_identifier_guard_still_exists(self):
        from test_no_maintainer_data_in_repo import identifiers
        self.assertTrue(callable(identifiers))

    def test_the_salary_guard_still_exists(self):
        from test_no_maintainer_data_in_repo import personal_figures
        self.assertTrue(callable(personal_figures))

    def test_they_still_read_only_the_profile(self):
        """它们读 `candidate.md` 是对的 —— 姓名雇主院校本来就在那儿。
        这条守卫补的是**它们看不到的那一类**，不是去改它们的取材。"""
        src = (ROOT / "tests"
               / "test_no_maintainer_data_in_repo.py").read_text(encoding="utf-8")
        self.assertIn("def _profile_path()", src)
        self.assertIn("candidate.md", src)


if __name__ == "__main__":
    unittest.main()
