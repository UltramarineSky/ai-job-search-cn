import { Tooltip } from "antd";
import { Cmd } from "./Cmd";
import type { Gate, GateState } from "../types";

/**
 * 签名元素 1 · 硬性条件四态方章
 *
 * 为什么不用 antd 的 Tag/Badge：Tag 是"标签"语义（可增删的属性），
 * 而这里是**判定**——一次性、有权威、不可自行摘掉。方章是这个语义的正确形制。
 *
 * 四态靠**形制**区分而不只靠颜色（实心/斜纹/空心/虚线），
 * 所以色盲用户可辨，缩到 17px 颜色失效时也仍然可辨。
 *
 * antd 只用 Tooltip —— 它带 aria 关联与键盘可达，比自己写 title 属性可靠。
 */

/** 印文四个字都是汉字，一字一态：过／否／疑／无。不混用符号。 */
const MARK: Record<GateState, string> = {
  pass: "过",
  fail: "否",
  unknown: "疑",
  na: "无",
};

const SPOKEN: Record<GateState, string> = {
  pass: "满足",
  fail: "不满足",
  unknown: "还没查到",
  na: "不涉及",
};

export function GateStamp({
  state,
  size = "md",
  label,
  why,
}: {
  state: GateState;
  size?: "sm" | "md";
  /** 条件名，用于 tooltip 与屏读 */
  label: string;
  why?: string;
}) {
  // 「还没查到」的读法要说清它不等于不合格，否则用户会当成没戏而放弃这个岗。
  const spoken =
    state === "unknown"
      ? "还没查到（不等于不合格，投之前自己问清）"
      : SPOKEN[state];
  const tip = why ? `${label} · ${spoken} —— ${why}` : `${label} · ${spoken}`;

  return (
    <Tooltip title={tip}>
      <span
        className="stamp"
        data-state={state}
        data-size={size}
        role="img"
        aria-label={tip}
      >
        <span aria-hidden>{MARK[state]}</span>
      </span>
    </Tooltip>
  );
}

/** 详情区的完整条件格：落印文 + 写依据。 */
/**
 * 这道门算不算「还没查到」——**要用户投前自己问一句的那一条**。
 *
 * `state === "unknown"` 之外还要排掉**自造门名**（`offSpec`）：那一行根本不是
 * 硬性条件（`04-job-evaluation.md` 第一步：「自造的门名和没判一样」），催用户
 * 去问它，问的是一件不存在的门。
 *
 * **这一份是正本。** 它原来被抄了三份：这里的计数、`JobReadout` 那句
 * 「投之前先问清 N 条」、以及它下面那句「有一条不满足就别投」的条件。
 * 三处问的是同一件事，而**加一个条件就要改三处**。
 *
 * ⚠️ 不含 `assumed`（按假设值判的）—— 那是**另一类**，`GateGrid` 底下
 * 给它的是另一句话（「按你资料里的假设值判的，不是从这个岗读到的」），两者
 * 不能相加。`JobReadout` 那句「有一条不满足就别投」自己在外面补 `|| g.assumed`，
 * 收拢时原样保留 —— 这次只收重复，不改任何一处的行为。
 */
export function countsAsUnknown(g: Gate): boolean {
  return g.state === "unknown" && !g.offSpec;
}

