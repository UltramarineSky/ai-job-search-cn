import { afterEach, describe, expect, test } from "bun:test"
import { apiFetch, htmlFetch, LiepinError, classifyNetworkError } from "../src/helpers.js"

// helpers.ts 里 fetch/text() 都走全局 fetch，直接改写 globalThis.fetch 即可注入。
const originalFetch = globalThis.fetch
afterEach(() => {
  globalThis.fetch = originalFetch
})

const detailHtml = await Bun.file(new URL("./fixtures/detail-job.html", import.meta.url)).text()
const transitHtml = await Bun.file(new URL("./fixtures/detail-transit.html", import.meta.url)).text()
const soft404Html = await Bun.file(new URL("./fixtures/detail-soft404.html", import.meta.url)).text()

const jobUrl = "https://www.liepin.com/job/233284.shtml"
const searchBody = { data: {} }

function timeoutError(): Error {
  const e = new Error("The operation timed out.")
  e.name = "TimeoutError"
  return e
}

describe("B1 · transit 限流挑战页归为 RATE_LIMITED，而非误报 PARSE_FAILED", () => {
  test("body 启发式：短页、无 ld+json、无 job-intro-content → RATE_LIMITED", async () => {
    globalThis.fetch = (async () =>
      new Response(transitHtml, {
        status: 200,
        headers: { "content-type": "text/html" },
      })) as typeof fetch
    let caught: unknown
    try {
      await htmlFetch(jobUrl)
    } catch (e) {
      caught = e
    }
    expect(caught).toBeInstanceOf(LiepinError)
    expect((caught as LiepinError).code).toBe("RATE_LIMITED")
    // 关键：绝不是 PARSE_FAILED（那会把用户误导去改解析锚点）。
    expect((caught as LiepinError).code).not.toBe("PARSE_FAILED")
  })

  test("重定向落点主机 wow.liepin.com/transit.html → RATE_LIMITED（即便 body 不算短）", async () => {
    globalThis.fetch = (async () => {
      const res = new Response("<html>" + "x".repeat(9000) + "</html>", { status: 200 })
      Object.defineProperty(res, "url", {
        value: "https://wow.liepin.com/t1012695/transit.html",
      })
      Object.defineProperty(res, "redirected", { value: true })
      return res
    }) as typeof fetch
    let caught: unknown
    try {
      await htmlFetch(jobUrl)
    } catch (e) {
      caught = e
    }
    expect((caught as LiepinError).code).toBe("RATE_LIMITED")
  })

  test("正常详情页（有 ld+json 与 job-intro-content）不被误判为挑战页", async () => {
    globalThis.fetch = (async () => new Response(detailHtml, { status: 200 })) as typeof fetch
    const html = await htmlFetch(jobUrl)
    expect(html).toContain("job-intro-content")
  })
})

describe("B2 · 网络错误/超时会退避重试，最终归为 NETWORK/TIMEOUT", () => {
  test("htmlFetch：前 2 次网络错误后成功 → 重试而非直接失败", async () => {
    let calls = 0
    globalThis.fetch = (async () => {
      calls++
      if (calls <= 2) throw new TypeError("fetch failed") // 模拟 DNS/连接重置
      return new Response(detailHtml, { status: 200 })
    }) as typeof fetch
    const html = await htmlFetch(jobUrl)
    expect(calls).toBe(3)
    expect(html).toContain("job-intro-content")
  })

  test("apiFetch：前 1 次超时后成功 → 重试而非直接失败", async () => {
    let calls = 0
    globalThis.fetch = (async () => {
      calls++
      if (calls === 1) throw timeoutError()
      return new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { "content-type": "application/json" },
      })
    }) as typeof fetch
    const json = (await apiFetch(searchBody)) as { ok: boolean }
    expect(calls).toBe(2)
    expect(json.ok).toBe(true)
  })

  // 退避循环「最后一击」的整段实跑要经历 6 次指数退避（~25s），不宜每次跑测都等；
  // 这里直接断言分类函数（循环最终抛的就是它的返回值），覆盖 NETWORK/TIMEOUT 归类。
  test("classifyNetworkError：超时 → TIMEOUT，其余网络错误 → NETWORK", () => {
    expect(classifyNetworkError(timeoutError()).code).toBe("TIMEOUT")
    const abort = new Error("aborted")
    abort.name = "AbortError"
    expect(classifyNetworkError(abort).code).toBe("TIMEOUT")
    expect(classifyNetworkError(new TypeError("fetch failed")).code).toBe("NETWORK")
    expect(classifyNetworkError("ECONNRESET").code).toBe("NETWORK")
  })
})

describe("B1b · 已下线职位的 HTTP 200 软 404 页归为 NOT_FOUND，而非误报 PARSE_FAILED", () => {
  // 猎聘对已下线的职位不返回 404，而是 HTTP 200 + 一个 5.3KB 的
  // 「我们找遍了所有地方 / 此页面似乎不存在 / 4s 后将进入猎聘首页」页面。
  // 它既无 ld+json 也无 job-intro-content，但比 transit 挑战页大，落不进
  // body.length < 4096 的启发式，于是被下游误报成 PARSE_FAILED
  // 「猎聘改了 markup」—— 那会把维护者引向去改解析锚点，而 url-reference.md
  // 明确警告不要那么做。正确结论是这条职位没了，调用方该标 expired。
  test("软 404 页 → NOT_FOUND，且绝不是 PARSE_FAILED / RATE_LIMITED", async () => {
    globalThis.fetch = (async () =>
      new Response(soft404Html, {
        status: 200,
        headers: { "content-type": "text/html" },
      })) as typeof fetch
    let caught: unknown
    try {
      await htmlFetch(jobUrl)
    } catch (e) {
      caught = e
    }
    expect(caught).toBeInstanceOf(LiepinError)
    expect((caught as LiepinError).code).toBe("NOT_FOUND")
    expect((caught as LiepinError).code).not.toBe("PARSE_FAILED")
    expect((caught as LiepinError).code).not.toBe("RATE_LIMITED")
  })

  test("控制用例：正常详情页不得被判成 NOT_FOUND（修复前后均应为绿）", async () => {
    globalThis.fetch = (async () =>
      new Response(detailHtml, { status: 200, headers: { "content-type": "text/html" } })) as typeof fetch
    const html = await htmlFetch(jobUrl)
    expect(html.length).toBeGreaterThan(4096)
  })
})
