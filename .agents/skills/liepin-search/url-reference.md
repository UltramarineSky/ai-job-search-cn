# 猎聘接口与解析锚点

> 本文件是 markup 变更时的维修手册。所有内容均由真实请求 / 真实 fixture 实测确认（2026-07-23）。

## 搜索接口

`POST https://api-c.liepin.com/api/com.liepin.searchfront4c.pc-search-job`

免登录。必需请求头：

| Header | 值 |
|---|---|
| `Content-Type` | `application/json` |
| `Origin` | `https://www.liepin.com` |
| `Referer` | `https://www.liepin.com/` |
| `X-Client-Type` | `web` |
| `X-Fscp-Version` | `1.1` |
| `X-Requested-With` | `XMLHttpRequest` |
| `X-Fscp-Std-Info` | `{"client_id": "40108"}` |
| `X-Fscp-Trace-Id` | 任意 UUID |
| `User-Agent` | 桌面 Chrome UA |

请求体：

```json
{
  "data": {
    "mainSearchPcConditionForm": {
      "city": "010", "dq": "010", "pubTime": "",
      "currentPage": 0, "pageSize": 40, "key": "关键词",
      "suggestTag": "", "workYearCode": "0",
      "compId": "", "compName": "", "compTag": "",
      "industry": "", "salary": "", "jobKind": "",
      "compScale": "", "compKind": "", "compStage": "", "eduLevel": ""
    },
    "passThroughForm": {
      "scene": "init", "skeyword": "关键词", "sfrom": "search_job_pc"
    }
  }
}
```

响应：

```
{ flag: 1, data: { data: { jobSubscribeInfo, jobCardList[], compList[] },
                   passThroughData, pagination } }
```

`pagination`：`{ pageSize, currentPage, hasNext, totalPage, totalCounts }`

### 字段路径

| 输出字段 | 来源 |
|---|---|
| `id` | `job.jobId` |
| `title` | `job.title` |
| `company` | `comp.compName` |
| `location` | `job.dq`（形如 `上海-浦东新区`） |
| `date` | `job.refreshTime`（`YYYYMMDDHHMMSS`）取前 8 位 |
| `url` | `job.link` |
| `salary` | `job.salary`（形如 `20-40k·15薪`，或 `薪资面议`） |
| `salaryMonths` | 从 `job.salary` 正则 `(\d+)\s*薪` 提取 |
| `eduLevel` | `job.requireEduLevel` |
| `workYears` | `job.requireWorkYears` |
| `compScale` | `comp.compScale` |
| `compIndustry` | `comp.compIndustry` |
| `compStage` | `comp.compStage`（可能为 `null`） |
| `recruiterTitle` | `recruiter.recruiterTitle` |
| `recruiterSurname` | `recruiter.recruiterName` 取姓（`surnameOf`，**不输出全名**）|
| `isHeadhunter` | `job.jobKind === "1"` |

### 已实测的坑

| 现象 | 说明 |
|---|---|
| `currentPage` 从 **0** 起 | CLI 的 `--page` 是 1 起始，内部减一 |
| `totalPage` 恒为 10 | 实际翻页上限 400 条 |
| `totalCounts` 报 ~800 | **不可信**，与 `totalPage` 矛盾 |
| `hasNext` 在第 0 页就是 `false` | **不可用**，改判 `currentPage + 1 < totalPage` |
| 每页 42 条 = 40 本市 + 2 非本市 | 推广位，CLI 不过滤 |
| `pubTime` 参数**无效** | 传 `1`（一天内）仍返回 2023 年职位；`--jobage` 必须客户端过滤 |
| `pubTime` 传非数字 | 响应缺 `pagination` 键，视为错误 |
| 无效城市码 | `totalCounts: 0` 且 `jobSubscribeInfo.dqName` 为 `null` |

## 城市码

已验证：北京 `010`、上海 `020`、天津 `030`、广州 `050020`、深圳 `050090`、
南京 `060020`、杭州 `070020`、合肥 `080020`、福州 `090020`、成都 `280020`。

**扩充方法（不要猜码）**：主搜索页页脚有城市 SEO 链接
`https://www.liepin.com/city-<slug>/zhaopin/`（如 `city-cd`、`city-wuhan`、`city-qingdao`）。
该页为 SSR，内嵌 `dqCode: <码>`，正则 `/dqCode["']?\s*[:=]\s*["']?(\d+)/` 即可提取。
验证方式：把码传给搜索接口，看 `jobSubscribeInfo.dqName` 是否回显预期城市名。

## 详情页

| 类型 | URL | 判据 |
|---|---|---|
| 企业直招 | `https://www.liepin.com/job/<id>.shtml` | `job.jobKind === "2"` |
| 猎头职位 | `https://www.liepin.com/a/<id>.shtml` | `job.jobKind === "1"` |

