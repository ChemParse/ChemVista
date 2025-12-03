"""
Tests for TrajectoryControlsWidget - UI for trajectory animation control.
"""

import pytest
from unittest.mock import MagicMock, patch
from PyQt5.QtCore import Qt

from chemvista.gui.widgets.trajectory_controls import (
    TrajectoryControlsWidget,
    ANIMATION_TIMER_INTERVAL_MS
)
from chemvista.scene_objects import TrajectoryObject


class TestTrajectoryControlsSetup:
    """Tests for TrajectoryControlsWidget initialization and setup"""

    def test_widget_initialization(self, qapp):
        """Test that widget initializes with correct defaults"""
        widget = TrajectoryControlsWidget()

        assert widget._trajectory is None
        assert widget._current_time == 0.0
        assert widget._substeps == 10
        assert widget.title_label.text() == "No trajectory selected"
        assert widget.frame_slider.maximum() == 0
        assert widget.fps_spin.value() == 10
        assert widget.loop_cb.isChecked() is True
        assert widget.smooth_cb.isChecked() is True
        assert widget.substeps_spin.value() == 10

    def test_set_trajectory(self, qapp, test_objects):
        """Test setting a trajectory"""
        widget = TrajectoryControlsWidget()
        trajectory_obj = TrajectoryObject.from_xyz_file(test_objects['trajectory_file'])

        widget.set_trajectory(trajectory_obj)

        assert widget._trajectory is trajectory_obj
        assert f"Trajectory: {trajectory_obj.name}" in widget.title_label.text()
        assert widget.frame_slider.maximum() > 0

    def test_set_trajectory_none(self, qapp, test_objects):
        """Test clearing the trajectory"""
        widget = TrajectoryControlsWidget()
        trajectory_obj = TrajectoryObject.from_xyz_file(test_objects['trajectory_file'])

        widget.set_trajectory(trajectory_obj)
        widget.set_trajectory(None)

        assert widget._trajectory is None
        assert widget.title_label.text() == "No trajectory selected"
        assert widget.frame_slider.maximum() == 0

    def test_clear_method(self, qapp, test_objects):
        """Test clear() method"""
        widget = TrajectoryControlsWidget()
        trajectory_obj = TrajectoryObject.from_xyz_file(test_objects['trajectory_file'])

        widget.set_trajectory(trajectory_obj)
        widget.clear()

        assert widget._trajectory is None


class TestTrajectoryControlsNavigation:
    """Tests for frame navigation controls"""

    def test_first_frame(self, qapp, test_objects):
        """Test going to first frame"""
        widget = TrajectoryControlsWidget()
        trajectory_obj = TrajectoryObject.from_xyz_file(test_objects['trajectory_file'])
        widget.set_trajectory(trajectory_obj)

        # Move to a later frame first
        widget._current_time = 5.0
        trajectory_obj.set_frame(5, send_signals=False)

        widget._on_first()

        assert widget._current_time == 0.0
        assert trajectory_obj.current_frame == 0

    def test_last_frame(self, qapp, test_objects):
        """Test going to last frame"""
        widget = TrajectoryControlsWidget()
        trajectory_obj = TrajectoryObject.from_xyz_file(test_objects['trajectory_file'])
        widget.set_trajectory(trajectory_obj)

        widget._on_last()

        expected_time = float(trajectory_obj.num_frames - 1)
        assert widget._current_time == expected_time
        assert trajectory_obj.current_frame == trajectory_obj.num_frames - 1

    def test_next_frame(self, qapp, test_objects):
        """Test going to next frame"""
        widget = TrajectoryControlsWidget()
        trajectory_obj = TrajectoryObject.from_xyz_file(test_objects['trajectory_file'])
        widget.set_trajectory(trajectory_obj)

        initial_frame = trajectory_obj.current_frame
        widget._on_next()

        assert widget._current_time == float(initial_frame + 1)

    def test_prev_frame(self, qapp, test_objects):
        """Test going to previous frame"""
        widget = TrajectoryControlsWidget()
        trajectory_obj = TrajectoryObject.from_xyz_file(test_objects['trajectory_file'])
        widget.set_trajectory(trajectory_obj)

        # Start at frame 5
        widget._current_time = 5.0
        trajectory_obj.set_frame(5, send_signals=False)

        widget._on_prev()

        assert widget._current_time == 4.0

    def test_prev_frame_at_start(self, qapp, test_objects):
        """Test previous frame at start doesn't go negative"""
        widget = TrajectoryControlsWidget()
        trajectory_obj = TrajectoryObject.from_xyz_file(test_objects['trajectory_file'])
        widget.set_trajectory(trajectory_obj)

        widget._current_time = 0.0
        trajectory_obj.set_frame(0, send_signals=False)

        widget._on_prev()

        assert widget._current_time == 0.0


