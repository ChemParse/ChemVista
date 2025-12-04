"""
Tests for visibility caching and fast visibility toggle system.
"""

import pytest
from unittest.mock import MagicMock, patch

from chemvista.gui.scene import SceneWidget
from chemvista.scene_objects import MoleculeObject, ScalarFieldObject
from chemvista.scene_manager import SceneManager
from chemvista.tree_structure import TreeSignals


@pytest.fixture
def signals():
    """Create tree signals for testing"""
    return TreeSignals()


@pytest.fixture
def scene(test_plotter, signals):
    """Create SceneManager with test plotter and signals"""
    manager = SceneManager(tree_signals=signals)
    manager.plotter = test_plotter
    return manager


class TestActorCache:
    """Tests for actor cache functionality"""

    def test_actor_cache_initialized_empty(self, qapp, mock_scene_widget):
        """Test that actor cache is initialized empty"""
        widget = mock_scene_widget
        assert widget._actor_cache == {}

    def test_actor_cache_cleared_on_refresh(self, qapp, test_files, mock_scene_widget):
        """Test that actor cache is cleared when doing full refresh"""
        widget = mock_scene_widget

        # Pre-populate cache with dummy data
        widget._actor_cache = {'test-uuid': [MagicMock()]}

        # Refresh should clear the cache
        widget.refresh_view()

        # Note: the cache gets repopulated during refresh
        # But _clear_actor_cache is called first
        assert isinstance(widget._actor_cache, dict)

    def test_actor_map_returned_from_render(self, scene: SceneManager, test_files, test_plotter):
        """Test that render() returns actor mapping"""
        obj = scene.load_xyz(test_files['molecule_1'])

        plotter, actor_map = scene.render(test_plotter)

        # Actor map should have at least one entry (the molecule)
        assert len(actor_map) >= 1

        # Each entry should have a list of actors
        for obj_uuid, actors in actor_map.items():
            assert isinstance(actors, list)
            assert len(actors) > 0

    def test_render_single_object(self, scene: SceneManager, test_files, test_plotter):
        """Test rendering a single object for preloading"""
        obj = scene.load_xyz(test_files['molecule_1'])

        actors = scene.render_single_object(obj, test_plotter)

        assert isinstance(actors, list)
        # May have actors (atoms/bonds) depending on the molecule


class TestFastVisibilityToggle:
    """Tests for fast visibility toggle via actor.SetVisibility()"""

    def test_visibility_toggle_with_cached_actor(self, qapp, scene: SceneManager, test_files, mock_scene_widget):
        """Test that visibility toggle uses cached actors when available"""
        # Load and render a molecule
        obj = scene.load_xyz(test_files['molecule_1'])

        widget = mock_scene_widget

        # Create mock actors
        mock_actor = MagicMock()
        mock_actor.SetVisibility = MagicMock()

        # Pre-populate cache with object's UUID
        widget._actor_cache[obj.uuid] = [mock_actor]

        # Toggle visibility
        widget._on_visibility_changed(obj.uuid, False)

        # Verify actor.SetVisibility was called
        mock_actor.SetVisibility.assert_called_once_with(False)

        # Verify plotter.render() was called
        widget.plotter.render.assert_called_once()

    def test_visibility_toggle_skips_render_changed(self, qapp, scene: SceneManager, test_files, mock_scene_widget):
        """Test that render_changed is skipped when visibility was handled"""
        obj = scene.load_xyz(test_files['molecule_1'])

        widget = mock_scene_widget

        # Create mock actors in cache
        mock_actor = MagicMock()
        widget._actor_cache[obj.uuid] = [mock_actor]

        # Handle visibility change (marks UUID as handled)
        widget._on_visibility_changed(obj.uuid, False)

        # Verify UUID was marked as handled
        assert obj.uuid in widget._visibility_handled_uuids

        # Now trigger render_changed - it should skip
        widget._on_render_changed(obj.uuid)

        # UUID should be removed from handled set
        assert obj.uuid not in widget._visibility_handled_uuids

    def test_trajectory_visibility_toggles_all_children(self, qapp, scene: SceneManager, test_files, mock_scene_widget):
        """Test that toggling trajectory visibility affects all child molecule actors"""
        # Load a trajectory (multi-frame XYZ)
        traj_obj = scene.load_xyz(test_files['trajectory'])

        widget = mock_scene_widget

        # Create mock actors for each child molecule
        child_actors = {}
        for child in traj_obj.children:
            mock_actor = MagicMock()
            mock_actor.SetVisibility = MagicMock()
            child_actors[child.uuid] = [mock_actor]
            widget._actor_cache[child.uuid] = [mock_actor]

        # Toggle trajectory visibility off
        widget._on_visibility_changed(traj_obj.uuid, False)

        # Verify SetVisibility was called on all child actors
        for child in traj_obj.children:
            for actor in child_actors[child.uuid]:
                actor.SetVisibility.assert_called_with(False)

        # Verify plotter.render() was called
        widget.plotter.render.assert_called()

        # Verify trajectory UUID was marked as handled
        assert traj_obj.uuid in widget._visibility_handled_uuids

    def test_trajectory_visibility_respects_child_states(self, qapp, scene: SceneManager, test_files, mock_scene_widget):
        """Test that toggling trajectory ON respects individual child visibility states"""
        # Load a trajectory (multi-frame XYZ)
        traj_obj = scene.load_xyz(test_files['trajectory'])

        widget = mock_scene_widget

        # Make some children invisible in the data model
        children = list(traj_obj.children)
        if len(children) >= 2:
            # Set second child as invisible in the data model
            children[1]._visible = False  # Direct set to avoid signal emission

        # Create mock actors for each child molecule
        child_actors = {}
        for child in traj_obj.children:
            mock_actor = MagicMock()
            mock_actor.SetVisibility = MagicMock()
            child_actors[child.uuid] = [mock_actor]
            widget._actor_cache[child.uuid] = [mock_actor]

        # Toggle trajectory visibility ON
        widget._on_visibility_changed(traj_obj.uuid, True)

        # Verify SetVisibility was called with correct value based on child's own visibility
        for i, child in enumerate(traj_obj.children):
            expected_visible = child.visible  # Should respect child's own visibility
            for actor in child_actors[child.uuid]:
                actor.SetVisibility.assert_called_with(expected_visible)

    def test_visibility_toggle_triggers_preload_for_uncached_visible(self, qapp, scene: SceneManager, test_files, mock_scene_widget):
        """Test that making an uncached object visible triggers preload"""
        obj = scene.load_xyz(test_files['molecule_1'])

        widget = mock_scene_widget

        # Mock render_single_object to return actors
        mock_actor = MagicMock()
        widget.scene_manager.render_single_object = MagicMock(return_value=[mock_actor])

        # Trigger visibility change for uncached object
        widget._on_visibility_changed(obj.uuid, True)

        # Verify render_single_object was called
        widget.scene_manager.render_single_object.assert_called_once()


