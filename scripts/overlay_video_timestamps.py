import argparse
import datetime
import os
import sys

import cv2

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "protobuf"))

from recording_pb2 import VideoCaptureData


def build_frame_timestamp_map(video_capture_data):
    """Build frame_number -> timestamp text map from video metadata."""
    video_meta = list(video_capture_data.video_meta)
    if not video_meta:
        raise ValueError("No frame metadata found in video_meta.pb3")

    global_start_ns = int(
        video_capture_data.time.seconds * 1e9 + video_capture_data.time.nanos
    )
    first_frame_boot_ns = min(meta.time_ns for meta in video_meta)

    frame_to_text = {}
    for meta in video_meta:
        global_ns = global_start_ns + (meta.time_ns - first_frame_boot_ns)
        global_dt = datetime.datetime.fromtimestamp(global_ns / 1e9)
        ts_text = global_dt.strftime("%Y-%m-%d %H:%M:%S.%f")
        frame_to_text[int(meta.frame_number)] = f"frame_ts: {ts_text}"
    return frame_to_text


def overlay_timestamps_on_video(input_dir, output_path=None):
    """Load files from directory and overlay pb3 timestamps on matching video frames."""
    pb3_path = os.path.join(input_dir, "video_meta.pb3")
    video_path = os.path.join(input_dir, "video_recording.mp4")

    if not os.path.isdir(input_dir):
        raise FileNotFoundError(f"Directory not found: {input_dir}")
    if not os.path.isfile(pb3_path):
        raise FileNotFoundError(f"Required file not found: {pb3_path}")
    if not os.path.isfile(video_path):
        raise FileNotFoundError(f"Required file not found: {video_path}")

    if output_path is None:
        output_path = os.path.join(input_dir, "video_recording_with_timestamps.mp4")

    with open(pb3_path, "rb") as f:
        video_capture_data = VideoCaptureData.FromString(f.read())

    frame_to_text = build_frame_timestamp_map(video_capture_data)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Failed to open video file: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        fps = 30.0

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    rotate_to_landscape = height > width

    if rotate_to_landscape:
        output_size = (height, width)
    else:
        output_size = (width, height)

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(output_path, fourcc, fps, output_size)
    if not writer.isOpened():
        cap.release()
        raise RuntimeError(f"Failed to create output video: {output_path}")

    frame_index = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Frame numbering in metadata can be 0-based or 1-based.
        ts_text = frame_to_text.get(frame_index)
        if ts_text is None:
            ts_text = frame_to_text.get(frame_index + 1, "frame_ts: N/A")

        if rotate_to_landscape:
            frame = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)

        cv2.putText(
            frame,
            ts_text,
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            (0, 255, 0),
            2,
            cv2.LINE_AA,
        )

        writer.write(frame)
        frame_index += 1

    cap.release()
    writer.release()

    print(f"Done. Output video: {output_path}")
    print(f"Processed frames: {frame_index}")


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Read video_meta.pb3 and video_recording.mp4 from a directory, "
            "then overlay timestamps on corresponding frames."
        )
    )
    parser.add_argument(
        "input_dir", help="Directory containing video_meta.pb3 and video_recording.mp4"
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Optional output video path. Default: <input_dir>/video_recording_with_timestamps.mp4",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    overlay_timestamps_on_video(args.input_dir, args.output)
