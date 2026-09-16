#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
upload_youtube.py – Laddar upp färdiga MP4:er till din YouTube-kanal.

Förberedelse (engångsgrej, se README.md för bildguide):
  1. Google Cloud Console -> skapa projekt -> aktivera "YouTube Data API v3".
  2. Skapa OAuth-klient (Desktop app) och ladda ner JSON:en.
  3. Döp den till  client_secrets.json  och lägg i den här mappen.

Första uppladdningen öppnar webbläsaren så du loggar in med kanalens
Google-konto; sedan sparas token.json och allt går automatiskt.

Exempel:
    python upload_youtube.py out/ep007-den-borttappade-stjarnan.mp4
    python upload_youtube.py out/*.mp4 --privacy unlisted
"""
import argparse
import json
import sys
from pathlib import Path

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
HERE = Path(__file__).resolve().parent


def get_service():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    secrets = HERE / "client_secrets.json"
    if not secrets.exists():
        sys.exit("Saknar client_secrets.json! Ladda ner den från Google Cloud Console\n"
                 "(APIs & Services -> Credentials -> OAuth client). Se README.md steg 4.")

    creds = None
    token = HERE / "token.json"
    if token.exists():
        creds = Credentials.from_authorized_user_file(str(token), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(secrets), SCOPES)
            creds = flow.run_local_server(port=0)
        token.write_text(creds.to_json())
    return build("youtube", "v3", credentials=creds)


def upload(yt, path, privacy):
    from googleapiclient.http import MediaFileUpload

    path = Path(path)
    meta_path = path.with_suffix(".json")
    if meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    else:
        meta = {"title": path.stem, "description": "", "tags": []}

    body = {
        "snippet": {
            "title": meta["title"],
            "description": meta.get("description", ""),
            "tags": meta.get("tags", []),
            "categoryId": meta.get("categoryId", "1"),
        },
        "status": {
            "privacyStatus": privacy,
            # Den här kanalen är 16+ underhållning – INTE barninnehåll.
            "selfDeclaredMadeForKids": bool(meta.get("madeForKids", False)),
        },
    }
    media = MediaFileUpload(str(path), chunksize=8 * 1024 * 1024,
                            resumable=True, mimetype="video/mp4")
    req = yt.videos().insert(part="snippet,status", body=body, media_body=media)
    resp = None
    while resp is None:
        status, resp = req.next_chunk()
        if status:
            print(f"\r  ⬆️  {path.name}: {int(status.progress() * 100)} %", end="", flush=True)
    print()
    return resp["id"]


def main():
    ap = argparse.ArgumentParser(description="Ladda upp videor till YouTube.")
    ap.add_argument("files", nargs="+", help="MP4-filer (meta läses från .json med samma namn)")
    ap.add_argument("--privacy", choices=["private", "unlisted", "public"],
                    default="unlisted",
                    help="Standard: unlisted (dold länk). Börja aldrig med public direkt.")
    args = ap.parse_args()

    yt = get_service()
    for f in args.files:
        vid = upload(yt, f, args.privacy)
        print(f"✅ Uppladdad: https://youtu.be/{vid}")


if __name__ == "__main__":
    main()
