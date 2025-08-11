""" Visualize experimental data """


from farms_app.extensions.base import CustomExtension
from imgui_bundle import imgui, implot3d, implot
from imgui_bundle import portable_file_dialogs as pfd
import numpy as np
import pandas as pd
import OpenGL.GL as GL  # type: ignore
import time
import cv2


class ExperimentalExtension(CustomExtension):
    """ Experimental """

    def __init__(self):
        self.show_window = True
        self.window_name = "experimental"
        self._io = imgui.get_io()
        self.data = {}
        self.frame = 100
        self.performance_warnings = []
        self.play = True

        self.current_frame = None
        self.texture_id = 0
        self.frame_width = 0
        self.frame_height = 0
        self.total_frames = 0
        self.current_frame_idx = 0
        self.fps = 30.0
        self.is_playing = False
        self.is_loaded = False
        self.last_frame_time = 0

        self.video_path = "/Users/tatarama/Downloads/LTKS-9152022-WK4-8-C3-cropped.mp4"
        self.cap = None

    def get_name(self) -> str:
        return "Experimental Data Viewer"

    def update_texture(self):
        """Update OpenGL texture with current frame"""
        if self.current_frame is None:
            return

        # Generate texture if not exists
        if self.texture_id == 0:
            self.texture_id = GL.glGenTextures(1)

        GL.glBindTexture(GL.GL_TEXTURE_2D, self.texture_id)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_LINEAR)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_LINEAR)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_S, GL.GL_CLAMP_TO_EDGE)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_T, GL.GL_CLAMP_TO_EDGE)

        GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_RGB,
                       self.frame_width, self.frame_height, 0,
                       GL.GL_RGB, GL.GL_UNSIGNED_BYTE, self.current_frame)
        GL.glBindTexture(GL.GL_TEXTURE_2D, 0)

    def load_video(self):
        """Load a video file"""
        try:
            if self.cap:
                self.cap.release()

            self.cap = cv2.VideoCapture(self.video_path)
            if not self.cap.isOpened():
                print(f"Error: Could not open video {self.video_path}")
                return False

            self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self.fps = self.cap.get(cv2.CAP_PROP_FPS)
            self.frame_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            self.frame_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            self.current_frame_idx = 0
            self.is_loaded = True

            # Read first frame
            self.read_frame()

            print(f"Loaded video: {self.video_path}")
            print(f"Resolution: {self.frame_width}x{self.frame_height}")
            print(f"FPS: {self.fps}, Total frames: {self.total_frames}")

            return True

        except Exception as e:
            print(f"Error loading video: {e}")
            return False

    def read_frame(self):
        """Read current frame from video"""
        if not self.cap or not self.is_loaded:
            return False

        ret, frame = self.cap.read()
        if ret:
            # Convert BGR to RGB for OpenGL
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            self.current_frame = frame_rgb
            self.update_texture()
            return True
        return False

    def seek_frame(self, frame_idx):
        """Seek to specific frame"""
        if not self.is_loaded or not self.cap:
            return

        frame_idx = max(0, min(frame_idx, self.total_frames - 1))
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        self.current_frame_idx = frame_idx
        self.read_frame()

    def cleanup(self):
        """Cleanup resources"""
        if self.cap:
            self.cap.release()
        if self.texture_id != 0:
            GL.glDeleteTextures([self.texture_id])

    def render_window(self) -> None:
        imgui.text("---   File dialogs   ---")
        if imgui.button("Load"):
            self.result = pfd.open_file("Load csv", default_path="", filters=("*.csv",), options=pfd.opt.multiselect).result()
            self.data["left"] = pd.read_csv(self.result[0])
            self.data["right"] = pd.read_csv(self.result[1])
            self.load_video()

            # # Columns to reverse
            # cols_to_reverse = self.data['left'].columns[2:]  # leave first two columns untouched

            # # Find indices of NaN separator rows (anywhere in the row)
            # nan_rows = self.data['left'][self.data['left'].isna().any(axis=1)].index

            # # Add boundaries
            # boundaries = [-1] + nan_rows.tolist() + [len(self.data['left'])]

            # # Reverse only the selected columns in each block
            # for start, end in zip(boundaries, boundaries[1:]):
            #     block = self.data['left'].iloc[start+1:end]
            #     self.data['left'].loc[start+1:end-1, cols_to_reverse] = block[cols_to_reverse].iloc[::-1].values

        if self.data:
            button_name = "Pause" if self.play else "Play"
            if imgui.button(button_name):
                self.play = not self.play
            if self.play:
                time.sleep(0.01)
            self.seek_frame(self.frame)
            if imgui.begin_child("Video", child_flags=imgui.ChildFlags_.borders | imgui.ChildFlags_.resize_x | imgui.ChildFlags_.resize_y):
                imgui.image(
                    int(self.texture_id),
                    imgui.ImVec2((self.frame_width, self.frame_height)),
                    uv0=imgui.ImVec2((0,0)),
                    uv1=imgui.ImVec2((1,1)),
                    # border_color=imgui.ImVec4((1, 0, 0, 1))
                )
            imgui.end_child()
            imgui.same_line()
            if implot3d.begin_plot("Mouse"):
                axes_flags = implot.AxisFlags_.lock | implot.AxisFlags_.no_grid_lines | implot.AxisFlags_.no_tick_marks
                implot3d.set_next_line_style(weight=2.0)
                implot3d.setup_box_scale(x=5.0, y=1.0, z=1.0)
                implot3d.setup_axes_limits(0, 800, -25.0, 160, 0, 100)
                implot3d.setup_box_initial_rotation(-85.0, 180.0)
                implot3d.setup_axis(implot3d.ImAxis3D_.x, label="x", flags=axes_flags)
                implot3d.setup_axis(implot3d.ImAxis3D_.y, label="y", flags=axes_flags)
                implot3d.setup_axis(implot3d.ImAxis3D_.z, label="z", flags=axes_flags)
                for side, data in self.data.items():
                    implot3d.set_next_marker_style(implot3d.Marker_.circle)
                    implot3d.plot_line(
                        f"{side}-hind",
                        np.array(
                            (
                                data["iliac_x"][self.frame],
                                data["hip_x"][self.frame],
                                data["knee_x"][self.frame],
                                data["ankle_x"][self.frame],
                                data["toe_x"][self.frame],
                            )
                        ),
                        np.array(
                            (
                                data["iliac_y"][self.frame],
                                data["hip_y"][self.frame],
                                data["knee_y"][self.frame],
                                data["ankle_y"][self.frame],
                                data["toe_y"][self.frame],
                            )
                        ),
                        np.array(
                            (
                                data["iliac_z"][self.frame],
                                data["hip_z"][self.frame],
                                data["knee_z"][self.frame],
                                data["ankle_z"][self.frame],
                                data["toe_z"][self.frame],
                            )
                        ),
                    )
                    implot3d.set_next_marker_style(implot3d.Marker_.circle)
                    implot3d.plot_line(
                        f"{side}-fore",
                        np.array(
                            (
                                data["shoulder_x"][self.frame],
                                data["elbow_x"][self.frame],
                                data["wrist_x"][self.frame],
                                data["finger_x"][self.frame],
                            )
                        ),
                        np.array(
                            (
                                data["shoulder_y"][self.frame],
                                data["elbow_y"][self.frame],
                                data["wrist_y"][self.frame],
                                data["finger_y"][self.frame],
                            )
                        ),
                        np.array(
                            (
                                data["shoulder_z"][self.frame],
                                data["elbow_z"][self.frame],
                                data["wrist_z"][self.frame],
                                data["finger_z"][self.frame],
                            )
                        ),
                    )
                implot3d.end_plot()

            if implot.begin_subplots("Joint angles", 3, 1, (-1, -1)):
                start_idx = max(0, self.frame - 100 + 1)
                end_idx = self.frame + 1
                if implot.begin_plot(""):
                    implot.plot_line("left-hip", np.array(self.data["left"]["hip_angle"][start_idx:end_idx]))
                    implot.plot_line("right-hip", np.array(self.data["right"]["hip_angle"][start_idx:end_idx]))
                    implot.end_plot()
                if implot.begin_plot(""):
                    implot.plot_line("left-knee", np.array(self.data["left"]["knee_angle"][start_idx:end_idx]))
                    implot.plot_line("right-knee", np.array(self.data["right"]["knee_angle"][start_idx:end_idx]))
                    implot.end_plot()
                if implot.begin_plot(""):
                    implot.plot_line("left-ankle", np.array(self.data["left"]["ankle_angle"][start_idx:end_idx]))
                    implot.plot_line("right-ankle", np.array(self.data["right"]["ankle_angle"][start_idx:end_idx]))
                    implot.end_plot()

                implot.end_subplots()

            if self.frame < min(len(self.data['left']), len(self.data['right'])) - 1:
                if self.play:
                    self.frame += 1
            else:
                self.frame = 0
