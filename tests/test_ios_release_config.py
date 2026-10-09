import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "ios_release", Path(__file__).resolve().parents[1] / "scripts/validate_ios_release.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
public_https, validate = module.public_https, module.validate


def test_rejects_unresolved_or_nonproduction_endpoints():
    for url in (None, "", "$(FITCREW_API_BASE_URL)", "http://api.fitcrew.com",
                "https://127.0.0.1", "https://[::1]", "https://api.local",
                "https://api.example.com", "https://api.test", "https://user:secret@host.com",
                "https://host.com:8443", "https://host.com/#token", "https://host.com\n",
                "https://host.com\\@evil.com", "https://host.com:bad"):
        assert not public_https(url), repr(url)


def test_public_url_shape_is_not_ownership_or_reachability_evidence():
    assert public_https("https://api.fitcrew.com/v1", api=True)
    assert public_https("https://fitcrew.com/privacy?lang=zh")
    assert not public_https("https://api.fitcrew.com/?token=value", api=True)


def test_source_template_cannot_pass_built_release_validation():
    info = {
        "FitCrewAPIBaseURL": "$(FITCREW_API_BASE_URL)",
        "PrivacyPolicyURL": "$(FITCREW_PRIVACY_POLICY_URL)",
        "CFBundleIdentifier": "$(PRODUCT_BUNDLE_IDENTIFIER)",
        "CFBundleShortVersionString": "3.0.0", "CFBundleVersion": "1",
        "NSHealthShareUsageDescription": "Read only after permission",
    }
    assert len(validate(info)) == 3
    info.update(FitCrewAPIBaseURL="https://api.fitcrew.com",
                PrivacyPolicyURL="https://fitcrew.com/privacy",
                CFBundleIdentifier="com.fitcrew.healthbridge")
    assert validate(info) == []
    info["NSAppTransportSecurity"] = {"NSAllowsArbitraryLoads": True}
    assert validate(info) == ["Transport security must not allow arbitrary loads"]
