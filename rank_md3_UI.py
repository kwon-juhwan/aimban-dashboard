import streamlit as st
import pandas as pd
import glob
import os
import altair as alt

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

# 4. 키워드별 제품 순위 추이 (상품명별 개별 그래프)
st.subheader("키워드별 제품 순위 추이 (그래프)")

if not filtered.empty:
    # rank 숫자형
    filtered["rank"] = pd.to_numeric(filtered["rank"], errors="coerce")

    # Altair 기본 차트 (점 + 선)
    base = alt.Chart(filtered).encode(
        x=alt.X("date:T", title="날짜"),
        y=alt.Y("rank:Q", title="순위"),
        color=alt.Color(
            "keyword:N",
            title="키워드",             # 우측 범례 제목
            legend=alt.Legend(orient="right")
        ),
        tooltip=[
            alt.Tooltip("date:T", title="날짜"),
            alt.Tooltip("keyword:N", title="키워드"),
            alt.Tooltip("title:N", title="상품명"),
            alt.Tooltip("rank:Q", title="순위"),
        ],
    )

    # 키워드별 선 + 점
    line = base.mark_line(point=True)
    points = base.mark_circle(size=60)

    per_product_chart = (line + points).properties(
        width=280,
        height=200,
    )

    # 🔥 상품명(title)별로 그래프를 쪼개서 그리기 (facet)
    chart = per_product_chart.facet(
        facet=alt.Facet("title:N", title=None),
        columns=3,   # 한 줄에 3개씩 배치 (원하면 2나 4로 변경 가능)
    ).resolve_scale(
        y="shared",  # 모든 그래프가 같은 순위 스케일 사용
        x="shared",
        color="shared"
    )

    st.altair_chart(chart, use_container_width=True)
else:
    st.info("현재 필터 조건에 해당되는 데이터가 없습니다.")
