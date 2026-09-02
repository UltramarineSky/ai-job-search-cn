#!/usr/bin/env python3
"""Supply-chain guards for the template's riskiest surfaces.

Run from anywhere: python tools/security_guards.py

This repo ships pre-approved Claude Code permissions and CLI code that every
fork user executes. These guards make the dangerous changes LOUD, not
impossible: a PR that intentionally needs one of them must update the
allowlists in this file in the same diff, so the change is explicit and
reviewable rather than buried.

Checks:
1. .claude/settings.json — every permissions.allow entry must be in the exact
   allowlist below. Catches permission widening (e.g. Bash(*), Bash(curl:*)),
   which would auto-approve commands on every fork.
2. .gitignore — the personal-data ignore rules must all still be present,
   and no un-allowlisted negation (!pattern) may re-include them. Catches
   weakening that would make future users silently commit their tracker,
   profile exports, or application archives.
3. .agents/**/package.json — no npm/bun lifecycle scripts (preinstall,
   install, postinstall, prepare, prepack) and no trustedDependencies.
   Catches code execution smuggled into `bun install`.

Stdlib only. Exit 0 on success, 1 with a failure list otherwise.
"""

import json
import subprocess
import sys
from pathlib import Path

# 管道/重定向时把输出定到 UTF-8。Windows 上 Python 只在 stdout 是真终端时才走
# WriteConsoleW；被管道接走就回落到 cp936(GBK)，而 Git Bash / VS Code / Windows
# Terminal 都按 UTF-8 解 —— 用户看到一屏乱码。这里的中文主要来自 argparse 的
# description / help，不是 print()，所以按 print 数中文的启发式扫不到它。
# 只改非 tty 那条路：真终端本来就对，强行改反而会让代码页 936 的 cmd.exe 开始乱码。
# 与 tools/_cli.py 的 force_utf8_output() 同一份逻辑；这里内联是因为本文件会被
# 测试单独拷进临时目录运行，不能依赖仓库里的任何模块。
for _s in (sys.stdout, sys.stderr):
    try:
        if _s is not None and hasattr(_s, "reconfigure") and not _s.isatty():
            _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass



ROOT = Path(__file__).resolve().parent.parent
errors: list[str] = []

# The exact permission entries the template ships. A PR that adds or changes
# an entry must add it here too - that is the point: the diff shows both.
ALLOWED_PERMISSIONS = {
    "Skill(job-application-assistant)",
    # portal CLI 有两个运行时：node 是默认路径（Claude Code 走 npm 安装，Node 必然已存在，
    # 且 CLI 零 runtime 依赖、无编译步骤），bun 是可选的开发/备用路径。两条都得在白名单里，
    # 否则默认路径每次都要用户手动批准。两条都限定到 cli.ts 这一个入口，不是宽授权。
    "Bash(node .agents/skills/*/cli/src/cli.ts:*)",
    "Bash(bun run .agents/skills/*/cli/src/cli.ts:*)",
    "Bash(pdftotext:*)",
}

# Personal-data ignore rules that must never disappear from .gitignore.
REQUIRED_IGNORE_RULES = [
    # Whole-directory rule (matches .gitignore:23 exactly): must stay the bare
    # `profile/` form, not a glob like `profile*` or `profile.*`, or it would
    # also swallow (or fail to distinguish from) the unrelated
    # `profile.example/` setup-scaffolding directory.
    "profile/",
    "salary_data.json",
    # Depth-independent: the job-scrape skill resolves `job_scraper/` relative
    # to its own directory, so the state file lands under .claude/skills/... and
    # a repo-rooted rule silently fails to match it.
    "**/job_scraper/seen_jobs.json",
    "documents/cv/**",
    "documents/linkedin/**",
    "documents/diplomas/**",
    "documents/references/**",
    "documents/applications/**",
    "documents/interview/**",
    "job_search_tracker.csv",
    "resume/main.typ",
    "resume/*.pdf",
    "cover_letter/main.typ",
    # Compiled cover letters embed the target company name and candidate
    # details - as sensitive as resume/*.pdf, which is already required.
    "cover_letter/*.pdf",
    # The optional resume photo is personal data too.
    "resume/photo.*",
    # Claude Code 会把 settings.local.json 合并到 settings.json 之上，因此它同样能
    # 预授权命令。它此前既不在 .gitignore 里也不被任何守卫读取，`git add -A` 会直接
    # 把它连同本机授予的权限一起提交，在每个 pull 的 fork 上无提示生效。
    ".claude/settings.local.json",
    # /job-notion-sync 的状态含 Notion 数据库与页面 id（对应到每一次投递），/job-scrape 的
    # 抓取清单同样是个人数据。二者按 skill 目录解析，落在 users/ 之外，所以必须
    # 由这两条深度无关的规则单独兜住。
    "**/job_scraper/notion_sync.json",
    "**/job_scraper/*.md",
    # JD 原文快照：抓取下来的岗位原文，与 documents/ 下其它子目录同属个人数据
    "documents/postings/**",
    # 多用户：每用户数据根与活动用户指针（个人数据，绝不提交）
    "users/",
    ".active_user",
    # 根级激活文件兜底：.active_user 缺失/迁移未完成时，激活文件可能误落到
    # 仓库根而非 users/<用户>/templates/ 下
    "templates/active-*.md",
    # 命令产出的个人数据：/job-gmail-sync 的状态（邮件 message id + 主题）、
    # /job-html-report 的仪表盘、/job-upskill 的学习计划。生成物同样含个人信息。
    "gmail_sync/",
    "reports/",
    # 整目录，与 gmail_sync/ / reports/ 一致。**别改回扩展名通配**：
    # `upskill/*.md` 只挡 md，而这个目录归 /job-upskill 写，它哪天缓存一份
    # 语料就是一个 .json 静默进版本库。同一类脆处在 web/public/ 上栽过一次。
    "upskill/",
    # 面板的导出快照与构建产物。**这两条 2026-08-20 补**——它们一直在 .gitignore
    # 里，却从没进过这份必需清单：删掉那两行不会有任何守卫报警，而
    # `web/public/data.json` 是全仓个人数据密度最高的**单个文件**——一份里同时有
    # 全部职位与评分、投递记录、三渠道话术全文（含网申自评这种上千字的段落）、
    # 薪资期望，外加 `pdf/` 下的真实简历 PDF。实测这两个目录里 37 个文件。
    # 它比这份清单里任何一条都更该被守住，却恰恰是唯一没被守住的。
    "web/public/",
    "web/dist/",
    # 维护者的本机笔记：发布前清单（点名了哪些标识符要清）、历史 bundle。
    # 按设计就是「不该被别人看到、但本机需要」的那一类。
    ".private/",
]