class TestTrajectoryControlsPlayback:
    """Tests for play/pause/stop functionality"""

    def test_play_pause_toggle(self, qapp, test_objects):
        """Test play/pause toggling"""
        widget = TrajectoryControlsWidget()
        trajectory_obj = TrajectoryObject.from_xyz_file(test_objects['trajectory_file'])
        widget.set_trajectory(trajectory_obj)

        # Initially not playing
        assert trajectory_obj.is_playing is False
        assert widget.play_btn.text() == "Play"

        # Start playing
        widget._on_play_pause()
        assert trajectory_obj.is_playing is True
        assert widget.play_btn.text() == "Pause"
        assert widget._timer.isActive() is True

        # Pause
        widget._on_play_pause()
        assert trajectory_obj.is_playing is False
        assert widget.play_btn.text() == "Play"
        assert widget._timer.isActive() is False

    def test_stop(self, qapp, test_objects):
        """Test stop resets to first frame"""
        widget = TrajectoryControlsWidget()
        trajectory_obj = TrajectoryObject.from_xyz_file(test_objects['trajectory_file'])
        widget.set_trajectory(trajectory_obj)

        # Start playing and move to frame 5
        widget._current_time = 5.0
        trajectory_obj.set_frame(5, send_signals=False)
        trajectory_obj.play()
        widget._start_timer()

        widget._on_stop()

        assert trajectory_obj.is_playing is False
        assert widget._current_time == 0.0
        assert widget._timer.isActive() is False

    def test_timer_tick_advances_time(self, qapp, test_objects):
        """Test that timer tick advances the animation time"""
        widget = TrajectoryControlsWidget()
        trajectory_obj = TrajectoryObject.from_xyz_file(test_objects['trajectory_file'])
        widget.set_trajectory(trajectory_obj)

        initial_time = widget._current_time
        widget._on_timer_tick()

        # Time should have advanced
        expected_increment = trajectory_obj.fps * (ANIMATION_TIMER_INTERVAL_MS / 1000.0)
        assert widget._current_time == pytest.approx(initial_time + expected_increment)

    def test_timer_tick_loops(self, qapp, test_objects):
        """Test that timer tick loops at end when loop is enabled"""
        widget = TrajectoryControlsWidget()
        trajectory_obj = TrajectoryObject.from_xyz_file(test_objects['trajectory_file'])
        widget.set_trajectory(trajectory_obj)

        # Move to near end
        max_time = float(trajectory_obj.num_frames - 1)
        widget._current_time = max_time - 0.01

        widget._on_timer_tick()

        # Should have looped back to near start
        assert widget._current_time < max_time / 2

    def test_timer_tick_stops_without_loop(self, qapp, test_objects):
        """Test that timer stops at end when loop is disabled"""
        widget = TrajectoryControlsWidget()
        trajectory_obj = TrajectoryObject.from_xyz_file(test_objects['trajectory_file'])
        widget.set_trajectory(trajectory_obj)

        # Disable loop
        trajectory_obj.loop = False
        widget.loop_cb.setChecked(False)

        # Move to near end
        max_time = float(trajectory_obj.num_frames - 1)
        widget._current_time = max_time - 0.01
        trajectory_obj.play()
        widget._start_timer()

        widget._on_timer_tick()

        # Should have stopped at max time
        assert widget._current_time == max_time
        assert trajectory_obj.is_playing is False


