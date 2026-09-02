import { describe, expect, test } from "bun:test"
import { parseFlags } from "../src/cli.js"
import { runCLI } from "./helpers.js"

describe("parseFlags 布尔 flag 不应吞掉后续的位置参数", () => {
  test("-h 后面的 detail 应该留在位置参数里，而不是被当成 -h 的值", () => {
    const flags = parseFlags(["-h", "detail"])
    expect(flags.h).toBe(true)
    expect(flags._).toEqual(["detail"])
  })
})

describe("parseFlags 应该把形似负数的 token 当成值消费，而不是当成新 flag", () => {
  test("--limit -1 应该解析成字符串 '-1'，而不是布尔 true", () => {
    const flags = parseFlags(["search", "-q", "Java", "-l", "北京", "--limit", "-1"])
    expect(typeof flags.limit).toBe("string")
    expect(flags.limit).toBe("-1")
    // 不应该把 "-1" 错当成一个新的、名为 "1" 的垃圾 flag
    expect(flags["1"]).toBeUndefined()
  })
})

describe("CLI 集成：cli -h detail（不发网络请求，help 分支在命令分发前就返回）", () => {
  test("显式求助应该退出 0 并打印帮助文本，而不是把 detail 吞成 -h 的值导致 cmd 为空", async () => {
    const r = await runCLI(["-h", "detail"])
    expect(r.exitCode).toBe(0)
    expect(r.stdout).toContain("liepin-cli")
  })
})
