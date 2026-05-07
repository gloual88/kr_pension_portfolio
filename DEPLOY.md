# KR 연금 자율주행 SAA — Streamlit Community Cloud 배포 가이드

영상 제작자가 24/7 접근 가능한 비밀번호 보호 데모를 띄우는 절차입니다.

## 0. 사전 준비 — 한 번만 수행

### A. 로컬 비밀번호 설정 (테스트용)

```powershell
# 시크릿 템플릿 복사 후 비밀번호 입력
Copy-Item .streamlit\secrets.toml.template .streamlit\secrets.toml
notepad .streamlit\secrets.toml   # APP_PASSWORD 값 변경
```

`.streamlit/secrets.toml`은 `.gitignore`에 등록되어 있어 커밋되지 않습니다.
같은 비밀번호를 Streamlit Cloud 측에도 별도로 입력합니다 (4-B 단계).

### B. 로컬 검증 (선택)

```powershell
d:\파이선\pykrx_venv\Scripts\Activate.ps1
cd d:\파이선\kr_pension_portfolio\dashboard
streamlit run app.py
```

브라우저에서 `localhost:8501` → 비밀번호 게이트 표시 → 입력 → 대시보드 진입 확인.

---

## 1. GitHub repo 생성 및 푸시

Streamlit Community Cloud는 **GitHub repo**에서 코드를 가져옵니다.
**무료 플랜은 public repo만 지원**하므로, repo 가시성을 결정해야 합니다.

| 옵션 | 장점 | 단점 |
|---|---|---|
| Public repo + 비밀번호 게이트 | 무료 | 코드 자체는 공개 (백테스트 결과 outputs/ 포함) |
| Private repo + Streamlit Cloud Pro | 코드 비공개 | 유료 (요금제 확인 필요) |

**권장: Public repo + 강력한 비밀번호** — 데이터/결과는 비밀번호로 보호되고, 코드만 공개되어도 문제 없는 수준이라면.

> outputs/에 민감 정보가 있다면 (개인 페르소나 등) → Private repo + Pro 또는 outputs/ 일부만 별도 처리.

### A. GitHub에서 빈 repo 생성

repo 이름 예시: `kr-pension-saa-demo`

### B. 로컬에서 repo 초기화 + 푸시

```powershell
cd d:\파이선

# 새 폴더로 배포본 분리 (선택, 더 깔끔)
# 또는 기존 d:\파이선\kr_pension_portfolio\에서 직접 git init

cd d:\파이선\kr_pension_portfolio
git init
git add .gitignore .streamlit/secrets.toml.template DEPLOY.md
git add __init__.py configs/ dashboard/ skills/ outputs/ outputs_personalized/ outputs_trimmed10/
# (필요 최소만 — agents/, llm/, scripts/는 dashboard 표시에 불필요할 수 있음)

git commit -m "Initial: KR pension SAA dashboard for video demo"
git branch -M main
git remote add origin https://github.com/<USERNAME>/<REPO>.git
git push -u origin main
```

> ⚠️ **푸시 전 반드시 확인**: `.env`, `secrets.toml`, `.venv/`가 add되지 않았는지 `git status`로 검증.

---

## 2. Streamlit Community Cloud 앱 생성

1. <https://share.streamlit.io> 접속 → GitHub 계정으로 로그인
2. **"Create app"** 클릭
3. **Repository**: 1단계에서 만든 repo 선택
4. **Branch**: `main`
5. **Main file path**: `dashboard/app.py`
   - (repo 루트가 `kr_pension_portfolio/` 자체라면 위 경로 그대로)
   - (repo가 `kr-pension-saa-demo/kr_pension_portfolio/` 구조면 `kr_pension_portfolio/dashboard/app.py`)
6. **Python version**: 3.11 권장 (요구사항 호환성)
7. **Advanced settings → Requirements file**: `dashboard/requirements.txt` 자동 인식
8. **Deploy** 클릭

---

## 3. Secrets 설정 (Cloud)

배포 후 **Settings → Secrets** 메뉴에서 비밀번호 입력:

```toml
APP_PASSWORD = "change-me-strong-password-here"
```

저장 후 앱이 자동 재배포됩니다 (~30초).

---

## 4. 영상 제작자에게 전달

배포가 완료되면 다음 형식으로 전달:

```
URL: https://<your-app-name>.streamlit.app
비밀번호: <설정한 APP_PASSWORD>
유효 기간: 영상 제작 완료 시까지

페이지 안내:
  - 개요 (홈): 위험자산 비중·레짐·Sharpe 등 KPI 4개
  - 백테스트: Walk-Forward NAV, Drawdown, 분기별 비중
  - 매크로 / Regime: 14개 매크로 readings, regime 점수
  - 자산군 분석: 18 ETF 별 CMA, 변동성, 시그널
  - LLM vs Baseline: 의사결정 비교
  - 월간 연금 포트폴리오: 21개 PC 모델 비중 + CIO 추천
```

---

## 5. 운영 / 종료

- **앱 정지**: Streamlit Cloud 대시보드 → "Reboot" 또는 "Delete"
- **로그 확인**: 앱 페이지 우측 하단 "Manage app" → 로그 보기
- **재배포**: GitHub에 새 커밋 푸시 시 자동 재배포

## 6. 문제 발생 시 체크리스트

| 증상 | 원인 / 조치 |
|---|---|
| 빌드 실패 — `requirements.txt not found` | Main file path 또는 Requirements file 경로 재확인 |
| `ModuleNotFoundError: No module named 'kr_pension_portfolio'` | repo 구조에 `kr_pension_portfolio/` 폴더가 포함되어 있고, 글라이드패스 페이지가 sys.path에 그 부모를 추가하는지 확인. 필요시 0_개인_글라이드패스.py를 임시로 dashboard/pages/에서 제외 |
| 비밀번호 페이지 미표시 | Secrets에 `APP_PASSWORD` 누락. Settings → Secrets 재확인 |
| outputs/ 데이터 미표시 | outputs/ 폴더가 git에 커밋되었는지 확인 (LFS 미사용 가정 — 50MB 미만이면 일반 git OK) |
| 한글 깨짐 | Cloud 환경에 한글 폰트 부재 — plotly는 SVG라 폰트 문제 적음. matplotlib 차트가 있다면 별도 폰트 설정 필요 |

## 7. 보안 주의

- ✅ 비밀번호 게이트로 1차 보호
- ✅ `.streamlit/secrets.toml`은 .gitignore에 등록되어 커밋 안 됨
- ⚠️ 민감 데이터(개인 잔고 등)가 outputs/에 있으면 public repo는 부적절
- ⚠️ 시크릿 노출 시: GitHub repo의 commit history도 확인하여 과거 노출 방지
