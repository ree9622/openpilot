# 의존성 체인 — 수정 시 반드시 함께 확인

> Claude가 코드 수정 시 연쇄 변경이 필요한 곳을 빠뜨리지 않기 위한 문서

## 1. 새 Param 추가 (CRITICAL — 부팅 크래시)

**5곳 모두 수정 필수**:

```
selfdrive/common/params.cc          ← 화이트리스트 {"KeyName", PERSISTENT}
selfdrive/manager/manager.py        ← default_params ("KeyName", "기본값")
selfdrive/assets/addon/script/param_init_value  ← KeyName:기본값
selfdrive/ui/qt/widgets/opkr.h      ← 위젯 클래스 선언
selfdrive/ui/qt/widgets/opkr.cc     ← 위젯 구현 + FrameXXX 등록
```

**검증**: `git grep "KeyName"` → 5곳 모두 나와야 함  
**빌드**: params.cc 또는 opkr.h/cc 수정 → `scons -j2` 필수  
**사고 이력**: 2026-04-03 화이트리스트 누락 → UnknownKeyName 크래시

---

## 2. 조향 튜닝 파라미터 변경

한 곳만 바꾸면 다른 곳과 불일치 발생:

```
manager.py (default_params)     ← 기본값 정의
  ↓ 연동
tunes.py (set_lat_tune)         ← CarParams에 반영 (스케일 변환 주의)
  ↓ 연동
latcontrol_torque.py (live_tune) ← 300프레임마다 재읽기 (같은 스케일 변환)
  ↓ 연동 (ATOM 사용 시)
latcontrol_atom.py              ← ATOM은 내부에 torque 속성 초기화 필요
```

**스케일 변환 규칙** (실수 단골):

| Param 키 | 저장값 | 스케일 | 실제값 예시 |
|----------|--------|--------|------------|
| TorqueKp | `10` | × 0.1 | 1.0 |
| TorqueKf | `10` | × 0.1 | 1.0 |
| TorqueKi | `2` | × 0.1 | 0.2 |
| TorqueFriction | `80` | × 0.001 | 0.080 |
| TorqueMaxLatAccel | `27` | × 0.1 | 2.7 |
| TorqueAngDeadZone | `10` | × 0.1 | 1.0 |
| TorqueJerkGain | `5` | × 0.01 | 0.05 |
| SteerRatioAdj | `1550` | × 0.01 | 15.50 |
| SteerActuatorDelayAdj | `30` | × 0.01 | 0.30 (초) |
| TireStiffnessFactorAdj | `100` | × 0.01 | 1.00 |
| SteerLimitTimerAdj | `100` | × 0.01 | 1.00 |

**실제 PID에 들어가는 값**: `kp = TorqueKp * 0.1 / (TorqueMaxLatAccel * 0.1)`

---

## 3. Variable Cruise (버튼 스패밍) 수정

```
navicontrol.py              ← 메인 로직 (목표속도 계산, 버튼 결정)
  ↓ 호출
carcontroller.py            ← update() 안에서 navicontrol 호출, CAN 전송
  ↓ 참조
controlsd.py                ← variable_cruise 플래그, v_cruise_kph 관리
  ↓ 참조
drive_helpers.py            ← update_v_cruise (크루즈 속도 업데이트)
  ↓ 참조
values.py                   ← Buttons enum, CarControllerParams
```

**주의**: navicontrol.py의 버튼 결정 로직은 carcontroller.py의 `self.resume_cnt`, `self.last_resume_frame` 등과 타이밍이 연동됨

---

## 4. CAN 메시지 추가/변경

```
opendbc/can/hyundai_*.dbc   ← CAN 메시지/시그널 정의
  ↓
hyundaican.py               ← create_XXX() 메시지 생성 함수
  ↓
carcontroller.py            ← 메시지 전송 (어느 CAN 버스로 보낼지)
  ↓
carstate.py                 ← 메시지 파싱 (어느 CAN 버스에서 읽을지)
  ↓
values.py                   ← 주소, DBC 이름, fingerprint
```

---

## 5. 차선변경 로직 수정

```
desire_helper.py            ← 차선변경 상태머신 (state, direction, timer)
  ↓ 참조
lateral_planner.py          ← desire → MPC에 반영
  ↓ 참조
controlsd.py                ← lane_change_delay, 깜빡이 연동
  ↓ 참조
carcontroller.py            ← 깜빡이 상태에 따른 토크 제한
```

---

## 6. 조향 제어 방식 추가 (새 LatControl)

```
selfdrive/controls/lib/latcontrol_XXX.py  ← 새 컨트롤러 구현
  ↓ 등록
controlsd.py (156~174행)                  ← elif 분기 추가
  ↓ 등록
tunes.py                                  ← LatTunes enum + set_lat_tune() 분기
  ↓ 등록
interface.py (97~107행)                   ← LateralControlMethod 분기
  ↓ UI
opkr.h/cc                                ← 드롭다운/슬라이더 항목 추가
```

---

## 7. 이벤트/경고 추가

```
selfdrive/controls/lib/events.py         ← 이벤트 정의 + 핸들러
  ↓
cereal/car.capnp                         ← EventName enum 추가 (빌드 필요)
  ↓
selfdrive/controls/controlsd.py          ← 이벤트 트리거 조건
  ↓
selfdrive/assets/addon/lang/events/*.txt ← 한국어/영어 메시지
```

---

## 8. C++ UI 위젯 수정 (opkr.h/cc)

```
opkr.h      ← 클래스 선언 (멤버변수, 메서드 시그니처)
  ↕ 반드시 일치
opkr.cc     ← 구현 + FrameXXX에 위젯 등록
  ↓ 빌드
scons -j2   ← git pull만으로는 반영 안 됨
```

**3곳 일치 확인**: 헤더 선언 ↔ 구현 ↔ Frame 등록

---

## 9. cereal 메시지 변경

```
cereal/*.capnp              ← 메시지 스키마 정의
  ↓ 빌드
scons -j2                   ← Python/C++ 바인딩 재생성
  ↓ 사용처
controlsd.py                ← 메시지 발행/구독
plannerd.py                 ← 메시지 발행/구독
UI 코드                     ← 메시지 표시
```

---

## 빠른 체크 명령어

```bash
# 새 Param이 모든 곳에 등록됐는지 확인
git grep "NewParamName"

# 특정 Param을 읽는 모든 곳 찾기
grep -rn '"TorqueKi"' selfdrive/

# C++ 헤더 ↔ 구현 불일치 확인
diff <(grep "class\|void\|int\|QString" selfdrive/ui/qt/widgets/opkr.h | head -20) \
     <(grep "::" selfdrive/ui/qt/widgets/opkr.cc | head -20)
```
