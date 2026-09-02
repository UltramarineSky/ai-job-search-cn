# 自定义模板

这个目录放**你自己注册的**简历 / 求职信模板，由 `/job-add-template` 命令管理。框架自带的 Typst 简历模板（`resume/template.typ`）开箱即用——只有你注册了自己的模板，这个目录才会有东西。

## 目录结构

```
templates/
├── cv/
│   └── <模板名>/
│       ├── template.typ (typst) 或 template.tex (LaTeX)  # 不含个人信息的骨架（用 [PLACEHOLDER] 占位）
│       ├── TEMPLATE.md      # 模板说明：编译引擎、字体、页数上限、排版规则、坑
│       ├── *.cls / *.sty    # 自定义类文件 / 样式文件（LaTeX 模板才需要）
│       └── fonts/           # 随模板带的字体文件（不用系统字体时才需要）
└── cover_letters/
    └── <模板名>/
        └── （同样的结构）
```

## 它怎么工作

- `/job-add-template` 会**问你一遍**这个模板的用法（编译引擎、字体、排版规则、页数上限），把文件存进这里，并且**必须先试编译通过**才登记。
- 启用一个模板，写的是**活动用户自己的** `templates/active-cv.md` / `templates/active-cover-letter.md`（即 `users/<活动用户>/templates/…`，已随 `users/` gitignore）。`/job-apply` 起草之前查的就是它——共享的说明文件从不会被写。
- `/job-add-template --list` 看已注册的模板；`/job-add-template --use <名字>` 切换。
- `/job-add-template --use default` **按类型还原**——删掉哪一类的激活文件就还原哪一类，不会把两类一起还原：简历回到 `resume/template.typ`，求职信回到 `cover_letter/template.typ`（两个默认模板不是同一个）。没指明类型时命令会先问清，不会替你决定。

模板里存的是 `[PLACEHOLDER]` 占位符，不是个人数据，所以可以放心提交和分享。

## 多用户

模板库本身（本目录）全用户共享——注册一次全家可用；「当前激活哪个」是每用户各自的状态，存在各自的 `users/<用户>/templates/` 下，互不影响。

**共享的代价是会撞名**：隔离的只是激活指针，骨架文件是公用的。用别人已注册过的名字重新注册，会直接覆盖对方在用的骨架，而对方的激活文件仍指向这个路径——他下次 `/job-apply` 就会用上你的字体、引擎和页数上限，全程没有告警。`/job-add-template` 在 Step 2 会检查重名并让你确认，不确定时换个名字。
