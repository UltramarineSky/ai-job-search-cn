"""`writeback.py`：深评写回是机械操作，不是纪律要求。

## 为什么有这个工具

分数存两处（evaluation.md 档案 + seen_jobs.json 库），靠「AI 记得写回」维持同步。
实测 4 个目录分叉了四个月没人发现——`resolve_score` 的兜底让面板永远显示对的，
分叉只伤读库的那一侧（/job-rank 选岗、预筛、/job-upskill）。

机制闭环是两半：导出器逐岗对账、发现分叉就自嚷（`export_web_data`），
本工具负责机械补账。这里测后一半的四条行为：

1. 试运行只报告不写盘（与 prescreen 同一惯例）；
2. `--apply` 写回分/判词/已深评标记/四维拆解，且**幂等**；
3. **文件自身违反判词天花板的拒收**（exit 1 并点名）——把违规值写进库
   等于把病搬家，文件是档案，工具不单边篡改；
4. 顺带清库内残留：已深评还挂「粗筛：」前缀、已评分还挂降权标记。
"""

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import writeback as wb  # noqa: E402

EVAL_OK = """# 职位评估：甲公司 - 产品经理

## 四维打分

| 维度 | 分数 | 说明 |
|---|---|---|
| 技能与经验 | **65** | 专业能力 70 × 0.6 + 业务域 58 × 0.4 |
| 薪资与职级 | 85 | 落在期望区间 |
| 强度与公司性质 | 70 | 上市公司 |
| 发展与风险 | 70 | 核心业务线 |

**综合得分：62/100**

## 结论

**值得投（62）**。
"""

#: 判词写高了一档：技能 55 属 40-59 档，最高只到「可以考虑」。
EVAL_CAPPED = EVAL_OK.replace("| 技能与经验 | **65** |", "| 技能与经验 | **55** |")


