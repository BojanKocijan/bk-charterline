"""Law 14 secret shapes, shared by the Law 32 hook (`enforce-laws.py`), the
Law 38 registry (`scripts/ai_tools.py`) and the AI inventory
(`scripts/ai_inventory.py`), so all three know the same kinds and let the
same placeholders through (#186).

It imports neither the hook nor `ai_tools.py`, so there is no import
cycle. It lives under `.claude/hooks/` because `dforge-update` shows that
folder's diff before installing an update (Law 28).

Dependency-free stdlib only.
"""
from __future__ import annotations

import base64
import json
import re

# Secret shapes for the Law 14 commit check and Law 39's MCP inputs (#119).
# Every quantifier is bounded, so a large input can't backtrack for long.
# `body` is the part after the prefix: one repeated character there is a
# placeholder (`ghp_xxxx…`).
SECRET_KINDS = [(kind, re.compile(pattern, re.ASCII)) for kind, pattern in (
    ("an AWS access key", r"\b(?:AKIA|ASIA)(?P<body>[0-9A-Z]{16})\b"),
    ("a GitHub token", r"\bgh[pousr]_(?P<body>[A-Za-z0-9]{36,255})\b"),
    ("a GitHub token", r"\bgithub_pat_(?P<body>[A-Za-z0-9_]{60,255})\b"),
    ("a GitLab token", r"\bglpat-(?P<body>[A-Za-z0-9_-]{20,255})"),
    ("a Slack token", r"\bxox[abposr]-(?P<body>[A-Za-z0-9-]{10,255})"),
    ("a Slack token", r"\bxapp-(?P<body>[A-Za-z0-9-]{10,255})"),
    ("a Stripe live key", r"\b[rs]k_live_(?P<body>[A-Za-z0-9]{20,255})"),
    ("an Anthropic key", r"\bsk-ant-(?P<body>[A-Za-z0-9_-]{20,255})"),
    ("an OpenAI key", r"\bsk-(?:proj|svcacct|admin)-(?P<body>[A-Za-z0-9_-]{20,255})"),
    ("an OpenAI key", r"\bsk-(?P<body>[A-Za-z0-9]{20}T3BlbkFJ[A-Za-z0-9]{20})\b"),  # legacy (#186)
    ("a Google API key", r"\bAIza(?P<body>[0-9A-Za-z_-]{35})(?![0-9A-Za-z_-])"),
    ("a Supabase key", r"\bsbp_(?P<body>[a-f0-9]{40})\b"),
    ("a Supabase key", r"\bsb_secret_(?P<body>[A-Za-z0-9_-]{20,255})"),
    ("a Netlify token", r"\bnfp_(?P<body>[A-Za-z0-9]{36,255})"),
    ("an npm token", r"\bnpm_(?P<body>[A-Za-z0-9]{36})\b"),
    ("a Figma token", r"\bfigd_(?P<body>[A-Za-z0-9_-]{30,255})"),
)]
PRIVATE_KEY_RE = re.compile(r"-----BEGIN ((RSA|EC|DSA|OPENSSH|ENCRYPTED|PGP) )?PRIVATE KEY( BLOCK)?-----")
# A key body: a line break (or a literal `\n` in a .env value), then 40+ base64 characters.
PRIVATE_KEY_BODY_RE = re.compile(r"(?:\r?\n|\\n)\s{0,8}[A-Za-z0-9+/=]{40,}")
JWT_RE = re.compile(
    r"(?<![A-Za-z0-9_-])eyJ[A-Za-z0-9_-]{10,4096}\.(?P<payload>eyJ[A-Za-z0-9_-]{10,8192})\.[A-Za-z0-9_-]{10,4096}",
    re.ASCII,
)
# A name containing a credential word, then `=` or `:`, then a value. The match
# starts at the word itself, so `STRIPE_SECRET_KEY` and `client_secret` count.
# A quoted value may hold symbols (`"S3cure!Pass#2024"`); a bare one may not.
ASSIGNMENT_RE = re.compile(
    r"(?i)(?P<word>api[_-]?key|secret|token|passw(?:or)?d|private[_-]?key|access[_-]?key)[\w.-]{0,40}"
    r"[\"']?\s{0,4}[:=]\s{0,4}(?:(?P<quote>[\"'])(?P<quoted>[^\"'\s\\]{16,256})(?P=quote)"
    r"|(?P<bare>[A-Za-z0-9+/_.~-]{16,256}={0,2})(?![A-Za-z0-9+/=_.~-]))",  # `=` only as padding
    re.ASCII,
)
REFERENCE_PREFIXES = ("${{", "${", "$", "process.env", "os.environ", "import.meta.env")
PUBLIC_PREFIXES = ("sk_test_", "rk_test_", "pk_", "sb_publishable_")
# A git SHA, a UUID or an integrity string: shaped like a key, but not one.
NOT_A_KEY_RE = re.compile(
    r"[0-9a-f]{40}|[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
    r"|sha(?:1|256|384|512)-.*",
    re.ASCII,
)
# A design token, file or model name (`color.primary.500`, `tls-secret-prod-2024`).
DOTTED_NAME_RE = re.compile(r"[a-z0-9]{1,15}(?:[./_-][a-z0-9]{1,15}){2,}", re.ASCII)


