"""
세이프루프 학교 안전 대시보드
공공데이터 기반 전국 학교 시설 안전 현황 시각화

점검 프로그램(safeloop)의 교육청 담당자가 공공 환원을 실행하면,
공유 폴더에 저장된 환원 CSV를 본 대시보드가 자동으로 합산해 표시합니다.
공유 폴더는 환경변수 SAFELOOP_SHARED_DIR 로 override 가능 (기본값:
~/Desktop/공공데이터 공모전/03_분석_데이터/점검_환원/).
"""
import os
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from pathlib import Path

st.set_page_config(
    page_title="세이프루프 — 학교 안전 대시보드",
    layout="wide",
    initial_sidebar_state="auto",
)

# 반응형(적응형) CSS — 좁은 화면(모바일·태블릿)에서 KPI·차트·표 자동 조정
st.markdown(
    """
    <style>
    /* 데스크톱 기본 */
    .stMetric { padding: 4px 0; }
    .stMetric label { font-size: 0.85rem !important; color: #555; }
    .stMetric [data-testid="stMetricValue"] { font-size: 1.6rem !important; font-weight: 700; }

    /* 태블릿 (768px 이하) */
    @media (max-width: 768px) {
        h1 { font-size: 1.5rem !important; }
        h2 { font-size: 1.2rem !important; }
        .stMetric [data-testid="stMetricValue"] { font-size: 1.3rem !important; }
        .stMetric label { font-size: 0.78rem !important; }
        .block-container { padding: 1rem 0.8rem !important; }
        .stTabs [data-baseweb="tab-list"] { flex-wrap: wrap; gap: 4px; }
        .stTabs [data-baseweb="tab"] { font-size: 0.85rem !important; padding: 6px 10px !important; }
    }

    /* 모바일 (480px 이하) */
    @media (max-width: 480px) {
        h1 { font-size: 1.25rem !important; }
        .stMetric [data-testid="stMetricValue"] { font-size: 1.15rem !important; }
        .stCaption, .stMarkdown p { font-size: 0.88rem !important; }
        .block-container { padding: 0.6rem 0.5rem !important; }
        /* 표·차트가 가로로 넘칠 때 가로 스크롤 */
        .stDataFrame, .stPlotlyChart, [data-testid="stPlotlyChart"] {
            overflow-x: auto !important;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

DATA_DIR = Path(__file__).parent / "data"
DATA_BASIS = "환경위생 2023 / 시설안전·학생수 2025"

# 분석에 사용한 비중 (데이터로 자동 계산한 객관 값)
W_MISMANAGE = 0.4636
W_ENVRISK = 0.3711
W_DAYS = 0.1653

# 공유 폴더 — 점검 프로그램의 교육청 담당자가 공공 환원 시 CSV 를 저장하는 위치.
# 본 대시보드는 이 폴더의 활성 환원 CSV(opendata_*.csv) 를 자동 합산합니다.
# `_rolled_back/` 하위 폴더는 무시 (롤백된 환원).
#
# 우선순위:
#   1. 환경변수 SAFELOOP_SHARED_DIR (사용자 지정)
#   2. 로컬 PC 표준 위치 (~/Desktop/공공데이터 공모전/03_분석_데이터/점검_환원/)
#   3. 저장소 내부 fallback (data/점검_환원/) — Streamlit Cloud 배포 환경 대응
def _resolve_shared_dir() -> Path:
    candidates = [
        os.environ.get("SAFELOOP_SHARED_DIR"),
        str(Path.home() / "Desktop" / "공공데이터 공모전" / "03_분석_데이터" / "점검_환원"),
        str(Path(__file__).parent / "data" / "점검_환원"),
    ]
    for p in candidates:
        if p and Path(p).exists():
            return Path(p)
    # 모두 존재하지 않으면 저장소 내부 경로 반환 (없으면 빈 결과)
    return Path(__file__).parent / "data" / "점검_환원"

SHARED_DIR = _resolve_shared_dir()


@st.cache_data(ttl=10)
def load_returned_data(shared_dir_str: str):
    """공유 폴더의 활성 환원 CSV 를 모두 읽어 하나의 DataFrame 으로 합산.

    Returns:
        (df, last_time_str)
        - df 가 비어 있으면 환원 0건
        - last_time_str: 가장 최신 환원 파일의 mtime (사람이 읽는 형식)
    """
    p = Path(shared_dir_str).expanduser()
    if not p.exists():
        return pd.DataFrame(), ""
    dfs = []
    latest_mtime = 0.0
    for csv_path in sorted(p.glob("opendata_*.csv")):
        try:
            df = pd.read_csv(csv_path)
            dfs.append(df)
            mt = csv_path.stat().st_mtime
            if mt > latest_mtime:
                latest_mtime = mt
        except Exception:
            continue
    if not dfs:
        return pd.DataFrame(), ""
    merged = pd.concat(dfs, ignore_index=True)
    last_str = datetime.fromtimestamp(latest_mtime).strftime("%Y-%m-%d %H:%M") if latest_mtime else ""
    return merged, last_str


@st.cache_data
def load_csv(name):
    """CSV 안전 로드 — 파일이 없거나 깨졌을 때 친절한 안내"""
    path = DATA_DIR / name
    try:
        df = pd.read_csv(path)
        df.columns = [c.strip().lstrip("﻿") for c in df.columns]
        return df
    except FileNotFoundError:
        st.error(f"⚠ 데이터 파일을 찾을 수 없습니다: `{name}`. 관리자에게 문의해 주세요.")
        st.stop()
    except Exception as e:
        st.error(f"⚠ 데이터를 읽는 중 문제가 발생했습니다: `{name}` ({type(e).__name__})")
        st.stop()


sido_df = load_csv("sido_summary.csv")
cluster_df = load_csv("cluster_summary.csv")
sens_df = load_csv("sensitivity_result.csv")
risk_df = load_csv("high_risk_schools_anonymized.csv")

st.title("세이프루프 — 학교 안전 대시보드")
st.caption(
    f"공공데이터로 본 전국 학교 시설 안전 현황 · 데이터 기준일: {DATA_BASIS}"
)
st.divider()

# === 핵심 수치 (KPI) ===
total_schools = int(cluster_df["학교수"].sum())
high_risk = int(cluster_df[cluster_df["위험군"] == "고위험"]["학교수"].sum())
caution = int(cluster_df[cluster_df["위험군"] == "주의"]["학교수"].sum())
ok = int(cluster_df[cluster_df["위험군"] == "양호"]["학교수"].sum())
# S1 = 우선순위 점수가 가장 높은 학교 526곳 (데이터에서 자동 추출)
S1_COUNT = min(526, len(risk_df))

# KPI 5개를 한 줄에 깔끔하게 정렬 (모바일에서는 반응형 CSS로 자동 세로 정렬)
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("전국 분석 학교", f"{total_schools:,}개교", "초·중·고 전수")
c2.metric("즉시 점검 필요 학교", f"{S1_COUNT:,}개교",
          f"전체의 {S1_COUNT/total_schools*100:.2f}%",
          delta_color="inverse",
          help="여러 위험 요인을 종합해 가장 시급한 학교 526곳을 뽑은 결과")
c3.metric("고위험 그룹", f"{high_risk:,}개교",
          f"전체의 {high_risk/total_schools*100:.1f}%",
          delta_color="inverse",
          help="3개 그룹(양호·주의·고위험) 자동 분류 중 고위험 전체")
c4.metric("주의 그룹", f"{caution:,}개교", f"전체의 {caution/total_schools*100:.1f}%", delta_color="off")
c5.metric("양호 그룹", f"{ok:,}개교", f"전체의 {ok/total_schools*100:.1f}%")

st.info(
    f"📌 **두 수치 차이 안내** — '즉시 점검 필요 학교({S1_COUNT}곳)'는 '고위험 그룹({high_risk:,}곳)' 중에서도 "
    f"가장 시급한 상위 학교만 추린 것입니다. 두 수치 모두 같은 데이터에서 나왔습니다."
)

# === 점검 환원 데이터 자동 합산 (점검 프로그램과의 연결고리) ===
returned_df, returned_last_time = load_returned_data(str(SHARED_DIR))
returned_count = len(returned_df) if not returned_df.empty else 0

if returned_count > 0:
    col_msg, col_btn = st.columns([5, 1])
    with col_msg:
        st.success(
            f"📥 **점검 환원 데이터 {returned_count}건 반영됨** "
            f"(마지막 갱신: {returned_last_time}) — "
            f"학교 현장 점검 결과가 추가되어 이 대시보드가 한층 정교해졌습니다."
        )
    with col_btn:
        if st.button("🔄 새로고침", help="환원 즉시 반영하려면 클릭",
                      key="refresh_returned"):
            load_returned_data.clear()
            st.rerun()
    with st.expander(f"환원 데이터 상세 보기 (학교 {returned_count}곳)"):
        st.caption(
            "교육청 담당자가 학교 점검 결과를 익명화·집계해 공공데이터로 환원한 결과입니다. "
            "개별 학교는 익명 ID(SHA-256 해시)로만 표시됩니다."
        )
        # 시도 분포
        if "sido" in returned_df.columns:
            sido_dist = returned_df["sido"].value_counts().reset_index()
            sido_dist.columns = ["시도교육청", "환원 건수"]
            colA, colB = st.columns([1, 1])
            with colA:
                st.markdown("**시도별 환원 분포**")
                st.dataframe(sido_dist, use_container_width=True, hide_index=True)
            with colB:
                if "safety_score" in returned_df.columns:
                    avg = returned_df["safety_score"].dropna().mean()
                    st.metric("환원 학교 평균 안전점수", f"{avg:.1f}점" if pd.notna(avg) else "—")
                if "grade" in returned_df.columns:
                    grade_dist = returned_df["grade"].value_counts().to_dict()
                    st.markdown("**등급 분포**")
                    st.write(grade_dist)
        # 원본 표
        st.markdown("**환원 데이터 원본 (익명)**")
        st.dataframe(returned_df, use_container_width=True, height=300)

st.divider()

# === 탭 ===
tab1, tab_map, tab2, tab3, tab4 = st.tabs([
    "시도별 현황",
    "지도로 보기",
    "그룹 분류",
    "결과 안정성",
    "고위험 학교 명단",
])

# ────────────────────────────────────────────────────
# 탭 1 — 시도별 현황
# ────────────────────────────────────────────────────
with tab1:
    st.subheader("시도교육청별 학교 안전 현황")
    st.caption("17개 시도교육청을 비교해 어느 지역에 위험 학교가 많은지 보여줍니다.")
    col1, col2 = st.columns([3, 1])
    with col2:
        sort_choice = st.selectbox(
            "어떤 기준으로 볼까요?",
            {
                "고위험_학교수": "고위험 학교 수",
                "고위험_비율": "고위험 비율(%)",
                "위험도_평균": "평균 위험도 점수",
                "학교수": "전체 학교 수",
            }.values(),
            index=0,
        )
        # 라벨 → 컬럼명 역매핑
        label_to_col = {"고위험 학교 수": "고위험_학교수", "고위험 비율(%)": "고위험_비율",
                        "평균 위험도 점수": "위험도_평균", "전체 학교 수": "학교수"}
        sort_by = label_to_col[sort_choice]
        sort_order = st.radio("정렬 순서", ["높은 순", "낮은 순"], horizontal=True)
    sido_sorted = sido_df.sort_values(by=sort_by, ascending=(sort_order == "낮은 순"))
    with col1:
        fig = px.bar(sido_sorted, x="시도교육청", y=sort_by, color="고위험_비율",
                     color_continuous_scale=["#10b981", "#f59e0b", "#dc2626"],
                     title=f"시도교육청별 {sort_choice}",
                     labels={sort_by: sort_choice, "시도교육청": "", "고위험_비율": "고위험 비율(%)"})
        fig.update_layout(xaxis_tickangle=-45, height=500)
        st.plotly_chart(fig, use_container_width=True)
    with st.expander("전체 시도별 상세 데이터 보기"):
        st.dataframe(sido_sorted.reset_index(drop=True), use_container_width=True, height=400)

# ────────────────────────────────────────────────────
# 탭 2 — 지도
# ────────────────────────────────────────────────────
with tab_map:
    st.subheader("지도에서 한눈에 보기")
    st.caption("원을 클릭하면 자세한 정보가 나옵니다. 마우스 휠로 확대·축소할 수 있습니다.")
    map_choice = st.radio(
        "어떤 지도를 볼까요?",
        ["시도별 (17개 시도교육청)", "고위험 상위 100개 학교 (학교명 비공개)"],
        horizontal=True,
    )
    map_files = {
        "시도별 (17개 시도교육청)": "data/maps/risk_map_sido.html",
        "고위험 상위 100개 학교 (학교명 비공개)": "data/maps/risk_map_top100.html",
    }
    map_path = Path(__file__).parent / map_files[map_choice]
    if map_path.exists():
        with open(map_path, "r", encoding="utf-8") as f:
            map_html = f.read()
        components.html(map_html, height=720, scrolling=True)
    else:
        st.error(f"지도 파일을 찾을 수 없습니다: {map_path.name}")
    st.caption(
        "※ 학교명·정확한 주소는 표시하지 않습니다(특정 학교에 '고위험'이라는 낙인을 막기 위함). "
        "더 상세한 시군구 단위 지도는 파일 크기 관계로 제외되었습니다."
    )

# ────────────────────────────────────────────────────
# 탭 3 — 그룹 분류 (K-Means)
# ────────────────────────────────────────────────────
with tab2:
    st.subheader("전국 학교를 3개 그룹으로 자동 분류")
    st.caption(
        "비슷한 위험 요인을 가진 학교끼리 묶어 '양호 / 주의 / 고위험' 3개 그룹으로 분류했습니다. "
        "사람이 임의로 나눈 게 아니라 컴퓨터가 데이터를 보고 자동으로 분류합니다."
    )
    col1, col2 = st.columns([2, 1])
    colors = {"양호": "#10b981", "주의": "#f59e0b", "고위험": "#dc2626"}
    with col1:
        fig = go.Figure()
        for _, row in cluster_df.iterrows():
            fig.add_trace(go.Bar(
                name=row["위험군"] + " 그룹",
                x=["관리 안 된 영역 수", "환경 위험 항목 수", "마지막 점검 후 일수(÷1,000)"],
                y=[row["미관리_평균"], row["환경위험_평균"], row["경과일_평균"] / 1000],
                marker_color=colors.get(row["위험군"], "#6b7280"),
            ))
        fig.update_layout(title="그룹별 평균 위험 요인", barmode="group", height=400)
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        st.markdown("### 그룹별 학교 수")
        for _, row in cluster_df.iterrows():
            color = colors.get(row["위험군"], "#6b7280")
            st.markdown(
                f'''<div style="padding:10px;border-left:4px solid {color};margin-bottom:10px;background:#f9fafb;border-radius:4px;">
                <b style="color:{color};">{row["위험군"]} 그룹</b><br>
                <span style="font-size:20pt;font-weight:700;">{int(row["학교수"]):,}</span> 개교 ({row["비율(%)"]}%)
                </div>''',
                unsafe_allow_html=True,
            )
    with st.expander("그룹별 상세 데이터 보기"):
        st.dataframe(cluster_df, use_container_width=True)
    with st.expander("🔍 분석에 사용한 비중(가중치)이 어떻게 정해졌나요?"):
        st.markdown(
            f"""
            세 가지 위험 요인의 비중은 데이터 자체에서 자동으로 계산한 값을 사용했습니다(객관적 방법).

            | 위험 요인 | 비중 | 의미 |
            |---|---:|---|
            | 관리 안 된 점검 영역 수 | **{W_MISMANAGE:.4f}** | 학교에서 점검·관리가 안 된 시설 영역이 몇 개인가 |
            | 환경 위험 항목 수 | **{W_ENVRISK:.4f}** | 환경위생 점검에서 부적합·미실시로 잡힌 항목 수 |
            | 마지막 점검 후 경과일 | **{W_DAYS:.4f}** | 가장 최근 점검 후 며칠이 지났나 |

            합계는 1.00입니다. 학교 간 차이가 큰(=구분 정보가 많은) 요인일수록 비중을 크게 부여하는
            **엔트로피 가중치** 방법으로 계산했으며, 사전에 직관적으로 설정한 비중(5:3:2)과도 거의 일치합니다.
            """
        )

# ────────────────────────────────────────────────────
# 탭 4 — 결과 안정성 (민감도)
# ────────────────────────────────────────────────────
with tab3:
    st.subheader("결과가 얼마나 안정적인가?")
    st.caption(
        "비중을 ±20% 흔들었을 때 '즉시 점검 필요 학교 526곳' 명단이 얼마나 유지되는지 확인합니다. "
        "겹침 비율이 높을수록 결과가 안정적입니다."
    )
    if "jaccard" in sens_df.columns and "overlap(%)" in sens_df.columns:
        col1, col2 = st.columns([3, 1])
        with col1:
            fig = px.scatter(
                sens_df, x="overlap(%)", y="jaccard",
                hover_data=["dm(%)", "de(%)", "dd(%)"],
                title="시나리오별 학교 명단 겹침 비율 (점 1개 = 비중 변동 시나리오)",
                labels={"overlap(%)": "기존 명단과 겹치는 비율(%)",
                        "jaccard": "겹침 점수(0~1, 1=완전 동일)"},
            )
            fig.update_traces(marker=dict(size=10, color="#1f3a8a", opacity=0.7))
            fig.update_layout(height=420)
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            st.markdown("### 한눈에 보기")
            st.metric("총 시나리오", f"{len(sens_df)}개")
            st.metric("겹침 비율 중앙값", f"{sens_df['overlap(%)'].median():.1f}%")
            st.metric("최소 겹침", f"{sens_df['overlap(%)'].min():.1f}%")
            st.metric("최대 겹침", f"{sens_df['overlap(%)'].max():.1f}%")
            st.caption("→ 중앙값 90% 이상이면 매우 안정적인 결과로 해석합니다.")
    with st.expander("전체 시나리오 결과 보기"):
        st.dataframe(sens_df, use_container_width=True, height=400)

# ────────────────────────────────────────────────────
# 탭 5 — 고위험 학교 명단
# ────────────────────────────────────────────────────
with tab4:
    st.subheader("고위험 학교 현황")
    st.caption(
        "특정 학교에 '고위험' 낙인이 찍히지 않도록 학교명·정확한 위치는 비공개입니다. "
        "시도교육청·학교급·설립 유형 단위로만 조회할 수 있습니다."
    )
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        risk_scope = st.radio(
            "어떤 학교를 볼까요?",
            [f"즉시 점검 필요 (상위 {S1_COUNT}곳)", f"고위험 그룹 전체 ({high_risk:,}곳)"],
            index=0,
        )
    with col2:
        sido_filter = st.multiselect("시도교육청", options=sorted(risk_df["시도교육청"].unique()), default=[])
    with col3:
        level_opts = sorted(risk_df["학교급"].dropna().unique()) if "학교급" in risk_df.columns else []
        level_filter = st.multiselect("학교급", options=level_opts, default=[])
    with col4:
        est_opts = sorted(risk_df["설립구분"].dropna().unique()) if "설립구분" in risk_df.columns else []
        est_filter = st.multiselect("설립 유형", options=est_opts, default=[])

    if risk_scope.startswith("즉시") and "우선순위_점수" in risk_df.columns:
        filtered = risk_df.nlargest(S1_COUNT, "우선순위_점수").copy()
    else:
        filtered = risk_df.copy()

    if sido_filter:
        filtered = filtered[filtered["시도교육청"].isin(sido_filter)]
    if level_filter and "학교급" in filtered.columns:
        filtered = filtered[filtered["학교급"].isin(level_filter)]
    if est_filter and "설립구분" in filtered.columns:
        filtered = filtered[filtered["설립구분"].isin(est_filter)]

    st.metric("선택한 조건의 학교 수", f"{len(filtered):,}개교")

    # 한글 친화 컬럼명으로 표시
    col_rename = {
        "학교_익명ID": "익명 ID",
        "시도교육청": "시도교육청",
        "학교급": "학교급",
        "설립구분": "설립 유형",
        "위험군": "위험 그룹",
        "위험도_점수": "위험도 점수",
        "우선순위_점수": "우선순위 점수",
        "미관리_영역수": "관리 안 된 영역 수",
        "환경_위험항목_수": "환경 위험 항목 수",
        "점검경과일_평균": "마지막 점검 후 일수",
        "학생수": "학생 수",
    }
    display_cols = [c for c in col_rename.keys() if c in filtered.columns]
    view = filtered[display_cols].rename(columns=col_rename).reset_index(drop=True)
    st.dataframe(view, use_container_width=True, height=500)
    csv = view.to_csv(index=False, encoding="utf-8-sig")
    st.download_button("선택한 조건의 데이터 내려받기 (CSV)", csv, "학교_안전_현황.csv", "text/csv")

# ────────────────────────────────────────────────────
# 한계 안내 (정직성)
# ────────────────────────────────────────────────────
st.divider()
with st.expander("📌 이 대시보드가 보여주는 것과 앞으로 더 보여줄 것"):
    st.markdown(
        """
        이 대시보드는 **현재 공공데이터로 볼 수 있는 학교 안전 현황**을 한눈에 정리한 것입니다.
        다만 공공데이터만으로는 학교 안전의 모든 면을 볼 수 없습니다. **보이지 않는 영역까지
        함께 다루는 것이 세이프루프(SafeLoop)의 목표**이며, 단계별로 다음을 채워가고 있습니다.

        **🏗 건물 그 자체의 상태**
        공공데이터에는 학교 건물의 준공연도·구조 정보가 공개되어 있지 않습니다. 그래서 현재 분석은
        "건물을 얼마나 잘 관리하는가"에 집중되어 있고, "건물이 얼마나 오래되었는가"는 다루지
        못합니다. 점검 결과가 누적되면 이 정보까지 자연스럽게 포함됩니다.

        **🔬 공간 단위의 위험 — 세이프루프가 채우려는 핵심 영역**
        현행 공공데이터는 학교 단위로만 제공되어 과학실·체육관·조리실 같은 **공간별 위험**은
        보이지 않습니다. 세이프루프 점검 앱이 AI 비전으로 공간별 점검 결과를 수집하면,
        이 빈 자리가 채워져 대시보드 자체가 더 정교해집니다.

        **📊 점검의 깊이**
        현재는 "점검 영역이 통과되었는가"라는 형식적 기록만 공개됩니다. 세이프루프 앱은
        법령 기반 표준 항목 36개와 별칭 300개 이상을 적용해, **무엇을 어떻게 점검했는지**까지
        구조화된 데이터로 만듭니다.

        **🧪 사고 발생 전의 예방 도구**
        이 대시보드는 사고가 일어난 후의 통계가 아니라 **사고가 나기 전의 위험 신호**를 보여주는
        도구입니다. 향후 학교 안전사고 통계가 누적되면 그 결과와 본 모델을 함께 비교해 신뢰도를
        더 높여갈 계획입니다.

        **🔄 데이터 순환 — 다음 단계로 이어집니다**
        지금 보시는 데이터는 분기별로 공공데이터포털에서 갱신됩니다. 점검 앱에서 모인 결과가
        교육시설통합정보망(KEIIS)·공공데이터포털로 환원되면, **다음 분기에는 이 대시보드도
        더 풍부하고 정확해집니다**. 같은 시스템이 스스로 더 똑똑해지는 구조입니다.
        """
    )

# ────────────────────────────────────────────────────
# 푸터 — "팀:" 표기 삭제, 대회 텍스트 삭제
# ────────────────────────────────────────────────────
st.divider()
col1, col2, col3 = st.columns(3)
col1.markdown("**서비스**: 세이프루프 (SafeLoop)")
col2.markdown("**분석 방법**: 자동 그룹 분류 + 가중 점수")
col3.markdown("**데이터 출처**: 학교알리미 · KEDI 교육통계 (출처표시 라이선스 KOGL Type 1)")
st.caption(
    f"© 2026 세이프루프 · 데이터 기준일: {DATA_BASIS} · "
    "학교 안전을 위한 공공데이터 시각화"
)
