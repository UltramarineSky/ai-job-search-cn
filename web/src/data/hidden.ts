import type { Job } from "../types";

/**
 * 屏蔽偏好：不想看的公司、职位、列
 *
 * ## 和「不投」是两件事
 *
 * `excluded.ts` 管的是**对这一个岗的判断**——「这个我不投」，要写回盘上，
 * 别的地方（`/job-rank`、报表、催进度）都得认。
 *
 * 这里管的是**看的时候不想看见**。它是纯视图偏好：不改任何岗的状态、
 * 不写盘、不影响计数口径以外的任何东西。把两者混在一起会出事——
 * 「这家公司我投过了，列表里别再显示」不等于「这家公司的岗我都不投」，
 * 后者会让下个月这家开了个好岗时你完全看不见。
 *
 * 所以：**只存 localStorage，随时可以全部清掉**。清掉之后一个岗都不会丢。
 *
 * ## 为什么需要它
 *
 * 用户 2026-08-13：「某些公司投过的，让用户选择是否隐藏。比如隐藏某些公司、
 * 某些职位、某些字段」。名单长到 90 行时，翻的成本主要来自**已经处理过的噪音**：
 * 同一家公司挂七八个岗、标题里带「销售」的一眼就不想看、某几列从来不看。
 * 这些都不该靠每次滚动时用眼睛过滤。
 */

const KEY = "jobSearchHidden.v1";

/**
 * localStorage 的键**按活动用户分开**。
 *
 * 多人共用一份 clone 时，每个人的数据在 `users/<名字>/` 下各自独立——切换用户那个
 * 弹窗里就印着这句话。而浏览器里这份偏好原来是**全局一把键**：甲把「字节」加进
 * 屏蔽词、切成乙、刷新，乙的名单里那些岗**静默少掉**，他不会知道少了什么，
 * 更不会想到是别人的过滤器还挂着。
 *
 * 视图偏好不写盘、不改任何岗的状态，但它**藏东西**——这个仓库对「静默吞掉」
 * 一贯的判据是：宁可多显示一条，不可让人不知道自己没看见。
 *
 * 空用户名（快照还没到、或压根没有活动用户）用不带后缀的旧键，
 * 这样存量偏好不会在升级当天凭空消失。
 */
export function userKey(base: string, user: string): string {
  return user ? `${base}:${user}` : base;
}

/**
 * 表格里可以关掉的列。
 *
 * **只列真实存在的列。** 第一版顺手写了「硬性条件」——而那一列早在更早的版本里
 * 就撤掉了（`Shortlist.tsx` 里留着当时的注释）。给一个关不掉的东西加开关，
 * 用户点了没反应，只会以为功能坏了。
 *
 * `score`（分数与判词）和职位名那一列不给关：前者是这张表存在的理由，
 * 后者关掉就不知道每行是什么了。
 */
export const HIDEABLE_COLUMNS: { key: string; label: string }[] = [
  { key: "skill", label: "技能" },
  { key: "annual", label: "年包" },
];

export interface HiddenPrefs {
  /**
   * 投过的公司，它别的岗也藏起来。**默认关**。
   *
   * 默认是「显示 + 打一个『这家投过』的标记」——用户 2026-08-13：
   * 「投过的公司也显示，不过提示该公司投过，让用户自己选择是否屏蔽」。
   * 藏掉等于替他做决定：同一家公司的另一个岗可能正是更合适的那个，
   * 而他连看都看不到。标记把事实给他，选择留给他。
   */
  appliedCompanies: boolean;
  /**
   * **这个岗自己已经投出去了，就别再显示。默认关。**
   *
   * 与上面那条是两回事：那条藏的是「这家公司的**别的**岗」，这条藏的是
   * 「**这一个**岗，我已经发过了」。
   *
   * 默认视图（可以投的岗位）本来就不列已投的，所以这个开关咬的是**点开
   * 流水线格子之后**的那几张表。实测活动用户 2026-08-26：「材料就绪」
   * 那一格 244 个里 **83 个已经投出去了**（34%），可投档 133 个里 62 个已投
   * —— 点进去要找「还没发的那批」，得先用眼睛把三分之一滤掉。
   *
   * 仍然默认关：已投的行上有状态按钮（约面了 / 挂了 / 没下文），
   * 藏掉就没地方点了。要不要藏是他的选择，不是默认。
   */
  applied: boolean;
  /** 按公司名屏蔽（子串匹配，大小写不敏感） */
  companies: string[];
  /** 按职位关键词屏蔽（子串匹配） */
  titles: string[];
  /** 关掉的列，取值来自 HIDEABLE_COLUMNS 的 key */
  columns: string[];
}

export const EMPTY: HiddenPrefs = {
  appliedCompanies: false, applied: false, companies: [], titles: [], columns: [],
};

