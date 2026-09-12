import { Typography } from "antd";
import { useCodeTool } from "../context/CodeToolContext";

/**
 * 可复制的命令片 / 复制按钮。
 *
 * ## 为什么要抽出来
 *
 * 页面上有 **23 个**复制按钮，原来每一个的无障碍名都是「复制」——读屏用户
 * Tab 过去听到二十三遍「复制」，不知道任何一个复制的是什么。而这一页的
 * 全部价值就在于「该敲哪条命令」，那 23 个按钮恰恰是它的出口。
 *
 * antd 的 `copyable` 把 `tooltips[0]` 同时用作按钮的 `aria-label`，所以名字里
 * 带上要复制的东西，鼠标提示和读屏播报一起就都对了。
 *
 * 顺带治掉另一件事：`copyable={{ tooltips: ["复制", "已复制"] }}` 这行配置
 * 原来在 8 个文件里抄了 19 遍。改一次提示语要改 19 处，漏一处就不一致。
 */

/** 命令片：等宽方框 + 复制。`children` 就是要敲的那条命令，支持随当前终端工具自适应格式。 */
export function Cmd({ children }: { children: string }) {
  const { formatCommand } = useCodeTool();
  const formatted = formatCommand(children);

  return (
    <Typography.Text
      code
      copyable={{
        text: formatted,
        // 提示要说**实际复制到剪贴板**的那条；免斜杠模式下显示和复制的
        // 都是 job-auto，提示却还写 /job-auto 就是骗用户。
        tooltips: [`复制 ${formatted}`, "已复制"],
      }}
    >
      {formatted}
    </Typography.Text>
  );
}

/**
 * 只有一个复制图标、没有可见文字的那种。
 *
 * `what` 说清复制的是什么（「打招呼开场白」）——图标本身不带文字，
 * 不说明白的话，读屏那边就只剩一个光秃秃的「复制」。
 */
export function CopyIcon({ text, what }: { text: string; what: string }) {
  return (
    <Typography.Text copyable={{ text, tooltips: [`复制${what}`, "已复制"] }} />
  );
}

/**
 * 带文字的复制按钮。
 *
 * 只给**这一页上最常按的那一下**用：打招呼开场白。整页存在的目的就是「去投」，
 * 而去投的第一个动作是把开场白复制走——它原来只是一个 14px 的灰图标，挂在一行
 * 12.5px 的说明后面，比旁边任何一个次要按钮都轻。
 *
 * 其余零散的复制点仍用 `CopyIcon`：每一处都做成按钮，一屏会摆出二十个按钮，
 * 那时又没有哪一个是重点了。
 *
 * 复制这件事本身仍然交给 antd 的 `copyable`（剪贴板、降级、「已复制」反馈、
 * aria-label 都在里面），这里只换一层外观。
 */
export function CopyButton({ text, label, what }: {
  text: string;
  label: string;
  what: string;
}) {
  return (
    <Typography.Text
      className="copy-btn"
      copyable={{ text, tooltips: [`复制${what}`, "已复制"] }}
    >
      {label}
    </Typography.Text>
  );
}
