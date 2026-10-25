# SPDX-License-Identifier: Apache-2.0
"""Steps 1 to 5 of a read (`read_side_contract.md` section 3): a material reference to the one record it pins,
or the reasons it is refused. The steps run in order, and the first that refuses ends the resolution.
"""

from collections.abc import Collection
from dataclasses import dataclass, field

from materica.core.hashing import content_hash
from materica.core.identifiers import CONTENT_HASH, MaterialRef
from materica.core.reasons import Reason
from materica.core.record import Record, RecordStore
from materica.shapes import Suite


@dataclass(frozen=True)
class ResolvedRecord:
    """The record the reference pins, its hash as recomputed under the hash suite (None without it), and the
    labels the steps gave."""

    record: Record
    recomputed_hash: str | None
    labels: tuple[str, ...]


@dataclass(frozen=True)
class Refused:
    """The reasons that ended steps 1 to 5, and the labels of the steps before: `hash_not_checked` only once
    the read has reached step 4. `record_found` says whether step 1 found the record the reference pins: every
    refusal of steps 2 to 5 is of a record found, and only step 1's own is of none."""

    reasons: tuple[Reason, ...]
    labels: tuple[str, ...] = ()
    record_found: bool = field(default=True, compare=False, repr=False)
    """Outside equality and `repr`, as `ReadResult.applied` and `resolved` are: bookkeeping for a build, so
    two refusals with the same reasons and labels are equal whichever step gave them."""


def resolve_record(
    ref: MaterialRef, store: RecordStore, claims: Collection[Suite]
) -> ResolvedRecord | Refused:
    found = _candidate(ref, store)
    if isinstance(found, Reason):
        return Refused((found,), record_found=False)
    for refusal in (found.version_refusal, found.envelope_refusal):
        if refusal is not None:
            return Refused((refusal,))
    recomputed: str | None = None
    labels: tuple[str, ...] = ()
    if "hash" in claims:
        recomputed = content_hash(found.value)
        if recomputed != found.value["content_hash"]:
            # The stated hash equals the pin (step 1), so the recomputed one differs from the pin as well.
            detail = f"{found.source}: recomputed {recomputed}"
            return Refused((Reason("hash_mismatch", detail=detail), Reason("pin_mismatch", detail=detail)))
    else:
        labels = ("hash_not_checked",)
    if found.type_refusal is not None:
        return Refused((found.type_refusal,), labels)
    return ResolvedRecord(found, recomputed, labels)


def _candidate(ref: MaterialRef, store: RecordStore) -> Record | Reason:
    """Step 1: the candidate of the reference's `id` and `version` stating its hash, or why there is none."""
    candidates = store.get(ref.id, ref.version)
    unreadable = ", ".join(source for source, _ in store.unparsed())
    if not candidates:
        if unreadable:
            return Reason(
                "malformed", detail=f"no record {ref.id} {ref.version}; it may be one of {unreadable}"
            )
        return Reason("absent", detail=f"no record {ref.id} {ref.version}")
    pinned = [
        candidate for candidate in candidates if candidate.value.get("content_hash") == ref.content_hash
    ]
    if pinned:
        if any(candidate.data != pinned[0].data for candidate in pinned[1:]):
            sources = ", ".join(candidate.source for candidate in pinned)
            return Reason("malformed", detail=f"copies of {ref.id} {ref.version} differ: {sources}")
        return pinned[0]
    ill_formed = ", ".join(candidate.source for candidate in candidates if not _well_formed(candidate))
    if unreadable or ill_formed:
        return Reason("malformed", detail=f"none holds the pin; it may be one of {unreadable or ill_formed}")
    return Reason("pin_mismatch", detail=f"no copy of {ref.id} {ref.version} states {ref.content_hash}")


def _well_formed(candidate: Record) -> bool:
    stated = candidate.value.get("content_hash")
    return isinstance(stated, str) and CONTENT_HASH.fullmatch(stated) is not None
