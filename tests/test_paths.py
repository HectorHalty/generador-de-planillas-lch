from pathlib import Path

from lch_app.paths import output_dir


def test_output_dir_next_to_frozen_exe(monkeypatch, tmp_path: Path) -> None:
    exe = tmp_path / "GeneradorPlanillasLCH.exe"
    exe.write_bytes(b"mz")
    monkeypatch.setattr("lch_app.paths.sys.frozen", True, raising=False)
    monkeypatch.setattr("lch_app.paths.sys.executable", str(exe))
    out = output_dir()
    assert out == tmp_path / ".lch-output"
    assert out.is_dir()
