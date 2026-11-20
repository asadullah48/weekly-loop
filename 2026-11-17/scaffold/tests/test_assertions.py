import pytest

from preflightkit.assertions import check, validate_requirements
from preflightkit.manifest import build_manifest
from preflightkit.probes import ProbeResult


def manifest_from(*results: ProbeResult) -> dict:
    return build_manifest(list(results))


def test_all_met():
    m = manifest_from(
        ProbeResult("command", "git", True),
        ProbeResult("env", "HOME", True),
    )
    assert check({"commands": ["git"], "env": ["HOME"]}, m) == []


def test_failed_probe_is_unmet():
    m = manifest_from(ProbeResult("command", "git", False, detail="not on PATH"))
    unmet = check({"commands": ["git"]}, m)
    assert len(unmet) == 1
    assert unmet[0].section == "commands"
    assert unmet[0].target == "git"
    assert unmet[0].reason == "not on PATH"


def test_unprobed_requirement_is_unmet():
    unmet = check({"modules": ["numpy"]}, manifest_from())
    assert len(unmet) == 1
    assert unmet[0].reason == "not probed"


def test_network_default_port_matching():
    m = manifest_from(ProbeResult("network", "github.com:443", True))
    assert check({"network": ["github.com"]}, m) == []
    assert check({"network": ["github.com:443"]}, m) == []
    unmet = check({"network": ["github.com:22"]}, m)
    assert len(unmet) == 1 and unmet[0].reason == "not probed"


def test_validate_requirements_rejects_bad_shapes():
    with pytest.raises(ValueError):
        validate_requirements(["git"])
    with pytest.raises(ValueError):
        validate_requirements({"not-a-section": []})
    with pytest.raises(ValueError):
        validate_requirements({"commands": "git"})
    with pytest.raises(ValueError):
        validate_requirements({"commands": [1]})
    validate_requirements({"commands": ["git"]})  # no raise
