import json, httpx
H={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36","Accept-Language":"pl-PL,pl;q=0.9","Origin":"https://zawodtyper.pl","Referer":"https://zawodtyper.pl/typer/6560/"}
out={}
for uid in (6560,):
    r=httpx.post("https://zawodtyper.pl/wp-content/NP_ajax.php",json={"endpoint":"api_get_user_bets","user_id":uid},headers=H,timeout=30)
    print(uid,r.status_code,len(r.text),r.headers.get("content-type"))
    try: out[uid]=r.json()
    except Exception: out[uid]=r.text[:3000]
json.dump(out,open("debug_bundle.js","w",encoding="utf-8"),ensure_ascii=False,indent=1)
