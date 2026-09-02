# 中文求职信模板（Typst）

## 依赖

- [Typst](https://typst.app) 0.13 或更高版本
  - Windows：`winget install --id Typst.Typst`
  - macOS：`brew install typst`
  - Linux：见官方发布页
  - **Windows 上安装后需新开终端**，已开启的终端不会自动获得 PATH
- 中文字体：与 `resume/` 完全一致，推荐 [Noto Sans SC / Noto Serif SC](https://fonts.google.com/noto)
  （开源、可免费商用）。回退链**以 `template.typ` 开头的字体声明为准**——首选 Noto 家族，
  然后按 Windows / macOS / Linux 各自的系统字体逐级回退（这里不抄一遍清单：README 抄链
  的下场是模板改了链、这里还停在旧版，实测就漂移过一次）。
  字体缺失时 Typst 会告警但**不会**编译失败，可能产出方块字（豆腐块）PDF——由
  文本层校验（见下方「编译」一节）抓出来。

## 文件

| 文件 | 说明 |
|---|---|
| `template.typ` | 版式与排版规则（`cover_letter()` 主函数），由框架维护 |
| `example.typ` | 占位符版示例（不含真实数据），供 CI 冒烟编译使用，**已随仓库提交** |
| `main.typ` | 你的真实求职信，含真实个人数据；本任务**不创建**，之后由 gitignore 规则排除、不进版本库 |

三者的关系与 `resume/` 目录完全对应：`template.typ` 是框架、`example.typ` 是可编译的
占位符冒烟样例、`main.typ` 是使用者自己填真实数据的文件。求职信与照片无关，
`cover_letter()` 不提供、也不需要照片参数。

## `cover_letter()` 参数

```typst
#cover_letter(
  姓名: "张三",
  联系: ("13900001111", "test@example.com", "北京"),
  日期: "2026年1月1日",
  收信: "某科技有限公司招聘负责人",   // 会被套进「尊敬的 #收信：」
  正文: (
    "第一段：为什么应聘这家公司这个岗位……",
    "第二段：我能带来什么，附量化证据……",
    "第三段：与岗位要求的匹配，以及诚实的能力边界……",
    "第四段：期待与感谢……",
  ),
  落款: "此致\n敬礼！",   // 可选，默认即为此值；按 "\n" 拆行渲染
)
```

- `正文` 既可以是**字符串数组**（每个元素独立成段，自动两端对齐 + 首行缩进），
  也可以直接传一段 `content`（此时原样插入，不做逐段处理）。
- `落款` 是结束语（如「此致\n敬礼！」），签名块（`求职人：姓名` / 联系方式 / 日期）
  由模板根据已传入的 `姓名`、`联系`、`日期` **自动生成**在落款之后，不需要再单独传。
- **`cover_letter()` 必须直接调用**（`#cover_letter(...)`），**不要**用
  `#show: cover_letter.with(...)` 这种 show 规则写法——`resume()` 之所以能用
  `#show: resume.with(...)`，是因为它保留了一个未命名的尾随 `body` 位置参数，专门
  用来承接 `#show` 规则隐式传入的"其余文档内容"；`cover_letter()` 的六个字段全部是
  具名参数、没有预留这个位置，`.with(...)` 把它们全部填满后，`#show` 仍会再塞一个
  内容参数进来，导致编译报错 `error: unexpected argument`（错误信息会指向
  `template.typ` 里 `cover_letter(` 的参数列表，容易误以为是参数定义写错了，
  实际是调用方式用错了）。

## 编译

```bash
typst compile users/<你的名字>/cover_letter/main.typ users/<你的名字>/cover_letter/main.pdf
```

冒烟编译（不依赖真实数据，`example.typ` 全部字段都是 `[占位符]`）：

```bash
typst compile cover_letter/example.typ cover_letter/example.pdf
```

Windows 上 `typst` 若不在 PATH，用完整路径调用，例如：

```powershell
& "C:\Users\<用户名>\AppData\Local\Microsoft\WinGet\Packages\Typst.Typst_Microsoft.Winget.Source_8wekyb3d8bbwe\typst-x86_64-pc-windows-msvc\typst.exe" compile cover_letter\example.typ cover_letter\example.pdf
```

## 已知陷阱

- **`@` 在正文 markup 中直接出现时必须转义为 `\@`**。`@` 是 Typst 的引用语法，
  例如直接在段落文字里写 `test@example.com` 会报
  `label ... does not exist in the document`。
- **但字符串字面量（函数参数里的 `"..."`）中的 `@` 不需要转义，也不能转义**。
  `cover_letter()` 的 `联系`、`收信`、`正文` 都是字符串（数组）参数，其中的
  `"test@example.com"` 会被原样当作文本插入；如果写成 `"test\@example.com"`，
  编译仍会成功，但反斜杠会被当作字面字符一起塞进渲染结果——PDF 文本层会变成
  `test\@example.com`，ATS/`pdftotext` 提取邮箱字段时会失配。`example.typ` 中的
  `test@example.com` 已按不转义写法验证通过。
- **不要用 `#show: cover_letter.with(...)` 调用**，见上一节「`cover_letter()` 参数」
  的说明；直接 `#cover_letter(...)` 调用即可。
- **检查 PDF 文本层时必须加 `-enc UTF-8`**：
  `pdftotext -layout -enc UTF-8 users/<你的名字>/cover_letter/main.pdf -`
  不加会让中文显示为乱码，产生「字体没嵌入」的假警报。
- `落款` 参数里的 `"\n"` 是真实换行字符，模板内部按 `.split("\n")` 拆行渲染；
  如果直接把多行文字拼进一个不含 `\n` 的字符串，不会自动换行。
