import re, httpx
H={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36","Accept-Language":"pl-PL,pl;q=0.9"}
r=httpx.get("https://zawodtyper.pl/wp-content/themes/zawodtyper/build/assets/main-BhI9KVzb.js",headers=H,timeout=60)
print("BUNDLE",r.status_code,len(r.text))
open("debug_bundle.js","w",encoding="utf-8").write(r.text)
# lazy chunks referenced
print("chunks:",sorted(set(re.findall(r'[\w\-]+-[\w]{8}\.js',r.text)))[:40])
