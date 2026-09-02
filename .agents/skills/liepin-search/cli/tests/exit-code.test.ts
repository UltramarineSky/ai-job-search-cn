/**
 * CLI 必须用 `process.exitCode` 设退出码，不能用 `process.exit()`。
 *
 * ## 为什么
 *
 * `htmlFetch`/`jsonFetch` 用了 `AbortSignal.timeout(15000)`，fetch 提前完成时那个
 * 定时器还挂着。`process.exit()` 会在句柄正在关闭的当口强杀进程，Windows 上稳定触发：
 *
 *     Assertion failed: !(handle->flags & UV_HANDLE_CLOSING), file src\win\async.c
 *
 * 现象极具迷惑性：**JSON 已经完整写到 stdout 了，退出码却是 127**。
 * 实测 `detail` 命令 100% 复现（3 次连跑，输出 3004/2526/1995 字节全部有效，
 * 退出码全是 127）；`search` 不受影响，它只发一次请求。
 *
 * 后果不是崩一次那么简单：`workflows/job-scrape.md` 明确要求「CLI 非零退出就记录错误
 * 并继续」，于是**每一条 detail 结果都被当成失败丢掉**——职位的薪资、学历、年限
 * 就这样静默地进不了 `seen_jobs.json`，打分时 45% 的权重没有依据。
 *
 * 这条测试只查源码写法，不发网络请求，所以在 CI 里也能跑。
 */

import { describe, expect, test } from "bun:test"
import { readFileSync } from "node:fs"
import { join } from "node:path"

const CLI_SRC = readFileSync(join(import.meta.dir, "..", "src", "cli.ts"), "utf8")

describe("退出码设置方式", () => {
  test("不出现 process.exit( —— 它会在句柄关闭途中强杀进程", () => {
    // 允许注释里提到这个名字（要解释为什么不能用），只禁止真正的调用。
    const withoutComments = CLI_SRC.split("\n")
      .filter((ln) => !ln.trim().startsWith("//") && !ln.trim().startsWith("*"))
      .join("\n")
    expect(withoutComments).not.toContain("process.exit(")
  })

  test("用 process.exitCode 设置退出码", () => {
    expect(CLI_SRC).toContain("process.exitCode")
  })

  test("成功与失败两条路径都设了退出码", () => {
    // .then 里设 main() 的返回码，.catch 里设 1
    expect(CLI_SRC).toMatch(/\.then\([^)]*\)\s*=>\s*\{[\s\S]{0,80}process\.exitCode/)
    expect(CLI_SRC).toMatch(/catch[\s\S]{0,400}process\.exitCode = 1/)
  })

  test("原因写在注释里，免得下次被'简化'回 process.exit()", () => {
    expect(CLI_SRC).toContain("UV_HANDLE_CLOSING")
    expect(CLI_SRC).toContain("AbortSignal.timeout")
  })
})
