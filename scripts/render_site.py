# -*- coding: utf-8 -*-
"""
收盘复盘网站的页面模板（纯标准库）。

设计方向：「晚间市场简报」——暖纸色底、宋体标题、窄体数字；A 股配色红涨绿跌。
首页先讲最新一期发生了什么（标题句 + 三大指数 + 涨跌家数 + 成交额），
再是行业强弱、近期走势、往期时间线。每日页是同样结构的完整版 + 原文。
"""
import os, json, html, shutil, datetime, re

E = html.escape
VER = datetime.datetime.now().strftime("%y%m%d%H%M%S")  # 样式表版本号，避免浏览器缓存旧样式
WEEK = "一二三四五六日"

def d_of(s): return datetime.date.fromisoformat(s)
def cn_date(s): d = d_of(s); return f"{d.year} 年 {d.month} 月 {d.day} 日 · 周{WEEK[d.weekday()]}"
def pct(v, dgt=2): return "—" if v is None else f"{v:+.{dgt}f}%"
def cls(v): return "flat" if v is None or v == 0 else ("up" if v > 0 else "dn")
def wan(v): return "—" if v is None else (f"{v/1e4:.2f}" if v >= 1e4 else f"{v:.0f}")
def wan_u(v): return "" if v is None else ("万亿" if v >= 1e4 else "亿")
def arrow(v): return "" if v is None or v == 0 else ("▲" if v > 0 else "▼")

# ---------------------------------------------------------------- 外壳
FN = "https://wanan99999.github.io/finance-news-daily/"
def cross(date):
    """与「每日财经要闻」网站互跳：首页→首页；单日页→同一天的要闻（那天没有要闻时，脚本把链接改回要闻首页）"""
    if not date: return f'<a class="xsite" href="{FN}">财经要闻<span aria-hidden="true">›</span></a>'
    return (f'<a class="xsite" id="xsite" href="{FN}d/{date}.html"><span class="xs-k">当日财经要闻</span><span aria-hidden="true">›</span></a>'
            f"<script>fetch('{FN}days.json',{{cache:'no-store'}}).then(r=>r.json()).then(l=>{{if(!l.some(x=>x.date==='{date}')){{const a=document.getElementById('xsite');a.href='{FN}';a.querySelector('.xs-k').textContent='财经要闻';}}}}).catch(()=>{{}});</script>")

def page(title, body, depth=0, desc="", date=None):
    pre = "../" * depth
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{E(title)}</title>
<meta name="description" content="{E(desc)}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow+Semi+Condensed:wght@500;600;700&family=Noto+Sans+SC:wght@400;500;700&family=Noto+Serif+SC:wght@600;700;900&display=swap">
<link rel="stylesheet" href="{pre}assets/style.css?v={VER}">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='8' fill='%23182c4f'/%3E%3Cpath d='M7 21l5-6 4 3 9-9' stroke='%23f5f3ee' stroke-width='3' fill='none' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E">
</head>
<body>
<header class="mast"><div class="mast-in">
  <a class="brand" href="{pre}index.html"><span class="mark" aria-hidden="true"></span>收盘复盘</a>
  <nav class="mast-nav"><a href="{pre}index.html#archive">往期</a><a class="cta" href="{pre}upload.html">上传复盘</a>{cross(date)}</nav>
