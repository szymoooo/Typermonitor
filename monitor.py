import json, os, re, sys, hashlib
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse
import httpx
from bs4 import BeautifulSoup

BASE = os.path.dirname(os.path.abspath(__file__))
PROFILES_FILE = os.path.join(BASE, "data", "profiles.json")
STATE_FILE = os.path.join(BASE, "data", "monitor_state.json")
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

def read_json(path, default):
    if not os.path.exists(path): return default
    with open(path, encoding="utf-8") as f: return json.load(f)

def write_json(path, value):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp=path+".tmp"
    with open(tmp,"w",encoding="utf-8") as f: json.dump(value,f,ensure_ascii=False,indent=2)
    os.replace(tmp,path)

def normalize(url):
    u=urlparse(url)
    if u.scheme not in ("http","https") or u.netloc.lower() not in ("zawodtyper.pl","www.zawodtyper.pl"):
        raise ValueError("Nieprawidłowa domena profilu: "+url)
    m=re.fullmatch(r"/typer/(\d+)/?",u.path)
    if not m: raise ValueError("Adres musi mieć postać https://zawodtyper.pl/typer/ID/")
    return f"https://zawodtyper.pl/typer/{m.group(1)}/",m.group(1)

def parse_profile(html, profile_url):
    soup=BeautifulSoup(html,"html.parser")
    name=""
    for selector in ("span.font-medium.text-2xl","h1","title"):
        el=soup.select_one(selector)
        if el:
            name=el.get_text(" ",strip=True)
            if name: break
    tips=[]
    for a in soup.select('a[href*="#comment-"]'):
        href=a.get("href","")
        m=re.search(r"#comment-(\d+)",href)
        if not m: continue
        ext=m.group(1)
        discipline=""
        img=a.select_one("img[alt]")
        if img: discipline=img.get("alt","").strip()
        event=""
        for sp in a.select("span"):
            value=sp.get_text(" ",strip=True)
            if " vs " in value.lower():
                event=value.strip()
                break
        odds_el=a.select_one("span[style*='color'], .font-bold.text-sm, .font-bold")
        odds=odds_el.get_text(" ",strip=True) if odds_el else ""
        lines=[x.strip() for x in a.stripped_strings if x.strip()]
        excluded={"Dziś","Jutro","Wczoraj"}
        candidates=[x for x in lines if x not in excluded and not re.fullmatch(r"\d{1,2}:\d{2}",x) and x!=event and x!=odds]
        pick=candidates[-1] if candidates else ""
        tips.append({
            "id":ext,"event":event,"pick":pick,"odds":odds,
            "discipline":discipline,"url":urljoin(profile_url,href)
        })
    # de-duplicate within page, preserve order
    unique={}
    for t in tips: unique[t["id"]]=t
    return name,list(unique.values())

def telegram(text):
    if not TOKEN or not CHAT_ID:
        print("Telegram not configured; alert skipped.")
        return
    try:
        r=httpx.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
          json={"chat_id":CHAT_ID,"text":text,"disable_web_page_preview":True},timeout=20)
        r.raise_for_status()
    except Exception as e:
        print("Telegram send failed:",repr(e))
        raise

def main():
    profiles=read_json(PROFILES_FILE,[])
    state=read_json(STATE_FILE,{"profiles":{},"last_run":None})
    state.setdefault("profiles",{})
    errors=0
    with httpx.Client(timeout=30,follow_redirects=True,headers={
      "User-Agent":"Mozilla/5.0 (compatible; Typermonitor/1.0)",
      "Accept-Language":"pl-PL,pl;q=0.9,en;q=0.8"}) as client:
        for item in profiles:
            if not item.get("enabled",True): continue
            try:
                url,tid=normalize(item["url"])
                response=client.get(url); response.raise_for_status()
                name,tips=parse_profile(response.text,url)
                key=tid
                previous=state["profiles"].get(key)
                current={t["id"] for t in tips}
                if previous is None:
                    # First scan is baseline: do not send historical tips as new alerts.
                    state["profiles"][key]={"url":url,"name":name,"seen":sorted(current)}
                    print(f"BASELINE {name or tid}: {len(current)} existing entries")
                    continue
                old=set(previous.get("seen",[]))
                new=[t for t in tips if t["id"] not in old]
                for t in reversed(new):
                    msg=(f"🆕 NOWY TYP — {name or previous.get('name') or tid}\n"
                         f"{t['event'] or 'Nowy wpis'}\n{t['pick']}\n"
                         f"Kurs: {t['odds'] or 'brak'}\n"
                         f"{t['discipline']}\n{t['url']}")
                    telegram(msg)
                    print("NEW TIP",tid,t["id"],t["event"],t["odds"])
                state["profiles"][key]={"url":url,"name":name or previous.get("name",""),
                                        "seen":sorted(old|current)}
                print(f"OK {name or tid}: {len(tips)} entries, {len(new)} new")
            except Exception as e:
                errors+=1
                print(f"ERROR {item.get('url')}: {e}")
    state["last_run"]=datetime.now(timezone.utc).isoformat()
    write_json(STATE_FILE,state)
    print(f"Finished. Errors: {errors}")
    # Keep a failed scrape visible in Actions logs; successful profiles still persist.
    if errors and errors==sum(1 for p in profiles if p.get("enabled",True)):
        sys.exit("All enabled profiles failed. Check HTML access / parser.")

if __name__=="__main__": main()
