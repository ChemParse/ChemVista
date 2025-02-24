import pytest
from chemvista.cli import create_init_dict
import pathlib


@pytest.fixture
def sample_files():
    return {
        'xyz': [
            pathlib.Path('test1.xyz'),
            pathlib.Path('test2.xyz')
        ],
        'cube_mol': [
            pathlib.Path('test1.cube'),
            pathlib.Path('test2.cube')
        ],
        'cube_field': [
            pathlib.Path('field1.cube'),
            pathlib.Path('field2.cube')
        ]
    }


def test_create_init_dict(sample_files):
    """Test creation of initialization dictionary"""
    init_dict = create_init_dict(
        xyz_files=sample_files['xyz'],
        cube_mol_files=sample_files['cube_mol'],
        cube_field_files=sample_files['cube_field']
    )

    assert 'xyz_files' in init_dict
    assert 'cube_mol_files' in init_dict
    assert 'cube_field_files' in init_dict

    assert init_dict['xyz_files'] == sample_files['xyz']
    assert init_dict['cube_mol_files'] == sample_files['cube_mol']
    assert init_dict['cube_field_files'] == sample_files['cube_field']


def test_create_init_dict_empty():
    """Test creation of initialization dictionary with empty lists"""
    init_dict = create_init_dict([], [], [])

    assert 'xyz_files' in init_dict
    assert 'cube_mol_files' in init_dict
    assert 'cube_field_files' in init_dict

    assert len(init_dict['xyz_files']) == 0
    assert len(init_dict['cube_mol_files']) == 0
    assert len(init_dict['cube_field_files']) == 0


def test_create_init_dict_mixed():
    """Test creation of initialization dictionary with some empty lists"""
    xyz_files = [pathlib.Path('test.xyz')]
    init_dict = create_init_dict(xyz_files, [], [])

    assert len(init_dict['xyz_files']) == 1
    assert len(init_dict['cube_mol_files']) == 0
    assert len(init_dict['cube_field_files']) == 0
    assert init_dict['xyz_files'] == xyz_files
