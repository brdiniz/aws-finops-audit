from __future__ import annotations

from typing import List

from ..models import Finding
from ..pricing import EIP_HOURLY, hourly_to_monthly


def unassociated(session, region, cfg) -> List[Finding]:
    ec2 = session.client("ec2", region_name=region)
    findings: List[Finding] = []
    for addr in ec2.describe_addresses()["Addresses"]:
        if addr.get("AssociationId") or addr.get("InstanceId") or addr.get("NetworkInterfaceId"):
            continue
        findings.append(
            Finding(
                check_id="eip-unassociated",
                title="Unassociated Elastic IP",
                resource_id=addr.get("AllocationId", addr.get("PublicIp", "unknown")),
                region=region,
                monthly_savings_usd=round(hourly_to_monthly(EIP_HOURLY), 2),
                confidence="high",
                detail=f"{addr.get('PublicIp', 'n/a')} is allocated but not attached to anything",
                recommendation="Release the address if it is not reserved for an allowlist or planned failover.",
            )
        )
    return findings
