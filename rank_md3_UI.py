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
    # [날짜, 키워드, 순위, 상품명]
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

# 3-1. 상품 선택 (그래프용)
st.sidebar.subheader("상품 선택")

if filtered.empty:
    selected_title = None
else:
    product_titles = sorted(filtered["title"].unique())
    selected_title = st.sidebar.selectbox(
        "그래프로 볼 상품명",
        options=product_titles,
    )

# 4. 키워드별 제품 순위 추이 (그래프)
st.subheader("키워드별 제품 순위 추이 (그래프)")

if filtered.empty or selected_title is None:
    st.info("현재 필터 조건에 해당되는 데이터가 없거나, 선택할 상품명이 없습니다.")
else:
    # 선택한 상품만 필터
    product_df = filtered[filtered["title"] == selected_title].copy()

    if product_df.empty:
        st.info("선택한 상품에 대한 데이터가 없습니다.")
    else:
        # 순위 숫자형 변환
        product_df["rank"] = pd.to_numeric(product_df["rank"], errors="coerce")

        # 날짜-키워드별 최소 순위 사용 (같은 날짜에 여러 행이 있을 경우)
        grouped = (
            product_df
            .groupby(["date", "keyword"])["rank"]
            .min()
            .reset_index()
            .sort_values("date")
        )

        # 피벗: index=날짜, columns=키워드, values=순위
        chart_df = grouped.pivot(
            index="date",
            columns="keyword",
            values="rank",
        ).sort_index()

        # 그래프 제목에 상품명 표시
        st.caption(f"상품명: {selected_title}")

        if chart_df.empty:
            st.info("그래프로 표시할 데이터가 없습니다.")
        else:
            # X축: 날짜, Y축: 순위, 컬러/범례: 키워드
            st.line_chart(chart_df, use_container_width=True)
