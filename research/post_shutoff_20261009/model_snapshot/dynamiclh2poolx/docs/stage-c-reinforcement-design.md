# DynamicLH2PoolX Stage C 보강 설계

설계 동결일: 2026-09-11  
목표: 선언된 지표 도달 LH2 유입에 대한 축대칭 동적 풀의 반경·재고·증발 이력을
추적 가능하게 검증한다.

> **구현 상태:** 2026-09-11에 C0–C3가 완료되어 통합 판정
> `PASS_RESTRICTED_STAGE_C_COMPONENT_SCOPE`가 생성됐다. 이 문서는 사전 설계와 관문을 보존한다.
> 실제 결과와 제한은 [`stage-c-completion-report.md`](stage-c-completion-report.md)가
> 우선한다.

## 완료의 정의

Stage C는 단순히 JUEL 곡선과 다시 겹치는 것으로 끝나지 않는다. 다음 네 묶음이
모두 충족될 때 완료한다.

1. 감사에서 찾은 질량 절단과 출력 면적 정의를 수정하고 회귀시험으로 고정한다.
2. 공간·시간·영역·wet/dry·관측 전면 민감도를 정량화해 수치오차를 실험
   불확실성보다 작게 만든다.
3. JUEL Trial 3/5 보정과 Trial 4/6 보류 검증을 수정 코드로 다시 실행한다.
4. 계수를 더 손대지 않고 HSE Test 6 콘크리트 장시간 시험을 제한 평가한다.

이 순서는 구현 검증, empirical validation, 결과 불확실성을 분리하라는
NASA-STD-7009B의 구조를 따른다.[^1]

## C0 — 감사 결함 수리

### C0.1 보존형 wet/dry 장부

- 깊이 절단으로 사라지는 질량을 없앤다. 재분배가 수치적으로 불안정하면
  `numerical_discarded_mass_kg`를 셀·시간별로 적산한다.
- 최종 질량식은 `initial + inflow = liquid + evaporated + escaped + discarded`로
  기계 검증한다.
- 배포 관문은 절대 잔차 `<= 1e-10 kg` **또는** 상대 잔차
  `<= 1e-10` 중 느슨한 쪽이 아니라, 규모에 맞춘
  `|unledgered| <= max(1e-12 kg, 1e-10 × handled_mass)`로 둔다.
- 미소 유입, 젖음/건조 반복, 완전 증발, 경계 유출 사례를 추가한다.

### C0.2 상태 면적과 관측 면적 분리

다음 출력을 따로 둔다.

| 출력 | 정의 |
|---|---|
| `wet_area_m2` | 계산상 `h > dry_depth`인 셀의 면적 |
| `reported_radius_m` | 실험 검출깊이 이상 최외곽 셀의 face 반경 |
| `reported_area_m2` | `pi × reported_radius²`인 관측 연산자 출력 |
| `wet_area_mean_depth_m` | 전체 액체부피 / `wet_area_m2` |
| `wet_area_mean_evaporation_flux` | 국소 증발률 적분 / `wet_area_m2` |
| `interval_mean_evaporation_rate` | 두 출력시각 누적증발 차 / 시간차 |

### C0.3 운동량 closure와 계약

- JUEL 식 4.19의 증발 기체 반경속도 가정을 enum으로 노출한다.[^2]
- `zero_radial_momentum_vapor`와 `liquid_velocity_carryoff`를 모두 시험하고 기본값
  근거를 문서화한다.
- surface 형식, 포화압력 범위, 초기재고 지원 여부를 구성 생성 시 검증한다.
- 입력·의존성·원문 hash·관측 연산자 버전을 결과 manifest에 echo한다.

## C1 — solution verification

### C1.1 결정론적/분석적 시험

- 무유입·무열원 정지상태와 일정 유입의 총질량 적분
- 이산 원형·환형 source의 면적 적분 1.0
- 마찰만 있는 단일셀의 해석적 감쇠 한계
- 증발만 있는 단일셀의 두 운동량 closure 해
- 외곽 유출의 도메인 질량 감소와 `escaped` 장부 동일성
- wet/dry 이동 전면의 비음수성과 무장부 손실 0
- 출력시각을 촘촘히/성기게 바꿔도 동일 시각 상태가 동일한지 확인

### C1.2 격자·시간·영역 행렬

JUEL 알루미늄 Trial 6을 우선 기준 사례로 쓴다.

