# OPKR Enhanced Fork — 개발 가이드

## 작업 전 필독 문서 (CRITICAL)

**코드 수정 전 작업 유형에 맞는 문서를 반드시 읽을 것:**

| 작업 유형 | 필독 문서 | 이유 |
|----------|----------|------|
| 아무 코드 수정이든 | [docs/DEPENDENCY-CHAINS.md](docs/DEPENDENCY-CHAINS.md) | 연쇄 수정 누락 방지 |
| 구조/흐름 파악 | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | 모듈 관계, 데이터 흐름 |
| 튜닝값 변경 | [docs/TUNING.md](docs/TUNING.md) | 스케일 변환, 상호작용, 현재값 |
| Param 관련 작업 | [docs/PARAMS.md](docs/PARAMS.md) | 키/기본값/스케일/읽는 파일 |
| 새 기능 추가 | ARCHITECTURE.md + DEPENDENCY-CHAINS.md 둘 다 | |
| 변경 이력 확인 | [docs/CHANGELOG.md](docs/CHANGELOG.md) | 커밋 히스토리, 설정 이력, 이슈 |

## 기기 접속

| 항목 | 값 |
|------|---|
| 차량 | KIA K5 (DL3) |
| SSH | `ssh -i ~/.ssh/id_ed25519 comma@192.168.0.167` |
| DongleId | 098453cb |

## 배포

```bash
# push 후 기기 반영 (Python만 변경한 경우)
ssh -i ~/.ssh/id_ed25519 comma@192.168.0.167 \
  "cd /data/openpilot && git fetch origin OPKR:refs/remotes/origin/OPKR && git reset --hard origin/OPKR && reboot"
```

```bash
# C++/Cython 변경 시 (params.cc, opkr.cc/h 등) — 반드시 빌드 포함
ssh -i ~/.ssh/id_ed25519 comma@192.168.0.167 \
  "cd /data/openpilot && git fetch origin OPKR:refs/remotes/origin/OPKR && git reset --hard origin/OPKR && scons -j2 && reboot"
```

## 차량 특성

- **longcontrol=False**: 직접 브레이크 불가, 버튼 스패밍으로 속도 제어
- **CAN**: crc8 그룹, cp/cp2/cp_cam 3파서 모두 valid 필요
- **조향**: Torque(3) + Smooth(1)

## 주의

- 주행 로직 수정 가능 (사용자가 실차 테스트 진행)
- Params() 반복 생성 금지 (파일 I/O 병목)

## 새 Param 추가 시 필수 체크리스트 (CRITICAL)

새 파라미터를 추가할 때 **아래 5곳을 반드시 모두 수정**. 하나라도 빠지면 기기 부팅 크래시.

1. **`selfdrive/common/params.cc`** — 키 화이트리스트 등록 (`{"KeyName", PERSISTENT}`)
2. **`selfdrive/manager/manager.py`** — 기본값 등록 (`("KeyName", "default")`)
3. **`selfdrive/assets/addon/script/param_init_value`** — 초기값 (`KeyName:default`)
4. **UI 위젯** (`selfdrive/ui/qt/widgets/opkr.h` + `opkr.cc`) — 선언+구현+등록
5. **기기에서 `scons -j2` 재빌드** — params.cc는 Cython `.so`로 컴파일됨, git pull만으로는 반영 안 됨!

> **2026-04-03 사고 1**: params.cc 화이트리스트 누락 → `UnknownKeyName` 크래시
> **2026-04-03 사고 2**: params.cc 수정 후 scons 빌드 없이 배포 → 동일 크래시 반복

## 배포 전 검증 규칙

- Python 파일: `py_compile.compile()` 구문 검사
- 새 Param: 위 5곳 체크리스트 확인
- C++ 파일(opkr.h/cc): 헤더 선언 ↔ 구현 ↔ FrameXXX 등록 3곳 일치 확인
- **기기 push 전 `git grep "새키이름"`으로 등록 누락 없는지 최종 확인**
- **params.cc 또는 C++ 변경 시 배포 명령에 `scons -j2` 포함 필수**

## 컴파일 필요한 파일 (git pull만으로는 반영 안 됨)

| 파일 | 빌드 산출물 | 빌드 명령 |
|------|-----------|----------|
| `selfdrive/common/params.cc` | `common/params_pyx.so` | `scons -j2 common/params_pyx.so` |
| `selfdrive/ui/qt/widgets/opkr.cc/h` | UI 바이너리 | `scons -j2` (전체) |
| `cereal/*.capnp` | 메시지 정의 | `scons -j2` |

## 상세 문서

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — 제어 루프, 모듈 관계, 데이터 흐름
- [docs/PARAMS.md](docs/PARAMS.md) — 전체 파라미터 카탈로그 (키/기본값/스케일/읽는 파일)
- [docs/DEPENDENCY-CHAINS.md](docs/DEPENDENCY-CHAINS.md) — 수정 시 연쇄 변경 필요한 곳
- [docs/TUNING.md](docs/TUNING.md) — 조향/종방향 튜닝 레퍼런스 (현재값, 상호작용)
- [docs/CHANGELOG.md](docs/CHANGELOG.md) — 변경 내역, 설정 이력, 이슈 현황
