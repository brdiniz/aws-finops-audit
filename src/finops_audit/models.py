from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Dict, List


@dataclass
class Finding:
    """One piece of potential waste on a single AWS resource."""

    check_id: str
    title: str
    resource_id: str
    region: str
    monthly_savings_usd: float
    confidence: str  # "high" | "medium" | "low"
    detail: str
    recommendation: str

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class CheckError:
    """A check that could not run (usually missing permissions)."""

    check_id: str
    region: str
    message: str

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class AuditResult:
    account_id: str
    regions: List[str]
    findings: List[Finding] = field(default_factory=list)
    errors: List[CheckError] = field(default_factory=list)

    @property
    def total_monthly_savings(self) -> float:
        return round(sum(f.monthly_savings_usd for f in self.findings), 2)

    def by_check(self) -> Dict[str, List[Finding]]:
        grouped: Dict[str, List[Finding]] = {}
        for f in self.findings:
            grouped.setdefault(f.check_id, []).append(f)
        return grouped

    def to_dict(self) -> Dict:
        return {
            "account_id": self.account_id,
            "regions": self.regions,
            "total_monthly_savings_usd": self.total_monthly_savings,
            "findings": [f.to_dict() for f in self.findings],
            "errors": [e.to_dict() for e in self.errors],
        }
