"""
Example: Export multiple trajectory phases as separate animations in one GLB file

This example demonstrates how to export multiple molecular trajectory phases
as separate animations in a single GLB file. This is useful for:
- Comparing different simulation phases side-by-side
- Saving space (one file with 4 animations vs 4 separate files)
- Organizing related animations together
- Viewing in 3D viewers that support animation selection

The resulting GLB file works like models with multiple animations
(e.g., a game character with "walk", "run", "jump" animations).
"""

from pathlib import Path
from chemvista import SceneManager


def main():
    # Initialize scene manager
    scene = SceneManager()
    
    # Load multiple trajectory phases
    # These could be different phases of a reaction, different conformers,
    # or any related molecular trajectories with the same atom count
    data_dir = Path("tests/data/xyz")
    
    print("Loading trajectory phases...")
    trajectories = []
    phase_names = []
    
    for i, filename in enumerate([
        "phase1_cis1_trans1_stabilized.xyz",
        "phase2_trans1_cis1_auto_stabilized.xyz",
        "phase3_cis1_auto_trans1_auto_stabilized.xyz",
        "phase4_trans1_auto_cis1_stabilized.xyz"
    ], 1):
        filepath = data_dir / filename
        if filepath.exists():
            traj = scene.load_xyz(filepath)
            trajectories.append(traj)
            phase_names.append(f"Phase {i}")
            print(f"  Loaded {filename} ({len(traj.children)} frames)")
    
    if not trajectories:
        print("No trajectory files found. Please check the data directory.")
        return
    
    # Export all phases as separate animations in one GLB file
    output_path = "motor_phases_multi_animation.glb"
    
    print(f"\nExporting {len(trajectories)} animations to: {output_path}")
    scene.export_multi_trajectory_animated_glb(
        trajectory_objects=trajectories,
        output_path=output_path,
        animation_names=phase_names,
        fps=10,
        resolution=15,
        scale="auto"  # Auto-scale to fit in viewer
    )
    
    print(f"\n✅ Success! Created {output_path}")
    print(f"\nThis file contains {len(trajectories)} animations:")
    for i, name in enumerate(phase_names, 1):
        print(f"  {i}. {name}")
    
    print("\n📖 How to view:")
    print("  • Windows 3D Viewer: Use animation dropdown to select phase")
    print("  • Online viewers: https://gltf-viewer.donmccurdy.com/")
    print("  • PowerPoint: Insert → 3D Models → From File")
    print("    (Note: PowerPoint may only play first animation)")
    
    # Also demonstrate single-trajectory export for comparison
    print("\n--- For comparison: single trajectory export ---")
    scene.export_trajectory_animated_glb(
        trajectories[0],
        output_path="single_phase.glb",
        fps=10,
        resolution=15,
        scale="auto"
    )
    print("Created single_phase.glb (single animation)")
    
    # Show file size comparison
    multi_size = Path(output_path).stat().st_size / 1024
    single_size = Path("single_phase.glb").stat().st_size / 1024
    print(f"\n📊 File size comparison:")
    print(f"  Multi-animation (4 phases): {multi_size:.1f} KB")
    print(f"  Single animation (1 phase): {single_size:.1f} KB")
    print(f"  4 separate files would be: {single_size * 4:.1f} KB")
    print(f"  Space saved: {(single_size * 4 - multi_size):.1f} KB ({(1 - multi_size/(single_size*4))*100:.0f}%)")


if __name__ == "__main__":
    main()
