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

# ================================================================ 页面（模板在 render_site.py）
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render_site
def render(): render_site.render(DATA, DOCX, OUT, REPO)


# ================================================================ 上证指数日 K（开高低收），用于首页蜡烛线
def _get(url, headers=None):
    import urllib.request
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (market-review build)", **(headers or {})})
    with urllib.request.urlopen(req, timeout=15) as r: return r.read().decode("utf8", "replace")

def _ohlc_sina():
    t = _get("https://quotes.sina.cn/cn/api/jsonp_v2.php/var=/CN_MarketDataService.getKLineData?symbol=sh000001&scale=240&ma=no&datalen=120",
             {"Referer": "https://finance.sina.com.cn"})
    rows = json.loads(t[t.index("["): t.rindex("]") + 1])
    return {r["day"][:10]: [float(r["open"]), float(r["high"]), float(r["low"]), float(r["close"])] for r in rows}

def _ohlc_yahoo():
    j = json.loads(_get("https://query1.finance.yahoo.com/v8/finance/chart/000001.SS?range=6mo&interval=1d"))["chart"]["result"][0]
    off = j["meta"].get("gmtoffset", 28800); q = j["indicators"]["quote"][0]; out = {}
    for k, ts in enumerate(j["timestamp"]):
        v = [q["open"][k], q["high"][k], q["low"][k], q["close"][k]]
        if None not in v: out[datetime.datetime.utcfromtimestamp(ts + off).date().isoformat()] = [float(x) for x in v]
    return out

def _ohlc_em():
    j = json.loads(_get("https://push2his.eastmoney.com/api/qt/stock/kline/get?secid=1.000001&fields1=f1&fields2=f51,f52,f53,f54,f55&klt=101&fqt=0&lmt=120"))
    out = {}
    for line in j["data"]["klines"]:
        d, o, c, h, l = line.split(",")[:5]; out[d] = [float(o), float(h), float(l), float(c)]
    return out

def enrich_ohlc():
    """给缺开高低收的日期补上证指数日 K；收盘价与文档一致（差 ≤0.05 点）才写入。三个来源依次尝试。"""
    if not os.path.isdir(DATA): return
    need = []
    for f in sorted(os.listdir(DATA)):
        if not f.endswith(".json"): continue
        with open(os.path.join(DATA, f), encoding="utf8") as fh: r = json.load(fh)
        if "ohlc" not in r: need.append((f, r))
    if not need: return
    for name, src in (("sina", _ohlc_sina), ("yahoo", _ohlc_yahoo), ("eastmoney", _ohlc_em)):
        try: k = src()
        except Exception as e: print(f"ohlc {name} 失败: {repr(e)[:120]}"); continue
        left = []
        for f, r in need:
            sh = next((i for i in r["indices"] if i["name"] == "上证指数"), None); v = k.get(r["date"])
            if sh and v and abs(v[3] - sh["close"]) <= 0.05:
                r["ohlc"] = {"上证指数": [round(x, 2) for x in v]}
                with open(os.path.join(DATA, f), "w", encoding="utf8") as fh: json.dump(r, fh, ensure_ascii=False, indent=1)
                print(f"ohlc {r['date']} <- {name}")
            else: left.append((f, r))
        need = left
        if not need: break
    for f, r in need: print(f"ohlc {r['date']} 未取到，蜡烛线用收盘价近似")

if __name__ == "__main__":
    ingest(); enrich_ohlc(); render()
