# OPKR 아키텍처 가이드

> Claude가 코드 수정 전 전체 흐름을 파악하기 위한 문서

## 프로세스 구조

```
manager.py (프로세스 매니저)
  ├── controlsd.py      ← 메인 제어 루프 (100Hz)
  ├── plannerd.py        ← 경로 계획 (lateralPlanner + longitudinalPlanner)
  ├── radard.py          ← 레이더 데이터 처리/퓨전
  ├── modeld             ← 신경망 모델 추론 (차선/경로)
  ├── calibrationd       ← 카메라 캘리브레이션
  ├── boardd             ← Panda HW 통신 (CAN 송수신)
  ├── camerad            ← 카메라 입력
  ├── dmonitoringd       ← 운전자 모니터링
  └── 기타 (loggerd, athena, thermald, ...)
```

## 메인 제어 루프 (controlsd.py)

```
100Hz 루프
  ├── CAN 수신 (boardd → can_sock)
  ├── CarState 업데이트 (CI.update → carstate.py)
  ├── 이벤트 처리 (Events)
  ├── 상태 머신 전환 (disabled/pre-enabled/enabled/softDisabling)
  │
  ├── [조향] LaC.update() → 토크 출력
  │     ├── LateralPlanner → desired_curvature 계산
  │     └── LatControl{PID|INDI|LQR|Torque|ATOM} → actuator 출력
  │
  ├── [종방향] LoC.update() → 가감속 출력
  │     ├── LongitudinalPlanner → 속도/가속도 계획
  │     └── LongControl → PID 제어 또는 버튼 스패밍
  │
  └── CAN 송신 (CarController → sendcan)
```

## 파일 맵 — 역할별 분류

### 제어 코어 (`selfdrive/controls/`)

| 파일 | 역할 | 수정 빈도 |
|------|------|----------|
| `controlsd.py` | 메인 루프, 상태머신, Param 읽기, LaC/LoC 호출 | **높음** |
| `lib/latcontrol_torque.py` | Torque 조향 (K5 DL3 기본) — PID + 지연보상 + Jerk FF + 라이브학습 | **높음** |
| `lib/latcontrol_atom.py` | ATOM 하이브리드 조향 (Torque+LQR+INDI+PID 속도별 전환) | 중간 |
| `lib/latcontrol_pid.py` | PID 조향 | 낮음 |
| `lib/latcontrol_lqr.py` | LQR 조향 | 낮음 |
| `lib/latcontrol_indi.py` | INDI 조향 | 낮음 |
| `lib/longcontrol.py` | 종방향 PID + 상태머신 (off/pid/stopping) | 중간 |
| `lib/lateral_planner.py` | 차선/경로 MPC → desired_curvature 계산 | 중간 |
| `lib/longitudinal_planner.py` | 속도 MPC → 가속도 계획 | 중간 |
| `lib/desire_helper.py` | 차선 변경 상태머신 | 낮음 |
| `lib/drive_helpers.py` | 크루즈 속도 업데이트, curvature limit, 유틸리티 | 중간 |
| `lib/lane_planner.py` | 차선 인식 + 모델 path 퓨전 | 낮음 |
| `lib/vehicle_model.py` | 차량 동역학 모델 (curvature ↔ steering angle) | 낮음 |
| `lib/events.py` | 이벤트 정의 (경고, 에러, 인게이지 조건) | 중간 |
| `lib/alertmanager.py` | 경고 표시 관리 | 낮음 |
| `lib/pid.py` | PID/LongPID 컨트롤러 클래스 | 낮음 |
| `lib/drive_stats.py` | 주행 통계 (NEW — 추가 파일) | — |

### 차량 인터페이스 (`selfdrive/car/hyundai/`)

| 파일 | 역할 |
|------|------|
| `interface.py` | CarInterface — 차량 파라미터 설정 (mass, wheelbase, steerRatio, 튜닝 선택) |
| `carcontroller.py` | CAN 메시지 생성/전송 (LKAS, SCC, 버튼 스패밍, HUD) |
| `carstate.py` | CAN 메시지 파싱 → CarState 객체 (속도, 조향각, 크루즈 상태) |
| `navicontrol.py` | 네비/OSM 속도제한, Variable Cruise 로직, 버튼 스패밍 제어 |
| `values.py` | 차종별 상수, CAN 주소, Buttons enum, CarControllerParams |
| `tunes.py` | 조향 튜닝 프리셋 (PID_A~N, TORQUE, LQR, INDI, ATOM) |
| `hyundaican.py` | CAN 메시지 생성 함수 (create_lkas11, create_scc11, ...) |
| `radar_interface.py` | 레이더 설정 |

### UI (`selfdrive/ui/qt/widgets/`)

| 파일 | 역할 |
|------|------|
| `opkr.h` / `opkr.cc` | OPKR 설정 UI 위젯 전체 (66KB/271KB) — Param 슬라이더/토글 |
| `steerWidget.h/cc` | 조향 시각화 |
| `controls.h/cc` | 제어 상태 UI |

