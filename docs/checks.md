# What each check does

Every check is read-only. Savings are estimates from static us-east-1 list prices (see `src/finops_audit/pricing.py`).

| Check ID | Flags | Savings estimate | Main false-positive risk |
|---|---|---|---|
| `ebs-unattached` | Volumes in `available` state older than `--min-age-days` | Full monthly volume cost | Volumes kept as cold backups or for a planned reattach |
| `ebs-gp2` | gp2 volumes that could be gp3 | About 20% of the volume cost | Volumes above 1,000 GB may need extra provisioned IOPS (marked medium confidence) |
| `snapshots-old` | Snapshots older than `--snapshot-age-days`, excluding snapshots used by your AMIs | Upper bound (size x $0.05/GB) | Snapshots are incremental, so real savings are lower; compliance retention may apply |
| `eip-unassociated` | Allocated Elastic IPs attached to nothing | $3.65/month each | IPs reserved for partner allowlists |
| `nat-idle` | Available NAT gateways that sent under 1 GB in `--lookback-days` | Hourly charge only | Standby gateways kept for failover |
| `elb-no-targets` | ALBs and NLBs with zero registered targets | Hourly charge only | Load balancers fronting Lambda targets or staged for a release |
| `ec2-idle` | Running instances whose daily average CPU stayed under 5% | On-demand price from a small built-in table | Memory-, disk- or network-bound workloads; unknown instance types get no estimate |

## Adding a check

1. Create a function `my_check(session, region, cfg) -> List[Finding]` in `src/finops_audit/checks/`.
2. Register it in `REGISTRY` in `checks/__init__.py` and add a title in `report.py`.
3. Add a test in `tests/`. `moto` covers most EC2 and ELB behaviour; use a small stub when moto does not model the field you need.
