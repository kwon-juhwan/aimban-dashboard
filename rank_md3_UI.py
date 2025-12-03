import streamlit as st
import pandas as pd
import glob
import os
import altair as alt  # 그래프용

RESULTS_DIR = "results"

st.set_page_config(
    page_title="노출 순위 대시보드",
    page_icon="📈",
    layout="wide",
)

st.title("📊 네이버 쇼핑 노출 순위 대시보드")
st.caption("results 폴더의 CSV를 기반으로 키워드별 노출 순위 추이를 확인합니다.")

# =========================
# 1. CSV 파일 읽기
# =========================
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

# 날짜 타입으로 변환
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

# 아임반만 보기
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

# 순위 숫자형으로 변환 (요약/그래프에서 공통 사용)
if not filtered.empty:
    filtered["rank"] = pd.to_numeric(filtered["rank"], errors="coerce")

# =========================
# 3-1. 요약 정보 + 변화 분석
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
    col3.metric("노출 키워드 수", num_kw)
    col4.metric("최신 데이터 날짜", latest_date)

    # ---- 최근 날짜 대비 변화 분석 ----
    st.markdown("### 🔄 최근 날짜 대비 키워드 순위 변화")

    unique_dates = sorted(filtered["date"].dt.date.unique())
    if len(unique_dates) < 2:
        st.info("순위 변화를 보려면 최소 2일 이상의 데이터가 필요합니다.")
    else:
        last_date = unique_dates[-1]
        prev_date = unique_dates[-2]

        latest_df = filtered[filtered["date"].dt.date == last_date]
        prev_df = filtered[filtered["date"].dt.date == prev_date]

        latest_rank = (
            latest_df.groupby("keyword")["rank"]
            .min()
            .reset_index()
            .rename(columns={"rank": "latest_rank"})
        )
        prev_rank = (
            prev_df.groupby("keyword")["rank"]
            .min()
            .reset_index()
            .rename(columns={"rank": "prev_rank"})
        )

        merged = prev_rank.merge(latest_rank, on="keyword", how="outer")

        # 상승/하락 키워드 (두 날 모두에 존재하는 키워드만)
        change = merged.dropna(subset=["prev_rank", "latest_rank"]).copy()
        change["diff"] = change["prev_rank"] - change["latest_rank"]  # +면 상승, -면 하락

        improved = change[change["diff"] > 0].sort_values("diff", ascending=False).head(5)
        dropped = change[change["diff"] < 0].sort_values("diff", ascending=True).head(5)

        col_up, col_down = st.columns(2)

        with col_up:
            st.markdown(f"**📈 순위 상승 키워드 ( {prev_date} → {last_date} )**")
            if improved.empty:
                st.write("상승한 키워드가 없습니다.")
            else:
                show_up = improved.rename(
                    columns={
                        "keyword": "키워드",
                        "prev_rank": "이전 순위",
                        "latest_rank": "최근 순위",
                        "diff": "개선 폭",
                    }
                )
                st.dataframe(show_up, hide_index=True, use_container_width=True)

        with col_down:
            st.markdown(f"**📉 순위 하락 키워드 ( {prev_date} → {last_date} )**")
            if dropped.empty:
                st.write("하락한 키워드가 없습니다.")
            else:
                show_down = dropped.rename(
                    columns={
                        "keyword": "키워드",
                        "prev_rank": "이전 순위",
                        "latest_rank": "최근 순위",
                        "diff": "변화 폭",
                    }
                )
                st.dataframe(show_down, hide_index=True, use_container_width=True)

        # ---- 노출 추가 / 소멸 키워드 ----
        st.markdown("### 🆕 노출이 추가되거나 사라진 키워드")

        prev_only = prev_rank[~prev_rank["keyword"].isin(latest_rank["keyword"])]
        new_only = latest_rank[~latest_rank["keyword"].isin(prev_rank["keyword"])]

        col_new, col_lost = st.columns(2)
        with col_new:
            st.markdown(f"**새로 노출된 키워드 ( {last_date} 기준 )**")
            if new_only.empty:
                st.write("새로운 키워드가 없습니다.")
            else:
                st.write(", ".join(sorted(new_only["keyword"].tolist())))

        with col_lost:
            st.markdown(f"**노출이 사라진 키워드 ( {prev_date} 기준 )**")
            if prev_only.empty:
                st.write("사라진 키워드가 없습니다.")
            else:
                st.write(", ".join(sorted(prev_only["keyword"].tolist())))

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

    csv_bytes = filtered_sorted.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
    st.download_button(
        label="📥 필터 적용 데이터 다운로드 (CSV)",
        data=csv_bytes,
        file_name="naver_rank_filtered.csv",
        mime="text/csv",
    )

# =========================
# 4-1. 상품 선택 (그래프용)
# =========================
st.sidebar.subheader("📦 상품 선택(그래프용)")

if filtered.empty:
    selected_title = None
    product_titles = []
else:
    product_titles = sorted(filtered["title"].unique())
    selected_title = st.sidebar.selectbox(
        "그래프로 볼 상품명",
        options=product_titles,
    )

# 기본: 전체 그래프 보이게 (False)
show_only_selected = st.sidebar.checkbox("선택한 상품만 그래프로 보기", value=False)

# =========================
# 5. 키워드별 제품 순위 추이 (그래프)
# =========================
st.subheader("키워드별 제품 순위 추이 (그래프)")

if filtered.empty or not product_titles:
    st.info("그래프를 그릴 수 있는 데이터가 없습니다. 필터 조건을 확인해주세요.")
else:

    def draw_product_chart(title: str):
        """특정 상품명에 대한 키워드별 순위 추이 그래프 (Altair: 선 + 점 + 툴팁)"""
        product_df = filtered[filtered["title"] == title].copy()
        if product_df.empty:
            return

        # 같은 날짜에 같은 키워드가 여러 개 있으면 최소 순위만 사용
        grouped = (
            product_df.groupby(["date", "keyword"])["rank"]
            .min()
            .reset_index()
            .sort_values("date")
        )
        if grouped.empty:
            return

        # 🔹 y축 도메인에 여유를 주어 위·아래로 붙지 않게
        min_rank = grouped["rank"].min()
        max_rank = grouped["rank"].max()
        padding = max(3, int((max_rank - min_rank) * 0.1))  # 범위의 10% 또는 최소 3
        y_scale = alt.Scale(domain=[min_rank - padding, max_rank + padding])

        # 🔹 키워드 개수에 따라 그래프 높이를 키워서 점 간격 확보
        num_keywords = grouped["keyword"].nunique()
        height = max(260, 40 + num_keywords * 20)

        base = alt.Chart(grouped).encode(
            x=alt.X("date:T", title="날짜"),
            y=alt.Y("rank:Q", title="순위", scale=y_scale),
            color=alt.Color(
                "keyword:N",
                title="키워드",
                legend=alt.Legend(orient="bottom"),
            ),
            tooltip=[
                alt.Tooltip("date:T", title="날짜"),
                alt.Tooltip("keyword:N", title="키워드"),
                alt.Tooltip("rank:Q", title="순위"),
            ],
        )

        chart = base.mark_line(point=alt.OverlayMarkDef(size=55)).properties(
            height=height
        )

        st.caption(f"상품명: {title}")
        st.altair_chart(chart, use_container_width=True)
        st.markdown("---")

    # 5-1. 선택한 상품 그래프
    if selected_title is not None:
        draw_product_chart(selected_title)

    # 5-2. 나머지 상품 그래프 (기본: 전체)
    if not show_only_selected:
        for title in product_titles:
            if title == selected_title:
                continue
            draw_product_chart(title)
