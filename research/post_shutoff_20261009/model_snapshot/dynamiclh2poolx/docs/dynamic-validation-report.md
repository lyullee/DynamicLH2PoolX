# DynamicLH2PoolX v0.2 동적 풀 검증 보고서

> **2026-09-11 Stage C 완료 갱신:** 아래 문서는 최초 제한 구성요소 비교의
> 재현 기록이다. 이후 wet/dry 장부와 출력 정의를 수정하고 공간·결합 수렴 및
> HSE 제한 평가를 추가해 `PASS_RESTRICTED_STAGE_C_COMPONENT_SCOPE`를 생성했다. 최종 수치와
> 적용 제한은 [`stage-c-completion-report.md`](stage-c-completion-report.md)가
> 우선한다.

## 결과

2026-09-11 기준, **선언 유입–축대칭 얕은층–국소 증발로 구성된 v0.2 경로의
제한된 구성요소 검증을 완료했다.** 고정면적 증발률은 Xie et al. (2023),
확산 반경은 Dienhart JUEL-3155 (1995)의 서로 다른 공개 실험으로 확인했다.
당시 수치 회귀 42개가 통과했다. 보강 후에는 50개가 통과한다.

이 결론은 분사 충돌, 액체 지표 도달률, 비축대칭 액편, 경사·방벽·배수 또는
기상 확산까지 검증했다는 뜻이 아니다.

## 수정된 증거 연결

이전 Concrete02 예측/관측비 1.173은 철회한다. 온도 `X_Value`의 1초 기록과
저울 `Orig.Time`의 0.5초 기록을 같은 행 시각으로 잘못 묶은 값이었다. 수정
추출기는 온도를 `Sync.Time`으로 보간하고 질량은 원래 저울 시각에 둔다.

또한 Xie Figure 9 질량과 Figure 11 증발속도를 같은 실험의 연속 기록처럼
적분한 비교를 폐기했다. 논문상 두 그림은 다른 실험·시계이며 둘을 잇는 초기
온도장이 없다. Figure 11 자체에 실험점과 모델곡선이 모두 있으므로 그것만으로
Stage B를 구성했다.

## Stage B — 비확산 풀 증발률

Xie et al. Figure 11의 내장 RGB 그림에서 검은 실험 표식 9점을 판독했다.
별도의 빨간 PTC 예측곡선은 본문의 누락 입력인 초기 열접촉시간과 콘크리트
초기온도만 복원하는 데 썼고, 검은 점은 적합에 사용하지 않았다. Table 3의
`k=0.88 W/(m K)`, `alpha=1.5775e-7 m2/s`를 사용했다.

| 지표 | DynamicLH2PoolX | 논문 보고 |
|---|---:|---:|
| 실험점 수 | 9 | 9 |
| 평균 절대 상대오차 | 7.74% | 7.48% |
| 최대 절대 상대오차 | 10.76% | 11.2% |
| RMSE | 5.742e-5 m/s | — |

빨간 출판곡선 자체의 재현 RMSE는 7.07e-7 m/s였다. 복원 입력은 초기
열접촉시간 55.50 s, 초기 기재온도 195.70 K다. 픽셀 판독 한계는 +/-1 s,
+/-6e-6 m/s이며 PDF SHA256과 좌표는 결과 manifest에 기록된다.

사전 재현 관문은 9점 전부 판독, 출판 평균·최대 상대오차와 각각 0.02 이내,
빨간 출판곡선 RMSE 6e-6 m/s 이하이다.

결정: `PASS_FIXED_AREA_PTC_RATE_REPRODUCTION`.

![Xie Figure 11 검증](../outputs/xie2023/figure11_validation.png)

## Stage C — 풀 확산 반경

공개 JUEL-3155 원보고서의 Figures 5.24/5.25와 Tables 3.8/3.9를 사용했다.
catch bowl 직경 0.4 m를 0.18–0.22 m 환형 유입으로 표현하고, 표면 위
0.5–1 mm 열전대 범위의 중간값 0.75 mm를 보고 전면 깊이로 고정했다.
`dr=0.02 m`, 최대 `dt=0.02 s`, Chezy 계수 `1e-3`이다.

표면별 계수 하나만 사전 보정했다. 물 Trial 3에서 일정 열유속 200 kW/m2,
알루미늄 Trial 5에서 반무한 전도 열유속 배율 0.40을 정하고, 이를 바꾸지 않고
Trial 4와 6에 적용했다.

| 표면·실험 | 역할 | n | 반경 RMSE | MAE | bias |
|---|---|---:|---:|---:|---:|
| 물 Trial 3 | 보정 | 7 | 0.181 m | 0.129 m | -0.129 m |
| 물 Trial 4 | 독립 보류 | 9 | **0.137 m** | 0.122 m | -0.078 m |
| 알루미늄 Trial 5 | 보정 | 5 | 0.129 m | 0.108 m | -0.108 m |
| 알루미늄 Trial 6 | 독립 보류 | 10 | **0.102 m** | 0.092 m | +0.004 m |

