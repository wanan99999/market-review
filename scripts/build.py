# -*- coding: utf-8 -*-
"""
每日收盘复盘网站生成器（只用 Python 标准库，本地和 GitHub Actions 都能跑）

  python scripts/build.py

1. 处理 inbox/ 里新上传的 .docx：解析日期、指数、涨跌家数、成交额、行业前五/后五、点评
   → 写 data/YYYY-MM-DD.json，原文件移到 docx/YYYY-MM-DD.docx（同一天重复上传会覆盖）
2. 用 data/*.json 生成整站到 _site/（首页、每日页、上传页）
"""
import os, re, json, html, shutil, zipfile, datetime
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INBOX, DOCX, DATA, OUT = (os.path.join(ROOT, d) for d in ("inbox", "docx", "data", "_site"))
REPO = os.environ.get("GITHUB_REPOSITORY", "wanan99999/market-review")
E = html.escape
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
ZW = re.compile(r"[​‌‍﻿]")

# ================================================================ 解析
def paragraphs(path):
    doc = ET.fromstring(zipfile.ZipFile(path).read("word/document.xml"))
    out = []
    for p in doc.iter(W + "p"):
        t = "".join((n.text or "") if n.tag == W + "t" else "\n" if n.tag == W + "br" else "" for n in p.iter())
        t = ZW.sub("", t).strip()
        if t: out.append(t)
    return out

def num(s): return float(s.replace(",", ""))

def find_date(text, fname):
    m = re.search(r"(20\d{2})年(\d{1,2})月(\d{1,2})日", text)
    if not m: m = re.search(r"(20\d{2})[.\-_年 ]?(\d{1,2})[.\-_月 ]?(\d{1,2})", fname)
    if m: return datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    m = re.search(r"(\d{1,2})[.月](\d{1,2})", fname + " " + text[:30])
    if m:
        y = datetime.date.today().year
        return datetime.date(y, int(m.group(1)), int(m.group(2)))
    return None

def parse(path):
    ps = paragraphs(path); text = "\n".join(ps); warn = []
    d = find_date(text, os.path.basename(path))
    if not d: raise ValueError("找不到日期：请在文件名或正文里写明，如 2026.11.17.docx")
    title = ps[0] if ps and len(ps[0]) <= 30 else f"{d.month}.{d.day}市场复盘"
    body = ps[1:] if ps and len(ps[0]) <= 30 else ps
    idx = []
    for m in re.finditer(r"([^；;，,。：:\s]{2,10}?)最新价为([\d,.]+)点[，,]?\s*(涨|跌)幅为(-?[\d.]+)%", text):
        chg = abs(num(m.group(4))) * (1 if m.group(3) == "涨" else -1)
        idx.append(dict(name=m.group(1), close=num(m.group(2)), chg=chg))
    if not idx: warn.append("没找到指数点位")
    g = lambda pat: (lambda m: num(m.group(1)) if m else None)(re.search(pat, text))
    br = dict(up=g(r"(\d+)只个股上涨"), down=g(r"(\d+)只个股下跌"), flat=g(r"(\d+)只个股(?:平盘|持平)"),
              avg=g(r"平均涨跌幅为(-?[\d.]+)%"), up_avg=g(r"上涨个股平均涨幅为(-?[\d.]+)%"), down_avg=g(r"下跌个股平均跌幅为(-?[\d.]+)%"))
    if br["up"] is None: warn.append("没找到涨跌家数")
    to = None; m = re.search(r"成交额约?([\d.]+)\s*(万亿|亿)元", text)
    if m: to = num(m.group(1)) * (1e4 if m.group(2) == "万亿" else 1)
    else: warn.append("没找到成交额")
    m = re.search(r"较(?:昨日|上一?交易日|前一交易日)(放量|缩量)", text); vol = m.group(1) if m else None
    def sectors(label):
        m = re.search(label + r"[^：:]*[：:](.+?)[。\n]", text)
        if not m: return []
        return [dict(name=re.sub(r"^\d+", "", a).strip(), chg=num(b)) for a, b in re.findall(r"([^、，,（(]+)[（(](-?[\d.]+)%[）)]", m.group(1))]
    top, bot = sectors("涨幅前五"), sectors("跌幅前五")
    if not top: warn.append("没找到行业涨幅前五")
    m = re.search(r"\d+月\d+日[，,](.+?)。", text); headline = m.group(1) if m else ""
    return dict(date=d.isoformat(), title=title, headline=headline, indices=idx, breadth=br, turnover=to, volume=vol,
                top=top, bottom=bot, paras=body, warnings=warn, source=os.path.basename(path),
                updated=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).strftime("%Y-%m-%d %H:%M"))

