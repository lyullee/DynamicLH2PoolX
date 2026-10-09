# DynamicLH2PoolX v0.2 Stage C 완료 보고서

완료일: 2026-09-11  
프로토콜: `dynamiclh2poolx_stage_c_restricted_20260911`  
통합 판정: `PASS_RESTRICTED_STAGE_C_COMPONENT_SCOPE`

## 결론과 적용 범위

감사에서 발견된 C0 결함을 수정하고, C1 해 검증, C2 JUEL 보류시험 재평가,
C3 HSE Test 6 제한 평가를 모두 통과했다. 따라서 v0.2 동적 경로는 **선언된
지표 도달 유입과 평탄한 표면의 매끄러운 축대칭 풀 source-term** 범위에서
제한적 검증 완료 상태다. 이 문자열은 전체 pool-formation 모델의 검증을 뜻하지
않는다.

이 판정은 분사 충돌과 지표 도달률, 비축대칭 가지·분리 액편, 경사·배수·방벽,
응축 공기 고체 침적, 복잡 지형 또는 기상 확산을 검증했다는 뜻이 아니다. 직전
FFI 논문 계산은 정적 LH2PoolX v0.1.2 observed-footprint 경로를 유지하며,
이번 결과로 과거 source reconstruction을 소급 교체하지 않는다.

## C0 — 감사 결함 해결

- `dry_depth_m` 이하의 양의 수심을 더 이상 삭제하지 않는다. 수치 양성 보정은
  `cumulative_numerical_mass_adjustment_kg`에 명시적으로 기록한다.
- 1.0e-7 kg 미소 유입 회귀시험에서 최종 재고는 약 1.0e-7 kg이고 미기록
  잔차는 -7.94e-23 kg, 상대값은 -7.94e-16이다.
- 계산 상태인 `wet_area_m2`와 관측 연산자인 `reported_radius_m` /
  `reported_area_m2`를 분리했다. 액체가 0.635 kg 남은 감사 반례에서 보고
  면적을 0으로 만들어도 wet-area 평균 열유속 754.77 W/m2와 증발 플럭스는
  0으로 사라지지 않는다.
- `interval_mean_evaporation_rate_kg_s`와
  `last_substep_evaporation_rate_kg_s`를 분리했다.
- 증발 운동량의 기본 closure는 JUEL 식 4.19에서 이탈 증기의 반경속도를 0으로
  두는 `zero_radial_momentum_vapor`로 결과를 보기 전에 고정했다.
  `liquid_velocity_carryoff`는 구조 민감도에만 사용한다.
- 설정 형식·음수 retention depth·잘못된 closure를 생성 단계에서 거부하며,
  결과에 설정 echo와 Python/NumPy/CoolProp 버전을 저장한다.

관련 회귀시험을 포함해 Python 3.12에서 총 50개 테스트가 통과한다.

## C1 — 수치 해 검증

JUEL 알루미늄 Trial 6의 60 s 상태를 사용하고 source annulus 경계를 셀 face에
정렬했다. `dr=0.02/0.01/0.005 m`는 각각 2/4/8개 셀로 같은 annulus를
표현하며, `dr=0.04 m`의 비정렬 결과는 진단값으로만 보존한다.

| 검증 | 세분 비교 | 반경 절대변화 | 액체재고 상대변화 | 누적증발 상대변화 |
|---|---|---:|---:|---:|
| 공간, `dt=0.005 s` | `dr 0.01 -> 0.005 m` | 0.000000 m | 0.2932% | 0.00377% |
| 결합 | `dr=dt 0.01 -> 0.005` | 0.000000 m | 0.2923% | 0.00376% |

각 비교의 coarse/fine 반경 원자료와 6자리 표시값은 convergence manifest에
함께 남겼다. 반경 값이 같은 것은 반올림으로 숨긴 것이 아니라 이 관측 연산자에서
두 해가 동일한 cell-face 반경을 반환했기 때문이다.

영역 반경 1.2 m와 1.6 m 결과는 같고 경계 유출은 0이다. 관측 전면 깊이를
0.5/0.75/1.0 mm로 바꾸면 반경은 0.47/0.45/0.44 m이므로, 이 변화는 해
오차와 섞지 않고 관측 연산자 불확실성으로 보고한다. 기본/대안 운동량 closure의
60 s 반경은 0.45/0.49 m이며 대안 결과로 기본값을 교체하지 않았다. 알루미늄의
0.40은 Trial 5에서 사전 보정해 동결한 값이며, 0.45의 약간 낮은 holdout RMSE는
사후 선택 근거로 쓰지 않았다.

