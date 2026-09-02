---
name: job-scrape
description: >
  抓新岗并自动评分：各平台收集、自动去重，抓完直接接批量打分，给出可以投的岗位，
  不停在「待评」。有免登录接口的走接口（猎聘），其余用浏览器读页面；只抓不评加 --no-rank。
  触发词：找职位、找新岗、抓职位、有没有新岗位、搜岗、find jobs、job scrape、/job-scrape
allowed-tools: Read, Write, Edit, Glob, Grep, Bash(node --version), Bash(node .agents/skills/*/cli/src/cli.ts:*), Bash(bun --version), Bash(bun run .agents/skills/*/cli/src/cli.ts:*), Bash(python tools/doctor.py:*), Bash(python tools/query_yield.py:*), Bash(python tools/jd_store.py:*), Bash(python tools/export_web_data.py:*), Bash(python tools/portal_budget.py:*), WebFetch, WebSearch, Agent, AskUserQuestion
---

# 找职位（壳）

读取并严格执行 `workflows/job-scrape.md`（结构模板与 CDP 参考在 `workflows/reference/`）。

> 上面 `allowed-tools` 里那五条 `python tools/*.py` 不是备用的：工作流要用它们
> 写词表产出（`query_yield`）、合并 JD 详情（`jd_store`）、收尾重导面板
> （`export_web_data`）、开工前看进度（`doctor`），以及**每家动手前过额度闸门**
> （`portal_budget`，Step 0.46）。少一条，那一步就够不着——
> 闸门够不着的后果尤其实在：2026-08-19 用户的猎聘账号被标异常、要短信验证。
> 改工作流时顺手核一眼——`tests/test_skill_permissions_cover_its_workflow.py` 会比。
