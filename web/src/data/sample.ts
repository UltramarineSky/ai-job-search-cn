import type { EnvItem, Job, NextStep, PipelineStage } from "../types";

/**
 * 演示数据 —— **全部虚构**。
 *
 * 真实运行时这些由后端从活动用户的
 * `users/<活动用户>/job_scraper/seen_jobs.json` + `job_search_tracker.csv` 读出，
 * 形状与 `types.ts` 一致即可直接替换本文件。
 *
 * ## 为什么是虚构的
 *
 * 这个文件在公开仓库里。真实跑批的评估内容会带出候选人的个人信息 ——
 * 能力边界（哪些技术不会）、学历口径、语言水平、薪资底线、通勤范围 ——
 * 那些属于 `profile/`（已 gitignore），不能以「演示数据」的名义进版本库。
 * 公司名同理：真实职位的公司 + 真实的负面评价放在公开仓库里也不合适。
 *
 * ## 但边界情况是真的
 *
 * 版面撑不撑得住取决于这些形状，所以每一种都留了一条：
 *
 * - 薪资三种口径混用：`40-60K·16薪`（月薪+薪数）、`3.5-5 万·15薪`、`4-6 万/月`（没写几薪）
 * - 公司名未公开（猎头代招 / 平台脱敏），公司背景查不到
 * - 硬性条件「还没查到」——既不算满足也不算不满足
 * - 判定基于资料里未确认的假设值（assumed）
 * - 某一项没有分数（`score: null`），不能当 0 画
 * - 不满足硬性条件 → 不进名单，但要能查到原因
 * - 待核实的信息（平台自相矛盾、主业与岗位跨度大）——不参与打分
 */

export const activeUser = "示例用户";

/**
 * 五个阶段是**真实先后顺序**（找 → 评 → 写 → 投 → 面），所以标了序号；
 * 序号在这里承载信息，不是装饰。措辞一律用求职者自己会说的话：
 * 「已抓取」是爬虫的说法，用户说的是「搜到多少个岗」。
 */
export const pipeline: PipelineStage[] = [
  { step: 1, label: "搜到职位", count: 110 },
  { step: 2, label: "打过分", count: 23 },
  { step: 3, label: "材料就绪", count: 3 },
  { step: 4, label: "已投递", count: 0 },
  { step: 5, label: "面试中", count: 0 },
];

export const nextStep: NextStep = {
  text: "材料写好了，但一条投递记录都还没有。投出去之后记一笔，后面跟进和面试准备都要用它",
  command: "/job-outcome <公司>",
};

export const envItems: EnvItem[] = [
  { name: "Node 22.18+", ok: true, detail: "v22.18.0", unlocks: "搜职位、打分排序" },
  { name: "Typst", ok: true, detail: "0.13.0", unlocks: "把简历编译成 PDF" },
  {
    name: "pdftotext",
    ok: true,
    detail: "已安装",
    unlocks: "检查简历 PDF 里的字能否被招聘系统读出",
  },
  {
    // 浏览器能力由 AI 工具提供，不是这个仓库的依赖 —— ok:null 表示不作判定
    name: "浏览器取数（由 AI 工具提供）",
    ok: null,
    detail: "Claude Code 装了浏览器扩展即可用",
    unlocks: "登录后抓 BOSS 直聘、智联招聘、前程无忧",
  },
];

