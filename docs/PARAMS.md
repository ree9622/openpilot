# OPKR 파라미터 카탈로그

> Claude가 Param 관련 작업 시 참조. 키 이름, 기본값, 스케일, 읽는 파일을 한눈에 파악.

## 범례

- **기본값**: manager.py default_params의 값
- **스케일**: 저장값 → 실제값 변환 (`×0.01` = `int(val) * 0.01`)
- **읽는 곳**: 해당 Param을 get()하는 주요 파일
- `bool`: get_bool() 사용, `str`: get() + encoding, `bytes`: get() raw

---

## 1. 조향 튜닝 (Lateral)

### Torque 방식 (LateralControlMethod=3)

| Param | 기본값 | 스케일 | 읽는 곳 |
|-------|--------|--------|---------|
| TorqueKp | 10 | ×0.1 | tunes.py, latcontrol_torque.py |
| TorqueKi | 2 | ×0.1 | tunes.py, latcontrol_torque.py |
| TorqueKf | 10 | ×0.1 | tunes.py, latcontrol_torque.py |
| TorqueFriction | 80 | ×0.001 | tunes.py, latcontrol_torque.py |
| TorqueMaxLatAccel | 27 | ×0.1 | tunes.py, latcontrol_torque.py |
| TorqueAngDeadZone | 10 | ×0.1 | tunes.py, latcontrol_torque.py |
| TorqueUseAngle | 1 | bool | tunes.py, latcontrol_torque.py |
| TorqueJerkGain | 5 | ×0.01 | latcontrol_torque.py |
| TorqueLiveLearning | 1 | bool | latcontrol_torque.py |

> **주의**: Kp/Ki/Kf는 `값 × 0.1 / (MaxLatAccel × 0.1)`로 PID에 입력됨

### PID 방식 (LateralControlMethod=0)

| Param | 기본값 | 스케일 | 읽는 곳 |
|-------|--------|--------|---------|
| PidKp | 25 | ×0.01 | tunes.py |
| PidKi | 40 | ×0.001 | tunes.py |
| PidKd | 150 | ×0.01 | tunes.py |
| PidKf | 7 | ×0.00001 | tunes.py |

### LQR 방식 (LateralControlMethod=2)

| Param | 기본값 | 스케일 | 읽는 곳 |
|-------|--------|--------|---------|
| Scale | 1500 | ×1.0 | tunes.py |
| LqrKi | 16 | ×0.001 | tunes.py |
| DcGain | 265 | ×0.00001 | tunes.py |

### INDI 방식 (LateralControlMethod=1)

| Param | 기본값 | 스케일 | 읽는 곳 |
|-------|--------|--------|---------|
| InnerLoopGain | 35 | ×0.1 | tunes.py |
| OuterLoopGain | 20 | ×0.1 | tunes.py |
| TimeConstant | 14 | ×0.1 | tunes.py |
| ActuatorEffectiveness | 20 | ×0.1 | tunes.py |

### 공통 조향

| Param | 기본값 | 스케일 | 읽는 곳 |
|-------|--------|--------|---------|
| LateralControlMethod | 3 | int(0~4) | interface.py |
| OpkrLiveTunePanelEnable | 0 | bool | controlsd.py, latcontrol_torque.py |
| OpkrLiveSteerRatio | 1 | bool | controlsd.py |
| LiveSteerRatioPercent | 0 | int(%) | controlsd.py |
| SteerRatioAdj | 1550 | ×0.01 | interface.py |
| SteerRatioMaxAdj | 1750 | ×0.01 | controlsd.py |
| SteerActuatorDelayAdj | 30 | ×0.01 | interface.py |
| SteerLimitTimerAdj | 100 | ×0.01 | interface.py |
| TireStiffnessFactorAdj | 100 | ×0.01 | interface.py |
| SteerMaxAdj | 384 | int | controlsd.py, carcontroller.py |
| SteerMaxBaseAdj | 384 | int | carcontroller.py |
| SteerDeltaUpAdj | 3 | int | carcontroller.py |
| SteerDeltaUpBaseAdj | 3 | int | carcontroller.py |
| SteerDeltaDownAdj | 7 | int | carcontroller.py |
| SteerDeltaDownBaseAdj | 7 | int | carcontroller.py |
| DesiredCurvatureLimit | 10 | ×0.01 | drive_helpers.py |

### Smooth Steer

| Param | 기본값 | 스케일 | 읽는 곳 |
|-------|--------|--------|---------|
| OpkrSteerMethod | 1 | int(0~1) | interface.py |
| OpkrMaxSteeringAngle | 90 | float | interface.py |
| OpkrMaxDriverAngleWait | 0.002 | float | interface.py |
| OpkrMaxSteerAngleWait | 0.001 | float | interface.py |
| OpkrDriverAngleWait | 0.001 | float | interface.py |
| OpkrMaxAngleLimit | 90 | int | carcontroller.py |

### 차선변경

