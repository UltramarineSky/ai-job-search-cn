import { useEffect, useState } from "react";
import type { JobPref } from "../types";
import { hasServer, postPref } from "../data/excluded";
import { Cmd } from "./Cmd";

/**
 * 「这几类岗要不要看」。
 *
 * **和判词无关。** 关掉一类只是把它从可投名单里滤掉，分数与判词原样留在库里，
 * 随时开得回来——用户的偏好不该反向改写评估结果。
 *
 * 三个默认全是「看」。尤其代招：2026-08-19 实测这份数据里 12 个可投岗有 11 个是
 * 猎头或人力资源机构代招，只有 1 个企业直招。默认关掉它，等于把国内高端岗位的
 * 常态排除掉。**「谁发的」和「什么用工形式」是两件事**——后者由硬性条件按
 * `employmentType`（全职/派遣）单独判，与这个开关无关。
 *
 * 每行都带**现在有多少个**：只问「要不要看代招」而不说「关掉会少 1361 个」，
 * 用户没法判断这个开关值不值得动。
 */
export function JobPrefs({ prefs, onChanged }: {
  prefs: JobPref[];
  onChanged?: () => void;
}) {
  const live = hasServer();
  const [busy, setBusy] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  /**
   * 乐观覆盖：**先按点下去的样子显示，props 追上来就自动退位。**
   *
   * 勾选框的位置来自重取回来的快照，而写盘那一下 `serve.py` 在响应之前同步跑
   * 导出子进程（实测 3.4-4.2 秒）。原来这几秒里勾选框不动、还变灰 ——
   * 跟用户 2026-09-02 报的「点了我投了，怎么没乐观更新」是同一个形状，
   * 只是换了个控件（`test_marking_applied_is_instant.py` 记着那条的四次）。
   *
   * **退位规则写成「props 和我说的一样了就删掉这一条」**，不是「重取回来就清空」：
   * 后者会把这期间新点的那一下一起抹掉，勾选框当场跳回去。
   */
  const [ov, setOv] = useState<Record<string, boolean>>({});
  useEffect(() => {
    setOv((o) => {
      const next = Object.fromEntries(Object.entries(o).filter(
        ([k, v]) => prefs.find((p) => p.key === k)?.enabled !== v));
      // 没变就返回原对象 —— 每次都新建会让这个 effect 自己触发自己。
      return Object.keys(next).length === Object.keys(o).length ? o : next;
    });
  }, [prefs]);
  const shown = (p: JobPref) => ov[p.key] ?? p.enabled;
  if (!prefs.length) return null;

  const toggle = async (p: JobPref) => {
    if (!live || busy) return;
    const want = !shown(p);
    setBusy(p.key);
    setErr(null);
    setOv((o) => ({ ...o, [p.key]: want }));       // ① 立刻
    try {
      await postPref(p.key, want);                 // ② 后台写
      onChanged?.();
    } catch (e) {
      setOv((o) => {                               // 回滚：盘上没改成
        const { [p.key]: _drop, ...rest } = o;
        return rest;
      });
      setErr(e instanceof Error ? e.message : "没改成，刷新一下再试");
    } finally {
      setBusy(null);
    }
  };

  const off = prefs.filter((p) => !shown(p)).length;

  return (
    <div className="jobprefs">
      <p className="jobprefs-lead">
        关掉一类只是<b>不再显示</b>，已经打好的分和结论都留着，随时能开回来。
      </p>

      <div className="portal-rows">
        {prefs.map((p) => (
          <div key={p.key}
               className={"portal-row jobpref-row" + (shown(p) ? "" : " is-off")}>
            <label className="portal-sw">
              <input
                type="checkbox"
                checked={shown(p)}
                disabled={!live || busy === p.key}
                onChange={() => void toggle(p)}
              />
              <b>{p.label}</b>
            </label>

            <span className="portal-n">
              <b>{p.n}</b> 个
            </span>

            <span className="portal-note">{p.note}</span>
          </div>
        ))}
      </div>

      {off > 0 && (
        <p className="portal-foot">
          有 {off} 类岗被你关掉了：可以投的名单里看不到它们，但它们没被删，开回来就在。
        </p>
      )}
      {!live && (
        <p className="portal-foot">
          要本地服务才能改：终端里跑 <Cmd>python tools/serve.py</Cmd> 打开这一页。
        </p>
      )}
      {err && <p className="portal-foot portal-err">{err}</p>}
    </div>
  );
}
