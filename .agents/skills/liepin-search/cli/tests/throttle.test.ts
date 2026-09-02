import { describe, expect, test } from "bun:test"
import { throttle } from "../src/helpers.js"

describe("throttle", () => {
  test("并发调用之间的放行时刻间隔不小于最小间隔", async () => {
    const timestamps: number[] = []

    // 并发发起 3 次调用；节流闸门必须把它们排队到 >=1500ms 的间隔上，
    // 而不是让它们读到同一个陈旧时间戳后一起放行。
    await Promise.all(
      [0, 1, 2].map(async () => {
        await throttle()
        timestamps.push(Date.now())
      }),
    )

    expect(timestamps.length).toBe(3)
    timestamps.sort((a, b) => a - b)
    for (let i = 1; i < timestamps.length; i++) {
      const gap = timestamps[i] - timestamps[i - 1]
      // 留一点时钟抖动余量
      expect(gap).toBeGreaterThanOrEqual(1400)
    }
  })
})
