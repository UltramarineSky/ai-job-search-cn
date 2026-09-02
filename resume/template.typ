// 中文简历模板（Typst）
//
// 设计取向：无强调色、无小节横线，层级全靠字重 / 字号 / 留白。
// 简历大概率被黑白打印，任何主题色在纸上都会变成一团灰；六条小节横线
// 会把一页切成六块。去掉它们之后，唯一一条线（页头）才担得起分量。
//
// ⚠️ @ 的转义规则分两种情形，不要混淆：
//    - 在 raw markup 正文里裸写 @（例如段落文字里直接敲 test@example.com）
//      会被当作 Typst 的引用语法解析，报 `label ... does not exist in the document`，
//      正文中的 @ 需要转义或改写。
//    - 但在字符串字面量里（如本模板 `联系` 元组、`entry` 的字符串参数）的 @
//      不需要也不能转义，直接写 "test@example.com" 即可；写成 "test\@example.com"
//      反斜杠会原样进入 PDF 文本层，破坏 ATS 提取。详见 README.md「已知陷阱」。

// 三档灰阶，无强调色。
#let 墨 = rgb("#111111")
#let 次 = rgb("#5a5a5a")
#let 淡 = rgb("#9a9a9a")

// 回退链按平台分段，三个平台都要覆盖到。
// ⚠️ 字体全缺时 typst **不报错**：只打印 `warning: unknown font family`、exit 0、
//    照样产出 PDF，而且 PDF 文本层完整可提取 —— 所以 ATS 文本层校验也会通过。
//    唯一能发现的办法是看编译 stderr 的 warning 或肉眼看渲染结果。
//    此前这份清单只有 Windows 字体，macOS 用户不装 Noto 就会静默拿到豆腐块简历。
//
// 首位固定 Noto Sans SC：它开源、三平台装了都一样，**共享模板要的是可预测**——
// 换个人编译不该长得不一样。想换字体请改自己那份 main.typ（它是自包含的），别动这里。
#let 中文字体 = (
  "Noto Sans SC",                                    // 跨平台首选（开源，可免费商用）
  "Source Han Sans SC",                              // 思源黑体，Noto 的同源命名
  "Microsoft YaHei", "SimHei", "DengXian",            // Windows
  "PingFang SC", "Hiragino Sans GB", "STHeiti",       // macOS
  "Noto Sans CJK SC", "WenQuanYi Zen Hei",            // Linux 发行版常见
)
#let 中文衬线 = (
  "Noto Serif SC", "Source Han Serif SC",
  "SimSun",                                          // Windows
  "Songti SC", "STSong",                             // macOS
  "Noto Serif CJK SC",                               // Linux
)

// 字重写数值而不是 "bold" / "regular"，这样换字体时只改这三行。
// 下面这组是 Noto Sans SC 的常规刻度。
#let 常规 = 400    // 正文
#let 加重 = 600    // 职位、项目名、成果数字
#let 衬线粗 = 700  // 姓名与小节名走衬线体
//
// ⚠️ 想换成 MiSans（小米开源，可免费商用；拉丁部分为中英混排调过，接缝不像思源黑体
//    那样「中文重、拉丁轻」）——**在你自己的 main.typ 里改，两处必须一起改**：
//      1. 中文字体 首位插入 "MiSans"
//      2. 常规 = 330、加重 = 520（衬线粗仍是 700，衬线体不受影响）
//    因为 MiSans 的字重命名不按常规刻度：
//      Regular=330（不是 400）、Medium=380、Demibold=450、Semibold=520、
//      Bold=630（不是 700）、Heavy=700
//    只换字体不改字重的话：正文 400 会选到 Medium（过重）、加重 600 会选到 Bold(630)
//    并盖过小节名的衬线 700，层级倒过来。改前先 `typst fonts --variants` 读真实值。

// 想让某个成果数字跳出来时包一层：`#成果[<N> 万+ 注册用户]`。
// 数字多的话，在 main.typ 里写一条正则更省事，也不会漏：
//   #show regex("<你的成果数字一>|<你的成果数字二>"): set text(weight: 加重)
// 只加重**成果**数字（多少人在用），不加重**规格**数字（多少个功能）——
// 规格数字是功能清单，加重了会把读者的注意力引到不重要的地方。
#let 成果(内容) = text(weight: 加重)[#内容]

// 项目标题后跟的短网址：`#链("example.com", "https://example.com/very/long/path")`。
// 显示域名而不是纯锚文本——简历会被打印，只挂在文字上的链接一打印就没了；
// 但也别把 40 个字符的完整路径摆出来，没人会照着手抄。
#let 链(显示, 地址) = text(size: 8.5pt, weight: 常规)[#link(地址)[#显示]]

