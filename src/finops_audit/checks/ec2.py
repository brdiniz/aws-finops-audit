from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List

from ..models import Finding
from ..pricing import ec2_monthly


def idle(session, region, cfg) -> List[Finding]:
    """Running instances whose daily average CPU never exceeded the threshold in the lookback window.

    CPU alone does not prove an instance is unused (memory- or network-bound workloads exist),
    so confidence is capped at medium and the recommendation is to right-size or stop after review.
    """
    ec2 = session.client("ec2", region_name=region)
    cw = session.client("cloudwatch", region_name=region)
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=cfg.lookback_days)
    launched_before = end - timedelta(days=cfg.lookback_days)

    findings: List[Finding] = []
    paginator = ec2.get_paginator("describe_instances")
    for page in paginator.paginate(Filters=[{"Name": "instance-state-name", "Values": ["running"]}]):
        for reservation in page["Reservations"]:
            for inst in reservation["Instances"]:
                if inst["LaunchTime"] > launched_before:
                    continue  # not enough history
                stats = cw.get_metric_statistics(
                    Namespace="AWS/EC2",
                    MetricName="CPUUtilization",
                    Dimensions=[{"Name": "InstanceId", "Value": inst["InstanceId"]}],
                    StartTime=start,
                    EndTime=end,
                    Period=86400,
                    Statistics=["Average"],
                )
                points = stats["Datapoints"]
                if not points:
                    continue
                peak_daily_avg = max(p["Average"] for p in points)
                if peak_daily_avg >= cfg.ec2_cpu_percent:
                    continue

                price = ec2_monthly(inst["InstanceType"])
                name = next((t["Value"] for t in inst.get("Tags", []) if t["Key"] == "Name"), "")
                findings.append(
                    Finding(
                        check_id="ec2-idle",
                        title="Idle EC2 instance",
                        resource_id=inst["InstanceId"],
                        region=region,
                        monthly_savings_usd=round(price, 2) if price else 0.0,
                        confidence="medium" if price else "low",
                        detail=(
                            f"{inst['InstanceType']}{' (' + name + ')' if name else ''}, "
                            f"peak daily average CPU {peak_daily_avg:.1f}% over {cfg.lookback_days} days"
                            + ("" if price else "; price not in the built-in table, savings not estimated")
                        ),
                        recommendation=(
                            "Check memory, network and disk activity. If it is truly idle, stop or terminate it; "
                            "otherwise right-size to a smaller instance type."
                        ),
                    )
                )
    return findings