export function loadHidden(user = ""): HiddenPrefs {
  try {
    // 这个用户自己那份；没有就退回旧的全局键（升级前存的，归当时在用的人）。
    const raw = localStorage.getItem(userKey(KEY, user))
      ?? (user ? localStorage.getItem(KEY) : null);
    if (!raw) return EMPTY;
    const d = JSON.parse(raw);
    // 逐字段兜底：**存量结构少一个键不该让整份偏好失效**。
    // 直接 `return d` 的话，加一个新字段就会让老用户的浏览器上
    // `d.columns` 是 undefined，渲染时 `.includes` 当场炸。
    return {
      appliedCompanies: Boolean(d?.appliedCompanies),
      applied: Boolean(d?.applied),
      companies: Array.isArray(d?.companies) ? d.companies.filter(Boolean) : [],
      titles: Array.isArray(d?.titles) ? d.titles.filter(Boolean) : [],
      columns: Array.isArray(d?.columns) ? d.columns.filter(Boolean) : [],
    };
  } catch {
    return EMPTY;
  }
}

export function saveHidden(p: HiddenPrefs, user = ""): void {
  try {
    localStorage.setItem(userKey(KEY, user), JSON.stringify(p));
  } catch {
    /* 隐私模式下 localStorage 会抛。偏好丢了不影响任何数据，静默即可。 */
  }
}

/** 归一化：去空白、转小写。公司名大小写混写很常见（acme / Acme / ACME）。 */
const norm = (s: string) => (s || "").trim().toLowerCase();

/**
 * 这个岗要不要藏起来。
 *
 * `appliedTo` 是**已投过的公司名集合**（已归一化），由调用方从当前快照算——
 * 不在这里算，因为它要跟着筛选视图变，而这个模块不该知道视图。
 */
/**
 * 把偏好里的关键词**预归一化一次**，给 `isHidden` 复用。
 *
 * 不做这一步的话，`norm(w)` 会在**每个岗 × 每个关键词**上重跑一遍
 * ——1200 个岗 × 56 个关键词 = 6.7 万次 `toLowerCase`，每次渲染都来一遍。
 * 2026-08-13 实测：关键词加到 50 多个时页面直接卡到渲染进程无响应
 * （CDP 45 秒超时两次）。
 */
export function compile(p: HiddenPrefs) {
  return {
    appliedCompanies: p.appliedCompanies,
    applied: p.applied,
    companies: p.companies.map(norm).filter(Boolean),
    titles: p.titles.map(norm).filter(Boolean),
  };
}

export type Compiled = ReturnType<typeof compile>;

export function isHidden(job: Job, p: Compiled, appliedTo: Set<string>): boolean {
  const co = norm(job.company);
  const ti = norm(job.title);
  // **已投过的公司**：只在这家已经投过、且这个岗自己还没投时才藏。
  // 「这个岗自己投过」的行由「已投」标记表达，不该在这里凭空消失。
  // **这一个岗自己投过了**：与下面那条按公司藏的不同，它不看别的岗。
  // 放在最前面 —— 已投的行同时也可能命中公司/标题屏蔽，谁先判都一样藏，
  // 但先判这条，读代码的人一眼看得出两条「已投」是分开的两件事。
  if (p.applied && job.applied) return true;
  if (p.appliedCompanies && !job.applied && co && appliedTo.has(co)) return true;
  if (p.companies.some((w) => co.includes(w))) return true;
  if (p.titles.some((w) => ti.includes(w))) return true;
  return false;
}

/**
 * 当前快照里已经投过的公司（归一化）。
 *
 * **脱敏名不算数。** 「某知名公司」「某上海大型电子商务公司」是平台的占位串，
 * 不是公司名——它底下挂的是**几十家互不相干的公司**。按字符串相等去认，
 * 就等于宣布它们是同一家。
 *
 * 2026-08-19 实测（2440 个岗）：已投的 69 个公司名里 36 个是脱敏串；
 * 全站 437 个岗被标「这家投过」，其中 **344 个（79%）来自脱敏串**——
 * 光「某知名公司」一个就顶 142 个。
 *
 * 更重的一面是「不想看什么」里那个「投过的公司不再显示」：勾上会**藏掉**
 * 这 344 个岗，而它们绝大多数与你投过的那家毫无关系。标错只是噪音，
 * 藏错是把岗弄丢。
 *
 * `anonymousEmployer` 是导出器已经算好的同一个判据（`export_web_data.py`
 * 的 `_anonymous_employer`），这里直接用，不另起一套。
 */
export function appliedCompanySet(jobs: Job[]): Set<string> {
  const s = new Set<string>();
  for (const j of jobs) {
    if (j.applied && j.company && !j.anonymousEmployer) s.add(norm(j.company));
  }
  return s;
}