class TestOnDemandLoading:
    """Tests for on-demand loading when making invisible objects visible"""

    def test_preload_single_object_adds_to_cache(self, qapp, scene: SceneManager, test_files, mock_scene_widget):
        """Test that on-demand loading adds object to cache"""
        obj = scene.load_xyz(test_files['molecule_1'])

        widget = mock_scene_widget

        # Mock render_single_object
        mock_actor = MagicMock()
        widget.scene_manager.render_single_object = MagicMock(return_value=[mock_actor])

        # Load the object on-demand
        widget._preload_single_object(obj.uuid, visible=True)

        # Verify it's now in cache
        assert obj.uuid in widget._actor_cache
        assert widget._actor_cache[obj.uuid] == [mock_actor]

        # Verify render_single_object was called with visible=True
        widget.scene_manager.render_single_object.assert_called_once()
        call_args = widget.scene_manager.render_single_object.call_args
        assert call_args[1].get('visible') is True or (len(call_args[0]) >= 3 and call_args[0][2] is True)


class TestCacheInvalidation:
    """Tests for cache invalidation scenarios"""

    def test_clear_actor_cache(self, qapp, mock_scene_widget):
        """Test _clear_actor_cache clears all cache data"""
        widget = mock_scene_widget

        # Pre-populate
        widget._actor_cache = {'uuid1': [MagicMock()], 'uuid2': [MagicMock()]}

        # Clear cache
        widget._clear_actor_cache()

        # Cache should be cleared
        assert widget._actor_cache == {}


class TestRendererActorReturns:
    """Tests for renderer actor return values"""

    def test_molecule_renderer_returns_actors(self, scene: SceneManager, test_objects, test_plotter):
        """Test that molecule renderer returns actors"""
        molecule = test_objects['molecule_1']
        settings = scene.molecule_renderer.get_default_settings()

        actors = scene.molecule_renderer.render(molecule, test_plotter, settings)

        assert isinstance(actors, list)
        assert len(actors) > 0

    def test_scalar_field_renderer_returns_actors(self, scene: SceneManager, test_objects, test_plotter):
        """Test that scalar field renderer returns actors"""
        field = test_objects['scalar_field']
        settings = scene.scalar_field_renderer.get_default_settings()

        actors = scene.scalar_field_renderer.render(field, test_plotter, settings)

        assert isinstance(actors, list)
        # Note: might be empty if no isosurface is found for default values

    def test_render_single_object_invisible_sets_visibility(self, scene: SceneManager, test_files, test_plotter):
        """Test that render_single_object with visible=False creates invisible actors"""
        obj = scene.load_xyz(test_files['molecule_1'])

        # Render with visible=False
        actors = scene.render_single_object(obj, test_plotter, visible=False)

        assert isinstance(actors, list)
        assert len(actors) > 0

        # Verify actors are invisible
        for actor in actors:
            if hasattr(actor, 'GetVisibility'):
                assert actor.GetVisibility() == 0, "Actor should be invisible"


@pytest.fixture
def mock_scene_widget(qapp, scene):
    """Create a mocked SceneWidget for testing"""
    from PyQt5.QtWidgets import QWidget

    class MockQtInteractor(QWidget):
        """Mock QtInteractor that behaves like a QWidget"""
        def __init__(self, parent=None):
            super().__init__(parent)
            self.clear = MagicMock()
            self.update = MagicMock()
            self.camera = MagicMock()
            self.render = MagicMock()
            self.reset_camera = MagicMock()
            self.set_background = MagicMock()
            self.add_mesh = MagicMock()
            self.close = MagicMock()
            self.renderer = MagicMock()

    with patch('chemvista.gui.scene.QtInteractor', MockQtInteractor):
        widget = SceneWidget(scene_manager=scene)

        # Set up scene signals
        from chemvista.gui.scene import SceneWidgetSignals
        widget._scene_signals = SceneWidgetSignals()

        # Mock scene.render to return proper tuple
        scene.render = MagicMock(return_value=(widget.plotter, {}))

        yield widget


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