export function GateGrid(
  { gates, url, notJudged = [] }:
  { gates: Gate[]; url?: string; notJudged?: string[] },
) {
  // 一条都没有 ≠ 都通过了。没有这个守卫时，下面那句会走 else 分支印出
  // 「这些条件都核对过了，没有要问的」—— 把**解析为空**说成**核对通过**，
  // 是这一页最危险的错误：用户据此以为学历、外包、地点都验过了。
  //
  // 实测就这么发生过：evaluation.md 的硬门表标题写成「第一步：硬性门槛」，
  // 而解析器靠字面词「硬门」定位，整张表被丢弃 → gates 为空 → 页面报全部通过。
  // 调用方那层的守卫是 `dimensions || gates || gaps`（**或**），只挡得住三者
  // 全空；四维解析成功、硬门解析失败时它判 true，照样渲染到这里。所以守卫要落在
  // 这里——数据为空的地方，而不是调用方猜"大概有数据"的地方。
  if (gates.length === 0) {
    return (
      <p className="gate-note" data-tone="unchecked">
        <b>这个岗的硬性条件还没核对过</b>
        {"——不是「都通过」，是评估里没有这张表。" +
         "学历、经验年限、外包还是直招、地点这些，投之前得对一遍。"}
        {/* 原来到这里就断了：告诉用户「你自己对一遍」，却不说**跑什么**能让它
            自动对。而 /job-apply 的第一步就是核这张表——命令是现成的，只是没说出来。 */}
        <br />
        让它核一遍：
        <Cmd>{url ? `/job-apply ${url}` : "/job-apply <职位链接>"}</Cmd>
      </p>
    );
  }
  // **自造门名不进这个数** —— 判据在 `countsAsUnknown`（上面那个函数），
  // 别在这儿另写一遍。
  //
  // 这一处还有它自己的一半：下面那句话的后半是「JD 和公司资料里都没写」
  // —— 实测那几行的依据里写着 JD 原话，那半句是**假的**。所以自造门名
  // 混进来时，说出口的是一句假话，问的是一件根本不存在的门。
  const unknownCount = gates.filter(countsAsUnknown).length;
  // 「按假设值判的」也是要你确认的一条。原来只数 unknown，于是上面明明标着
  // 「投前请自己确认」，下面却写「这些条件都核对过了，没有要问的」——自相矛盾。
  const assumedCount = gates.filter((g) => g.assumed).length;

  return (
    <>
      <div className="gate-grid">
        {gates.map((g) => (
          <div
            key={g.name}
            className="gate"
            data-flag={g.assumed ? "ask" : g.state}
          >
            <span className="gate-name">
              {g.name}
              {/* 行留着（审计要人去改它），但得说清它不是一道硬性条件——
                  不说的话，格子里一个「还没查到」的章会读成「这条没过关」。
                  `04` 给了归位规则：地点、英语、年龄这类归「候选人明确排除」，
                  专业、技术栈本来就是要打分的维度。 */}
              {g.offSpec && <span className="gate-offspec">不算硬性条件</span>}
              <span className="gate-why">
                {g.assumed ? `${g.why} · 投前请自己确认` : g.why}
              </span>
            </span>
            <GateStamp state={g.state} label={g.name} why={g.why} />
          </div>
        ))}
      </div>
      <p className="gate-note">
        {/* 三处都是实测读出来的毛病：
            ① 原来无论哪种情况都先印一次总数，于是只有一种时同一个数说两遍
               （「投之前要问清楚 1 条： 1 条还没查到」），中间还因为 `{" "}`
               多一个空格。总数只在两种都有时才有意义。
            ② 「琥珀色空心章」「琥珀色边框」是**用外观去指认元素**。这与本文件
               顶上那条「四态靠形制区分」不冲突，两件事：形制是**画**给人看的
               区别，色觉障碍者也认得出；而**写**成一句话去指路就不行了——
               「琥珀色」在高对比模式下不成立，「空心章」是用户从没学过的词。
               这一句该说的是这条**状态本身是什么**，不是它长什么样。
            ③ 「不等于不合格」留着——它是这句里唯一会改变决定的信息。 */}
        {unknownCount > 0 && assumedCount === 0 && (
          <>
            投之前要问清楚 {unknownCount} 条：<b>还没查到</b>
            {"——JD 和公司资料里都没写。不等于不合格，自己问一句就好。"}
          </>
        )}
        {assumedCount > 0 && unknownCount === 0 && (
          <>
            投之前要确认 {assumedCount} 条：<b>按你资料里的假设值判的</b>
            {"，不是从这个岗读到的，自己核对一下。"}
          </>
        )}
        {unknownCount > 0 && assumedCount > 0 && (
          <>
            投之前要问清楚 {unknownCount + assumedCount} 条：{unknownCount} 条
            <b>还没查到</b>
            {"（资料里没写，不等于不合格）；"}
            {assumedCount} 条<b>按你资料里的假设值判的</b>
            {"，自己核对一下。"}
          </>
        )}
        {unknownCount + assumedCount === 0 && notJudged.length === 0 && (
          <>这些条件都核对过了，没有要问的。</>
        )}
        {/* **部分缺行和整张表为空是同一种谎，只是更难发现**：表在、行也在，
            只是少了几行，于是页面照旧印「都核对过了」。2026-08-20 实测 236 个
            印这句话的岗里，60 个实际有 2-3 道门没查。 */}
        {notJudged.length > 0 && (
          <>
            {unknownCount + assumedCount > 0 && "另外，"}
            这个岗<b>有 {notJudged.length} 项没核对</b>
            {`：${notJudged.join("、")}。`}
            {"不是「通过」，是评估里根本没写这几行——投之前自己对一遍，"}
            {"或者让它重核一次："}
            <Cmd>{url ? `/job-apply ${url}` : "/job-apply <职位链接>"}</Cmd>
          </>
        )}
      </p>
    </>
  );
}
