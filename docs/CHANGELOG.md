# OPKR Enhanced Fork — 변경 내역

## 커밋 히스토리

| 커밋 | 날짜 | 설명 |
|------|------|------|
| `fbd05ec` | 2026-07-19 | 크루즈 버튼 프레임 처리 및 차량/OpenPilot 최고 설정 속도 동기화 수정 |
| `ea526c5` | 2026-04-03 | CLAUDE.md: scons 빌드 필수 규칙 추가 |
| `ae9b816` | 2026-04-03 | params.cc: TorqueJerkGain/TorqueLiveLearning 화이트리스트 등록 |
| `e8ed7ff` | 2026-04-03 | UI: Jerk 피드포워드 슬라이더 + 라이브 토크 학습 토글 추가 |
| `797172a` | 2026-04-03 | 튜닝: SteerActuatorDelay 36→30, TireStiffness 85→100, CurvatureLimit 10→20 |
| `3237355` | 2026-04-03 | variable cruise: 재활성화 시 VSetDis로 cruise_max_speed 초기화 |
| `cb473d4` | 2026-04-03 | variable cruise: 선행차 추종 후 설정 속도 복귀 안 되는 버그 수정 |
| `fbb9bb7` | 2026-04-03 | 조향 컨트롤러 3대 개선 (지연보상/Jerk FF/라이브학습) |
| `b8721ff` | 2026-04-03 | CLAUDE.md 추가 |
| `13114a1` | 2026-04-03 | 선행차 급접근 시 감속 반응 개선 |
| `204950c` | 2026-04-03 | 레이더 기반 선행차 출발 알림 추가 |
| `35f53d8` | 2026-04-03 | README 재작성 |
| `0b1d1fe` | 2026-04-03 | 설정 설명 TIER 3-4 개선 |
| `3f9993d` | 2026-04-03 | 모듈 레벨 Params 최적화, 죽은 코드 제거 |
| `b31578c` | 2026-04-03 | 안전 경고 강화, 기술 용어 설명 추가 |
| `283c2c8` | 2026-04-03 | 한국어 번역 개선 |
| `8bfb6ae` | 2026-04-03 | 코드 품질 (오타, Decimal, Params, 디커플링) |
| `6fbf02a` | 2026-04-03 | CAN error grace period + 디버그 로깅 |

---

## 코드 변경 상세

### 1. 코드 품질 개선 (`8bfb6ae`)

- 오타: `LAT_TOROUE`→`LAT_TORQUE`, `Loger`→`Logger`, `defualt`→`default`
- bare except 5곳 → 구체적 예외 타입 (`Exception`, `ValueError`, `IndexError`, `IOError`)
- Params() 반복 생성 제거: controlsd 26회, navicontrol 20회, values 3회 → 단일 인스턴스
- Decimal 남용 제거: 13개 파일에서 `float(Decimal(x)*Decimal('0.01'))` → `int(x)*0.01`
- 죽은 LatTunes enum (PID_B/E/K) 제거, PID_N 추가
- longcontrol.py, controlsd.py에서 hyundai.values import 제거 → 로컬 상수

### 2. 한국어 번역 (`283c2c8`, `0b1d1fe`)

- 미번역 7건 번역 (CSteerWidget 조향 전환)
- 오역/복붙 오류 수정 (`시스템`→`스타일`, `프리필트`→`프리빌트`, `RT델다`→`RT델타`)
- 영한 혼재 제거 (`-value`→`-값`, `자동Resume`→`자동 재개`, `Reboot`→`재부팅 필요`)
- UI 용어 통일 (`리프레시`→`새로고침`, 탭 이름 `메뉴` 접미사 제거)
- opkr.cc 버튼 `tr()` 누락 수정

### 3. 설정 설명 강화 (`b31578c`, `0b1d1fe`)

**안전 관련 (CRITICAL)**
- 종방향 제어/레이더 비활성: AEB 경고 모호→확정
- E2E Long: "조심하세요"→딥러닝 설명+급감속/급가속 경고
- 스티어링 경고 무시: 모순적 설명 수정+하드웨어 오류 경고
- 자동 재개/자동 RES: 자동 가속 경고 추가

**기술 용어 설명 (22건)**
- PID Kp/Ki/Kd/Kf, SteerRatio, ActuatorDelay, CameraOffset/PathOffset
- UFC, OSM, TR, LKAS, BSM, MDPS 약어 풀이

### 4. CAN Error Grace Period (`6fbf02a`)

- controlsd.py: 시동 후 5초간 canError 이벤트 억제
- interface.py: CAN invalid 시 cp/cp2/cp_cam 상태+차속+크루즈 로깅

### 5. 모듈 레벨 최적화 (`3f9993d`)

- desire_helper.py: Params() 4회→1회
- carstate.py: 미사용 FCA_OPT 제거, Params 재사용
- navicontrol.py: 미사용 MoveAvg 제거

### 6. 레이더 기반 선행차 출발 알림 (`204950c`)

- 정차 3초 + 선행차 1.5m+ 이동 → "띵동" 차임
- E2ELong 없이 작동 (기존 e2e_standstill은 E2ELong 의존)
- 설정: DepartChimeAtResume=1

### 7. 선행차 급접근 감속 개선 (`13114a1`)

