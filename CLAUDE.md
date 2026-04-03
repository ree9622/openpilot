# OPKR Enhanced Fork — 개발 가이드

## 기기 접속

| 항목 | 값 |
|------|---|
| 차량 | KIA K5 (DL3) |
| SSH | `ssh -i ~/.ssh/id_ed25519 comma@192.168.0.167` |
| DongleId | 098453cb |

## 배포

```bash
# push 후 기기 반영
ssh -i ~/.ssh/id_ed25519 comma@192.168.0.167 \
  "cd /data/openpilot && git fetch origin OPKR:refs/remotes/origin/OPKR && git reset --hard origin/OPKR"
```

## 차량 특성

- **longcontrol=False**: 직접 브레이크 불가, 버튼 스패밍으로 속도 제어
- **CAN**: crc8 그룹, cp/cp2/cp_cam 3파서 모두 valid 필요
- **조향**: Torque(3) + Smooth(1)

## 주의

- 주행 로직 수정 금지 (실차 테스트 없이)
- Params() 반복 생성 금지 (파일 I/O 병목)

## 상세 문서

- [docs/CHANGELOG.md](docs/CHANGELOG.md) — 변경 내역, 설정 이력, 이슈 현황
