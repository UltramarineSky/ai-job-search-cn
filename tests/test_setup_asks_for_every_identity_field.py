"""模板「身份」一节的每个字段，问卷都得问到。

## 漏掉的那一个有三个下游

`profile.example/candidate.md` 的「身份」一节列了 12 个字段。`/job-setup` 的 Section 1
问了其中 11 个——**唯独没问「到岗时间」**（`[YOUR_AVAILABILITY]`）。

而这个字段有三处消费方：

- 简历上「随时到岗」那一行直接取自它
- `/job-apply` 的渠道判定：猎头看的是「能不能推进去」，对方问起时要答得出
- `07-interview-prep.md`：HR 初面要确认职级、汇报线、到岗时间

（2026-08-17 起它**不再**进打招呼开场白——`06-outreach-templates.md` 的
「这 200 字里不许出现的五类」把到岗时间列为不写。字段本身照旧要问，
下游三处只是换成了上面这三个。）

问卷不问 → 字段留着占位符 → 三处要么空着，要么执行者现编一个。
而 `profile_ready` 现在按「模板占位符还剩几个」判断，留着它就永远判不到「已就绪」。

## 判据

「身份」一节里每个 `- **标签：** [占位符]` 的标签，都要能在 `setup.md` 里找到
（中文标签或它的英文说法，见 `ALIASES`）。新增字段时问卷要一起改。
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCAFFOLD = ROOT / "profile.example" / "candidate.md"
SETUP = ROOT / "workflows" / "job-setup.md"

#: 问卷里可能用英文问的字段。中文标签之外的合法说法都列上——
#: 判据认的是「问没问到这件事」，不是「用没用同一个词」。
ALIASES = {
    "姓名": ("Full name",),
    "现居城市": ("Location", "城市"),
    "手机": ("Phone", "电话"),
    "邮箱": ("email",),
    "作品集 / 个人主页": ("作品集", "个人主页", "portfolio"),
    "语言": ("Languages",),
    # 2026-08-20 job-setup.md 翻成中文之后，问卷里问的是「在职状态」；
    # 英文说法留着——判据认的是「问没问到这件事」，不是「用没用同一个词」。
    "求职状态": ("在职状态", "employment status"),
    "户口所在地": ("户口",),
    "应届生身份": ("应届生",),
    "竞业限制": ("竞业",),
    "到岗时间": ("到岗", "availability", "notice period"),
}


def identity_fields() -> list:
    """模板「身份」一节里的字段标签。"""
    t = SCAFFOLD.read_text(encoding="utf-8")
    m = re.search(r"^## 身份\n(.*?)^## ", t, re.S | re.M)
    if not m:
        return []
    return [x.split("（")[0].strip()
            for x in re.findall(r"^-\s*\*\*(.+?)：\*\*", m.group(1), re.M)]


class SetupAsksForEveryIdentityField(unittest.TestCase):

    def test_the_scan_finds_the_fields(self):
        """控制用例：真抽到了字段，否则下面那条永远绿。"""
        f = identity_fields()
        self.assertGreaterEqual(len(f), 8,
                                f"「身份」一节只抽到 {len(f)} 个字段：{f}")

    def test_every_field_is_asked_about(self):
        setup = SETUP.read_text(encoding="utf-8").lower()
        bad = []
        for lab in identity_fields():
            keys = (lab,) + ALIASES.get(lab, ())
            if not any(k.lower() in setup for k in keys):
                bad.append(f"「{lab}」（也找过：{ALIASES.get(lab, ())}）")
        self.assertEqual(
            bad, [],
            "模板里有这些字段，问卷却没问：" + chr(10) + "  " + (chr(10) + "  ").join(bad)
            + chr(10) + "不问 → 留着占位符 → 用到它的地方要么空着、要么现编；"
            + chr(10) + "而 profile_ready 按「占位符还剩几个」判，留一个就永远不算就绪。"
            + chr(10) + "换了说法而不是真漏，就往 ALIASES 里加一行。")

    def test_the_detector_can_actually_fail(self):
        """变异内建：编一个模板里没有的字段，检查器必须认不出来。"""
        setup = SETUP.read_text(encoding="utf-8").lower()
        self.assertNotIn("星座与血型", setup, "这个词竟然真在 setup.md 里？")


if __name__ == "__main__":
    unittest.main()
