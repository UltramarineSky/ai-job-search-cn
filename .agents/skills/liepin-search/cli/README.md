# liepin-cli

猎聘公开职位搜索 CLI。免登录、**零运行时依赖**，Node 22.18+ 或 Bun 直接跑，不用先装依赖：

```bash
node src/cli.ts search -q "后端开发" -l "北京" --format table
```

下面这几条是**改这个 CLI 时才用的**开发任务，要装 Bun：

```bash
bun install          # 只装 TypeScript 类型，无运行时依赖
bun run typecheck
bun test             # 离线 fixture 测试，不发网络请求
```

在线冒烟测试默认跳过，需要时显式开启：

```bash
LIEPIN_LIVE=1 bun test tests/search.live.test.ts
```

接口细节与解析锚点见 `../url-reference.md`。

> 仅供个人求职使用，请保持低频。
