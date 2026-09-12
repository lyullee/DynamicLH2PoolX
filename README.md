# DynamicLH2PoolX

DynamicLH2PoolX v0.2는 사용자가 선언한 지표 도달 액체 유량을 받아 LH2 풀의
축대칭 확산, 국소 접촉시간 기반 증발, 액체 재고와 질량수지를 함께 계산합니다.
기존 v0.1 준정상 경로도 `evaluate_pool_source`/`quasi_steady`로 유지됩니다.

## 검증 상태

2026-09-11 기준 Stage C 보강 관문 C0–C3를 모두 통과했으며 통합 판정은
`PASS_RESTRICTED_STAGE_C_COMPONENT_SCOPE`입니다. 이 판정은 선언된 지표 도달 유입, 수평 표면,
매끄러운 축대칭 얕은층이라는 동적 경로의 제한 범위에만 적용됩니다.

- Xie et al. (2023) Figure 11의 독립 실험 증발속도 9점: 평균 절대
  상대오차 7.74%, 최대 10.76% (논문 보고값 7.48%, 11.2%).
- Dienhart JUEL-3155의 독립 보류 실험: 물 Trial 4 반경 RMSE 0.137 m,
  알루미늄 Trial 6 반경 RMSE 0.102 m.
- 보고서의 10–60초 연속 액막 영상 반경 구간 포함률: 두 표면 모두 100%.
- HSE Test 6: 방출 종료 반경 0.92 m, 열전대 정의 건조시간 19 s. 단,
  응축 공기 고체 침적에 의한 1.3–1.4 m 팽창·후퇴 피크는 재현하지 못합니다.
- 수치·계약 테스트 50개 통과. 미소 유입 반례의 상대 미기록 질량오차는
  약 8e-16이며, HSE 계산의 최대 절대 미기록 오차는 1.2e-12 kg 미만입니다.
- `dr=0.01 -> 0.005 m` 및 결합 `dr=dt=0.01 -> 0.005` 세분에서 60 s 반경
  변화는 0, 재고 변화는 각각 0.294%와 0.293%입니다.

검증 범위는 수평의 물 또는 균질 고체 표면, 선언된 액체 유입, 매끄러운 축대칭
얕은층 풀입니다. 분사 충돌·지표 도달률, 비축대칭 가지/맥동/분리된 액편,
경사·배수·방벽·복잡 지형, 기상 확산은 계산하지 않습니다. 물의 일정 열유속
경로는 Dienhart가 허용한 약 50–60초 범위의 보정식입니다. 자세한 수치와 출처는
[`docs/dynamic-validation-report.md`](docs/dynamic-validation-report.md)에 있습니다.
감사 결과는 [`docs/v02-code-audit.md`](docs/v02-code-audit.md), 실행 가능한 보강
절차는 [`docs/stage-c-reinforcement-design.md`](docs/stage-c-reinforcement-design.md)에
있습니다. 최종 범위·수치·제한은
[`docs/stage-c-completion-report.md`](docs/stage-c-completion-report.md)가 우선합니다.

직전 FFI 논문 계산은 정적 LH2PoolX v0.1.2 observed-footprint 경로를 그대로
유지합니다. 이번 Stage C 완료는 과거 FFI source reconstruction을 소급해
교체하거나 재검증했다는 뜻이 아닙니다.

## 설치와 테스트

```powershell
python -m pip install -e .
python -m pip install -r requirements-validation.txt
python -m pytest -q
```

## 동적 풀 사용 예

```python
from dynamiclh2poolx import (
    DeclaredInflow,
    DynamicPoolConfig,
    ShallowLayerNumerics,
    SolidSemiInfiniteSurface,
    run_dynamic_pool,
)

surface = SolidSemiInfiniteSurface(
    name="concrete",
    conductivity_W_mK=0.88,
    diffusivity_m2_s=1.5775e-7,
    initial_temperature_K=195.7,
)
numerics = ShallowLayerNumerics(
    domain_radius_m=5.0,
    source_radius_m=0.20,
)
result = run_dynamic_pool(
    DynamicPoolConfig(surface=surface, numerics=numerics),
    DeclaredInflow(times_s=(0.0, 60.0), rates_kg_s=(0.10, 0.0)),
    output_times_s=(0.0, 10.0, 30.0, 60.0, 90.0),
)
print(result.ledger[-1].reported_radius_m, result.mass_balance_residual_kg)
```

`DynamicPoolLedger`에는 유입·액체질량, 계산 wet area, 관측 연산자의 보고
반경·면적, wet-area 평균깊이·열유속, 구간평균/마지막 내부 스텝 증발률,
누적 증발량·경계 유출량·수치질량조정·closure ID가 SI 단위로 저장됩니다. 고체는
`SolidSemiInfiniteSurface`, 물은 근거와 보정명을 요구하는
`ConstantHeatFluxWaterSurface`를 사용합니다.

기존 고정면적 경로는 `FixedAreaPoolConfig`와 `run_fixed_area_pool`, 기존
준정상 경로는 `LH2Release`와 `evaluate_pool_source`를 사용합니다.

## 전체 검증 재현

Stage C만 재현하려면 공개 원문 PDF 경로를 명시합니다.

```powershell
.\.venv\Scripts\python.exe scripts/validate_stage_c.py `
  --dienhart-pdf "outputs/sources/dienhart_1995_juel3155.pdf" `
  --rr985-pdf "C:/path/to/rr985.pdf" `
  --rr986-pdf "C:/path/to/rr986.pdf"
```

PRESLHY 조건부 진단과 Xie 고정면적 검증까지 포함하려면 아래 전체 실행기를
사용합니다. 먼저 위 Stage C 실행으로 통합 manifest를 생성해야 합니다.

```powershell
.\.venv\Scripts\python.exe scripts/validate_all.py `
  --dataset-dir "C:/path/to/PRESLHY/dataset" `
  --xie-pdf "outputs/sources/xie2023.pdf" `
  --dienhart-pdf "outputs/sources/dienhart_1995_juel3155.pdf"
```

결과표·그림·원문 SHA256·판독 절차는 `outputs/`에 생성됩니다. PRESLHY 반복
충전 비교는 유입 계측이 없으므로 통과 관문이 아니라 조건부 스트레스 진단으로
보존됩니다. 원본 자료는 코드와 함께 재배포하지 않습니다.

## License

Code: MIT. 실험 자료와 파생 판독점에는 각 원출처의 라이선스가 적용됩니다.
