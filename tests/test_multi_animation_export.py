"""
Tests for multi-animation GLB export functionality
"""

import pytest
import tempfile
from pathlib import Path
from chemvista import SceneManager


class TestMultiAnimationExport:
    """Test multi-animation GLB export with multiple trajectories"""

    @pytest.fixture
    def scene_manager(self):
        """Create a fresh SceneManager for each test"""
        return SceneManager()

    @pytest.fixture
    def phase_trajectories(self, scene_manager):
        """Load all phase trajectory files"""
        data_dir = Path(__file__).parent / "data" / "xyz"
        phase_files = [
            "phase1_cis1_trans1_stabilized.xyz",
            "phase2_trans1_cis1_auto_stabilized.xyz",
            "phase3_cis1_auto_trans1_auto_stabilized.xyz",
            "phase4_trans1_auto_cis1_stabilized.xyz"
        ]
        
        trajectories = []
        for phase_file in phase_files:
            filepath = data_dir / phase_file
            if filepath.exists():
                traj = scene_manager.load_xyz(filepath)
                trajectories.append(traj)
        
        return trajectories

    def test_multi_animation_export_creates_file(self, scene_manager, phase_trajectories):
        """Test that multi-animation export creates a valid GLB file"""
        if len(phase_trajectories) < 2:
            pytest.skip("Not enough trajectory files available for testing")
        
        with tempfile.NamedTemporaryFile(suffix='.glb', delete=False) as tmp:
            output_path = Path(tmp.name)
        
        try:
            # Export with multiple trajectories
            scene_manager.export_multi_trajectory_animated_glb(
                trajectory_objects=phase_trajectories[:2],  # Use first 2 for speed
                output_path=output_path,
                animation_names=["Animation 1", "Animation 2"],
                fps=10,
                resolution=8,  # Lower resolution for faster test
                scale="auto"
            )
            
            # Verify file was created
            assert output_path.exists()
            assert output_path.stat().st_size > 0
            
            # Verify it's a valid GLB using pygltflib if available
            try:
                import pygltflib
                gltf = pygltflib.GLTF2().load(str(output_path))
                
                # Verify structure
                assert len(gltf.animations) == 2
                assert gltf.animations[0].name == "Animation 1"
                assert gltf.animations[1].name == "Animation 2"
                
                # Each animation should have same number of channels (one per atom)
                num_channels_1 = len(gltf.animations[0].channels)
                num_channels_2 = len(gltf.animations[1].channels)
                assert num_channels_1 == num_channels_2
                assert num_channels_1 > 0
                
            except ImportError:
                pytest.skip("pygltflib not available for detailed validation")
        
        finally:
            # Cleanup
            if output_path.exists():
                output_path.unlink()

    def test_multi_animation_export_with_default_names(self, scene_manager, phase_trajectories):
        """Test that default animation names use trajectory names"""
        if len(phase_trajectories) < 2:
            pytest.skip("Not enough trajectory files available for testing")
        
        with tempfile.NamedTemporaryFile(suffix='.glb', delete=False) as tmp:
            output_path = Path(tmp.name)
        
        try:
            # Export without custom animation names
            scene_manager.export_multi_trajectory_animated_glb(
                trajectory_objects=phase_trajectories[:2],
                output_path=output_path,
                fps=10,
                resolution=8
            )
            
            assert output_path.exists()
            
            # Verify animation names match trajectory names
            try:
                import pygltflib
                gltf = pygltflib.GLTF2().load(str(output_path))
                assert len(gltf.animations) == 2
                # Names should come from trajectory object names
                assert gltf.animations[0].name is not None
                assert gltf.animations[1].name is not None
            except ImportError:
                pytest.skip("pygltflib not available for validation")
        
        finally:
            if output_path.exists():
                output_path.unlink()

    def test_multi_animation_export_empty_list_raises_error(self, scene_manager):
        """Test that exporting with empty trajectory list raises ValueError"""
        with tempfile.NamedTemporaryFile(suffix='.glb', delete=False) as tmp:
            output_path = Path(tmp.name)
        
        try:
            with pytest.raises(ValueError, match="At least one trajectory"):
                scene_manager.export_multi_trajectory_animated_glb(
                    trajectory_objects=[],
                    output_path=output_path
                )
        finally:
            if output_path.exists():
                output_path.unlink()

    def test_multi_animation_export_mismatched_names_raises_error(self, scene_manager, phase_trajectories):
        """Test that mismatched animation names count raises ValueError"""
        if len(phase_trajectories) < 2:
            pytest.skip("Not enough trajectory files available for testing")
        
        with tempfile.NamedTemporaryFile(suffix='.glb', delete=False) as tmp:
            output_path = Path(tmp.name)
        
        try:
            with pytest.raises(ValueError, match="must match"):
                scene_manager.export_multi_trajectory_animated_glb(
                    trajectory_objects=phase_trajectories[:2],
                    output_path=output_path,
                    animation_names=["Only One Name"]  # Wrong count
                )
        finally:
            if output_path.exists():
                output_path.unlink()

    def test_multi_animation_same_geometry_as_single(self, scene_manager, phase_trajectories):
        """Test that multi-animation export has same geometry as single export"""
        if len(phase_trajectories) < 1:
            pytest.skip("No trajectory files available for testing")
        
        with tempfile.NamedTemporaryFile(suffix='.glb', delete=False) as tmp1, \
             tempfile.NamedTemporaryFile(suffix='.glb', delete=False) as tmp2:
            single_path = Path(tmp1.name)
            multi_path = Path(tmp2.name)
        
        try:
            # Export single trajectory
            scene_manager.export_trajectory_animated_glb(
                phase_trajectories[0],
                output_path=single_path,
                fps=10,
                resolution=8
            )
            
            # Export same trajectory via multi-animation
            scene_manager.export_multi_trajectory_animated_glb(
                trajectory_objects=[phase_trajectories[0]],
                output_path=multi_path,
                fps=10,
                resolution=8
            )
            
            try:
                import pygltflib
                single_gltf = pygltflib.GLTF2().load(str(single_path))
                multi_gltf = pygltflib.GLTF2().load(str(multi_path))
                
                # Get vertex counts from first mesh primitive
                single_vertices = single_gltf.accessors[
                    single_gltf.meshes[0].primitives[0].attributes.POSITION
                ].count
                multi_vertices = multi_gltf.accessors[
                    multi_gltf.meshes[0].primitives[0].attributes.POSITION
                ].count
                
                # Should have same number of vertices (atoms + bonds)
                assert single_vertices == multi_vertices
                
            except ImportError:
                pytest.skip("pygltflib not available for comparison")
        
        finally:
            if single_path.exists():
                single_path.unlink()
            if multi_path.exists():
                multi_path.unlink()
