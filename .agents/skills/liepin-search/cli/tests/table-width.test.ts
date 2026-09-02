import { describe, expect, test } from "bun:test"
import { displayWidth, padTo, renderTable } from "../src/commands/search.js"
import type { LiepinJobCard } from "../src/helpers.js"

function card(id: string, title: string): LiepinJobCard {
  return {
    id,
    title,
    company: "—",
    location: "—",
    date: "2026-07-20",
    url: `https://www.liepin.com/job/${id}.shtml`,
    salary: "—",
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

describe("displayWidth", () => {
  test("纯中文：每个字占 2 列", () => {
    expect(displayWidth("职位")).toBe(4)
  })

  test("纯 ASCII：每个字符占 1 列", () => {
    expect(displayWidth("Job")).toBe(3)
  })

  test("中英混合", () => {
    expect(displayWidth("Java工程师")).toBe(4 + 3 * 2)
  })

  test("全角标点也占 2 列", () => {
    expect(displayWidth("你好，世界！")).toBe(12)
  })
})

describe("padTo", () => {
  test("按显示宽度补齐，而不是按字符数", () => {
    const padded = padTo("职位", 10)
    expect(displayWidth(padded)).toBe(10)
  })

  test("截断中文时不按字符数切，而是按显示宽度切，且不产生宽度溢出", () => {
    // "职位职位职位"视觉宽度 12，超出目标宽度 10；截断后应恰好 <=10
    // 且不能把最后一个双宽字符切成半个字符导致宽度计算错误
    const padded = padTo("职位职位职位", 10)
    expect(displayWidth(padded)).toBe(10)
  })

  test("不切断代理对（星形平面的 CJK 扩展字）", () => {
    // U+20000 是 CJK 扩展 B 的第一个字，UTF-16 下是代理对（2 个 code unit）
    const wideChar = String.fromCodePoint(0x20000)
    const s = wideChar + wideChar + wideChar // 视觉宽度 6
    const padded = padTo(s, 5)
    // 截断后不应该出现孤立的半个代理对（那样 .length 会是奇数但仍能安全往返）
    expect([...padded].every((ch) => ch.length === 1 || ch.length === 2)).toBe(true)
    expect(displayWidth(padded)).toBeLessThanOrEqual(5)
    // padTo 应该整字符截断：结果要么是 0、1 或 2 个完整的 wideChar 加空格补齐
    expect(padded.startsWith(wideChar) || padded.trim() === "").toBe(true)
  })
})

describe("renderTable 中文对齐", () => {
  test("除标题外其余字段完全相同的两行，整行显示宽度不应因标题是中文还是英文而不同", () => {
    // 两张卡片除了 title（10 个 ASCII 字符 vs 10 个中文字符）外，其余字段完全相同。
    // 标题列如果按显示宽度而不是字符数补齐/截断，两行的总显示宽度必须相等，
    // 否则后面的公司/地点/薪资/更新列在终端里就会错位。
    const cards = [card("1", "A".repeat(10)), card("2", "职".repeat(10))]
    const table = renderTable(cards)
    const rows = table.split("\n").slice(2)
    expect(displayWidth(rows[0]!)).toBe(displayWidth(rows[1]!))
  })

  test("每个定宽字段补齐后本身的显示宽度都精确等于目标宽度（不多不少）", () => {
    const cards = [card("1", "职位职位职位职位职位职位职位职位职位职位")] // 20 个中文字，视觉宽度 40，超出 30
    const table = renderTable(cards)
    const row = table.split("\n")[2]!
    // 按定宽字段依次切分（用 displayWidth 累加而不是裸 .slice，因为 padTo 对宽字符的
    // 截断补齐后原始码元数不一定等于目标显示宽度）
    function takeField(s: string, width: number): { field: string; rest: string } {
      let w = 0
      let i = 0
      for (const ch of s) {
        w += displayWidth(ch)
        i += ch.length
        if (w >= width) break
      }
      return { field: s.slice(0, i), rest: s.slice(i) }
    }
    let rest = row
    for (const width of [11, 30, 22, 16, 14]) {
      const { field, rest: r } = takeField(rest, width)
      expect(displayWidth(field)).toBe(width)
      rest = r.slice(1) // 跳过字段间的分隔空格
    }
  })
})
