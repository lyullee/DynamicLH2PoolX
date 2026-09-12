# 한국수소및신에너지학회지 투고 보강 체크리스트

이 체크리스트는 DynamicLH2PoolX를 `Journal of Hydrogen and New Energy`에
투고하기 위한 내부 준비 문서다. Zenodo DOI는 현재 서비스 장애로 인해
필수 항목에서 제외한다.

## 완료된 과학적 보강

- [x] C0 미소 유입 질량보존과 wet/reporting 면적 분리
- [x] C1 공간 격자 및 `dr--dt` 결합 수렴
- [x] C2 JUEL Trial 3/5 사전 보정, Trial 4/6 holdout
- [x] C2 재료별 RMSE, MAE, bias, 영상구간 포함률
- [x] 재료별 단일 calibration trial에 대한 bootstrap CI 미주장
- [x] digitisation interval 및 predeclared parameter sensitivity 저장
- [x] C3 HSE Test 6 종점 반경·건조시간 평가
- [x] HSE 전체 궤적 RMSE와 응축공기 침적 피크를 비통과 구조 진단으로 분리
- [x] 기본 증발 운동량 closure를 비교 전에 고정
- [x] 설정 echo, closure ID, 소프트웨어 버전, SHA256 manifest 저장
- [x] 50개 자동화 회귀·계약·보존·solver 테스트 통과
- [x] GitHub 공개 저장소 및 PyPI 재현성 artifact 연결

## 원고에 반영해야 할 핵심 사항

- [x] 제목을 “제한적 검증” 범위로 명시
- [x] 지표 도달 유입이 입력이라는 가정 명시
- [x] 지배방정식, Rusanov flux, CFL 조건, friction closure 설명
- [x] 물 closure의 약 50--60 s 적용 한계 명시
- [x] fixed-area route를 직접적인 반경 baseline으로 사용하지 않음
- [x] HSE를 엄밀한 독립 외부검증으로 과장하지 않음
- [x] FFI v0.1.2 static source reconstruction과 동적 route를 분리
- [x] 데이터·코드·원문 PDF의 재배포 범위와 provenance 설명

## 제출 직전 편집 작업

- [ ] 실제 저자 순서, 소속, 교신저자, 연구비, 감사문 확정
- [ ] 학회 Hanword 템플릿으로 B5 2단 원고 변환
- [ ] 본문 6쪽 이상인지 확인
- [ ] 영문 Abstract를 150단어 이하로 최종 교정
- [ ] 한글·영문 키워드 5--6개 최종 확정
- [ ] 모든 figure/table caption을 영문으로 통일
- [ ] 본문 내 그림·표·방정식 일련번호와 상호참조 확인
- [ ] 모든 단위와 기호를 SI 체계로 통일
- [ ] 참고문헌을 학회 영문 형식과 DOI 순서로 교정
- [ ] 최종 그림에서 digitisation interval, holdout 표기, limitation 표기 확인
- [ ] PyPI `0.2.0.dev0` commit과 원고의 소프트웨어 버전 일치 확인
- [ ] Zenodo DOI 없이도 재현 가능한 GitHub commit/PyPI URL을 Data Availability에 기재

## 최종 주장문

> DynamicLH2PoolX is verified for a restricted component scope consisting of
> declared ground inflow, horizontal smooth-axisymmetric spreading, and named
> surface heat-transfer closures. This evidence does not validate impact
> deposition, asymmetric spill formation, condensed-air deposition, or
> atmospheric dispersion.

이 문구보다 넓은 “validated complete LH₂ pool model” 표현은 사용하지 않는다.

