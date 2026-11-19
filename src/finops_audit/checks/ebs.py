from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List

from ..models import Finding
from ..pricing import EBS_GB_MONTH, ebs_monthly


def _old_enough(created, days: int) -> bool:
    return created <= datetime.now(timezone.utc) - timedelta(days=days)


def unattached(session, region, cfg) -> List[Finding]:
    ec2 = session.client("ec2", region_name=region)
    findings: List[Finding] = []
    paginator = ec2.get_paginator("describe_volumes")
    for page in paginator.paginate(Filters=[{"Name": "status", "Values": ["available"]}]):
        for vol in page["Volumes"]:
            if not _old_enough(vol["CreateTime"], cfg.min_age_days):
                continue
            savings = ebs_monthly(vol["VolumeType"], vol["Size"])
            findings.append(
                Finding(
                    check_id="ebs-unattached",
                    title="Unattached EBS volume",
                    resource_id=vol["VolumeId"],
                    region=region,
                    monthly_savings_usd=round(savings, 2),
                    confidence="high",
                    detail=f"{vol['Size']} GB {vol['VolumeType']}, not attached to any instance",
                    recommendation=(
                        "Snapshot the volume if the data might be needed, then delete it. "
                        "Confirm with the owning team first."
                    ),
                )
            )
    return findings


def gp2_to_gp3(session, region, cfg) -> List[Finding]:
    """gp3 is about 20% cheaper per GB than gp2 with a 3,000 IOPS baseline."""
    ec2 = session.client("ec2", region_name=region)
    findings: List[Finding] = []
    paginator = ec2.get_paginator("describe_volumes")
    for page in paginator.paginate(Filters=[{"Name": "volume-type", "Values": ["gp2"]}]):
        for vol in page["Volumes"]:
            size = vol["Size"]
            saving = size * (EBS_GB_MONTH["gp2"] - EBS_GB_MONTH["gp3"])
            # gp2 gets 3 IOPS/GB, so volumes above 1,000 GB exceed the gp3 baseline and need extra provisioning.
            confidence = "high" if size <= 1000 else "medium"
            findings.append(
                Finding(
                    check_id="ebs-gp2",
                    title="gp2 volume can move to gp3",
                    resource_id=vol["VolumeId"],
                    region=region,
                    monthly_savings_usd=round(saving, 2),
                    confidence=confidence,
                    detail=f"{size} GB gp2"
                    + ("" if size <= 1000 else " (above 1,000 GB: check IOPS needs before migrating)"),
                    recommendation=(
                        "Modify the volume type to gp3 in place (no downtime). "
                        "Provision extra IOPS or throughput only if the workload needs more than the baseline."
                    ),
                )
            )
    return findings
