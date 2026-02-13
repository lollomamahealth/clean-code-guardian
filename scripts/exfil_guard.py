#!/usr/bin/env python3
"""
Exfiltration guard hook for Clean Code Guardian.

Blocks outbound tool calls that may leak secrets via WebSearch queries,
WebFetch URLs, or Bash commands (curl, dig, nc, etc.).

Input: JSON on stdin with tool_name, tool_input
Output: JSON with hookSpecificOutput containing permissionDecision, or {} to allow.

Fail-open: any parse error or exception outputs {} so legitimate work is never blocked.
"""

import json
import math
import os
import re
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse


def get_plugin_dir() -> Path:
    """Get the plugin directory path via env var or relative path."""
    env_root = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if env_root:
        return Path(env_root)
    return Path(__file__).parent.parent


def load_config() -> dict:
    """Load exfiltration detection config from reference/exfil-patterns.json."""
    config_file = get_plugin_dir() / "reference" / "exfil-patterns.json"
    if not config_file.exists():
        return {}
    try:
        return json.loads(config_file.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def deny(reason: str) -> dict:
    """Build a PreToolUse deny response."""
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }


def shannon_entropy(s: str) -> float:
    """Compute Shannon entropy of a string in bits per character."""
    if not s:
        return 0.0
    freq: dict[str, int] = {}
    for ch in s:
        freq[ch] = freq.get(ch, 0) + 1
    length = len(s)
    return -sum((c / length) * math.log2(c / length) for c in freq.values())


def scan_secret_patterns(text: str, patterns: list[dict]) -> dict | None:
    """Scan text against secret patterns. Returns first match or None."""
    for pat in patterns:
        try:
            if re.search(pat["pattern"], text):
                return pat
        except re.error:
            continue
    return None


def check_entropy(text: str, threshold: float, min_length: int) -> str | None:
    """Check tokens in text for high entropy. Returns the flagged token or None."""
    tokens = re.split(r"[\s&?=,;|]+", text)
    for token in tokens:
        if len(token) >= min_length and shannon_entropy(token) >= threshold:
            return token
    return None


def check_suspicious_domain(hostname: str, domains: list[str]) -> str | None:
    """Check if hostname matches a suspicious domain. Returns the domain or None."""
    hostname_lower = hostname.lower()
    for domain in domains:
        if hostname_lower == domain or hostname_lower.endswith("." + domain):
            return domain
    return None


def check_websearch(tool_input: dict, config: dict) -> dict | None:
    """Check WebSearch tool_input for exfiltration attempts."""
    query = tool_input.get("query", "")
    if not query:
        return None

    secret_patterns = config.get("secret_patterns", [])
    match = scan_secret_patterns(query, secret_patterns)
    if match:
        return deny(
            f"Exfiltration guard: WebSearch query contains a suspected secret "
            f"({match['description']}). Blocked to prevent data leakage."
        )

    threshold = config.get("entropy_threshold", 4.0)
    min_length = config.get("entropy_min_length", 20)
    flagged = check_entropy(query, threshold, min_length)
    if flagged:
        return deny(
            f"Exfiltration guard: WebSearch query contains a high-entropy token "
            f"({flagged[:40]}...) that may encode secrets. Blocked to prevent data leakage."
        )

    return None


def check_webfetch(tool_input: dict, config: dict) -> dict | None:
    """Check WebFetch tool_input for exfiltration attempts."""
    url = tool_input.get("url", "")
    if not url:
        return None

    try:
        parsed = urlparse(url)
    except Exception:
        return None

    suspicious_domains = config.get("suspicious_domains", [])
    domain_match = check_suspicious_domain(parsed.hostname or "", suspicious_domains)
    if domain_match:
        return deny(
            f"Exfiltration guard: WebFetch URL targets suspicious domain "
            f"({domain_match}). Blocked to prevent data leakage."
        )

    secret_patterns = config.get("secret_patterns", [])
    match = scan_secret_patterns(url, secret_patterns)
    if match:
        return deny(
            f"Exfiltration guard: WebFetch URL contains a suspected secret "
            f"({match['description']}). Blocked to prevent data leakage."
        )

    threshold = config.get("entropy_threshold", 4.0)
    min_length = config.get("entropy_min_length", 20)
    query_params = parse_qs(parsed.query)
    for param_name, values in query_params.items():
        for val in values:
            flagged = check_entropy(val, threshold, min_length)
            if flagged:
                return deny(
                    f"Exfiltration guard: WebFetch URL query param '{param_name}' "
                    f"contains a high-entropy value that may encode secrets. "
                    f"Blocked to prevent data leakage."
                )

    return None


def check_bash(tool_input: dict, config: dict) -> dict | None:
    """Check Bash tool_input for exfiltration attempts."""
    command = tool_input.get("command", "")
    if not command:
        return None

    secret_patterns = config.get("secret_patterns", [])
    match = scan_secret_patterns(command, secret_patterns)
    if match:
        return deny(
            f"Exfiltration guard: Bash command contains a suspected secret "
            f"({match['description']}). Blocked to prevent data leakage."
        )

    bash_exfil = config.get("bash_exfil_commands", [])
    for exfil_cmd in bash_exfil:
        try:
            if re.search(exfil_cmd["pattern"], command):
                suspicious_domains = config.get("suspicious_domains", [])
                urls = re.findall(r"https?://([^/\s'\"]+)", command)
                hostnames = re.findall(r"(?:\s|^)([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})", command)
                all_hosts = urls + hostnames
                for host in all_hosts:
                    domain_match = check_suspicious_domain(host, suspicious_domains)
                    if domain_match:
                        return deny(
                            f"Exfiltration guard: Bash command uses {exfil_cmd['description']} "
                            f"targeting suspicious domain ({domain_match}). "
                            f"Blocked to prevent data leakage."
                        )

                threshold = config.get("entropy_threshold", 4.0)
                min_length = config.get("entropy_min_length", 20)
                flagged = check_entropy(command, threshold, min_length)
                if flagged:
                    return deny(
                        f"Exfiltration guard: Bash command uses {exfil_cmd['description']} "
                        f"with a high-entropy argument ({flagged[:40]}...) that may encode "
                        f"secrets. Blocked to prevent data leakage."
                    )
        except re.error:
            continue

    return None


def main():
    """Main entry point for the hook."""
    try:
        input_data = json.load(sys.stdin)

        tool_name = input_data.get("tool_name", "")
        tool_input = input_data.get("tool_input", {})

        config = load_config()
        if not config:
            print(json.dumps({}))
            return

        if tool_name == "WebSearch":
            result = check_websearch(tool_input, config)
        elif tool_name == "WebFetch":
            result = check_webfetch(tool_input, config)
        elif tool_name == "Bash":
            result = check_bash(tool_input, config)
        else:
            result = None

        print(json.dumps(result if result else {}))

    except json.JSONDecodeError:
        print(json.dumps({}))
    except Exception:
        print(json.dumps({}))


if __name__ == "__main__":
    main()