class _Repo(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        (self.d / ".active_user").write_text("测试", encoding="utf-8")
        u = self.d / "users" / "测试"
        (u / "job_scraper").mkdir(parents=True)
        self.apps = u / "documents" / "applications"
        self.sj = u / "job_scraper" / "seen_jobs.json"
        self._save({"seen": {
            "https://x/1#产品经理": {
                "url": "https://x/1", "title": "产品经理", "company": "甲公司",
                "status": "ranked", "rank_score": 76, "rank_verdict": "粗筛：强匹配",
                "rank_breakdown": {"技能与经验": 47},
            },
        }})
        self._olds = wb.ROOT, wb._cli.ROOT
        wb.ROOT = wb._cli.ROOT = self.d

    def tearDown(self):
        wb.ROOT, wb._cli.ROOT = self._olds

    def _save(self, store):
        self.sj.write_text(json.dumps(store, ensure_ascii=False), encoding="utf-8")

    def _dir(self, name, eval_text):
        d = self.apps / name
        d.mkdir(parents=True, exist_ok=True)
        (d / "posting.md").write_text("- 链接：https://x/1\n", encoding="utf-8")
        (d / "evaluation.md").write_text(eval_text, encoding="utf-8")

    def _run(self, *argv):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = wb.main(list(argv))
        return code, buf.getvalue()

    def _entry(self):
        return json.loads(self.sj.read_text(encoding="utf-8"))["seen"]["https://x/1#产品经理"]


class DryRunReportsButNeverWrites(_Repo):
    def test_drift_is_reported_and_store_untouched(self):
        self._dir("甲公司_产品经理", EVAL_OK)
        code, out = self._run()
        self.assertEqual(code, 0)
        self.assertIn("待写回", out)
        self.assertIn("76 → 62", out.replace(" ", "").replace("分", " 分").replace("→", " → ") or out)
        e = self._entry()
        self.assertEqual(e["rank_score"], 76, "试运行改了盘")
        self.assertNotIn("evaluated", e)


class ApplyWritesBackAndIsIdempotent(_Repo):
    def test_apply_then_clean(self):
        self._dir("甲公司_产品经理", EVAL_OK)
        code, out = self._run("--apply")
        self.assertEqual(code, 0, out)
        e = self._entry()
        self.assertEqual(e["rank_score"], 62)
        self.assertEqual(e["rank_verdict"], "值得投")
        self.assertTrue(e["evaluated"])
        self.assertEqual(e["rank_breakdown"]["技能与经验"], 65,
                         "四维拆解没跟着写回 —— /job-upskill 与面板四格读的是它")
        self.assertIn("专业能力70×0.6+业务域58×0.4", e["rank_breakdown"]["四维"])
        code2, out2 = self._run("--apply")
        self.assertEqual(code2, 0)
        self.assertIn("一致", out2, f"第二次跑还有变更，不幂等：{out2}")


class CapViolationsAreRefusedNotCopied(_Repo):
    def test_refuses_and_names_the_file(self):
        self._dir("甲公司_产品经理", EVAL_CAPPED)
        code, out = self._run("--apply")
        self.assertEqual(code, 1, "文件写高了判词却没报错")
        self.assertIn("拒收", out)
        self.assertIn("可以考虑", out, "没告诉人该压到哪一档")
        e = self._entry()
        self.assertEqual(e["rank_score"], 76,
                         "违规值被写进库了 —— 那是把病搬家，不是修病")


class StoreResidueIsSweptAlong(_Repo):
    def test_prefix_and_parking_marker(self):
        store = json.loads(self.sj.read_text(encoding="utf-8"))
        store["seen"]["https://x/2#乙岗"] = {
            "url": "https://x/2", "title": "乙岗", "company": "乙公司",
            "status": "ranked", "rank_score": 70,
            "rank_verdict": "粗筛：值得投", "evaluated": True,
            "deprioritized": {"依据": "旧标记"},
        }
        self._save(store)
        code, _ = self._run("--apply")
        self.assertEqual(code, 0)
        e = json.loads(self.sj.read_text(encoding="utf-8"))["seen"]["https://x/2#乙岗"]
        self.assertEqual(e["rank_verdict"], "值得投", "前缀残留没清")
        self.assertNotIn("deprioritized", e, "降权残留没清")


class ASkippedDirIsNeverReportedAsAgreement(unittest.TestCase):
    """读不出来的目录要说出来，不能报成「库与深评档案一致」。

    `read_dir` 对缺 `posting.md`（职位链接从那里取）的目录返回 None，原来是裸
    `continue`——跳过的一个字都不提。全部跳过时打印的是「库与深评档案一致，
    没有要写回的」，**把「我没看」说成了「都对得上」**。实测批量产出的 5 个
    目录只有 evaluation.md，五个全被静默跳过而工具报一致，深评结论一分钟都没
    进库。这与本仓库反复修的「解析为空说成核对通过」是同一个病。

    另一半是别过度报警：**硬性条件没过的评估按框架规定不打分**，它没有综合
    得分是对的，不该每次跑都对着一份正常评估喊「读不出来」。
    """

    EVAL = ("# 甲公司 — 岗A\n\n## 评分明细\n\n| 维度 | 分数 |\n|---|---|\n"
            "| 技能与经验 | 70 |\n\n**综合得分：70/100**\n\n## 结论：值得投\n")
    GATE_FAIL_EVAL = ("# 乙公司 — 岗B\n\n**综合得分：不打分（硬性条件没过）**\n\n"
                      "## 结论：不满足硬性条件\n")

    def _run(self, files):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            (root / "AGENTS.md").write_text("x", encoding="utf-8")
            (root / ".active_user").write_text("u", encoding="utf-8")
            u = root / "users" / "u"
            (u / "job_scraper").mkdir(parents=True)
            (u / "job_scraper" / "seen_jobs.json").write_text(
                json.dumps({"seen": {"https://x/1": {
                    "url": "https://x/1", "title": "岗A", "company": "甲公司",
                    "status": "ranked", "rank_score": 61,
                    "rank_verdict": "值得投"}}}, ensure_ascii=False),
                encoding="utf-8")
            d = u / "documents" / "applications" / "甲公司_岗A"
            d.mkdir(parents=True)
            for n, body in files.items():
                (d / n).write_text(body, encoding="utf-8")
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                wb.ROOT = root
                try:
                    wb.main([])
                finally:
                    wb.ROOT = ROOT
            return out.getvalue()

    def test_a_dir_without_posting_is_named_not_swallowed(self):
        got = self._run({"evaluation.md": self.EVAL})
        self.assertNotIn("库与深评档案一致", got,
                         f"跳过了一个目录却报「一致」：{got!r}")
        self.assertIn("甲公司_岗A", got, f"没说是哪个目录读不出来：{got!r}")

    def test_a_gate_fail_evaluation_is_written_back_not_skipped(self):
        """硬性条件没过的评估**照样要写回**：分清空、结论换掉、标已深评。

        原来 read_dir 对它返回 None（取不到整数分），于是这种评估永远进不了库；
        而 export 的分叉提醒照样逐次催「跑 writeback 补账」，本工具跑完却说
        「库与深评档案一致」——两个工具对同一个目录互相踢皮球，用户照提示跑命令、
        命令说没事、面板下次继续催，死循环。
        """
        got = self._run({"evaluation.md": self.GATE_FAIL_EVAL,
                         "posting.md": "- 链接：https://x/1\n"})
        self.assertNotIn("读不出来", got, f"有 posting 的硬门评估被当成残档：{got!r}")
        self.assertNotIn("一致", got, f"该写回的硬门结论被说成无事可做：{got!r}")
        self.assertIn("待写回", got, f"没把硬门结论列进待写回：{got!r}")
        self.assertIn("不满足硬性条件", got,
                      f"写回预告里没把结论译成人话：{got!r}")

    def test_a_gate_fail_dir_without_posting_is_still_flagged(self):
        """缺 posting.md 的目录不管是不是硬门评估都读不出来（链接从那里取）。"""
        got = self._run({"evaluation.md": self.GATE_FAIL_EVAL})
        self.assertIn("读不出来", got,
                      f"缺 posting 的目录没被点名：{got!r}")

    def test_the_message_has_no_markdown_bold(self):
        """终端不渲染 markdown——这条提示第一版就带着 `**`，自家守卫当场抓到。"""
        got = self._run({"evaluation.md": self.EVAL})
        self.assertNotRegex(got, r"\*\*[^*\n]+\*\*",
                            f"提示里有 markdown 粗体，用户看到的是星号：{got!r}")


if __name__ == "__main__":
    unittest.main()