class TestTrajectoryControlsSettings:
    """Tests for FPS, loop, and substeps settings"""

    def test_fps_change(self, qapp, test_objects):
        """Test changing FPS"""
        widget = TrajectoryControlsWidget()
        trajectory_obj = TrajectoryObject.from_xyz_file(test_objects['trajectory_file'])
        widget.set_trajectory(trajectory_obj)

        widget._on_fps_changed(30)

        assert trajectory_obj.fps == 30

    def test_loop_change(self, qapp, test_objects):
        """Test changing loop setting"""
        widget = TrajectoryControlsWidget()
        trajectory_obj = TrajectoryObject.from_xyz_file(test_objects['trajectory_file'])
        widget.set_trajectory(trajectory_obj)

        widget._on_loop_changed(Qt.Unchecked)
        assert trajectory_obj.loop is False

        widget._on_loop_changed(Qt.Checked)
        assert trajectory_obj.loop is True

    def test_substeps_change(self, qapp, test_objects):
        """Test changing substeps"""
        widget = TrajectoryControlsWidget()
        trajectory_obj = TrajectoryObject.from_xyz_file(test_objects['trajectory_file'])
        widget.set_trajectory(trajectory_obj)

        widget._on_substeps_changed(20)

        assert widget._substeps == 20
        # Slider max should be updated
        expected_max = (trajectory_obj.num_frames - 1) * 20
        assert widget.frame_slider.maximum() == expected_max


class TestTrajectoryControlsSignals:
    """Tests for signal emission"""

    def test_time_changed_signal_emitted(self, qapp, test_objects):
        """Test that time_changed signal is emitted in smooth mode"""
        widget = TrajectoryControlsWidget()
        trajectory_obj = TrajectoryObject.from_xyz_file(test_objects['trajectory_file'])
        widget.set_trajectory(trajectory_obj)

        # Ensure smooth mode is on
        widget.smooth_cb.setChecked(True)

        # Track signal emission
        signal_received = []
        widget.time_changed.connect(lambda uuid, time: signal_received.append((uuid, time)))

        widget._on_next()

        assert len(signal_received) == 1
        assert signal_received[0][0] == trajectory_obj.uuid
        assert signal_received[0][1] == 1.0  # Should be frame 1

    def test_frame_changed_signal_emitted(self, qapp, test_objects):
        """Test that frame_changed signal is emitted in discrete mode"""
        widget = TrajectoryControlsWidget()
        trajectory_obj = TrajectoryObject.from_xyz_file(test_objects['trajectory_file'])
        widget.set_trajectory(trajectory_obj)

        # Disable smooth mode
        widget.smooth_cb.setChecked(False)

        # Track signal emission
        signal_received = []
        widget.frame_changed.connect(lambda uuid: signal_received.append(uuid))

        widget._on_next()

        assert len(signal_received) == 1
        assert signal_received[0] == trajectory_obj.uuid


class TestTrajectoryControlsSlider:
    """Tests for slider interaction"""

    def test_slider_smooth_mode(self, qapp, test_objects):
        """Test slider changes in smooth mode emit time_changed"""
        widget = TrajectoryControlsWidget()
        trajectory_obj = TrajectoryObject.from_xyz_file(test_objects['trajectory_file'])
        widget.set_trajectory(trajectory_obj)

        widget.smooth_cb.setChecked(True)

        # Track signal emission
        signal_received = []
        widget.time_changed.connect(lambda uuid, time: signal_received.append((uuid, time)))

        # Change slider value (represents substeps * time)
        widget.frame_slider.setValue(widget._substeps * 2)  # Time = 2.0

        assert len(signal_received) == 1
        assert signal_received[0][0] == trajectory_obj.uuid
        assert signal_received[0][1] == 2.0

    def test_slider_discrete_mode(self, qapp, test_objects):
        """Test slider changes in discrete mode emit frame_changed"""
        widget = TrajectoryControlsWidget()
        trajectory_obj = TrajectoryObject.from_xyz_file(test_objects['trajectory_file'])
        widget.set_trajectory(trajectory_obj)

        widget.smooth_cb.setChecked(False)

        # Track signal emission
        signal_received = []
        widget.frame_changed.connect(lambda uuid: signal_received.append(uuid))

        # Change slider value
        widget.frame_slider.setValue(widget._substeps * 2)

        assert len(signal_received) == 1
        assert signal_received[0] == trajectory_obj.uuid


@pytest.fixture
def test_objects(test_files):
    """Augmented test objects with trajectory file path"""
    return {
        'trajectory_file': test_files['trajectory']
    }


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
