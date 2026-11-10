#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
healthcheck.py -- 竞品直播间监控「一条命令体检」只读脚本。

不启动/停止监控，不发邮件，不写业务文件（只读 state.json / _sessions.json / 日志）。
用法：
  python healthcheck.py                # 人看的体检报告
  python healthcheck.py --json         # 结构化输出，供自动化/子代理消费
  python healthcheck.py --base <程序目录>  # 程序目录，也可用环境变量 DLM_BASE
"""
import os
import sys
import json
import glob
import shutil
import datetime
import subprocess

DEFAULT_BASE = ""  # 留空：用 --base 或环境变量 DLM_BASE
NOW = datetime.datetime.now()


def resolve_base():
    for i, a in enumerate(sys.argv):
        if a == "--base" and i + 1 < len(sys.argv):
            return sys.argv[i + 1]
    base = os.environ.get("DLM_BASE") or DEFAULT_BASE
    if not base:
        sys.exit("请用 --base 或环境变量 DLM_BASE 指定监控程序目录")
    return base


BASE = resolve_base()
STATE = os.path.join(BASE, "state.json")
SESSIONS = os.path.join(BASE, "share", "online", "_sessions.json")
REC_DIR = os.path.join(BASE, "recordings")
LOG = os.path.join(BASE, "logs", "monitor.log")
MODELS = os.path.join(BASE, "models")
WATCHDOG = os.path.join(BASE, "watchdog.py")


def read_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def check_state():
    out = {"ok": False, "updated": None, "age_min": None, "live": [], "recording": []}
    st = read_json(STATE)
    if not st:
        out["error"] = "state.json 不存在或无法解析"
        return out
    out["updated"] = st.get("updated")
    try:
        dt = datetime.datetime.fromisoformat(st["updated"])
        if dt.tzinfo is not None:
            dt = dt.astimezone().replace(tzinfo=None)
        out["age_min"] = round((NOW - dt).total_seconds() / 60, 1)
        # state 每轮轮询（默认 180s）刷新，5 分钟内算活着
        out["ok"] = out["age_min"] is not None and out["age_min"] <= 5
    except Exception as e:
        out["error"] = f"updated 解析失败: {e}"
    for r in st.get("rooms", []):
        if r.get("recording"):
            out["recording"].append(f"{r.get('name')}({r.get('room_id')}) 在线{r.get('viewers')}")
        elif r.get("live"):
            out["live"].append(f"{r.get('name')}({r.get('room_id')}) 在线{r.get('viewers')}")
    out["rooms_total"] = len(st.get("rooms", []))
    return out


def check_watchdog():
    out = {"ok": None}
    if not os.path.exists(WATCHDOG):
        out["error"] = "watchdog.py 不存在"
        return out
    try:
        p = subprocess.run([sys.executable, WATCHDOG, "--json"],
                           capture_output=True, text=True, timeout=120,
                           cwd=BASE, encoding="utf-8", errors="replace")
        data = json.loads(p.stdout)
        out.update({
            "ok": True,
            "backlog_count": data.get("backlog_count"),
            "in_grace_count": data.get("in_grace_count"),
            "already_sent": data.get("already_sent"),
            "backlog": [
                {"name": b.get("name"), "room_id": b.get("room_id"),
                 "date": b.get("date"), "time": b.get("time"),
                 "ended_ago_min": round(b.get("ended_ago_min") or 0)}
                for b in data.get("backlog", [])
            ],
        })
    except Exception as e:
        out["error"] = f"watchdog 执行失败: {e}"
    return out


def check_sessions():
    out = {"ok": False}
    d = read_json(SESSIONS)
    if not d:
        out["error"] = "_sessions.json 不存在（先跑一次 sync_all.py）"
        return out
    out["ok"] = True
    out["count"] = d.get("count")
    out["pending_count"] = d.get("pending_count")
    out["generated"] = d.get("generated") or d.get("updated")
    return out


def check_disk():
    try:
        u = shutil.disk_usage(BASE)
        return {"ok": round(u.free / 1024 ** 3, 1) >= 10,
                "free_gb": round(u.free / 1024 ** 3, 1),
                "total_gb": round(u.total / 1024 ** 3, 1)}
    except Exception as e:
        return {"ok": None, "error": str(e)}


def check_models():
    need = ["model.int8.onnx", "tokens.txt", "silero_vad.onnx"]
    missing = [n for n in need if not os.path.exists(os.path.join(MODELS, n))]
    return {"ok": not missing, "missing": missing}


def check_today():
    today = NOW.strftime("%Y-%m-%d")
    items = []
    for d in glob.glob(os.path.join(REC_DIR, "*", today, "*")):
        if not os.path.isdir(d):
            continue
        # 目录名格式 <抖音号>_<账号名>，去掉号前缀只留账号名
        raw = os.path.basename(os.path.dirname(os.path.dirname(d)))
        name = raw.split("_", 1)[1] if "_" in raw else raw
        items.append({
            "account": name,
            "time": os.path.basename(d),
            "has_report": os.path.exists(os.path.join(d, "报告.html")),
            "has_review": os.path.exists(os.path.join(d, "复盘.md")),
            "ended": os.path.exists(os.path.join(d, "ENDED")),
            "sent": os.path.exists(os.path.join(d, "email_sent.marker")),
        })
    items.sort(key=lambda x: x["time"])
    return {"ok": True, "date": today, "count": len(items), "sessions": items}


def check_log():
    if not os.path.exists(LOG):
        return {"ok": None, "error": "monitor.log 不存在"}
    try:
        with open(LOG, encoding="utf-8", errors="replace") as f:
            lines = f.readlines()[-400:]
    except Exception as e:
        return {"ok": False, "error": str(e)}
    bad = [l.rstrip() for l in lines
           if ("Traceback" in l or "[错误]" in l or "[失败]" in l or "ERROR" in l)]
    return {"ok": not bad, "recent_errors": bad[-8:],
            "last_line": lines[-1].rstrip() if lines else ""}


def collect():
    r = {
        "checked_at": NOW.strftime("%Y-%m-%d %H:%M:%S"),
        "base": BASE,
        "base_exists": os.path.isdir(BASE),
        "monitor": check_state(),
        "watchdog": check_watchdog(),
        "site": check_sessions(),
        "disk": check_disk(),
        "models": check_models(),
        "today": check_today(),
        "log": check_log(),
    }
    m, w = r["monitor"], r["watchdog"]
    blockers = []
    if not r["base_exists"]:
        blockers.append("程序目录不存在")
    if not m.get("ok"):
        blockers.append("监控进程疑似未运行（state.json 超过 5 分钟未更新）")
    if w.get("backlog_count"):
        blockers.append(f"有 {w['backlog_count']} 场已下播未发报告（积压）")
    if r["disk"].get("ok") is False:
        blockers.append(f"磁盘剩余 {r['disk'].get('free_gb')}GB 低于 10GB 阈值，录制已暂停")
    if r["models"].get("ok") is False:
        blockers.append(f"ASR 模型缺失：{', '.join(r['models']['missing'])}")
    r["verdict"] = "OK" if not blockers else "ATTENTION"
    r["blockers"] = blockers
    return r


def render_text(r):
    L = []
    add = L.append
    add("=" * 56)
    add(f"竞品直播间监控体检  {r['checked_at']}")
    add(f"程序目录 {r['base']}")
    add("=" * 56)

    m = r["monitor"]
    if m.get("ok"):
        add(f"[正常] 监控运行中，state 更新于 {m['age_min']} 分钟前"
            f"（共 {m.get('rooms_total')} 个号）")
    else:
        add(f"[异常] 监控疑似停摆：state 更新于 {m.get('age_min')} 分钟前"
            if m.get("age_min") is not None else
            f"[异常] {m.get('error', '无法读取运行状态')}")
    if m.get("recording"):
        add("       正在录制：" + "；".join(m["recording"]))
    if m.get("live"):
        add("       在播未录：" + "；".join(m["live"]))

    w = r["watchdog"]
    if w.get("ok"):
        add(f"[{'正常' if not w['backlog_count'] else '注意'}] 漏发兜底：积压 {w['backlog_count']} 场 / "
            f"宽限内 {w['in_grace_count']} 场 / 累计已发 {w['already_sent']} 场")
        for b in w.get("backlog", []):
            add(f"       ! {b['name']} {b['date']} {b['time']} 已下播 {b['ended_ago_min']} 分钟未发")
    else:
        add(f"[异常] 漏发兜底：{w.get('error')}")

    s = r["site"]
    if s.get("ok"):
        add(f"[{'正常' if not s.get('pending_count') else '注意'}] 站点：共 {s.get('count')} 场 / "
            f"待发 {s.get('pending_count')} 场")
    else:
        add(f"[异常] 站点：{s.get('error')}")

    d = r["disk"]
    add(f"[{'正常' if d.get('ok') else '注意'}] 磁盘剩余 {d.get('free_gb')}GB / 总 {d.get('total_gb')}GB")

    mo = r["models"]
    add(f"[{'正常' if mo.get('ok') else '异常'}] ASR 模型"
        + ("" if mo.get("ok") else " 缺失：" + ", ".join(mo.get("missing", []))))

    t = r["today"]
    add(f"[今日] {t['date']} 共 {t['count']} 场")
    for x in t.get("sessions", []):
        flag = ("已发" if x["sent"] else ("待发" if x["ended"] else "录制/转写中"))
        add(f"       {x['time']}  {x['account']}  报告{'✓' if x['has_report'] else '×'}"
            f" 复盘{'✓' if x['has_review'] else '×'}  {flag}")

    lg = r["log"]
    if lg.get("recent_errors"):
        add(f"[注意] 日志近 400 行有 {len(lg['recent_errors'])} 条报错，最后一条：")
        add("       " + lg["recent_errors"][-1][:150])
    elif lg.get("last_line"):
        add(f"[正常] 日志末行：{lg['last_line'][:110]}")

    add("-" * 56)
    add(f"结论：{r['verdict']}")
    for b in r["blockers"]:
        add(f"  · {b}")
    add("=" * 56)
    return "\n".join(L)


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    r = collect()
    if "--json" in sys.argv:
        print(json.dumps(r, ensure_ascii=False, indent=1))
    else:
        print(render_text(r))


if __name__ == "__main__":
    main()
