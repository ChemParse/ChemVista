"""
Tests for export consistency across different interfaces (CLI, GUI, Python API).

This module verifies that:
1. The same input produces consistent output across different interfaces
2. Parameter changes (colors, sizes, palettes) affect the output consistently
3. Export properties can be verified without comparing binary files

The test strategy uses lightweight "fingerprints" of exported files:

For GLB files:
- Vertex count, face count, mesh count
- Geometry hashes (positions, indices)
- Unique colors (as set of RGBA tuples)
- Bounding box dimensions
- Animation data (for animated exports)

For PNG files:
- Image dimensions (width, height)
- Pixel data hash
- Color statistics (unique colors, dominant colors)
- Non-transparent pixel count

These fingerprints are deterministic for the same input and settings,
allowing us to verify consistency without storing large reference files.

Reference fingerprints are stored in tests/data/reference_fingerprints.json
and can be regenerated with: pytest --generate-fingerprints
"""

import pytest
import pathlib
import tempfile
import struct
import json
import hashlib
import numpy as np
import pyvista as pv
from dataclasses import dataclass
from typing import Dict, Set, Tuple, List, Optional
from chemvista.scene_manager import SceneManager
from chemvista.exporter import Exporter
from chemvista.tree_structure import TreeSignals


# ============================================================================
# Reference fingerprint storage
# ============================================================================

REFERENCE_FINGERPRINTS_FILE = pathlib.Path(__file__).parent / 'data' / 'reference_fingerprints.json'


def load_reference_fingerprints() -> Dict[str, dict]:
    """Load reference fingerprints from JSON file."""
    if not REFERENCE_FINGERPRINTS_FILE.exists():
        return {}
    with open(REFERENCE_FINGERPRINTS_FILE, 'r') as f:
        return json.load(f)


def save_reference_fingerprints(fingerprints: Dict[str, dict]) -> None:
    """Save reference fingerprints to JSON file."""
    REFERENCE_FINGERPRINTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(REFERENCE_FINGERPRINTS_FILE, 'w') as f:
        json.dump(fingerprints, f, indent=2, sort_keys=True)


def pytest_addoption(parser):
    """Add --generate-fingerprints option to pytest."""
    try:
        parser.addoption(
            "--generate-fingerprints",
            action="store_true",
            default=False,
            help="Regenerate reference fingerprints instead of comparing"
        )
    except ValueError:
        # Option already added (e.g., in conftest.py)
        pass


@dataclass
class GLBFingerprint:
    """
    Comprehensive fingerprint of a GLB file for consistency testing.

    This captures enough data to detect changes in:
    - Geometry (vertex positions, face topology)
    - Colors and materials
    - Animation (bones, keyframes, transforms)
    - Scene structure (mesh count, node hierarchy)
    """
    # Basic counts
    vertex_count: int
    face_count: int
    mesh_count: int
    node_count: int

    # Geometry hashes - detect actual position/topology changes
    positions_hash: str  # Hash of all vertex positions
    indices_hash: str    # Hash of all face indices

    # Bounding box
    bbox_min: Tuple[float, float, float]
    bbox_max: Tuple[float, float, float]

    # Color data
    unique_colors: Set[Tuple[int, int, int, int]]  # Set of RGBA tuples
    color_histogram: Dict[str, int]  # Binned color counts

    # Per-mesh info (name -> stats)
    mesh_info: Dict[str, dict]  # {mesh_name: {vertices, faces, bbox, colors}}

    # Animation data
    has_animation: bool
    bone_count: int
    frame_count: int
    animation_duration: float  # Total animation duration in seconds
    keyframe_hash: str  # Hash of keyframe data to detect transform changes

    # Scene structure
    scene_hierarchy_hash: str  # Hash of node parent-child relationships

    # Material info
    material_count: int
    material_hashes: List[str]  # Hash of each material's properties

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        # Convert numpy types to Python native types for JSON serialization
        unique_colors_list = sorted([[int(v) for v in c] for c in self.unique_colors])
        return {
            'vertex_count': int(self.vertex_count),
            'face_count': int(self.face_count),
            'mesh_count': int(self.mesh_count),
            'node_count': int(self.node_count),
            'positions_hash': self.positions_hash,
            'indices_hash': self.indices_hash,
            'bbox_min': [float(v) for v in self.bbox_min],
            'bbox_max': [float(v) for v in self.bbox_max],
            'unique_colors': unique_colors_list,
            'color_histogram': {k: int(v) for k, v in self.color_histogram.items()},
            'mesh_info': {
                name: {
                    k: (int(v) if isinstance(v, (int, np.integer)) else
                        [[int(c) for c in color] for color in v] if k == 'colors' else
                        [float(x) for x in v] if isinstance(v, (list, tuple)) else v)
                    for k, v in info.items()
                }
                for name, info in self.mesh_info.items()
            },
            'has_animation': bool(self.has_animation),
            'bone_count': int(self.bone_count),
            'frame_count': int(self.frame_count),
            'animation_duration': float(self.animation_duration),
            'keyframe_hash': self.keyframe_hash,
            'scene_hierarchy_hash': self.scene_hierarchy_hash,
            'material_count': int(self.material_count),
            'material_hashes': self.material_hashes,
        }

    @classmethod
    def from_dict(cls, d: dict) -> 'GLBFingerprint':
        """Create from dict."""
        return cls(
            vertex_count=d['vertex_count'],
            face_count=d['face_count'],
            mesh_count=d.get('mesh_count', 1),
            node_count=d.get('node_count', 1),
            positions_hash=d.get('positions_hash', ''),
            indices_hash=d.get('indices_hash', ''),
            bbox_min=tuple(d['bbox_min']),
            bbox_max=tuple(d['bbox_max']),
            unique_colors=set(tuple(c) for c in d['unique_colors']),
            color_histogram=d['color_histogram'],
            mesh_info=d.get('mesh_info', {}),
            has_animation=d['has_animation'],
            bone_count=d['bone_count'],
            frame_count=d['frame_count'],
            animation_duration=d.get('animation_duration', 0.0),
            keyframe_hash=d.get('keyframe_hash', ''),
            scene_hierarchy_hash=d.get('scene_hierarchy_hash', ''),
            material_count=d.get('material_count', 0),
            material_hashes=d.get('material_hashes', []),
        )

    def matches(self, other: 'GLBFingerprint',
                check_colors: bool = True,
                check_geometry: bool = True,
                check_animation: bool = True,
                check_hashes: bool = True,
                bbox_tolerance: float = 0.01) -> Tuple[bool, List[str]]:
        """
        Check if two fingerprints match within tolerance.

        Returns:
            Tuple of (matches: bool, differences: List[str])
        """
        differences = []

        if check_geometry:
            if self.vertex_count != other.vertex_count:
                differences.append(f"vertex_count: {self.vertex_count} vs {other.vertex_count}")
            if self.face_count != other.face_count:
                differences.append(f"face_count: {self.face_count} vs {other.face_count}")
            if self.mesh_count != other.mesh_count:
                differences.append(f"mesh_count: {self.mesh_count} vs {other.mesh_count}")
            if self.node_count != other.node_count:
                differences.append(f"node_count: {self.node_count} vs {other.node_count}")

            # Check bounding box within tolerance
            for i, axis in enumerate(['x', 'y', 'z']):
                if abs(self.bbox_min[i] - other.bbox_min[i]) > bbox_tolerance:
                    differences.append(f"bbox_min_{axis}: {self.bbox_min[i]:.4f} vs {other.bbox_min[i]:.4f}")
                if abs(self.bbox_max[i] - other.bbox_max[i]) > bbox_tolerance:
                    differences.append(f"bbox_max_{axis}: {self.bbox_max[i]:.4f} vs {other.bbox_max[i]:.4f}")

            # Check geometry hashes
            if check_hashes:
                if self.positions_hash and other.positions_hash:
                    if self.positions_hash != other.positions_hash:
                        differences.append(f"positions_hash mismatch (geometry changed)")
                if self.indices_hash and other.indices_hash:
                    if self.indices_hash != other.indices_hash:
                        differences.append(f"indices_hash mismatch (topology changed)")

        if check_colors:
            if self.unique_colors != other.unique_colors:
                only_self = self.unique_colors - other.unique_colors
                only_other = other.unique_colors - self.unique_colors
                if only_self:
                    differences.append(f"colors only in self: {sorted(only_self)}")
                if only_other:
                    differences.append(f"colors only in other: {sorted(only_other)}")

            # Check material hashes
            if check_hashes and self.material_hashes and other.material_hashes:
                if set(self.material_hashes) != set(other.material_hashes):
                    differences.append(f"material_hashes mismatch (materials changed)")

        if check_animation:
            if self.has_animation != other.has_animation:
                differences.append(f"has_animation: {self.has_animation} vs {other.has_animation}")
            if self.bone_count != other.bone_count:
                differences.append(f"bone_count: {self.bone_count} vs {other.bone_count}")
            if self.frame_count != other.frame_count:
                differences.append(f"frame_count: {self.frame_count} vs {other.frame_count}")
            if abs(self.animation_duration - other.animation_duration) > 0.001:
                differences.append(f"animation_duration: {self.animation_duration:.3f} vs {other.animation_duration:.3f}")

            # Check keyframe hash
            if check_hashes and self.keyframe_hash and other.keyframe_hash:
                if self.keyframe_hash != other.keyframe_hash:
                    differences.append(f"keyframe_hash mismatch (animation data changed)")

        # Check scene hierarchy
        if check_hashes and self.scene_hierarchy_hash and other.scene_hierarchy_hash:
            if self.scene_hierarchy_hash != other.scene_hierarchy_hash:
                differences.append(f"scene_hierarchy_hash mismatch (scene structure changed)")

        return len(differences) == 0, differences


