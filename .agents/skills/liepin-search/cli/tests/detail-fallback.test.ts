import { afterEach, describe, expect, test } from "bun:test"
import { runDetail } from "../src/commands/detail.js"

// 猎聘详情页有两条路径：企业直招 /job/<id>.shtml、猎头职位 /a/<id>.shtml。
// 只给裸数字 id 时分不出是哪一种，`resolveTarget` 依次试两条。
//
// 这个回退是照着「拼错的那条返回 404、htmlFetch 返回空串」写的。但猎聘对不存在的
// 详情页**返回 HTTP 200** 加一个「此页面似乎不存在」页（network-boundary.test.ts
// 的 B1b 就是为它加的），helpers 把它抛成 `LiepinError NOT_FOUND`。抛出去之后
// 循环连第二条路径都到不了——**猎头职位用裸 id 永远取不到**，还报「该职位大概率
// 已下线，请标记为过期」，于是 fetch_details.py 把一个活着的岗写成 expired。

const originalFetch = globalThis.fetch
const originalWrite = process.stdout.write
afterEach(() => {
  globalThis.fetch = originalFetch
  process.stdout.write = originalWrite
})

const soft404 = await Bun.file(
  new URL("./fixtures/detail-soft404.html", import.meta.url),
).text()
const detailA = await Bun.file(
  new URL("./fixtures/detail-a.html", import.meta.url),
).text()

/** 只有 /a/ 那条路径有内容，/job/ 一律返回软 404 —— 猎头职位的真实形状。 */
function onlyHeadhunterPathExists() {
  globalThis.fetch = (async (input: string | URL | Request) => {
    const url = typeof input === "string" ? input : input.toString()
    const body = url.includes("/a/") ? detailA : soft404
    return new Response(body, {
      status: 200,
      headers: { "content-type": "text/html" },
    })
  }) as typeof fetch
}

function captureStdout(): { out: () => string } {
  let buf = ""
  process.stdout.write = ((chunk: unknown) => {
    buf += String(chunk)
    return true
  }) as typeof process.stdout.write
  return { out: () => buf }
}

describe("裸 id 的路径回退：第一条走空不是终局", () => {
  test("猎头职位（只有 /a/ 有内容）用裸 id 也取得到", async () => {
    onlyHeadhunterPathExists()
    const cap = captureStdout()
    const code = await runDetail({ id: "1983665159", format: "json" })
    expect(code).toBe(0)
    expect(cap.out()).toContain("\"url\"")
    expect(cap.out()).toContain("/a/")
  })

  test("两条路径都是软 404 时，仍然如实报 NOT_FOUND", async () => {
    globalThis.fetch = (async () =>
      new Response(soft404, {
        status: 200,
        headers: { "content-type": "text/html" },
      })) as typeof fetch
    captureStdout()
    const errs: string[] = []
    const origErr = process.stderr.write
    process.stderr.write = ((c: unknown) => {
      errs.push(String(c))
      return true
    }) as typeof process.stderr.write
    try {
      const code = await runDetail({ id: "1983665159", format: "json" })
      expect(code).toBe(1)
      expect(errs.join("")).toContain("NOT_FOUND")
    } finally {
      process.stderr.write = origErr
    }
  })

  test("给了完整 URL 就只有一条路径，软 404 直接是终局，不再多打一次猎聘", async () => {
    let calls = 0
    globalThis.fetch = (async () => {
      calls += 1
      return new Response(soft404, {
        status: 200,
        headers: { "content-type": "text/html" },
      })
    }) as typeof fetch
    captureStdout()
    const origErr = process.stderr.write
    process.stderr.write = (() => true) as typeof process.stderr.write
    try {
      const code = await runDetail({
        id: "https://www.liepin.com/job/1983665159.shtml",
        format: "json",
      })
      expect(code).toBe(1)
      expect(calls).toBe(1)
    } finally {
      process.stderr.write = origErr
    }
  })
})
