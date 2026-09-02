import { useState } from "react";
import { Cmd } from "./Cmd";
import type { HrAnswer } from "../types";

/**
 * HR 聊天框里反复问的那几句，连同事先写好的答案。
 *
 * ## 为什么值得单独有一块
 *
 * 「看机会的原因？」「看哪里的？」「期望多少？」——这几句每谈一家就要答一遍。
 * **临场编的代价不是慢，是口径不一致**：同一个问题在打招呼、HR 初面、背调三处
 * 说法对不上，正是面试官交叉验证时要抓的（`07-interview-prep.md`）。
 *
 * ## 这一块只做两件事
 *
 * 1. **给得出去** —— 一键复制，直接粘进聊天框；
 * 2. **改得动** —— 就地编辑，存回 `profile/hr-answers.md`。
 *
 * 不做的：不生成、不润色。那是 `/job-setup` 和对话里的事，这一页的边界一直是
 * 「改一个字段」（`serve.py` 自己那条：不接大模型）。
 */
export function HrAnswers({ items, live, onSave }: {
  items: HrAnswer[];
  /** 本地服务在跑才存得回去；静态打开时只读。 */
  live: boolean;
  /** 存不回去就**抛**，别返回 false —— 真因在异常里，吞掉之后
   *  界面只能说一句放之四海皆准的「再点一次」。 */
  onSave: (q: string, a: string) => Promise<void>;
}) {
  const [editing, setEditing] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState<string | null>(null);
  const [err, setErr] = useState("");

  const blank = items.filter((i) => i.empty).length;

  return (
    <div className="hrqa">
      {/* **没写的那几条要先说出来。** 一份看着满满的问答里混着两条占位符，
          用户会以为都准备好了——直到 HR 问到那一条。 */}
      {blank > 0 && (
        <p className="hrqa-todo" role="status">
          <b>还有 {blank} 条没写</b>
          {"：下面标了「还没写」的那几条，HR 问到时你手上没有说法。"}
        </p>
      )}
      {err && <p className="hrqa-err" role="alert">{err}</p>}

      {items.map((it) => {
        const on = editing === it.q;
        return (
          <div className="hrqa-item" key={it.q} data-empty={it.empty}>
            <p className="hrqa-q">
              {it.q}
              {it.empty && <em className="hrqa-flag">还没写</em>}
            </p>

            {on ? (
              <>
                <textarea
                  className="hrqa-edit"
                  value={draft}
                  rows={Math.max(3, draft.split("\n").length + 1)}
                  onChange={(e) => setDraft(e.target.value)}
                  aria-label={`改「${it.q}」的答案`}
                />
                <div className="hrqa-row">
                  <button
                    type="button"
                    className="hrqa-btn"
                    disabled={busy}
                    onClick={async () => {
                      setBusy(true);
                      setErr("");
                      // **把服务端的真因显示出来**，别只说「没存进去」。
                      // `post()` 那边的注释写着「服务端把真因放在 error 里；
                      // 别把失败咽掉」——`Portals` 三条写路径都照做了，
                      // 只有这一条原来 `catch { return false }`，于是
                      // 「profile 目录不存在」「token 不对」「文件只读」
                      // 一律显示成同一句「再点一次」，而再点一次都没用。
                      try {
                        await onSave(it.q, draft);
                        setEditing(null);
                      } catch (e) {
                        setErr(e instanceof Error ? e.message
                               : "没存进去——本地服务还在跑的话再点一次");
                      } finally {
                        setBusy(false);
                      }
                    }}
                  >
                    {busy ? "存…" : "存"}
                  </button>
                  <button
                    type="button"
                    className="hrqa-btn"
                    onClick={() => setEditing(null)}
                  >
                    不改了
                  </button>
                </div>
              </>
            ) : (
              <>
                {/* 空的不渲染一个空段落——那看起来像加载失败。 */}
                {it.a
                  ? <p className="hrqa-a">{it.a}</p>
                  : <p className="hrqa-a is-blank">（空的）</p>}
                <div className="hrqa-row">
                  <button
                    type="button"
                    className="hrqa-btn"
                    disabled={!it.a}
                    onClick={() => {
                      void navigator.clipboard?.writeText(it.a);
                      setCopied(it.q);
                      window.setTimeout(() => setCopied(null), 1500);
                    }}
                  >
                    {copied === it.q ? "复制好了" : "复制"}
                  </button>
                  {/* **静态打开时不给「改」。** 给了点下去存不回盘，
                      而用户以为存上了——同这一页别处对 `live` 的处理。 */}
                  {live && (
                    <button
                      type="button"
                      className="hrqa-btn"
                      onClick={() => { setEditing(it.q); setDraft(it.a); }}
                    >
                      改
                    </button>
                  )}
                </div>
              </>
            )}
          </div>
        );
      })}

      <p className="hrqa-foot">
        {live
          ? "改完直接存回 profile/hr-answers.md；那份文件也能自己开着改。"
          : "现在是只读——起本地服务才改得动："}
        {!live && <Cmd>python tools/serve.py</Cmd>}
      </p>
      {/* 长答案（面试、背调那一版）不在这儿，别把两个渠道混成一份。 */}
      <p className="hrqa-foot">
        面试和背调要用的长版本在资料里各自的小节，聊天框这一版只求短、能直接粘。
      </p>
    </div>
  );
}
