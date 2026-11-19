from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List

from ..models import Finding
from ..pricing import SNAPSHOT_GB_MONTH


def old_snapshots(session, region, cfg) -> List[Finding]:
    """Flags snapshots older than the threshold.

    Savings are an upper bound: snapshots are incremental, so deleting one frees
    only the blocks no other snapshot references. Snapshots used by AMIs are skipped.
    """
    ec2 = session.client("ec2", region_name=region)
    cutoff = datetime.now(timezone.utc) - timedelta(days=cfg.snapshot_age_days)

    ami_snapshots = set()
    for page in ec2.get_paginator("describe_images").paginate(Owners=["self"]):
        for image in page["Images"]:
            for mapping in image.get("BlockDeviceMappings", []):
                snap_id = mapping.get("Ebs", {}).get("SnapshotId")
                if snap_id:
                    ami_snapshots.add(snap_id)

    existing_volumes = set()
    for page in ec2.get_paginator("describe_volumes").paginate():
        for vol in page["Volumes"]:
            existing_volumes.add(vol["VolumeId"])

    findings: List[Finding] = []
    for page in ec2.get_paginator("describe_snapshots").paginate(OwnerIds=["self"]):
        for snap in page["Snapshots"]:
            if snap["StartTime"] > cutoff or snap["SnapshotId"] in ami_snapshots:
                continue
            orphaned = snap.get("VolumeId") not in existing_volumes
            age_days = (datetime.now(timezone.utc) - snap["StartTime"]).days
            savings = snap["VolumeSize"] * SNAPSHOT_GB_MONTH
            findings.append(
                Finding(
                    check_id="snapshots-old",
                    title="Old EBS snapshot",
                    resource_id=snap["SnapshotId"],
                    region=region,
                    monthly_savings_usd=round(savings, 2),
                    confidence="medium" if orphaned else "low",
                    detail=(
                        f"{snap['VolumeSize']} GB, {age_days} days old, "
                        + ("source volume no longer exists" if orphaned else "source volume still exists")
                    ),
                    recommendation=(
                        "Adopt a lifecycle policy (Data Lifecycle Manager or AWS Backup) and delete snapshots "
                        "outside your retention window. Savings are an upper bound because snapshots are incremental."
                    ),
                )
            )
    return findings
