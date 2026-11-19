# aws-finops-audit

A small, read-only command-line tool that scans an AWS account for common cost waste and writes a report with an estimated monthly saving for each finding.

It runs in under a minute, changes nothing in your account, and needs only a handful of `Describe*` permissions.

## What it finds

| Check | Example |
|---|---|
| Unattached EBS volumes | A 500 GB volume left behind after an instance was terminated |
| gp2 volumes that can move to gp3 | About 20% cheaper per GB, with no downtime |
| Old snapshots | Backups from instances and volumes that no longer exist |
| Unassociated Elastic IPs | Allocated and billed, attached to nothing |
| Idle NAT gateways | An hourly charge for a gateway that moved almost no traffic |
| Load balancers with no targets | ALBs and NLBs fronting nothing |
| Idle EC2 instances | CPU under 5% every day for two weeks |

Details, assumptions and false-positive risks for each check are in [docs/checks.md](docs/checks.md). A sample report is in [examples/sample-report.md](examples/sample-report.md).

## Quick start

```bash
git clone https://github.com/<your-username>/aws-finops-audit.git
cd aws-finops-audit
pip install -e .

finops-audit --profile my-profile --regions eu-west-1,us-east-1 -o report.md
```

Useful options:

```text
--checks ebs-unattached,nat-idle   Run a subset
--format json                      Machine-readable output
--lookback-days 30                 CloudWatch window for idle checks (default 14)
--snapshot-age-days 180            Snapshot age threshold (default 90)
--min-age-days 14                  Ignore resources newer than this (default 7)
```

## Permissions

The tool only reads. Attach the policy in [docs/iam-policy.json](docs/iam-policy.json) to a role or user. If a permission is missing, that check is skipped and listed under "Checks that could not run" instead of failing the whole run.

## How accurate are the numbers?

They are estimates, not quotes. The tool uses static us-east-1 on-demand list prices, so it ignores discounts, Savings Plans, Reserved Instances and regional price differences. Treat each number as the order of magnitude of what is at stake, and confirm in Cost Explorer before you delete or resize anything. Every finding carries a confidence level and a recommendation that says what to verify first.

## Development

```bash
pip install -e ".[dev]"
pytest
```

Tests use [moto](https://github.com/getmoto/moto), so no AWS account or credentials are needed.

## Want help acting on the report?

Finding waste is the easy part. Deciding what is safe to remove, right-sizing without hurting performance, and putting guardrails in place so the waste does not come back usually takes someone who has run production AWS environments.

I offer a fixed-scope **AWS cost review**: I run this and a deeper manual analysis against your account (read-only access), then give you a prioritised list of savings with the risk and effort of each, and a walkthrough call. I also advise teams on engineering structure and on AWS migrations.

Contact: <your-email-or-booking-link>

## License

MIT. See [LICENSE](LICENSE).
