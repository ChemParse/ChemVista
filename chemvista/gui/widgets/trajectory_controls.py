"""
Trajectory animation controls widget for ChemVista GUI.

Provides playback controls (play/pause, stop, frame navigation) and
settings (fps, loop) for trajectory animations with smooth interpolation.
"""

import logging
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QSlider,
    QLabel, QSpinBox, QCheckBox, QGroupBox
)
from PyQt5.QtGui import QIcon

from ...scene_objects import TrajectoryObject

logger = logging.getLogger("chemvista.gui.widgets.trajectory_controls")

# Timer interval in milliseconds for smooth animation (60 FPS render rate)
ANIMATION_TIMER_INTERVAL_MS = 16  # ~60 updates per second


class TrajectoryControlsWidget(QWidget):
    """Widget providing playback controls for trajectory animation with smooth interpolation"""

    # Signal emitted when animation time changes (for view refresh)
    # Emits (trajectory_uuid, time_value) for interpolated rendering
    frame_changed = pyqtSignal(str)  # Emits trajectory UUID
    time_changed = pyqtSignal(str, float)  # Emits trajectory UUID and time value

    def __init__(self, parent=None):
        super().__init__(parent)
        self._trajectory: TrajectoryObject = None
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_timer_tick)

        # Smooth animation state
        self._current_time = 0.0  # Continuous time value for interpolation
        self._substeps = 10  # Number of interpolation steps per frame transition

        self._setup_ui()
        self._update_enabled_state()

    def _setup_ui(self):
        """Create the UI elements"""
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)

        # Title label
        self.title_label = QLabel("No trajectory selected")
        self.title_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.title_label)

        # Frame slider
        slider_layout = QHBoxLayout()

        self.frame_slider = QSlider(Qt.Horizontal)
        self.frame_slider.setMinimum(0)
        self.frame_slider.setMaximum(0)
        self.frame_slider.valueChanged.connect(self._on_slider_changed)
        slider_layout.addWidget(self.frame_slider)

        self.frame_label = QLabel("0 / 0")
        self.frame_label.setMinimumWidth(60)
        slider_layout.addWidget(self.frame_label)

        layout.addLayout(slider_layout)

        # Playback controls
        controls_layout = QHBoxLayout()

        self.first_btn = QPushButton("|<")
        self.first_btn.setToolTip("First frame")
        self.first_btn.setFixedWidth(40)
        self.first_btn.clicked.connect(self._on_first)
        controls_layout.addWidget(self.first_btn)

        self.prev_btn = QPushButton("<")
        self.prev_btn.setToolTip("Previous frame")
        self.prev_btn.setFixedWidth(40)
        self.prev_btn.clicked.connect(self._on_prev)
        controls_layout.addWidget(self.prev_btn)

        self.play_btn = QPushButton("Play")
        self.play_btn.setToolTip("Play/Pause")
        self.play_btn.setFixedWidth(60)
        self.play_btn.clicked.connect(self._on_play_pause)
        controls_layout.addWidget(self.play_btn)

        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setToolTip("Stop and reset")
        self.stop_btn.setFixedWidth(60)
        self.stop_btn.clicked.connect(self._on_stop)
        controls_layout.addWidget(self.stop_btn)

        self.next_btn = QPushButton(">")
        self.next_btn.setToolTip("Next frame")
        self.next_btn.setFixedWidth(40)
        self.next_btn.clicked.connect(self._on_next)
        controls_layout.addWidget(self.next_btn)

        self.last_btn = QPushButton(">|")
        self.last_btn.setToolTip("Last frame")
        self.last_btn.setFixedWidth(40)
        self.last_btn.clicked.connect(self._on_last)
        controls_layout.addWidget(self.last_btn)

        controls_layout.addStretch()
        layout.addLayout(controls_layout)

        # Settings
        settings_layout = QHBoxLayout()

        settings_layout.addWidget(QLabel("FPS:"))
        self.fps_spin = QSpinBox()
        self.fps_spin.setRange(1, 60)
        self.fps_spin.setValue(10)
        self.fps_spin.valueChanged.connect(self._on_fps_changed)
        self.fps_spin.setToolTip("Frames per second (frame transitions per second)")
        settings_layout.addWidget(self.fps_spin)

        self.loop_cb = QCheckBox("Loop")
        self.loop_cb.setChecked(True)
        self.loop_cb.stateChanged.connect(self._on_loop_changed)
        settings_layout.addWidget(self.loop_cb)

        self.smooth_cb = QCheckBox("Smooth")
        self.smooth_cb.setChecked(True)
        self.smooth_cb.setToolTip("Enable smooth interpolation between frames")
        settings_layout.addWidget(self.smooth_cb)

        settings_layout.addWidget(QLabel("Substeps:"))
        self.substeps_spin = QSpinBox()
        self.substeps_spin.setRange(1, 30)
        self.substeps_spin.setValue(10)
        self.substeps_spin.valueChanged.connect(self._on_substeps_changed)
        self.substeps_spin.setToolTip("Interpolation steps per frame (higher = smoother)")
        settings_layout.addWidget(self.substeps_spin)

        settings_layout.addStretch()
        layout.addLayout(settings_layout)

        self.setLayout(layout)

    def set_trajectory(self, trajectory: TrajectoryObject):
        """Set the trajectory to control"""
        # Stop any current playback
        self._stop_timer()

        self._trajectory = trajectory

        if trajectory is not None:
            self.title_label.setText(f"Trajectory: {trajectory.name}")
            num_frames = trajectory.num_frames

            # Use higher resolution slider for smooth animation
            # Slider range: 0 to (num_frames - 1) * substeps
            slider_max = max(0, (num_frames - 1) * self._substeps) if num_frames > 1 else 0
            self.frame_slider.setMaximum(slider_max)

            # Sync current time with trajectory current frame
            self._current_time = float(trajectory.current_frame)
            self.frame_slider.setValue(int(self._current_time * self._substeps))
            self._update_frame_label()

            # Sync settings from trajectory
            self.fps_spin.setValue(trajectory.fps)
            self.loop_cb.setChecked(trajectory.loop)

            logger.info(f"Trajectory controls set to '{trajectory.name}' with {num_frames} frames")
        else:
            self.title_label.setText("No trajectory selected")
            self.frame_slider.setMaximum(0)
            self.frame_slider.setValue(0)
            self._current_time = 0.0
            self._update_frame_label()

        self._update_enabled_state()

    def clear(self):
        """Clear the current trajectory"""
        self.set_trajectory(None)

    def _update_enabled_state(self):
        """Update enabled state of all controls"""
        has_traj = self._trajectory is not None
        has_frames = has_traj and self._trajectory.num_frames > 0

        self.frame_slider.setEnabled(has_frames)
        self.first_btn.setEnabled(has_frames)
        self.prev_btn.setEnabled(has_frames)
        self.play_btn.setEnabled(has_frames)
        self.stop_btn.setEnabled(has_frames)
        self.next_btn.setEnabled(has_frames)
        self.last_btn.setEnabled(has_frames)
        self.fps_spin.setEnabled(has_traj)
        self.loop_cb.setEnabled(has_traj)

    def _update_frame_label(self):
        """Update the frame counter label"""
        if self._trajectory:
            total = self._trajectory.num_frames
            if self.smooth_cb.isChecked():
                # Show interpolated time with one decimal
                self.frame_label.setText(f"{self._current_time:.1f} / {total - 1}")
            else:
                # Show discrete frame
                current = int(self._current_time)
                self.frame_label.setText(f"{current} / {total - 1}")
        else:
            self.frame_label.setText("0 / 0")

    def _update_play_button(self):
        """Update play button text based on state"""
        if self._trajectory and self._trajectory.is_playing:
            self.play_btn.setText("Pause")
        else:
            self.play_btn.setText("Play")

    # ==================== Event Handlers ====================

    def _on_slider_changed(self, value):
        """Handle slider value change"""
        if self._trajectory and not self._timer.isActive():
            # Convert slider value to continuous time
            self._current_time = value / self._substeps

            if self.smooth_cb.isChecked():
                # Emit time_changed for interpolated rendering
                self._update_frame_label()
                self.time_changed.emit(self._trajectory.uuid, self._current_time)
            else:
                # Discrete frame mode - snap to nearest frame
                frame = int(round(self._current_time))
                self._trajectory.set_frame(frame, send_signals=False)
                self._update_frame_label()
                self.frame_changed.emit(self._trajectory.uuid)

    def _on_first(self):
        """Go to first frame"""
        if self._trajectory:
            self._current_time = 0.0
            self._trajectory.set_frame(0, send_signals=False)
            self._sync_slider()
            self._emit_change()

    def _on_prev(self):
        """Go to previous frame"""
        if self._trajectory:
            # Move to previous integer frame
            self._current_time = max(0.0, float(int(self._current_time) - 1))
            self._trajectory.set_frame(int(self._current_time), send_signals=False)
            self._sync_slider()
            self._emit_change()

    def _on_next(self):
        """Go to next frame"""
        if self._trajectory:
            max_time = float(self._trajectory.num_frames - 1)
            # Move to next integer frame
            self._current_time = min(max_time, float(int(self._current_time) + 1))
            self._trajectory.set_frame(int(self._current_time), send_signals=False)
            self._sync_slider()
            self._emit_change()

    def _on_last(self):
        """Go to last frame"""
        if self._trajectory:
            self._current_time = float(self._trajectory.num_frames - 1)
            self._trajectory.last_frame(send_signals=False)
            self._sync_slider()
            self._emit_change()

    def _emit_change(self):
        """Emit the appropriate change signal based on smooth mode"""
        if self._trajectory:
            if self.smooth_cb.isChecked():
                self.time_changed.emit(self._trajectory.uuid, self._current_time)
            else:
                self.frame_changed.emit(self._trajectory.uuid)

    def _on_play_pause(self):
        """Toggle play/pause"""
        if self._trajectory:
            if self._trajectory.is_playing:
                self._trajectory.pause()
                self._stop_timer()
            else:
                self._trajectory.play()
                self._start_timer()
            self._update_play_button()

    def _on_stop(self):
        """Stop playback and reset to first frame"""
        if self._trajectory:
            self._trajectory.stop()
            self._stop_timer()
            self._current_time = 0.0
            self._sync_slider()
            self._update_play_button()
            self._emit_change()

    def _on_fps_changed(self, value):
        """Handle FPS change"""
        if self._trajectory:
            self._trajectory.fps = value
            # Timer interval is fixed for smooth animation; fps controls time advancement

    def _on_loop_changed(self, state):
        """Handle loop checkbox change"""
        if self._trajectory:
            self._trajectory.loop = (state == Qt.Checked)

    def _on_substeps_changed(self, value):
        """Handle substeps change"""
        old_substeps = self._substeps
        self._substeps = value

        # Update slider range to match new substeps
        if self._trajectory and self._trajectory.num_frames > 1:
            slider_max = (self._trajectory.num_frames - 1) * self._substeps
            self.frame_slider.setMaximum(slider_max)
            # Adjust current slider position proportionally
            self.frame_slider.blockSignals(True)
            self.frame_slider.setValue(int(self._current_time * self._substeps))
            self.frame_slider.blockSignals(False)

    # ==================== Timer Management ====================

    def _start_timer(self):
        """Start the animation timer with fixed interval for smooth updates"""
        if self._trajectory:
            # Use fixed interval for smooth rendering (~60 FPS)
            self._timer.start(ANIMATION_TIMER_INTERVAL_MS)
            logger.debug(f"Animation timer started with {ANIMATION_TIMER_INTERVAL_MS}ms interval")

    def _stop_timer(self):
        """Stop the animation timer"""
        self._timer.stop()
        logger.debug("Animation timer stopped")

    def _on_timer_tick(self):
        """Handle timer tick - advance animation smoothly"""
        if not self._trajectory:
            return

        num_frames = self._trajectory.num_frames
        if num_frames <= 1:
            self._stop_timer()
            self._update_play_button()
            return

        max_time = float(num_frames - 1)

        # Calculate time increment based on FPS setting and timer interval
        # fps = frame transitions per second
        # time_increment = fps * (timer_interval_ms / 1000)
        time_increment = self._trajectory.fps * (ANIMATION_TIMER_INTERVAL_MS / 1000.0)

        # Advance time
        self._current_time += time_increment

        # Handle looping or end of animation
        if self._current_time >= max_time:
            if self._trajectory.loop:
                self._current_time = self._current_time % max_time
            else:
                self._current_time = max_time
                self._stop_timer()
                self._trajectory.pause()
                self._update_play_button()

        # Sync slider and emit signal
        self._sync_slider()

        if self.smooth_cb.isChecked():
            self.time_changed.emit(self._trajectory.uuid, self._current_time)
        else:
            # Discrete mode: only emit when crossing frame boundaries
            frame = int(self._current_time)
            if frame != self._trajectory.current_frame:
                self._trajectory.set_frame(frame, send_signals=False)
                self.frame_changed.emit(self._trajectory.uuid)

    def _sync_slider(self):
        """Sync slider position with current time"""
        if self._trajectory:
            # Block signals to prevent feedback loop
            self.frame_slider.blockSignals(True)
            self.frame_slider.setValue(int(self._current_time * self._substeps))
            self.frame_slider.blockSignals(False)
            self._update_frame_label()