| Param | 기본값 | 스케일 | 읽는 곳 |
|-------|--------|--------|---------|
| OpkrLaneChangeSpeed | 30 | int(km/h) | desire_helper.py, controlsd.py |
| OpkrAutoLaneChangeDelay | 0 | int | controlsd.py |
| LCTimingFactorEnable | 1 | bool | controlsd.py |
| LCTimingFactor30 | 10 | int | controlsd.py |
| LCTimingFactor60 | 40 | int | controlsd.py |
| LCTimingFactor80 | 60 | int | controlsd.py |
| LCTimingFactor110 | 80 | int | controlsd.py |

### 다중 조향 (속도/각도별 전환)

| Param | 기본값 | 스케일 | 읽는 곳 |
|-------|--------|--------|---------|
| MultipleLateralUse | 2 | int(0~2) | controlsd.py |
| MultipleLateralOpS | 3,3,0 | CSV | controlsd.py |
| MultipleLateralSpd | 60,90 | CSV(km/h) | controlsd.py |
| MultipleLateralOpA | 3,3,0 | CSV | controlsd.py |
| MultipleLateralAng | 20,35 | CSV(°) | controlsd.py |

---

## 2. 종방향 (Longitudinal / Variable Cruise)

| Param | 기본값 | 스케일 | 읽는 곳 |
|-------|--------|--------|---------|
| OpkrVariableCruise | 1 | bool | controlsd.py |
| VarCruiseSpeedFactor | 10 | int | controlsd.py, navicontrol.py |
| CruiseOverMaxSpeed | 0 | bool | controlsd.py |
| StoppingDist | 38 | ×0.1(m) | longcontrol.py |
| StoppingDistAdj | 0 | bool | carcontroller.py |
| AutoEnableSpeed | 9 | int(km/h) | controlsd.py |
| AutoEnable | 1 | bool | controlsd.py |
| CruiseGap1 | 12 | int | controlsd.py |
| CruiseGap2 | 13 | int | controlsd.py |
| CruiseGap3 | 14 | int | controlsd.py |
| CruiseGap4 | 16 | int | controlsd.py |
| DynamicTRGap | 1 | int | navicontrol.py |
| DynamicTRSpd | 0,20,40,60,110 | CSV | navicontrol.py |
| DynamicTRSet | 1.2,1.3,1.4,1.5,1.6 | CSV | navicontrol.py |
| CustomTREnabled | 1 | bool | controlsd.py |
| RadarLongHelper | 2 | int | carcontroller.py |
| OpkrAutoResume | 1 | bool | carcontroller.py |
| CruiseAutoRes | 0 | bool | carcontroller.py |
| AutoResOption | 0 | int | carcontroller.py |
| AutoResCondition | 0 | int | carcontroller.py |
| AutoRESDelay | 1 | int | carcontroller.py |
| RESCountatStandstill | 19 | int | carcontroller.py |
| AutoResLimitTime | 0 | int | carcontroller.py |
| DepartChimeAtResume | 0 | bool | controlsd.py |
| CruiseGapBySpdOn | 0 | bool | carcontroller.py |
| CruiseGapBySpdSpd | 25,65,130 | CSV | carcontroller.py |
| CruiseGapBySpdGap | 1,2,3,4 | CSV | carcontroller.py |
| E2ELong | 0 | bool | controlsd.py |
| LongLogDisplay | 0 | bool | longcontrol.py |
| CruiseStatemodeSelInit | 1 | int | carcontroller.py |

---

## 3. 속도 제한 / 네비

| Param | 기본값 | 스케일 | 읽는 곳 |
|-------|--------|--------|---------|
| OSMSpeedLimitEnable | 0 | bool | controlsd.py |
| OpkrSpeedLimitOffset | 0 | int | controlsd.py, navicontrol.py |
| OpkrSpeedLimitOffsetOption | 0 | int | controlsd.py, navicontrol.py |
| StockNaviSpeedEnabled | 0 | bool | controlsd.py |
| OPKRNaviSelect | 0 | int | controlsd.py |
| OSMCustomSpeedLimitC | 30,40,50,60,70,90 | CSV | controlsd.py |
| OSMCustomSpeedLimitT | 30,40,65,72,80,95 | CSV | controlsd.py |
| SafetyCamDecelDistGain | 0 | int | navicontrol.py |
| SpeedLimitDecelOff | 0 | bool | navicontrol.py |
| VCurvSpeedC | 30,50,70,90 | CSV | navicontrol.py |
| VCurvSpeedT | 43,58,73,87 | CSV | navicontrol.py |
| OCurvSpeedC | 30,40,50,60,70 | CSV | navicontrol.py |
| OCurvSpeedT | 35,45,60,70,80 | CSV | navicontrol.py |
| CruiseSetwithRoadLimitSpeedEnabled | 0 | bool | controlsd.py |
| CruiseSetwithRoadLimitSpeedOffset | 0 | int | controlsd.py |
| CurvDecelOption | 2 | int | navicontrol.py |
| RoadList | (복합 CSV) | str | controlsd.py |
| RoutineDriveOption | OPKR | str | navicontrol.py |

