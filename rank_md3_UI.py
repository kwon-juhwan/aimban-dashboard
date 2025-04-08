import streamlit as st
import pandas as pd
import plotly.express as px
import os

st.set_page_config(layout="wide")
st.title("📊 상품별 키워드 순위 추이 대시보드")

# 📁 누적 CSV 로드
results_dir = "results"
all_data = []

if not os.path.exists(results_dir):
    st.error(f"❌ '{results_dir}' 폴더가 존재하지 않습니다.")
    st.stop()

csv_files = [f for f in sorted(os.listdir(results_dir)) if f.endswith(".csv")]

for file in csv_files:
    try:
        df = pd.read_csv(os.path.join(results_dir, file), encoding="utf-8-sig", header=None)
        if df.shape[1] < 4:
            continue
        df.columns = ["날짜", "키워드", "순위", "상품명"]
        all_data.append(df)
    except Exception as e:
        st.error(f"⚠️ '{file}' 읽는 중 오류 발생: {e}")

if not all_data:
    st.warning("유효한 결과 파일이 없습니다.")
    st.stop()

df_all = pd.concat(all_data, ignore_index=True)
df_all["날짜"] = pd.to_datetime(df_all["날짜"], errors="coerce")
df_all["순위"] = pd.to_numeric(df_all["순위"], errors="coerce")
df_all = df_all.dropna(subset=["날짜", "순위", "키워드", "상품명"])

# 🛍️ 상품 선택
unique_products = df_all["상품명"].unique().tolist()
selected_products = st.multiselect("🛍️ 개별 그래프로 표시할 상품 선택", unique_products, default=unique_products)

# 📈 상품별 개별 그래프 출력
for product in selected_products:
    st.markdown(f"### 🛍️ {product}")
    product_df = df_all[df_all["상품명"] == product]

    if product_df.empty:
        st.info(f"{product}에 대한 데이터가 없습니다.")
        continue

    fig = px.line(
        product_df,
        x="날짜",
        y="순위",
        color="키워드",
        markers=True,
        title=f"{product} - 키워드별 순위 추이",
        hover_data=["키워드", "순위"]
    )
    fig.update_yaxes(autorange="reversed", title="순위 (1위가 위)")
    fig.update_layout(xaxis_title="날짜", legend_title="키워드")
    st.plotly_chart(fig, use_container_width=True)
