import { describe, expect, test } from "bun:test"
import { parseJobCards, LiepinError } from "../src/helpers.js"

describe("错误分类走 code 字段，而不是正则匹配消息文本", () => {
  test("flag !== 1 时抛出的错误 code 是 RATE_LIMITED", () => {
    expect.assertions(2)
    try {
      parseJobCards({ flag: 0, data: {} })
    } catch (e) {
      expect(e).toBeInstanceOf(LiepinError)
      expect((e as LiepinError).code).toBe("RATE_LIMITED")
    }
  })

  test("缺 pagination 时抛出的错误 code 是 PARSE_FAILED", () => {
    expect.assertions(2)
    try {
      parseJobCards({ flag: 1, data: { data: { jobCardList: [] } } })
    } catch (e) {
      expect(e).toBeInstanceOf(LiepinError)
      expect((e as LiepinError).code).toBe("PARSE_FAILED")
    }
  })

  test("接口给了卡片但一张都没解析成功时，code 是 PARSE_FAILED", () => {
    expect.assertions(2)
    const payload = {
      flag: 1,
      data: {
        pagination: { currentPage: 0, totalPage: 1, totalCounts: 1 },
        data: { jobCardList: [{ job: {}, comp: {}, recruiter: {} }] },
      },
    }
    try {
      parseJobCards(payload)
    } catch (e) {
      expect(e).toBeInstanceOf(LiepinError)
      expect((e as LiepinError).code).toBe("PARSE_FAILED")
    }
  })
})
