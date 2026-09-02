---
name: job-application-assistant
description: >
  求职顾问与材料助手：看这个岗能不能投、按岗位改简历、写打招呼话术和求职信、
  准备面试。聊到求职就自动接管，不必记命令。
  触发词：求职、投递、这个岗能投吗、简历、求职信、面试、岗位匹配、职业规划、
  job posting、CV、cover letter、interview prep、apply
allowed-tools: Read, Glob, Grep, WebFetch, WebSearch, Edit, Write, AskUserQuestion
---

# 求职助手（壳）

求职咨询语境的触发壳。角色定义与全局规则见根目录 `AGENTS.md`；评估框架与文风资料：

- `workflows/reference/03-writing-style.md` —— 写作风格与铁律
- `workflows/reference/04-job-evaluation.md` —— 职位评估框架（硬门+四维+真伪信号）
- `workflows/reference/05-cv-templates.md` —— 简历模板规则
- `workflows/reference/06-outreach-templates.md` —— 三渠道话术与求职信
- `workflows/reference/07-interview-prep.md` —— 面试准备

## 这个壳自己做不了投递，到那一步要让用户敲命令

**它只做咨询**：读资料、给判断、写字。真要出材料那一步 —— 深评、定制简历、
编译 PDF、双角色审稿 —— **让用户敲 `/job-apply <职位链接>`**（要定制简历是
`/job-cv <职位链接>`）。那两条命令的 stub 没有 frontmatter，不受本壳的权限限制。

**权限窄是有意的，不是漏了。** 这个壳是**聊到求职就自动接管**的，而
`workflows/job-apply.md` 的代码块里要跑四类命令（`typst compile`、`typst fonts`、
`pdftotext -layout -enc UTF-8`、渠道 CLI），还要起并行子代理做审稿 —— 上面那行
`allowed-tools` 里 **Bash 和 Agent 一个都没有**（2026-08-24 核过）。
一个凭一句话就自动接管的壳，手里不该攥着编译、写盘、起子代理这些能力；
**够不着不是缺陷，是这个壳的边界**。

所以到了那一步**别硬走**（照着工作流跑到一半撞权限，用户看到的是一堆失败的
命令），也别绕道用 `Write` 手搓一份材料 —— 直接把命令给他。判据同
`AGENTS.md`「每一处引导都要写出该敲的命令」。
