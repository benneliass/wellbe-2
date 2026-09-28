#!/usr/bin/env python3
"""Idempotently brand the ZITADEL login pages as WellBe.

Applies the instance label policy (WellBe colours, logo, icon, Figtree font, no
"Powered by ZITADEL" watermark), activates it, and sets the English login texts
to WellBe wording. Re-run after re-initializing ZITADEL.

Environment:
  ZITADEL_URL   base URL, e.g. https://wellbe-auth.tail9c487a.ts.net
  ZITADEL_PAT   instance admin personal access token (the bootstrap PAT)

Run from the backend workspace:
  cd backend && uv run python ../scripts/ops/zitadel_branding.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import httpx

REPO = Path(__file__).resolve().parents[2]
LOGO = REPO / "apps/web/public/wellbe-mark.png"
FONT = REPO / "apps/web/app/fonts/figtree-latin-wght-normal.woff2"

# packages/ui/src/tokens.css: teal-600 keeps white button text above WCAG AA.
LABEL_POLICY = {
    "primaryColor": "#0d6e6d",
    "backgroundColor": "#f8fafc",
    "warnColor": "#dc2626",
    "fontColor": "#0f172a",
    "primaryColorDark": "#0ea5a4",
    "backgroundColorDark": "#0f172a",
    "warnColorDark": "#f87171",
    "fontColorDark": "#f8fafc",
    "hideLoginNameSuffix": True,
    "disableWatermark": True,
}

LOGIN_TEXTS = {
    "loginText": {
        "title": "Sign in to WellBe",
        "description": "Your private health workspace. Only you can see your data.",
        "loginNameLabel": "Email or username",
        "loginNamePlaceholder": "you@example.com",
        "nextButtonText": "Continue",
    },
    "passwordText": {
        "title": "Enter your password",
        "description": "Continue to your WellBe workspace.",
        "passwordLabel": "Password",
        "nextButtonText": "Sign in",
        "resetLinkText": "Forgot password?",
        "backButtonText": "Back",
    },
    "initPasswordText": {
        "title": "Choose your password",
        "description": "Set a new password for your WellBe login.",
    },
    "passwordChangeText": {
        "title": "Choose a new password",
        "description": "Your temporary password has to be replaced before you continue.",
        "nextButtonText": "Save and continue",
    },
    "logoutText": {
        "title": "You're signed out",
        "description": "Your WellBe session has ended.",
    },
}


def main() -> int:
    url = os.environ.get("ZITADEL_URL", "").rstrip("/")
    pat = os.environ.get("ZITADEL_PAT", "")
    if not url or not pat:
        print("ZITADEL_URL and ZITADEL_PAT are required", file=sys.stderr)
        return 2
    client = httpx.Client(base_url=url, headers={"Authorization": f"Bearer {pat}"}, timeout=30)

    def check(resp: httpx.Response, what: str) -> None:
        if resp.status_code == 400 and "has not been changed" in resp.text:
            print(f"# {what}: unchanged")
            return
        if resp.status_code >= 300:
            raise SystemExit(f"{what} failed: {resp.status_code} {resp.text[:300]}")
        print(f"# {what}: ok")

    current = client.get("/admin/v1/policies/label").json().get("policy", {})
    body = {**{k: v for k, v in current.items() if k in LABEL_POLICY}, **LABEL_POLICY}
    check(client.put("/admin/v1/policies/label", json=body), "label policy")

    for kind in ("logo", "icon"):
        with LOGO.open("rb") as f:
            check(
                client.post(
                    f"/assets/v1/instance/policy/label/{kind}",
                    files={"file": (LOGO.name, f, "image/png")},
                ),
                f"upload {kind}",
            )
    with FONT.open("rb") as f:
        check(
            client.post(
                "/assets/v1/instance/policy/label/font",
                files={"file": (FONT.name, f, "font/woff2")},
            ),
            "upload font",
        )

    check(client.post("/admin/v1/policies/label/_activate", json={}), "activate label policy")
    check(client.put("/admin/v1/text/login/en", json=LOGIN_TEXTS), "login texts (en)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