판정: `PASS_STAGE_C_SOLUTION_VERIFICATION`.

## C2 — JUEL 보류시험과 불확실성 표현

관측값·프로토콜·출처 manifest를 코드에서 분리하고 Trial 3/5를 보정,
Trial 4/6을 보류시험으로 유지했다.

| 보류시험 | 반경 RMSE | MAE | bias | 영상 반경구간 포함률 |
|---|---:|---:|---:|---:|
| 물 Trial 4 | 0.1374 m | 0.1222 m | -0.0778 m | 100% |
| 알루미늄 Trial 6 | 0.1016 m | 0.0920 m | +0.0040 m | 100% |

재료별 보정 trial이 하나뿐이므로 trial bootstrap 95% CI를 만들지 않았다.
대신 Figure 5.24/5.25 판독구간과 사전 선언한 열전달 파라미터 민감도를
`parameter_sensitivity_not_ci`로 저장했다. 민감도 결과 중 RMSE가 가장 작은
값을 사후 선택해 기본 계수를 바꾸지 않았다.

판정: `PASS_RESTRICTED_SPREADING`.

## C3 — HSE Test 6 제한 평가

분류는 **same-case-thermal-input-constrained independent radius assessment**다.
같은 사례의 초기 지반온도 266 K를 입력으로 사용하고 RR985의 GASP 기본
콘크리트 물성 `k=0.93 W/(m K)`, `alpha=4.8e-7 m2/s`를 사용했으므로 엄밀한
독립 외부검증이라고 부르지 않는다. 반경 관측값으로 계수를 맞추지는 않았다.

RR986의 시험 ID·수직 하향·100 mm 높이와 RR985 Figure 2/Table 6/Figure 9를
각각 고유 source ID로 동결했다. RR985 본문의 10 mm 표기는 RR986와 충돌하므로
입력에서 제외했다. RR985가 보고한 콘크리트 거칠기/잔류 puddle 깊이 5 mm를
물리 입력으로 선언했으며, 4/5/6 mm 민감도를 모두 저장했다.

| 항목 | 관측/관문 | 계산 |
|---|---:|---:|
| 방출 종료 반경 | 0.9–1.0 m | 0.92 m |
| 방출 후 열전대 정의 건조 | 12–22 s | 19 s |
| 질량수지 잔차 | 보존 관문 | 4.76e-13 kg |
| 최대 절대 미기록 잔차 | 보존 관문 | 8.24e-13 kg |
| 수치 질량조정 / 경계유출 | 0 요구 | 0 / 0 kg |

정확한 재고 소진시각과 열전대의 `T < 30 K` 건조 판정은 같은 관측량이 아니다.
또한 RR985가 응축 공기 고체 침적과 연결한 1.3–1.4 m 팽창·후퇴 피크는 재현하지
못했다. 따라서 전 방출 궤적 RMSE 0.438 m는 **전체 궤적을 재현하지 못했다는
진단값**으로 공개하고, 종점 반경과 건조시간 관문과 분리한다.

판정: `PASS_HSE_RADIUS_ASSESSMENT_ENDPOINTS_WITH_STRUCTURAL_LIMITATION`.

## 재현성과 산출물

- `data/stage_c_protocol.json`: 계산 전 고정한 closure·격자·관문
- `data/source_manifest.json`: 시험 번호·방향·그림/표의 고유 ID
- `data/juel3155_radius_observations.csv`: JUEL 판독점과 역할
- `data/hse_rr985_test6_radius.csv`: HSE Figure 2 판독점과 오차
- `outputs/stage_c/convergence/manifest.json`: C1 수치 행렬
- `outputs/spreading_validation/manifest.json`: JUEL 지표와 민감도
- `outputs/stage_c/hse_test6/manifest.json`: HSE 입력·결과·구조 제한
- `data/stage_c_evidence.json`: 공개 저장소에 추적되는 핵심 지표·범위·hash snapshot
- `outputs/stage_c/manifest.json`: 로컬 재실행 시 생성되는 원문·코드·프로토콜 hash와 통합 판정

원문·코드·프로토콜의 SHA256과 실행 소프트웨어 버전은 각 manifest에 기록한다.
현재 C0–C3 완료에는 유료 문헌이 필요하지 않았다. Takeno et al.와 일부 후속
저널판은 유료일 수 있지만, 현재 관문에 필요한 정보는 공개 JUEL-3155와 HSE
RR985/RR986으로 충족됐다.