</div></header>
<main class="wrap">
{body}
</main>
<footer class="foot"><div class="foot-in"><span>每日 A 股收盘复盘</span><span>上传 Word 后自动整理发布 · 红涨绿跌</span></div></footer>
<button class="totop" id="totop" type="button" aria-label="回到顶部" title="回到顶部"><span aria-hidden="true"></span>顶部</button>
<script>(function(){{const b=document.getElementById("totop");const f=()=>b.classList.toggle("on",scrollY>400);addEventListener("scroll",f,{{passive:true}});f();b.addEventListener("click",()=>scrollTo({{top:0,behavior:matchMedia("(prefers-reduced-motion: reduce)").matches?"auto":"smooth"}}));}})();</script>
</body>
</html>
"""

# ---------------------------------------------------------------- 组件
def chip(v, dgt=2):
    return f'<span class="chg {cls(v)}"><i aria-hidden="true">{arrow(v)}</i>{pct(v, dgt)}</span>'

def breadth(b, size="lg"):
    up, dn, fl = b.get("up") or 0, b.get("down") or 0, b.get("flat") or 0; tot = up + dn + fl
    if not tot: return ""
    pu = up / tot * 100; pd_ = dn / tot * 100
    lab = (f'<div class="bm-lab"><span class="up">上涨 <b class="num">{up:.0f}</b></span>'
           + (f'<span class="flat">平盘 <b class="num">{fl:.0f}</b></span>' if fl else "")
           + f'<span class="dn">下跌 <b class="num">{dn:.0f}</b></span></div>') if size == "lg" else ""
    return (f'<div class="bm {size}">{lab}<div class="bm-bar" role="img" aria-label="上涨 {up:.0f} 家，下跌 {dn:.0f} 家">'
            f'<span class="u" style="width:{pu:.2f}%"></span>' + (f'<span class="f" style="width:{100-pu-pd_:.2f}%"></span>' if fl else "")
            + f'<span class="d" style="width:{pd_:.2f}%"></span></div>'
            + (f'<div class="bm-sub"><span>{pu:.0f}%</span><span>{pd_:.0f}%</span></div>' if size == "lg" else "") + "</div>")

def sectors(top, bot):
    if not top and not bot: return ""
    m = max([abs(s["chg"]) for s in top + bot] or [1]) or 1
    def col(title, items, kind):
        rows = "".join(f'<li title="{E(s["name"])} {s["chg"]:+.2f}%"><span class="sn">{E(s["name"])}</span>'
                       f'<span class="sb"><span class="{cls(s["chg"])}" style="width:{max(abs(s["chg"]) / m * 100, 3):.1f}%"></span></span>'
                       f'<span class="sv num {cls(s["chg"])}">{s["chg"]:+.2f}%</span></li>' for s in items)
        return f'<div class="sc {kind}"><h3>{title}</h3><ol>{rows}</ol></div>' if items else ""
    return f'<div class="sectors">{col("领涨行业", top, "rise")}{col("领跌行业", bot, "fall")}</div>'

def idx_tiles(r, prev=None, series=None):
    out = ""
    for i in r["indices"]:
        sp = ""
        if series and len(series.get(i["name"], [])) >= 2: sp = spark(series[i["name"]], cls(i["chg"]))
        out += (f'<div class="tile {cls(i["chg"])}"><div class="t-name">{E(i["name"])}</div>'
                f'<div class="t-val num">{i["close"]:,.2f}</div>{chip(i["chg"])}{sp}</div>')
    return f'<div class="tiles">{out}</div>'

def spark(vals, c):
    lo, hi = min(vals), max(vals); rg = (hi - lo) or 1; w, h = 200, 40
    pts = [(2 + k * (w - 4) / (len(vals) - 1), 3 + (hi - v) / rg * (h - 6)) for k, v in enumerate(vals)]
    d = "M" + "L".join(f"{x:.1f},{y:.1f}" for x, y in pts); x, y = pts[-1]
    area = d + f"L{pts[-1][0]:.1f},{h}L{pts[0][0]:.1f},{h}Z"
    return (f'<svg class="spark {c}" viewBox="0 0 {w} {h}" preserveAspectRatio="none" aria-hidden="true">'
            f'<path d="{area}" class="sa"/><path d="{d}" class="sl" vector-effect="non-scaling-stroke"/></svg>')

def stats(r):
    b = r["breadth"]; ratio = (b["up"] / b["down"]) if b.get("up") and b.get("down") else None
    items = [("全市场平均", f'<b class="num {cls(b.get("avg"))}">{pct(b.get("avg"))}</b>'),
             ("上涨股平均", f'<b class="num up">{pct(b.get("up_avg"))}</b>'),
             ("下跌股平均", f'<b class="num dn">{pct(b.get("down_avg"))}</b>'),
             ("涨跌比", f'<b class="num">{"—" if ratio is None else f"{ratio:.2f}"}</b>')]
    return '<dl class="stats">' + "".join(f"<div><dt>{a}</dt><dd>{v}</dd></div>" for a, v in items) + "</dl>"

def turnover_box(r, prev):
    to = r.get("turnover"); delta = ""
    if to and prev and prev.get("turnover"):
        dv = to / prev["turnover"] - 1; delta = f'<span class="tv-d {cls(dv)}">较上期 {dv:+.1%}</span>'
    elif r.get("volume"): delta = f'<span class="tv-d">较前一日{E(r["volume"])}</span>'
    return f'<div class="tv"><div class="tv-k">两市成交额</div><div class="tv-v"><span class="num">{wan(to)}</span><small>{wan_u(to)}元</small></div>{delta}</div>'

# ---------------------------------------------------------------- 走势小图（≥2 期才显示）
def trend_panels(days):
    ds = days[-40:]
    if len(ds) < 2: return ""
    W, H, L, R, T, B = 360, 150, 8, 8, 14, 22
    n = len(ds); X = lambda k: L + (k + .5) * (W - L - R) / n; bw = min((W - L - R) / n * .56, 22)
    lab = "".join(f'<text x="{X(k):.1f}" y="{H - 6}" text-anchor="middle">{d["date"][5:].replace("-", "/")}</text>'
                  for k, d in enumerate(ds) if n <= 8 or k % max(1, n // 6) == 0 or k == n - 1)
    # 上证指数日 K 蜡烛线（红涨绿跌：收盘≥开盘为红）。缺开高低收的日期用「前收→收盘」近似
    p1 = ""; nm = "上证指数"
    K = []
    for k, d in enumerate(ds):
        c = next((i["close"] for i in d["indices"] if i["name"] == nm), None)
        o = (d.get("ohlc") or {}).get(nm)
        if o: K.append(o)
        elif c is not None:
            pc = K[-1][3] if K else c; K.append([pc, max(pc, c), min(pc, c), c])
        else: K.append(None)
    if any(K):
        CW, CH, CL, CR, CT, CB = 760, 230, 8, 52, 12, 24
        cx = lambda k: CL + (k + .5) * (CW - CL - CR) / n; cw = max(min((CW - CL - CR) / n * .62, 14), 2)
        lo = min(x[2] for x in K if x); hi = max(x[1] for x in K if x); pad = (hi - lo) * .06 or 10; lo -= pad; hi += pad
        Y = lambda v: CT + (hi - v) / (hi - lo) * (CH - CT - CB)
        step = 10 ** max(0, len(str(int((hi - lo) / 4))) - 1); step = next(m * step for m in (1, 2, 5, 10) if (hi - lo) / (m * step) <= 5)
        g, t = "", (int(lo // step) + 1) * step
        while t < hi:
            near = K[-1] and abs(Y(t) - Y(K[-1][3])) < 14   # 离最新价标签太近的刻度不写数字
            g += f'<line x1="{CL}" x2="{CW - CR}" y1="{Y(t):.1f}" y2="{Y(t):.1f}" class="gl"/>' + ("" if near else f'<text x="{CW - CR + 6}" y="{Y(t) + 4:.1f}" class="yl">{t:,.0f}</text>'); t += step
        cs = ""
        for k, x in enumerate(K):
            if not x: continue
            o, h_, l_, c = x; up = c >= o; cl = "cu" if up else "cd"
            top, bot = Y(max(o, c)), Y(min(o, c)); prev = K[k - 1][3] if k and K[k - 1] else None
            chg = f"  {((c / prev - 1) * 100):+.2f}%" if prev else ""
            cs += (f'<g class="{cl}"><title>{ds[k]["date"]}  开 {o:,.2f}  高 {h_:,.2f}  低 {l_:,.2f}  收 {c:,.2f}{chg}</title>'
                   f'<line x1="{cx(k):.1f}" x2="{cx(k):.1f}" y1="{Y(h_):.1f}" y2="{Y(l_):.1f}"/>'
                   f'<rect x="{cx(k) - cw / 2:.1f}" y="{top:.1f}" width="{cw:.1f}" height="{max(bot - top, 1):.1f}"/></g>')
        last = K[-1]
        mark = (f'<line x1="{CL}" x2="{CW - CR}" y1="{Y(last[3]):.1f}" y2="{Y(last[3]):.1f}" class="lastl"/>'
                f'<rect x="{CW - CR + 2}" y="{Y(last[3]) - 9:.1f}" width="{CR - 4}" height="18" rx="4" class="lastb {"cu" if last[3] >= last[0] else "cd"}"/>'
                f'<text x="{CW - CR / 2:.1f}" y="{Y(last[3]) + 4:.1f}" text-anchor="middle" class="lastt">{last[3]:,.0f}</text>') if last else ""
        clab = "".join(f'<text x="{cx(k):.1f}" y="{CH - 6}" text-anchor="middle">{d["date"][5:].replace("-", "/")}</text>'
                       for k, d in enumerate(ds) if n <= 12 or k % max(1, n // 8) == 0 or k == n - 1)
        p1 = (f'<figure class="tp wide"><figcaption>{nm} 日K <span class="lg"><i class="up"></i>阳线 <i class="dn"></i>阴线</span></figcaption>'
              f'<div class="kscroll" id="kscroll"><svg viewBox="0 0 {CW} {CH}" role="img" aria-label="{nm}日K线，最近 {n} 个交易日">{g}{cs}{mark}{clab}</svg></div></figure>'
              '<script>(function(){const k=document.getElementById("kscroll");if(k)k.scrollLeft=k.scrollWidth;})();</script>')
    # 涨跌家数
    mx = max(max(d["breadth"].get("up") or 0, d["breadth"].get("down") or 0) for d in ds) or 1; mid = T + (H - T - B) / 2; hh = (H - T - B) / 2 - 2
    bars = "".join(f'<g><title>{d["date"]} 上涨 {d["breadth"].get("up") or 0:.0f} / 下跌 {d["breadth"].get("down") or 0:.0f}</title>'
                   f'<rect class="bu" x="{X(k) - bw/2:.1f}" y="{mid - (d["breadth"].get("up") or 0) / mx * hh:.1f}" width="{bw:.1f}" height="{(d["breadth"].get("up") or 0) / mx * hh:.1f}" rx="2"/>'
                   f'<rect class="bd" x="{X(k) - bw/2:.1f}" y="{mid + 1:.1f}" width="{bw:.1f}" height="{(d["breadth"].get("down") or 0) / mx * hh:.1f}" rx="2"/></g>' for k, d in enumerate(ds))
    p2 = f'<figure class="tp"><figcaption>涨跌家数 <span class="lg"><i class="up"></i>上涨 <i class="dn"></i>下跌</span></figcaption><svg viewBox="0 0 {W} {H}" role="img" aria-label="每日上涨与下跌家数"><line x1="{L}" x2="{W - R}" y1="{mid:.1f}" y2="{mid:.1f}" class="ax"/>{bars}{lab}</svg></figure>'
    # 成交额
    tv = [d.get("turnover") or 0 for d in ds]; mt = max(tv) or 1
    tb = "".join(f'<g><title>{d["date"]} 成交额 {wan(v)} {wan_u(v)}元</title><rect class="bt" x="{X(k) - bw/2:.1f}" y="{H - B - v / mt * (H - T - B):.1f}" width="{bw:.1f}" height="{v / mt * (H - T - B):.1f}" rx="2"/>'
                 + (f'<text class="tvl" x="{X(k):.1f}" y="{H - B - v / mt * (H - T - B) - 4:.1f}" text-anchor="middle">{v/1e4:.2f}</text>' if n <= 10 and v else "") + "</g>"
                 for k, (d, v) in enumerate(zip(ds, tv)))
    p3 = f'<figure class="tp"><figcaption>成交额（万亿元）</figcaption><svg viewBox="0 0 {W} {H}" role="img" aria-label="每日成交额">{tb}{lab}</svg></figure>'
    return f'<section class="sec"><div class="sec-h"><h2>近期走势</h2><span class="sec-note">最近 {n} 期</span></div><div class="trends">{p1}{p2}{p3}</div></section>'

# ---------------------------------------------------------------- 页面
def archive(days):
    """往期按月分组：月份导航 + 每月一个可折叠分组（最近一个月默认展开）。每月一行汇总：期数、上证月内涨跌、平均成交额。"""
    months = {}
    for d in reversed(days): months.setdefault(d["date"][:7], []).append(d)
    nav = "".join(f'<button class="mchip" type="button" data-m="{m}" aria-pressed="{"true" if k == 0 else "false"}">{int(m[:4])} 年 {int(m[5:])} 月<small>{len(v)}</small></button>' for k, (m, v) in enumerate(months.items()))
    groups = ""
    for gi, (m, ds) in enumerate(months.items()):
        items = ""
        for d in ds:
            dt = d_of(d["date"])
            chips = "".join(f'<span class="ai"><em>{E(i["name"][:2])}</em>{chip(i["chg"])}</span>' for i in d["indices"][:3])
            items += (f'<a class="ar" href="d/{d["date"]}.html"><div class="ar-date"><span class="ar-d num">{dt.day:02d}</span><span class="ar-m">{dt.month} 月<br>周{WEEK[dt.weekday()]}</span></div>'
                      f'<div class="ar-main"><h3>{E(d["title"])}</h3><p>{E(d["headline"])}</p><div class="ar-chips">{chips}</div></div>'
                      f'<div class="ar-side">{breadth(d["breadth"], "sm")}<span class="ar-tv"><span class="num">{wan(d.get("turnover"))}</span> {wan_u(d.get("turnover"))}</span></div></a>')
        # 月度汇总：上证（第一个指数）月内各日涨跌连乘、上涨天数、平均成交额
        first = ds[0]["indices"][0]["name"] if ds[0]["indices"] else None
        chg = [next((i["chg"] for i in d["indices"] if i["name"] == first), None) for d in ds]
        chg = [c for c in chg if c is not None]
        mret = None
        if chg:
            mret = 1.0
            for c in chg: mret *= 1 + c / 100
            mret = (mret - 1) * 100
        upd = sum(1 for c in chg if c > 0)
        tvs = [d["turnover"] for d in ds if d.get("turnover")]
        summ = (f'<span class="ms">{len(ds)} 期</span>'
                + (f'<span class="ms" title="按已收录交易日的涨跌幅连乘">{E(first)} 本月 {chip(mret)}</span>' if mret is not None else "")
                + (f'<span class="ms">上涨 {upd} 天 / 下跌 {len(chg) - upd} 天</span>' if chg else "")
                + (f'<span class="ms">日均成交 <b class="num">{wan(sum(tvs) / len(tvs))}</b> {wan_u(sum(tvs) / len(tvs))}</span>' if tvs else ""))
        groups += (f'<div class="mg" id="m-{m}" data-m="{m}"{"" if gi == 0 else " hidden"}><div class="mg-h"><span class="mg-t">{int(m[:4])} 年 <b>{int(m[5:])}</b> 月</span>'
                   f'<span class="mg-s">{summ}</span></div><div class="arlist">{items}</div></div>')
    navh = f'<nav class="mnav" aria-label="选择月份">{nav}</nav>'
    return (f'<section class="sec" id="archive"><div class="sec-h"><h2>往期复盘</h2><span class="sec-note">共 {len(days)} 期 · {len(months)} 个月</span></div>'
            f'{navh}<div class="mgs">{groups}</div></section>'
            '<script>/* 月份切换：只显示所选月份，不滚动页面；所选月份记在网址里，刷新或返回后保持 */'
            '(function(){const bs=[...document.querySelectorAll(".mchip")],gs=[...document.querySelectorAll(".mg")];'
            'function show(m,save){if(!gs.some(g=>g.dataset.m===m))return;gs.forEach(g=>g.hidden=g.dataset.m!==m);bs.forEach(b=>b.setAttribute("aria-pressed",b.dataset.m===m?"true":"false"));'
            'if(save)history.replaceState(null,"",location.pathname+location.search+"#m-"+m);}'
            'bs.forEach(b=>b.addEventListener("click",()=>show(b.dataset.m,true)));'
            'const h=location.hash.match(/^#m-([0-9]{4}-[0-9]{2})$/);if(h)show(h[1],false);})();</script>')

def index_page(days):
    if not days:
        return page("收盘复盘", '<section class="empty"><h1>还没有复盘</h1><p>点右上角「上传复盘」上传第一份 Word 文档，约 1 分钟后出现在这里。</p><a class="btn" href="upload.html">上传复盘</a></section>')
    r = days[-1]; prev = days[-2] if len(days) > 1 else None
    series = {}
    for d in days[-40:]:
        for i in d["indices"]: series.setdefault(i["name"], []).append(i["close"])
    body = f"""<section class="lead">
  <div class="lead-text">
    <div class="eyebrow"><span class="dot" aria-hidden="true"></span>最新一期 · {cn_date(r["date"])}</div>
    <h1>{E(r["headline"] or r["title"])}</h1>
    <a class="more" href="d/{r["date"]}.html">阅读{E(r["title"])}全文</a>
  </div>
  {turnover_box(r, prev)}