# Negation (re-include) rules the template legitimately ships. .gitignore is
# order-sensitive: a later `!pattern` re-includes a path an earlier rule
# excluded, so a rule can be physically present in REQUIRED_IGNORE_RULES yet
# no longer ignored (e.g. adding `!salary_data.json`). Set membership on the
# required rules cannot see that. Any negation outside this allowlist is a
# failure - add an intentional one here in the same PR, exactly as with
# ALLOWED_PERMISSIONS, so the widening is explicit and reviewable.
ALLOWED_IGNORE_NEGATIONS = {
    "!documents/**/.gitkeep",
}

FORBIDDEN_SCRIPTS = {"preinstall", "install", "postinstall", "prepare", "prepack"}


# settings 文件里**经过审阅**的键面。只看 permissions.allow 等于没看：`hooks` 能在每次
# 会话启动时跑任意命令，`permissions.defaultMode: bypassPermissions` 直接关掉所有确认，
# `permissions.additionalDirectories` 把可写范围扩到仓库外——这些都不经过 allow 列表。
# 出现清单外的键就报错，要求在同一个 PR 里显式加进来，与 ALLOWED_PERMISSIONS 同一套路。
ALLOWED_SETTINGS_KEYS = {"permissions"}
ALLOWED_PERMISSION_KEYS = {"allow"}

# Claude Code 会把 settings.local.json 合并到 settings.json 之上，所以它同样能预授权命令。
# 它的**内容**是每台机器本地授予的，不该拿仓库的允许清单去卡（那会让每个开发者授予一次
# 本地权限就红）。真正的风险只有一个：它被提交进版本库，于是本机授权推给每个 pull 的
# fork。所以判据是「有没有被 git 跟踪」，而不是里面写了什么。
LOCAL_SETTINGS = ".claude/settings.local.json"


def _is_tracked(rel: str) -> bool:
    """该路径是否已被 git 跟踪。无法判定（无 git / 非仓库）时返回 False。"""
    try:
        res = subprocess.run(
            ["git", "ls-files", "--error-unmatch", "--", rel],
            cwd=str(ROOT), capture_output=True, text=True,
            encoding="utf-8", errors="replace",
        )
    except (OSError, ValueError):
        return False
    return res.returncode == 0


