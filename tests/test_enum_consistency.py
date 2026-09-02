"""双方枚举一致性：AGENTS.md 活动用户枚举 ↔ gitignore 守卫。

gmail_sync 缺口的成因是这两处各自为政。本测试以 AGENTS.md 枚举为**权威**：枚举里的
每一项都必须被 security_guards 的必需 gitignore 规则覆盖（或显式声明例外）。AGENTS.md
加了新的个人数据目录而守卫没跟上 → 本测试红。

原先这里还有第三方——一次性迁移脚本 `tools/migrate_to_multiuser.py`。它已随「只保留
公开仓库里真实会用到的东西」一并删除：那个脚本只服务于 3.0 之前的单租户布局升级，而
`profile/` 与 `users/` 都被 gitignore，新 clone 根本不存在需要迁移的旧数据。
"""

import re
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))
import security_guards  # noqa: E402

AGENTS_MD = REPO_ROOT / "AGENTS.md"

# 权威映射：AGENTS.md 枚举项 → 必需的 gitignore 规则。
# None 表示显式例外——仅由 "users/" 整体规则覆盖。
EXPECTED = {
    "profile/": "profile/",
    "job_scraper/": "**/job_scraper/seen_jobs.json",
    "job_search_tracker.csv": "job_search_tracker.csv",
    "documents/": "documents/applications/**",
    "resume/main.typ": "resume/main.typ",
    "cover_letter/main.typ": "cover_letter/main.typ",
    "reports/": "reports/",
    "gmail_sync/": "gmail_sync/",
    # 2026-08-22 起是整目录规则（同 gmail_sync/ 与 reports/）——
    # 扩展名通配只挡 md，落一个 .json 缓存就静默进版本库。
    "upskill/": "upskill/",
    # 守卫 None：枚举项解析出的真身是 users/<用户>/templates/active-*.md，只由
    # "users/" 整体规则兜住。根级 "templates/active-*.md" 是另一回事——含斜杠的
    # gitignore 模式根锚定，只能匹配误落到仓库根的那一份，见下面的专门断言。
    "templates/active-cv.md": None,
    "templates/active-cover-letter.md": None,
}


def parse_enumeration() -> set[str]:
    """抽出枚举句里反引号包裹的路径项（去掉尾部省略号）。"""
    text = AGENTS_MD.read_text(encoding="utf-8")
    m = re.search(r"任何命令/技能里提到\s*(.*?)时，\*\*一律解析", text, re.S)
    assert m, "AGENTS.md 枚举句结构变了——同步更新本测试的抽取正则"
    return {t.rstrip("…") for t in re.findall(r"`([^`]+)`", m.group(1))}


class EnumConsistencyTests(unittest.TestCase):
    def test_enumeration_matches_expected(self):
        """枚举与权威映射互为镜像：任一侧多出条目都必须显式处理。"""
        self.assertEqual(parse_enumeration(), set(EXPECTED))

    def test_every_item_covered_by_guards(self):
        rules = security_guards.REQUIRED_IGNORE_RULES
        for item, guard in EXPECTED.items():
            with self.subTest(item=item):
                if guard is None:
                    self.assertIn("users/", rules)   # 例外项由 users/ 整体规则兜住
                else:
                    self.assertIn(guard, rules)

    def test_root_level_activation_fallback_rule_present(self):
        """根级激活文件的兜底规则不得消失。

        `.active_user` 缺失时 /job-add-template 可能把激活文件写到仓库根；这条规则拦住
        误提交。它**不能**替代 "users/"——含斜杠的 gitignore 模式是根锚定的，匹配不到
        users/<用户>/templates/ 下的真身。
        """
        rules = security_guards.REQUIRED_IGNORE_RULES
        self.assertIn("templates/active-*.md", rules)
        self.assertIn("users/", rules)

    def test_personal_data_rules_are_required(self):
        """.gitignore 里的个人数据规则必须都被守卫要求，否则删掉它们守卫照样报 OK。"""
        for rule in ("**/job_scraper/notion_sync.json", "**/job_scraper/*.md",
                     "documents/postings/**", ".claude/settings.local.json"):
            with self.subTest(rule=rule):
                self.assertIn(rule, security_guards.REQUIRED_IGNORE_RULES)


if __name__ == "__main__":
    unittest.main()
