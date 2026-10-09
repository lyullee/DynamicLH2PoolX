# DynamicLH2PoolX v0.2 코드 감사

감사일: 2026-09-11  
대상: `dynamiclh2poolx` 0.2.0.dev0 동적 풀 경로

## 결론

> **조치 완료(2026-09-11):** 아래 A1–A7은 감사 당시 발견사항을 보존한
> 기록이다. A1/A2/A4–A6은 코드와 회귀시험으로 수정했고, A3은 source-annulus
> 정렬 및 `dr`–`dt` 결합 검증으로 통과했으며, 총 50개 테스트가 통과한다.
> 통합 판정은 `PASS_RESTRICTED_STAGE_C_COMPONENT_SCOPE`다. 실제 수치와 잔여 범위 제한은
> [`stage-c-completion-report.md`](stage-c-completion-report.md)를 우선한다.

감사 당시 v0.2는 설치·빌드가 가능하고 기존 42개 테스트가 통과했다. 질량·운동량
보존식의 축대칭 기하항, JUEL-3155의 층류·Chezy 마찰항 합산, 환형/원형 유입의
면적 정규화, 국소 누적 접촉시간 적분도 원식과 일치한다.[^1]

다만 감사 당시 상태를 **동적 풀 모델 검증 완료본으로 배포해서는 안 됐다.** 직접
재현된 장부 누락 1건, 출력 정의 불일치 1건과 공간 수렴 증거 부족이 있다.
따라서 기존 `PASS_RESTRICTED_SPREADING`은 실험 비교를 재현했다는 기록으로는
유효하지만, Stage C 보강 전 배포 판정은 `PROVISIONAL`이었다. 이는
작동 여부에 대한 인상평이 아니라 아래의 재현 가능한 수정 목록이다.

## 감사 범위와 재현 방법

- 동적 풀·확산·기재 closure와 공개 자료형을 줄 단위로 추적했다.
- JUEL-3155 식 4.18–4.34 및 Figures 5.24/5.25를 구현과 대조했다.[^1]
- `scripts/audit_v02_numerics.py`로 공간·시간격자와 관측 전면 민감도, 작은
  질량 장부 반례, 출력 면적 반례, 운동량 closure 반례를 생성했다.
- Python 3.12 환경에서 `pytest` 42건, 의존성 일관성 및 wheel 구성을
  점검했다.
- NASA-STD-7009B가 요구하는 solution verification, 입력 기록, 검증 자료·지표,
  결과 불확실성 관점으로 증거의 빈 곳을 점검했다.[^2]

수치 근거는 `outputs/v02_audit/numerical_audit.json`에 생성된다. 이 파일은
실행 산출물이므로 Git에는 넣지 않으며 위 스크립트로 다시 만든다.

## 감사 당시 수정해야 했던 항목

### A1. 건조 임계값이 액체 질량을 장부 없이 삭제한다 — 우선순위 0

`spreading.py:162-164`는 `dry_depth_m`보다 얕아진 셀을 0으로 만들고,
`dynamic_pool.py:185-187`도 증발 뒤 같은 처리를 한다. 삭제된 부피가 증발량,
경계 유출량 또는 수치 폐기량 어느 장부에도 들어가지 않는다.

공개 API 반례에서 1초 동안 선언한 유입량 `1.0e-7 kg`은 최종 액체·증발·경계
유출이 모두 0이 되었고 질량 잔차가 `1.0e-7 kg`, 즉 유입 대비 **100%**였다.
기존 테스트의 절대 허용오차 `2e-6 kg`보다 작아 테스트는 이 실패를 감지하지
못한다.

해결 조건은 다음과 같다.

1. 보존형 wet/dry 처리로 임계값 이하 양의 수심을 유지하거나 인접 wet 셀로
   재분배한다.
2. 불가피한 절단은 `numerical_discarded_mass_kg`로 누적해 질량식에 넣는다.
3. 절대값과 함께 `|residual| / max(cumulative_inflow, initial_mass)`를 검사한다.
4. 미소 유입, 전면 후퇴, 반복 wet/dry를 회귀 테스트로 추가한다.

### A2. 재고·반경·열유속이 서로 다른 셀 집합을 사용한다 — 우선순위 0

`dynamic_pool.py:223-228`은 액체질량에는 모든 양의 수심을 쓰지만 반경과 면적은
`reported_front_depth_m` 이상인 셀만 쓴다. 이어 전체 증발률을 이 보고 면적으로
나눠 평균 증발·열유속을 만든다.

