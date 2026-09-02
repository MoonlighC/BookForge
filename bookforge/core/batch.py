"""Batch preflight policies shared by the UI and worker orchestration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from bookforge.core.converter import ConversionError, ConverterService
from bookforge.core.metadata import MetadataOverrides
from bookforge.core.queue import QueueItem, QueueStatus, path_key


class OverwritePolicy(str, Enum):
    ASK = "Ask"
    REPLACE_ALL = "Replace all"
    SKIP_ALL = "Skip all"


class OverwriteDecision(str, Enum):
    REPLACE = "Replace"
    SKIP = "Skip"
    CANCEL_BATCH = "Cancel batch"


@dataclass(frozen=True, slots=True)
class BatchJob:
    item_id: str
    source_path: Path
    output_format: str
    overwrite: bool = False
    metadata_overrides: MetadataOverrides = MetadataOverrides()


@dataclass(frozen=True, slots=True)
class PreflightIssue:
    item_id: str
    status: QueueStatus
    message: str


@dataclass(frozen=True, slots=True)
class PreflightResult:
    jobs: tuple[BatchJob, ...]
    issues: tuple[PreflightIssue, ...]
    batch_cancelled: bool = False


def preflight_batch(
    converter: ConverterService,
    items: tuple[QueueItem, ...],
    output_folder: Path,
    overwrite_policy: OverwritePolicy,
    ask_overwrite: Callable[[Path], OverwriteDecision] | None = None,
) -> PreflightResult:
    """Validate a batch and resolve output policy without running Calibre."""
    validated: list[tuple[QueueItem, Path]] = []
    issues: list[PreflightIssue] = []
    claimed_outputs: set[str] = set()

    for item in items:
        try:
            output_path = converter.preflight(
                item.source_path,
                output_folder,
                item.output_format,
                item.metadata_overrides,
            )
        except ConversionError as exc:
            issues.append(
                PreflightIssue(item.item_id, QueueStatus.FAILED, str(exc))
            )
            continue

        output_key = path_key(output_path)
        if output_key in claimed_outputs:
            issues.append(
                PreflightIssue(
                    item.item_id,
                    QueueStatus.FAILED,
                    "Another queued book targets the same output filename.",
                )
            )
            continue
        claimed_outputs.add(output_key)
        validated.append((item, output_path))

    jobs: list[BatchJob] = []
    for index, (item, output_path) in enumerate(validated):
        overwrite = False
        if output_path.exists():
            if overwrite_policy is OverwritePolicy.REPLACE_ALL:
                overwrite = True
            elif overwrite_policy is OverwritePolicy.SKIP_ALL:
                issues.append(
                    PreflightIssue(
                        item.item_id,
                        QueueStatus.SKIPPED,
                        "Skipped because the output file already exists.",
                    )
                )
                continue
            else:
                if ask_overwrite is None:
                    raise ValueError("Ask policy requires an overwrite callback.")
                decision = ask_overwrite(output_path)
                if decision is OverwriteDecision.SKIP:
                    issues.append(
                        PreflightIssue(
                            item.item_id,
                            QueueStatus.SKIPPED,
                            "Skipped because the existing output was not replaced.",
                        )
                    )
                    continue
                if decision is OverwriteDecision.CANCEL_BATCH:
                    accepted_ids = {job.item_id for job in jobs}
                    for accepted_item, _path in validated[:index]:
                        if accepted_item.item_id in accepted_ids:
                            issues.append(
                                PreflightIssue(
                                    accepted_item.item_id,
                                    QueueStatus.CANCELLED,
                                    "Batch cancelled before conversion started.",
                                )
                            )
                    for remaining_item, _path in validated[index:]:
                        issues.append(
                            PreflightIssue(
                                remaining_item.item_id,
                                QueueStatus.CANCELLED,
                                "Batch cancelled before conversion started.",
                            )
                        )
                    return PreflightResult((), tuple(issues), True)
                overwrite = True

        jobs.append(
            BatchJob(
                item.item_id,
                item.source_path,
                item.output_format,
                overwrite,
                item.metadata_overrides,
            )
        )

    return PreflightResult(tuple(jobs), tuple(issues))