def ingest():
    os.makedirs(DATA, exist_ok=True); os.makedirs(DOCX, exist_ok=True); done = []
    if not os.path.isdir(INBOX): return done
    for f in sorted(os.listdir(INBOX)):
        p = os.path.join(INBOX, f)
        if not f.lower().endswith(".docx") or f.startswith("~$"): continue
        try:
            r = parse(p)
        except Exception as e:
            print(f"!! {f}: {e}"); os.makedirs(os.path.join(INBOX, "failed"), exist_ok=True)
            shutil.move(p, os.path.join(INBOX, "failed", f)); continue
        json.dump(r, open(os.path.join(DATA, r["date"] + ".json"), "w", encoding="utf8"), ensure_ascii=False, indent=1)
        shutil.move(p, os.path.join(DOCX, r["date"] + ".docx"))
        done.append(r["date"]); print(f"OK {f} -> {r['date']}" + (f"  注意：{'；'.join(r['warnings'])}" if r["warnings"] else ""))
    return done

# ================================================================ 页面
WEEK = "一二三四五六日"
def cn_date(s):
    d = datetime.date.fromisoformat(s); return f"{d.year} 年 {d.month} 月 {d.day} 日 · 周{WEEK[d.weekday()]}"
def pct(v, dgt=2): return "—" if v is None else f"{v:+.{dgt}f}%"
def cls(v): return "" if v is None or v == 0 else ("up" if v > 0 else "dn")
def yi(v): return "—" if v is None else (f"{v/1e4:.2f} 万亿" if v >= 1e4 else f"{v:.0f} 亿")