</section>
{idx_tiles(r, prev, series)}
<section class="card breadth-card"><div class="sec-h"><h2>涨跌分布</h2></div>{breadth(r["breadth"])}{stats(r)}</section>
{f'<section class="card"><div class="sec-h"><h2>行业强弱</h2><span class="sec-note">申万一级 · {r["date"][5:].replace("-", "/")}</span></div>{sectors(r["top"], r["bottom"])}</section>' if r["top"] or r["bottom"] else ""}
{trend_panels(days)}
{archive(days)}"""
    return page("收盘复盘 · 每日 A 股收盘简报", body, 0, r["headline"])

def prose(paras):
    out = ""
    for p in paras:
        s = E(p)
        s = re.sub(r"[（(](-?\d+(?:\.\d+)?)%[）)]", lambda m: f'（<span class="num {cls(float(m.group(1)))}">{float(m.group(1)):+.2f}%</span>）', s)
        out += f"<p>{s}</p>"
    return out

def day_page(r, prev, nxt):
    nav = ('<nav class="pn">' + (f'<a class="pn-a" href="{prev["date"]}.html"><small>上一期 · {prev["date"][5:].replace("-", "/")}</small><b>{E(prev["title"])}</b></a>' if prev else "<span></span>")
           + (f'<a class="pn-a next" href="{nxt["date"]}.html"><small>下一期 · {nxt["date"][5:].replace("-", "/")}</small><b>{E(nxt["title"])}</b></a>' if nxt else "<span></span>") + "</nav>")
    body = f"""<a class="back" href="../index.html">返回全部日期</a>
