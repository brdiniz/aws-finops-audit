> **Sample output.** Generated against a mocked AWS account with made-up resources, so you can see the format. Not real customer data.

# AWS cost waste report

- Account: `123456789012`
- Regions: eu-west-1
- Generated: 2026-11-19 12:24 UTC
- Findings: 9
- **Estimated monthly savings: $228.15** (about $2,737.80 per year)

> Estimates use static us-east-1 list prices and ignore discounts, Savings Plans and Reserved Instances. Validate in Cost Explorer before acting.

## Summary

| Check | Findings | Est. monthly savings |
|---|---:|---:|
| Unattached EBS volumes | 4 | $174.00 |
| Idle NAT gateways | 1 | $32.85 |
| EBS gp2 volumes that can move to gp3 | 2 | $14.00 |
| Unassociated Elastic IPs | 2 | $7.30 |

## Unattached EBS volumes

| Resource | Region | Est. savings/mo | Confidence | Detail |
|---|---|---:|---|---|
| `vol-42d529fd1e9d11ee5` | eu-west-1 | $80.00 | high | 1000 GB gp3, not attached to any instance |
| `vol-312fc41c453d6ba16` | eu-west-1 | $50.00 | high | 500 GB gp2, not attached to any instance |
| `vol-68e8dded22dbc38f7` | eu-west-1 | $24.00 | high | 300 GB gp3, not attached to any instance |
| `vol-4f160b04fc29e6c68` | eu-west-1 | $20.00 | high | 200 GB gp2, not attached to any instance |

**Recommendation:** Snapshot the volume if the data might be needed, then delete it. Confirm with the owning team first.

## Idle NAT gateways

| Resource | Region | Est. savings/mo | Confidence | Detail |
|---|---|---:|---|---|
| `nat-39e21231e05584029` | eu-west-1 | $32.85 | medium | 0.0 MB sent to the internet in 14 days |

**Recommendation:** Check which subnets route through it. Delete it, or consolidate to one NAT per VPC in non-production environments. Gateway VPC endpoints for S3 and DynamoDB are free.

## EBS gp2 volumes that can move to gp3

| Resource | Region | Est. savings/mo | Confidence | Detail |
|---|---|---:|---|---|
| `vol-312fc41c453d6ba16` | eu-west-1 | $10.00 | high | 500 GB gp2 |
| `vol-4f160b04fc29e6c68` | eu-west-1 | $4.00 | high | 200 GB gp2 |

**Recommendation:** Modify the volume type to gp3 in place (no downtime). Provision extra IOPS or throughput only if the workload needs more than the baseline.

## Unassociated Elastic IPs

| Resource | Region | Est. savings/mo | Confidence | Detail |
|---|---|---:|---|---|
| `eipalloc-bab33edc922de91e6` | eu-west-1 | $3.65 | high | 127.112.49.237 is allocated but not attached to anything |
| `eipalloc-9fbb56428ed65d5d0` | eu-west-1 | $3.65 | high | 127.81.214.26 is allocated but not attached to anything |

**Recommendation:** Release the address if it is not reserved for an allowlist or planned failover.