| 축 | 실행값 |
|---|---|
| 공간 `dr` | 0.04, 0.02, 0.01, 0.005 m |
| 최대 `dt` | 0.04, 0.02, 0.01, 0.005 s |
| 영역반경 | 1.2, 1.6, 2.4 m |
| 보고 전면깊이 | 0.5, 0.75, 1.0 mm |
| 운동량 closure | 두 명시 옵션 |

현재 `dr=0.04/0.02/0.01 m`의 60초 반경은 0.44/0.46/0.45 m라 비단조다.
`dr=0.005 m`를 추가하고 필요하면 0.03/0.015/0.0075 m 계열을 써 점근 구간을
찾는다. 비단조이면 GCI 숫자를 억지로 보고하지 않고 범위를 수치 불확실성으로
보존한다. 수렴차수와 GCI는 Celik 절차로 반경, 재고, 누적증발 각각 계산한다.[^3]

통과 기준은 다음과 같이 **실험 재실행 전에 고정**한다.

- 세격자 추가 변화: 반경 `<= 0.02 m`, 재고·누적증발 `<= 2%`.
- 시간 세분 추가 변화: 반경 `<= 0.01 m`, 재고·누적증발 `<= 1%`.
- 영역 확대 시 경계 유출 0이고 관심 출력 변화가 위 시간 기준 이내.
- 보고 전면 민감도는 모델오차가 아니라 측정 연산자 불확실성으로 별도 보고.
- 보존 장부의 무기록 질량은 C0.1 기준 만족.

JUEL 반경센서는 0.1/0.2 m 간격이고 약 0.5–1 mm 높이에 있으므로 위 수치 목표는
관측 공간해상도보다 작다.[^2][^4]

## C2 — JUEL 관측자료와 보정 규약 고정

### C2.1 파일 분리

- `data/juel3155_radius_observations.csv`: 표면, trial, branch, 시각, 반경,
  시간/공간 불확실성, 보정/보류 역할
- `data/stage_c_protocol.json`: 판정선과 허용 closure만 저장
- `data/source_manifest.json`: 원문 URL, 페이지, figure/table, SHA256, 판독일
- 실행 스크립트에는 관측값과 판정선을 하드코딩하지 않는다.

Figure 5.24/5.25의 판독 오차를 각 점의 구간으로 보존한다. 0.1 m 열전대
간격 때문에 같은 trial의 시간점·두 branch는 독립 표본으로 세지 않는다.
재료별 보정 trial이 하나뿐이므로 trial bootstrap 95% CI는 만들지 않고,
판독구간과 사전 선언 parameter sensitivity를 불확실성 기록으로 사용한다.[^2]

### C2.2 보정

- 물 Trial 3: 물 closure의 단일 열유속 계수만 추정한다.
- 알루미늄 Trial 5: 단일 열전달 배율만 추정한다.
- Chezy, dry depth, 수치 점성, 보고 전면을 실험 적합 파라미터로 쓰지 않는다.
- 사전 선언한 물 열유속과 알루미늄 열유속 배율 범위의 parameter sensitivity를
  저장하되 confidence interval이라고 부르지 않는다.
- C0/C1을 마친 뒤 보정값과 코드 commit을 동결한다.

### C2.3 JUEL 보류 검증

Trial 4와 6에 동결 계수를 적용한다. 기존 기준인 trial별 반경 RMSE 0.15 m 및
10–60초 영상 반경구간 포함률 90%를 유지하되, 다음을 함께 요구한다.

- bias와 95% 불확실성 구간
- 수치·판독 불확실성을 포함한 정규화 잔차
- branch별 지표와 trial 전체 지표를 둘 다 보고
- 초기 분리 고리, 가지 전면, 물 위 얼음 등 미모델 현상을 잔차에서 삭제하지 않음

JUEL은 알루미늄 풀의 초기 분리 고리와 약 10초 이후의 준정상 반경, 말기 관측
불확실성을 명시한다. DynamicLH2PoolX가 이 현상을 직접 재현한다고 주장하지 않는다.[^2]

## C3 — HSE Test 6 제한 반경 평가

HSE Test 6은 JUEL에 쓰지 않은 장시간 콘크리트 시험이며, 수직 하향 방출이라
축대칭 근사에 가장 적합하다고 RR985가 선정했다.[^5] 다만 같은 사례의 초기
지반온도를 입력하고 RR985의 GASP 기본 열물성을 사용하므로 분류는
`same-case-thermal-input-constrained independent radius assessment`로 제한한다.
공개 조건은 다음과 같다.

