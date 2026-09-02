// 搜索卡片里那个人的**姓**：接口一直在给，而 CLI 一直只取了旁边那个角色标签。
//
// `recruiter` 对象每张卡片都有四个键：`recruiterId` / `recruiterName` /
// `recruiterTitle` / `recruiterPhoto`。此前只取了 `recruiterTitle` ——
// 实测样本 42 张卡片里它装的是**职务**：「猎头顾问」一个值就挂在 16 个不同的
// `recruiterId` 上，还有「HRBP」「招聘专员」「研发总监」和 4 张空串。
// **同一个值挂在十几个人身上，它标的就不是人。**
//
// 后果在很下游：台账的 `contact_person` 一列实测 0/85 有值，而三处在读它
// （`/job-outcome followup` 的跟进话术、Step 2b 起草的跟进、`/job-interview`
// 查面试官从哪切入），每一次都在走降级路径 —— 跟进消息称呼「团队」而不是
// 「<姓>女士」，而 `job-outcome.md` 写着那正是「群发」和「专门找我」的分界。
//
// **只吐姓，不吐全名。** 全名是第三方个人信息，下游要它只为一句称呼；
// 截断放在最上游，落了盘再脱敏等于赌后面每一层都记得脱。
import { describe, expect, test } from "bun:test"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"
import { parseJobCards, surnameOf } from "../src/helpers.js"

describe("surnameOf", () => {
  test("单姓取第一个字", () => {
    expect(surnameOf("张伟")).toBe("张")
  })

  test("复姓取两个字", () => {
    expect(surnameOf("欧阳修远")).toBe("欧阳")
    expect(surnameOf("司马青衫")).toBe("司马")
  })

  test("平台把称谓写进名字时先摘掉称谓", () => {
    // 「<姓>女士」这种写法直接切前两个字会得到「张女」。
    expect(surnameOf("张女士")).toBe("张")
    expect(surnameOf("李顾问")).toBe("李")
    expect(surnameOf("王HR")).toBe("王")
  })

  test("摘完称谓只剩一个字也照样成立", () => {
    expect(surnameOf("陈")).toBe("陈")
  })

  test("空、null、非字符串一律 null", () => {
    for (const v of ["", "   ", null, undefined, 42, {}]) {
      expect(surnameOf(v)).toBeNull()
    }
  })

  test("**非中文名一律 null —— 猜错就是把全名原样吐出去**", () => {
    // 拉丁名分不出姓在前在后。这是这个函数存在的理由之一，不是边角情况。
    expect(surnameOf("Alice Chen")).toBeNull()
    expect(surnameOf("chen")).toBeNull()
  })

  test("绝不返回全名", () => {
    for (const n of ["张伟", "欧阳修远", "李小明", "王大锤"]) {
      const got = surnameOf(n)!
      expect(got.length).toBeLessThanOrEqual(2)
      expect(n.startsWith(got)).toBe(true)
      expect(got).not.toBe(n)
    }
  })
})

describe("卡片带上这个姓", () => {
  const raw = JSON.parse(
    readFileSync(
      fileURLToPath(new URL("./fixtures/search-response.json", import.meta.url)),
      "utf-8",
    ),
  )
  const { cards } = parseJobCards(raw)

  test("每张卡片都有这个键（缺失值是 null，不省略键）", () => {
    expect(cards.length).toBeGreaterThan(0)
    for (const c of cards) {
      expect(c).toHaveProperty("recruiterSurname")
    }
  })

  test("样本里真的取到了", () => {
    expect(cards.some((c) => c.recruiterSurname)).toBe(true)
  })

  test("取的是姓，不是全名", () => {
    // 样本已脱敏成「招聘者A」这类占位，所以只能验形状：**不许超过两个字**。
    for (const c of cards) {
      if (c.recruiterSurname) expect(c.recruiterSurname.length).toBeLessThanOrEqual(2)
    }
  })

  test("**它和 `recruiterTitle` 不是一回事** —— 后者是角色标签", () => {
    // 这一条钉的正是当初取错字段的那个判断。
    const titles = new Set(cards.map((c) => c.recruiterTitle).filter(Boolean))
    for (const t of titles) {
      expect(surnameOf(t)).not.toBe(t) // 「猎头顾问」当姓用会切成「猎」
    }
    expect(cards.some((c) => c.recruiterTitle === "猎头顾问")).toBe(true)
  })

  test("既有的字段一个没动", () => {
    const c = cards[0]!
    for (const k of ["id", "title", "company", "url", "salary", "eduLevel",
                     "workYears", "compScale", "compIndustry", "isHeadhunter"]) {
      expect(c).toHaveProperty(k)
    }
  })
})