def _check_one_settings_file(rel: str, *, required: bool) -> None:
    path = ROOT / rel
    if not path.is_file():
        if required:
            errors.append(f"{rel}: missing")
        return
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"{rel}: unreadable or invalid JSON: {exc}")
        return
    if not isinstance(data, dict):
        errors.append(f"{rel}: top-level JSON value must be an object")
        return
    for key in sorted(set(data) - ALLOWED_SETTINGS_KEYS):
        errors.append(
            f"{rel}: unreviewed settings key {key!r}. Keys outside "
            f"{sorted(ALLOWED_SETTINGS_KEYS)} can grant execution without going through "
            "permissions.allow (e.g. 'hooks' runs commands on every session start). If it is "
            "intentional, add it to ALLOWED_SETTINGS_KEYS in tools/security_guards.py in the "
            "same PR so the widening is explicit and reviewable."
        )
    permissions = data.get("permissions", {})
    if not isinstance(permissions, dict):
        errors.append(f"{rel}: permissions must be an object")
        return
    for key in sorted(set(permissions) - ALLOWED_PERMISSION_KEYS):
        errors.append(
            f"{rel}: unreviewed permissions key {key!r}. 'defaultMode' can disable prompting "
            "entirely and 'additionalDirectories' widens the writable area beyond the repo. "
            "Add it to ALLOWED_PERMISSION_KEYS in tools/security_guards.py in the same PR."
        )
    allow = permissions.get("allow", [])
    if not isinstance(allow, list) or not all(isinstance(entry, str) for entry in allow):
        errors.append(f"{rel}: permissions.allow must be a list of strings")
        return
    for entry in allow:
        if entry not in ALLOWED_PERMISSIONS:
            errors.append(
                f"{rel}: permission not in the reviewed allowlist: {entry!r}. "
                "Pre-approved permissions run without prompting on every fork. If this entry is "
                "intentional, add it to ALLOWED_PERMISSIONS in tools/security_guards.py in the "
                "same PR so the widening is explicit and reviewable."
            )
    if required:
        for entry in ALLOWED_PERMISSIONS - set(allow):
            # Not an error: settings may legitimately drop an entry. But an
            # allowlist entry that no longer exists should be pruned.
            print(f"note: allowlisted permission not present in settings.json: {entry!r}")


def check_permissions() -> None:
    _check_one_settings_file(".claude/settings.json", required=True)
    if _is_tracked(LOCAL_SETTINGS):
        errors.append(
            f"{LOCAL_SETTINGS} is tracked by git. Claude Code merges it over settings.json, so "
            "committing it pre-approves this machine's local grants on every fork that pulls. "
            "Run: git rm --cached .claude/settings.local.json  (it is in .gitignore already)."
        )


def check_gitignore() -> None:
    path = ROOT / ".gitignore"
    try:
        lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines()]
    except OSError as exc:
        errors.append(f".gitignore: unreadable: {exc}")
        return
    rules = set(lines)
    for rule in REQUIRED_IGNORE_RULES:
        if rule not in rules:
            errors.append(
                f".gitignore: required personal-data rule missing: {rule!r}. "
                "These rules keep fork users from committing personal data. If the rule moved "
                "or was renamed intentionally, update REQUIRED_IGNORE_RULES in "
                "tools/security_guards.py in the same PR."
            )
    for line in lines:
        if line.startswith("!") and line not in ALLOWED_IGNORE_NEGATIONS:
            errors.append(
                f".gitignore: negation rule not in the reviewed allowlist: {line!r}. "
                "A negation re-includes a path an earlier rule excluded and can silently "
                "re-expose personal data (a required ignore rule stays present but stops "
                "taking effect). If this negation is intentional, add it to "
                "ALLOWED_IGNORE_NEGATIONS in tools/security_guards.py in the same PR."
            )


def check_package_manifests() -> None:
    manifests = [
        p for p in ROOT.glob(".agents/**/package.json") if "node_modules" not in p.parts
    ]
    if not manifests:
        # A fork with zero portal skills installed (before the first
        # /job-add-portal, or between removing all portals and adding a
        # replacement) legitimately has no .agents/**/package.json yet, and
        # git does not track empty directories - .agents/skills/ can vanish
        # from disk entirely in that state. That is not the same failure as
        # the glob root being renamed/moved (which ROOT resolving from this
        # script's own path under tools/ already rules out), so only note it.
        print("note: .agents: no package.json files found (no portal skills installed yet)")
    for manifest in manifests:
        relpath = manifest.relative_to(ROOT)
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"{relpath}: unreadable or invalid JSON: {exc}")
            continue
        if not isinstance(data, dict):
            errors.append(f"{relpath}: top-level JSON value must be an object")
            continue
        scripts = data.get("scripts", {})
        if not isinstance(scripts, dict):
            errors.append(f"{relpath}: scripts must be an object")
            continue
        bad = FORBIDDEN_SCRIPTS & set(scripts)
        if bad:
            errors.append(
                f"{relpath}: lifecycle script(s) {sorted(bad)} are forbidden - they execute "
                "arbitrary code during `bun install` on every fork user's machine."
            )
        if "trustedDependencies" in data:
            errors.append(
                f"{relpath}: trustedDependencies is forbidden - it re-enables dependency "
                "lifecycle scripts that bun blocks by default."
            )


def main() -> int:
    # argparse 是标准库。**这里不能 import 本仓库的模块**（比如共享的命令行 helper）：
    # 这个脚本会被测试**单独拷进一个临时目录**跑（见 tests 里的 shutil.copy），
    # 拷过去的只有它自己，任何跨文件 import 都会在那边直接 ImportError。
    import argparse
    argparse.ArgumentParser(description="检查权限白名单、gitignore 与依赖清单").parse_args()
    check_permissions()
    check_gitignore()
    check_package_manifests()
    if errors:
        print(f"security_guards: {len(errors)} failure(s)")
        for err in errors:
            print(f"  - {err}")
        return 1
    print("security_guards: OK (permissions allowlist, gitignore rules, package manifests)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
