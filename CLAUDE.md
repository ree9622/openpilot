# OPKR Enhanced Fork — 개발 가이드

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

- [docs/CHANGELOG.md](docs/CHANGELOG.md) — 변경 내역, 설정 이력, 이슈 현황
