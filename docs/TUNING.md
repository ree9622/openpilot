# 튜닝 레퍼런스 — K5 DL3

> Claude가 튜닝 파라미터 수정 시 각 값의 의미, 상호작용, 현재 설정을 참조하기 위한 문서

## 차량 기본 특성

| 항목 | 값 | 비고 |
|------|---|------|
| 차종 | KIA K5 (DL3) | `CAR.K5_DL3` |
| 질량 | 1515 + 136(화물) = 1651 kg | |
| 휠베이스 | 2.85 m | |
| longcontrol | **False** | 직접 가감속 불가, 버튼 스패밍만 |
| CAN 그룹 | crc8 | |
| 조향 방식 | Torque(3) + Smooth(1) | LateralControlMethod=3, OpkrSteerMethod=1 |

## 조향 튜닝 (Torque 방식)

### 핵심 파라미터

| Param | 저장값 | 스케일 | 실제값 | 역할 | 올리면 | 내리면 |
|-------|--------|--------|--------|------|--------|--------|
| **TorqueKp** | 10 | ×0.1÷maxLatAccel | 0.37 | 비례 게인 — 에러에 즉각 반응 | 반응 빠름, 떨림↑ | 반응 느림, 안정↑ |
| **TorqueKi** | 2 | ×0.1÷maxLatAccel | 0.074 | 적분 게인 — 잔류 오차 제거 | 차선 중앙↑, 오버슈트↑ | 오프셋 남음 |
| **TorqueKf** | 10 | ×0.1÷maxLatAccel | 0.37 | 피드포워드 — 커브 진입 시 선제 조향 | 커브 반응↑ | 커브 지연 |
| **TorqueFriction** | 80 | ×0.001 | 0.080 | 마찰 보상 — 핸들 데드존 극복 | 떨림↓, 핸들 무거움↑ | 핸들 자유로움, 떨림↑ |
| **TorqueMaxLatAccel** | 27 | ×0.1 | 2.7 | 최대 횡가속도 — Kp/Ki/Kf 분모 | 게인 전체↓ (보수적) | 게인 전체↑ (공격적) |
| **TorqueAngDeadZone** | 10 | ×0.1 | 1.0° | 조향각 데드존 — 미세 떨림 무시 | 직진 안정↑, 반응↓ | 민감↑ |
| **TorqueUseAngle** | 1 | bool | true | 조향각 센서 사용 (false→자이로) | 저속 안정 | 고속 정밀 |

### 실제 PID 입력값 계산

```python
max_lat_accel = TorqueMaxLatAccel * 0.1  # 2.7
kp = TorqueKp * 0.1 / max_lat_accel      # 10 * 0.1 / 2.7 = 0.37
ki = TorqueKi * 0.1 / max_lat_accel      # 2 * 0.1 / 2.7 = 0.074
kf = TorqueKf * 0.1 / max_lat_accel      # 10 * 0.1 / 2.7 = 0.37
friction = TorqueFriction * 0.001         # 80 * 0.001 = 0.080
```

### 개선 기능 (stock openpilot 백포트)

| 기능 | Param | 기본값 | 설명 |
|------|-------|--------|------|
| **지연보상** | SteerActuatorDelayAdj | 30 (→0.30초) | 과거 요청 vs 현재 측정 비교로 위상 지연 제거 |
| **Jerk FF** | TorqueJerkGain | 5 (→0.05) | 조향 전환 시 응답 개선 (d(lat_accel)/dt) |
| **라이브학습** | TorqueLiveLearning | 1 (on) | friction/kf를 실시간 선형회귀로 학습 |

**라이브학습 조건**: 54km/h↑, 인게이지 2초↑, 비과격 주행  
**라이브학습 범위**: 초기값 대비 ±30%, EMA(0.995) 스무딩  
**우선순위**: OpkrLiveTunePanelEnable=1이면 학습 비활성 (수동 튜닝 우선)

---

## 차량 동역학 파라미터

| Param | 저장값 | 스케일 | 실제값 | 역할 |
|-------|--------|--------|--------|------|
| **SteerRatioAdj** | 1550 | ×0.01 | 15.50 | 핸들 회전비 — 클수록 핸들 많이 돌려야 |
| **SteerActuatorDelayAdj** | 30 | ×0.01 | 0.30초 | MDPS 반응 지연 — 지연보상 버퍼 크기 결정 |
| **TireStiffnessFactorAdj** | 100 | ×0.01 | 1.00 | 타이어 강성 — 클수록 민첩, 작으면 부드러움 |
| **SteerLimitTimerAdj** | 100 | ×0.01 | 1.00초 | 조향 제한 타이머 |
| **SteerRatioMaxAdj** | 1750 | ×0.01 | 17.50 | 라이브 SR 최대값 |
| **LiveSteerRatioPercent** | 0 | 그대로 | 0% | SR 인위적 보정 (제거됨) |

