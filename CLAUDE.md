# OPKR Enhanced Fork — 개발 가이드

## 기기 접속 정보

| 항목 | 값 |
|------|---|
| 차량 | KIA K5 (DL3) |
| 기기 IP | 192.168.0.167 |
| SSH | `ssh -i ~/.ssh/id_ed25519 comma@192.168.0.167` |
| SSH 키 | `~/.ssh/id_ed25519` (GitHub ree9622에 등록) |
| DongleId | 098453cb |
| OS | Android aarch64, kernel 3.18.20-Comma+ |

## 기기 배포 방법

```bash
# 로컬에서 push 후
ssh -i ~/.ssh/id_ed25519 comma@192.168.0.167 \
  "cd /data/openpilot && git fetch origin OPKR:refs/remotes/origin/OPKR && git reset --hard origin/OPKR"
```

## 차량 특성 (K5 DL3)

- **longcontrol=False**: 오픈파일럿이 직접 브레이크/가속 불가. 순정 SCC가 담당.
- **속도 제어**: 크루즈 SET/RES 버튼 스패밍(navicontrol.py)으로 목표속도만 조절
- **CAN 특성**: crc8 그룹, cp/cp2/cp_cam 3개 파서 모두 valid 필요
- **조향**: Torque 컨트롤러(method=3), Smooth 모드(method=1)

## 주의사항

- **주행 로직 수정 금지**: 테스트 환경(실차) 없이 제어 알고리즘 변경하지 말 것
- **carcontroller.py**: 1245줄짜리 update(). 리팩토링하려면 실차 테스트 필수
- **Params()**: 파일시스템 기반 key-value. 반복 생성하면 I/O 병목 발생
- **CAN error**: 시동 직후 5초 grace period 적용됨 (controlsd.py)

## 로그 확인

```bash
# CAN 에러
logcat -d | grep -E "CAN_INVALID|grace|canError"

# 프로세스 상태
ps aux | grep -E 'controlsd|pandad|manager'

# 설정값 확인
cat /data/params/d/<ParamName>
```

## Git 구조

- **origin**: ree9622/openpilot (이 포크)
- **upstream**: openpilotkr/openpilot (원본 OPKR)
