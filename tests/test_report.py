import json

from finops_audit.models import AuditResult, CheckError, Finding
from finops_audit.report import to_json, to_markdown


def _result():
    r = AuditResult(account_id="123456789012", regions=["eu-west-1"])
    r.findings = [
        Finding("eip-unassociated", "t", "eipalloc-1", "eu-west-1", 3.65, "high", "d", "release it"),
        Finding("nat-idle", "t", "nat-1", "eu-west-1", 32.85, "medium", "d", "delete it"),
    ]
    r.errors = [CheckError("ec2-idle", "eu-west-1", "AccessDenied: no permission")]
    return r


def test_total_savings():
    assert _result().total_monthly_savings == 36.5


def test_markdown_lists_biggest_check_first_and_errors():
    md = to_markdown(_result())
    assert md.index("Idle NAT gateways") < md.index("Unassociated Elastic IPs")
    assert "$36.50" in md
    assert "Checks that could not run" in md


def test_json_round_trip():
    data = json.loads(to_json(_result()))
    assert data["total_monthly_savings_usd"] == 36.5
    assert len(data["findings"]) == 2
