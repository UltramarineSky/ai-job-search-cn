// 中文求职信模板（Typst）
//
// 视觉与 resume/template.typ 同源：同一套灰阶、字重、字体链、页边距和信头，
// 因为这两份文档几乎总是一起发出去——观感不一致会显得是随手拼的。
//
// ⚠️ 但**不照搬**排版参数：信是用来读的，简历是用来扫的。
//    正文 11pt / 行距 0.85em / 首行缩进 2em 都比简历宽松，这是刻意的，别对齐成一样。
//
// ⚠️ 设计令牌（墨/次/淡、常规/加重/衬线粗）与 resume/template.typ 必须逐字一致，
//    改一边就要改另一边——`tests/test_template_visual_sync.py` 会盯住这件事。
//
// ⚠️ @ 的转义规则分两种情形，不要混淆（与 resume/template.typ 完全一致）：
//    - 在 raw markup 正文里裸写 @（例如段落文字里直接敲 test@example.com）
//      会被当作 Typst 的引用语法解析，报 `label ... does not exist in the document`，
//      正文中的 @ 需要转义成 \@ 或改写（例如「联系方式见简历」）。
//    - 但在字符串字面量里（如本模板 `联系` 数组、`收信`/`正文`/`落款` 的字符串参数）
//      的 @ 不需要也不能转义，直接写 "test@example.com" 即可；写成
//      "test\@example.com" 反斜杠会原样进入 PDF 文本层，破坏 ATS 提取。
//      详见 README.md「已知陷阱」。

// 三档灰阶，无强调色。求职信同样可能被黑白打印。
#let 墨 = rgb("#111111")
#let 次 = rgb("#5a5a5a")
#let 淡 = rgb("#9a9a9a")

// 回退链按平台分段，三个平台都要覆盖到（与 resume/template.typ 保持一致）。
// ⚠️ 字体全缺时 typst 只出 `warning: unknown font family`、exit 0、PDF 文本层仍可提取，
//    所以自动检查全都会通过 —— 只有看 stderr warning 或肉眼看渲染才能发现豆腐块。
#let 中文字体 = (
  "Noto Sans SC",
  "Source Han Sans SC",
  "Microsoft YaHei", "SimHei", "DengXian",            // Windows
  "PingFang SC", "Hiragino Sans GB", "STHeiti",       // macOS
  "Noto Sans CJK SC", "WenQuanYi Zen Hei",            // Linux
)
#let 中文衬线 = (
  "Noto Serif SC", "Source Han Serif SC",
  "SimSun",                                          // Windows
  "Songti SC", "STSong",                             // macOS
  "Noto Serif CJK SC",                               // Linux
)

// 字重写数值而不是 "bold" / "regular"。这组是 Noto Sans SC 的常规刻度；
// 换 MiSans 要一并改成 330 / 520 / 700，原因见 resume/README.md。
#let 常规 = 400
#let 加重 = 600
#let 衬线粗 = 700

// cover_letter：中文正式求职信主函数
//
// 参数：
//   姓名 — 信头与落款签名用
//   头衔 — 可选，渲染在姓名右侧（与简历同一个位置和写法）；留空则不渲染
//   联系 — 数组，如 (城市, 电话, 邮箱)，在信头以 " · " 连接展示
//   日期 — 落款处展示（中文信件的日期在落款，不在顶部）
//   收信 — 收信对象描述（公司/部门/称呼），会被套进「尊敬的 #收信：」
//   正文 — 段落数组（每个数组元素渲染为独立段落）或单个 content 块
//   落款 — 结束语，默认「此致\n敬礼！」；按 "\n" 拆行渲染，
//          签名（姓名 + 日期）在其后自动生成，无需另外传入
#let cover_letter(
  姓名: "",
  头衔: "",
  联系: (),
  日期: "",
  收信: "",
  正文: (),
  落款: "此致\n敬礼！",
) = {
  set page(paper: "a4", margin: (x: 1.45cm, y: 1.25cm))
  // 11pt / 0.85em：比简历（9.6pt / 0.73em）宽松，因为这是要逐句读完的散文。
  set text(font: 中文字体, size: 11pt, weight: 常规, lang: "zh", fill: 墨)
  set par(justify: true, leading: 0.85em, first-line-indent: 2em)
  // 链接不用彩色：全篇无强调色，蓝字在一片黑灰里会跳，打印出来又变灰失效。
  show link: it => underline(offset: 0.16em, stroke: 0.4pt + 淡, text(fill: 次, it))

  // 信头与简历逐项对齐：姓名（衬线大字）左、头衔右，联系行在下，一条墨线收口。
  // 两份文档摆在一起时，这个信头是「同一套材料」最直接的信号。
  grid(
    columns: (auto, 1fr),
    column-gutter: 0.8em,
    align: (left + bottom, right + bottom),
    text(font: 中文衬线, size: 19pt, weight: 衬线粗)[#姓名],
    if 头衔 != "" { text(size: 11.5pt, fill: 次)[#头衔] } else { [] },
  )
  v(0.34em)
  par(first-line-indent: 0em)[
    #text(size: 8.8pt, fill: 次)[#联系.join(" · ")]
  ]
  v(0.5em)
  line(length: 100%, stroke: 0.7pt + 墨)
  v(1.1em)

  // 收信人称呼（顶格，不缩进）
  par(first-line-indent: 0em)[
    #text(size: 11pt, weight: 加重)[尊敬的 #收信：]
  ]
  v(0.6em)

  // 正文：接受段落数组（逐段落排版，首行缩进 + 两端对齐）或直接一段 content
  if type(正文) == array {
    for 段 in 正文 [
      #par[#段]
      #v(0.55em)
    ]
  } else {
    正文
  }

  v(0.6em)

  // 落款：结束语（按 \n 拆行）+ 自动生成的签名块。
  // 联系方式不在这里重复——信头已经有了，签名只留姓名与日期。
  par(first-line-indent: 0em)[
    #for (行序, 行) in 落款.split("\n").enumerate() [
      #if 行序 > 0 [#linebreak()]
      #行
    ]
  ]
  v(1.4em)
  align(right)[
    #text[求职人：#姓名]
    #linebreak()
    #text(size: 10pt, fill: 次)[#日期]
  ]
}
