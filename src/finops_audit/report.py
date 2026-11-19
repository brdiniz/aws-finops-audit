from __future__ import annotations

import json
from datetime import datetime, timezone

from .models import AuditResult

CHECK_TITLES = {
    "ebs-unattached": "Unattached EBS volumes",
    "ebs-gp2": "EBS gp2 volumes that can move to gp3",
    "snapshots-old": "Old EBS snapshots",
    "eip-unassociated": "Unassociated Elastic IPs",
    "nat-idle": "Idle NAT gateways",
    "elb-no-targets": "Load balancers with no targets",
    "ec2-idle": "Idle EC2 instances",
}


def _usd(value: float) -> str:
    return f"${value:,.2f}"


def to_json(result: AuditResult) -> str:
    return json.dumps(result.to_dict(), indent=2)


def to_markdown(result: AuditResult) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "# AWS cost waste report",
        "",
        f"- Account: `{result.account_id}`",
        f"- Regions: {', '.join(result.regions)}",
        f"- Generated: {now}",
        f"- Findings: {len(result.findings)}",
        f"- **Estimated monthly savings: {_usd(result.total_monthly_savings)}**"
        f" (about {_usd(result.total_monthly_savings * 12)} per year)",
        "",
        "> Estimates use static us-east-1 list prices and ignore discounts, Savings Plans"
        " and Reserved Instances. Validate in Cost Explorer before acting.",
        "",
    ]

    if result.findings:
        lines += ["## Summary", "", "| Check | Findings | Est. monthly savings |", "|---|---:|---:|"]
        for check_id, items in sorted(
            result.by_check().items(),
            key=lambda kv: -sum(f.monthly_savings_usd for f in kv[1]),
        ):
            total = sum(f.monthly_savings_usd for f in items)
            lines.append(f"| {CHECK_TITLES.get(check_id, check_id)} | {len(items)} | {_usd(total)} |")
        lines.append("")

        for check_id, items in sorted(
            result.by_check().items(),
            key=lambda kv: -sum(f.monthly_savings_usd for f in kv[1]),
        ):
            lines += [f"## {CHECK_TITLES.get(check_id, check_id)}", ""]
            lines += ["| Resource | Region | Est. savings/mo | Confidence | Detail |", "|---|---|---:|---|---|"]
            for f in sorted(items, key=lambda x: -x.monthly_savings_usd):
                lines.append(
                    f"| `{f.resource_id}` | {f.region} | {_usd(f.monthly_savings_usd)} "
                    f"| {f.confidence} | {f.detail} |"
                )
            lines += ["", f"**Recommendation:** {items[0].recommendation}", ""]
    else:
        lines += ["No waste found by the checks that ran.", ""]

    if result.errors:
        lines += ["## Checks that could not run", ""]
        for e in result.errors:
            lines.append(f"- `{e.check_id}` in {e.region}: {e.message}")
        lines.append("")

    return "\n".join(lines)