def _is_placeholder(body: str) -> bool:
    """One repeated character once separators and up to three short leading
    parts go (`xoxb-xxxx-xxxx`, `api03-xxxx`), or no digit and no capital at
    all (`your-api-key-goes-here`): real tokens are random."""
    core = re.sub(r"^(?:[A-Za-z0-9]{1,12}[-_]){1,3}", "", body)
    return len(set(core) - {"-", "_"}) <= 1 or not re.search(r"[0-9A-Z]", body)


def _jwt_role(payload: str) -> object:
    try:
        data = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
    except Exception:
        return None
    return data.get("role") if isinstance(data, dict) else None


def _assignment_is_secret(word: str, value: str) -> bool:
    if (value.startswith(REFERENCE_PREFIXES) or value.startswith(PUBLIC_PREFIXES)
            or "EXAMPLE" in value or _is_placeholder(value)
            or NOT_A_KEY_RE.fullmatch(value) or JWT_RE.match(value)):
        return False  # a JWT is judged by its own rule
    if not word.lower().startswith("passw") and DOTTED_NAME_RE.fullmatch(value):
        return False  # never for passwords: a passphrase looks just like this
    mixed = re.search(r"[A-Za-z]", value) and re.search(r"[0-9]", value)
    return bool(mixed) or len(value) >= 32


def find_secret(text: str) -> tuple[str, int] | None:
    """The kind and offset of the first secret in `text`, or None.
    Placeholders, references, test and public keys, key headers with no
    key body and Supabase anon JWTs pass (#119). Where a token sits in an
    assignment, the token's own kind is reported."""
    found: list[tuple[int, int, str]] = []
    for kind, pattern in SECRET_KINDS:
        for match in pattern.finditer(text):
            if "EXAMPLE" not in match.group(0) and not _is_placeholder(match.group("body")):
                found.append((match.start(), 0, kind))
                break
    for match in PRIVATE_KEY_RE.finditer(text):
        if PRIVATE_KEY_BODY_RE.search(text, match.end(), match.end() + 300):
            found.append((match.start(), 0, "a private key"))
            break
    for match in JWT_RE.finditer(text):
        if _jwt_role(match.group("payload")) != "anon":
            found.append((match.start(), 0, "a JWT"))
            break
    for match in ASSIGNMENT_RE.finditer(text):
        group = "quoted" if match.group("quoted") is not None else "bare"
        if _assignment_is_secret(match.group("word"), match.group(group)):
            found.append((match.start(group), 1, "a credential assignment"))
            break
    if not found:
        return None
    offset, _, kind = min(found)
    return kind, offset