<section class="lead day">
  <div class="lead-text">
    <div class="eyebrow">{cn_date(r["date"])}</div>
    <h1>{E(r["title"])}</h1>
    {f'<p class="dek">{E(r["headline"])}</p>' if r["headline"] else ""}
  </div>
  {turnover_box(r, prev)}
</section>
{idx_tiles(r)}
{f'<section class="card breadth-card"><div class="sec-h"><h2>涨跌分布</h2></div>{breadth(r["breadth"])}{stats(r)}</section>' if r["breadth"].get("up") is not None else ""}
{f'<section class="card"><div class="sec-h"><h2>行业强弱</h2><span class="sec-note">申万一级 · 涨幅前五 / 跌幅前五</span></div>{sectors(r["top"], r["bottom"])}</section>' if r["top"] or r["bottom"] else ""}
<article class="card article"><div class="sec-h"><h2>{"市场数据" if r.get("generated") else "复盘原文"}</h2>{'<span class="sec-note">由行情数据计算生成 · 不含点评</span>' if r.get("generated") else f'<a class="dl" href="../docx/{r["date"]}.docx" download="{r["date"]}_收盘复盘.docx">下载 Word</a>'}</div>{prose(r["paras"])}</article>
{nav}"""
    return page(f'{r["title"]} · 收盘复盘', body, 1, r["headline"], r["date"])

UPLOAD = """<a class="back" href="index.html">返回</a>
<section class="lead day"><div class="lead-text"><div class="eyebrow">上传后自动整理发布，约 1–2 分钟</div><h1>上传复盘</h1>
<p class="dek">文件名或正文里要有日期，例如 2026.11.17.docx。同一天重复上传会覆盖。</p></div></section>
<section class="card up-card">
  <ol class="steps">
    <li><div class="st-h"><span class="st-n">1</span>访问令牌</div>
      <div class="tokrow"><input id="tok" type="password" autocomplete="off" placeholder="github_pat_…" aria-label="GitHub 访问令牌"><button class="btn ghost" id="forget" type="button">清除</button></div>
      <p class="hint">只需填一次，保存在这台设备的浏览器里，不会上传到网站。需对本仓库有 Contents 读写、Actions 只读权限。</p></li>
    <li><div class="st-h"><span class="st-n">2</span>选择 Word 文件</div>
      <div class="drop" id="drop" tabindex="0" role="button" aria-label="选择或拖入 Word 文件"><input id="file" type="file" accept=".docx" multiple hidden>
        <span class="drop-ic" aria-hidden="true"></span><span><b>点击选择</b>，或把 .docx 拖到这里</span><small>可一次选多份</small></div>
      <ul class="files" id="files"></ul></li>
    <li><div class="st-h"><span class="st-n">3</span>上传并发布</div>
      <button class="btn" id="go" type="button" disabled>上传并发布</button>
      <div class="status" id="status" aria-live="polite"></div></li>
  </ol>
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
  $("files").innerHTML = picked.map(f => `<li><span>${f.name.replace(/[<>&]/g, "")}</span><small>${Math.max(1, Math.round(f.size / 1024))} KB</small></li>`).join("") || '<li class="warn">请选择 .docx 文件</li>';
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
      say(`正在上传 ${k + 1}/${picked.length}：${f.name.replace(/[<>&]/g, "")}`);
      const name = f.name.replace(/[^\\w.\\-\\u4e00-\\u9fa5]/g, "_"), path = "/contents/inbox/" + encodeURIComponent(name);
      const ex = await gh(path); const sha = ex.status === 200 ? (await ex.json()).sha : undefined;
      await gh(path, { method: "PUT", body: JSON.stringify({ message: "上传复盘 " + name, content: b64(await f.arrayBuffer()), ...(sha ? { sha } : {}) }) });
    }
    say("上传完成，网站正在自动整理发布……");
    for (let i = 0; i < 60; i++) {
      await new Promise(r => setTimeout(r, 5000));
      const r = await gh(`/actions/runs?branch=main&per_page=5&created=${encodeURIComponent(">=" + t0)}`); const runs = (await r.json()).workflow_runs || [];
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
/* ---------- tokens ---------- */
:root {
  --bg: #f4f1ea; --paper: #fffdf8; --ink: #16181d; --ink-2: #4a4e57; --ink-3: #8b8e95; --rule: #e4ddcf; --rule-2: #efe9dd;
  --navy: #182c4f; --navy-ink: #f5f3ee; --accent: #1f4f9a; --line: #182c4f;
  --up: #d1352f; --dn: #0d9152; --flat: #a9acb3; --up-bg: rgba(209,53,47,.09); --dn-bg: rgba(13,145,82,.10); --bar: #8ea7cf;
  --serif: "Noto Serif SC", "Songti SC", "SimSun", serif;
  --sans: "Noto Sans SC", "PingFang SC", "Microsoft YaHei", system-ui, sans-serif;
  --numf: "Barlow Semi Condensed", "Noto Sans SC", system-ui, sans-serif;
  --r: 14px; --shadow: 0 1px 0 rgba(22,24,29,.04), 0 8px 24px -16px rgba(22,24,29,.18);
}
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
  --bg: #0f1216; --paper: #161a20; --ink: #eceae4; --ink-2: #b7b9bf; --ink-3: #868a93; --rule: #2a2f37; --rule-2: #20252c;
  --navy: #0b1526; --navy-ink: #eceae4; --accent: #86aef0; --line: #86aef0; --up: #ff5f58; --dn: #2fc27f; --flat: #5b6069;
  --up-bg: rgba(255,95,88,.12); --dn-bg: rgba(47,194,127,.12); --bar: #5f80b5; --shadow: none; color-scheme: dark } }
:root[data-theme="dark"] {
  --bg: #0f1216; --paper: #161a20; --ink: #eceae4; --ink-2: #b7b9bf; --ink-3: #868a93; --rule: #2a2f37; --rule-2: #20252c;
  --navy: #0b1526; --navy-ink: #eceae4; --accent: #86aef0; --line: #86aef0; --up: #ff5f58; --dn: #2fc27f; --flat: #5b6069;
  --up-bg: rgba(255,95,88,.12); --dn-bg: rgba(47,194,127,.12); --bar: #5f80b5; --shadow: none; color-scheme: dark }
* { box-sizing: border-box }
html { scroll-padding-top: 72px }
body { margin: 0; background: var(--bg); color: var(--ink); font-family: var(--sans); font-size: 15px; line-height: 1.75; -webkit-font-smoothing: antialiased }
a { color: var(--accent); text-decoration: none } a:hover { text-decoration: underline; text-underline-offset: 3px }
.num { font-family: var(--numf); font-variant-numeric: tabular-nums; letter-spacing: .01em }
.up { color: var(--up) } .dn { color: var(--dn) } .flat { color: var(--ink-3) }
:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; border-radius: 4px }
/* ---------- masthead ---------- */
.mast { background: var(--navy); color: var(--navy-ink); position: sticky; top: 0; z-index: 10 }
.mast-in { max-width: 1040px; margin: 0 auto; padding: 12px 20px; display: flex; align-items: center; gap: 16px }
.brand { color: var(--navy-ink); font-family: var(--serif); font-weight: 900; font-size: 20px; letter-spacing: .08em; display: inline-flex; align-items: center; gap: 10px }
.brand:hover { text-decoration: none } .mark { width: 10px; height: 10px; border-radius: 2px; background: linear-gradient(135deg, var(--up) 50%, var(--dn) 50%) }
.mast-nav { margin-left: auto; display: flex; align-items: center; gap: 18px; font-size: 14px } .mast-nav a { color: rgba(245,243,238,.82) } .mast-nav a:hover { color: #fff; text-decoration: none }
.mast-nav .cta { font-weight: 500 }
.wrap { max-width: 1040px; margin: 0 auto; padding: 32px 20px 72px; display: grid; gap: 22px; min-width: 0 }
.foot { border-top: 1px solid var(--rule); color: var(--ink-3); font-size: 12.5px }
.foot-in { max-width: 1040px; margin: 0 auto; padding: 18px 20px; display: flex; justify-content: space-between; gap: 12px; flex-wrap: wrap }
/* ---------- lead ---------- */
.lead { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 24px; align-items: end; padding: 8px 0 18px; border-bottom: 2px solid var(--ink) }
.eyebrow { font-size: 13px; color: var(--ink-2); letter-spacing: .04em; display: flex; align-items: center; gap: 8px }
.eyebrow .dot { width: 7px; height: 7px; border-radius: 50%; background: var(--up); box-shadow: 0 0 0 4px var(--up-bg) }
.lead h1 { font-family: var(--serif); font-weight: 900; font-size: clamp(26px, 4.4vw, 44px); line-height: 1.22; margin: 10px 0 12px; letter-spacing: .01em; text-wrap: balance }
.lead.day h1 { font-size: clamp(28px, 4.8vw, 46px) }
.dek { margin: 0; font-size: 17px; color: var(--ink-2); max-width: 40em }
.more { font-size: 15px; font-weight: 500; display: inline-flex; gap: 6px; align-items: center } .more::after { content: "→" }
.tv { text-align: right; min-width: 170px } .tv-k { font-size: 12.5px; color: var(--ink-3); letter-spacing: .06em }
.tv-v { display: flex; align-items: baseline; justify-content: flex-end; gap: 4px; line-height: 1.05 } .tv-v .num { font-size: 52px; font-weight: 700 } .tv-v small { font-size: 14px; color: var(--ink-2) }
.tv-d { font-size: 13px; color: var(--ink-2) } .tv-d.up { color: var(--up) } .tv-d.dn { color: var(--dn) }
/* ---------- index tiles ---------- */
.tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 12px }
.tile { background: var(--paper); border: 1px solid var(--rule); border-radius: var(--r); padding: 16px 18px 12px; box-shadow: var(--shadow); position: relative; overflow: hidden; display: grid; gap: 2px }
.tile::before { content: ""; position: absolute; inset: 0 auto 0 0; width: 4px; background: var(--flat) } .tile.up::before { background: var(--up) } .tile.dn::before { background: var(--dn) }
.t-name { font-size: 14px; color: var(--ink-2); font-weight: 500 } .t-val { font-size: 34px; font-weight: 700; line-height: 1.15 }
.chg { display: inline-flex; align-items: center; gap: 4px; justify-self: start; font-family: var(--numf); font-weight: 600; font-size: 15px; padding: 1px 10px 1px 8px; border-radius: 999px; background: var(--rule-2); color: var(--ink-2) }
.chg i { font-style: normal; font-size: 10px } .chg.up { background: var(--up-bg); color: var(--up) } .chg.dn { background: var(--dn-bg); color: var(--dn) }
.spark { width: 100%; height: 40px; margin-top: 8px } .spark .sl { fill: none; stroke: var(--ink-3); stroke-width: 2 } .spark .sa { fill: var(--rule-2) }
.spark.up .sl { stroke: var(--up) } .spark.up .sa { fill: var(--up-bg) } .spark.dn .sl { stroke: var(--dn) } .spark.dn .sa { fill: var(--dn-bg) }
/* ---------- cards ---------- */
.card { background: var(--paper); border: 1px solid var(--rule); border-radius: var(--r); padding: 20px 22px; box-shadow: var(--shadow); min-width: 0 }
.sec-h { display: flex; align-items: baseline; justify-content: space-between; gap: 12px; margin-bottom: 14px; flex-wrap: wrap }
.sec-h h2 { font-family: var(--serif); font-size: 20px; font-weight: 700; margin: 0; letter-spacing: .02em } .sec-note { font-size: 12.5px; color: var(--ink-3) }
.sec { display: grid; gap: 0 }
/* breadth meter */
.bm-lab { display: flex; justify-content: space-between; font-size: 14px; margin-bottom: 8px } .bm-lab b { font-size: 24px; font-weight: 700; margin-left: 4px }
.bm-bar { display: flex; gap: 3px; height: 16px; border-radius: 8px; overflow: hidden } .bm-bar span { display: block; height: 100% }
.bm-bar .u { background: var(--up) } .bm-bar .d { background: var(--dn) } .bm-bar .f { background: var(--flat) }
.bm-sub { display: flex; justify-content: space-between; font-size: 12px; color: var(--ink-3); margin-top: 4px; font-family: var(--numf) }
.bm.sm .bm-bar { height: 6px; border-radius: 3px; gap: 2px; width: 120px }
.stats { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 0; margin: 16px 0 0; border-top: 1px solid var(--rule-2) }
.stats div { padding: 12px 14px 2px; border-left: 1px solid var(--rule-2) } .stats div:first-child { border-left: 0; padding-left: 0 }
.stats dt { font-size: 12.5px; color: var(--ink-3) } .stats dd { margin: 0 } .stats b { font-size: 24px; font-weight: 700 }
/* sectors */
.sectors { display: grid; grid-template-columns: 1fr 1fr; gap: 28px }
.sc h3 { font-size: 13px; font-weight: 500; color: var(--ink-3); margin: 0 0 8px; letter-spacing: .06em } .sc.rise h3 { color: var(--up) } .sc.fall h3 { color: var(--dn) }
.sc ol { list-style: none; margin: 0; padding: 0; display: grid; gap: 4px; counter-reset: s }
.sc li { display: grid; grid-template-columns: 22px 5.5em minmax(0, 1fr) 64px; align-items: center; gap: 10px; padding: 5px 0; border-bottom: 1px dashed var(--rule-2); counter-increment: s }
.sc li::before { content: counter(s); font-family: var(--numf); font-weight: 600; color: var(--ink-3); font-size: 14px }
.sc li:last-child { border-bottom: 0 } .sn { font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis }
.sb { height: 10px; background: var(--rule-2); border-radius: 5px; overflow: hidden } .sb span { display: block; height: 100%; border-radius: 5px }
.sb .up { background: var(--up) } .sb .dn { background: var(--dn) } .sb .flat { background: var(--flat) }
.sv { text-align: right; font-weight: 600; font-size: 16px }
/* trends */
.trends { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px } .tp.wide { grid-column: 1 / -1 } .kscroll { overflow-x: auto; -webkit-overflow-scrolling: touch; scrollbar-width: thin }
@media (max-width: 680px) { .kscroll svg { min-width: 620px } }
.tp .gl { stroke: var(--rule-2); stroke-width: 1 } .tp .yl { font-size: 11.5px }
.tp .cu line { stroke: var(--up); stroke-width: 1.2 } .tp .cu rect { fill: var(--up) } .tp .cd line { stroke: var(--dn); stroke-width: 1.2 } .tp .cd rect { fill: var(--dn) }
.tp .lastl { stroke: var(--ink-3); stroke-dasharray: 3 3; stroke-width: 1 } .tp .lastb.cu { fill: var(--up) } .tp .lastb.cd { fill: var(--dn) } .tp .lastt { fill: #fff; font-size: 11.5px; font-weight: 600 }
.tp { margin: 0; background: var(--paper); border: 1px solid var(--rule); border-radius: var(--r); padding: 14px 14px 8px; box-shadow: var(--shadow); min-width: 0 }
.tp figcaption { font-size: 13.5px; font-weight: 500; color: var(--ink-2); display: flex; justify-content: space-between; gap: 8px }
.tp .lg { font-size: 12px; color: var(--ink-3); font-weight: 400; display: inline-flex; align-items: center; gap: 4px } .tp .lg i { width: 8px; height: 8px; border-radius: 2px; display: inline-block; margin-left: 6px }
.tp .lg i.up { background: var(--up) } .tp .lg i.dn { background: var(--dn) }
.tp svg { display: block; width: 100%; height: auto; overflow: visible } .tp text { fill: var(--ink-3); font-size: 11px; font-family: var(--numf) }
.tp .ln { fill: none; stroke: var(--line); stroke-width: 2.25 } .tp circle { fill: var(--paper); stroke: var(--line); stroke-width: 2 }
.tp .bu { fill: var(--up) } .tp .bd { fill: var(--dn) } .tp .bt { fill: var(--bar) } .tp .ax { stroke: var(--rule) } .tp .tvl { fill: var(--ink-2); font-size: 11.5px }
/* archive */
.arlist { display: grid; gap: 10px }
.ar { display: grid; grid-template-columns: 92px minmax(0, 1fr) auto; gap: 20px; align-items: center; background: var(--paper); border: 1px solid var(--rule); border-radius: var(--r); padding: 16px 20px; color: var(--ink); box-shadow: var(--shadow); transition: border-color .15s, transform .15s }
.ar:hover { text-decoration: none; border-color: var(--ink-3); transform: translateY(-1px) }
.ar-date { display: grid; justify-items: start; border-right: 1px solid var(--rule); padding-right: 16px } .ar-d { font-size: 40px; font-weight: 700; line-height: 1 } .ar-m { font-size: 12.5px; color: var(--ink-3); margin-top: 4px; line-height: 1.45; white-space: nowrap }
.ar-main h3 { font-family: var(--serif); font-size: 18px; margin: 0 } .ar-main p { margin: 2px 0 8px; color: var(--ink-2); font-size: 14px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis }
.ar-chips { display: flex; gap: 12px; flex-wrap: wrap } .ai { display: inline-flex; align-items: center; gap: 6px; font-size: 13px } .ai em { font-style: normal; color: var(--ink-3) } .ai .chg { font-size: 13.5px; padding: 0 8px 0 6px }
.ar-side { display: grid; justify-items: end; gap: 8px; font-size: 13px; color: var(--ink-2) } .ar-tv .num { font-size: 20px; font-weight: 700; color: var(--ink) }
/* article */
.article p { margin: 0 0 14px; font-size: 16px; line-height: 1.95; text-align: justify } .article p:last-child { margin: 0 }
.article .num { font-weight: 600 } .dl { font-size: 14px; font-weight: 500; border: 1px solid var(--rule); padding: 3px 14px; border-radius: 999px } .dl:hover { text-decoration: none; border-color: var(--accent) }
/* back / prev-next */
.back { display: inline-flex; align-items: center; gap: 8px; justify-self: start; font-size: 15px; color: var(--ink-2); padding: 7px 18px 7px 12px; border: 1px solid var(--rule); border-radius: 999px; background: var(--paper) }
.back::before { content: ""; width: 8px; height: 8px; border-left: 2px solid currentColor; border-bottom: 2px solid currentColor; transform: rotate(45deg); margin-left: 4px }
.back:hover { text-decoration: none; color: var(--ink); border-color: var(--ink-3) }
.pn { display: grid; grid-template-columns: 1fr 1fr; gap: 12px }
.pn-a { display: grid; gap: 2px; background: var(--paper); border: 1px solid var(--rule); border-radius: var(--r); padding: 14px 18px; color: var(--ink) } .pn-a.next { text-align: right }
.pn-a small { color: var(--ink-3); font-size: 12.5px } .pn-a b { font-family: var(--serif); font-size: 17px } .pn-a:hover { text-decoration: none; border-color: var(--ink-3) }
/* upload */
.up-card { padding: 8px 22px } .steps { list-style: none; margin: 0; padding: 0 }
.steps > li { padding: 18px 0; border-bottom: 1px solid var(--rule-2) } .steps > li:last-child { border-bottom: 0 }
.st-h { display: flex; align-items: center; gap: 10px; font-weight: 700; margin-bottom: 10px } .st-n { width: 24px; height: 24px; border-radius: 50%; background: var(--navy); color: var(--navy-ink); display: inline-grid; place-items: center; font-family: var(--numf); font-size: 14px }
.tokrow { display: flex; gap: 8px } .tokrow input { flex: 1; min-width: 0; font: inherit; padding: 9px 14px; border: 1px solid var(--rule); border-radius: 10px; background: var(--bg); color: var(--ink) }
.hint { color: var(--ink-3); font-size: 12.5px; margin: 8px 0 0 }
.drop { border: 1.5px dashed var(--ink-3); border-radius: 12px; padding: 28px 16px; text-align: center; color: var(--ink-2); cursor: pointer; display: grid; justify-items: center; gap: 4px; background: var(--bg) }
.drop small { color: var(--ink-3) } .drop.on, .drop:hover { border-color: var(--accent); color: var(--accent) }
.drop-ic { width: 34px; height: 40px; border: 2px solid currentColor; border-radius: 4px; position: relative; margin-bottom: 6px } .drop-ic::after { content: "W"; position: absolute; inset: 0; display: grid; place-items: center; font-weight: 700; font-family: var(--numf) }
.files { list-style: none; padding: 0; margin: 10px 0 0; display: grid; gap: 6px } .files li { display: flex; justify-content: space-between; gap: 10px; background: var(--rule-2); padding: 7px 12px; border-radius: 8px; font-size: 14px } .files small { color: var(--ink-3) } .files .warn { color: var(--up) }
.btn { font: inherit; font-weight: 500; padding: 10px 26px; border-radius: 999px; border: 0; background: var(--navy); color: var(--navy-ink); cursor: pointer; display: inline-block } .btn:hover { text-decoration: none; filter: brightness(1.15) } .btn:disabled { opacity: .4; cursor: default; filter: none }
.btn.ghost { background: transparent; color: var(--ink-2); border: 1px solid var(--rule); padding: 8px 16px }
.status { margin-top: 12px; font-size: 14.5px; color: var(--ink-2) } .status.ok { color: var(--dn) } .status.err { color: var(--up) }
.empty { text-align: center; padding: 72px 20px; display: grid; gap: 12px; justify-items: center } .empty h1 { font-family: var(--serif); margin: 0 }
/* 往期按月：月份按钮切换，只显示所选月份 */
.mnav { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 16px }
.mchip { font: inherit; display: inline-flex; align-items: center; gap: 6px; padding: 5px 14px; border: 1px solid var(--rule); border-radius: 999px; background: var(--paper); color: var(--ink-2); font-size: 14px; cursor: pointer }
.mchip small { font-family: var(--numf); color: var(--ink-3); font-size: 12px } .mchip:hover { border-color: var(--ink-3); color: var(--ink) }
.mchip[aria-pressed="true"] { background: var(--navy); border-color: var(--navy); color: var(--navy-ink) } .mchip[aria-pressed="true"] small { color: var(--navy-ink); opacity: .7 }
.mg[hidden] { display: none }
.mg-h { display: grid; gap: 4px; padding: 0 2px 12px; margin-bottom: 12px; border-bottom: 1px solid var(--rule) }
.mg-t { font-family: var(--serif); font-size: 18px; font-weight: 700; color: var(--ink) } .mg-t b { font-size: 26px; font-family: var(--numf); margin: 0 2px }
.mg-s { display: flex; gap: 6px 18px; flex-wrap: wrap; align-items: center; font-size: 13px; color: var(--ink-2) } .ms { display: inline-flex; align-items: center; gap: 6px } .ms .chg { font-size: 13px; padding: 0 8px 0 6px } .ms b { font-size: 15px }
/* 与财经要闻互跳 */
.mast-nav .xsite { display: inline-flex; align-items: center; gap: 6px; background: var(--navy-ink); color: var(--navy); padding: 5px 12px 5px 16px; border-radius: 999px; font-weight: 700; white-space: nowrap; box-shadow: 0 2px 8px -2px rgba(0,0,0,.35) }
.xsite span[aria-hidden] { font-size: 18px; line-height: 1; margin-top: -2px } .mast-nav .xsite:hover { background: #fff; color: var(--navy); text-decoration: none }
@media (max-width: 520px) { .mast-nav { gap: 10px; font-size: 13px } .mast-nav a[href$="#archive"] { display: none } .mast-nav .xsite { padding: 4px 10px 4px 13px } }
/* 回到顶部 */
.totop { position: fixed; right: max(18px, env(safe-area-inset-right, 0px)); bottom: max(18px, env(safe-area-inset-bottom, 0px)); z-index: 20; font: inherit; font-size: 12px; font-weight: 500;
  width: 52px; height: 52px; border-radius: 50%; border: 1px solid var(--rule); background: var(--navy); color: var(--navy-ink); cursor: pointer;
  display: grid; place-items: center; align-content: center; gap: 0; box-shadow: 0 6px 18px -6px rgba(0,0,0,.35);
  opacity: 0; transform: translateY(12px); pointer-events: none; transition: opacity .2s, transform .2s }
.totop span { width: 9px; height: 9px; border-left: 2px solid currentColor; border-top: 2px solid currentColor; transform: rotate(45deg); margin-top: 4px }
.totop.on { opacity: 1; transform: none; pointer-events: auto } .totop:hover { filter: brightness(1.2) }
/* ---------- responsive ---------- */
@media (max-width: 680px) { .trends { grid-template-columns: minmax(0, 1fr) } }
@media (max-width: 720px) {
  .wrap { padding: 20px 16px 56px; gap: 18px } .mast-in { padding: 10px 16px }
  .lead { grid-template-columns: minmax(0, 1fr); gap: 12px } .tv { text-align: left } .tv-v { justify-content: flex-start } .tv-v .num { font-size: 40px }
  .stats { grid-template-columns: repeat(2, minmax(0, 1fr)) } .stats div:nth-child(3) { border-left: 0; padding-left: 0 }
  .sectors { grid-template-columns: minmax(0, 1fr); gap: 18px }
  .ar { grid-template-columns: 64px minmax(0, 1fr); gap: 14px; padding: 14px 16px } .ar-side { grid-column: 1 / -1; grid-auto-flow: column; justify-content: space-between; align-items: center }
  .ar-d { font-size: 32px } .ar-date { padding-right: 10px }
  .pn { grid-template-columns: minmax(0, 1fr) }
  .card { padding: 16px }
  .tiles { grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px } .tile { padding: 10px 10px 8px 12px; border-radius: 12px }
  .t-name { font-size: 12.5px } .t-val { font-size: 20px } .tile .chg { font-size: 12.5px; padding: 0 7px 0 5px } .spark { height: 26px; margin-top: 4px }
}
@media (prefers-reduced-motion: reduce) { * { transition: none !important } }
"""

def _w(path, text):
    with open(path, "w", encoding="utf8") as fh: fh.write(text)

def render(DATA, DOCX, OUT, REPO):
    shutil.rmtree(OUT, ignore_errors=True)
    for d in ("d", "assets", "docx"): os.makedirs(os.path.join(OUT, d), exist_ok=True)
    def _load(fp):
        with open(fp, encoding="utf8") as fh: return json.load(fh)
    days = sorted((_load(os.path.join(DATA, f)) for f in os.listdir(DATA) if f.endswith(".json")), key=lambda r: r["date"]) if os.path.isdir(DATA) else []
    _w(os.path.join(OUT, "assets", "style.css"), CSS)
    for i, r in enumerate(days):
        _w(os.path.join(OUT, "d", r["date"] + ".html"), day_page(r, days[i - 1] if i else None, days[i + 1] if i + 1 < len(days) else None))
        src = os.path.join(DOCX, r["date"] + ".docx")
        if os.path.exists(src): shutil.copyfile(src, os.path.join(OUT, "docx", r["date"] + ".docx"))
    _w(os.path.join(OUT, "index.html"), index_page(days))
    _w(os.path.join(OUT, "upload.html"), page("上传复盘 · 收盘复盘", UPLOAD.replace("__REPO__", REPO), 0, "上传当天的 Word 复盘"))
    _w(os.path.join(OUT, "days.json"), json.dumps([dict(date=r["date"], title=r["title"]) for r in days], ensure_ascii=False))
    # 每日数据也公开发布（供「市场看板」聚合 App / 小程序读取）
    os.makedirs(os.path.join(OUT, "data"), exist_ok=True)
    for r in days: _w(os.path.join(OUT, "data", r["date"] + ".json"), json.dumps(r, ensure_ascii=False))
    _w(os.path.join(OUT, ".nojekyll"), "")
    print(f"site: {len(days)} days -> _site/")