// 姓名左、目标岗位右，同一行：左边「我是谁」，右边「我要什么」，一行说完，
// 「求职意向」整整一节因此可以省掉。
#let resume(姓名: "", 头衔: "", 联系: (), 照片: none, body) = {
  // 边距是收页数的第一个旋钮：内容差一两行装不下时先动这里，再考虑删内容。
  set page(paper: "a4", margin: (x: 1.45cm, y: 1.25cm))
  // 字号阶梯：姓名 19 / 小节名 11.5 / 职位 10.5 / 正文 9.6 / 单位 9.3 / 时间 8.8。
  set text(font: 中文字体, size: 9.6pt, weight: 常规, lang: "zh", fill: 墨)
  set par(justify: true, leading: 0.73em)
  // 项目符号统一走原生 list：续行会自动悬挂缩进。手写「· 文字 \」不会缩进，
  // 换行后的文字和「·」顶格，扫读时会被误当成新的一条。
  set list(
    marker: text(fill: 淡)[·],
    indent: 0pt, body-indent: 0.35em, spacing: 0.48em,
  )
  // 链接不用彩色：全篇无强调色，蓝字在一片黑灰里会跳，打印出来又变灰失效。
  // 改用次级灰 + 极淡下划线——下划线是「可点」的通用信号，且印在纸上无害。
  show link: it => underline(offset: 0.16em, stroke: 0.4pt + 淡, text(fill: 次, it))

  let 页头 = {
    grid(
      columns: (auto, 1fr),
      column-gutter: 0.8em,
      align: (left + bottom, right + bottom),
      text(font: 中文衬线, size: 19pt, weight: 衬线粗)[#姓名],
      if 头衔 != "" { text(size: 11.5pt, fill: 次)[#头衔] } else { [] },
    )
    v(0.34em)
    text(size: 8.8pt, fill: 次)[#联系.join(" · ")]
  }

  // 有照片（可选）时左右分栏，文字被限制在左栏宽度内、不会被照片压住。
  if 照片 != none {
    grid(
      columns: (1fr, auto),
      column-gutter: 0.6cm,
      align: (left + top, right + top),
      页头,
      image(照片, width: 2.6cm),
    )
  } else {
    页头
  }
  v(0.5em)
  // 全篇唯一一条线。小节不再画线，这条才担得起 0.7pt 的墨色。
  line(length: 100%, stroke: 0.7pt + 墨)
  v(0.1em)

  body
}

// 章节标题：不画线，靠留白 + 衬线 + 字重分层。
// sticky 让标题黏住后面的内容——否则标题会孤零零留在页尾、内容全被推到下一页。
#let section(标题) = {
  v(0.95em)
  // 标题下方的留白写在 block 内部而不是 below：实测 block(sticky: true, below: …)
  // 的 below 会被折叠掉，标题和紧跟的条目标题贴死，读成一个两行标题。
  // 去掉横线后这两行之间没有任何分隔物，这段留白是唯一的分层手段。
  block(sticky: true)[
    #text(font: 中文衬线, size: 11.5pt, weight: 衬线粗)[#标题]
    #v(0.42em)
  ]
}

// 一条经历：标题行左右分栏 + 副标题 + 要点。
// 右列（时间）在所有小节里共用同一条对齐轴——教育经历也走 entry，把学校放右列，
// 页面右缘才不会在下半页断掉。
#let entry(职位: "", 时间: "", 单位: "", 要点: ()) = {
  // 只把「职位 + 公司」这一小块设为不可断并黏住正文：整条 entry 都
  // breakable: false 的话，条目一长就会整条被挤到下一页、上一页留一大片空白。
  block(breakable: false, sticky: true)[
    #grid(
      columns: (1fr, auto),
      column-gutter: 0.8em,
      text(size: 10.5pt, weight: 加重)[#职位],
      // 等宽数字：日期都靠右，数字成列才对得齐。只作用于数字——
      // 中文套等宽会被拉成散字，中英混排还会在接缝处炸出大间隙。
      text(size: 8.8pt, fill: 次, number-width: "tabular")[#时间],
    )
    #if 单位 != "" [
      #v(-0.15em)
      #text(size: 9.3pt, fill: 次)[#单位]
    ]
  ]
  v(0.18em)
  if 要点.len() > 0 {
    list(..要点)
  }
  v(0.2em)
}
