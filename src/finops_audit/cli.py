from __future__ import annotations

import argparse
import sys
from typing import List, Optional

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from . import __version__
from .checks import REGISTRY, Thresholds
from .models import AuditResult, CheckError
from .report import to_json, to_markdown


def run_audit(
    session: boto3.Session,
    regions: List[str],
    checks: Optional[List[str]] = None,
    cfg: Optional[Thresholds] = None,
) -> AuditResult:
    cfg = cfg or Thresholds()
    selected = checks or list(REGISTRY)
    unknown = [c for c in selected if c not in REGISTRY]
    if unknown:
        raise ValueError(f"Unknown check(s): {', '.join(unknown)}. Available: {', '.join(REGISTRY)}")

    account_id = session.client("sts").get_caller_identity()["Account"]
    result = AuditResult(account_id=account_id, regions=regions)

    for region in regions:
        for check_id in selected:
            try:
                result.findings.extend(REGISTRY[check_id](session, region, cfg))
            except ClientError as exc:
                code = exc.response.get("Error", {}).get("Code", "ClientError")
                result.errors.append(CheckError(check_id, region, f"{code}: {exc.response['Error'].get('Message', '')}"))
            except BotoCoreError as exc:
                result.errors.append(CheckError(check_id, region, str(exc)))
    return result


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="finops-audit",
        description="Read-only audit that finds common AWS cost waste and estimates monthly savings.",
    )
    p.add_argument("--profile", help="AWS profile name (default: standard credential chain)")
    p.add_argument("--regions", default=None, help="Comma-separated regions (default: the profile's region)")
    p.add_argument("--checks", default=None, help=f"Comma-separated subset of: {', '.join(REGISTRY)}")
    p.add_argument("--format", choices=["md", "json"], default="md")
    p.add_argument("--output", "-o", help="Write the report to this file instead of stdout")
    p.add_argument("--lookback-days", type=int, default=14, help="CloudWatch window for idle checks")
    p.add_argument("--snapshot-age-days", type=int, default=90)
    p.add_argument("--min-age-days", type=int, default=7, help="Ignore resources newer than this")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    session = boto3.Session(profile_name=args.profile)

    regions = [r.strip() for r in args.regions.split(",")] if args.regions else [session.region_name]
    if not regions or regions == [None]:
        print("No region set. Pass --regions or configure a default region.", file=sys.stderr)
        return 2
    checks = [c.strip() for c in args.checks.split(",")] if args.checks else None
    cfg = Thresholds(
        min_age_days=args.min_age_days,
        snapshot_age_days=args.snapshot_age_days,
        lookback_days=args.lookback_days,
    )

    try:
        result = run_audit(session, regions, checks, cfg)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except (BotoCoreError, ClientError) as exc:
        print(f"Could not authenticate with AWS: {exc}", file=sys.stderr)
        return 1

    output = to_json(result) if args.format == "json" else to_markdown(result)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(output + "\n")
        print(
            f"Wrote {args.output}: {len(result.findings)} findings, "
            f"~${result.total_monthly_savings:,.2f}/month estimated savings",
            file=sys.stderr,
        )
    else:
        print(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
