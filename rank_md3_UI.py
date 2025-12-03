import streamlit as st
import pandas as pd
import glob
import os

RESULTS_DIR = "results"

st.set_page_config(page_title="노출 순위 대시보드", layout="wide")

st.title("네이버 쇼핑 노출 순위 대시보드")

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

# 2. 사이드바 필터
st.sidebar.header("필터")

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

# 3. 필터 적용
filtered = data[
    (data["date"].dt.date >= start_date)
    & (data["date"].dt.date <= end_date)
    & (data["keyword"].isin(selected_keywords))
].copy()

st.subheader("필터 적용된 결과표")
st.dataframe(filtered.sort_values(["date", "keyword", "rank"]))

# 4. 키워드별 제품 순위 추이 차트
st.subheader("키워드별 제품 순위 추이 (그래프)")

if not filtered.empty:
    # 순위 숫자형 변환
    filtered["rank"] = pd.to_numeric(filtered["rank"], errors="coerce")

    # 날짜 기준 정렬 후, (date, keyword, title) 별 최소 순위 사용
    chart_df = (
        filtered
        .sort_values("date")
        .groupby(["date", "keyword", "title"], as_index=False)["rank"]
        .min()
    )

    # 시리즈 이름: "키워드 | 상품명"
    chart_df["series"] = chart_df["keyword"] + " | " + chart_df["title"]

    # 피벗: 날짜별 (키워드+상품명) 순위
    pivot_df = chart_df.pivot(index="date", columns="series", values="rank")

    st.line_chart(pivot_df)
else:
    st.info("현재 필터 조건에 해당되는 데이터가 없습니다.")