def page(title, body, depth=0, extra_head=""):
    pre = "../" * depth
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{E(title)}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;500;700&display=swap">
<link rel="stylesheet" href="{pre}assets/style.css">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='7' fill='%231a3a6b'/%3E%3Cpath d='M7 21l5-6 4 3 9-9' stroke='white' stroke-width='3' fill='none' stroke-linecap='round'/%3E%3C/svg%3E">
{extra_head}</head>
<body>
<header class="top"><div class="bar"><a class="brand" href="{pre}index.html">收盘复盘</a><span class="grow"></span><a class="upbtn" href="{pre}upload.html">上传复盘</a></div></header>
<main class="wrap">
{body}
</main>
<footer class="foot"><div class="wrap">每日 A 股收盘复盘 · 上传 Word 后自动整理发布</div></footer>
</body>
</html>
"""

def spark(vals, w=260, h=56, color="currentColor"):
    vals = [v for v in vals if v is not None]
    if len(vals) < 2: return ""
    lo, hi = min(vals), max(vals); rg = (hi - lo) or 1
    pts = [(4 + i * (w - 8) / (len(vals) - 1), 4 + (hi - v) / rg * (h - 8)) for i, v in enumerate(vals)]
    d = "M" + "L".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    x, y = pts[-1]
    return f'<svg class="spark" viewBox="0 0 {w} {h}" preserveAspectRatio="none" aria-hidden="true"><path d="{d}" fill="none" stroke="{color}" stroke-width="2" vector-effect="non-scaling-stroke"/><circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="{color}"/></svg>'

def breadth_bar(b, big=False):
    up, dn, fl = b.get("up") or 0, b.get("down") or 0, b.get("flat") or 0; tot = up + dn + fl
    if not tot: return ""
    return (f'<div class="bb{" big" if big else ""}" role="img" aria-label="上涨 {up:.0f} 家，下跌 {dn:.0f} 家">'
            f'<span class="u" style="flex:{up}"></span>' + (f'<span class="f" style="flex:{fl}"></span>' if fl else "") + f'<span class="d" style="flex:{dn}"></span></div>')

def sector_chart(top, bot):
    rows = [(s["name"], s["chg"]) for s in top] + [(s["name"], s["chg"]) for s in bot]
    if not rows: return ""
    m = max(abs(v) for _, v in rows) or 1; Wd, L, R, rh = 640, 92, 64, 30
    mid = L + (Wd - L - R) / 2; half = (Wd - L - R) / 2
    H = len(rows) * rh + (14 if top and bot else 0) + 8; out = [f'<svg class="sect" viewBox="0 0 {Wd} {H}" role="img" aria-label="行业涨跌幅前五与后五">']
    y = 4
    for i, (n, v) in enumerate(rows):
        if i == len(top) and top and bot: y += 14
        w = abs(v) / m * half; x = mid if v >= 0 else mid - w
        c = "var(--up)" if v > 0 else "var(--dn)" if v < 0 else "var(--ink-3)"
        out.append(f'<g><title>{E(n)} {v:+.2f}%</title><text x="{L - 10}" y="{y + rh/2 + 4}" text-anchor="end" class="sl">{E(n)}</text>'
                   f'<rect x="{x:.1f}" y="{y + 6}" width="{max(w, 2):.1f}" height="{rh - 12}" rx="3" fill="{c}"/>'
                   f'<text x="{(mid + w + 6) if v >= 0 else (mid - w - 6):.1f}" y="{y + rh/2 + 4}" text-anchor="{"start" if v >= 0 else "end"}" class="sv">{v:+.2f}%</text></g>')
        y += rh
    out.append(f'<line x1="{mid}" x2="{mid}" y1="0" y2="{H}" class="axis"/></svg>')
    return "".join(out)

def turnover_chart(days):
    ds = [d for d in days if d.get("turnover")][-30:]
    if len(ds) < 2: return ""
    Wd, H, L, B, T = 640, 150, 8, 24, 18; m = max(d["turnover"] for d in ds); bw = (Wd - 2 * L) / len(ds)
    out = [f'<svg class="tchart" viewBox="0 0 {Wd} {H}" role="img" aria-label="成交额">']
    for i, d in enumerate(ds):
        h = d["turnover"] / m * (H - T - B); x = L + i * bw; rw = min(bw * 0.64, 40)
        out.append(f'<g><title>{d["date"]} 成交额 {yi(d["turnover"])}</title><rect x="{x + (bw - rw) / 2:.1f}" y="{H - B - h:.1f}" width="{rw:.1f}" height="{h:.1f}" rx="3" class="tb"/>'
                   + (f'<text x="{x + bw/2:.1f}" y="{H - B - h - 5:.1f}" text-anchor="middle" class="sv">{d["turnover"]/1e4:.2f}</text>' if len(ds) <= 15 else "")
                   + f'<text x="{x + bw/2:.1f}" y="{H - 6}" text-anchor="middle" class="sl">{d["date"][5:].replace("-", "/")}</text></g>')
    out.append("</svg>"); return "".join(out)

def day_page(r, prev, nxt):
    b = r["breadth"]
    idx = "".join(f'<div class="ix"><div class="n">{E(i["name"])}</div><div class="c">{i["close"]:,.2f}</div><div class="p {cls(i["chg"])}">{pct(i["chg"])}</div></div>' for i in r["indices"])
    bs = ""
    if b.get("up") is not None:
        bs = f"""<section class="card"><h2>涨跌分布</h2>{breadth_bar(b, True)}
