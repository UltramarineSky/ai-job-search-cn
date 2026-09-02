import { describe, expect, test } from "bun:test"
import {
  decodeHtmlEntities,
  stripTags,
  refreshTimeToDate,
  parseJobCards,
  parseSalaryMonths,
  extractIntro,
  parseJobDetail,
} from "../src/helpers.js"
import fixture from "./fixtures/search-response.json"

const jobHtml = await Bun.file(new URL("./fixtures/detail-job.html", import.meta.url)).text()
const aHtml = await Bun.file(new URL("./fixtures/detail-a.html", import.meta.url)).text()

describe("decodeHtmlEntities", () => {
  test("解码命名实体", () => {
    expect(decodeHtmlEntities("A&amp;B &lt;x&gt; &quot;q&quot;")).toBe('A&B <x> "q"')
  })

  test("解码十进制与十六进制数字实体", () => {
    expect(decodeHtmlEntities("&#33021;&#x529B;")).toBe("能力")
  })

  test("nbsp 变成普通空格", () => {
    expect(decodeHtmlEntities("a&nbsp;b")).toBe("a b")
  })
})

describe("stripTags", () => {
  test("剥离标签并压缩空白", () => {
    expect(stripTags("<p>岗位 <b>职责</b></p>")).toBe("岗位 职责")
  })
})

describe("refreshTimeToDate", () => {
  test("把 YYYYMMDDHHMMSS 转成 ISO 日期", () => {
    expect(refreshTimeToDate("20260710171849")).toBe("2026-07-10")
  })

  test("空值返回 null", () => {
    expect(refreshTimeToDate(null)).toBeNull()
    expect(refreshTimeToDate("")).toBeNull()
  })

  test("长度不足的脏数据返回 null 而不是抛错", () => {
    expect(refreshTimeToDate("2026")).toBeNull()
  })
})

describe("parseSalaryMonths", () => {
  test("从「20-40k·15薪」提取 15", () => {
    expect(parseSalaryMonths("20-40k·15薪")).toBe(15)
  })

  test("没有薪数时返回 null", () => {
    expect(parseSalaryMonths("20-35k")).toBeNull()
  })

  test("薪资面议返回 null", () => {
    expect(parseSalaryMonths("薪资面议")).toBeNull()
  })

  test("null 输入返回 null", () => {
    expect(parseSalaryMonths(null)).toBeNull()
  })
})

