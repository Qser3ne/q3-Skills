#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import sys
import time
from typing import Any

try:
    import requests
except ImportError as exc:  # pragma: no cover
    raise SystemExit("missing dependency: requests") from exc

try:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.x25519 import (
        X25519PrivateKey,
        X25519PublicKey,
    )
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
except ImportError:
    serialization = None
    X25519PrivateKey = None
    X25519PublicKey = None
    AESGCM = None


def env_or(value: str | None, key: str, default: str | None = None) -> str | None:
    return value if value not in (None, "") else os.getenv(key, default)


def dump(payload: Any) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def fail(message: str, *, extra: dict[str, Any] | None = None, code: int = 2) -> None:
    payload: dict[str, Any] = {"ok": False, "error": message}
    if extra:
        payload.update(extra)
    dump(payload)
    raise SystemExit(code)


class GZCTFClient:
    def __init__(
        self,
        *,
        base_url: str,
        token: str,
        cookie_name: str = "GZCTF_Token",
        proxy: str | None = None,
        timeout: float = 20.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.cookies.set(cookie_name, token)
        self.session.headers.update({"Accept": "application/json"})
        if proxy:
            self.session.proxies.update({"http": proxy, "https": proxy})
        self._config: dict[str, Any] | None = None

    def request(self, method: str, path: str, **kwargs: Any) -> requests.Response:
        return self.session.request(
            method=method,
            url=f"{self.base_url}{path}",
            timeout=self.timeout,
            **kwargs,
        )

    @staticmethod
    def parse_response(resp: requests.Response) -> Any:
        content_type = resp.headers.get("Content-Type", "")
        if "json" in content_type:
            try:
                return resp.json()
            except ValueError:
                pass
        text = resp.text
        return text if text else None

    def config(self) -> dict[str, Any]:
        if self._config is None:
            resp = self.request("GET", "/api/config")
            resp.raise_for_status()
            data = self.parse_response(resp)
            if not isinstance(data, dict):
                fail("unexpected /api/config response", extra={"data": data})
            self._config = data
        return self._config


def encrypt_api_data(plain_text: str, public_key_b64: str | None) -> str:
    if not public_key_b64:
        return plain_text
    if not plain_text:
        fail("flag cannot be empty")
    if not all([serialization, X25519PrivateKey, X25519PublicKey, AESGCM]):
        fail("missing dependency: cryptography")

    recipient_public = X25519PublicKey.from_public_bytes(base64.b64decode(public_key_b64))
    ephemeral_private = X25519PrivateKey.generate()
    ephemeral_public = ephemeral_private.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    shared_secret = ephemeral_private.exchange(recipient_public)
    aes_key = hashlib.sha256(shared_secret).digest()
    nonce = os.urandom(12)
    cipher_text = AESGCM(aes_key).encrypt(nonce, plain_text.encode("utf-8"), None)
    return base64.b64encode(ephemeral_public + nonce + cipher_text).decode("ascii")


def resolve_game_id(args: argparse.Namespace) -> int:
    raw = env_or(getattr(args, "game_id", None), "GZCTF_GAME_ID")
    if not raw:
        fail("missing game id; pass --game-id or set GZCTF_GAME_ID")
    try:
        return int(raw)
    except ValueError as exc:
        fail(f"invalid game id: {raw}")  # pragma: no cover
        raise exc


def build_client(args: argparse.Namespace) -> GZCTFClient:
    base_url = env_or(args.base_url, "GZCTF_BASE_URL", "https://hackhub.get-shell.com")
    token = env_or(args.token, "GZCTF_TOKEN")
    proxy = env_or(args.proxy, "GZCTF_PROXY")
    if not token:
        fail("missing token; pass --token or set GZCTF_TOKEN")
    return GZCTFClient(
        base_url=base_url,
        token=token,
        cookie_name=args.cookie_name,
        proxy=proxy,
        timeout=args.timeout,
    )


def emit_http_result(resp: requests.Response, *, extra: dict[str, Any] | None = None) -> None:
    payload: dict[str, Any] = {
        "ok": resp.ok,
        "status_code": resp.status_code,
        "data": GZCTFClient.parse_response(resp),
    }
    if extra:
        payload.update(extra)
    dump(payload)


def cmd_profile(args: argparse.Namespace) -> None:
    client = build_client(args)
    resp = client.request("GET", "/api/account/profile")
    emit_http_result(resp)


def cmd_config(args: argparse.Namespace) -> None:
    client = build_client(args)
    resp = client.request("GET", "/api/config")
    emit_http_result(resp)


def cmd_list(args: argparse.Namespace) -> None:
    client = build_client(args)
    game_id = resolve_game_id(args)
    resp = client.request("GET", f"/api/game/{game_id}/details")
    data = client.parse_response(resp)
    if not resp.ok:
        dump({"ok": False, "status_code": resp.status_code, "data": data})
        return
    challenges = data.get("challenges", {}) if isinstance(data, dict) else {}
    category = args.category
    if category:
        challenges = {category: challenges.get(category, [])}
    flat: list[dict[str, Any]] = []
    for cat_name, items in challenges.items():
        for item in items or []:
            row = dict(item)
            row["_category_group"] = cat_name
            flat.append(row)
    dump(
        {
            "ok": True,
            "status_code": resp.status_code,
            "game_id": game_id,
            "challenge_count": len(flat),
            "challenges": flat,
        }
    )


def cmd_challenge(args: argparse.Namespace) -> None:
    client = build_client(args)
    game_id = resolve_game_id(args)
    resp = client.request("GET", f"/api/game/{game_id}/challenges/{args.challenge_id}")
    emit_http_result(resp, extra={"game_id": game_id, "challenge_id": args.challenge_id})


def cmd_create(args: argparse.Namespace) -> None:
    client = build_client(args)
    game_id = resolve_game_id(args)
    resp = client.request("POST", f"/api/game/{game_id}/container/{args.challenge_id}")
    data = client.parse_response(resp)
    if resp.ok and isinstance(data, dict) and data.get("entry"):
        data["entryUrl"] = f"http://{data['entry']}"
    dump(
        {
            "ok": resp.ok,
            "status_code": resp.status_code,
            "game_id": game_id,
            "challenge_id": args.challenge_id,
            "data": data,
        }
    )


def cmd_destroy(args: argparse.Namespace) -> None:
    client = build_client(args)
    game_id = resolve_game_id(args)
    resp = client.request("DELETE", f"/api/game/{game_id}/container/{args.challenge_id}")
    emit_http_result(resp, extra={"game_id": game_id, "challenge_id": args.challenge_id})


def cmd_extend(args: argparse.Namespace) -> None:
    client = build_client(args)
    game_id = resolve_game_id(args)
    resp = client.request("POST", f"/api/game/{game_id}/container/{args.challenge_id}/extend")
    emit_http_result(resp, extra={"game_id": game_id, "challenge_id": args.challenge_id})


def fetch_status(
    client: GZCTFClient,
    *,
    game_id: int,
    challenge_id: int,
    submission_id: int,
) -> requests.Response:
    return client.request(
        "GET",
        f"/api/game/{game_id}/challenges/{challenge_id}/status/{submission_id}",
    )


def cmd_status(args: argparse.Namespace) -> None:
    client = build_client(args)
    game_id = resolve_game_id(args)
    resp = fetch_status(
        client,
        game_id=game_id,
        challenge_id=args.challenge_id,
        submission_id=args.submission_id,
    )
    emit_http_result(
        resp,
        extra={
            "game_id": game_id,
            "challenge_id": args.challenge_id,
            "submission_id": args.submission_id,
        },
    )


def cmd_submit(args: argparse.Namespace) -> None:
    client = build_client(args)
    game_id = resolve_game_id(args)
    public_key = client.config().get("apiPublicKey")
    encrypted_flag = encrypt_api_data(args.flag, public_key)
    resp = client.request(
        "POST",
        f"/api/game/{game_id}/challenges/{args.challenge_id}",
        json={"flag": encrypted_flag},
    )
    data = client.parse_response(resp)
    if not resp.ok:
        dump(
            {
                "ok": False,
                "status_code": resp.status_code,
                "game_id": game_id,
                "challenge_id": args.challenge_id,
                "data": data,
            }
        )
        return

    submission_id = int(data)
    result: dict[str, Any] = {
        "ok": True,
        "status_code": resp.status_code,
        "game_id": game_id,
        "challenge_id": args.challenge_id,
        "submission_id": submission_id,
    }

    if not args.wait:
        dump(result)
        return

    deadline = time.time() + args.poll_timeout
    history: list[dict[str, Any]] = []
    final_data: Any = "FlagSubmitted"
    final_status = 200
    while time.time() < deadline:
        poll = fetch_status(
            client,
            game_id=game_id,
            challenge_id=args.challenge_id,
            submission_id=submission_id,
        )
        final_status = poll.status_code
        final_data = client.parse_response(poll)
        history.append({"status_code": poll.status_code, "data": final_data})
        if not poll.ok or final_data != "FlagSubmitted":
            break
        time.sleep(args.poll_interval)

    result.update(
        {
            "final_status_code": final_status,
            "final_result": final_data,
            "history": history,
        }
    )
    dump(result)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Operate GZCTF/HackHub challenge APIs")
    parser.add_argument("--base-url", help="Base site URL; default: $GZCTF_BASE_URL or https://hackhub.get-shell.com")
    parser.add_argument("--token", help="Cookie value; default: $GZCTF_TOKEN")
    parser.add_argument("--cookie-name", default="GZCTF_Token", help="Cookie name; default: GZCTF_Token")
    parser.add_argument("--proxy", help="HTTP/HTTPS proxy URL; default: $GZCTF_PROXY")
    parser.add_argument("--timeout", type=float, default=20.0, help="HTTP timeout in seconds")

    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("profile", help="Get account profile")
    p.set_defaults(func=cmd_profile)

    p = sub.add_parser("config", help="Get client config")
    p.set_defaults(func=cmd_config)

    p = sub.add_parser("list", help="List game challenges")
    p.add_argument("--game-id")
    p.add_argument("--category", help="Filter category group, e.g. Web")
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("challenge", help="Get one challenge detail")
    p.add_argument("--game-id")
    p.add_argument("--challenge-id", type=int, required=True)
    p.set_defaults(func=cmd_challenge)

    p = sub.add_parser("create", help="Create/start challenge container")
    p.add_argument("--game-id")
    p.add_argument("--challenge-id", type=int, required=True)
    p.set_defaults(func=cmd_create)

    p = sub.add_parser("destroy", help="Destroy challenge container")
    p.add_argument("--game-id")
    p.add_argument("--challenge-id", type=int, required=True)
    p.set_defaults(func=cmd_destroy)

    p = sub.add_parser("extend", help="Extend challenge container lifetime")
    p.add_argument("--game-id")
    p.add_argument("--challenge-id", type=int, required=True)
    p.set_defaults(func=cmd_extend)

    p = sub.add_parser("status", help="Poll one submission status")
    p.add_argument("--game-id")
    p.add_argument("--challenge-id", type=int, required=True)
    p.add_argument("--submission-id", type=int, required=True)
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("submit", help="Submit one flag")
    p.add_argument("--game-id")
    p.add_argument("--challenge-id", type=int, required=True)
    p.add_argument("--flag", required=True)
    p.add_argument("--wait", action="store_true", help="Poll until final result or timeout")
    p.add_argument("--poll-interval", type=float, default=0.5, help="Status polling interval in seconds")
    p.add_argument("--poll-timeout", type=float, default=20.0, help="Maximum polling time in seconds")
    p.set_defaults(func=cmd_submit)

    return parser


def main() -> int:
    args = build_parser().parse_args()
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
