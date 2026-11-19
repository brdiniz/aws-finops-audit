from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List

from ..models import Finding
from ..pricing import NAT_GATEWAY_HOURLY, hourly_to_monthly


def idle(session, region, cfg) -> List[Finding]:
    """NAT gateways that sent almost no traffic over the lookback window.

    Only the hourly charge is counted as savings; data processing charges depend on traffic.
    """
    ec2 = session.client("ec2", region_name=region)
    cw = session.client("cloudwatch", region_name=region)
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=cfg.lookback_days)
    threshold_bytes = cfg.nat_idle_gb * 1024**3

    findings: List[Finding] = []
    for page in ec2.get_paginator("describe_nat_gateways").paginate(
        Filter=[{"Name": "state", "Values": ["available"]}]
    ):
        for gw in page["NatGateways"]:
            if gw["CreateTime"] > end - timedelta(days=cfg.min_age_days):
                continue
            stats = cw.get_metric_statistics(
                Namespace="AWS/NATGateway",
                MetricName="BytesOutToDestination",
                Dimensions=[{"Name": "NatGatewayId", "Value": gw["NatGatewayId"]}],
                StartTime=start,
                EndTime=end,
                Period=86400,
                Statistics=["Sum"],
            )
            total = sum(p["Sum"] for p in stats["Datapoints"])
            if total >= threshold_bytes:
                continue
            findings.append(
                Finding(
                    check_id="nat-idle",
                    title="Idle NAT gateway",
                    resource_id=gw["NatGatewayId"],
                    region=region,
                    monthly_savings_usd=round(hourly_to_monthly(NAT_GATEWAY_HOURLY), 2),
                    confidence="medium",
                    detail=f"{total / 1024**2:.1f} MB sent to the internet in {cfg.lookback_days} days",
                    recommendation=(
                        "Check which subnets route through it. Delete it, or consolidate to one NAT per VPC "
                        "in non-production environments. Gateway VPC endpoints for S3 and DynamoDB are free."
                    ),
                )
            )
    return findings
