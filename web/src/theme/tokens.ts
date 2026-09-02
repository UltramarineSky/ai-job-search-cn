import { theme, type ThemeConfig } from "antd";

/**
 * 仪表舱 · 主题令牌
 *
 * antd 组件只当底座（交互逻辑 + 可达性），视觉全部由这里的 token 与
 * `cockpit.css` 里的 CSS variables 接管。目标是让人看不出这是 antd 默认观感。
 *
 * 三条贯穿全局的取向，都是从项目本身读出来的，不是随手选的风格：
 *
 * 1. **零圆角**。这个项目的核心动作是「盖章 / 判定」，方形是它的形制语言。
 *    antd 默认 6px 圆角会把方章变成药丸，所以 borderRadius 一路压到 2。
 * 2. **等宽数字**。分数、权重、薪资、年限全是要对齐比较的数，
 *    所以数字统一 tabular-nums，字体栈里 mono 优先。
 * 3. **中文优先的字号下限**。中文字形在同等 px 下比拉丁更吃尺寸，
 *    所以 fontSize 基线抬到 14.5、fontSizeSM 抬到 13——低于 13 的中文在深底上读不清。
 */

/**
 * 舱内配色。语义名而非色名，改色时不必改用处。
 *
 * 下面的对比度**一律按最亮的那层底 `panelRaised` 算**——在最不利的一层成立，
 * 在 bay / panel 上自然更高。原来三个数没按同一层算（`lit` 的 15:1 是对 panel，
 * 另两个是对 panelRaised），于是它们承诺的到底是什么，谁也说不清。
 * `tests/test_contrast.py` 把这些数当断言验：注释和色值对不上就红。
 */
export const palette = {
  bay: "#0D1218", // 舱内底
  panel: "#151C25", // 面板
  panelRaised: "#1C2530", // 抬起的面板（hover / 选中）
  edge: "#2A3542", // 分隔线
  edgeStrong: "#374553", // 可交互边框
  lit: "#EAF1F7", // 主文字 ≈13.6:1
  dim: "#A8B4C2", // 次要文字 ≈7.4:1
  faint: "#8494A5", // 弱文字 ≈5.0:1，AA 下限，再暗就读不清
  data: "#3CCBBF", // 数据青：读数、通过
  dataDeep: "#1E6E68", // 数据青的暗调，用于边框
  caution: "#E8AC3A", // 琥珀：未知 / 待确认
  lock: "#E86259", // 红：硬门不通过 / 越界表述
} as const;

const FONT_SANS =
  '"Noto Sans SC","PingFang SC","Microsoft YaHei",system-ui,sans-serif';
const FONT_MONO =
  '"JetBrains Mono","IBM Plex Mono",ui-monospace,"Cascadia Mono",Consolas,monospace';

