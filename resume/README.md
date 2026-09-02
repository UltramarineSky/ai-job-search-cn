# 中文简历模板（Typst）

## 依赖

- [Typst](https://typst.app) 0.13 或更高版本
  - Windows：`winget install --id Typst.Typst`
  - macOS：`brew install typst`
  - Linux：见官方发布页
  - **Windows 上安装后需新开终端**，已开启的终端不会自动获得 PATH
- 中文字体：推荐 [Noto Sans SC / Noto Serif SC](https://fonts.google.com/noto)（开源、可免费商用）
  - 模板的回退链按平台分段：`Noto Sans SC → 思源黑体 → Windows/macOS/Linux 系统字体`。
    **首位固定开源字体，共享模板要的是可预测**——换个人编译不该长得不一样
  - 字体缺失时 Typst 会告警（`unknown font family`）并回退到系统字体；若一个中文字体都
    没有，会产出方块字（豆腐块）PDF——编译**不会**因此失败。这种情况由 `/job-apply` 的
    ATS 文本层校验（`pdftotext -layout -enc UTF-8` 提取后检查方块字/乱码）抓出来
  - ⚠️ **字体嵌进 PDF，收简历的人不用装任何字体**；只有编译这台机器需要。

### 可选：换成 MiSans（中英混排更顺）

[MiSans](https://hyperos.mi.com/font)（小米开源，可免费商用）的拉丁部分是为中英混排调过的，
接缝不像思源黑体那样「中文重、拉丁轻」——简历里 `GitHub`、`SaaS`、`0→1` 这类混排越密，
收益越明显。装 `otf/` 目录下全部 10 个字重即可。

**在你自己的 `main.typ` 里改**（它是自包含的），不要动共享模板。**两处必须一起改**：

1. `中文字体` 首位插入 `"MiSans"`
2. `常规 = 330`、`加重 = 520`（`衬线粗` 仍是 700，衬线体不受影响）

因为 **MiSans 的字重命名不按常规刻度**：

| 名字 | 实际 weight |
|---|---|
| Regular | **330**（不是 400） |
| Medium | 380 |
| Demibold | 450 |
| Semibold | 520 |
| **Bold** | **630**（不是 700） |
| Heavy | 700 |

只换字体不改字重的话：正文 `400` 会选到 **Medium**（过重）、加重 `600` 会选到 **Bold(630)**
并盖过小节名的衬线 700，层级会倒过来（职位看着比它所属的小节还响）。
改字重前先用 `typst fonts --variants` 读真实值，别猜。

## 文件

| 文件 | 说明 |
|---|---|
| `template.typ` | 样式与排版规则，由框架维护 |
| `example.typ` | 占位符版示例（不含真实数据），供 CI 冒烟编译使用，**已随仓库提交** |
| `main.typ` | 你的主简历，含真实个人数据 —— **不在这个目录**（见下），且**已被 gitignore、不进版本库** |

> **`main.typ` 在你自己的目录下**：`users/<你的名字>/resume/main.typ`
> （`<你的名字>` 见仓库根 `.active_user`）。这个目录只放**共享**的模板与示例。
> 多人共用一份 clone 时各写各的，不会互相覆盖。

## 编译

```bash
typst compile users/<你的名字>/resume/main.typ users/<你的名字>/resume/main.pdf
```

冒烟编译（不依赖真实数据，走这个目录里的示例）：

```bash
typst compile resume/example.typ resume/example.pdf
```

## 排版约定（改内容前先看这几条）

- **目标岗位写在 `头衔` 参数里，不要另起「求职意向」一节。** 它会渲染在姓名右侧
  同一行：左边「我是谁」，右边「我要什么」，一行说完，省掉整整一节。

  ```typst
  #show: resume.with(姓名: "张三", 头衔: "Java 后端工程师", 联系: (...))
  ```

- **要点用 `- ` 开头的原生列表，不要手写 `· 文字 \`。** 原生 list 的续行会自动
  悬挂缩进；手写的不会——换行后的文字和「·」顶格，扫读时会被误当成新的一条。

- **成果数字加重，规格数字不加重。** 「<N> 万+ 注册用户」「<N>K+ stars」这类
  *有多少人在用* 的数字包一层 `#成果[…]`；「<N>+ 动作」「<N>+ 语言」这类
  *有多少功能* 的规格数字保持常规——加重了会把注意力引到不重要的地方。
  数字多时在 `main.typ` 里写一条正则更省事，改文案也不会漏：

  ```typst
  #show regex("<你的成果数字一>|<你的成果数字二>"): set text(weight: 加重)
  ```

- **链接用 `#链(显示, 地址)`，显示域名而不是纯锚文本。** 简历会被打印，只挂在文字上的
  链接一打印就没了；但也别摆 40 个字符的完整路径，没人会照着手抄。

- **教育经历也走 `entry`，学校放左、学历专业放右。** 右列（时间/学校）在所有小节里
  共用同一条对齐轴，页面右缘才不会在下半页断掉；而读的人先看学校层次，专业是次级信息。

- **装不下一页时，先动 `resume()` 里的页边距，再考虑删内容。** 加宽文字列往往能让
  一两处折行缩回单行，比压行距划算。

## 照片（可选）

`resume()` 支持可选的 `照片` 参数，`none`（默认）时完全不渲染、不占位，排版与不传时完全一致。

- 传入图片路径时，会在页面右上角渲染证件照（约 1 寸比例，宽度 2.6cm）。
- 照片属于个人数据，本模板仅提供参数，不附带任何真实图片；照片文件放在
  **`users/<你的名字>/resume/photo.jpg`**——也就是**和你自己那份 `main.typ` 同一个
  目录**（`*.jpg` 与 `users/` 都已 gitignore，不进版本库）。

  > **不是你现在读的这个目录。** 仓库根的 `resume/` 放的是共享模板
  > （`template.typ` / `example.typ`），照片搁这儿 Typst 找不到：它默认不允许
  > `image()` 访问入口文件目录之外的路径（`../profile/…` 会报
  > `would escape the project root`）。

  同目录下用 `照片: "photo.jpg"` 即可
  `typst compile users/<你的名字>/resume/main.typ` 直接编译，无需 `--root` 参数。
- **文件格式必须与扩展名一致**：`.jpg` 必须是真正的 JPEG 数据。若手头是 PNG，直接
  把它命名为 `photo.png` 并写 `照片: "photo.png"` 即可，**不要**把 PNG 改名成 `.jpg`——
  Typst 按真实字节解码，改名后的 PNG 会报 `failed to decode image ... Illegal start bytes`。
- 是否需要照片视行业而定：互联网岗位通常不放；体制内、传统行业、校招简历常见要求附照片。
- 在 `main.typ` 中启用：

  ```typst
  #show: resume.with(
    姓名: "张三",
    联系: (...),
    照片: "photo.jpg",
  )
  ```

## 已知陷阱

- **`@` 在正文 markup 中直接出现时必须转义为 `\@`**。`@` 是 Typst 的引用语法，
  例如直接在段落文字里写 `test@example.com` 会报
  `label ... does not exist in the document`。
- **但字符串字面量（函数参数里的 `"..."`）中的 `@` 不需要转义，也不能转义**。
  `resume()` 的 `联系` 参数、`entry()` 的各字段都是字符串数组，其中的
  `"test@example.com"` 会被原样当作文本插入，不会触发 label 解析；
  如果写成 `"test\@example.com"`，编译虽然仍会成功，但反斜杠会被当作字面字符
  一起塞进渲染结果 —— PDF 文本层会变成 `test\@example.com`，
  ATS/`pdftotext` 提取邮箱字段时会失配。经实测确认。
- **检查 PDF 文本层时必须加 `-enc UTF-8`**：
  `pdftotext -layout -enc UTF-8 users/<你的名字>/resume/main.pdf -`
  不加会让中文显示为乱码，产生「字体没嵌入」的假警报。