| 항목 | 값/근거 |
|---|---|
| 지표 | 옥외 콘크리트 |
| 방출 | 60 L/min, 약 0.0707 kg/s, 561 s |
| 방향/높이 | 수직 하향, 지표 100 mm 위 |
| 초기 지반온도 | 이전 시험 영향으로 약 266 K |
| 관측 | 0.5–2.8 m에 0.1 m 간격 지표 열전대 24개 |
| 풀 판정 | `T < 30 K`; 50 K로 바꿔도 반경 민감도 작음 |
| 반경 이력 | 약 1.0 m plateau → 1.3–1.4 m 팽창 → 약 1.0 m 후퇴 |
| 방출 후 건조 | 약 16.9–17 s |

RR986 원시험 보고서의 100 mm를 우선한다. RR985 §3 본문의 “10 mm”는 RR986와
후속 실험 문헌의 100 mm와 충돌하므로 오타로 기록하고 입력에는 사용하지 않는다.
RR986은 고체 공기성분 침적을 관찰했고, RR985는 1.3–1.4 m의 급팽창/후퇴 원인
후보로 이를 든다. 축대칭 매끄러운 모델의 구조 오차로 남긴다.[^5][^6]

### C3.1 입력 불확실성

DynamicLH2PoolX는 지표에 도달한 액체유입을 요구한다. 이 시험은 노즐 질량유량은
알지만 100 mm 충돌 뒤 액체 도달률과 source footprint를 직접 측정하지 않았다.
기본 계산은 보고된 0.0707 kg/s 전량 도달, 0 반경운동량으로 하고, 다음을
validation 입력 불확실성으로 전파한다.

- 액체 도달률 0.9–1.0
- source 반경 0.0125–0.10 m
- RR986 동일 시험의 지반 온도 추세로 제약한 `k`, `alpha` 범위
- 초기 지반온도와 관측시각 판독 불확실성

이 범위를 반경에 맞춰 재보정하지 않는다. 콘크리트 물성은 실험 간 3–5배까지
옮겨가지 않는다는 연결 프로젝트 RR986 분석을 반영해 일반 콘크리트 한 값으로
고정하지 않는다.[^6]

### C3.2 사전 고정 평가 지표

- 방출 종료 반경 `0.9–1.0 m`
- 방출 종료 후 건조시간 `17 ± 5 s`
- 0–561초 반경 RMSE와 1.3–1.4 m 급팽창/후퇴는 응축 공기 고체 침적이 모델
  범위 밖이므로 공개 진단값으로 남기되 통과 관문으로 쓰지 않는다.
- HSE 결과를 본 뒤 JUEL 보정계수를 변경하면 외부검증은 무효로 하고 새 버전에서
  다시 분할한다.

RR985는 원 반경이 직접 측정된 값이 아니라 지표 열전대에서 추출됐고, 풀 깊이는
계측 정밀도와 비슷해 추정할 수 없다고 명시한다. 따라서 반경·건조시간만 관문으로
쓰며 HSE 사례에서 재고나 증발률을 실측 검증했다고 주장하지 않는다.[^5]

## C4 — 추가 자료의 역할

### NASA White Sands

Witcofski & Chirivella Test 6은 최대 5.7 m3를 약 35초 동안 9.1 m pond로
방출했고 약 8초 더 기화했다.[^7] 그러나 Dewar를 최대 690 kPa로 가압했고 실제
지표 액체 도달률과 액체 풀 반경이 보고되지 않았다. 따라서 Stage C 정량 관문이
아니라 대규모·급속방출의 시스템 수준 입력-envelope 점검에만 쓴다.

### ELVHYS 2025 공개 자료

EU CORDIS의 ELVHYS D4.1은 HSE 실험자료가 Dataverse에 공개됐음을 확인한다.[^8]
확인 결과 이는 2010년 RR986의 `lh2unig051.xls`가 아니라 ELVHYS WP4.1/4.2의
별도 신규 실험이다. 현 Stage C 원자료를 대체하지 않지만, v0.3 이후 독립 시험을
추가하는 공개 후보로 등록한다.

### 현재 찾지 못한 자료

- RR986 내부 파일명으로 알려진 `lh2unig051.xls` 원파일은 연결된 네 작업공간과
  공개 웹 검색에서 찾지 못했다.
- 현재 로컬 자료는 RR985/RR986 PDF와 과거 Figure 15 수기 판독값이다.
- 원파일을 확보하면 Figure 2 반경을 다시 생성하고 시간 판독오차를 줄인다.

## C5 — 자동화된 완료 관문

최종 `validate_stage_c.py`는 다음 순서에서 하나라도 실패하면 완료 문자열을 내지
않는다.

