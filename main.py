from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
import httpx, re
from bs4 import BeautifulSoup
from urllib.parse import urlparse

app = FastAPI(title="Typermonitor API", version="0.2.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

PROFILE_RE = re.compile(r"^/typer/(\d+)/?$", re.I)

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/api/profile")
async def get_profile(url: str):
    parsed = urlparse(url)
    match = PROFILE_RE.match(parsed.path)
    if parsed.scheme not in ("http", "https") or parsed.hostname not in ("zawodtyper.pl", "www.zawodtyper.pl") or not match:
        raise HTTPException(400, "Podaj prawidłowy adres profilu zawodtyper.pl/typer/ID/")
    profile_id = match.group(1)
    headers = {"User-Agent": "Mozilla/5.0 (compatible; Typermonitor/0.2; +https://github.com/szymoooo/Typermonitor)"}
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=20, headers=headers) as client:
            response = await client.get(url)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(502, f"Nie udało się pobrać profilu: {exc.__class__.__name__}")
    soup = BeautifulSoup(response.text, "html.parser")
    name_node = soup.select_one("span.font-medium.text-2xl")
    name = name_node.get_text(" ", strip=True) if name_node else ""
    if not name:
        # Fallback: title commonly contains "Typer [display name]"
        title = soup.title.get_text(" ", strip=True) if soup.title else ""
        name = re.sub(r"^Typer\s+", "", title, flags=re.I).split("|")[0].strip()
    if not name or name.lower() in (profile_id, f"typer {profile_id}".lower()):
        raise HTTPException(422, "Strona została pobrana, ale nie znaleziono nazwy profilu. Struktura HTML może być inna.")
    avatar_node = soup.select_one("img[alt], img")
    avatar = avatar_node.get("src") if avatar_node else None
    if avatar and avatar.startswith("//"):
        avatar = "https:" + avatar
    return {"id": profile_id, "name": name, "avatar": avatar, "profile_url": str(response.url)}