<div class="bl"><span class="up">上涨 <b>{b["up"]:.0f}</b> 家</span>{f'<span>平盘 <b>{b["flat"]:.0f}</b></span>' if b.get("flat") else ""}<span class="dn">下跌 <b>{b["down"]:.0f}</b> 家</span></div>
<div class="kv"><div><span>全市场平均涨跌</span><b class="{cls(b["avg"])}">{pct(b["avg"])}</b></div><div><span>上涨股平均</span><b class="up">{pct(b["up_avg"])}</b></div>
<div><span>下跌股平均</span><b class="dn">{pct(b["down_avg"])}</b></div><div><span>成交额</span><b>{yi(r["turnover"])}</b>{f'<small>较前一日{r["volume"]}</small>' if r.get("volume") else ""}</div></div></section>"""
    sc = sector_chart(r["top"], r["bottom"])
    sec = f'<section class="card"><h2>申万一级行业 · 涨幅前五 / 跌幅前五</h2>{sc}</section>' if sc else ""
    paras = "".join(f"<p>{E(p)}</p>" for p in r["paras"])
    nav = (f'<nav class="pn">' + (f'<a href="{prev["date"]}.html">‹ {prev["date"][5:].replace("-", "/")} {E(prev["title"])}</a>' if prev else "<span></span>")
           + (f'<a href="{nxt["date"]}.html">{nxt["date"][5:].replace("-", "/")} {E(nxt["title"])} ›</a>' if nxt else "<span></span>") + "</nav>")
    body = f"""<a class="back" href="../index.html">返回全部日期</a>
<header class="dh"><div class="eyebrow">{cn_date(r["date"])}</div><h1>{E(r["title"])}</h1>{f'<p class="lede">{E(r["headline"])}</p>' if r["headline"] else ""}</header>
<div class="ixs">{idx}</div>
{bs}
{sec}
<section class="card prose"><h2>复盘原文</h2>{paras}<p class="dl"><a href="../docx/{r["date"]}.docx" download="{r["date"]}_收盘复盘.docx">下载 Word 原文</a></p></section>
{nav}"""
    return page(f'{r["title"]} · 收盘复盘', body, 1)

def index_page(days):
    if not days:
        return page("收盘复盘", '<section class="card empty"><h1>还没有复盘</h1><p>点右上角「上传复盘」上传第一份 Word 文档。</p></section>')
    last = days[-1]
    names = [i["name"] for i in last["indices"]]
    cards = ""
    for n in names:
        ser = [next((i["close"] for i in d["indices"] if i["name"] == n), None) for d in days[-60:]]
        cur = next(i for i in last["indices"] if i["name"] == n)
        cards += f'<div class="ix wide {cls(cur["chg"])}"><div class="n">{E(n)}</div><div class="c">{cur["close"]:,.2f}</div><div class="p {cls(cur["chg"])}">{pct(cur["chg"])}</div>{spark(ser)}</div>'
    rows = ""
    for d in reversed(days):
        sh = d["indices"][0] if d["indices"] else None; b = d["breadth"]
        bt = "" if b.get("up") is None else "涨 %d / 跌 %d" % (b["up"], b["down"] or 0)
        rows += (f'<a class="row" href="d/{d["date"]}.html"><span class="dt">{d["date"][5:].replace("-", "/")}<small>周{WEEK[datetime.date.fromisoformat(d["date"]).weekday()]}</small></span>'
                 f'<span class="tt">{E(d["title"])}<small>{E(d["headline"])}</small></span>'
                 f'<span class="sh {cls(sh["chg"]) if sh else ""}">{E(sh["name"]) if sh else ""} {pct(sh["chg"]) if sh else ""}</span>'
                 f'<span class="br">{breadth_bar(b)}<small>{bt}</small></span>'
                 f'<span class="to">{yi(d["turnover"])}</span></a>')
    tc = turnover_chart(days)
    body = f"""<header class="hero"><h1>每日收盘复盘</h1><p class="lede">最新一期：<a href="d/{last["date"]}.html">{cn_date(last["date"])} · {E(last["title"])}</a></p></header>
