// 在线冒烟测试：会发真实请求到猎聘，默认跳过。
// 开启方式：LIEPIN_LIVE=1 bun test tests/search.live.test.ts
//
// 之所以默认跳过：CI 里发真实请求既会触发猎聘风控，也会让构建结果随线上数据漂移。
// 解析逻辑的回归由 tests/parsing.test.ts 的离线 fixture 覆盖。

import { describe, expect, test } from "bun:test"
import { runCLI, parseJSON } from "./helpers.js"

const live = process.env.LIEPIN_LIVE === "1"

describe.skipIf(!live)("在线冒烟", () => {
  test("搜索返回真实结果", async () => {
    const r = await runCLI(["search", "-q", "Java", "-l", "北京", "--limit", "5"])
    const out = parseJSON<{ meta: { count: number }; results: Array<Record<string, unknown>> }>(r)
    expect(out.results.length).toBeGreaterThan(0)
    for (const job of out.results) {
      expect(job.id).toBeTruthy()
      expect(job.title).toBeTruthy()
      expect(String(job.url)).toContain("liepin.com")
      expect(String(job.title)).not.toContain("<")
    }
  })

  test("detail 返回可读正文", async () => {
    const s = await runCLI(["search", "-q", "Java", "-l", "北京", "--limit", "1"])
    const out = parseJSON<{ results: Array<{ url: string }> }>(s)
    const r = await runCLI(["detail", out.results[0]!.url, "--format", "plain"])
    expect(r.exitCode).toBe(0)
    expect(r.stdout.length).toBeGreaterThan(200)
    expect(r.stdout).not.toContain("<div")
  })
})
