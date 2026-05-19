"""
Post-processing rules engine.

User-defined regex find/replace rules organized into named profiles.
Rules are applied to the final Markdown string after conversion,
letting users normalize output without manual editing.

Profiles are stored as JSON in the config directory.
"""

import json
import os
import re
from dataclasses import dataclass, field, asdict
from typing import Optional


_PROFILES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config", "rule_profiles.json")


@dataclass
class Rule:
    name: str = ""
    pattern: str = ""
    replacement: str = ""
    enabled: bool = True
    use_regex: bool = True

    def apply(self, text: str) -> str:
        if not self.enabled or not self.pattern:
            return text
        try:
            if self.use_regex:
                compiled = re.compile(self.pattern)
                return compiled.sub(self.replacement, text)
            return text.replace(self.pattern, self.replacement)
        except (re.error, Exception):
            return text


@dataclass
class RuleProfile:
    name: str = ""
    rules: list[Rule] = field(default_factory=list)

    def apply_all(self, text: str) -> str:
        for rule in self.rules:
            text = rule.apply(text)
        return text

    def preview(self, text: str) -> tuple[str, list[str]]:
        """Apply rules one at a time, returning final text and per-rule change summaries."""
        changes: list[str] = []
        for rule in self.rules:
            if not rule.enabled or not rule.pattern:
                continue
            before = text
            text = rule.apply(text)
            if text != before:
                diff_count = _count_changes(before, text, rule)
                changes.append(f"{rule.name}: {diff_count} replacement(s)")
            else:
                changes.append(f"{rule.name}: no matches")
        return text, changes


def _count_changes(before: str, after: str, rule: Rule) -> int:
    try:
        if rule.use_regex:
            return len(re.findall(rule.pattern, before))
        return before.count(rule.pattern)
    except re.error:
        return 0


# ---------------------------------------------------------------------------
# Profile persistence
# ---------------------------------------------------------------------------

def load_profiles() -> list[RuleProfile]:
    path = os.path.normpath(_PROFILES_PATH)
    if not os.path.isfile(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        profiles = []
        for p in data:
            rules = [Rule(**{k: v for k, v in r.items() if k in Rule.__dataclass_fields__}) for r in p.get("rules", [])]
            profiles.append(RuleProfile(name=p.get("name", ""), rules=rules))
        return profiles
    except Exception:
        return []


def save_profiles(profiles: list[RuleProfile]) -> None:
    path = os.path.normpath(_PROFILES_PATH)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = []
    for profile in profiles:
        data.append({
            "name": profile.name,
            "rules": [asdict(r) for r in profile.rules],
        })
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)


def get_profile_by_name(profiles: list[RuleProfile], name: str) -> Optional[RuleProfile]:
    for p in profiles:
        if p.name == name:
            return p
    return None