def parse_glb(filepath: pathlib.Path) -> Tuple[dict, bytes]:
    """
    Parse a GLB file and extract JSON header and binary data.

    Returns:
        Tuple of (gltf_json: dict, binary_data: bytes)
    """
    with open(filepath, 'rb') as f:
        # GLB header
        magic = f.read(4)
        assert magic == b'glTF', f"Invalid GLB magic: {magic}"
        version = struct.unpack('<I', f.read(4))[0]
        assert version == 2, f"Unsupported GLB version: {version}"
        length = struct.unpack('<I', f.read(4))[0]

        # JSON chunk
        json_len = struct.unpack('<I', f.read(4))[0]
        json_type = f.read(4)
        assert json_type == b'JSON', f"Expected JSON chunk, got: {json_type}"
        json_bytes = f.read(json_len)
        gltf = json.loads(json_bytes.decode('utf-8').rstrip())

        # Binary chunk
        bin_len = struct.unpack('<I', f.read(4))[0]
        bin_type = f.read(4)
        assert bin_type == b'BIN\x00', f"Expected BIN chunk, got: {bin_type}"
        bin_data = f.read(bin_len)

    return gltf, bin_data


def _extract_accessor_data(gltf: dict, bin_data: bytes, accessor_idx: int) -> np.ndarray:
    """Extract data from a GLTF accessor."""
    accessor = gltf['accessors'][accessor_idx]
    buffer_view = gltf['bufferViews'][accessor['bufferView']]

    # Get data type
    component_type = accessor['componentType']
    dtype_map = {
        5120: np.int8,
        5121: np.uint8,
        5122: np.int16,
        5123: np.uint16,
        5125: np.uint32,
        5126: np.float32,
    }
    dtype = dtype_map.get(component_type, np.float32)

    # Get component count per element
    type_map = {
        'SCALAR': 1,
        'VEC2': 2,
        'VEC3': 3,
        'VEC4': 4,
        'MAT2': 4,
        'MAT3': 9,
        'MAT4': 16,
    }
    components = type_map.get(accessor['type'], 1)

    # Extract data
    offset = buffer_view.get('byteOffset', 0) + accessor.get('byteOffset', 0)
    count = accessor['count']
    byte_length = count * components * dtype().itemsize

    data = np.frombuffer(bin_data[offset:offset + byte_length], dtype=dtype)
    if components > 1:
        data = data.reshape(count, components)

    return data


def _hash_data(data: np.ndarray, precision: int = 6) -> str:
    """Create a hash of numpy array data with configurable precision for floats."""
    if data.dtype in [np.float32, np.float64]:
        # Round floats to specified precision before hashing
        rounded = np.round(data, precision)
        return hashlib.sha256(rounded.tobytes()).hexdigest()[:16]
    return hashlib.sha256(data.tobytes()).hexdigest()[:16]


