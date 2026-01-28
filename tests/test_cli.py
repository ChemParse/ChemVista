import pytest
import pathlib
import argparse
import sys
from unittest.mock import patch, MagicMock

from chemvista.cli import main


@pytest.fixture
def sample_files():
    """Sample files fixture for CLI testing"""
    return {
        'xyz': [pathlib.Path('test1.xyz'), pathlib.Path('test2.xyz')],
        'cube_mol': [pathlib.Path('test1.cube')],
        'cube_field': [pathlib.Path('test2.cube'), pathlib.Path('test3.cube')],
    }


def create_init_dict(xyz_files, cube_mol_files, cube_field_files):
    """Create initialization dictionary from file lists"""
    return {
        'xyz_files': xyz_files,
        'cube_mol_files': cube_mol_files,
        'cube_field_files': cube_field_files
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


@patch('argparse.ArgumentParser.parse_args')
@patch('chemvista.cli.QApplication')
@patch('chemvista.cli.ChemVistaApp')
def test_cli_interactive_mode(mock_app_class, mock_qapp, mock_parse_args):
    """Test CLI interactive mode"""
    # Setup mock arguments
    args = argparse.Namespace(
        xyz=[],
        cube_mol=[],
        cube_field=[],
        interactive=True,
        render=False,
        screenshot=None
    )
    mock_parse_args.return_value = args

    # Mock QApplication
    mock_qapp.return_value = MagicMock()

    # Mock ChemVistaApp
    mock_app = MagicMock()
    mock_app_class.return_value = mock_app

    # Call the main function with mocked dependencies
    with patch.object(sys, 'argv', ['chemvista']):
        with patch('chemvista.cli.SceneManager'):
            with pytest.raises(SystemExit):
                main()

    # Verify the GUI application was created
    mock_app_class.assert_called_once()
    mock_qapp.return_value.exec_.assert_called_once()


@patch('argparse.ArgumentParser.parse_args')
@patch('chemvista.cli.SceneManager')
def test_cli_screenshot_mode(mock_scene_manager, mock_parse_args):
    """Test CLI screenshot mode"""
    # Setup mock arguments
    screenshot_path = pathlib.Path('screenshot.png')
    args = argparse.Namespace(
        xyz=[],
        cube_mol=[],
        cube_field=[],
        interactive=False,
        render=False,
        screenshot=screenshot_path
    )
    mock_parse_args.return_value = args

    # Setup mock scene manager and plotter
    mock_manager = MagicMock()
    mock_plotter = MagicMock()
    mock_manager.render.return_value = mock_plotter
    mock_scene_manager.return_value = mock_manager

    # Call the main function with mocked dependencies
    with patch.object(sys, 'argv', ['chemvista']):
        main()

    # Verify screenshot was taken
    mock_manager.render.assert_called_once_with(off_screen=True)
    mock_plotter.screenshot.assert_called_once_with(str(screenshot_path))