감사 반례에서는 액체 `0.63504384 kg`과 마지막 내부 스텝 증발률
`0.00175034 kg/s`가 존재하지만, 높은 보고 전면을 설정하자 반경·면적·보고
증발유속·보고 열유속이 모두 0이 됐다. 수치 상태와 측정 연산자를 분리하지 않은
결과다.

해결 조건은 계산 wet area, 관측 전면으로 얻은 reported area, 국소 열유속
면적평균을 각각 별도 필드로 내보내는 것이다. `mean_depth`의 분모도 어느 면적인지
이름에 명시한다. 면적이 0인데 질량 또는 증발률이 양수인 상태는 경고가 아니라
정의된 출력으로 표현해야 한다.

### A3. 공간격자 수렴이 아직 입증되지 않았다 — 우선순위 1

JUEL 알루미늄 Trial 6의 60초 결과는 다음과 같다.

| 조건 | 반경 [m] | 액체질량 [kg] | 누적증발 [kg] |
|---|---:|---:|---:|
| `dr=0.04 m` | 0.44 | 0.307639 | 25.235447 |
| `dr=0.02 m` | 0.46 | 0.318832 | 25.224254 |
| `dr=0.01 m` | 0.45 | 0.323662 | 25.219423 |

반경열이 0.44→0.46→0.45 m로 비단조이고, 조격자와 세격자 액체질량 차이는
약 4.95%다. 따라서 세 격자 값을 가졌다는 이유만으로 Grid Convergence Index를
계산할 수 없으며 더 세밀한 격자나 다른 해상도 조합으로 점근 구간을 찾아야
한다.[^3] 반면 `dt=0.04, 0.02, 0.01 s`에서 60초 반경은 모두 0.46 m이고 질량
변화는 0.01% 미만이라 현재 사례의 시간 스텝 민감도는 작다.

### A4. 증발 운동량 closure가 암묵적이다 — 우선순위 1

`dynamic_pool.py:183-187`은 증발 수심만 빼고 wet 셀의 운동량은 유지한다.
JUEL 식 4.19에는 증발 기체의 반경속도 `u_t`가 있으므로 이는 자동으로 틀렸다고
볼 수 없고, 사실상 **이탈 기체의 반경 운동량을 0으로 둔 closure**다.[^1]
그러나 문서·설정·민감도 시험이 없다. 수심 1 mm, 속도 0.2 m/s에서 절반이
증발하는 한 셀 예에서는 현재 분할 후 속도가 0.4 m/s가 되며, 액체와 같은
반경속도로 질량이 이탈한다고 두면 0.2 m/s다.

`zero_radial_momentum_vapor`와 `liquid_velocity_carryoff`를 명시적으로 구현하고
JUEL/HSE 사례의 반경·건조시간 민감도를 기록해야 한다. 기본값은 근거와 함께
고정한다.

### A5. `evaporation_rate_kg_s`는 출력시각 순간값이 아니다 — 우선순위 1

`dynamic_pool.py:192`는 마지막 내부 스텝의 평균만 저장하고 이를 출력시각
레코드에 전달한다. 급격한 wet/dry나 유입 종료 부근에서는 출력 간격 평균도,
엄밀한 순간값도 아니다. `last_substep_evaporation_rate_kg_s`로 이름을 정직하게
바꾸거나 출력 구간 적분차로 `interval_mean_evaporation_rate_kg_s`를 제공하고,
국소 면적 적분 순간값은 별도로 계산해야 한다.

### A6. 설정·결과의 계약과 추적성이 부족하다 — 우선순위 2

- `DynamicPoolConfig(object())`가 생성 단계에서 허용되고 실행 중
  `AttributeError`로 실패한다. 표면 형식을 즉시 검사해야 한다.
- `initial_liquid_mass_kg`는 공개 필드지만 양수는 모두 거부한다. 지원 전까지
  필드를 제거하거나 초기 깊이장 입력으로 완성한다.
- CoolProp 유효 포화압력 범위 밖 입력의 오류를 공용 예외로 정규화하지 않는다.
- 결과가 전체 설정, 유입 이력, 입력/원문 hash, Python·NumPy·CoolProp 버전,
  관측 연산자 버전을 되돌려주지 않는다. NASA-STD-7009B가 권하는 입력 echo와
  결과 추적성을 충족하도록 manifest를 확장해야 한다.[^2]
- 큰 상대 질량오차나 보정 배율 사용이 `source_status`를 자동으로 낮추지 않는다.

