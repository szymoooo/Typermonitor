import re, httpx
H={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36","Accept-Language":"pl-PL,pl;q=0.9"}
B="https://zawodtyper.pl/wp-content/themes/zawodtyper/build/assets/"
out=""
for n in ("UserProfile-CIicqc1r.js","LastBets-DY5YGSBp.js","DailyBetsProfile-Bqd8qiIn.js"):
    r=httpx.get(B+n,headers=H,timeout=60); print(n,r.status_code,len(r.text))
    out+=f"\n/* ===== {n} ===== */\n"+r.text
open("debug_bundle.js","w",encoding="utf-8").write(out)
