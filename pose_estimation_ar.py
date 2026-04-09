from pathlib import Path

import cv2 as cv
import numpy as np
from PIL import Image, ImageSequence


CHECKERBOARD = (7, 5)
SQUARE_SIZE = 1.0
INPUT_VIDEO = "chessboard.mp4"
OUTPUT_VIDEO = "pose_estimation_result.mp4"
PANEL_WIDTH_RATIO = 0.8 #사이즈 크기 
ASSET_CANDIDATES = [
    Path("assets/character.gif"),
    Path("assets/character.png"),
]


def build_object_points(pattern_size, square_size):
    objp = np.zeros((pattern_size[0] * pattern_size[1], 3), np.float32)
    grid = np.mgrid[0 : pattern_size[0], 0 : pattern_size[1]].T.reshape(-1, 2)
    objp[:, :2] = grid * square_size
    return objp


def choose_asset_path():
    for asset_path in ASSET_CANDIDATES:
        if asset_path.exists():
            return asset_path

    print("Character asset not found.")
    print("Place one of the following files:")
    for asset_path in ASSET_CANDIDATES:
        print(f"- {asset_path}")
    raise SystemExit


def rgba_to_bgra(arr):
    return cv.cvtColor(arr, cv.COLOR_RGBA2BGRA)


def add_alpha_from_white_background(img_bgr, threshold=245):
    img_gray = cv.cvtColor(img_bgr, cv.COLOR_BGR2GRAY)
    alpha = np.where(img_gray >= threshold, 0, 255).astype(np.uint8)
    return np.dstack((img_bgr, alpha))


def load_png_asset(asset_path):
    character = cv.imread(str(asset_path), cv.IMREAD_UNCHANGED)
    if character is None:
        print(f"Failed to load character asset: {asset_path}")
        raise SystemExit

    if character.ndim == 2:
        character = cv.cvtColor(character, cv.COLOR_GRAY2BGRA)
        character[:, :, 3] = 255
    elif character.ndim == 3 and character.shape[2] == 3:
        character = add_alpha_from_white_background(character)
    elif character.ndim == 3 and character.shape[2] == 4:
        pass
    else:
        print("Unsupported PNG format.")
        raise SystemExit

    return [character]


def load_gif_asset(asset_path):
    frames = []
    with Image.open(asset_path) as gif:
        for frame in ImageSequence.Iterator(gif):
            rgba = frame.convert("RGBA")
            frame_np = np.array(rgba)
            frames.append(rgba_to_bgra(frame_np))

    if not frames:
        print(f"Failed to decode GIF frames: {asset_path}")
        raise SystemExit

    return frames


def load_asset_frames(asset_path):
    suffix = asset_path.suffix.lower()
    if suffix == ".gif":
        return load_gif_asset(asset_path)
    if suffix == ".png":
        return load_png_asset(asset_path)

    print(f"Unsupported asset type: {asset_path.suffix}")
    raise SystemExit


def get_billboard_points(pattern_size, square_size, image_shape):
    board_width = (pattern_size[0] - 1) * square_size
    board_height = (pattern_size[1] - 1) * square_size

    img_h, img_w = image_shape[:2]
    aspect_ratio = img_h / img_w

    panel_width = board_width * PANEL_WIDTH_RATIO
    panel_height = panel_width * aspect_ratio

    x0 = (board_width - panel_width) * 0.5
    x1 = x0 + panel_width
    y_ground = board_height * 0.95
    z_top = -panel_height

    return np.float32(
        [
            [x0, y_ground, 0.0],
            [x1, y_ground, 0.0],
            [x1, y_ground, z_top],
            [x0, y_ground, z_top],
        ]
    )


def alpha_blend_warped(frame, warped_bgr, warped_alpha):
    alpha = warped_alpha.astype(np.float32) / 255.0
    alpha = alpha[..., None]
    frame[:] = (
        warped_bgr.astype(np.float32) * alpha
        + frame.astype(np.float32) * (1.0 - alpha)
    ).astype(np.uint8)


