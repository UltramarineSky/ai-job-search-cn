import { describe, expect, test } from "bun:test"
import { runCLI } from "./helpers.js"

describe("CLI 参数校验（不发网络请求）", () => {
  test("缺少 --location 时报错退出", async () => {
    const r = await runCLI(["search", "-q", "Java"])
    expect(r.exitCode).toBe(1)
    expect(JSON.parse(r.stderr).code).toBe("NO_LOCATION")
    expect(r.stdout).toBe("")
  })

  test("未知城市名报错并提示可选值", async () => {
    const r = await runCLI(["search", "-q", "Java", "-l", "瓦坎达"])
    expect(r.exitCode).toBe(1)
    const err = JSON.parse(r.stderr)
    expect(err.code).toBe("BAD_CITY")
    expect(err.error).toContain("北京")
  })

  test("--page 非数字时报错", async () => {
    const r = await runCLI(["search", "-q", "Java", "-l", "北京", "--page", "abc"])
    expect(r.exitCode).toBe(1)
    expect(JSON.parse(r.stderr).code).toBe("BAD_ARG")
  })

  test("未知命令报错", async () => {
    const r = await runCLI(["frobnicate"])
    expect(r.exitCode).toBe(1)
    expect(JSON.parse(r.stderr).code).toBe("BAD_CMD")
  })

  test("detail 缺少 id 时报错", async () => {
    const r = await runCLI(["detail"])
    expect(r.exitCode).toBe(1)
    expect(JSON.parse(r.stderr).code).toBe("NO_ID")
  })

  test("无参数时打印帮助并退出 1", async () => {
    const r = await runCLI([])
    expect(r.exitCode).toBe(1)
    expect(r.stdout).toContain("liepin-cli")
  })
})
