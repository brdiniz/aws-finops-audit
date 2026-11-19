from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List

import boto3

from ..models import Finding


@dataclass
class Thresholds:
    min_age_days: int = 7  # ignore resources newer than this (avoids flagging things mid-provisioning)
    snapshot_age_days: int = 90
    lookback_days: int = 14  # CloudWatch window for idle checks
    ec2_cpu_percent: float = 5.0
    nat_idle_gb: float = 1.0  # total bytes out over the window below this = idle


CheckFn = Callable[[boto3.Session, str, Thresholds], List[Finding]]

from . import ebs, ec2, eip, elb, nat, snapshots  # noqa: E402

REGISTRY: Dict[str, CheckFn] = {
    "ebs-unattached": ebs.unattached,
    "ebs-gp2": ebs.gp2_to_gp3,
    "snapshots-old": snapshots.old_snapshots,
    "eip-unassociated": eip.unassociated,
    "nat-idle": nat.idle,
    "elb-no-targets": elb.no_targets,
    "ec2-idle": ec2.idle,
}
