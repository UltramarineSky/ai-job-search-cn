import { createContext, useContext, useState, useEffect, type ReactNode } from "react";

/**
 * 当前跑在哪个 AI 编码工具里，决定命令块显不显示开头的斜杠。
 *
 * 取值正本是 tools/_cli.py 的 detect_code_tool()，由导出快照带过来：
 * - claude：Claude Code，保留斜杠（/job-auto，支持 Tab 补全）
 * - antigravity / gemini / generic：命令不带斜杠直接发
 * 后端也可能经 JOBS_CODE_TOOL 返回 cursor / codex 等自定值 —— 行为和
 * generic 一样（都是免斜杠），归一到 generic，只影响 Radio 停在哪一档。
 */
export type CodeTool = "antigravity" | "claude" | "gemini" | "generic";

const KNOWN_TOOLS: readonly string[] = ["antigravity", "claude", "gemini", "generic"];
const STORAGE_KEY = "job_search_code_tool";

function asKnownTool(v: unknown): CodeTool | null {
  return typeof v === "string" && KNOWN_TOOLS.includes(v) ? (v as CodeTool) : null;
}

interface CodeToolContextType {
  tool: CodeTool;
  setTool: (tool: CodeTool) => void;
  formatCommand: (cmd: string) => string;
  isNoSlash: boolean;
}

const CodeToolContext = createContext<CodeToolContextType>({
  tool: "generic",
  setTool: () => {},
  formatCommand: (cmd) => (cmd.startsWith("/") ? cmd.slice(1) : cmd),
  isNoSlash: true,
});

export function CodeToolProvider({
  initialTool,
  children,
}: {
  initialTool?: string;
  children: ReactNode;
}) {
  const [tool, setToolState] = useState<CodeTool>(() => {
    try {
      const saved = asKnownTool(localStorage.getItem(STORAGE_KEY));
      if (saved) return saved;
    } catch {
      // localStorage 不可用时按探测结果走
    }
    return asKnownTool(initialTool) ?? "generic";
  });

  // 服务端探测结果变化（换了终端工具 / 起服务的环境变了）时跟过去，
  // 但用户在面板上手选过就以他的选择为准（见 setTool 的持久化）。
  useEffect(() => {
    try {
      if (localStorage.getItem(STORAGE_KEY)) return;
    } catch {
      // 读不到就按新探测值更新
    }
    const detected = asKnownTool(initialTool);
    if (detected) setToolState(detected);
  }, [initialTool]);

  const setTool = (t: CodeTool) => {
    setToolState(t);
    try {
      localStorage.setItem(STORAGE_KEY, t);
    } catch {
      // 存不住不影响本次会话
    }
  };

  const isNoSlash = tool !== "claude";

  const formatCommand = (cmd: string) => {
    if (isNoSlash && cmd.startsWith("/")) {
      return cmd.slice(1);
    }
    return cmd;
  };

  return (
    <CodeToolContext.Provider value={{ tool, setTool, formatCommand, isNoSlash }}>
      {children}
    </CodeToolContext.Provider>
  );
}

export function useCodeTool() {
  return useContext(CodeToolContext);
}