export const cockpitTheme: ThemeConfig = {
  // antd 6 起 CSS variables 主题**默认开启且不可关**（`cssVar` 只剩 prefix/key 两个
  // 配置项，传 `true` 会 TS2559）。cockpit.css 直接引用 --ant-* 变量，正是靠这一点。
  // 同时关掉 hash：类名稳定，覆盖选择器才写得出来。
  hashed: false,
  algorithm: theme.darkAlgorithm,
  token: {
    // **关掉 antd 的进场动画。**
    //
    // 实测 2026-08-24（浏览器开着「减少动态效果」）：点开设置那几个 Modal，
    // 弹窗**根本不出现** —— DOM 里在、标题也对，`opacity` 卡在 0。
    // antd 的 `ant-zoom-appear` / `ant-fade-appear` 把 `opacity: 0` 写在动画的
    // **起始状态**里，靠动画跑完才回到 1；而 `cockpit.css` 在
    // `prefers-reduced-motion` 下把动画整个关掉，元素就永远停在起始那一帧。
    //
    // 把时长改成 `0.01ms` 试过，仍然不出现：rc-motion 靠 `animationend`
    // 摘掉那两个 class，短到那个程度它收不到。**所以从源头关**：
    // 告诉 antd 不要动画，它就不会先把元素设成透明。
    // 这一页本来就是静态设计，没有动画可损失。
    motion: false,

    colorPrimary: palette.data,
    colorInfo: palette.data,
    colorSuccess: palette.data,
    colorWarning: palette.caution,
    colorError: palette.lock,

    colorBgBase: palette.bay,
    colorTextBase: palette.lit,
    colorBgContainer: palette.panel,
    colorBgElevated: palette.panelRaised,
    colorBgLayout: palette.bay,
    colorBorder: palette.edge,
    colorBorderSecondary: palette.edge,

    colorText: palette.lit,
    colorTextSecondary: palette.dim,
    colorTextTertiary: palette.faint,
    // antd 的 quaternary 默认低到 ~2.5:1，中文在深底上直接糊掉。
    // 这里拉到与 tertiary 同级，宁可少一层灰阶也不要读不清的字。
    colorTextQuaternary: palette.faint,

    // **焦点环**。antd 所有 :focus-visible 都取这一个 token，暗色算法把它从
    // colorPrimary 推导成 #204B47——实测画在面板底（#151C25）上只有 1.76:1，
    // 按钮底（#0D1218）上 1.93:1，而 WCAG 1.4.11 对非文字元素要求 3:1。
    // 深色底上那圈环基本看不见，键盘操作时不知道自己在哪。
    // 我们自己做的元素（.rail-cell / 表格行 / .shelf-restore）早就在 cockpit.css
    // 里用 var(--data) 画环，实测 8.6:1——这里把 antd 那半边拉齐到同一个颜色。
    colorPrimaryBorder: palette.data,

    // 方形语言：判定类界面不该有圆角。
    borderRadius: 2,
    borderRadiusLG: 2,
    borderRadiusSM: 2,
    borderRadiusXS: 1,

    fontFamily: FONT_SANS,
    fontFamilyCode: FONT_MONO,
    fontSize: 15,
    fontSizeSM: 13,
    fontSizeLG: 16,
    fontSizeHeading3: 20,
    fontSizeHeading4: 16,
    lineHeight: 1.7,

    controlHeight: 34,
    controlOutlineWidth: 2,
    // 去掉 antd 默认的柔和投影——仪表盘要硬边，靠线分层而非靠影。
    boxShadow: "none",
    boxShadowSecondary: "none",
    boxShadowTertiary: "none",
    wireframe: false,
    motionDurationMid: "0.12s",
  },
  components: {
    Table: {
      headerBg: palette.panel,
      headerColor: palette.faint,
      headerSplitColor: palette.edge,
      borderColor: palette.edge,
      rowHoverBg: palette.panelRaised,
      rowSelectedBg: palette.panelRaised,
      rowSelectedHoverBg: palette.panelRaised,
      cellPaddingBlock: 13,
      cellPaddingInline: 16,
      // 表头当作标签栏而不是标题栏
      headerBorderRadius: 0,
    },
    Collapse: {
      headerBg: palette.panel,
      contentBg: palette.panel,
      headerPadding: "11px 16px",
      contentPadding: 0,
      borderRadiusLG: 0,
    },
    Tag: {
      defaultBg: palette.panelRaised,
      defaultColor: palette.dim,
      borderRadiusSM: 2,
    },
    Descriptions: {
      labelBg: "transparent",
      titleColor: palette.lit,
      contentColor: palette.dim,
      itemPaddingBottom: 6,
    },
    Button: {
      defaultBg: "transparent",
      defaultBorderColor: palette.edgeStrong,
      defaultColor: palette.dim,
      primaryShadow: "none",
      defaultShadow: "none",
      fontWeight: 500,
    },
    Tooltip: {
      colorBgSpotlight: palette.panelRaised,
      colorTextLightSolid: palette.lit,
      borderRadius: 2,
    },
    Progress: { defaultColor: palette.data, remainingColor: palette.bay },
    Divider: { colorSplit: palette.edge },
    Empty: { colorTextDescription: palette.faint },
  },
};

/** 档位 → 语义色。判词是这个项目的最终输出，颜色跟着判词走。 */
export type Verdict = "强匹配" | "值得投" | "可以考虑" | "不建议" | "跳过";

export const verdictColor: Record<Verdict, string> = {
  强匹配: palette.data,
  值得投: palette.lit,
  可以考虑: palette.caution,
  不建议: palette.lock,
  跳过: palette.faint,
};

/**
 * ConfigProvider 上的组件配置（不属于主题令牌，但同样是「整页统一」的设定，
 * 所以和令牌放在一起，免得日后有人只找到一半）。
 *
 * `button.autoInsertSpace: false` —— antd 默认给**恰好两个汉字**的按钮中间插一个
 * 空格（它管这叫中文排版优化）。实测「挂了」上屏变成「挂 了」，正是本仓库一直在
 * 拦的那类「中文之间被塞进空格」。只是这次插空格的是**组件库**，不是我们的源码，
 * 所以那条扫 JSX 的检查看不见它——`tests/test_web_copy.py` 里另有一条按配置验。
 */
export const cockpitComponents = {
  button: { autoInsertSpace: false },
} as const;
