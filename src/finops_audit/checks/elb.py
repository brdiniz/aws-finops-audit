from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List

from botocore.exceptions import ClientError

from ..models import Finding
from ..pricing import ALB_HOURLY, NLB_HOURLY, hourly_to_monthly


def no_targets(session, region, cfg) -> List[Finding]:
    """Application and Network Load Balancers with no registered targets behind them."""
    elbv2 = session.client("elbv2", region_name=region)
    cutoff = datetime.now(timezone.utc) - timedelta(days=cfg.min_age_days)
    findings: List[Finding] = []

    for page in elbv2.get_paginator("describe_load_balancers").paginate():
        for lb in page["LoadBalancers"]:
            lb_type = lb.get("Type")
            if lb_type not in ("application", "network") or lb["CreatedTime"] > cutoff:
                continue

            try:
                target_groups = elbv2.describe_target_groups(LoadBalancerArn=lb["LoadBalancerArn"])["TargetGroups"]
            except ClientError as exc:
                # Some API versions answer "not found" instead of an empty list when none are attached.
                if exc.response.get("Error", {}).get("Code") != "TargetGroupNotFound":
                    raise
                target_groups = []
            registered = 0
            for tg in target_groups:
                health = elbv2.describe_target_health(TargetGroupArn=tg["TargetGroupArn"])
                registered += len(health["TargetHealthDescriptions"])
            if registered:
                continue

            hourly = ALB_HOURLY if lb_type == "application" else NLB_HOURLY
            findings.append(
                Finding(
                    check_id="elb-no-targets",
                    title="Load balancer with no targets",
                    resource_id=lb["LoadBalancerName"],
                    region=region,
                    monthly_savings_usd=round(hourly_to_monthly(hourly), 2),
                    confidence="medium",
                    detail=(
                        f"{lb_type} load balancer with {len(target_groups)} target group(s) "
                        "and 0 registered targets"
                    ),
                    recommendation=(
                        "Confirm it is not a placeholder for a planned release or a Lambda target, then delete it."
                    ),
                )
            )
    return findings
