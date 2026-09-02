import { describe, expect, test } from "bun:test"
import { beijingDate, filterByAge } from "../src/commands/search.js"
import type { LiepinJobCard } from "../src/helpers.js"

function card(id: string, date: string | null): LiepinJobCard {
  return {
    id,
    title: `职位${id}`,
    company: null,
    location: null,
    date,
    url: `https://www.liepin.com/job/${id}.shtml`,
    salary: null,
    salaryMonths: null,
    eduLevel: null,
    workYears: null,
    compScale: null,
    compIndustry: null,
    compStage: null,
    recruiterTitle: null, recruiterSurname: null,
    isHeadhunter: false,
  }
}

describe("beijingDate", () => {
  test("北京时间 00:00-08:00 这个窗口里，北京日期比 UTC 日期大一天", () => {
    // 选一个具体、非 Date.now() 的时间戳：UTC 2026-07-23T19:00:00Z
    // 对应北京时间 2026-07-24T03:00:00（北京已经跨入次日凌晨，UTC 还停在前一天）
    const ms = Date.UTC(2026, 6, 23, 19, 0, 0)
    const utcDate = new Date(ms).toISOString().slice(0, 10)
    expect(utcDate).toBe("2026-07-23")
    expect(beijingDate(ms)).toBe("2026-07-24")
  })

  test("北京时间 08:00 之后，北京日期与 UTC 日期相同", () => {
    // UTC 2026-07-23T01:00:00Z -> 北京时间 2026-07-23T09:00:00
    const ms = Date.UTC(2026, 6, 23, 1, 0, 0)
    expect(beijingDate(ms)).toBe("2026-07-23")
  })
})

describe("filterByAge 时区正确性", () => {
  // 固定的「现在」：UTC 2026-07-23T19:00:00Z == 北京时间 2026-07-24T03:00:00
  // 这正是 bug 描述的窗口：北京已经是 07-24，UTC 还是 07-23。
  const now = Date.UTC(2026, 6, 23, 19, 0, 0)

  test("--jobage 7 不应放进北京日历下 8 天前的职位", () => {
    // 该职位 refreshTime 对应的北京日历日期是 2026-07-16，
    // 相对北京「今天」2026-07-24 已经是 8 天前，--jobage 7 应当排除它。
    const cards = [card("a", "2026-07-16")]
    const result = filterByAge(cards, 7, now)
    expect(result.cards.length).toBe(0)
    expect(result.tooOld).toBe(1)
  })

  test("--jobage 7 应当放进北京日历下恰好 7 天前的职位（边界含入）", () => {
    const cards = [card("b", "2026-07-17")]
    const result = filterByAge(cards, 7, now)
    expect(result.cards.length).toBe(1)
    expect(result.tooOld).toBe(0)
  })
})
