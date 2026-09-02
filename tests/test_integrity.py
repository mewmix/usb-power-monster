from pathlib import Path

from usb_power_monster.integrity import mutate_and_verify, prepare_payload, verify_payload


def test_payload_roundtrip(tmp_path: Path):
    p = tmp_path / "payload.bin"
    expected = prepare_payload(p, 1024 * 1024, 1234)
    actual, _, total = verify_payload(p, expected)
    assert actual == expected
    assert total == 1024 * 1024


def test_mutation_remains_verifiable(tmp_path: Path):
    p = tmp_path / "payload.bin"
    prepare_payload(p, 1024 * 1024, 1234)
    expected, written = mutate_and_verify(p, 42)
    actual, _, _ = verify_payload(p, expected)
    assert written == 4096
    assert actual == expected