1. C0 회귀시험
2. C1 수치수렴 manifest
3. JUEL 보정 실행 및 계수 동결 hash
4. JUEL Trial 4/6 보류 실행
5. HSE Test 6 무재보정 제한 반경 평가
6. 입력·원문·코드·의존성 hash가 포함된 통합 manifest

완료 문자열은 `PASS_RESTRICTED_STAGE_C_COMPONENT_SCOPE` 하나만 사용한다. 수치수렴은 됐지만
HSE 원자료가 그림 판독뿐이면 결과에 `data_quality=figure_digitised`를 반드시
붙인다. 실패 시 단순 `FAIL` 대신 실패 관문과 다음 수정 대상을 기록한다.

## 실행 산출물

| 산출물 | 내용 |
|---|---|
| `tests/test_dynamic_conservation.py` | C0 질량·wet/dry 회귀 |
| `tests/test_dynamic_momentum.py` | 두 증발 운동량 closure |
| `scripts/run_stage_c_convergence.py` | C1 격자·시간·영역 행렬 |
| `data/juel3155_radius_observations.csv` | JUEL 동결 판독점 |
| `data/hse_rr985_test6_radius.csv` | HSE Figure 2 판독점과 불확실성 |
| `data/stage_c_protocol.json` | 실행 전 고정 관문 |
| `scripts/validate_stage_c.py` | 통합 실행기 |
| `outputs/stage_c/manifest.json` | 모든 hash·지표·판정 |

## 유료 자료와 사용자 요청이 필요한 시점

이 설계의 C0–C3 완료에는 유료 자료가 필요 없다. JUEL, HSE, Xie, NASA 및
ELVHYS 자료가 공개돼 있다. 다음 자료는 유료일 수 있지만 현재 필수는 아니다.

- Takeno et al. (1994): 원 논문은 유료 접근일 수 있으며 HSE도 원좌표·정확한
  시험 조합을 확보하지 못했다고 기록했다.
- Middha et al. (2011): 저널판은 유료일 수 있으나 공개 학위논문과 HSE/FZJ
  자료로 Stage C 설계 근거를 대체할 수 있다.
- Verfondern & Dienhart (2007): 저널판 대신 공개 JUEL-3155와 FZJ 2007
  기술보고서를 사용할 수 있다.[^4]

이 논문들의 원문 고유 그림이나 표가 실제 관문에 필요해지는 경우에만 구매 전에
사용자에게 제목·DOI·필요 페이지·대체 불가능한 이유를 알린다.

## Sources

[^1]: NASA, [NASA-STD-7009B, *Standard for Models and Simulations*](https://standards.nasa.gov/sites/default/files/standards/NASA/B/1/NASA-STD-7009B-Final-3-5-2024.pdf) (2024).
[^2]: B. Dienhart, [*Spreading and Vaporization of Liquid Hydrogen onto Water and Solid Ground*, JUEL-3155](https://juser.fz-juelich.de/record/860517/files/J%C3%BCl_3155_Dienhart.pdf) (1995), eqs. 4.18–4.34 and Figs. 5.24–5.25.
[^3]: NASA Glenn, [*Examining Spatial (Grid) Convergence*](https://www.grc.nasa.gov/www/wind/valid/tutorial/spatconv.html); I. B. Celik et al., [ASME discretization-uncertainty procedure](https://doi.org/10.1115/1.2960953) (2008).
[^4]: K. Verfondern, [*Safety Concept of Hydrogen Systems*, Energie & Umwelt 10](https://juser.fz-juelich.de/record/1311/files/Energie%26Umwelt_10.pdf) (2007), §8.
[^5]: P. Batt, [*Modelling of liquid hydrogen spills*, HSE RR985](https://www.hse.gov.uk/research/rrpdf/rr985.pdf) (2014), §§3–6.
[^6]: M. Royle and D. Willoughby, [*Releases of unignited liquid hydrogen*, HSE RR986](https://www.hse.gov.uk/research/rrpdf/rr986.pdf) (2014), §§5–8.
[^7]: R. D. Witcofski and J. E. Chirivella, [NASA NTRS record: *Experimental and analytical analyses of the mechanisms governing the dispersion of flammable clouds formed by liquid hydrogen spills*](https://ntrs.nasa.gov/citations/19840053985) (1984).
[^8]: European Commission CORDIS, [ELVHYS project results and D4.1 HSE experimental-data record](https://cordis.europa.eu/project/id/101101381/results) (2025).