보고서가 비디오에서 식별한 매끄러운 연속 액막 구간은 물 0.4–0.6 m,
알루미늄 0.3–0.5 m다. 10–60초 계산 반경의 구간 포함률은 둘 다 100%였다.
이 문서의 최초 계산에서 물/알루미늄 질량수지 잔차는 각각
1.05e-7/3.43e-7 kg였다. C0 수정 후 최신 manifest의 잔차는 약 1e-13 kg다.

초기의 분리 고리, 가지형 전면, 맥동과 떠다니는 고체 조각은 매끄러운 축대칭
반경으로 재현할 수 없으며 RMSE에 그대로 남겼다. 물 closure는 보고서가 허용한
약 50–60초 범위에 한정된다.

관문은 각 보류 표면의 RMSE 0.15 m 이하와 영상구간 포함률 90% 이상이다.

결정: `PASS_RESTRICTED_SPREADING`.

![Dienhart 반경 검증](../outputs/spreading_validation/radius_validation.png)

## PRESLHY E3.4 스트레스 진단

Concrete02/03 원본 저울 비교와 수정된 온도 시계 정렬은 삭제하지 않고
`DIAGNOSTIC_MIXED_NOT_RELEASE_GATE`로 보존한다. 이 자료에는 반복 충전 중 실제
지표 도달 유입량이 없어, 초기질량 이후를 무유입으로 두는 비교가 조건부다.
Concrete02 4구간 가운데 첫 구간은 기존 30% 질량손실 점검선을 벗어났고 일부
구간은 조기 소멸했다. 이는 유입이 알려진 Xie/JUEL 구성요소 검증을 뒤집는
배포 관문이 아니라 모델 적용 시 남는 불확실성 기록이다.

## 추가 문헌 일관성 확인

연결 작업공간의 자료목록과 공개 문헌을 추가로 대조했다. Takeno et al. (1994)의
초록은 초기 구간 이후 콘크리트 위 증발률이 `1/sqrt(t)`에 비례한다고 보고한다.
HSE RR985는 이 자료로 GASP를 시험했지만, 원 좌표가 없고 출판 그림이 어느 시험
조건인지 특정되지 않아 직접 정량 비교가 불가능하다고 명시한다. 따라서 이 자료를
새 검증점처럼 세지 않았다.

최근 공개 HySafe 연구가 Takeno, Bailey, PRESLHY와 ISO/TR 15916:2015를 묶어
보고한 후기 LH2 후퇴속도는 약 0.5–0.63 mm/s다. Xie 검증에서 DynamicLH2PoolX의
135초 값은 0.500 mm/s로 이 범위의 하단과 일치한다. 이는 보조 문헌 일관성
확인이지 Xie 9점과 별개의 독립 표본 수로 계산하지 않는다.

## 수치 검증과 재현

최초 보고 시 Python 3.12에서 42개 테스트가 통과했고, Stage C 보강 후 50개가
통과한다. 분석적 고체 접촉 적분의 분할 독립성,
무입력·무열원 한계, 단계 유입, 비음수 깊이, JSON 왕복, closure 구분,
질량보존과 잘못된 환형 원천 거부를 포함한다.

```powershell
.\.venv\Scripts\python.exe scripts/validate_all.py `
  --dataset-dir "C:/path/to/PRESLHY/dataset" `
  --xie-pdf "outputs/sources/xie2023.pdf" `
  --dienhart-pdf "outputs/sources/dienhart_1995_juel3155.pdf"
```

전체 결과는 `outputs/validation_summary.json`, 세부 결과는 각 하위 manifest에
기록된다. 원자료는 재배포하지 않는다.

## 출처

1. Xie et al., [Experimental Study on Boiling Vaporization of Liquid Hydrogen
   in Nonspreading Pool](https://doi.org/10.3390/pr11051415), *Processes* 11,
   1415 (2023), Figure 11, Table 3. CC BY 4.0.
2. Dienhart, [Tiefkalte Flussiggas-Lachen, JUEL-3155](https://juser.fz-juelich.de/record/860517)
   (1995), equations 4.2–4.34, Figures 5.24/5.25, Tables 3.8/3.9.
3. Verfondern & Dienhart, [Pool Spreading and Vaporization of Liquid Hydrogen](https://conference.ing.unipi.it/ichs2005/Papers/110078.pdf),
   ICHS 2005.
4. Friedrich et al., [PRESLHY Experiment series 3.4](https://doi.org/10.35097/1319),
   KIT (2020/2023), CC BY-SA 4.0.
5. Takeno et al., [Evaporation rates of liquid hydrogen and liquid oxygen
   spilled onto the ground](https://doi.org/10.1016/0950-4230(94)80061-8),
   *J. Loss Prevention in the Process Industries* 7 (1994), 425–431.
6. Batt, [Modelling of liquid hydrogen spills, HSE RR985](https://www.hse.gov.uk/research/rrpdf/rr985.pdf)
   (2014), §4.2.
7. [Bunding of Large LH2 Spills](https://doi.org/10.58895/hysafe.33),
   *Hydrogen Safety* (2025), §4.1.

자료 판독·실행일: 2026-09-11. 반올림하지 않은 값은 생성된 manifest가 우선한다.