### 설정/초기화

| 파일 | 역할 |
|------|------|
| `selfdrive/common/params.cc` | Param 키 화이트리스트 (C++) — **빌드 필요** |
| `selfdrive/manager/manager.py` | default_params 기본값 정의 (40~247행) |
| `selfdrive/assets/addon/script/param_init_value` | 기기 초기화 시 Param 값 |

## 데이터 흐름

### 조향 (Lateral Control)

```
모델(modeld) → lateralPlan.desiredCurvature
                    ↓
controlsd.py → LaC.update(desired_curvature, CS, ...)
                    ↓
latcontrol_torque.py:
  1. 지연보상: curvature_request_buffer에서 360ms 전 요청 꺼냄
  2. 에러 계산: delayed_request - actual_curvature
  3. PID: error → P + I + D
  4. Jerk FF: d(desired_lat_accel)/dt × jerk_gain
  5. Friction FF: sign(error) × friction
  6. 라이브학습: friction/kf 실시간 보정
  7. output_torque 출력
                    ↓
carcontroller.py → create_lkas11(torque) → CAN 전송
                    ↓
차량 MDPS(전동 파워스티어링) 구동
```

### 종방향 (Longitudinal Control) — K5 DL3

```
** longcontrol=False → 직접 가감속 제어 불가 **

모델/레이더 → longitudinalPlan (속도/가속도 계획)
                    ↓
controlsd.py → LoC.update() → 목표 가속도 계산
                    ↓
carcontroller.py → navicontrol.py (Variable Cruise)
  ├── 선행차 거리/속도 기반 목표속도 계산
  ├── 크루즈 버튼 스패밍 (RES_ACCEL / SET_DECEL)
  │     ├── 가속: RES 버튼 반복
  │     └── 감속: SET 버튼 반복 (급접근 시 간격 단축)
  └── create_clu11(button) → CAN 전송

⚠️ 한계: 버튼 스패밍은 1km/h 단위, 반응 지연 존재
⚠️ 정차 시: SCC가 자동 정지, openpilot은 재출발만 담당
```

### Param 읽기 흐름

```
기기 파일시스템 (/data/params/)
  ↓ Params().get() / get_bool()
controlsd.py __init__() — 시작 시 1회 읽기
controlsd.py 300프레임마다 — live_tune 재읽기 (OpkrLiveTunePanelEnable=1일 때)
  ↓
interface.py get_params() — CarParams 구성 시 1회
tunes.py set_lat_tune() — 튜닝값 적용
  ↓
latcontrol_torque.py __init__() — JerkGain, LiveLearning 읽기
latcontrol_torque.py live_tune() — 300프레임마다 재읽기
```

## 조향 제어 방식 (LateralControlMethod)

| 값 | 방식 | 클래스 | 설명 |
|----|------|--------|------|
| 0 | PID | `LatControlPID` | 기본 PID |
| 1 | INDI | `LatControlINDI` | Incremental Non-linear Dynamic Inversion |
| 2 | LQR | `LatControlLQR` | Linear Quadratic Regulator |
| 3 | **Torque** | `LatControlTorque` | **K5 DL3 기본** — 토크 기반 + 지연보상/Jerk/학습 |
| 4 | ATOM | `LatControlATOM` | 하이브리드 (Torque + LQR/INDI/PID 속도별 전환) |
| 5 | Angle | `LatControlAngle` | 각도 직접 제어 (일부 차종) |

## CAN 버스 구조 (현대/기아)

```
CAN 0 (메인):     차량 기본 (속도, 조향각, 크루즈, 기어)
CAN 1 (보조):     MDPS (파워스티어링), SAS (조향각센서)
CAN 2 (카메라):   LKAS (차선유지), LFA (차선추종), SCC (스마트크루즈)
```

- `cp`: CAN 0 파서, `cp2`: CAN 1 파서, `cp_cam`: CAN 2 파서
- 3개 모두 valid해야 인게이지 가능 (canValid 체크)
- K5 DL3: `crc8` 그룹, `sccBus` 자동 감지 (0/1/2/-1)

## 주요 메시징 토픽

| 토픽 | 발행자 | 구독자 | 내용 |
|------|--------|--------|------|
| `carState` | controlsd | UI, plannerd | 차량 상태 (속도, 조향각, 크루즈) |
| `carControl` | controlsd | UI | 제어 명령 (토크, 가속도) |
| `lateralPlan` | plannerd | controlsd | desired_curvature, 차선변경 상태 |
| `longitudinalPlan` | plannerd | controlsd | 속도/가속도 계획 |
| `radarState` | radard | controlsd, plannerd | 선행차 거리/상대속도 |
| `modelV2` | modeld | plannerd | 신경망 예측 (차선, 경로) |
| `liveParameters` | calibrationd | controlsd | steerRatio, angleOffset |
| `sendcan` | controlsd | boardd | CAN 메시지 전송 |