describe("parseJobCards", () => {
  const parsed = parseJobCards(fixture)

  test("解析出全部职位卡", () => {
    expect(parsed.cards.length).toBe(42)
  })

  test("分页信息来自 pagination", () => {
    expect(parsed.totalPage).toBe(10)
    expect(parsed.currentPage).toBe(0)
  })

  test("契约必需字段非空", () => {
    for (const c of parsed.cards) {
      expect(c.id).toBeTruthy()
      expect(c.title).toBeTruthy()
      expect(c.url).toMatch(/^https:\/\/www\.liepin\.com\//)
    }
  })

  test("date 是 ISO 日期", () => {
    expect(parsed.cards[0]!.date).toMatch(/^\d{4}-\d{2}-\d{2}$/)
  })

  test("jobKind=1 判定为猎头职位且链接走 /a/", () => {
    const hunters = parsed.cards.filter((c) => c.isHeadhunter)
    expect(hunters.length).toBeGreaterThan(0)
    for (const h of hunters) {
      expect(h.url).toContain("/a/")
      expect(h.recruiterTitle).toBe("猎头顾问")
    }
  })

  test("企业直招链接走 /job/", () => {
    const direct = parsed.cards.filter((c) => !c.isHeadhunter)
    expect(direct.length).toBeGreaterThan(0)
    for (const d of direct) {
      expect(d.url).toContain("/job/")
    }
  })

  test("缺失字段是 null 而不是被省略", () => {
    const withoutStage = parsed.cards.find((c) => c.compStage === null)
    expect(withoutStage).toBeDefined()
    expect(Object.keys(withoutStage!)).toContain("compStage")
  })

  test("flag 非 1 时抛错，不静默返回空数组", () => {
    expect(() => parseJobCards({ flag: 0, data: {} })).toThrow()
  })

  test("缺 pagination 时抛错", () => {
    expect(() => parseJobCards({ flag: 1, data: { data: { jobCardList: [] } } })).toThrow()
  })

  test("干净输入的 skipped 为 0", () => {
    expect(parsed.skipped).toBe(0)
  })

  test("一张坏卡（缺 jobId）被跳过，其余正常解析", () => {
    const broken = structuredClone(fixture) as typeof fixture
    delete (broken.data.data.jobCardList[0] as { job: { jobId?: string } }).job.jobId
    const result = parseJobCards(broken)
    expect(result.cards.length).toBe(parsed.cards.length - 1)
    expect(result.skipped).toBe(1)
  })

  test("解析过程中真正抛异常的卡也被计数为 skipped", () => {
    const broken = structuredClone(fixture) as typeof fixture
    Object.defineProperty(broken.data.data.jobCardList[0], "job", {
      get() {
        throw new Error("模拟解析异常")
      },
    })
    const result = parseJobCards(broken)
    expect(result.cards.length).toBe(parsed.cards.length - 1)
    expect(result.skipped).toBe(1)
  })

  test("全军覆没时抛错，而不是返回空数组", () => {
    const broken = structuredClone(fixture) as typeof fixture
    for (const card of broken.data.data.jobCardList) {
      delete (card as { job: { jobId?: string } }).job.jobId
    }
    expect(() => parseJobCards(broken)).toThrow()
  })

  // F1：jobId/refreshTime/jobKind 若被猎聘以 JSON number 下发，硬性要求 string 会
  // 让整卡被跳（进而全卡被跳→误报 PARSE_FAILED），且日期/猎头判定静默失效。
  test("数值型 jobId/refreshTime/jobKind 仍能解析，日期与猎头判定正确", () => {
    const variant = structuredClone(fixture) as typeof fixture
    const card0 = variant.data.data.jobCardList[0] as {
      job: { jobId: unknown; refreshTime: unknown; jobKind: unknown }
    }
    card0.job.jobId = 77763361 // number 而非 "77763361"
    card0.job.refreshTime = 20260710171849 // number 而非 "20260710171849"
    card0.job.jobKind = 1 // number 而非 "1"

    const result = parseJobCards(variant)
    // 卡片没被跳过：总数不变，skipped 为 0。
    expect(result.cards.length).toBe(parsed.cards.length)
    expect(result.skipped).toBe(0)

    const c0 = result.cards[0]!
    expect(c0.id).toBe("77763361")
    expect(c0.date).toBe("2026-07-10")
    expect(c0.isHeadhunter).toBe(true)
  })
})

describe("extractIntro", () => {
  test("从企业直招页提取职位正文", () => {
    const intro = extractIntro(jobHtml)
    expect(intro).toBeTruthy()
    expect(intro!.length).toBeGreaterThan(100)
  })

  test("从猎头职位页提取职位正文", () => {
    const intro = extractIntro(aHtml)
    expect(intro).toBeTruthy()
    expect(intro!.length).toBeGreaterThan(100)
  })

  test("正文不含 HTML 标签残留", () => {
    expect(extractIntro(jobHtml)).not.toContain("<")
  })

  test("正文保留换行结构", () => {
    expect(extractIntro(jobHtml)).toContain("\n")
  })

  test("没有锚点时返回 null", () => {
    expect(extractIntro("<html><body>空页</body></html>")).toBeNull()
  })
})

describe("parseJobDetail", () => {
  const jobUrl = "https://www.liepin.com/job/233284.shtml"
  const aUrl = "https://www.liepin.com/a/1.shtml"

  test("企业直招页：标题从 <title> 提取，去掉城市前缀与「【…招聘】」外壳", () => {
    const detail = parseJobDetail(jobHtml, "233284", jobUrl)
    expect(detail.title).toBe("高级java开发工程师(A233284)")
    expect(detail.title).not.toBe("(未取到标题)")
    expect(detail.title).not.toContain("【")
    expect(detail.title).not.toContain("招聘】")
  })

  test("猎头职位页：标题从 <title> 提取", () => {
    const detail = parseJobDetail(aHtml, "1", aUrl)
    expect(detail.title).toBe("高级Java开发工程师")
    expect(detail.title).not.toBe("(未取到标题)")
    expect(detail.title).not.toContain("【")
    expect(detail.title).not.toContain("招聘】")
  })

  test("企业直招页：薪资取自 class=\"salary\"（不是侧边栏推荐卡的 job-salary）", () => {
    const detail = parseJobDetail(jobHtml, "233284", jobUrl)
    expect(detail.salary).toBe("20-35k")
  })

  test("猎头职位页：薪资取自 class=\"salary\"", () => {
    const detail = parseJobDetail(aHtml, "1", aUrl)
    expect(detail.salary).toBe("20-40k·15薪")
  })

  test("企业直招页：company 取自 JSON-LD 的 hiringOrganization.name", () => {
    const detail = parseJobDetail(jobHtml, "233284", jobUrl)
    expect(detail.company).toBe("某上海互联网科技公司")
  })

  test("猎头职位页：company 取自 JSON-LD 的 hiringOrganization.name", () => {
    const detail = parseJobDetail(aHtml, "1", aUrl)
    expect(detail.company).toBe("某宁波大型银行公司")
  })

  test("企业直招页：location 取自 JSON-LD 的 jobLocation.address.streetAddress，以城市开头", () => {
    const detail = parseJobDetail(jobHtml, "233284", jobUrl)
    expect(detail.location).toBeTruthy()
    expect(detail.location).toMatch(/^上海/)
  })

  test("猎头职位页：location 取自 JSON-LD 的 jobLocation.address.streetAddress，以城市开头", () => {
    const detail = parseJobDetail(aHtml, "1", aUrl)
    expect(detail.location).toBeTruthy()
    expect(detail.location).toMatch(/^上海/)
  })

  test("猎头职位页：JSON-LD 的 title 字段带尾随空格，需 trim", () => {
    const detail = parseJobDetail(aHtml, "1", aUrl)
    expect(detail.title).toBe("高级Java开发工程师")
    expect(detail.title.endsWith(" ")).toBe(false)
  })

  test("JSON-LD 块含裸换行（description 字段）不能整体 JSON.parse，" +
    "但字段提取仍要成功——防止日后有人「顺手」改成直接 JSON.parse 而回归", () => {
    const ldJsonMatch = jobHtml.match(
      /<script type="application\/ld\+json">([\s\S]*?"@type":\s*"JobPosting"[\s\S]*?)<\/script>/,
    )
    expect(ldJsonMatch).toBeTruthy()
    // 确认这个真实块本身确实是非法 JSON（含裸换行），不是这条测试凭空假设的
    expect(() => JSON.parse(ldJsonMatch![1]!)).toThrow()

    // parseJobDetail 面对这个非法块仍要正确提取字段
    const detail = parseJobDetail(jobHtml, "233284", jobUrl)
    expect(detail.title).toBe("高级java开发工程师(A233284)")
    expect(detail.company).toBe("某上海互联网科技公司")
    expect(detail.location).toMatch(/^上海/)
  })

  test("isHeadhunter 由 URL 路径判定：/a/ 为猎头职位，/job/ 为企业直招", () => {
    expect(parseJobDetail(aHtml, "1", aUrl).isHeadhunter).toBe(true)
    expect(parseJobDetail(jobHtml, "233284", jobUrl).isHeadhunter).toBe(false)
  })

  test("没有 JSON-LD 也没有 <title> 标签时标题回落为占位符，而不是抛错；company/location 为 null", () => {
    const detail = parseJobDetail("<html><body>无标题页面</body></html>", "1", jobUrl)
    expect(detail.title).toBe("(未取到标题)")
    expect(detail.company).toBeNull()
    expect(detail.location).toBeNull()
  })

  // F2：schema.org 允许 jobLocation/hiringOrganization 是数组；此时应取首个对象，
  // 而不是静默丢失 location/company。
  test("jobLocation 是 Place 数组时，取首个对象的 address.streetAddress", () => {
    const html =
      "<html><head><title>t</title>" +
      '<script type="application/ld+json">' +
      '{"@type":"JobPosting","title":"数组地点职位",' +
      '"hiringOrganization":{"name":"某公司"},' +
      '"jobLocation":[{"@type":"Place","address":{"streetAddress":"上海市浦东新区某路1号"}},' +
      '{"@type":"Place","address":{"streetAddress":"北京市朝阳区"}}]}' +
      "</script></head>" +
      '<body><dd data-selector="job-intro-content">正文正文正文</dd></body></html>'
    const detail = parseJobDetail(html, "1", "https://www.liepin.com/job/1.shtml")
    expect(detail.location).toBe("上海市浦东新区某路1号")
    expect(detail.title).toBe("数组地点职位")
  })

  test("hiringOrganization 是数组时，取首个对象的 name", () => {
    const html =
      "<html><head><title>t</title>" +
      '<script type="application/ld+json">' +
      '{"@type":"JobPosting","title":"数组公司职位",' +
      '"hiringOrganization":[{"name":"首个公司"},{"name":"第二公司"}],' +
      '"jobLocation":{"address":{"streetAddress":"上海市"}}}' +
      "</script></head>" +
      '<body><dd data-selector="job-intro-content">正文正文正文</dd></body></html>'
    const detail = parseJobDetail(html, "1", "https://www.liepin.com/job/1.shtml")
    expect(detail.company).toBe("首个公司")
  })

  test("没有 JSON-LD 但有 <title> 标签时，标题回落到 <title> 解析", () => {
    const html =
      "<html><head><title>【上海 兜底职位招聘】-兜底公司上海招聘信息-猎聘</title></head>" +
      "<body>无 JSON-LD 的页面</body></html>"
    const detail = parseJobDetail(html, "1", jobUrl)
    expect(detail.title).toBe("兜底职位")
    expect(detail.company).toBeNull()
    expect(detail.location).toBeNull()
  })
})