### SteerRatio와 지연보상의 상호작용

```
SteerRatio ↑ → 같은 curvature에 더 큰 조향각 필요 → 토크 ↑
ActuatorDelay ↑ → 지연보상 버퍼 길어짐 → 더 과거 요청과 비교
  → delay가 실제보다 크면: 언더스티어 보상 → 오버슈트
  → delay가 실제보다 작으면: 보상 부족 → 진동 잔존
```

---

## 종방향 튜닝 (Variable Cruise)

### 기본 PID 값 (tunes.py OPKR)

| 게인 | BP (속도 m/s) | 값 | 비고 |
|------|---------------|---|------|
| Kp | [0,4,9,17,23,31] | [0.5, 0.5, 0.5, 0.5, 0.5, 0.5] | 전 속도 동일 |
| Ki | 〃 | [0, 0, 0, 0, 0, 0] | **비활성** |
| Kd | 〃 | [0, 0, 0, 0, 0, 0] | **비활성** |
| Kf | 〃 | [1, 1, 1, 1, 1, 1] | FF만 작동 |

> longcontrol=False이므로 PID 출력은 직접 사용되지 않음.  
> 실제 감속/가속은 **버튼 스패밍**으로만 이루어짐.

### Variable Cruise 핵심 설정

| Param | 기본값 | 역할 |
|-------|--------|------|
| VarCruiseSpeedFactor | 8 | 선행차 추종 시 속도 예측 배수 (낮을수록 일찍 감속) |
| OpkrVariableCruise | 1 | Variable Cruise 활성화 |
| CruiseGap1~4 | 차간 갭 설정 (초) | |
| DynamicTRGap/Spd/Set | 동적 TR 설정 | |
| StoppingDist | — | 정차 거리 (×0.1m) |
| AutoEnableSpeed | 17 | 자동 인게이지 속도 (km/h) |
| DepartChimeAtResume | 1 | 선행차 출발 알림음 |

---

## Smooth Steer (OpkrSteerMethod=1)

| Param | 기본값 | 역할 |
|-------|--------|------|
| OpkrSteerMethod | 1 | 0=기본, 1=Smooth |
| OpkrMaxSteeringAngle | 90 | 최대 조향각 (°) |
| OpkrMaxDriverAngleWait | 0.002 | 운전자 개입 대기 |
| OpkrMaxSteerAngleWait | 0.001 | 조향 대기 |
| OpkrDriverAngleWait | 0.001 | 운전자 각도 대기 |

---

## 현재 기기 설정값 (2026-04-03 기준)

| 카테고리 | Param | 값 | 변경 이유 |
|----------|-------|---|----------|
| 안전 | ComIssueGone | 0 | 에러 무시하면 원인 추적 불가 |
| 안전 | AutoEnableSpeed | 17 | 주차장 오인게이지 방지 |
| 튜닝 | TorqueKi | 2 | 차선 중앙 유지 개선 |
| 튜닝 | TorqueFriction | 80 | 핸들 떨림 감소 |
| 튜닝 | SteerActuatorDelayAdj | 30 | 36→30 (실차 반응 맞춤) |
| 튜닝 | TireStiffnessFactorAdj | 100 | 85→100 (타이어 강성 보정) |
| 튜닝 | TorqueJerkGain | 5 | Jerk FF 활성화 |
| 튜닝 | TorqueLiveLearning | 1 | 라이브 학습 활성화 |
| 종방향 | VarCruiseSpeedFactor | 8 | 10→8 (일찍 감속) |
| UI | DebugUi1 | 1 | 디버깅용 |
| UI | AnimatedRPM | 0 | UI 부하 줄임 |
| 배터리 | OpkrBatteryChargingMax | 75 | 배터리 수명 보호 |
| SR | LiveSteerRatioPercent | 0 | 인위적 보정 제거 |
| 알림 | DepartChimeAtResume | 1 | 선행차 출발 알림 |

---

## 튜닝 변경 시 체크리스트

1. **스케일 변환 확인** — 저장값 × 스케일 = 의도한 실제값인지
2. **MaxLatAccel 분모 효과** — Kp/Ki/Kf는 MaxLatAccel로 나눠짐, MaxLatAccel 변경 시 전부 영향
3. **live_tune 동기화** — tunes.py와 latcontrol_torque.py의 스케일 변환이 동일한지
4. **ATOM 호환** — ATOM 사용자도 있으므로 torque 관련 속성 변경 시 latcontrol_atom.py도 확인
5. **manager.py 기본값** — 새 사용자가 받을 기본값이 합리적인지
6. **실차 테스트** — 직진, 완만 커브, 급커브, 고속도로 합류 순서로 검증
