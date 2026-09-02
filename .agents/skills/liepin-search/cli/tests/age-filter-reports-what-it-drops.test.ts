import { describe, expect, test } from "bun:test"
import { filterByAge } from "../src/commands/search.js"
import type { LiepinJobCard } from "../src/helpers.js"

function card(id: string, date: string | null): LiepinJobCard {
  return {
    id, title: "岗", company: null, location: null, date, url: `https://x/${id}`,
    salary: null, salaryMonths: null, eduLevel: null, workYears: null,
    compScale: null, compIndustry: null, compStage: null,
    recruiterTitle: null, recruiterSurname: null, isHeadhunter: false, description: null,
  } as LiepinJobCard
}

// 北京时间 2026-07-24
const now = Date.UTC(2026, 6, 23, 19, 0, 0)

describe("--jobage 丢掉的要报出来，而且两种原因分开报", () => {
  test("没有日期的卡片被丢掉，并计进 noDate", () => {
    const r = filterByAge([card("a", null), card("b", "2026-07-23")], 7, now)
    expect(r.cards.map((c) => c.id)).toEqual(["b"])
    expect(r.noDate).toBe(1)
    expect(r.tooOld).toBe(0)
  })

  test("太旧的计进 tooOld，不混进 noDate", () => {
    const r = filterByAge([card("a", "2026-01-01"), card("b", "2026-07-23")], 7, now)
    expect(r.cards.map((c) => c.id)).toEqual(["b"])
    expect(r.tooOld).toBe(1)
    expect(r.noDate).toBe(0)
  })

  test("两种混在一起时各数各的", () => {
    const r = filterByAge(
      [card("a", null), card("b", "2026-01-01"), card("c", null), card("d", "2026-07-24")],
      7, now,
    )
    expect(r.cards.map((c) => c.id)).toEqual(["d"])
    expect(r.noDate).toBe(2)
    expect(r.tooOld).toBe(1)
  })

  test("不传 --jobage 时一个都不丢，两个计数都是 0", () => {
    const cards = [card("a", null), card("b", "2020-01-01")]
    for (const days of [0, -1, 9999]) {
      const r = filterByAge(cards, days, now)
      expect(r.cards.length).toBe(2)
      expect(r.noDate).toBe(0)
      expect(r.tooOld).toBe(0)
    }
  })

  test("全被丢光时仍然报得出为什么", () => {
    const r = filterByAge([card("a", null), card("b", null)], 7, now)
    expect(r.cards.length).toBe(0)
    // 这正是下游最需要分清的一种：查到了 2 个，一个都没留下，
    // 而原因是「没日期」不是「没结果」。
    expect(r.noDate).toBe(2)
  })
})