两者均为 SSR。路径拼错返回 **404**。

**推荐传完整 URL。** `resolveTarget`（`src/commands/detail.ts`）对裸数字 id 会先试
`/job/` 再试 `/a/`：猎头职位因此每次都要先发一次必然 404 的 `/job/` 请求，才落到
正确路径——多耗一次对猎聘的访问，与本项目「低频访问」的原则冲突。传完整 URL
（路径已确定）可以避免这次多余请求。

**正文锚点**：`<dd data-selector="job-intro-content">…</dd>`，在两种页面中都**恰好出现一次**。
正文换行是字面 `\n`，无需还原 `<br>`。

### 结构化数据（标题 / 公司名 / 地点）：优先用 JSON-LD

以下是 2026-07-23 用真实 fixture（`tests/fixtures/detail-job.html` 企业直招、
`tests/fixtures/detail-a.html` 猎头职位）实测确认的结论。

两个 fixture 里各有 **两个** `<script type="application/ld+json">` 块：

1. 第一个块没有 `@type`，是百度站内搜索用的 `cambrian.jsonld`：它的 `title` 字段
   就是整串 `<title>` 文本（`【上海 高级java开发工程师(A233284)招聘】-雪球科技
   上海招聘信息-猎聘`）——没用，跳过它。
2. 第二个块是 `"@type": "JobPosting"`，schema.org 标准结构化数据，字段干净可靠：
   - `title`：干净的职位名，如 `"高级java开发工程师(A233284)"`
     （猎头职位页这里带**尾随空格**，如 `"高级Java开发工程师 "`，要 trim）
   - `hiringOrganization.name`：**当前职位**的公司名，如 `"雪球科技"` / `"某宁波
     大型银行公司"`（已核对与搜索结果里同一职位的 `comp.compName` 一致）
   - `hiringOrganization.sameAs`：公司主页 URL
   - `jobLocation.address.streetAddress`：如 `"上海-浦东新区御桥路…"` / `"上海"`

定位这个块时**不要假设它总是第几个**，按内容找含 `"@type": "JobPosting"` 的那个
`<script type="application/ld+json">`。

> **维护提示**：`findJobPostingLdJson`（`src/helpers.ts`）目前取页面里**第一个**
> `@type: JobPosting` 的 ld+json 块，隐含假设了「当前职位」的结构化数据先于其他任何
> `JobPosting` 块出现。如果将来猎聘改版，在主职位之前插入了「相似职位推荐」之类的
> `JobPosting` 结构化数据，这个函数会取错块，取到别的职位的标题/公司名而不报错（因为
> `@type` 匹配依旧成立，不会触发 `PARSE_FAILED`）。排查详情页出现公司名/标题错误（尤其是
> 看起来像「别的职位」的数据）时，先检查页面里 `JobPosting` 块的数量与顺序，不要直接
> 假设是锚点本身失效。

**这个块不能直接整体 `JSON.parse`**：`description` 字段的字符串值里混着裸换行符，
是非法 JSON（实测报 `Invalid control character`）。可行的两种做法：
1. 定向正则按 key 提取需要的几个字段（本项目采用）——这几个字段本身不含裸换行，
   可以安全地用标准 JSON 字符串转义规则匹配，注意要处理字段值里可能出现的
   转义引号 `\"`（不能简单地找下一个 `"` 就当结尾）；
2. 或者把字符串里的裸控制字符转义之后再整体 `JSON.parse`。

两种都行，不要为了省事直接对整块调用 `JSON.parse`——会在真实页面上直接抛错。

**薪资仍然走 HTML 锚点**：`class="salary"`（**精确匹配，不是 `job-salary`**）。
JSON-LD 的 `baseSalary` 字段没有实际金额（`value` 里只有 `unitText`），不可用。
两个 fixture 分别在 `class="salary"` 给出 `20-35k` 与 `20-40k·15薪`，都是**当前
职位**的正确薪资。`job-salary` 命中的是侧边栏「相似职位推荐」卡片的薪资，不是
当前职位——这正是下面「已证伪的旧结论」踩的坑。

#### 已证伪的旧结论（不要再用）

| 字段 | 早前写的锚点 | 实测问题 |
|---|---|---|
| 标题 | `<h1>…</h1>` | 页面里根本没有 `<h1>`，永远匹配不到，回落成占位符 |
| 公司名 | `class="…name-box…"` | 文档顺序里**第一个** `name-box` 其实是当前职位自己的应聘卡片，不是侧边栏——旧正则贪婪匹配到第一个 `</div>`，把标题和薪资拼在了一起，取出来的不是干净的公司名 |
| 薪资 | `class="…job-salary…"` | 命中的才是侧边栏「相似职位推荐」卡片的薪资，混进了别的职位的数据 |

