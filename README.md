# 세이프루프 — 학교 안전 대시보드

**팀**: 세이프루프 (SafeLoop)
**대회**: 제8회 교육 공공데이터 AI 활용대회
**역할**: Stage 1 공공데이터 분석 결과 시각화 (실제 심사위원이 URL로 접속해 검증 가능)

> **관련 저장소**: [`wizbeee/safeloop`](https://github.com/wizbeee/safeloop) (Private · 학교 안전 점검 시스템)
> 본 대시보드는 위 점검 프로그램의 **공공 환원** 결과를 자동 합산해 표시합니다.
> 환원 데이터 형식은 [`docs/opendata_schema.md`](docs/opendata_schema.md) 참고.

---

## 로컬 실행

```bash
# 1. 가상환경 생성
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. 의존성 설치
pip install -r requirements.txt

# 3. 실행
streamlit run app.py
# → http://localhost:8501 접속
```

---

## Streamlit Cloud 배포 (무료)

### 1. GitHub 저장소 생성
```bash
cd safeloop_dashboard
git init
git add .
git commit -m "SafeLoop 대시보드 v1"
git branch -M main
git remote add origin https://github.com/[YOUR_USERNAME]/safeloop-dashboard.git
git push -u origin main
```

저장소는 **public** 또는 **private** 모두 가능 (Streamlit Cloud는 둘 다 지원).

### 2. Streamlit Cloud에서 배포
1. https://share.streamlit.io 접속 (GitHub 계정으로 로그인)
2. 우측 상단 **"New app"** 클릭
3. 설정:
   - Repository: `[YOUR_USERNAME]/safeloop-dashboard`
   - Branch: `main`
   - Main file path: `app.py`
4. **Deploy!** 클릭
5. 1~2분 후 URL 발급 (예: `https://safeloop-dashboard.streamlit.app`)

### 3. PPT 슬라이드에 URL 삽입
발급된 URL을 세이프루프 PPT의 슬라이드 1(표지) 또는 슬라이드 15(결론)에 추가합니다.

---

## 데이터 구성

모든 데이터는 익명화·집계 처리되어 개인정보·학교 식별 위험이 없습니다.

| 파일 | 내용 | 식별 가능성 |
|---|---|:---:|
| `sido_summary.csv` | 시도교육청별 집계 | 없음 (시도 단위) |
| `cluster_summary.csv` | K-Means 클러스터 요약 | 없음 (통계) |
| `sensitivity_result.csv` | 가중치 민감도 분석 | 없음 (수치) |
| `high_risk_schools_anonymized.csv` | 고위험 학교 (익명화) | 없음 (학교명 제거, ID 해시) |

### 익명화 처리 내역
- 학교명 → `S00000` 형식 익명 ID
- 정보공시 학교코드 → 제거
- 주소·교육지원청·지역 → 제거 (시도교육청만 유지)

---

## 대시보드 구성 (4개 탭)

1. **시도별 분포** — 17개 시도교육청별 위험도 비교
2. **K-Means 클러스터** — 3군집 (양호/주의/고위험) 시각화
3. **민감도 분석** — 가중치 ±20% 변동 시 결과 안정성 (26 시나리오)
4. **고위험 학교 명단** — 익명화된 고위험 학교 필터·조회·CSV 다운로드

---

## 기술 스택

- **Frontend/Backend**: Streamlit
- **데이터**: pandas
- **시각화**: Plotly
- **배포**: Streamlit Community Cloud (무료)

---

## 프로젝트 전체 흐름에서 이 대시보드의 위치

```
[Stage 1 · 이 대시보드] ← 공공데이터 분석
       ↓
Stage 2: AI 맞춤 점검표 (별도 시연 앱)
       ↓
Stage 3: 실질 점검 + 데이터 순환
       ↓
Stage 4: 정책 활용
       ↓
Stage 1 고도화 (순환)
```

---

## 문의

세이프루프 (SafeLoop) · 제8회 교육 공공데이터 AI 활용대회 · 2026