def overlay_character(frame, character_bgra, projected_quad):
    h, w = frame.shape[:2]
    src_h, src_w = character_bgra.shape[:2]

    src_quad = np.float32(
        [
            [0, src_h - 1],
            [src_w - 1, src_h - 1],
            [src_w - 1, 0],
            [0, 0],
        ]
    )
    dst_quad = np.float32(projected_quad).reshape(4, 2)
    H = cv.getPerspectiveTransform(src_quad, dst_quad)

    character_bgr = character_bgra[:, :, :3]
    character_alpha = character_bgra[:, :, 3]

    warped_bgr = cv.warpPerspective(
        character_bgr,
        H,
        (w, h),
        flags=cv.INTER_LINEAR,
        borderMode=cv.BORDER_CONSTANT,
        borderValue=(0, 0, 0),
    )
    warped_alpha = cv.warpPerspective(
        character_alpha,
        H,
        (w, h),
        flags=cv.INTER_LINEAR,
        borderMode=cv.BORDER_CONSTANT,
        borderValue=0,
    )

    alpha_blend_warped(frame, warped_bgr, warped_alpha)


def draw_axes(frame, rvec, tvec, K, dist):
    axis = np.float32(
        [
            [0, 0, 0],
            [2.0, 0, 0],
            [0, 2.0, 0],
            [0, 0, -2.0],
        ]
    )
    axis_img, _ = cv.projectPoints(axis, rvec, tvec, K, dist)
    axis_img = np.int32(axis_img).reshape(-1, 2)
    origin = tuple(axis_img[0])
    cv.line(frame, origin, tuple(axis_img[1]), (0, 0, 255), 3, cv.LINE_AA)
    cv.line(frame, origin, tuple(axis_img[2]), (0, 255, 0), 3, cv.LINE_AA)
    cv.line(frame, origin, tuple(axis_img[3]), (255, 0, 0), 3, cv.LINE_AA)


def main():
    data = np.load("calibration_data.npz")
    K = data["mtx"]
    dist = data["dist"]

    asset_path = choose_asset_path()
    asset_frames = load_asset_frames(asset_path)
    board_points = build_object_points(CHECKERBOARD, SQUARE_SIZE)
    billboard_points = get_billboard_points(CHECKERBOARD, SQUARE_SIZE, asset_frames[0].shape)

    video = cv.VideoCapture(INPUT_VIDEO)
    if not video.isOpened():
        print(f"Cannot open input video: {INPUT_VIDEO}")
        raise SystemExit

    writer = None
    frame_idx = 0
    print(f"Running camera pose estimation and AR overlay with {asset_path.name}... (ESC to quit)")

    while True:
        valid, frame = video.read()
        if not valid:
            break

        gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
        found, corners = cv.findChessboardCorners(
            gray,
            CHECKERBOARD,
            cv.CALIB_CB_ADAPTIVE_THRESH + cv.CALIB_CB_NORMALIZE_IMAGE,
        )

        status_text = "Chessboard not found"

        if found:
            corners = cv.cornerSubPix(
                gray,
                corners,
                (11, 11),
                (-1, -1),
                (cv.TERM_CRITERIA_EPS + cv.TERM_CRITERIA_MAX_ITER, 30, 0.001),
            )

            success, rvec, tvec = cv.solvePnP(board_points, corners, K, dist)
            if success:
                projected_quad, _ = cv.projectPoints(
                    billboard_points, rvec, tvec, K, dist
                )
                asset_frame = asset_frames[frame_idx % len(asset_frames)]
                overlay_character(frame, asset_frame, projected_quad)
                draw_axes(frame, rvec, tvec, K, dist)
                cv.drawChessboardCorners(frame, CHECKERBOARD, corners, found)
                status_text = f"Pose estimated + {asset_path.suffix[1:].upper()} overlay"

        if writer is None:
            frame_size = (frame.shape[1], frame.shape[0])
            writer = cv.VideoWriter(
                OUTPUT_VIDEO,
                cv.VideoWriter_fourcc(*"mp4v"),
                30.0,
                frame_size,
            )

        cv.putText(
            frame,
            status_text,
            (10, 30),
            cv.FONT_HERSHEY_DUPLEX,
            0.7,
            (0, 255, 0),
            1,
        )
        cv.imshow("Camera Pose Estimation and AR", frame)
        writer.write(frame)

        if cv.waitKey(30) & 0xFF == 27:
            break

        frame_idx += 1

    video.release()
    if writer is not None:
        writer.release()
    cv.destroyAllWindows()

    print(f"Saved {OUTPUT_VIDEO}")


if __name__ == "__main__":
    main()