---

## 4. 경로 / 차선

| Param | 기본값 | 스케일 | 읽는 곳 |
|-------|--------|--------|---------|
| CameraOffsetAdj | 60 | ×0.01(m) | lane_planner.py |
| PathOffsetAdj | 0 | ×0.01(m) | lane_planner.py |
| LanelessMode | 2 | int(0/1/2) | lateral_planner.py |
| LaneWidth | 37 | ×0.1(m) | lateral_planner.py |
| SpdLaneWidthSpd | 0,31 | CSV(m/s) | lateral_planner.py |
| SpdLaneWidthSet | 2.8,3.5 | CSV(m) | lateral_planner.py |
| LeftCurvOffsetAdj | 0 | int | controlsd.py |
| RightCurvOffsetAdj | 0 | int | controlsd.py |
| LeftEdgeOffset | 0 | int | lateral_planner.py |
| RightEdgeOffset | 0 | int | lateral_planner.py |
| CloseToRoadEdge | 0 | bool | lateral_planner.py |

---

## 5. 시스템 / UI / 기기

| Param | 기본값 | 스케일 | 읽는 곳 |
|-------|--------|--------|---------|
| IsMetric | 1 | bool | controlsd.py |
| ComIssueGone | 1 | bool | controlsd.py |
| UFCModeEnabled | 1 | bool | controlsd.py, interface.py |
| OpkrBattLess | 0 | bool | controlsd.py |
| OpkrBatteryChargingControl | 1 | bool | thermald |
| OpkrBatteryChargingMin | 50 | int(%) | thermald |
| OpkrBatteryChargingMax | 60 | int(%) | thermald |
| OpkrAutoShutdown | 2 | int | thermald |
| OpkrForceShutdown | 5 | int | thermald |
| OpkrAutoScreenOff | -2 | int | UI |
| OpkrUIBrightness | 0 | int | UI |
| OpkrUIBrightnessOff | 10 | int | UI |
| OpkrUIVolumeBoost | 0 | int | UI |
| OpkrEnableDriverMonitoring | 1 | bool | dmonitoringd |
| OpkrMonitoringMode | 0 | bool | controlsd.py |
| OpkrEnableLogger | 0 | bool | manager.py |
| OpkrEnableUploader | 0 | bool | manager.py |
| OpkrEnableGetoffAlert | 0 | bool | controlsd.py |
| CommaStockUI | 0 | str | controlsd.py |
| DebugUi1 | 0 | bool | UI |
| DebugUi2 | 0 | bool | UI |
| DebugUi3 | 0 | bool | UI |
| AnimatedRPM | 1 | bool | UI |
| ShowStopLine | 0 | bool | UI |
| TopTextView | 0 | bool | UI |
| LanguageSetting | main_en | str | UI |

---

## 6. 안전 / LKAS

| Param | 기본값 | 스케일 | 읽는 곳 |
|-------|--------|--------|---------|
| StockLKASEnabled | 1 | bool | controlsd.py |
| NoSmartMDPS | 0 | bool | controlsd.py, interface.py |
| OpkrTurnSteeringDisable | 0 | bool | carcontroller.py |
| SteerWarningFix | 0 | bool | carstate.py |
| LdwsCarFix | 0 | bool | carcontroller.py |
| IsLdwEnabled | 0 | bool | controlsd.py |
| AvoidLKASFaultEnabled | 0 | bool | carcontroller.py |
| AvoidLKASFaultMaxAngle | 85 | int | carcontroller.py |
| AvoidLKASFaultMaxFrame | 90 | int | carcontroller.py |
| AvoidLKASFaultBeyond | 0 | bool | carcontroller.py |
| OpkrVariableSteerMax | 0 | bool | carcontroller.py |
| OpkrVariableSteerDelta | 0 | bool | carcontroller.py |
| IgnoreCANErroronISG | 0 | bool | controlsd.py |
| SteerThreshold | 150 | int | carstate.py |

---

## 7. 레이더 / SCC

| Param | 기본값 | 스케일 | 읽는 곳 |
|-------|--------|--------|---------|
| RadarDisable | 0 | bool | interface.py |
| UseRadarTrack | 0 | bool | radar_interface.py |
| FCA11Message | 0 | bool | carcontroller.py |
| OpkrBlindSpotDetect | 1 | bool | carstate.py |
| SetSpeedFive | 0 | bool | carcontroller.py |

---

## Param 작업 시 빠른 참조

```bash
# 특정 Param이 사용되는 모든 위치
grep -rn '"ParamName"' selfdrive/

# manager.py에서 기본값 확인
grep 'ParamName' selfdrive/manager/manager.py

# params.cc 화이트리스트 확인
grep 'ParamName' selfdrive/common/params.cc

# opkr.h/cc UI 위젯 확인
grep 'ParamName' selfdrive/ui/qt/widgets/opkr.h selfdrive/ui/qt/widgets/opkr.cc
```
