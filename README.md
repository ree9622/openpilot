# OPKR Enhanced Fork

> [OPKR (openpilotkr)](https://github.com/openpilotkr/openpilot) 포크 기반 코드 품질 개선 및 한글화 고도화 프로젝트

**원본**: [openpilotkr/openpilot (OPKR branch)](https://github.com/openpilotkr/openpilot/tree/OPKR)  
**이 포크**: [ree9622/openpilot (OPKR branch)](https://github.com/ree9622/openpilot/tree/OPKR)

---

## 이 포크에서 변경된 것

원본 OPKR의 주행 로직은 변경하지 않고, **코드 품질**, **한국어 번역**, **안전 경고**, **디버깅 지원**을 개선했습니다.

### 1. 코드 품질 개선 (`8bfb6ae`)

| 항목 | 변경 내용 | 영향 파일 수 |
|------|----------|-------------|
| **오타 수정** | `LAT_TOROUE` → `LAT_TORQUE`, `Loger` → `Logger`, `defualt` → `default` | 3 |
| **bare except 제거** | `except: pass` → 구체적 예외 타입으로 변경. 자율주행 중 에러가 무시되는 위험 제거 | 4 |
| **Params() 최적화** | `Params()` 반복 생성(최대 40회/init) → 단일 인스턴스 재사용. 부팅 시 파일 I/O 감소 | 6 |
| **Decimal 남용 제거** | `float(Decimal(x) * Decimal('0.01'))` → `int(x) * 0.01`. 13개 파일에서 불필요한 오버헤드 제거 | 13 |
| **죽은 코드 정리** | 미사용 `LatTunes` enum(`PID_B/E/K`), 미사용 `FCA_OPT` 변수, 미사용 `MoveAvg` import 제거 | 4 |
| **Hyundai 디커플링** | 범용 모듈(`longcontrol.py`, `controlsd.py`)에서 `hyundai.values` 직접 import 제거 | 2 |

### 2. 한국어 번역 개선 (`283c2c8`, `0b1d1fe`)

- **미번역 7건** 번역 완료 (CSteerWidget 조향 전환 설정)
- **오역/복붙 오류** 수정 (`시스템` → `스타일`, `프리필트` → `프리빌트`, `RT델다` → `RT델타`)
- **영한 혼재** 제거 (`-value` → `-값`, `자동Resume` → `자동 재개`, `Reboot` → `재부팅 필요`)
- **UI 용어 통일** (`리프레시` → `새로고침`, 탭 이름 `메뉴` 접미사 제거)
- **코드 버그** 수정 (`opkr.cc` 버튼 라벨에 `tr()` 래퍼 누락)

### 3. 설정 설명 강화 (`b31578c`, `0b1d1fe`)

안전 관련 설정에 구체적인 경고와 설명을 추가했습니다:

| 우선순위 | 설정 | 변경 내용 |
|---------|------|----------|
| **CRITICAL** | 종방향 제어 / 레이더 비활성 | AEB 비활성화 경고를 모호한 표현에서 확정적 경고로 변경 |
| **CRITICAL** | E2E Long | "조심하세요" → 딥러닝 모델 설명 + 급감속/급가속 구체적 위험 경고 |
| **CRITICAL** | 스티어링 경고 무시 | 모순적 설명 수정 + 하드웨어 오류 무시 위험 경고 |
| **HIGH** | 자동 재개 / 자동 RES | 자동 가속 경고 추가 |
| **MEDIUM** | PID Kp/Ki/Kd/Kf | "조정" → 각 게인의 실제 조향 효과 설명 |
| **MEDIUM** | SteerRatio, CameraOffset, PathOffset 등 | 파라미터명 반복 → 실제 운전 영향 설명 |

**총 35+ 설정 설명 개선**

### 4. CAN 에러 디버깅 지원 (`6fbf02a`)

K5 DL3 등에서 시동 직후 인게이지 실패(경고음) 문제 디버깅을 위한 코드:

- **시동 후 5초 Grace Period**: CAN bus 안정화 전 `canError` 이벤트 억제
- **디버그 로깅 강화**: CAN 실패 시 어떤 파서(`cp`/`cp2`/`cp_cam`)가 실패인지 + 차속 + 크루즈 상태 출력

```
CAN_INVALID cp=True cp2=True cp_cam=False vEgo=0.0 cruiseActive=False
```

### 5. 모듈 레벨 최적화 (`3f9993d`)

- `desire_helper.py`: `Params()` 호출 4회 → 1회로 감소
- `carstate.py`: `__init__`에서 `Params()` 인스턴스 재사용
- 미사용 코드 제거 (`MoveAvg`, `FCA_OPT`)

---

## 설치 방법

### 기존 OPKR 사용자 (기기에서)

```bash
cd /data/openpilot
git remote set-url origin https://github.com/ree9622/openpilot.git
git fetch origin OPKR:refs/remotes/origin/OPKR
git reset --hard origin/OPKR
reboot
```

### 새로 설치

```bash
cd /data
mv openpilot openpilot_bak
git clone https://github.com/ree9622/openpilot.git -b OPKR
reboot
```

### 원본 OPKR로 복구

```bash
cd /data/openpilot
git remote set-url origin https://github.com/openpilotkr/openpilot.git
git fetch origin OPKR
git reset --hard origin/OPKR
reboot
```

---

## 지원 차량

OPKR 원본과 동일. 현대/기아/제네시스 37개 차종:

**현대**: 아반떼(AD/CN7/HEV), i30(PD), 쏘나타(DN8/HEV/LF/터보/HEV LF), 투싼(TL), 싼타페(TM/HEV), 팰리세이드(LX2), 코나(OS/HEV/EV), 아이오닉(HEV/EV), 넥쏘(FE), 그랜저(IG/HEV/FL)

**기아**: K5(JF/HEV/DL3/HEV DL3), K7(YG/HEV), 셀토스(SP2), 니로(HEV/EV), 쏘울 EV(SK3), 스팅어(CK), 모하비(HM)

**제네시스**: G70(IK/2020), G80(DH), G90(HI), EQ900(HI), DH

---

## 디버깅 (개발자용)

### SSH 접속

```bash
ssh comma@<기기IP>
```

### CAN 에러 로그 확인

```bash
# 실시간
logcat | grep -E "CAN_INVALID|grace|canError"

# 인게이지 실패 시
logcat -d | grep -E "CAN_INVALID|grace" | tail -20
```

### 로그 출력 형식

```
CAN grace period: can_rcv_error=False canValid=True timer=100/500
CAN_INVALID cp=True cp2=True cp_cam=False vEgo=0.0 cruiseActive=False
```

- `cp`: 메인 CAN 파서
- `cp2`: 보조 CAN 파서
- `cp_cam`: 카메라 CAN 파서
- `grace timer`: 시동 후 CAN 안정화 대기 시간 (500프레임 = 5초)

---

## 커밋 히스토리

| 커밋 | 설명 |
|------|------|
| `6fbf02a` | CAN 에러 grace period + 디버그 로깅 |
| `0b1d1fe` | 설정 설명 TIER 3-4 개선 |
| `3f9993d` | 모듈 레벨 Params 최적화, 죽은 코드 제거 |
| `b31578c` | 안전 경고 강화, 기술 용어 설명 추가 |
| `283c2c8` | 한국어 번역 개선 (미번역, 오역, 일관성) |
| `8bfb6ae` | 코드 품질 (오타, Decimal, Params, 디커플링) |

---

## 원본 OPKR 정보

OPKR은 현대/기아/제네시스 차량에 특화된 [comma.ai openpilot](https://github.com/commaai/openpilot) 포크입니다.

주요 기능: Variable Cruise (버튼 스패밍), UFC 모드, ATOM 하이브리드 조향, OSM 속도 제한, 라이브 튜닝, SmartMDPS 지원, SCC 자동 감지, 2개 프리셋 저장 등.

자세한 OPKR 기능은 [원본 README](https://github.com/openpilotkr/openpilot/tree/OPKR)를 참조하세요.

---

## 라이선스

openpilot is released under the MIT license. See [LICENSE](LICENSE) for details.

**이 소프트웨어는 연구 목적의 알파 품질 소프트웨어입니다. 제품이 아닙니다. 현지 법규를 준수할 책임은 사용자에게 있습니다. 명시적이거나 묵시적인 어떠한 보증도 없습니다.**