- 선행차 25m 이내 + 상대속도 -10km/h 이하 → 버튼 간격 5~7 프레임으로 단축
- VarCruiseSpeedFactor 10→8 (4초 앞 예측으로 일찍 감속)

---

## 기기 설정 변경 이력 (2026-04-03)

| 설정 | 한글명 | 변경 전 | 변경 후 | 이유 |
|------|--------|--------|--------|------|
| ComIssueGone | 통신에러 알림 끄기 | 1 | **0** | 에러 무시하면 원인 추적 불가 |
| AutoEnableSpeed | 자동 인게이지 속도 | 9 | **17** | 주차장 오인게이지 방지 |
| OpkrBatteryChargingMax | 최대 배터리 충전 | 60 | **75** | 배터리 수명 보호 |
| DebugUi1 | 디버그 보기 1 | 0 | **1** | 디버깅용 |
| RTShield | RTShield 프로세스 | 1 | **0** | CPU/메모리 절약 |
| LiveSteerRatioPercent | 라이브SR 조정 | -5 | **0** | 인위적 보정 제거 |
| DepartChimeAtResume | 출발 시 차임 | 0 | **1** | 선행차 출발 알림 |
| AnimatedRPM | RPM 애니메이션 | 1 | **0** | UI 부하 줄임 |
| ShowStopLine | 정지선 표시 | 1 | **0** | E2ELong=0이면 불필요 |
| EndToEndToggle | E2E 토글 | 1 | **0** | E2ELong=0과 불일치 해소 |
| VarCruiseSpeedFactor | 변속크루즈 속도 계수 | 10 | **8** | 일찍 감속 시작 |
| TorqueKi | 토크 적분 게인 | 1 | **2** | 차선 중앙 유지 개선 |
| TorqueFriction | 토크 마찰 보상 | 65 | **80** | 핸들 떨림 감소, 학습 초기값 개선 |

---

## 추천 설정값 (K5 DL3)

| 설정 | 한글명 | 값 | 설명 |
|------|--------|---|------|
| OpkrLaneChangeSpeed | 차선변경 최소속도 | 30 | 30km/h 미만 차선변경 차단 |
| OpkrAutoLaneChangeDelay | 차선변경 지연 | 0 (Nudge) | 깜빡이+핸들터치 |
| LCTimingFactor30/60/80/110 | 차선변경 시간 | 10/40/60/80 | 기본값 |
| CurvOffset (L/R) | 커브 오프셋 | 0/0 | 모델이 이미 처리 |
| OpkrSteerMethod | 스티어링 모드 | 1 (Smooth) | 부드러운 전환 |
| LateralControlMethod | 조향 제어 | 3 (Torque) | K5 DL3 적합 |
| LaneWidth | 차선폭 | 37 (3.7m) | 실시간 수렴 |

---

### 8. 조향 컨트롤러 3대 개선 (stock openpilot 백포트)

**파일**: `selfdrive/controls/lib/latcontrol_torque.py`, `latcontrol_atom.py`

**8-1. 조향 지연 보상 버퍼 (Delay Compensation)**
- stock openpilot의 핵심 개선사항 백포트
- `steerActuatorDelay`(K5 기본 360ms) 만큼 과거의 요청 curvature와 현재 측정값을 비교
- 기존: "지금 원하는 것" vs "지금 측정값" → 위상 지연으로 오버슈트/진동
- 개선: "360ms 전에 원한 것" vs "지금 측정값" → 위상 지연 제거
- `curvature_request_buffer`: deque 기반 링 버퍼

**8-2. Jerk 피드포워드 (Jerk Feedforward)**
- `desired_lateral_jerk = d(desired_lateral_accel)/dt`
- 조향 전환 시 (직진→커브, 커브→직진) 응답 지연 감소
- `JERK_GAIN = 0.05` (보수적, 실차 튜닝 필요)

**8-3. 라이브 토크 학습 (LiveTorqueLearner)**
- stock openpilot `torqued` 데몬의 핵심 알고리즘을 경량 인라인 구현
- 54km/h 이상, 인게이지 2초 후, 비과격 주행 시 (output_torque, actual_lat_accel) 수집
- 선형 회귀로 friction과 kf 보정계수를 실시간 학습
- 초기값 대비 ±30% 범위 제한, EMA(0.995) 스무딩
- OpkrLiveTunePanelEnable=1이면 학습 비활성 (수동 튜닝 우선)
- 타이어 마모, 노면 상태, 차량 개체차에 자동 적응

**ATOM 호환**: `LatCtrlToqATOM`에 동일 속성 초기화 추가 — ATOM(3) + Smooth(1) 설정에서 정상 작동

---

## 알려진 이슈

### 인게이지 간헐적 실패

- **증상**: 시동 후 크루즈 누르면 가끔 경고음+실패
- **추정 원인**: CAN bus 안정화 전 canError
- **대책**: 5초 grace period (`6fbf02a`)
- **확인**: `logcat -d | grep CAN_INVALID`
- **상태**: 실차 검증 필요

### 선행차 감속 시 브레이크 부족

- **증상**: 앞차 감속 시 수동 브레이크 필요
- **원인**: longcontrol=False, 버튼 스패밍 속도 한계
- **대책**: 급접근 시 버튼 간격 단축 + VarCruiseSpeedFactor 8
- **상태**: 실차 검증 필요
