"""Static reference prices (USD, us-east-1, on-demand, Linux).

These are deliberately simple estimates so the tool needs no Pricing API access.
Other regions are usually within roughly +/-30%, so treat every number in the
report as an order-of-magnitude estimate, not a quote. Verify against the AWS
Pricing Calculator or Cost Explorer before committing to a change.
"""

HOURS_PER_MONTH = 730

# $ per GB-month
EBS_GB_MONTH = {
    "gp3": 0.08,
    "gp2": 0.10,
    "io1": 0.125,
    "io2": 0.125,
    "st1": 0.045,
    "sc1": 0.015,
    "standard": 0.05,
}
EBS_DEFAULT_GB_MONTH = 0.10
SNAPSHOT_GB_MONTH = 0.05

# $ per hour
EIP_HOURLY = 0.005
NAT_GATEWAY_HOURLY = 0.045
ALB_HOURLY = 0.0225
NLB_HOURLY = 0.0225
CLB_HOURLY = 0.025

# $ per month, on-demand Linux, us-east-1
EC2_MONTHLY = {
    "t2.micro": 8.47,
    "t2.small": 16.79,
    "t2.medium": 33.87,
    "t3.micro": 7.59,
    "t3.small": 15.18,
    "t3.medium": 30.37,
    "t3.large": 60.74,
    "t3.xlarge": 121.47,
    "m5.large": 70.08,
    "m5.xlarge": 140.16,
    "m5.2xlarge": 280.32,
    "m6i.large": 70.08,
    "c5.large": 62.05,
    "c5.xlarge": 124.10,
    "r5.large": 91.98,
    "r5.xlarge": 183.96,
}


def ebs_monthly(volume_type: str, size_gb: int) -> float:
    return size_gb * EBS_GB_MONTH.get(volume_type, EBS_DEFAULT_GB_MONTH)


def hourly_to_monthly(hourly: float) -> float:
    return hourly * HOURS_PER_MONTH


def ec2_monthly(instance_type: str):
    """Returns the monthly price or None if the instance type is not in the table."""
    return EC2_MONTHLY.get(instance_type)
