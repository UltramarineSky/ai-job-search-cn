---
name: job-upskill
description: >
  拿库里的岗位跟你的资料比，算出经历对不上的地方，给一份排好优先级、
  带学习资源的补齐计划。
  触发词：我该学什么、能力差距、差在哪、学习计划、补短板、skill gaps、upskill、/job-upskill
allowed-tools: Read, Write, Glob, Grep, Bash(python tools/gap_split.py:*), Bash(python tools/applied_jds.py:*), WebFetch, WebSearch
---

# 补能力差距（壳）

读取并严格执行 `workflows/job-upskill.md`。

> `Bash(python tools/gap_split.py:*)` 是必需的：工作流明写「**用工具分，别手数**
> ——四格是机械的，手数容易错」。这条权限缺过一次，等于把唯一能分的那个工具
> 挡在门外（`tests/test_skill_permissions_cover_its_workflow.py` 现在盯着）。
>
> `applied_jds.py` 同理，它是 `--applied`（只算投过的那批）唯一的入口。