<section><h2 class="sh2">主要指数 <small>截至 {last["date"]}</small></h2><div class="ixs">{cards}</div></section>
{f'<section class="card"><h2>两市成交额（万亿元）</h2>{tc}</section>' if tc else ""}
<section><h2 class="sh2">全部日期 <small>{len(days)} 期</small></h2><div class="list"><div class="row head"><span>日期</span><span>标题</span><span>上证</span><span>涨跌家数</span><span>成交额</span></div>{rows}</div></section>"""
    return page("每日收盘复盘", body)

UPLOAD = """<a class="back" href="index.html">返回</a>
<header class="dh"><h1>上传复盘</h1><p class="lede">选择当天的 Word 复盘（.docx，可多选），上传后网站会自动整理发布，大约 1–2 分钟。文件名或正文里要有日期，例如 2026.11.17.docx。</p></header>
<section class="card">
  <label class="fl" for="tok">GitHub 访问令牌</label>
  <div class="tokrow"><input id="tok" type="password" autocomplete="off" placeholder="github_pat_…（只需填一次，保存在本设备浏览器）"><button class="btn ghost" id="forget" type="button">清除</button></div>
  <p class="hint">令牌只保存在这台设备的浏览器里，不会上传到网站。需要对本仓库有 Contents 读写、Actions 只读权限。</p>
  <div class="drop" id="drop" tabindex="0" role="button" aria-label="选择或拖入 Word 文件"><input id="file" type="file" accept=".docx" multiple hidden><b>点击选择</b> 或把 .docx 拖到这里</div>
  <ul class="files" id="files"></ul>
  <button class="btn" id="go" type="button" disabled>上传并发布</button>
  <div class="status" id="status" aria-live="polite"></div>
</section>
<script>
const REPO = "__REPO__", API = "https://api.github.com/repos/" + REPO;
const $ = id => document.getElementById(id); let picked = [];
try { $("tok").value = localStorage.getItem("gh_token") || ""; } catch (e) {}
$("forget").onclick = () => { try { localStorage.removeItem("gh_token"); } catch (e) {} $("tok").value = ""; };
const drop = $("drop");
drop.onclick = () => $("file").click(); drop.onkeydown = e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); $("file").click(); } };
drop.ondragover = e => { e.preventDefault(); drop.classList.add("on"); }; drop.ondragleave = () => drop.classList.remove("on");
drop.ondrop = e => { e.preventDefault(); drop.classList.remove("on"); pick(e.dataTransfer.files); };
$("file").onchange = e => pick(e.target.files);
function pick(fs) { picked = [...fs].filter(f => /\\.docx$/i.test(f.name));
  $("files").innerHTML = picked.map(f => `<li>${f.name}<small>${Math.max(1, Math.round(f.size / 1024))} KB</small></li>`).join("") || "<li>请选择 .docx 文件</li>";
  $("go").disabled = !picked.length; }
const say = (h, c = "") => { $("status").className = "status " + c; $("status").innerHTML = h; };
const b64 = buf => { let s = "", a = new Uint8Array(buf); for (let i = 0; i < a.length; i += 0x8000) s += String.fromCharCode.apply(null, a.subarray(i, i + 0x8000)); return btoa(s); };
async function gh(path, opt = {}) { const r = await fetch(API + path, { ...opt, headers: { Authorization: "Bearer " + $("tok").value.trim(), Accept: "application/vnd.github+json", ...(opt.headers || {}) } });
  if (!r.ok && r.status !== 404) { let m = ""; try { m = (await r.json()).message; } catch (e) {} throw new Error(r.status + " " + m); } return r; }