export const jobs: Job[] = [
  {
    id: "j-agent-ux",
    url: "https://www.zhipin.com/job_detail/example0001.html",
    title: "智能助手 C 端产品专家",
    company: "某头部消费互联网公司（代招未具名）",
    anonymousEmployer: true,
    salary: "40-60K·16薪",
    location: "上海",
    experience: "5 年以上",
    channel: "BOSS 直聘",
    viaHeadhunter: true,
    score: 82,
    skill: 88,
    skillWhy: "Agent 架构与工具调用是他做了三年的主线",
    annual: { low: 64, high: 96, assumed12: false },
    verdict: "强匹配",
    materials: {
      greeting:
        "您好，看到贵司在招智能助手方向的 C 端产品专家。我近三年一直做面向个人用户的 " +
        "AI 产品，主导过多智能体协作与工具调用链路从设计到上线的完整过程，与岗位描述的方向一致。" +
        "作品和数据可以随时细聊，期待交流。",
      resumePdf: "documents/applications/示例互联网公司_智能助手C端产品专家/resume.pdf",
    },
    dimensions: [
      { name: "技能与经验", score: 88, weight: 30, note: "Agent 架构与工具调用直接对口" },
      { name: "薪资与职级", score: 85, weight: 25, note: "高于期望上沿" },
      { name: "强度与性质", score: 72, weight: 20, note: "上市公司" },
      { name: "发展与风险", score: 80, weight: 25, note: "做主智能体架构，赛道正" },
    ],
    gates: [
      { name: "学历院校", state: "pass", why: "本科即可，不限专业" },
      { name: "外包 / 驻场 / 派遣", state: "pass", why: "猎头代招甲方岗，不是派遣" },
      { name: "通勤时长", state: "pass", why: "上海市内" },
      { name: "公司背景", state: "unknown", why: "公司名没公开，查不到实体" },
      { name: "户口落户", state: "na", why: "这个岗不涉及" },
    ],
    gaps: [
      {
        kind: "任职要求",
        claim: "5 年以上互联网产品经验",
        detail: "示例：方向内年限不足，要靠作品体量补",
      },
    ],
    quality: [
      {
        title: "公司名没公开",
        detail:
          "平台只写「代招公司：某头部消费互联网公司」，定不到具体公司，公司背景和近期动向都没法核实。开场白改用 JD 自己写明的业务场景切入",
      },
    ],
  },
  {
    id: "j-remote-pm",
    url: "https://www.liepin.com/job/example0002.shtml",
    title: "AI 产品经理（远程居家办公）",
    company: "某人才服务集团（代招）",
    anonymousEmployer: true,
    salary: "40-60k",
    location: "远程",
    experience: "5-10 年",
    channel: "猎聘",
    viaHeadhunter: true,
    score: 77,
    skill: 86,
    skillWhy: "JD 点名的编码工具正是他的日常",
    annual: { low: 48, high: 72, assumed12: true },
    salaryMonthsUnknown: true,
    verdict: "强匹配",
    materials: {
      greeting:
        "您好，关注到这个远程 AI 产品经理岗位。我日常就在用 JD 里点名的 Claude Code 这类" +
        "智能体编码工具做产品原型，远程协作有成熟的节奏。方便的话想进一步了解业务场景。",
      resumePdf: "documents/applications/示例人才集团_AI产品经理远程/resume.pdf",
    },
    dimensions: [
      { name: "技能与经验", score: 86, weight: 30, note: "JD 点名 Claude Code 等编码工具" },
      { name: "薪资与职级", score: 80, weight: 25, note: "高于期望" },
      { name: "强度与性质", score: 74, weight: 20, note: "远程，不用通勤" },
      { name: "发展与风险", score: 64, weight: 25, note: "细分赛道，天花板待看" },
    ],
    gates: [
      { name: "通勤时长", state: "pass", why: "远程办公" },
      { name: "外包 / 驻场 / 派遣", state: "pass", why: "猎头代招甲方岗" },
      { name: "学历院校", state: "unknown", why: "要求统招本科，具体口径待确认" },
      { name: "公司背景", state: "unknown", why: "公司名没公开" },
      { name: "应届生 / 三方", state: "na", why: "社招，不涉及" },
    ],
    gaps: [
      {
        kind: "加分项",
        claim: "游戏化设计经验",
        detail: "示例：做过留存机制，游戏化的系统设计经验有限",
      },
    ],
    quality: [
      { title: "公司名没公开", detail: "猎头代招，未具名的甲方，公司信息没法核实" },
    ],
  },
  {
    id: "j-platform-pm",
    url: "https://www.zhaopin.com/jobdetail/example0003.html",
    title: "AI 产品经理",
    company: "示例科技（上海）有限公司",
    salary: "3.5-5 万·15薪",
    location: "上海徐汇",
    experience: "3-5 年",
    channel: "智联招聘",
    viaHeadhunter: false,
    score: 74,
    skill: 80,
    annual: { low: 52.5, high: 75, assumed12: false },
    verdict: "值得投",
    dimensions: [
      { name: "技能与经验", score: 80, weight: 30, note: "大模型应用全流程" },
      { name: "薪资与职级", score: 78, weight: 25, note: "15 薪，年包够期望" },
      { name: "强度与性质", score: 70, weight: 20, note: "甲方直招" },
      { name: "发展与风险", score: 68, weight: 25, note: "行业成熟，增速一般" },
    ],
    gates: [
      { name: "学历院校", state: "pass", why: "本科即可" },
      { name: "外包 / 驻场 / 派遣", state: "pass", why: "甲方直招" },
      { name: "通勤时长", state: "pass", why: "市内，60 分钟内" },
      { name: "户口落户", state: "na", why: "这个岗不涉及" },
    ],
    gaps: [
      { kind: "任职要求", claim: "行业 AI 产品落地", detail: "示例：该行业的门道要补" },
    ],
    quality: [],
  },
  {
    id: "j-solution-lead",
    url: "https://www.zhaopin.com/jobdetail/example0004.html",
    title: "AI 解决方案产品负责人",
    company: "示例远方数科有限公司",
    salary: "4-6 万/月",
    salaryMonthsUnknown: true,
    location: "上海闵行",
    experience: "3-5 年",
    channel: "智联招聘",
    viaHeadhunter: false,
    score: 63,
    skill: 52,
    skillWhy: "核心职责里的评测体系他完全没做过",
    annual: { low: 48, high: 72, assumed12: true, estimated: true },
    verdict: "值得投",
    materials: {
      greeting:
        "您好，看到贵司 AI 解决方案产品负责人的岗位。我做过企业侧 AI 产品从需求拆解到" +
        "落地的完整闭环，财务业务这块我会以最快速度补齐领域语言，想先约个时间了解岗位的实际边界。",
      resumePdf: "documents/applications/示例远方数科_AI解决方案产品负责人/resume.pdf",
      coverLetter: true,
    },
    dimensions: [
      { name: "技能与经验", score: 52, weight: 30, note: "核心职责有一条完全没做过" },
      { name: "薪资与职级", score: 72, weight: 25, note: "区间覆盖期望" },
      { name: "强度与性质", score: 62, weight: 20, note: "已上市" },
      { name: "发展与风险", score: 58, weight: 25, note: "领域跨度大" },
    ],
    gates: [
      { name: "学历院校", state: "pass", why: "本科即可，不限 211/985" },
      { name: "外包 / 驻场 / 派遣", state: "pass", why: "企业 HR 直招" },
      { name: "通勤时长", state: "pass", why: "闵行 · 60 分钟内" },
      { name: "工作年限", state: "unknown", why: "JD 没写具体怎么算" },
      { name: "语言要求", state: "unknown", why: "JD 没提，投前问清" },
      { name: "户口落户", state: "na", why: "这个岗不涉及" },
      { name: "应届生 / 三方", state: "na", why: "社招，不涉及" },
    ],
    gaps: [
      {
        kind: "核心职责",
        claim: "建立 AI 输出评测体系",
        detail:
          "示例：评测集建设、badcase 回流、自动化指标都没做过。能说的是产品判断层面的质量拆解",
        overclaim: "搭建过评测体系",
      },
      {
        kind: "任职要求",
        claim: "熟悉 Python 和 SQL",
        detail: "示例：能读懂逻辑、能借 AI 写出可用的东西",
        overclaim: "熟练 Python",
      },
      {
        kind: "领域空白",
        claim: "理解企业财务、销售、订单流程",
        detail: "示例：没做过这条业务线，相关业务语言要从零补",
      },
    ],
    quality: [
      {
        title: "平台两处信息对不上",
        detail:
          "列表页写「上市公司」，详情页写「未融资」。查外部资料支持列表页（确已上市），按列表页采信",
      },
      {
        title: "主业和这个岗差得远",
        detail:
          "公司主业是传统制造，这个岗做 B2B AI 财务助手。是新开的业务线还是内部信息化，公开信息不够判断",
      },
      {
        title: "薪资算不出年包",
        detail: "只给了月薪、没写几薪，年包定不下来（按 12 薪算是 48-72 万）",
      },
    ],
  },
  {
    id: "j-manufacturing-pm",
    url: "https://www.liepin.com/job/example0005.shtml",
    title: "AI 产品经理（智能制造方向）",
    company: "某人力资源服务商（示例）",
    salary: "25-35k·14薪",
    location: "上海静安",
    experience: "5-10 年",
    channel: "猎聘",
    viaHeadhunter: false,
    score: 57,
    verdict: "可以考虑",
    dimensions: [
      { name: "技能与经验", score: 70, weight: 30, note: "制造业 AI 应用对口" },
      { name: "薪资与职级", score: 48, weight: 25, note: "年包下沿低于你的底线" },
      { name: "强度与性质", score: 46, weight: 20, note: "跟谁签合同还没定" },
      { name: "发展与风险", score: null, weight: 25, note: "用工性质未定，这项先不打分" },
    ],
    gates: [
      { name: "学历院校", state: "pass", why: "学历不限" },
      {
        name: "外包 / 驻场 / 派遣",
        state: "unknown",
        why: "招人的是人力资源服务集团，JD 没写用工性质",
      },
      { name: "工作年限", state: "unknown", why: "要求 5-10 年，方向内不够" },
      { name: "户口落户", state: "na", why: "这个岗不涉及" },
      { name: "应届生 / 三方", state: "na", why: "社招，不涉及" },
    ],
    gaps: [
      { kind: "任职要求", claim: "5-10 年经验", detail: "示例：方向内年限不足" },
    ],
    quality: [
      {
        title: "跟谁签合同存疑",
        detail:
          "招人的是人力资源服务集团，JD 没写外包还是派遣，所以记「还没查到」而不判不满足——但如果你资料里写明「一律排除」，投前必须问清合同跟谁签",
      },
    ],
  },
  // ---- 不满足硬性条件：不进上面的名单，但要能查到为什么 ----
  {
    id: "j-director",
    url: "https://www.zhipin.com/job_detail/example0006.html",
    title: "AI 产品总监",
    company: "示例数字营销集团",
    salary: "70-100K·18薪",
    location: "上海长宁",
    experience: "10 年以上",
    channel: "BOSS 直聘",
    viaHeadhunter: false,
    score: null,
    verdict: "不满足硬性条件",
    gateFailReason:
      "学历不满足：JD 要求「计算机科学、软件工程、人工智能等相关专业硕士学历及以上」",
    dimensions: [],
    gates: [{ name: "学历院校", state: "fail", why: "要硕士 + 计算机相关专业" }],
    gaps: [],
    quality: [],
  },
  {
    id: "j-fund",
    url: "https://www.liepin.com/job/example0007.shtml",
    title: "基金-AI 产品经理",
    company: "某人才咨询（代招上市券商）",
    anonymousEmployer: true,
    salary: "25-35k·20薪",
    location: "上海陆家嘴",
    experience: "5 年以上",
    channel: "猎聘",
    viaHeadhunter: true,
    score: null,
    verdict: "不满足硬性条件",
    gateFailReason: "学历不满足：要硕士及以上 + 计算机 / AI / 金融工程 / 金融专业",
    dimensions: [],
    gates: [{ name: "学历院校", state: "fail", why: "要硕士及以上" }],
    gaps: [],
    quality: [],
  },
  {
    id: "j-research",
    url: "https://www.liepin.com/job/example0008.shtml",
    title: "AI 产品经理（行业研究方向）",
    company: "示例青梧咨询有限公司",
    salary: "20-35k·14薪",
    location: "上海黄浦",
    experience: "1-3 年",
    channel: "猎聘",
    viaHeadhunter: false,
    score: null,
    verdict: "不满足硬性条件",
    gateFailReason: "语言不满足：JD 明写「英语精通」，与你资料里写明的语言边界冲突",
    dimensions: [],
    gates: [{ name: "语言要求", state: "fail", why: "JD 明写英语精通" }],
    gaps: [],
    quality: [],
  },
];