### A7. 테스트 42건은 동적 PDE 검증 범위를 대표하지 않는다 — 우선순위 2

동적 전용 테스트는 6건이고 분석적 접촉적분, 무유입, 무열원, 비음수/직렬화,
closure 구분, 잘못된 환형원 거부를 다룬다. 공간·시간·영역 수렴, wet/dry 장부,
경계 유출, 운동량 증발원, 관측 전면, 출력간격 독립성, 작은 규모의 상대 질량
보존을 검증하지 않는다. 42라는 총개수 대신 기능-시험 추적표를 관리해야 한다.

## 확인 결과 문제가 아닌 항목

- `spreading.py:168-171`의 층류 점성항과 Chezy항 동시 합산은 JUEL-3155
  p.96의 연속 전이 구현과 일치한다.[^1]
- `spreading.py:159`의 축대칭 압력 기하원은 보존형 방정식 변환에 필요한 항이다.
- `normalised_central_source`는 이산 환형면적에 대해 유입 부피를 정확히
  정규화한다.
- 국소 `cumulative_contact_age_s`는 각 지표 요소의 실제 젖은 시간을 쓰는
  JUEL 식 4.34의 단순화와 일치한다. 다만 원 보고서처럼 재가열과 수평 지반전도는
  포함하지 않는다.[^1]
- 경계 유출 질량을 별도 장부로 두고 경계 도달 시 범위 밖 경고를 내는 설계는
  유지할 가치가 있다.

## 검증 코드 자체의 감사

`scripts/run_validation_spreading.py`는 관측점, 물 열유속 `200 kW/m2`, 알루미늄
배율 `0.40`, 판정선 `RMSE <= 0.15 m`와 영상구간 포함률 `>= 90%`를 한 파일에
하드코딩한다. 보정 Trial 3/5와 보류 Trial 4/6의 분리는 올바른 방향이지만,
같은 실험의 가지·시간점은 상관된 관측인데 독립 표본처럼 RMSE에 들어간다.
또한 판정선이 계산 전에 동결됐다는 외부 기록이 없다.

보강에서는 원자료/판독점, 보정 규약, 동결된 판정선, 실행 코드를 네 파일로
분리하고 trial을 통계 단위로 삼는다. 세부 절차는
`docs/stage-c-reinforcement-design.md`에 정의한다.

## 유료 자료 상태

현재 수정과 Stage C 재검증에 **유료 다운로드는 필요하지 않다**. 핵심 방정식과
실험은 JUEL-3155, HSE RR985/RR986, Xie et al., NASA 기준으로 공개되어
있다.[^5]
Takeno et al. (1994), Middha et al. (2011), Verfondern & Dienhart (2007)의
저널판은 유료일 수 있으나 각각 공개 HSE 분석, 공개 학위논문/회의자료,
JUEL 원보고서·FZJ 공개 보고서로 필요한 내용을 대체할 수 있다. 특히 HSE는
Takeno 원좌표와 정확한 시험 조건 자체가 없다고 기록하므로 논문 구매만으로
그 결손이 해결된다고 보기는 어렵다.[^4]

## Sources

[^1]: B. Dienhart, [*Spreading and Vaporization of Liquid Hydrogen onto Water and Solid Ground*, JUEL-3155](https://juser.fz-juelich.de/record/860517/files/J%C3%BCl_3155_Dienhart.pdf) (1995), pp. 96, 99, 139–140.
[^2]: NASA, [NASA-STD-7009B, *Standard for Models and Simulations*](https://standards.nasa.gov/sites/default/files/standards/NASA/B/1/NASA-STD-7009B-Final-3-5-2024.pdf) (2024), solution verification, validation and credibility evidence.
[^3]: NASA Glenn, [*Examining Spatial (Grid) Convergence*](https://www.grc.nasa.gov/www/wind/valid/tutorial/spatconv.html); I. B. Celik et al., [Procedure for Estimation and Reporting of Uncertainty Due to Discretization in CFD Applications](https://doi.org/10.1115/1.2960953) (2008).
[^4]: P. Batt, [*Modelling of liquid hydrogen spills*, HSE RR985](https://www.hse.gov.uk/research/rrpdf/rr985.pdf) (2014), §§3–6.
[^5]: J. Xie et al., [*Experimental Study on Boiling Vaporization of Liquid Hydrogen in Nonspreading Pool*](https://doi.org/10.3390/pr11051415), *Processes* 11, 1415 (2023), CC BY 4.0.
