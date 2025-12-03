import streamlit as st
import pandas as pd
import glob
import os

RESULTS_DIR = "results"

st.set_page_config(
    page_title="노출 순위 대시보드",
    page_icon="📈",
    layout="wide",
)

st.title("📊 네이버 쇼핑 노출 순위 대시보드")
st.caption("results 폴더의 CSV를 기반으로 키워드별 노출 순위 추이를 확인합니다.")

# 1. CSV 파일 읽기
csv_files = glob.glob(os.path.join(RESULTS_DIR, "*.csv"))

if not csv_files:
    st.warning("results 폴더에 CSV 파일이 없습니다. 먼저 수집 스크립트를 실행해주세요.")
    st.stop()

dfs = []
for f in csv_files:
    df = pd.read_csv(f, header=None, encoding="utf-8-sig")
    # rank_md3 기준: [날짜, 키워드, 순위, 상품명]
    df.columns = ["date", "keyword", "rank", "title"]
    dfs.append(df)

data = pd.concat(dfs, ignore_index=True)

# 날짜 타입 변환
data["date"] = pd.to_datetime(data["date"], errors="coerce")

# =========================
# 2. 사이드바 필터
# =========================
st.sidebar.header("🔎 필터")

# 날짜 필터
min_date = data["date"].min()
max_date = data["date"].max()
start_date, end_date = st.sidebar.date_input(
    "날짜 범위",
    value=(min_date.date(), max_date.date()),
    min_value=min_date.date(),
    max_value=max_date.date(),
)

# 키워드 필터
all_keywords = sorted(data["keyword"].unique())
selected_keywords = st.sidebar.multiselect(
    "키워드 선택",
    options=all_keywords,
    default=all_keywords,
)

# (옵션) 아임반만 보기 토글
only_aimban = st.sidebar.checkbox("상품명에 '아임반' 포함만 보기", value=False)

# =========================
# 3. 필터 적용
# =========================
filtered = data[
    (data["date"].dt.date >= start_date)
    & (data["date"].dt.date <= end_date)
    & (data["keyword"].isin(selected_keywords))
].copy()

if only_aimban:
    filtered = filtered[filtered["title"].str.contains("아임반", na=False)]

# =========================
# 3-1. 상단 요약 카드
# =========================
st.subheader("요약 정보")

if filtered.empty:
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("데이터 건수", 0)
    col2.metric("기간(일)", 0)
    col3.metric("선택된 키워드 수", len(selected_keywords))
    col4.metric("최신 데이터 날짜", "-")
else:
    num_rows = len(filtered)
    num_days = filtered["date"].dt.date.nunique()
    num_kw = filtered["keyword"].nunique()
    latest_date = filtered["date"].max().date().isoformat()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("데이터 건수", f"{num_rows:,}")
    col2.metric("기간(일)", num_days)
    col3.metric("선택된 키워드 수", num_kw)
    col4.metric("최신 데이터 날짜", latest_date)

# =========================
# 4. 필터 적용된 결과표
# =========================
st.subheader("필터 적용된 결과표")

if filtered.empty:
    st.info("현재 필터 조건에 해당되는 데이터가 없습니다.")
else:
    filtered_sorted = filtered.sort_values(["date", "keyword", "rank"])

    with st.expander("📄 상세 데이터 보기", expanded=True):
        st.dataframe(filtered_sorted, use_container_width=True)

    # 다운로드 버튼
    csv_bytes = filtered_sorted.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
    st.download_button(
        label="📥 필터 적용 데이터 다운로드 (CSV)",
        data=csv_bytes,
        file_name="naver_rank_filtered.csv",
        mime="text/csv",
    )

# =========================
# 4-1. 상품 선택 (키워드별 제품 노출순위용)
# =========================
st.sidebar.subheader("📦 상품 선택(그래프용)")

if filtered.empty:
    selected_title = None
else:
    product_titles = sorted(filtered["title"].unique())
    selected_title = st.sidebar.selectbox(
        "그래프로 볼 상품명",
        options=product_titles,
    )

# =========================
# 5. 키워드별 제품 노출 순위 추이 (그래프)
# =========================
st.subheader("키워드별 제품 순위 추이 (그래프)")

if filtered.empty or selected_title is None:
    st.info("그래프를 그릴 수 있는 데이터가 없습니다. 필터 조건이나 상품 선택을 확인해주세요.")
else:
    # 선택한 상품만 추출
    product_df = filtered[filtered["title"] == selected_title].copy()

    if product_df.empty:
        st.info("선택한 상품에 대한 데이터가 없습니다.")
    else:
        # 순위 숫자형으로
        product_df["rank"] = pd.to_numeric(product_df["rank"], errors="coerce")

        # 같은 날짜에 같은 키워드가 여러 번 있으면 최소 순위만 사용
        grouped = (
            product_df.groupby(["date", "keyword"])["rank"]
            .min()
            .reset_index()
            .sort_values("date")
        )

        # 날짜 x 키워드 피벗 → 각 키워드가 하나의 라인
        chart_df = grouped.pivot(
            index="date",
            columns="keyword",
            values="rank",
        ).sort_index()

        st.caption(f"상품명: {selected_title}")

        if chart_df.empty:
            st.info("그래프로 표시할 데이터가 없습니다.")
        else:
            # X축: 날짜, Y축: 순위, 각 라인: 키워드
            st.line_chart(chart_df, use_container_width=True)
