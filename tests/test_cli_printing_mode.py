"""Tests for CLI integration with 3D printing mode."""

import pytest
import subprocess
import sys
import pathlib


@pytest.fixture
def sample_xyz_file(tmp_path):
    """Create a sample XYZ file for testing"""
    xyz_file = tmp_path / "test.xyz"
    xyz_content = """2
H2 molecule
H 0.0 0.0 0.0
H 0.74 0.0 0.0
"""
    xyz_file.write_text(xyz_content)
    return xyz_file


class TestCLIPrintingMode:
    """Test CLI with 3D printing mode flags"""

    def test_printing_mode_flag_exists(self):
        """Test that --printing-mode flag is recognized"""
        result = subprocess.run(
            [sys.executable, "-m", "chemvista.cli", "--help"],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0
        assert "--printing-mode" in result.stdout

    def test_printing_resolution_flag_exists(self):
        """Test that --printing-resolution flag is recognized"""
        result = subprocess.run(
            [sys.executable, "-m", "chemvista.cli", "--help"],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0
        assert "--printing-resolution" in result.stdout

    def test_glb_export_with_printing_mode(self, sample_xyz_file, tmp_path):
        """Test GLB export with printing mode flag via CLI"""
        output_file = tmp_path / "output_print.glb"

        result = subprocess.run(
            [
                sys.executable, "-m", "chemvista.cli",
                "--xyz", str(sample_xyz_file),
                "--glb", str(output_file),
                "--printing-mode",
                "--printing-resolution", "32"
            ],
            capture_output=True,
            text=True,
            timeout=30
        )

        assert result.returncode == 0, f"CLI failed: {result.stderr}"
        assert output_file.exists()

    def test_printing_resolution_values(self, sample_xyz_file, tmp_path):
        """Test different printing resolution values"""
        for resolution in [16, 32, 64]:
            output_file = tmp_path / f"output_res_{resolution}.glb"

            result = subprocess.run(
                [
                    sys.executable, "-m", "chemvista.cli",
                    "--xyz", str(sample_xyz_file),
                    "--glb", str(output_file),
                    "--printing-mode",
                    "--printing-resolution", str(resolution)
                ],
                capture_output=True,
                text=True,
                timeout=30
            )

            assert result.returncode == 0
            assert output_file.exists()
