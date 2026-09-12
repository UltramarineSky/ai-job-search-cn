import { Button } from "antd";
import { Cmd } from "./Cmd";
import type { BaseResume as BaseResumeData } from "../types";

/**
 * 你的基简历
 *
 * ## 为什么单独有这一块
 *
 * 面板原来碰简历只有两处，**都不是「你的简历」本身**：
 *
 * - 「市场怎么读你的简历」—— 从评估语料反推主场与该补的词，不含简历内容
 * - 各岗详情里的「打开定制简历 PDF」—— 那是**某次投递的定制版**，还得先展开那一行
 *
 * 而基简历才是所有投递共用的那一份：改一次，影响之后每一次投递。它的内容、
 * 它编译出来的 PDF、它的审核报告，面板上一个入口都没有。
 *
 * ## 这一块只做「看得见」
 *
 * 改简历、审简历都在命令行（那里才有模型能读懂内容、比对资料）。这里负责
 * 让人知道：**它长什么样、上次审是什么时候、结论是什么、该敲什么命令**。
 */
export function BaseResume(
  { data, user }: { data: BaseResumeData; user?: string },
) {
  const { updated, sections, pdf, pdfLocal, pdfStale, audit } = data;
  // **复制下来要能直接敲。** 这条原来写死 `users/<你>/…`，而 `<Cmd>` 是
  // 点一下就复制的 —— 复制到的那串粘进终端会失败，用户得先知道自己那个
  // 目录名叫什么。而面板手里就有 `activeUser`（快照里那一项）。
  // 判据是 `AGENTS.md`「每一处引导都要写出该敲的命令」那句：
  // 「读完这句他能不能直接动手」。拿不到用户名时才退回占位符。
  const base = `users/${user || "<你>"}/resume/main`;

  return (
    <div className="bresume">
      <div className="bresume-row">
        <span className="kicker">最后修改</span>
        <b>{updated}</b>
        {/* http 模式（serve.py / vite preview）要走 `pdf`（/pdf/…，服务端有路由）；
            `pdfLocal` 是 file:// 单文件时代的相对路径，那条路已删，在 http 下
            解析成 /resume/main.pdf → 404。顺序反了按钮就是死链。 */}
        {pdf && (
          <Button size="small" href={pdf || pdfLocal} target="_blank" rel="noopener">
            打开简历 PDF
          </Button>
        )}
      </div>

      {/* PDF 比源文件旧 = 你改了 .typ 但没重新编译，打开的是**上一版**。
          这种「文件在、但内容是旧的」最容易骗人：按钮能点、PDF 能开，
          只是内容不是你以为的那份。必须说出来。 */}
      {pdfStale && (
        <p className="bresume-stale">
          {"PDF 比源文件旧——你改过简历但还没重新编译，" +
           "现在打开的是上一版。重新编译："}
          <Cmd>{`typst compile ${base}.typ ${base}.pdf`}</Cmd>
        </p>
      )}

      {/* 解析不到章节 ≠ 简历没有章节。判据是 `#section("…")` 这个模板写法
          （`resume/template.typ` 定义、`example.typ` 在用），换一套不这么写的
          模板就会解析为空——那时页面原来只剩一个孤零零的「章节顺序」标签和
          一片空白，看起来像简历坏了。空要说出来，而且要说清是**读不出来**
          不是**没有**。 */}
      {sections.length === 0 && (
        <p className="bresume-stale" data-tone="unchecked">
          {"读不出章节顺序——这份简历没有用 #section(\"…\") 这种写法标章节。" +
           "不影响简历本身，只是这一栏显示不了；换回自带模板就能读到。"}
        </p>
      )}

      {/* 基线里缺的章节。**放在「章节顺序」那一行之前**：先说少了什么，
          再列现有的顺序——反过来是让人先读完一份看着完整的清单，
          再被告知它不完整。
          用 --caution 不用 --lock：少一节不是错误，是还没补。 */}
      {(data.missingSections?.length ?? 0) > 0 && (
        <p className="bresume-stale">
          {`按国内社招的基线，这份简历还少一节：${data.missingSections!.join("、")}。`}
          {data.missingSections!.includes("求职意向")
            ? "「求职意向」写岗位、城市、期望年包——HR 扫简历先找「这人要什么」，没有它就得从你的经历里自己猜投的是不是这个级别、这个城市。"
            : ""}
          {/* **他可能已经写过了。** 定制简历里常常有主简历漏掉的那一节
              （实测：15 份定制版里 4 份第二行就是「求职意向」，而主简历没有）。
              给原文比给建议有用——从零想一句和照抄一句不是一回事。 */}
          {Object.entries(data.missingWrittenElsewhere ?? {}).map(([sec, line]) => (
            <span className="bresume-elsewhere" key={sec}>
              {`你在定制简历里已经写过这一节了，照抄过来就行：`}
              <code>{line}</code>
            </span>
          ))}
          {"补完跑 "}
          <Cmd>/job-resume</Cmd>
          {" 再审一遍。"}
        </p>
      )}

      {/* 正文里踩了 `03` 的那几句。和「少一节」并排的理由一样：
          都是「你手上这一份还差什么」。而这一条的杠杆更大 ——
          定制版是从主简历复制出去的，实测那一句进了 12 份，
          在这儿改一次，下次 /job-cv 重出时一起干净。
          给出原句而不只给词：一个词在两千字里搜不着，一句话找得到。 */}
      {(data.styleWarn?.length ?? 0) > 0 && (
        <p className="bresume-stale">
          {`正文里有 ${data.styleWarn!.length} 处写作规范建议改写的写法：`}
          {data.styleWarn!.map((w) => (
            <span className="bresume-elsewhere" key={w}>{w}</span>
          ))}
          {"改完跑 "}
          <Cmd>/job-resume</Cmd>
          {" 复核一遍。"}
        </p>
      )}

      {/* 资料里没填、而硬门要用的取值。和上面「少一节」并排：都是
          「你手上的材料还差什么」，而不是某一个岗的事。 */}
      {(data.gateInputsMissing?.length ?? 0) > 0 && (
        <p className="bresume-stale">
          {`资料里「${data.gateInputsMissing!.map((g) => g.field).join("、")}」还没填，而${
            data.gateInputsMissing!.length > 1 ? "它们分别是" : "它是"}硬性条件里的「${
            data.gateInputsMissing!.map((g) => g.gate).join("、")}」那一项——没有它，这道门在每一个岗上都判不了（不是「不适用」，是判不了）。`}
          <Cmd>/job-setup</Cmd>
          {" 补一下。"}
        </p>
      )}

      {sections.length > 0 && (
      <div className="bresume-row">
        <span className="kicker">章节顺序</span>
        <span className="bresume-secs">
          {sections.map((s, i) => (
            <span key={s}>
              {i > 0 && <em>→</em>}
              {s}
            </span>
          ))}
        </span>
      </div>
      )}

      <div className="bresume-row">
        <span className="kicker">上次审核</span>
        {audit ? (
          <>
            <b>{audit.date}</b>
            {audit.count > 1 && <span className="bresume-n">共 {audit.count} 份</span>}
            {/* **结论比简历旧时先说这件事，再给结论。** 那句「可以直接投」
                是决定性的，读的人会照着它去投。顺序反过来（先结论后提醒）
                等于让他先信一遍再收回。 */}
            {audit.stale && (
              <span className="bresume-audit-stale">
                简历在这之后改过（{audit.resumeChangedOn}）——下面这句说的是上一版
              </span>
            )}
            {audit.verdict && <span className="bresume-verdict">{audit.verdict}</span>}
          </>
        ) : (
          <span className="bresume-never">还没审过</span>
        )}
        <Cmd>/job-resume</Cmd>
      </div>

      <p className="bresume-note">
        {"审核会逐条比对简历与你的资料：有没有对不上的数字、"}
        {"有没有写到你自己说过做不了的事、结构与页数合不合规。报告存在 "}
        <code>reports/</code>
        {" 下，按日期累加——"}
        改一版审一次，历次放在一起才看得出上次说要补的补了没有。
        {audit
          ? "改简历与审核都在命令行做，这一页只负责让你看得见。"
          : "简历还没被审过——投出去之前建议先跑一次。"}
      </p>
    </div>
  );
}
