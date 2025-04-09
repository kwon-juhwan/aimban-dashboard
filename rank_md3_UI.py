import streamlit as st
import pandas as pd
import plotly.express as px
import os

# ✅ 페이지 설정
st.set_page_config(layout="wide", page_title="아임반 키워드 순위 대시보드", page_icon="📊")

# ✅ 네이버 스타일 HTML & CSS
st.markdown("""
    <style>
        body {
            background-color: #f9f9f9;
        }
        .title {
            font-size: 32px;
            font-weight: 700;
            color: #1e1e1e;
            text-align: left;
            margin-bottom: 0px;
        }
        .subtitle {
            font-size: 16px;
            color: #666666;
            margin-bottom: 30px;
        }
        .card {
            background-color: white;
            padding: 30px 25px 20px 25px;
            border-radius: 10px;
            box-shadow: 0px 1px 4px rgba(0, 0, 0, 0.05);
            margin-bottom: 30px;
        }
    </style>
""", unsafe_allow_html=True)

# ✅ 상단 제목
st.markdown("<div class='title'>📊 아임반 상품 키워드 순위 추이 대시보드</div>", unsafe_allow_html=True)
st.markdown("<div class='subtitle'>매일 수집된 데이터를 기반으로 키워드 순위 변화를 시각화합니다.</div>", unsafe_allow_html=True)

# ✅ results 폴더에서 CSV 불러오기
results_dir = "results"
os.makedirs(results_dir, exist_ok=True)

all_data = []
for file in sorted(os.listdir(results_dir)):
    if file.endswith(".csv"):
        df = pd.read_csv(os.path.join(results_dir, file), encoding="utf-8-sig", header=None)
        df.columns = ["날짜", "키워드", "순위", "상품명"]
        all_data.append(df)

if not all_data:
    st.warning("⚠️ 저장된 데이터가 없습니다. 먼저 수집 스크립트를 실행해 주세요.")
    st.stop()

df_all = pd.concat(all_data, ignore_index=True)
df_all["날짜"] = pd.to_datetime(df_all["날짜"], errors="coerce")
df_all["순위"] = pd.to_numeric(df_all["순위"], errors="coerce")
df_all = df_all.dropna(subset=["날짜", "키워드", "순위", "상품명"])
df_all = df_all.sort_values("날짜").drop_duplicates(subset=["날짜", "키워드", "상품명"], keep="first")  # ✅ 중복 제거 추가

# ✅ 사이드바 필터
st.sidebar.title("🔍 필터")
products = df_all["상품명"].unique().tolist()
selected_products = st.sidebar.multiselect("🛍️ 상품명 선택", products, default=products)

# ✅ 상품별 카드 UI로 시각화
for product in selected_products:
    st.markdown(f"<div class='card'><h4>🛍️ {product}</h4>", unsafe_allow_html=True)

    product_df = df_all[df_all["상품명"] == product]

    fig = px.line(
        product_df,
        x="날짜",
        y="순위",
        color="키워드",
        markers=True,
        title="",
        hover_data=["키워드", "순위"]
    )
    fig.update_yaxes(autorange="reversed", title="순위 (1위가 위)")
    fig.update_layout(
        xaxis_title="날짜",
        legend_title="키워드",
        title_font=dict(size=16),
        margin=dict(t=10, l=0, r=0, b=0),
        height=500
    )

    st.plotly_chart(fig, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)
