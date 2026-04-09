# Third_Impact

컴퓨터비전 HW4 `Camera Pose Estimation and AR` 과제를 위한 프로젝트입니다.  
HW3에서 구한 카메라 캘리브레이션 결과를 재사용하여 체커보드의 자세를 추정하고, 그 위에 2D 캐릭터 PNG/GIF를 AR 형태로 시각화했습니다.

## 유튜브영상
## Demo

[![Demo](https://img.youtube.com/vi/cdSFtEpmWYY/0.jpg)](https://youtu.be/cdSFtEpmWYY)

## 프로젝트 목표

- HW3의 카메라 내부 파라미터와 왜곡 계수를 재사용한다.
- 입력 영상에서 체커보드 코너를 검출한다.
- `cv.solvePnP()`를 이용해 카메라 자세를 추정한다.
- 추정된 pose를 바탕으로 2D 캐릭터 이미지를 체커보드 위에 세운 판처럼 투영한다.

## 사용 파일

- `pose_estimation_ar.py`
  - HW4 메인 실행 파일
  - 체커보드 검출, pose estimation, AR 오버레이 수행
- `camera_calibration.py`
  - HW3에서 사용한 카메라 캘리브레이션 코드
- `distortion_correction.py`
  - HW3 결과 확인용 왜곡 보정 코드
- `calibration_data.npz`
  - 카메라 행렬과 왜곡 계수 저장 파일
- `chessboard.mp4`
  - 입력 영상
- `assets/character.gif`
  - 애니메이션 AR 캐릭터 파일
- `assets/character.png`
  - 정적 AR 캐릭터 파일

## 사용한 캘리브레이션 결과

HW3에서 구한 calibration 결과를 그대로 사용했습니다.

Camera matrix:

```text
[[1.20552422e+03 0.00000000e+00 6.44908485e+02]
 [0.00000000e+00 1.21234616e+03 3.57918243e+02]
 [0.00000000e+00 0.00000000e+00 1.00000000e+00]]
```

Distortion coefficients:

```text
[[ 2.74702871e-01 -1.82186265e+00  7.79881090e-04 -3.74130709e-03
   4.29483939e+00]]
```

## 구현 방법

1. `calibration_data.npz`에서 카메라 행렬 `K`와 왜곡 계수 `dist`를 불러온다.
2. 영상 프레임마다 `cv.findChessboardCorners()`로 체커보드 코너를 검출한다.
3. `cv.cornerSubPix()`로 코너를 정밀하게 보정한다.
4. 체커보드의 3D 기준점과 검출된 2D 코너를 이용해 `cv.solvePnP()`를 수행한다.
5. 선택한 PNG/GIF 캐릭터를 3D 평면 위의 billboard로 가정하고 `cv.projectPoints()`와 perspective transform으로 영상 위에 합성한다.
6. pose가 잘 추정되는지 확인하기 위해 3축 좌표축도 함께 그린다.

## AR 오브젝트 설명

- 단순한 와이어프레임 박스 대신, 사용자가 원하는 2D 캐릭터 이미지가 AR 오브젝트가 되도록 구현했다.
- `GIF` 파일을 사용할 경우 여러 프레임을 순서대로 읽어 애니메이션처럼 표시할 수 있다.
- `PNG` 파일도 사용할 수 있으며, 투명 배경이 있으면 더 자연스럽게 합성된다.

## 실행 방법

필수 패키지 설치:

```bash
python -m pip install opencv-python numpy Pillow
```

메인 실행:

```bash
python pose_estimation_ar.py
```

실행 전 아래 파일 중 하나를 준비해야 합니다.

```text
assets/character.gif
assets/character.png
```

참고:

```bash
python camera_calibration.py
python distortion_correction.py
```

## 결과

- 체커보드가 정상적으로 검출되는 구간에서는 카메라 자세가 추정되고, 그 위에 캐릭터 이미지가 AR 형태로 표시되었다.
- GIF를 사용할 경우 캐릭터가 움직이는 것처럼 보여 정적인 박스보다 더 눈에 띄는 AR 결과를 얻을 수 있었다.
- 좌표축도 함께 표시하여 pose estimation이 실제로 작동하고 있음을 확인할 수 있었다.

## 한계점

- 체커보드가 영상에서 일부 잘린 상태로 촬영되면 코너를 충분히 검출하지 못해 AR이 나타나지 않았다.
- 체커보드가 너무 작게 보이거나 많이 기울어진 경우 pose estimation이 불안정할 수 있다.
- 조명이 너무 강하거나 반사가 심하면 체커보드 코너 검출 성능이 떨어질 수 있다.
- PNG에 투명 배경이 없으면 합성 결과가 다소 부자연스러울 수 있다.

## 정리

이번 과제에서는 HW3의 카메라 캘리브레이션 결과를 바탕으로, 체커보드 pose estimation과 애니 장면 AR 시각화를 구현했다.  
기본적인 큐브 대신 원하는 캐릭터 PNG/GIF를 사용할 수 있도록 확장하여, 더 직관적이고 재미있는 AR 결과를 만들 수 있었다.