（`<title>` 标签解析仍保留作为标题的兜底：JSON-LD 缺失或取不到 `title` 时才用，
格式固定为 `【<城市> <职位名>招聘】-<后缀>-猎聘`，取「【」与「招聘】」之间的内容，
去掉城市名前缀。两者都取不到时回落为占位符 `"(未取到标题)"`，不抛错。）

### 详情页的临时限流（2026-07-23 触发，2026-07-24 自行解除）

**结论：这是临时限流，不是永久拦截，也不需要浏览器自动化。** 记录在此是为了让将来
遇到同样现象的人不要重蹈两次误判。

**现象**：开发期间对详情页做了较密集的请求后，`/job/<id>.shtml` 与 `/a/<id>.shtml`
开始一律 `302` 跳到 `https://wow.liepin.com/t1012695/transit.html`（内容仅 ~1.3KB，
正文只有备案页脚），`Set-Cookie` 带 `acw_tc`（`Max-Age=1800`）。CLI 表现为
`PARSE_FAILED` —— 页面抓到了但选不出 `job-intro-content`。

**已排除的错误结论**（都实测证伪过，别再走一遍）：

| 曾经的猜测 | 证伪方式 |
|---|---|
| 阿里云 WAF 的 JS 挑战，纯 HTTP 客户端过不去 | 解除后裸 `curl` 直接就能拿到正文，全程没执行任何 JS |
| 需要登录 | 解除后**匿名** `curl`（无任何 cookie）即可拿到正文 |
| 裸 URL 缺少 `dataPromId` 里的 `skId`/`ckId`/`sfrom` 等来路参数 | 解除后裸 URL（不带任何查询串）同样正常 |
| 需要特定 `Referer` | 解除后无 `Referer`、任意 `Referer` 均正常 |

当时之所以误判为「加参数就好了」，是因为带参数的那次请求恰好赶上限流到期，把**时间上的
巧合**读成了因果。

**正确的排查顺序**：`detail` 报 `PARSE_FAILED` 时，先直接用 `curl` 请求同一个 URL，
按响应形态分三种情形，**只有第三种才该怀疑锚点**：

| 响应形态 | 是什么 | CLI 归类 | 该怎么做 |
|---|---|---|---|
| ~1.3KB、无 `job-intro-content`、无 JSON-LD，或落点是 `wow.liepin.com/…/transit.html` | 限流挑战页 | `RATE_LIMITED` | **停手等待**（本次约一天后恢复，实际取决于此前请求量）。不要改锚点，不要引入浏览器自动化绕行 |
| HTTP **200** + 约 5KB、正文是「我们找遍了所有地方 / 此页面似乎不存在 / 4s 后将进入猎聘首页」 | **职位已下线的软 404**（猎聘不返回 404 状态码） | `NOT_FOUND` | 这条职位没了，**标记为过期**，不要重试、也不要改锚点 |
| **正常的详情页**（有 JSON-LD 或 `job-intro-content`）却选不出正文 | 锚点可能真失效了 | `PARSE_FAILED` | 这时才去查锚点 |

> 软 404 这条是 2026-07-30 实测补上的：当时对一个已下线职位（`/a/82583801.shtml`）
> 调 `detail`，返回 5335 字节、HTTP 200、两个锚点都没有。它比 transit 页大，落不进
> `isChallengePage` 的 `body.length < 4096` 启发式，于是被误报成 `PARSE_FAILED`
> 「猎聘改了 markup」——正好是本节警告过的那个陷阱。现按页面文案（而非体积）识别，
> 归 `NOT_FOUND`。

**范围**：限流期间 `search`（`api-c.liepin.com`）始终正常，多次调用均返回结构化数据；
搜索页 `www.liepin.com/zhaopin/` 的 HTML 也正常。只有详情页 SSR 被限。

**这件事的实践含义**：CLI 内置的 1.5 秒最小间隔是必要的但不充分——它只约束单进程。
真正决定会不会被限流的是**总请求量**。批量跑 `/job-rank` 时要控制并发与总量。

## 合规

- `www.liepin.com/robots.txt` 含 `Disallow: /*?*` —— 禁止带查询串的 www 路径。
  搜索走 `api-c.liepin.com`（该主机无 robots.txt），详情页 `/job/<id>.shtml` 与
  `/a/<id>.shtml` 不带查询串，不在禁止列表。
- 搜索页加载 `secscan-remote.js` 与 `security.min.js`（风控与指纹）。高频访问会触发验证。
- 结论：仅供个人使用，低频，SKILL.md 顶部带醒目警告。
