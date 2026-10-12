"""Store names are requests to authorize, never an authorization source."""

import re
from dataclasses import dataclass

from loja_assistente.analytics.contracts import StoreScope
from loja_assistente.assistant.filter_limits import normalize


@dataclass(frozen=True)
class MentionResolution:
    resolved_ids: list[str]
    ambiguous: dict[str, list[StoreScope]]
    unknown: list[str]


def inspect_mentions(text: str, stores: list[StoreScope]) -> MentionResolution:
    # Resolve only against the authorized roster. Unknown references remain requests to deny.
    references = re.findall(r"\b[ab]\d{3}\b", text)
    names = {normalize(store.name) for store in stores} | {"centro", "jardins", "norte"}
    # A compound name must not also request a shorter name contained inside it.
    name_pattern = (
        r"\b(?:"
        + "|".join(re.escape(name) for name in sorted(names, key=lambda name: (-len(name), name)))
        + r")\b"
    )
    references.extend(match.group() for match in re.finditer(name_pattern, text))
    references.extend(explicit_store_names(text))
    organization = re.search(r"organizacao\s+([ab])\b", text)
    if organization:
        references.append(f"organization:{organization.group(1)}")
    if "brisa" in text:
        references.append("organization:brisa")
    if "aurora" in text:
        references.append("organization:aurora")
    resolved: list[str] = []
    ambiguous: dict[str, list[StoreScope]] = {}
    unknown: list[str] = []
    for reference in dict.fromkeys(references):
        matches = [
            store for store in stores if reference in (normalize(store.name), store.id.casefold())
        ]
        if len(matches) > 1:
            ambiguous[reference] = matches
        elif matches:
            resolved.append(matches[0].id)
        else:
            unknown.append(reference)
    return MentionResolution(list(dict.fromkeys(resolved)), ambiguous, unknown)


def resolve_mentions(text: str, stores: list[StoreScope]) -> list[str] | None:
    mentions = inspect_mentions(text, stores)
    if mentions.ambiguous:
        return None
    return [*mentions.resolved_ids, *mentions.unknown]


def explicit_store_names(text: str) -> list[str]:
    # This bounded grammar accepts names separated by "e" or commas, ending at a period clause.
    boundary = (
        r"\b(?:ontem|anteontem|hoje|nos|no|nas|na|em|durante|desde|entre|comparad[oa]s?|versus|vs)\b"
        r"|\b(?:semana\s+passada|(?:este|nesse)\s+mes|ultimos?\s+|com\s+o\s+periodo)"
        r"|\bde\s+\d|[:?;.!]"
    )
    references = []
    for mention in re.finditer(r"\blojas?\s+", text):
        names = re.split(boundary, text[mention.end() :], maxsplit=1)[0]
        for candidate in re.split(r",|\s+e\s+", names):
            candidate = re.sub(r"^(?:(?:da|de|na)\s+)?(?:lojas?\s+)?", "", candidate.strip())
            candidate = candidate.strip(" \"'“”")
            if candidate and candidate not in ("toda", "todas", "anterior"):
                references.append(candidate)
    return references
