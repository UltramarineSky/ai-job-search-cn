import { Collapse } from "antd";
import { Cmd } from "./Cmd";
import type { Job } from "../types";

/**
 * 模拟面的问答回看。
 *
 * ## 为什么是只读的
 *
 * 练习在 Claude Code 里进行——那里才有模型能出题、能追问、能给反馈。
 * `serve.py` 的设计原则明写着「**不接大模型**：这里所有操作都是改一个字段，
 * 不需要判断力」。面板要是也去出题，就得给它接模型和 API key，与那条边界直接冲突。
 *
 * 所以分工是：**对话里练 → 落盘 → 面板回看**。
 *
 * ## 回看要看什么
 *
 * 不是重温自己答得多好，而是找出**上次答得含糊的那几题**——下一关多半还会问。
 * 所以答案按 `interview.md` Step 4b 的规定是**原话记录、不润色**：润色过的记录
 * 看着漂亮，回看时一点用没有。
 *
 * 轮次倒序（最近的一轮排最前）：准备下一关时最该先看的是上一关。
 */
export function InterviewLog({ job }: { job: Job }) {
  const log = job.interviewLog ?? [];
  if (log.length === 0) return null;

  const rounds = [...log].reverse();
  const totalQ = log.reduce((n, r) => n + r.qa.length, 0);

  return (
    <div className="ilog">
      <div className="sec-head" style={{ marginTop: 22, marginBottom: 9 }}>
        <h2 style={{ fontSize: 14.5 }}>面试练习记录</h2>
        <span className="sec-note">
          {log.length} 轮 · {totalQ} 题 · 最近的排最前 ·
          答案是原话，没润色
        </span>
      </div>

      {/* 默认全部折叠。这块排在详情区最末、是**回看**用的，不是每次展开岗位都要读的
          ——自动展开最近一轮会把「怎么投」「为什么是这个结论」往下推一大截，
          而后两者才是展开一个岗位时真正要看的东西。轮次标题行已经给出了
          日期/阶段/题数，够判断要不要点开。 */}
      <Collapse
        className="ilog-collapse"
        ghost
        items={rounds.map((r, i) => ({
          key: `r${i}`,
          label: (
            <span className="ilog-head">
              <b>第 {r.round || rounds.length - i} 轮</b>
              {r.stage && <span className="ilog-stage">{r.stage}</span>}
              {r.date && <span className="ilog-date">{r.date}</span>}
              <span className="ilog-n">{r.qa.length} 题</span>
            </span>
          ),
          children: (
            <>
              {r.scene && <p className="ilog-scene">{r.scene}</p>}
              {/* 0 题的轮是真实情况：起了个头就中断了（解析器宽进，不丢这种轮）。
                  但展开后一片空白会让人以为渲染坏了——说清是「没记下问答」。 */}
              {r.qa.length === 0 && (
                <p className="ilog-a ilog-empty">
                  这一轮没记下问答——多半是刚开场就中断了。再练一轮会补上。
                </p>
              )}
              {r.qa.map((x, k) => (
                <div className="ilog-qa" key={k}>
                  <p className="ilog-q">
                    <span className="ilog-num">{k + 1}</span>
                    {x.q}
                  </p>
                  {/* 答案缺失是真实情况（那题没答完就跳过了），如实显示，
                      不要拿空白冒充「答得很好」 */}
                  {x.a ? (
                    <p className="ilog-a">{x.a}</p>
                  ) : (
                    <p className="ilog-a ilog-empty">（这题没记下回答）</p>
                  )}
                  {x.feedback && <p className="ilog-fb">{x.feedback}</p>}
                </div>
              ))}
            </>
          ),
        }))}
      />

      <p className="ilog-foot">
        再练一轮：复制{" "}
        <Cmd>{`/job-interview ${job.company}`}</Cmd>{" "}
        {"回命令行里跑——出题与反馈需要模型，这一页只负责回看。"}
      </p>
    </div>
  );
}
