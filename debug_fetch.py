import re, sys, httpx
from bs4 import BeautifulSoup
H={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36","Accept-Language":"pl-PL,pl;q=0.9"}
r=httpx.get("https://zawodtyper.pl/typer/6560/",headers=H,follow_redirects=True,timeout=30)
h=r.text
print("STATUS",r.status_code,"LEN",len(h),"URL",r.url)
print("comment- count:",h.count("comment-"),"| '#comment-':",h.count("#comment-"))
s=BeautifulSoup(h,"html.parser")
print("scripts:",len(s.find_all("script")),"| __NEXT_DATA__" if "__NEXT_DATA__" in h else "| no next_data")
for kw in ("vs ","Kurs","kurs","wygra","Dziś"):
    print(kw,"->",h.count(kw))
open("debug_profile.html","w",encoding="utf-8").write(h)
