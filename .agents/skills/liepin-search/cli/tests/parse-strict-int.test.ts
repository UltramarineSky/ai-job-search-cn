import { describe, expect, test } from "bun:test"
import { parseStrictInt } from "../src/cli.js"
import { runCLI } from "./helpers.js"

describe("parseStrictInt 严格校验整数字面量", () => {
  test("拒绝带拖尾垃圾字符的输入（parseInt 会静默截断的那种）", () => {
    expect(parseStrictInt("3abc")).toBeNull()
    expect(parseStrictInt("7xyz")).toBeNull()
    expect(parseStrictInt("5oops")).toBeNull()
  })

  test("接受纯整数字面量，包括带前导负号的", () => {
    expect(parseStrictInt("42")).toBe(42)
    expect(parseStrictInt("0")).toBe(0)
    expect(parseStrictInt("-7")).toBe(-7)
  })

  test("拒绝空串、小数、纯字母、纯符号", () => {
    expect(parseStrictInt("")).toBeNull()
    expect(parseStrictInt("3.5")).toBeNull()
    expect(parseStrictInt("abc")).toBeNull()
    expect(parseStrictInt("-")).toBeNull()
  })
})

describe("CLI 集成：--page 3abc 必须报 BAD_ARG（在 apiFetch 之前短路，不发网络请求）", () => {
  test("退出 1，stderr 的 code 是 BAD_ARG", async () => {
    const r = await runCLI(["search", "-q", "Java", "-l", "北京", "--page", "3abc"])
    expect(r.exitCode).toBe(1)
    const err = JSON.parse(r.stderr)
    expect(err.code).toBe("BAD_ARG")
    expect(r.stdout).toBe("")
  })
})
