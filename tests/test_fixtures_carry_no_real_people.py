"""抓来的测试夹具里不许留着真人的信息。

## 为什么会有这个文件

`.agents/skills/liepin-search/cli/tests/fixtures/search-response.json` 是从猎聘搜索
接口**实抓**下来的一份响应，进了版本库。审计时才发现它带着 **31 个真实招聘者姓名、
82 个平台 ID、27 个头像标识**。

这跟仓库里别处的个人数据是两回事：那些是维护者**自己的**，泄了他自己认账；
这些是**别人的**——招聘者没同意过被写进一个公开仓库。而且 `recruiterId` / `imId`
是猎聘的账号标识，拿着它能直接定位到人。

夹具要的是**结构**，不是真名。所以真值一律换成合成值（`招聘者A`、确定性的假
哈希），换完 `bun test` 93 项照过——**没有一条测试断言在那些真值上**，
它们从一开始就只是抓下来忘了洗。

## 这条拦的是「下次再抓一份进来」

重新抓夹具是很自然的动作（接口字段变了就得更新）。而**洗数据不是自然动作**，
不写下来就会忘。所以判据放在夹具本身上，不放在流程上。
"""

import json
import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

#: 值里含真人信息的字段。键是字段名，值是「合成值长什么样」的判据。
PERSON_FIELDS = {
    "recruiterName": re.compile(r"^(招聘者|测试|示例|fixture|sample)"),
    "recruiterId": re.compile(r"^[0-9a-f]+$"),
    "imId": re.compile(r"^[0-9a-f]+$"),
    "recruiterPhoto": re.compile(r"^[0-9a-f]+$"),
}

#: 任何夹具里都不该出现的东西——不限字段，扫全文。
FORBIDDEN = {
    "手机号": re.compile(r"\b1[3-9]\d{9}\b"),
    "身份证": re.compile(r"\b[1-9]\d{5}(?:19|20)\d{2}[01]\d[0-3]\d[\dXx]\b"),
    "邮箱": re.compile(r"[\w.+-]+@[\w-]+\.[\w-]{2,}"),
}


def fixture_files():
    out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True,
                         text=True).stdout.split()
    return [ROOT / f for f in out
            if "/fixtures/" in f and Path(f).suffix in (".json", ".html", ".txt")]


class FixturesCarryNoRealPeople(unittest.TestCase):

    def test_there_are_fixtures_to_check(self):
        """控制用例：真有夹具，下面几条才不是空跑。"""
        self.assertTrue(fixture_files(), "一个夹具都找不到？这几条就没在验东西")

    def test_person_fields_hold_synthetic_values(self):
        bad = []
        for f in fixture_files():
            text = f.read_text(encoding="utf-8", errors="replace")
            for field, ok in PERSON_FIELDS.items():
                for m in re.finditer(rf'"{field}"\s*:\s*"([^"]*)"', text):
                    v = m.group(1)
                    if v and not ok.match(v):
                        bad.append(f"{f.relative_to(ROOT).as_posix()} 的 {field}"
                                   f" 还是实抓的值")
                        break
        self.assertEqual(
            sorted(set(bad)), [],
            "夹具里留着真人信息（招聘者的姓名 / 平台 ID）：\n  " + "\n  ".join(sorted(set(bad)))
            + "\n夹具要的是结构不是真名，重新抓完请把这些字段换成合成值")

    def test_no_contact_details_anywhere_in_a_fixture(self):
        bad = []
        for f in fixture_files():
            text = f.read_text(encoding="utf-8", errors="replace")
            for what, pat in FORBIDDEN.items():
                n = len(pat.findall(text))
                if n:
                    bad.append(f"{f.relative_to(ROOT).as_posix()}：{what} ×{n}")
        self.assertEqual(bad, [],
                         "夹具里有联系方式，那是能直接找到人的信息：\n  " + "\n  ".join(bad))

    def test_the_json_fixtures_still_parse(self):
        """洗过之后结构不能坏 —— 坏了 CLI 的测试会红得莫名其妙。"""
        for f in fixture_files():
            if f.suffix != ".json":
                continue
            with self.subTest(fixture=f.name):
                try:
                    json.loads(f.read_text(encoding="utf-8"))
                except json.JSONDecodeError as e:
                    self.fail(f"{f.name} 不是合法 JSON 了：{e}")


if __name__ == "__main__":
    unittest.main()