def extract_glb_fingerprint(filepath: pathlib.Path) -> GLBFingerprint:
    """
    Extract a comprehensive fingerprint from a GLB file.

    This extracts key properties that should be consistent across
    different export methods for the same input, including:
    - Geometry (positions, indices, per-mesh data)
    - Colors and materials
    - Animation (keyframes, bone transforms)
    - Scene structure
    """
    gltf, bin_data = parse_glb(filepath)

    # Basic counts
    mesh_count = len(gltf.get('meshes', []))
    node_count = len(gltf.get('nodes', []))
    material_count = len(gltf.get('materials', []))

    # Collect all position and index data for hashing
    all_positions = []
    all_indices = []
    total_vertex_count = 0
    total_face_count = 0

    # Global bounding box
    global_bbox_min = [float('inf'), float('inf'), float('inf')]
    global_bbox_max = [float('-inf'), float('-inf'), float('-inf')]

    # Per-mesh info
    mesh_info = {}

    # Collect all colors
    all_unique_colors = set()
    color_histogram = {}

    for mesh_idx, mesh in enumerate(gltf.get('meshes', [])):
        mesh_name = mesh.get('name', f'mesh_{mesh_idx}')
        mesh_vertices = 0
        mesh_faces = 0
        mesh_bbox_min = [float('inf'), float('inf'), float('inf')]
        mesh_bbox_max = [float('-inf'), float('-inf'), float('-inf')]
        mesh_colors = set()

        for prim in mesh.get('primitives', []):
            attrs = prim.get('attributes', {})

            # Extract positions
            if 'POSITION' in attrs:
                pos_data = _extract_accessor_data(gltf, bin_data, attrs['POSITION'])
                all_positions.append(pos_data)
                mesh_vertices += len(pos_data)
                total_vertex_count += len(pos_data)

                # Update bounding box from accessor min/max if available
                pos_accessor = gltf['accessors'][attrs['POSITION']]
                min_vals = pos_accessor.get('min', None)
                max_vals = pos_accessor.get('max', None)
                if min_vals:
                    for i in range(3):
                        mesh_bbox_min[i] = min(mesh_bbox_min[i], min_vals[i])
                        global_bbox_min[i] = min(global_bbox_min[i], min_vals[i])
                if max_vals:
                    for i in range(3):
                        mesh_bbox_max[i] = max(mesh_bbox_max[i], max_vals[i])
                        global_bbox_max[i] = max(global_bbox_max[i], max_vals[i])

            # Extract indices
            if 'indices' in prim:
                idx_data = _extract_accessor_data(gltf, bin_data, prim['indices'])
                all_indices.append(idx_data)
                face_count_prim = len(idx_data) // 3
                mesh_faces += face_count_prim
                total_face_count += face_count_prim

            # Extract colors
            if 'COLOR_0' in attrs:
                color_data = _extract_accessor_data(gltf, bin_data, attrs['COLOR_0'])
                # Handle different color formats
                if color_data.dtype == np.float32:
                    # Convert float [0,1] to uint8 [0,255]
                    color_data = (color_data * 255).astype(np.uint8)
                if color_data.shape[1] == 3:
                    # Add alpha channel if missing
                    alpha = np.full((len(color_data), 1), 255, dtype=np.uint8)
                    color_data = np.hstack([color_data, alpha])

                # Collect unique colors
                for rgba in color_data:
                    color_tuple = tuple(rgba)
                    mesh_colors.add(color_tuple)
                    all_unique_colors.add(color_tuple)

                    # Histogram binning
                    r_bin = (rgba[0] // 16) * 16
                    g_bin = (rgba[1] // 16) * 16
                    b_bin = (rgba[2] // 16) * 16
                    key = f"R{r_bin}_G{g_bin}_B{b_bin}"
                    color_histogram[key] = color_histogram.get(key, 0) + 1

        # Store mesh info
        mesh_info[mesh_name] = {
            'vertices': mesh_vertices,
            'faces': mesh_faces,
            'bbox_min': mesh_bbox_min if mesh_bbox_min[0] != float('inf') else [0, 0, 0],
            'bbox_max': mesh_bbox_max if mesh_bbox_max[0] != float('-inf') else [0, 0, 0],
            'colors': sorted([list(c) for c in mesh_colors])[:10],  # Store up to 10 unique colors
        }

    # Create geometry hashes
    positions_hash = ''
    indices_hash = ''
    if all_positions:
        combined_positions = np.vstack(all_positions) if len(all_positions) > 1 else all_positions[0]
        positions_hash = _hash_data(combined_positions)
    if all_indices:
        combined_indices = np.concatenate(all_indices) if len(all_indices) > 1 else all_indices[0]
        indices_hash = _hash_data(combined_indices)

    # Handle case where no positions found
    if global_bbox_min[0] == float('inf'):
        global_bbox_min = [0.0, 0.0, 0.0]
        global_bbox_max = [0.0, 0.0, 0.0]

    # Animation data
    has_animation = 'animations' in gltf and len(gltf['animations']) > 0
    bone_count = 0
    frame_count = 0
    animation_duration = 0.0
    keyframe_hash = ''

    if 'skins' in gltf and len(gltf['skins']) > 0:
        bone_count = len(gltf['skins'][0].get('joints', []))

    if has_animation:
        anim = gltf['animations'][0]
        all_keyframe_data = []

        for sampler in anim.get('samplers', []):
            # Input accessor (timestamps)
            input_accessor_idx = sampler['input']
            timestamps = _extract_accessor_data(gltf, bin_data, input_accessor_idx)
            frame_count = max(frame_count, len(timestamps))

            # Get duration from max timestamp
            if len(timestamps) > 0:
                animation_duration = max(animation_duration, float(timestamps.max()))

            # Output accessor (transforms)
            output_accessor_idx = sampler['output']
            transforms = _extract_accessor_data(gltf, bin_data, output_accessor_idx)
            all_keyframe_data.append(transforms.flatten())

        # Create keyframe hash
        if all_keyframe_data:
            combined_keyframes = np.concatenate(all_keyframe_data)
            keyframe_hash = _hash_data(combined_keyframes)

    # Scene hierarchy hash
    hierarchy_data = []
    for node_idx, node in enumerate(gltf.get('nodes', [])):
        children = node.get('children', [])
        hierarchy_data.append((node_idx, tuple(sorted(children))))
    scene_hierarchy_hash = hashlib.sha256(str(sorted(hierarchy_data)).encode()).hexdigest()[:16]

    # Material hashes
    material_hashes = []
    for mat in gltf.get('materials', []):
        # Hash relevant material properties
        mat_data = {
            'name': mat.get('name', ''),
            'doubleSided': mat.get('doubleSided', False),
            'alphaMode': mat.get('alphaMode', 'OPAQUE'),
            'alphaCutoff': mat.get('alphaCutoff', 0.5),
        }
        # Include PBR properties if present
        pbr = mat.get('pbrMetallicRoughness', {})
        if pbr:
            mat_data['baseColorFactor'] = pbr.get('baseColorFactor', [1, 1, 1, 1])
            mat_data['metallicFactor'] = pbr.get('metallicFactor', 1.0)
            mat_data['roughnessFactor'] = pbr.get('roughnessFactor', 1.0)
        mat_hash = hashlib.sha256(json.dumps(mat_data, sort_keys=True).encode()).hexdigest()[:16]
        material_hashes.append(mat_hash)

    return GLBFingerprint(
        vertex_count=total_vertex_count,
        face_count=total_face_count,
        mesh_count=mesh_count,
        node_count=node_count,
        positions_hash=positions_hash,
        indices_hash=indices_hash,
        bbox_min=tuple(global_bbox_min),
        bbox_max=tuple(global_bbox_max),
        unique_colors=all_unique_colors,
        color_histogram=color_histogram,
        mesh_info=mesh_info,
        has_animation=has_animation,
        bone_count=bone_count,
        frame_count=frame_count,
        animation_duration=animation_duration,
        keyframe_hash=keyframe_hash,
        scene_hierarchy_hash=scene_hierarchy_hash,
        material_count=material_count,
        material_hashes=material_hashes,
    )


# ============================================================================
# PNG Fingerprinting
# ============================================================================

@dataclass
class PNGFingerprint:
    """
    Fingerprint of a PNG screenshot for consistency testing.

    This captures enough data to detect changes in:
    - Image dimensions
    - Pixel content (via hash)
    - Color distribution
    - Transparency
    """
    # Image dimensions
    width: int
    height: int

    # Content hash - detect any pixel changes
    pixel_hash: str

    # Color statistics
    unique_color_count: int
    dominant_colors: List[Tuple[int, int, int, int]]  # Top N colors by frequency

    # Transparency info
    has_transparency: bool
    non_transparent_pixel_count: int
    transparent_pixel_ratio: float

    # Color histogram (binned)
    color_histogram: Dict[str, int]

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dictionary."""
        return {
            'width': self.width,
            'height': self.height,
            'pixel_hash': self.pixel_hash,
            'unique_color_count': self.unique_color_count,
            'dominant_colors': [list(c) for c in self.dominant_colors],
            'has_transparency': self.has_transparency,
            'non_transparent_pixel_count': self.non_transparent_pixel_count,
            'transparent_pixel_ratio': self.transparent_pixel_ratio,
            'color_histogram': self.color_histogram,
        }

    @classmethod
    def from_dict(cls, d: dict) -> 'PNGFingerprint':
        """Create from dictionary."""
        return cls(
            width=d['width'],
            height=d['height'],
            pixel_hash=d['pixel_hash'],
            unique_color_count=d['unique_color_count'],
            dominant_colors=[tuple(c) for c in d['dominant_colors']],
            has_transparency=d['has_transparency'],
            non_transparent_pixel_count=d['non_transparent_pixel_count'],
            transparent_pixel_ratio=d['transparent_pixel_ratio'],
            color_histogram=d['color_histogram'],
        )

    def matches(
        self,
        other: 'PNGFingerprint',
        check_hash: bool = True,
        check_colors: bool = True,
        dimension_tolerance: int = 0,
    ) -> Tuple[bool, List[str]]:
        """
        Compare this fingerprint to another.

        Args:
            other: The fingerprint to compare against
            check_hash: If True, compare pixel hash (exact match)
            check_colors: If True, compare color statistics
            dimension_tolerance: Allowed difference in dimensions

        Returns:
            Tuple of (matches: bool, differences: List[str])
        """
        differences = []

        # Check dimensions
        if abs(self.width - other.width) > dimension_tolerance:
            differences.append(f"width: {self.width} vs {other.width}")
        if abs(self.height - other.height) > dimension_tolerance:
            differences.append(f"height: {self.height} vs {other.height}")

        # Check pixel hash (exact content match)
        if check_hash:
            if self.pixel_hash != other.pixel_hash:
                differences.append("pixel_hash mismatch (image content changed)")

        # Check color statistics
        if check_colors:
            if self.unique_color_count != other.unique_color_count:
                differences.append(
                    f"unique_color_count: {self.unique_color_count} vs {other.unique_color_count}"
                )
            if self.has_transparency != other.has_transparency:
                differences.append(
                    f"has_transparency: {self.has_transparency} vs {other.has_transparency}"
                )
            # Allow small tolerance for transparent pixel ratio due to antialiasing
            if abs(self.transparent_pixel_ratio - other.transparent_pixel_ratio) > 0.01:
                differences.append(
                    f"transparent_pixel_ratio: {self.transparent_pixel_ratio:.3f} vs {other.transparent_pixel_ratio:.3f}"
                )

        return len(differences) == 0, differences


def extract_png_fingerprint(filepath: pathlib.Path) -> PNGFingerprint:
    """
    Extract a fingerprint from a PNG file.

    Args:
        filepath: Path to the PNG file

    Returns:
        PNGFingerprint containing image statistics
    """
    from PIL import Image

    with Image.open(filepath) as img:
        # Ensure RGBA mode for consistent processing
        if img.mode != 'RGBA':
            img = img.convert('RGBA')

        width, height = img.size
        pixels = np.array(img)

        # Compute pixel hash
        pixel_hash = hashlib.sha256(pixels.tobytes()).hexdigest()[:16]

        # Flatten to list of RGBA tuples
        flat_pixels = pixels.reshape(-1, 4)

        # Count unique colors
        unique_colors = set(map(tuple, flat_pixels))
        unique_color_count = len(unique_colors)

        # Find dominant colors (most frequent)
        color_counts = {}
        for pixel in flat_pixels:
            color = tuple(pixel)
            color_counts[color] = color_counts.get(color, 0) + 1

        sorted_colors = sorted(color_counts.items(), key=lambda x: -x[1])
        dominant_colors = [color for color, count in sorted_colors[:10]]

        # Transparency analysis
        alpha_channel = flat_pixels[:, 3]
        transparent_pixels = np.sum(alpha_channel < 255)
        fully_transparent = np.sum(alpha_channel == 0)
        non_transparent = len(alpha_channel) - fully_transparent
        has_transparency = transparent_pixels > 0
        transparent_ratio = fully_transparent / len(alpha_channel)

        # Color histogram (bin colors for comparison)
        color_histogram = {}
        for pixel in flat_pixels:
            # Bin to reduce granularity (32 bins per channel)
            r_bin = pixel[0] // 8
            g_bin = pixel[1] // 8
            b_bin = pixel[2] // 8
            a_bin = pixel[3] // 64  # 4 alpha bins
            bin_key = f"{r_bin}_{g_bin}_{b_bin}_{a_bin}"
            color_histogram[bin_key] = color_histogram.get(bin_key, 0) + 1

        return PNGFingerprint(
            width=width,
            height=height,
            pixel_hash=pixel_hash,
            unique_color_count=unique_color_count,
            dominant_colors=dominant_colors,
            has_transparency=has_transparency,
            non_transparent_pixel_count=non_transparent,
            transparent_pixel_ratio=transparent_ratio,
            color_histogram=color_histogram,
        )


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def signals(qtbot):
    """Create TreeSignals for testing."""
    return TreeSignals()


@pytest.fixture
def scene_manager_factory(test_plotter):
    """Factory to create fresh SceneManager instances."""
    managers = []

    def _create():
        signals = TreeSignals()
        manager = SceneManager(tree_signals=signals)
        manager.plotter = test_plotter
        managers.append(manager)
        return manager

    yield _create

    # Cleanup not needed for SceneManager


@pytest.fixture
def scene_manager(scene_manager_factory):
    """Create a SceneManager for testing."""
    return scene_manager_factory()


@pytest.fixture
def temp_glb():
    """Create a temporary GLB file path."""
    with tempfile.NamedTemporaryFile(suffix='.glb', delete=False) as tmp:
        filepath = pathlib.Path(tmp.name)
    yield filepath
    filepath.unlink(missing_ok=True)


@pytest.fixture
def temp_glb_pair():
    """Create two temporary GLB file paths for comparison."""
    paths = []
    for _ in range(2):
        with tempfile.NamedTemporaryFile(suffix='.glb', delete=False) as tmp:
            paths.append(pathlib.Path(tmp.name))
    yield tuple(paths)
    for p in paths:
        p.unlink(missing_ok=True)


@pytest.fixture
def temp_png():
    """Create a temporary PNG file path."""
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
        filepath = pathlib.Path(tmp.name)
    yield filepath
    filepath.unlink(missing_ok=True)


@pytest.fixture
def temp_png_pair():
    """Create two temporary PNG file paths for comparison."""
    paths = []
    for _ in range(2):
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            paths.append(pathlib.Path(tmp.name))
    yield tuple(paths)
    for p in paths:
        p.unlink(missing_ok=True)


# ============================================================================
# Test: Same input produces same output (determinism)
# ============================================================================

class TestExportDeterminism:
    """Test that repeated exports produce identical results."""

    def test_static_export_deterministic(self, scene_manager_factory, test_files, temp_glb_pair):
        """Exporting the same molecule twice should produce identical fingerprints."""
        path1, path2 = temp_glb_pair

        # First export
        sm1 = scene_manager_factory()
        sm1.load_xyz(test_files['molecule_1'])
        exporter1 = Exporter(sm1)
        exporter1.export_glb(path1)
        fp1 = extract_glb_fingerprint(path1)

        # Second export with fresh scene manager
        sm2 = scene_manager_factory()
        sm2.load_xyz(test_files['molecule_1'])
        exporter2 = Exporter(sm2)
        exporter2.export_glb(path2)
        fp2 = extract_glb_fingerprint(path2)

        # Compare
        matches, diffs = fp1.matches(fp2)
        assert matches, f"Export not deterministic: {diffs}"

    def test_animated_export_deterministic(self, scene_manager_factory, test_files, temp_glb_pair):
        """Exporting the same trajectory twice should produce identical fingerprints."""
        path1, path2 = temp_glb_pair

        # First export
        sm1 = scene_manager_factory()
        traj_obj1 = sm1.load_xyz(test_files['trajectory'])
        exporter1 = Exporter(sm1)
        exporter1.export_trajectory_animated_glb(traj_obj1, path1, fps=10, resolution=8)
        fp1 = extract_glb_fingerprint(path1)

        # Second export with fresh scene manager
        sm2 = scene_manager_factory()
        traj_obj2 = sm2.load_xyz(test_files['trajectory'])
        exporter2 = Exporter(sm2)
        exporter2.export_trajectory_animated_glb(traj_obj2, path2, fps=10, resolution=8)
        fp2 = extract_glb_fingerprint(path2)

        # Compare
        matches, diffs = fp1.matches(fp2)
        assert matches, f"Animated export not deterministic: {diffs}"

    @pytest.mark.screenshot
    def test_png_screenshot_deterministic(self, scene_manager_factory, test_files, temp_png_pair):
        """Taking the same screenshot twice should produce identical images."""
        path1, path2 = temp_png_pair

        # First screenshot - create fresh plotter
        sm1 = scene_manager_factory()
        sm1.load_xyz(test_files['molecule_1'])
        plotter1 = pv.Plotter(off_screen=True)
        sm1.render(plotter=plotter1)
        plotter1.screenshot(str(path1))
        plotter1.close()
        fp1 = extract_png_fingerprint(path1)

        # Second screenshot with fresh scene manager and plotter
        sm2 = scene_manager_factory()
        sm2.load_xyz(test_files['molecule_1'])
        plotter2 = pv.Plotter(off_screen=True)
        sm2.render(plotter=plotter2)
        plotter2.screenshot(str(path2))
        plotter2.close()
        fp2 = extract_png_fingerprint(path2)

        # Compare
        matches, diffs = fp1.matches(fp2)
        assert matches, f"PNG screenshot not deterministic: {diffs}"


# ============================================================================
# Test: PNG Screenshot exports
# ============================================================================

@pytest.mark.screenshot
class TestPNGExport:
    """Test PNG screenshot export functionality."""

    def test_png_screenshot_creates_file(self, scene_manager_factory, test_files, temp_png):
        """PNG screenshot should create a valid image file."""
        sm = scene_manager_factory()
        sm.load_xyz(test_files['molecule_1'])

        plotter = pv.Plotter(off_screen=True)
        sm.render(plotter=plotter)
        plotter.screenshot(str(temp_png))
        plotter.close()

        assert temp_png.exists()
        fp = extract_png_fingerprint(temp_png)
        assert fp.width > 0
        assert fp.height > 0

    def test_png_screenshot_has_content(self, scene_manager_factory, test_files, temp_png):
        """PNG screenshot should contain rendered molecule (not just background)."""
        sm = scene_manager_factory()
        sm.load_xyz(test_files['molecule_1'])

        plotter = pv.Plotter(off_screen=True)
        sm.render(plotter=plotter)
        plotter.screenshot(str(temp_png))
        plotter.close()

        fp = extract_png_fingerprint(temp_png)
        # Should have multiple colors (not just single background color)
        assert fp.unique_color_count > 1, "Screenshot appears to be a solid color"

    def test_png_palette_affects_colors(self, scene_manager_factory, test_files, temp_png_pair):
        """Different palettes should produce different colors in screenshots."""
        path1, path2 = temp_png_pair

        # Screenshot with default palette
        sm1 = scene_manager_factory()
        sm1.load_xyz(test_files['molecule_1'])
        plotter1 = pv.Plotter(off_screen=True)
        sm1.render(plotter=plotter1)
        plotter1.screenshot(str(path1))
        plotter1.close()
        fp1 = extract_png_fingerprint(path1)

        # Screenshot with PowerPoint palette
        sm2 = scene_manager_factory()
        sm2.load_xyz(test_files['molecule_1'])
        sm2.set_palette('powerpoint')
        plotter2 = pv.Plotter(off_screen=True)
        sm2.render(plotter=plotter2)
        plotter2.screenshot(str(path2))
        plotter2.close()
        fp2 = extract_png_fingerprint(path2)

        # Pixel hashes should differ (different colors)
        assert fp1.pixel_hash != fp2.pixel_hash, "Different palettes should produce different images"

    def test_png_transparent_background(self, scene_manager_factory, test_files, temp_png):
        """PNG screenshot with transparent background should have transparency."""
        sm = scene_manager_factory()
        sm.load_xyz(test_files['molecule_1'])

        plotter = pv.Plotter(off_screen=True)
        sm.render(plotter=plotter)
        plotter.set_background([0, 0, 0, 0])  # Transparent background
        plotter.screenshot(str(temp_png), transparent_background=True)
        plotter.close()

        fp = extract_png_fingerprint(temp_png)
        assert fp.has_transparency, "Screenshot with transparent background should have transparency"
        assert fp.transparent_pixel_ratio > 0, "Should have some transparent pixels"

    def test_png_window_size_affects_dimensions(self, scene_manager_factory, test_files, temp_png_pair):
        """Different window sizes should produce different image dimensions."""
        path1, path2 = temp_png_pair

        # Small window
        sm1 = scene_manager_factory()
        sm1.load_xyz(test_files['molecule_1'])
        plotter1 = pv.Plotter(off_screen=True, window_size=(400, 300))
        sm1.render(plotter=plotter1)
        plotter1.screenshot(str(path1))
        plotter1.close()
        fp1 = extract_png_fingerprint(path1)

        # Larger window
        sm2 = scene_manager_factory()
        sm2.load_xyz(test_files['molecule_1'])
        plotter2 = pv.Plotter(off_screen=True, window_size=(800, 600))
        sm2.render(plotter=plotter2)
        plotter2.screenshot(str(path2))
        plotter2.close()
        fp2 = extract_png_fingerprint(path2)

        # Dimensions should differ
        assert fp1.width != fp2.width or fp1.height != fp2.height, \
            "Different window sizes should produce different image dimensions"


# ============================================================================
# Test: Parameter changes affect output correctly
# ============================================================================

class TestParameterEffects:
    """Test that parameter changes correctly affect export output."""

    def test_palette_changes_colors(self, scene_manager_factory, test_files, temp_glb_pair):
        """Different palettes should produce different colors in export."""
        path1, path2 = temp_glb_pair

        # Export with default palette
        sm1 = scene_manager_factory()
        sm1.load_xyz(test_files['molecule_1'])
        exporter1 = Exporter(sm1)
        exporter1.export_glb(path1)
        fp1 = extract_glb_fingerprint(path1)

        # Export with CPK palette
        sm2 = scene_manager_factory()
        sm2.load_xyz(test_files['molecule_1'])
        sm2.set_palette('cpk')
        exporter2 = Exporter(sm2)
        exporter2.export_glb(path2)
        fp2 = extract_glb_fingerprint(path2)

        # Colors should be different
        assert fp1.unique_colors != fp2.unique_colors, \
            "Different palettes should produce different colors"

        # But geometry should be the same
        matches, diffs = fp1.matches(fp2, check_colors=False)
        assert matches, f"Geometry changed unexpectedly: {diffs}"

    def test_custom_color_affects_export(self, scene_manager_factory, test_files, temp_glb_pair):
        """Custom element colors should appear in export."""
        path1, path2 = temp_glb_pair

        # Export with default colors
        sm1 = scene_manager_factory()
        sm1.load_xyz(test_files['molecule_1'])
        exporter1 = Exporter(sm1)
        exporter1.export_glb(path1)
        fp1 = extract_glb_fingerprint(path1)

        # Export with red carbon - update only C while keeping other settings
        sm2 = scene_manager_factory()
        sm2.load_xyz(test_files['molecule_1'])
        # Update just the carbon color in existing settings
        sm2.molecule_renderer.atoms_settings['C'] = {'color': [255, 0, 0], 'radius': 0.16}
        exporter2 = Exporter(sm2)
        exporter2.export_glb(path2)
        fp2 = extract_glb_fingerprint(path2)

        # Red color should be present
        has_red = any(c[0] == 255 and c[1] == 0 and c[2] == 0
                      for c in fp2.unique_colors)
        assert has_red, "Red color not found in export with red carbon setting"

        # And should NOT be in the default export
        has_red_default = any(c[0] == 255 and c[1] == 0 and c[2] == 0
                              for c in fp1.unique_colors)
        assert not has_red_default, "Red color unexpectedly in default export"

    def test_resolution_affects_vertex_count(self, scene_manager_factory, test_files, temp_glb_pair):
        """Higher resolution should produce more vertices."""
        path1, path2 = temp_glb_pair

        # Export with low resolution
        sm1 = scene_manager_factory()
        traj_obj1 = sm1.load_xyz(test_files['trajectory'])
        exporter1 = Exporter(sm1)
        exporter1.export_trajectory_animated_glb(traj_obj1, path1, resolution=6)
        fp1 = extract_glb_fingerprint(path1)

        # Export with high resolution
        sm2 = scene_manager_factory()
        traj_obj2 = sm2.load_xyz(test_files['trajectory'])
        exporter2 = Exporter(sm2)
        exporter2.export_trajectory_animated_glb(traj_obj2, path2, resolution=12)
        fp2 = extract_glb_fingerprint(path2)

        # Higher resolution should have more vertices
        assert fp2.vertex_count > fp1.vertex_count, \
            f"Higher resolution should have more vertices: {fp1.vertex_count} vs {fp2.vertex_count}"

    def test_fps_affects_animation_timing(self, scene_manager_factory, test_files, temp_glb_pair):
        """FPS parameter should be reflected in animation (frame count stays same)."""
        path1, path2 = temp_glb_pair

        # Export with 10 fps
        sm1 = scene_manager_factory()
        traj_obj1 = sm1.load_xyz(test_files['trajectory'])
        exporter1 = Exporter(sm1)
        exporter1.export_trajectory_animated_glb(traj_obj1, path1, fps=10)
        fp1 = extract_glb_fingerprint(path1)

        # Export with 30 fps
        sm2 = scene_manager_factory()
        traj_obj2 = sm2.load_xyz(test_files['trajectory'])
        exporter2 = Exporter(sm2)
        exporter2.export_trajectory_animated_glb(traj_obj2, path2, fps=30)
        fp2 = extract_glb_fingerprint(path2)

        # Frame count should be the same (fps affects timing, not frame count)
        assert fp1.frame_count == fp2.frame_count, \
            f"Frame count should be same: {fp1.frame_count} vs {fp2.frame_count}"

    def test_palette_affects_animated_export(self, scene_manager_factory, test_files, temp_glb_pair):
        """Palette should affect animated exports too."""
        path1, path2 = temp_glb_pair

        # Export with default palette
        sm1 = scene_manager_factory()
        traj_obj1 = sm1.load_xyz(test_files['trajectory'])
        exporter1 = Exporter(sm1)
        exporter1.export_trajectory_animated_glb(traj_obj1, path1, resolution=8)
        fp1 = extract_glb_fingerprint(path1)

        # Export with powerpoint palette (darker colors)
        sm2 = scene_manager_factory()
        traj_obj2 = sm2.load_xyz(test_files['trajectory'])
        sm2.set_palette('powerpoint')
        exporter2 = Exporter(sm2)
        exporter2.export_trajectory_animated_glb(traj_obj2, path2, resolution=8)
        fp2 = extract_glb_fingerprint(path2)

        # Colors should be different
        assert fp1.unique_colors != fp2.unique_colors, \
            "Palette should affect animated export colors"

        # But animation properties should be the same
        assert fp1.bone_count == fp2.bone_count
        assert fp1.frame_count == fp2.frame_count


# ============================================================================
# Test: Python API consistency with CLI
# ============================================================================

class TestAPIConsistency:
    """Test that Python API produces same results as CLI would."""

    def test_python_api_export_produces_valid_glb(self, scene_manager, test_files, temp_glb):
        """Python API export should produce valid GLB."""
        scene_manager.load_xyz(test_files['molecule_1'])
        exporter = Exporter(scene_manager)
        exporter.export_glb(temp_glb)

        # Should be parseable
        fp = extract_glb_fingerprint(temp_glb)

        assert fp.vertex_count > 0
        assert fp.face_count > 0
        assert len(fp.unique_colors) > 0

    def test_scene_manager_export_method_matches_exporter(self, scene_manager_factory, test_files, temp_glb_pair):
        """SceneManager.export_to_glb should produce same result as Exporter."""
        path1, path2 = temp_glb_pair

        # Export using SceneManager method
        sm1 = scene_manager_factory()
        sm1.load_xyz(test_files['molecule_1'])
        sm1.export_to_glb(path1)
        fp1 = extract_glb_fingerprint(path1)

        # Export using Exporter directly
        sm2 = scene_manager_factory()
        sm2.load_xyz(test_files['molecule_1'])
        exporter = Exporter(sm2)
        exporter.export_glb(path2)
        fp2 = extract_glb_fingerprint(path2)

        # Should be identical
        matches, diffs = fp1.matches(fp2)
        assert matches, f"SceneManager and Exporter produce different results: {diffs}"


# ============================================================================
# Test: Export fingerprint structure validation
# ============================================================================

class TestFingerprintValidation:
    """Test the fingerprint extraction and comparison utilities."""

    def test_fingerprint_serialization(self, scene_manager, test_files, temp_glb):
        """Fingerprint should be serializable and deserializable."""
        scene_manager.load_xyz(test_files['molecule_1'])
        exporter = Exporter(scene_manager)
        exporter.export_glb(temp_glb)

        fp1 = extract_glb_fingerprint(temp_glb)

        # Serialize and deserialize
        fp_dict = fp1.to_dict()
        fp2 = GLBFingerprint.from_dict(fp_dict)

        # Should match
        matches, diffs = fp1.matches(fp2)
        assert matches, f"Serialization roundtrip failed: {diffs}"

    def test_fingerprint_detects_color_differences(self, scene_manager_factory, test_files, temp_glb_pair):
        """Fingerprint comparison should detect color differences."""
        path1, path2 = temp_glb_pair

        # Two different color exports
        sm1 = scene_manager_factory()
        sm1.load_xyz(test_files['molecule_1'])
        exporter1 = Exporter(sm1)
        exporter1.export_glb(path1)
        fp1 = extract_glb_fingerprint(path1)

        sm2 = scene_manager_factory()
        sm2.load_xyz(test_files['molecule_1'])
        # Update just the carbon color in existing settings
        sm2.molecule_renderer.atoms_settings['C'] = {'color': [0, 255, 0], 'radius': 0.16}
        exporter2 = Exporter(sm2)
        exporter2.export_glb(path2)
        fp2 = extract_glb_fingerprint(path2)

        # Should detect difference
        matches, diffs = fp1.matches(fp2, check_colors=True, check_geometry=False)
        assert not matches, "Should detect color differences"
        assert any('colors' in d for d in diffs)

    def test_fingerprint_animation_detection(self, scene_manager_factory, test_files, temp_glb_pair):
        """Fingerprint should correctly detect animation presence."""
        path_static, path_animated = temp_glb_pair

        # Static export
        sm1 = scene_manager_factory()
        sm1.load_xyz(test_files['molecule_1'])
        exporter1 = Exporter(sm1)
        exporter1.export_glb(path_static)
        fp_static = extract_glb_fingerprint(path_static)

        # Animated export
        sm2 = scene_manager_factory()
        traj_obj = sm2.load_xyz(test_files['trajectory'])
        exporter2 = Exporter(sm2)
        exporter2.export_trajectory_animated_glb(traj_obj, path_animated)
        fp_animated = extract_glb_fingerprint(path_animated)

        assert not fp_static.has_animation, "Static export should not have animation"
        assert fp_animated.has_animation, "Trajectory export should have animation"
        assert fp_animated.bone_count > 0, "Animated export should have bones"
        assert fp_animated.frame_count > 1, "Animated export should have multiple frames"


# ============================================================================
# Test: Specific color verification
# ============================================================================

class TestColorVerification:
    """Test specific color values in exports."""

    def test_default_carbon_color(self, scene_manager, test_files, temp_glb):
        """Default carbon should be gray."""
        scene_manager.load_xyz(test_files['molecule_1'])
        exporter = Exporter(scene_manager)
        exporter.export_glb(temp_glb)
        fp = extract_glb_fingerprint(temp_glb)

        # Default carbon is [144, 144, 144] in chemvista palette
        has_default_gray = any(
            c[0] == 144 and c[1] == 144 and c[2] == 144
            for c in fp.unique_colors
        )
        assert has_default_gray, f"Default gray carbon not found. Colors: {sorted(fp.unique_colors)}"

    def test_powerpoint_palette_darker_carbon(self, scene_manager, test_files, temp_glb):
        """PowerPoint palette should have darker carbon."""
        scene_manager.load_xyz(test_files['molecule_1'])
        scene_manager.set_palette('powerpoint')
        exporter = Exporter(scene_manager)
        exporter.export_glb(temp_glb)
        fp = extract_glb_fingerprint(temp_glb)

        # PowerPoint carbon is [40, 40, 40]
        has_dark_carbon = any(
            c[0] == 40 and c[1] == 40 and c[2] == 40
            for c in fp.unique_colors
        )
        assert has_dark_carbon, f"Dark carbon not found. Colors: {sorted(fp.unique_colors)}"

    def test_explicit_red_carbon(self, scene_manager, test_files, temp_glb):
        """Explicitly set red carbon should appear in export."""
        scene_manager.load_xyz(test_files['molecule_1'])
        # Update just the carbon color in existing settings
        scene_manager.molecule_renderer.atoms_settings['C'] = {'color': [255, 0, 0], 'radius': 0.16}
        exporter = Exporter(scene_manager)
        exporter.export_glb(temp_glb)
        fp = extract_glb_fingerprint(temp_glb)

        has_red = any(
            c[0] == 255 and c[1] == 0 and c[2] == 0
            for c in fp.unique_colors
        )
        assert has_red, f"Red carbon not found. Colors: {sorted(fp.unique_colors)}"


# ============================================================================
# Test: Bond color consistency
# ============================================================================

class TestBondColorConsistency:
    """Test that bond colors are consistent across exports."""

    def test_default_bond_color(self, scene_manager, test_files, temp_glb):
        """Default bonds should be light gray."""
        scene_manager.load_xyz(test_files['molecule_1'])
        exporter = Exporter(scene_manager)
        exporter.export_glb(temp_glb)
        fp = extract_glb_fingerprint(temp_glb)

        # Default bond color is [211, 211, 211]
        has_bond_gray = any(
            c[0] == 211 and c[1] == 211 and c[2] == 211
            for c in fp.unique_colors
        )
        assert has_bond_gray, f"Default bond gray not found. Colors: {sorted(fp.unique_colors)}"

    def test_powerpoint_bond_color(self, scene_manager, test_files, temp_glb):
        """PowerPoint palette should have darker bonds."""
        scene_manager.load_xyz(test_files['molecule_1'])
        scene_manager.set_palette('powerpoint')
        exporter = Exporter(scene_manager)
        exporter.export_glb(temp_glb)
        fp = extract_glb_fingerprint(temp_glb)

        # PowerPoint bond color is [70, 70, 80]
        has_dark_bonds = any(
            c[0] == 70 and c[1] == 70 and c[2] == 80
            for c in fp.unique_colors
        )
        assert has_dark_bonds, f"Dark bonds not found. Colors: {sorted(fp.unique_colors)}"


# ============================================================================
# Test: Reference fingerprint comparison (version stability)
# ============================================================================

class TestReferenceFingerprints:
    """
    Compare current exports against stored reference fingerprints.

    These tests ensure that export behavior remains stable across versions.
    If the export format changes intentionally, regenerate references with:
        pytest tests/test_export_consistency.py --generate-fingerprints -k reference

    Reference fingerprints are stored in tests/data/reference_fingerprints.json
    """

    # Define which exports to track as references
    REFERENCE_CONFIGS = {
        'molecule_default': {
            'file_key': 'molecule_1',
            'palette': None,
            'animated': False,
        },
        'molecule_cpk': {
            'file_key': 'molecule_1',
            'palette': 'cpk',
            'animated': False,
        },
        'molecule_powerpoint': {
            'file_key': 'molecule_1',
            'palette': 'powerpoint',
            'animated': False,
        },
        'trajectory_default': {
            'file_key': 'trajectory',
            'palette': None,
            'animated': True,
            'resolution': 8,
        },
        'trajectory_powerpoint': {
            'file_key': 'trajectory',
            'palette': 'powerpoint',
            'animated': True,
            'resolution': 8,
        },
    }

    def _generate_fingerprint(self, scene_manager_factory, test_files, config, temp_glb):
        """Generate a fingerprint based on config."""
        sm = scene_manager_factory()

        if config['animated']:
            obj = sm.load_xyz(test_files[config['file_key']])
        else:
            obj = sm.load_xyz(test_files[config['file_key']])

        if config.get('palette'):
            sm.set_palette(config['palette'])

        exporter = Exporter(sm)

        if config['animated']:
            exporter.export_trajectory_animated_glb(
                obj, temp_glb,
                resolution=config.get('resolution', 8)
            )
        else:
            exporter.export_glb(temp_glb)

        return extract_glb_fingerprint(temp_glb)

    def test_reference_molecule_default(self, request, scene_manager_factory, test_files, temp_glb):
        """Test molecule export with default palette against reference."""
        self._run_reference_test(
            'molecule_default', request, scene_manager_factory, test_files, temp_glb
        )

    def test_reference_molecule_cpk(self, request, scene_manager_factory, test_files, temp_glb):
        """Test molecule export with CPK palette against reference."""
        self._run_reference_test(
            'molecule_cpk', request, scene_manager_factory, test_files, temp_glb
        )

    def test_reference_molecule_powerpoint(self, request, scene_manager_factory, test_files, temp_glb):
        """Test molecule export with PowerPoint palette against reference."""
        self._run_reference_test(
            'molecule_powerpoint', request, scene_manager_factory, test_files, temp_glb
        )

    def test_reference_trajectory_default(self, request, scene_manager_factory, test_files, temp_glb):
        """Test trajectory export with default palette against reference."""
        self._run_reference_test(
            'trajectory_default', request, scene_manager_factory, test_files, temp_glb
        )

    def test_reference_trajectory_powerpoint(self, request, scene_manager_factory, test_files, temp_glb):
        """Test trajectory export with PowerPoint palette against reference."""
        self._run_reference_test(
            'trajectory_powerpoint', request, scene_manager_factory, test_files, temp_glb
        )

    def _run_reference_test(self, ref_name, request, scene_manager_factory, test_files, temp_glb):
        """Run a reference comparison test."""
        config = self.REFERENCE_CONFIGS[ref_name]
        fp = self._generate_fingerprint(scene_manager_factory, test_files, config, temp_glb)

        # Check if we should generate references
        generate_mode = request.config.getoption("--generate-fingerprints", default=False)

        if generate_mode:
            # Save the fingerprint as reference
            refs = load_reference_fingerprints()
            refs[ref_name] = fp.to_dict()
            save_reference_fingerprints(refs)
            pytest.skip(f"Generated reference fingerprint for '{ref_name}'")
        else:
            # Compare against stored reference
            refs = load_reference_fingerprints()

            if ref_name not in refs:
                pytest.fail(
                    f"No reference fingerprint found for '{ref_name}'. "
                    f"Run with --generate-fingerprints to create it."
                )

            ref_fp = GLBFingerprint.from_dict(refs[ref_name])
            matches, diffs = fp.matches(ref_fp)

            if not matches:
                # Provide detailed diff for debugging
                diff_msg = "\n".join(f"  - {d}" for d in diffs)
                pytest.fail(
                    f"Export '{ref_name}' differs from reference:\n{diff_msg}\n\n"
                    f"If this change is intentional, regenerate references with:\n"
                    f"  pytest tests/test_export_consistency.py --generate-fingerprints -k reference"
                )


# ============================================================================
# Utility: Generate all reference fingerprints
# ============================================================================

def generate_all_references(test_files_dict: dict):
    """
    Standalone utility to generate all reference fingerprints.

    Usage from Python:
        from tests.test_export_consistency import generate_all_references
        generate_all_references({
            'molecule_1': 'tests/data/mpf_motor.xyz',
            'trajectory': 'tests/data/mpf_motor_trajectory.xyz',
        })
    """
    import pyvista as pv
    pv.OFF_SCREEN = True

    refs = {}

    for ref_name, config in TestReferenceFingerprints.REFERENCE_CONFIGS.items():
        print(f"Generating reference: {ref_name}")

        signals = TreeSignals()
        sm = SceneManager(tree_signals=signals)

        file_path = pathlib.Path(test_files_dict[config['file_key']])
        obj = sm.load_xyz(file_path)

        if config.get('palette'):
            sm.set_palette(config['palette'])

        with tempfile.NamedTemporaryFile(suffix='.glb', delete=False) as tmp:
            temp_path = pathlib.Path(tmp.name)

        try:
            exporter = Exporter(sm)

            if config['animated']:
                exporter.export_trajectory_animated_glb(
                    obj, temp_path,
                    resolution=config.get('resolution', 8)
                )
            else:
                exporter.export_glb(temp_path)

            fp = extract_glb_fingerprint(temp_path)
            refs[ref_name] = fp.to_dict()
        finally:
            temp_path.unlink(missing_ok=True)

    save_reference_fingerprints(refs)
    print(f"Saved {len(refs)} reference fingerprints to {REFERENCE_FINGERPRINTS_FILE}")


# ============================================================================
# Test: Save actual GLB files for visual inspection
# ============================================================================

# Output directory for saved test files
TEST_OUTPUT_DIR = pathlib.Path(__file__).parent / 'output'


class TestSaveExportSamples:
    """
    Save actual GLB files for visual inspection.

    These tests save GLB files to tests/output/ so you can:
    1. Open them in a 3D viewer (Blender, glTF viewers, PowerPoint, etc.)
    2. Visually verify the rendering is correct
    3. Compare different palettes side by side

    Run with: pytest tests/test_export_consistency.py -k save_sample -v
    Files are saved to: tests/output/
    """

    @pytest.fixture(autouse=True)
    def setup_output_dir(self):
        """Ensure output directory exists."""
        TEST_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    def test_save_sample_molecule_default(self, scene_manager_factory, test_files):
        """Save molecule with default palette."""
        sm = scene_manager_factory()
        sm.load_xyz(test_files['molecule_1'])

        output_path = TEST_OUTPUT_DIR / 'molecule_default.glb'
        exporter = Exporter(sm)
        exporter.export_glb(output_path)

        assert output_path.exists()
        fp = extract_glb_fingerprint(output_path)
        print(f"\nSaved: {output_path}")
        print(f"  Vertices: {fp.vertex_count}, Faces: {fp.face_count}")
        print(f"  Colors: {sorted(fp.unique_colors)}")

    def test_save_sample_molecule_cpk(self, scene_manager_factory, test_files):
        """Save molecule with CPK palette."""
        sm = scene_manager_factory()
        sm.load_xyz(test_files['molecule_1'])
        sm.set_palette('cpk')

        output_path = TEST_OUTPUT_DIR / 'molecule_cpk.glb'
        exporter = Exporter(sm)
        exporter.export_glb(output_path)

        assert output_path.exists()
        fp = extract_glb_fingerprint(output_path)
        print(f"\nSaved: {output_path}")
        print(f"  Vertices: {fp.vertex_count}, Faces: {fp.face_count}")
        print(f"  Colors: {sorted(fp.unique_colors)}")

    def test_save_sample_molecule_powerpoint(self, scene_manager_factory, test_files):
        """Save molecule with PowerPoint palette (dark colors for no-shadow viewing)."""
        sm = scene_manager_factory()
        sm.load_xyz(test_files['molecule_1'])
        sm.set_palette('powerpoint')

        output_path = TEST_OUTPUT_DIR / 'molecule_powerpoint.glb'
        exporter = Exporter(sm)
        exporter.export_glb(output_path)

        assert output_path.exists()
        fp = extract_glb_fingerprint(output_path)
        print(f"\nSaved: {output_path}")
        print(f"  Vertices: {fp.vertex_count}, Faces: {fp.face_count}")
        print(f"  Colors: {sorted(fp.unique_colors)}")

    def test_save_sample_trajectory_default(self, scene_manager_factory, test_files):
        """Save animated trajectory with default palette."""
        sm = scene_manager_factory()
        traj_obj = sm.load_xyz(test_files['trajectory'])

        output_path = TEST_OUTPUT_DIR / 'trajectory_default.glb'
        exporter = Exporter(sm)
        exporter.export_trajectory_animated_glb(traj_obj, output_path, fps=10, resolution=8)

        assert output_path.exists()
        fp = extract_glb_fingerprint(output_path)
        print(f"\nSaved: {output_path}")
        print(f"  Vertices: {fp.vertex_count}, Faces: {fp.face_count}")
        print(f"  Animation: {fp.frame_count} frames, {fp.animation_duration:.2f}s")
        print(f"  Bones: {fp.bone_count}")
        print(f"  Colors: {sorted(fp.unique_colors)}")

    def test_save_sample_trajectory_powerpoint(self, scene_manager_factory, test_files):
        """Save animated trajectory with PowerPoint palette."""
        sm = scene_manager_factory()
        traj_obj = sm.load_xyz(test_files['trajectory'])
        sm.set_palette('powerpoint')

        output_path = TEST_OUTPUT_DIR / 'trajectory_powerpoint.glb'
        exporter = Exporter(sm)
        exporter.export_trajectory_animated_glb(traj_obj, output_path, fps=10, resolution=8)

        assert output_path.exists()
        fp = extract_glb_fingerprint(output_path)
        print(f"\nSaved: {output_path}")
        print(f"  Vertices: {fp.vertex_count}, Faces: {fp.face_count}")
        print(f"  Animation: {fp.frame_count} frames, {fp.animation_duration:.2f}s")
        print(f"  Bones: {fp.bone_count}")
        print(f"  Colors: {sorted(fp.unique_colors)}")

    def test_save_sample_benzene(self, scene_manager_factory, test_files):
        """Save benzene molecule (C6H6)."""
        sm = scene_manager_factory()
        sm.load_xyz(test_files['molecule_2'])  # C6H6.xyz

        output_path = TEST_OUTPUT_DIR / 'benzene_default.glb'
        exporter = Exporter(sm)
        exporter.export_glb(output_path)

        assert output_path.exists()
        fp = extract_glb_fingerprint(output_path)
        print(f"\nSaved: {output_path}")
        print(f"  Vertices: {fp.vertex_count}, Faces: {fp.face_count}")
        print(f"  Colors: {sorted(fp.unique_colors)}")

    def test_save_sample_with_scalar_field(self, scene_manager_factory, test_files):
        """Save molecule with scalar field (isosurface)."""
        sm = scene_manager_factory()
        sm.load_molecule_from_cube(test_files['scalar_filed_cube'])

        output_path = TEST_OUTPUT_DIR / 'molecule_with_isosurface.glb'
        exporter = Exporter(sm)
        exporter.export_glb(output_path)

        assert output_path.exists()
        fp = extract_glb_fingerprint(output_path)
        print(f"\nSaved: {output_path}")
        print(f"  Meshes: {fp.mesh_count}")
        print(f"  Vertices: {fp.vertex_count}, Faces: {fp.face_count}")
        print(f"  Colors: {sorted(fp.unique_colors)}")

    def test_save_sample_all_palettes_comparison(self, scene_manager_factory, test_files):
        """Save the same molecule with all available palettes for comparison."""
        from chemvista.renderer.palettes import get_available_palettes

        palettes = get_available_palettes()
        print(f"\nSaving molecule with {len(palettes)} palettes:")

        for palette_name in palettes:
            sm = scene_manager_factory()
            sm.load_xyz(test_files['molecule_1'])
            sm.set_palette(palette_name)

            output_path = TEST_OUTPUT_DIR / f'molecule_{palette_name}.glb'
            exporter = Exporter(sm)
            exporter.export_glb(output_path)

            assert output_path.exists()
            fp = extract_glb_fingerprint(output_path)
            print(f"  {palette_name}: {output_path.name} - {len(fp.unique_colors)} colors")

    # -------------------------------------------------------------------------
    # PNG Screenshot samples
    # -------------------------------------------------------------------------

    @pytest.mark.screenshot
    def test_save_sample_png_molecule_default(self, scene_manager_factory, test_files):
        """Save PNG screenshot with default palette."""
        sm = scene_manager_factory()
        sm.load_xyz(test_files['molecule_1'])

        plotter = pv.Plotter(off_screen=True)
        sm.render(plotter=plotter)
        output_path = TEST_OUTPUT_DIR / 'molecule_default.png'
        plotter.screenshot(str(output_path))
        plotter.close()

        assert output_path.exists()
        fp = extract_png_fingerprint(output_path)
        print(f"\nSaved: {output_path}")
        print(f"  Size: {fp.width}x{fp.height}")
        print(f"  Unique colors: {fp.unique_color_count}")

    @pytest.mark.screenshot
    def test_save_sample_png_molecule_powerpoint(self, scene_manager_factory, test_files):
        """Save PNG screenshot with PowerPoint palette."""
        sm = scene_manager_factory()
        sm.load_xyz(test_files['molecule_1'])
        sm.set_palette('powerpoint')

        plotter = pv.Plotter(off_screen=True)
        sm.render(plotter=plotter)
        output_path = TEST_OUTPUT_DIR / 'molecule_powerpoint.png'
        plotter.screenshot(str(output_path))
        plotter.close()

        assert output_path.exists()
        fp = extract_png_fingerprint(output_path)
        print(f"\nSaved: {output_path}")
        print(f"  Size: {fp.width}x{fp.height}")
        print(f"  Unique colors: {fp.unique_color_count}")

    @pytest.mark.screenshot
    def test_save_sample_png_transparent(self, scene_manager_factory, test_files):
        """Save PNG screenshot with transparent background."""
        sm = scene_manager_factory()
        sm.load_xyz(test_files['molecule_1'])

        plotter = pv.Plotter(off_screen=True)
        sm.render(plotter=plotter)
        plotter.set_background([0, 0, 0, 0])
        output_path = TEST_OUTPUT_DIR / 'molecule_transparent.png'
        plotter.screenshot(str(output_path), transparent_background=True)
        plotter.close()

        assert output_path.exists()
        fp = extract_png_fingerprint(output_path)
        print(f"\nSaved: {output_path}")
        print(f"  Size: {fp.width}x{fp.height}")
        print(f"  Has transparency: {fp.has_transparency}")
        print(f"  Transparent ratio: {fp.transparent_pixel_ratio:.2%}")

    @pytest.mark.screenshot
    def test_save_sample_png_benzene(self, scene_manager_factory, test_files):
        """Save PNG screenshot of benzene."""
        sm = scene_manager_factory()
        sm.load_xyz(test_files['molecule_2'])  # C6H6.xyz

        plotter = pv.Plotter(off_screen=True)
        sm.render(plotter=plotter)
        output_path = TEST_OUTPUT_DIR / 'benzene_default.png'
        plotter.screenshot(str(output_path))
        plotter.close()

        assert output_path.exists()
        fp = extract_png_fingerprint(output_path)
        print(f"\nSaved: {output_path}")
        print(f"  Size: {fp.width}x{fp.height}")
        print(f"  Unique colors: {fp.unique_color_count}")

    @pytest.mark.screenshot
    def test_save_sample_png_all_palettes(self, scene_manager_factory, test_files):
        """Save PNG screenshots with all available palettes."""
        from chemvista.renderer.palettes import get_available_palettes

        palettes = get_available_palettes()
        print(f"\nSaving PNG screenshots with {len(palettes)} palettes:")

        for palette_name in palettes:
            sm = scene_manager_factory()
            sm.load_xyz(test_files['molecule_1'])
            sm.set_palette(palette_name)

            plotter = pv.Plotter(off_screen=True)
            sm.render(plotter=plotter)
            output_path = TEST_OUTPUT_DIR / f'molecule_{palette_name}.png'
            plotter.screenshot(str(output_path))
            plotter.close()

            assert output_path.exists()
            fp = extract_png_fingerprint(output_path)
            print(f"  {palette_name}: {output_path.name} - {fp.unique_color_count} colors")