$("go").onclick = async () => {
  const tok = $("tok").value.trim(); if (!tok) { say("请先填写访问令牌", "err"); $("tok").focus(); return; }
  try { localStorage.setItem("gh_token", tok); } catch (e) {}
  $("go").disabled = true; const t0 = new Date(Date.now() - 60000).toISOString();
  try {
    for (const [k, f] of picked.entries()) {
      say(`正在上传 ${k + 1}/${picked.length}：${f.name}`);
      const name = f.name.replace(/[^\\w.\\-\\u4e00-\\u9fa5]/g, "_"), path = "/contents/inbox/" + encodeURIComponent(name);
      const ex = await gh(path); const sha = ex.status === 200 ? (await ex.json()).sha : undefined;
      await gh(path, { method: "PUT", body: JSON.stringify({ message: "上传复盘 " + name, content: b64(await f.arrayBuffer()), ...(sha ? { sha } : {}) }) });
    }
    say("上传完成，网站正在自动整理发布……");
    for (let i = 0; i < 60; i++) {
      await new Promise(r => setTimeout(r, 5000));
      const r = await gh(`/actions/runs?branch=main&per_page=5&created=>=${t0}`); const runs = (await r.json()).workflow_runs || [];
      if (!runs.length) continue;
      const busy = runs.some(x => x.status !== "completed"), bad = runs.find(x => x.status === "completed" && x.conclusion !== "success" && x.conclusion !== "cancelled");
      if (bad) { say(`自动发布失败：<a href="${bad.html_url}" target="_blank" rel="noopener">查看日志</a>`, "err"); break; }
      if (!busy) { say('已发布！<a href="index.html?t=' + Date.now() + '">回到首页查看</a>（页面可能还有约 1 分钟缓存）', "ok"); break; }
      say("网站正在自动整理发布……（" + (i + 1) * 5 + " 秒）");
    }
  } catch (e) { say("出错了：" + e.message + "（检查令牌是否正确、是否有本仓库写权限）", "err"); }
  $("go").disabled = false;
};
</script>"""

CSS = r"""
:root { --bg: #f3f5f8; --surface: #fff; --ink: #121821; --ink-2: #4a5361; --ink-3: #7c8594; --rule: #e1e5eb; --chip: #eef1f5;
  --top: #14305a; --top-ink: #fff; --accent: #1f6fd1; --up: #d93838; --dn: #129b5a; --flat: #b9c0ca; --tb: #6f93c9;
  --f: "Noto Sans SC", "PingFang SC", "Microsoft YaHei", system-ui, sans-serif }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { --bg: #0f1318; --surface: #171c23; --ink: #e9edf2; --ink-2: #b4bcc8; --ink-3: #87909d;
  --rule: #2a313b; --chip: #212833; --top: #0e1f3a; --accent: #5aa0f0; --up: #f06464; --dn: #36c27c; --flat: #4a525e; --tb: #5b84c0; color-scheme: dark } }
:root[data-theme="dark"] { --bg: #0f1318; --surface: #171c23; --ink: #e9edf2; --ink-2: #b4bcc8; --ink-3: #87909d;
  --rule: #2a313b; --chip: #212833; --top: #0e1f3a; --accent: #5aa0f0; --up: #f06464; --dn: #36c27c; --flat: #4a525e; --tb: #5b84c0; color-scheme: dark }
* { box-sizing: border-box } body { margin: 0; background: var(--bg); color: var(--ink); font-family: var(--f); font-size: 15px; line-height: 1.7 }
a { color: var(--accent); text-decoration: none } a:hover { text-decoration: underline }
.top { background: var(--top); color: var(--top-ink); position: sticky; top: 0; z-index: 5 }
.bar { max-width: 980px; margin: 0 auto; padding: 10px 16px; display: flex; align-items: center; gap: 12px }
.brand { color: #fff; font-weight: 700; font-size: 18px; letter-spacing: .04em } .grow { flex: 1 }
.upbtn { color: #fff; border: 1px solid rgba(255,255,255,.45); padding: 4px 14px; border-radius: 999px; font-size: 14px } .upbtn:hover { background: rgba(255,255,255,.12); text-decoration: none }
.wrap { max-width: 980px; margin: 0 auto; padding: 24px 16px 56px; display: grid; gap: 20px; min-width: 0 }
.foot { color: var(--ink-3); font-size: 12.5px; border-top: 1px solid var(--rule) } .foot .wrap { padding: 16px }
h1 { font-size: clamp(24px, 4vw, 32px); line-height: 1.3; margin: 0 } h2 { font-size: 17px; margin: 0 0 12px }
.sh2 { margin: 0 0 10px } .sh2 small, h2 small { font-weight: 400; color: var(--ink-3); font-size: 13px; margin-left: 6px }
.lede { color: var(--ink-2); margin: 6px 0 0; font-size: 16px } .eyebrow { color: var(--ink-3); font-size: 13px }
.hero { display: grid; gap: 2px }
.card { background: var(--surface); border: 1px solid var(--rule); border-radius: 12px; padding: 18px 20px; min-width: 0 }
.up { color: var(--up) } .dn { color: var(--dn) }
.ixs { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 10px }
.ix { background: var(--surface); border: 1px solid var(--rule); border-radius: 12px; padding: 14px 16px; display: grid; gap: 2px; min-width: 0 }
.ix .n { color: var(--ink-2); font-size: 13.5px } .ix .c { font-size: 24px; font-weight: 700; font-variant-numeric: tabular-nums } .ix .p { font-weight: 500; font-variant-numeric: tabular-nums }
.ix.up { border-top: 3px solid var(--up) } .ix.dn { border-top: 3px solid var(--dn) }
.spark { width: 100%; height: 48px; margin-top: 6px; color: var(--ink-3) } .ix.up .spark { color: var(--up) } .ix.dn .spark { color: var(--dn) }
.bb { display: flex; height: 8px; border-radius: 4px; overflow: hidden; gap: 2px; min-width: 60px } .bb.big { height: 14px; border-radius: 7px }
.bb .u { background: var(--up) } .bb .d { background: var(--dn) } .bb .f { background: var(--flat) }
.bl { display: flex; justify-content: space-between; gap: 10px; margin: 8px 0 14px; font-size: 14px } .bl b { font-size: 18px; font-variant-numeric: tabular-nums }
.kv { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px }
.kv div { background: var(--chip); border-radius: 8px; padding: 10px 12px; display: grid } .kv span { color: var(--ink-3); font-size: 12.5px } .kv b { font-size: 19px; font-variant-numeric: tabular-nums } .kv small { color: var(--ink-3); font-size: 12px }
svg { display: block; width: 100%; height: auto } svg text { font-family: var(--f) }
.sect { max-width: 680px }
.sect .sl, .tchart .sl { fill: var(--ink-2); font-size: 12.5px } .sect .sv, .tchart .sv { fill: var(--ink); font-size: 12px; font-variant-numeric: tabular-nums } .axis { stroke: var(--rule) } .tb { fill: var(--tb) }
.prose p { margin: 0 0 12px; color: var(--ink) } .prose .dl { margin: 6px 0 0 }
.back { display: inline-flex; align-items: center; gap: 6px; justify-self: start; font-size: 15px; color: var(--ink-2); padding: 6px 16px 6px 10px; border: 1px solid var(--rule); border-radius: 999px; background: var(--surface) }
.back::before { content: ""; width: 8px; height: 8px; border-left: 2px solid currentColor; border-bottom: 2px solid currentColor; transform: rotate(45deg); margin-left: 4px }
.back:hover { text-decoration: none; border-color: var(--accent); color: var(--accent) }
.dh { display: grid; gap: 2px }
.pn { display: flex; justify-content: space-between; gap: 12px; flex-wrap: wrap; font-size: 14px }
.list { background: var(--surface); border: 1px solid var(--rule); border-radius: 12px; overflow: hidden }
.row { display: grid; grid-template-columns: 70px minmax(0, 1fr) 120px 150px 80px; gap: 12px; align-items: center; padding: 12px 16px; border-top: 1px solid var(--rule); color: var(--ink) }
.row:hover { background: var(--chip); text-decoration: none } .row.head { border-top: 0; font-size: 12.5px; color: var(--ink-3); background: var(--chip) } .row.head:hover { background: var(--chip) }
.row .dt { font-weight: 700; font-variant-numeric: tabular-nums; display: grid; line-height: 1.3 } .row small { color: var(--ink-3); font-weight: 400; font-size: 12px }
.row .tt { display: grid; min-width: 0; line-height: 1.4 } .row .tt small { white-space: nowrap; overflow: hidden; text-overflow: ellipsis }
.row .sh, .row .to { font-variant-numeric: tabular-nums; font-size: 14px } .row .br { display: grid; gap: 3px } .row .to { text-align: right }
@media (max-width: 640px) { .row { grid-template-columns: 56px minmax(0, 1fr) 96px } .row .br, .row .to, .row.head span:nth-child(4), .row.head span:nth-child(5) { display: none } }
/* 上传页 */
.fl { font-weight: 500; display: block; margin-bottom: 6px } .tokrow { display: flex; gap: 8px }
.tokrow input { flex: 1; min-width: 0; font: inherit; padding: 8px 12px; border: 1px solid var(--rule); border-radius: 8px; background: var(--bg); color: var(--ink) }
.hint { color: var(--ink-3); font-size: 12.5px; margin: 6px 0 16px }
.drop { border: 2px dashed var(--rule); border-radius: 12px; padding: 28px 16px; text-align: center; color: var(--ink-2); cursor: pointer }
.drop.on, .drop:hover, .drop:focus-visible { border-color: var(--accent); color: var(--accent); outline: none }
.files { list-style: none; padding: 0; margin: 12px 0; display: grid; gap: 6px } .files li { display: flex; justify-content: space-between; background: var(--chip); padding: 6px 12px; border-radius: 8px; font-size: 14px } .files small { color: var(--ink-3) }
.btn { font: inherit; font-weight: 500; padding: 9px 22px; border-radius: 8px; border: 0; background: var(--accent); color: #fff; cursor: pointer } .btn:disabled { opacity: .45; cursor: default }
.btn.ghost { background: transparent; color: var(--ink-2); border: 1px solid var(--rule); padding: 8px 14px }
.btn:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px }
.status { margin-top: 14px; font-size: 14.5px; color: var(--ink-2) } .status.ok { color: var(--dn) } .status.err { color: var(--up) }
.empty { text-align: center; padding: 48px 20px }
"""

def render():
    shutil.rmtree(OUT, ignore_errors=True)
    for d in ("d", "assets", "docx"): os.makedirs(os.path.join(OUT, d), exist_ok=True)
    days = sorted((json.load(open(os.path.join(DATA, f), encoding="utf8")) for f in os.listdir(DATA) if f.endswith(".json")), key=lambda r: r["date"]) if os.path.isdir(DATA) else []
    open(os.path.join(OUT, "assets", "style.css"), "w", encoding="utf8").write(CSS)
    for i, r in enumerate(days):
        open(os.path.join(OUT, "d", r["date"] + ".html"), "w", encoding="utf8").write(day_page(r, days[i - 1] if i else None, days[i + 1] if i + 1 < len(days) else None))
        src = os.path.join(DOCX, r["date"] + ".docx")
        if os.path.exists(src): shutil.copyfile(src, os.path.join(OUT, "docx", r["date"] + ".docx"))
    open(os.path.join(OUT, "index.html"), "w", encoding="utf8").write(index_page(days))
    open(os.path.join(OUT, "upload.html"), "w", encoding="utf8").write(page("上传复盘", UPLOAD.replace("__REPO__", REPO)))
    json.dump([dict(date=r["date"], title=r["title"]) for r in days], open(os.path.join(OUT, "days.json"), "w", encoding="utf8"), ensure_ascii=False)
    open(os.path.join(OUT, ".nojekyll"), "w").write("")
    print(f"site: {len(days)} days -> _site/")

if __name__ == "__main__":
    ingest(); render()
