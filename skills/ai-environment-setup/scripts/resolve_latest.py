#!/usr/bin/env python3
"""Read current official release metadata. Never installs or authenticates."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


GITHUB_PRODUCTS = {
    "obsidian": "obsidianmd/obsidian-releases",
    "obsidian-git": "Vinzent03/obsidian-git",
}
NPM_PRODUCTS = {
    "dws": "dingtalk-workspace-cli",
    "feishu": "@larksuite/cli",
    "claude": "@anthropic-ai/claude-code",
}
PAGE_PRODUCTS = {
    "egolite": "https://www.egolite.ai/download",
    "chatgpt": "https://learn.chatgpt.com/docs/app",
    "cindy": "https://cindy.app/download",
    "git": "https://git-scm.com/install/",
}
PRODUCTS = tuple(GITHUB_PRODUCTS) + tuple(NPM_PRODUCTS) + ("node",) + tuple(PAGE_PRODUCTS)
MAX_RESPONSE_BYTES = 4 * 1024 * 1024
STABLE_VERSION = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)(?:\+[0-9A-Za-z.-]+)?$")


def fetch_json(url: str, timeout: float = 15):
    """Only the static official HTTPS endpoints selected below are requested."""
    request = Request(
        url,
        headers={"Accept": "application/json", "User-Agent": "ai-environment-setup-skill"},
    )
    with urlopen(request, timeout=timeout) as response:
        if response.geturl().split(":", 1)[0].lower() != "https":
            raise ValueError("official metadata redirected away from HTTPS")
        body = response.read(MAX_RESPONSE_BYTES + 1)
        if len(body) > MAX_RESPONSE_BYTES:
            raise ValueError("release metadata exceeds the response-size limit")
    return json.loads(body.decode("utf-8"))


def version_tuple(value: str):
    match = STABLE_VERSION.fullmatch(value)
    if not match:
        raise ValueError("expected a stable numeric release version")
    return tuple(int(part) for part in match.groups())


def resolve_product(product: str, fetch=fetch_json, timeout: float = 15) -> dict:
    """Return metadata or a page-required status; lookup failures are never success."""
    if product not in PRODUCTS:
        raise ValueError("unknown product")
    result = {
        "product": product,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "status": "error",
        "target_version": None,
        "installation_verified": False,
    }
    if product in PAGE_PRODUCTS:
        result.update(
            status="needs_official_page",
            source=PAGE_PRODUCTS[product],
            note="Check the current official page, target platform, and in-app updater; no version is guessed.",
        )
        return result

    if product in GITHUB_PRODUCTS:
        result["source"] = f"https://api.github.com/repos/{GITHUB_PRODUCTS[product]}/releases/latest"
    elif product in NPM_PRODUCTS:
        package = quote(NPM_PRODUCTS[product], safe="@")
        result["source"] = f"https://registry.npmjs.org/{package}/latest"
    else:
        result["source"] = "https://nodejs.org/dist/index.json"

    try:
        payload = fetch(result["source"], timeout=timeout)
        if product in GITHUB_PRODUCTS:
            if not isinstance(payload, dict):
                raise ValueError("expected a GitHub release object")
            if payload.get("draft") is not False or payload.get("prerelease") is not False:
                raise ValueError("the response does not establish a public, non-preview release")
            version = str(payload.get("tag_name", "")).strip()
            version_tuple(version)
            assets = payload.get("assets", [])
            if not isinstance(assets, list):
                raise ValueError("expected a release asset list")
            result.update(
                target_version=version,
                channel="github-latest-public-release",
                release_page=payload.get("html_url"),
                published_at=payload.get("published_at"),
                assets=[
                    {key: asset.get(key) for key in ("name", "browser_download_url", "size", "digest")}
                    for asset in assets
                    if isinstance(asset, dict)
                ],
                note="Confirm the vendor download page, system requirements, and native architecture before selecting an asset.",
            )
        elif product in NPM_PRODUCTS:
            if not isinstance(payload, dict) or payload.get("name") != NPM_PRODUCTS[product]:
                raise ValueError("the npm response does not match the official package")
            version = str(payload.get("version", ""))
            version_tuple(version)
            result.update(
                target_version=version,
                channel="npm-latest",
                package=NPM_PRODUCTS[product],
                engines=payload.get("engines", {}),
                note="This is the npm distribution version; verify the actual installed CLI and any separately downloaded binary.",
            )
        else:
            if not isinstance(payload, list):
                raise ValueError("expected the official Node.js release index")
            candidates = []
            for release in payload:
                if not isinstance(release, dict) or not release.get("lts"):
                    continue
                version = str(release.get("version", ""))
                try:
                    numeric = version_tuple(version)
                except ValueError:
                    continue
                candidates.append((numeric, release))
            if not candidates:
                raise ValueError("the official index contains no stable LTS release")
            release = max(candidates, key=lambda item: item[0])[1]
            result.update(
                target_version=release["version"],
                channel="latest-lts",
                lts=release["lts"],
                files=release.get("files", []),
                note="Confirm this LTS supports the target system and the selected CLI; Current is not selected.",
            )
        result["status"] = "release_metadata"
    except (HTTPError, URLError, OSError, ValueError, TypeError, KeyError) as error:
        result.update(status="error", target_version=None, error=str(error))
    return result


def exit_code(results: list) -> int:
    if any(item["status"] == "error" for item in results):
        return 1
    if any(item["status"] == "needs_official_page" for item in results):
        return 2
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--products", choices=PRODUCTS, nargs="+", required=True)
    parser.add_argument("--timeout", type=float, default=15, help="Seconds per metadata request (1-60).")
    args = parser.parse_args(argv)
    if not 1 <= args.timeout <= 60:
        parser.error("--timeout must be between 1 and 60 seconds")
    results = [resolve_product(product, timeout=args.timeout) for product in dict.fromkeys(args.products)]
    report = {
        "purpose": "official-release-metadata-only",
        "results": results,
        "environment_setup_verified": False,
    }
    print(json.dumps(report, ensure_ascii=True, indent=2))
    return exit_code(results)


if __name__ == "__main__":
    sys.exit(main())
