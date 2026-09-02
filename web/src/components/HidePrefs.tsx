import { useEffect, useRef, useState } from "react";
import { EMPTY, HIDEABLE_COLUMNS, type HiddenPrefs } from "../data/hidden";

/**
 * 「不想看什么」——名单的视图过滤
 *
 * ## 三条铁律
 *
 * 1. **必须说出藏了几个。** 一个筛选器最危险的失败模式是「用户忘了它开着」，
 *    然后以为岗位变少了。所以藏起来的条数一直印在标题上，一眼看得见。
 * 2. **随时能全清。** 一个按钮回到「什么都不藏」，不用逐条删。
 * 3. **不改任何岗的状态。** 这里只管看不看得见；「这个我不投」是另一件事
 *    （那要写回盘上，见 `data/excluded.ts` 顶上的说明）。
 */
export function HidePrefs({ prefs, onChange, hiddenCount }: {
  prefs: HiddenPrefs;
  onChange: (p: HiddenPrefs) => void;
  hiddenCount: number;
}) {
  const [open, setOpen] = useState(false);
  const [co, setCo] = useState("");
  const [ti, setTi] = useState("");
  const wrap = useRef<HTMLDivElement>(null);

  // **Esc 关、点外面关。**
  //
  // 这块是 `position: absolute; z-index: 20`，展开时**盖住表头和前两行**，
  // 而第一版只能再点一次「不想看什么」才关得掉——盖住了正文，出口却只有
  // 来时那一个。这一页的用户弹层 2026 年早些时候栽过一模一样的跟头，
  // `App.tsx` 里那段注释还留着，我建这块时没看见它。
  //
  // 所以这次写在组件自己里：下一个建浮层的人复制这个组件就自带出口。
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    const onDown = (e: MouseEvent) => {
      // 点在触发按钮上不管——那一下本来就会 toggle，这里再关一次
      // 就成了「关了又开」，看起来像没反应。
      if (!wrap.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("keydown", onKey);
    document.addEventListener("mousedown", onDown);
    return () => {
      document.removeEventListener("keydown", onKey);
      document.removeEventListener("mousedown", onDown);
    };
  }, [open]);
  const any = prefs.applied || prefs.appliedCompanies || prefs.companies.length > 0
    || prefs.titles.length > 0 || prefs.columns.length > 0;

  const add = (kind: "companies" | "titles", v: string) => {
    const w = v.trim();
    if (!w || prefs[kind].includes(w)) return;
    onChange({ ...prefs, [kind]: [...prefs[kind], w] });
  };
  const drop = (kind: "companies" | "titles", v: string) =>
    onChange({ ...prefs, [kind]: prefs[kind].filter((x) => x !== v) });
  const toggleCol = (k: string) =>
    onChange({
      ...prefs,
      columns: prefs.columns.includes(k)
        ? prefs.columns.filter((x) => x !== k)
        : [...prefs.columns, k],
    });

  return (
    <div className="hide-wrap" ref={wrap}>
      <button type="button" className="hide-toggle" onClick={() => setOpen(!open)}
              aria-expanded={open}>
        不想看什么
        {/* 藏了多少必须一直在外面。折起来之后看不到这个数，
            用户就会把「岗变少了」当成数据问题。 */}
        {/* 中文不能进 .mono-label：那个类是 0.17em 字距 + uppercase，
            拉丁排版的做法，套在中文上会拉成散架的一串（cockpit.css 顶上有说明）。
            数字走 mono，「藏了」两个字留在外面。 */}
        {hiddenCount > 0 && (
          <span className="hide-n">
            藏了<b className="mono-label">{hiddenCount}</b>
          </span>
        )}
      </button>

      {open && (
        <div className="hide-body">
          {/* **两条「已投」的开关排在一起，但它们藏的不是一个东西。**
              上面这条藏「这一个岗，我发过了」；下面那条藏「这家公司的**别的**岗」。
              分开写是因为用户要的常常只是前者：点开「材料就绪」想找还没发的那批，
              而那一格 244 个里 83 个已经投出去了（实测 2026-08-26）。 */}
          <label className="hide-line">
            <input type="checkbox" checked={prefs.applied}
                   onChange={(e) => onChange({ ...prefs, applied: e.target.checked })} />
            <span>已经投过的岗不显示</span>
          </label>
          <p className="hide-note">
            <span>「可以投的岗位」本来就不列已投的，这个开关管的是点开「材料就绪」「已投递」这些格子之后的那几张表。</span>
          </p>

          <label className="hide-line">
            <input type="checkbox" checked={prefs.appliedCompanies}
                   onChange={(e) => onChange({ ...prefs, appliedCompanies: e.target.checked })} />
            <span>投过的公司，它别的岗也不显示</span>
          </label>
          <p className="hide-note">
            <span>只藏这家公司的其它岗，已经投过的那个照常显示——不然你会找不到自己投了什么。</span>
          </p>

          <div className="hide-line">
            <span className="hide-k">不看这些公司</span>
            <input className="hide-in" value={co} placeholder="公司名，回车加一个"
                   onChange={(e) => setCo(e.target.value)}
                   onKeyDown={(e) => {
                     if (e.key === "Enter") { add("companies", co); setCo(""); }
                   }} />
          </div>
          {prefs.companies.length > 0 && (
            <div className="hide-chips">
              {prefs.companies.map((w) => (
                <button type="button" key={w} onClick={() => drop("companies", w)}
                        title="点一下去掉">{w} ×</button>
              ))}
            </div>
          )}

          <div className="hide-line">
            <span className="hide-k">职位里带这些词就不看</span>
            <input className="hide-in" value={ti} placeholder="如 销售、实习，回车加一个"
                   onChange={(e) => setTi(e.target.value)}
                   onKeyDown={(e) => {
                     if (e.key === "Enter") { add("titles", ti); setTi(""); }
                   }} />
          </div>
          {prefs.titles.length > 0 && (
            <div className="hide-chips">
              {prefs.titles.map((w) => (
                <button type="button" key={w} onClick={() => drop("titles", w)}
                        title="点一下去掉">{w} ×</button>
              ))}
            </div>
          )}

          <div className="hide-line">
            <span className="hide-k">表格里不显示这几列</span>
            <span className="hide-chips">
              {HIDEABLE_COLUMNS.map((c) => (
                <button type="button" key={c.key}
                        data-on={prefs.columns.includes(c.key) ? "" : undefined}
                        onClick={() => toggleCol(c.key)}>
                  {c.label}
                </button>
              ))}
            </span>
          </div>

          <p className="hide-note">
            <span>这些只影响你看到什么，不改任何岗的状态、不写进盘上，清掉就全回来了。要真的不投某个岗，展开它点「不投这个岗」。</span>
          </p>
          {/* **用 EMPTY，别再抄一份。** 这里原来把空值就地写了一遍，
              于是加一个开关就有两处要同步 —— 2026-08-26 加「已经投过的岗不显示」
              时，`tsc` 当场报这里少一个字段。它要是没被类型管住，症状就是
              「全部清掉」清不干净，而屏幕上没有任何提示。 */}
          {any && (
            <button type="button" className="hide-clear"
                    onClick={() => onChange({ ...EMPTY })}>
              全部清掉
            </button>
          )}
        </div>
      )}
    </div>
  );
}
