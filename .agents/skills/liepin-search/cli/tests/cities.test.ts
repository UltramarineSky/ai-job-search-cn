import { describe, expect, test } from "bun:test"
import { resolveCity, knownCityNames } from "../src/cities.js"

describe("resolveCity", () => {
  test("中文城市名解析为城市码", () => {
    expect(resolveCity("北京")).toBe("010")
    expect(resolveCity("上海")).toBe("020")
    expect(resolveCity("深圳")).toBe("050090")
    expect(resolveCity("成都")).toBe("280020")
  })

  test("带「市」后缀也能解析", () => {
    expect(resolveCity("杭州市")).toBe("070020")
  })

  test("已经是城市码时原样返回", () => {
    expect(resolveCity("050020")).toBe("050020")
  })

  test("未知城市返回 null", () => {
    expect(resolveCity("瓦坎达")).toBeNull()
  })

  test("首尾空白不影响解析", () => {
    expect(resolveCity("  南京 ")).toBe("060020")
  })
})

describe("knownCityNames", () => {
  test("返回全部已知城市名，供报错时提示", () => {
    const names = knownCityNames()
    expect(names).toContain("北京")
    expect(names.length).toBeGreaterThanOrEqual(10)
  })
})
