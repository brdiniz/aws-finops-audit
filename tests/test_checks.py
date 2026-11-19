from datetime import datetime, timedelta, timezone

import boto3
import pytest
from moto import mock_aws

from finops_audit.checks import Thresholds
from finops_audit.cli import run_audit

REGION = "us-east-1"
# Resources in moto are created "now", so disable the age filters for tests.
CFG = Thresholds(min_age_days=0, snapshot_age_days=-1, lookback_days=14)


@pytest.fixture(autouse=True)
def aws_env(monkeypatch):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", REGION)


def _run(check):
    return run_audit(boto3.Session(region_name=REGION), [REGION], [check], CFG)


@mock_aws
def test_unattached_volume_is_flagged_and_priced():
    ec2 = boto3.client("ec2", region_name=REGION)
    ec2.create_volume(AvailabilityZone=f"{REGION}a", Size=100, VolumeType="gp3")
    result = _run("ebs-unattached")
    assert len(result.findings) == 1
    assert result.findings[0].monthly_savings_usd == 8.0  # 100 GB * $0.08


@mock_aws
def test_gp2_volume_suggests_gp3_saving():
    ec2 = boto3.client("ec2", region_name=REGION)
    ec2.create_volume(AvailabilityZone=f"{REGION}a", Size=500, VolumeType="gp2")
    ec2.create_volume(AvailabilityZone=f"{REGION}a", Size=500, VolumeType="gp3")
    result = _run("ebs-gp2")
    assert len(result.findings) == 1
    assert result.findings[0].monthly_savings_usd == 10.0  # 500 GB * ($0.10 - $0.08)


@mock_aws
def test_unassociated_eip_only():
    ec2 = boto3.client("ec2", region_name=REGION)
    ec2.allocate_address(Domain="vpc")
    result = _run("eip-unassociated")
    assert len(result.findings) == 1
    assert result.findings[0].monthly_savings_usd == 3.65


@mock_aws
def test_old_snapshot_flagged_and_ami_snapshot_skipped():
    ec2 = boto3.client("ec2", region_name=REGION)
    vol = ec2.create_volume(AvailabilityZone=f"{REGION}a", Size=10)
    snap = ec2.create_snapshot(VolumeId=vol["VolumeId"])["SnapshotId"]
    result = _run("snapshots-old")
    # moto ships with canned snapshots, so look up ours by id.
    ours = [f for f in result.findings if f.resource_id == snap]
    assert len(ours) == 1
    assert ours[0].monthly_savings_usd == 0.5  # 10 GB * $0.05


def test_snapshot_used_by_ami_is_skipped():
    # moto ignores the snapshot id passed to register_image, so use a stub client here.
    from finops_audit.checks import snapshots

    old = datetime.now(timezone.utc) - timedelta(days=200)
    pages = {
        "describe_images": [{"Images": [{"BlockDeviceMappings": [{"Ebs": {"SnapshotId": "snap-ami"}}]}]}],
        "describe_volumes": [{"Volumes": []}],
        "describe_snapshots": [
            {
                "Snapshots": [
                    {"SnapshotId": "snap-ami", "StartTime": old, "VolumeSize": 8, "VolumeId": "vol-gone"},
                    {"SnapshotId": "snap-orphan", "StartTime": old, "VolumeSize": 8, "VolumeId": "vol-gone"},
                ]
            }
        ],
    }

    class StubEC2:
        def get_paginator(self, name):
            return _FakePaginator(pages[name])

    session = _FakeSession(StubEC2(), None)
    findings = snapshots.old_snapshots(session, REGION, Thresholds())
    assert [f.resource_id for f in findings] == ["snap-orphan"]


@mock_aws
def test_idle_nat_gateway():
    ec2 = boto3.client("ec2", region_name=REGION)
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]["VpcId"]
    subnet = ec2.create_subnet(VpcId=vpc, CidrBlock="10.0.1.0/24")["Subnet"]["SubnetId"]
    eip = ec2.allocate_address(Domain="vpc")["AllocationId"]
    ec2.create_nat_gateway(SubnetId=subnet, AllocationId=eip)
    result = _run("nat-idle")
    assert len(result.findings) == 1
    assert result.findings[0].monthly_savings_usd == 32.85


@mock_aws
def test_load_balancer_without_targets():
    ec2 = boto3.client("ec2", region_name=REGION)
    elb = boto3.client("elbv2", region_name=REGION)
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]["VpcId"]
    subnets = [
        ec2.create_subnet(VpcId=vpc, CidrBlock=f"10.0.{i}.0/24", AvailabilityZone=f"{REGION}{az}")["Subnet"]["SubnetId"]
        for i, az in ((1, "a"), (2, "b"))
    ]
    elb.create_load_balancer(Name="empty-alb", Subnets=subnets, Type="application")
    result = _run("elb-no-targets")
    assert len(result.findings) == 1
    assert result.findings[0].resource_id == "empty-alb"


class _FakePaginator:
    def __init__(self, pages):
        self._pages = pages

    def paginate(self, **_):
        return self._pages


class _FakeEC2:
    def __init__(self, launch_time):
        self._launch_time = launch_time

    def get_paginator(self, _):
        inst = {
            "InstanceId": "i-123",
            "InstanceType": "m5.large",
            "LaunchTime": self._launch_time,
            "Tags": [{"Key": "Name", "Value": "batch-worker"}],
        }
        return _FakePaginator([{"Reservations": [{"Instances": [inst]}]}])


class _FakeCW:
    def __init__(self, averages):
        self._averages = averages

    def get_metric_statistics(self, **_):
        return {"Datapoints": [{"Average": a} for a in self._averages]}


class _FakeSession:
    def __init__(self, ec2, cw):
        self._clients = {"ec2": ec2, "cloudwatch": cw}

    def client(self, name, **_):
        return self._clients[name]


def _ec2_idle(averages):
    from finops_audit.checks import ec2 as ec2_check

    launch = datetime.now(timezone.utc) - timedelta(days=60)
    session = _FakeSession(_FakeEC2(launch), _FakeCW(averages))
    return ec2_check.idle(session, REGION, Thresholds())


def test_ec2_idle_flagged_when_cpu_stays_low():
    findings = _ec2_idle([1.2, 2.0, 3.1])
    assert len(findings) == 1
    assert findings[0].monthly_savings_usd == 70.08
    assert "batch-worker" in findings[0].detail


def test_ec2_not_flagged_when_any_day_is_busy():
    assert _ec2_idle([1.0, 40.0, 2.0]) == []


def test_unknown_check_name_raises():
    with pytest.raises(ValueError):
        run_audit(boto3.Session(region_name=REGION), [REGION], ["nope"], CFG)
