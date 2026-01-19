import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib.font_manager as fm
import os

# -----------------------------------------------------------
# 1. Basic Settings
# -----------------------------------------------------------
st.set_page_config(page_title="Small Business Status Analysis", layout="wide")
sns.set_style("white")
plt.rcParams['figure.dpi'] = 150
plt.rcParams['axes.unicode_minus'] = False

# Font Settings
font_path = 'NanumGothic.ttf'
if os.path.exists(font_path):
    fm.fontManager.addfont(font_path)
    font_name = fm.FontProperties(fname=font_path).get_name()
    plt.rc('font', family=font_name)
else:
    if os.name == 'nt': plt.rc('font', family='Malgun Gothic')
    elif os.name == 'posix': plt.rc('font', family='AppleGothic')
    else: plt.rc('font', family='NanumGothic')

# -----------------------------------------------------------
# 2. Robust Data Load Function
# -----------------------------------------------------------
@st.cache_data
def load_and_fix_data(file_path):
    df = None
    
    encodings = ['utf-8', 'cp949', 'euc-kr']
    for enc in encodings:
        try:
            df = pd.read_csv(file_path, encoding=enc, header=None)
            sample_str = df.iloc[0:3].astype(str).to_string()
            if '운영점포수' in sample_str or '점포수' in sample_str:
                break
            else:
                df = None
        except:
            continue
            
    if df is None:
        raise ValueError("Cannot read the file. Please check encoding or file format.")

    # --- Header Fixing Logic ---
    is_fixed = False
    header_row_idx = None
    for i in range(3):
        row_vals = df.iloc[i].astype(str).values.tolist()
        if any('점포수' in v for v in row_vals):
            header_row_idx = i
            break
            
    if header_row_idx is not None:
        df.columns = df.iloc[header_row_idx]
        df = df.iloc[header_row_idx + 1:].reset_index(drop=True)
        is_fixed = True

    df.columns = df.columns.astype(str).str.replace(' ', '').str.strip()
    
    col_map = {
        '생활밀접업종별(1)': '대분류',
        '생활밀접업종별(2)': '소분류',
        '운영점포수(개)': '점포수',
        '종사자수(명)': '종사자수',
        '평균영업기간(년)': '영업기간',
        '면적당매출액(백만원/3.3㎡)': '면적당매출',
        '면적당종사자수(명/3.3㎡)': '면적당종사자'
    }
    
    new_cols = {}
    for col in df.columns:
        for k, v in col_map.items():
            if k in col:
                new_cols[col] = v
    df = df.rename(columns=new_cols)

    numeric_cols = ['점포수', '종사자수', '영업기간', '면적당매출', '면적당종사자']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.replace(',', '', regex=False)
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    return df, is_fixed

# -----------------------------------------------------------
# 3. Main Logic
# -----------------------------------------------------------
st.title("📊 Small Business Management Status (by Industry)")

current_dir = os.path.dirname(os.path.abspath(__file__))
file_name = "영세자영업+경영활동+현황(업종별)_20260116165351.csv"
file_path = os.path.join(current_dir, file_name)

try:
    if not os.path.exists(file_path):
        st.error(f"❌ File not found: {file_path}")
    else:
        df, was_fixed = load_and_fix_data(file_path)

        if was_fixed:
            st.toast("✅ Complex headers processed successfully!", icon="🛠️")

        # --- Sidebar ---
        st.sidebar.header("🔍 Settings")
        
        # 1. Select Major Industry
        if '대분류' in df.columns:
            majors = df['대분류'].unique().tolist()
            
            # '서울시'가 포함된 항목 제거
            majors = [m for m in majors if '서울시' not in m]

            default_idx = majors.index('외식업') if '외식업' in majors else 0
            
            if not majors:
                st.error("표시할 업종 데이터가 없습니다 (서울시 제외됨).")
                st.stop()
                
            selected_major = st.sidebar.selectbox("Select Major Industry", majors, index=default_idx)
        else:
            st.error("Column '대분류' not found.")
            st.stop()

        # 2. Filter Option
        hide_total = st.sidebar.checkbox("Hide 'Total' (소계)", value=True)

        # --- Data Filtering ---
        plot_df = df[df['대분류'] == selected_major].copy()
        
        if hide_total and '소분류' in df.columns:
            plot_df = plot_df[plot_df['소분류'] != '소계']

        plot_df = plot_df.sort_values('점포수', ascending=False)

        # --- Visualization ---
        st.subheader(f"✨ Detailed Analysis: {selected_major}")

        bar_cols = ['점포수', '종사자수']
        line_cols = ['면적당매출', '영업기간']

        available_bars = [c for c in bar_cols if c in plot_df.columns]
        available_lines = [c for c in line_cols if c in plot_df.columns]

        if not available_bars and not available_lines:
            st.warning("No data columns found for visualization.")
            st.dataframe(plot_df.head())
        else:
            fig, ax1 = plt.subplots(figsize=(14, 8))

            # 1. Bar Chart
            if available_bars:
                melted = plot_df.melt(id_vars='소분류', value_vars=available_bars, var_name='Metric', value_name='Value')
                sns.barplot(data=melted, x='소분류', y='Value', hue='Metric', ax=ax1, palette='Blues_d', alpha=0.7)
                
                ax1.legend(loc='upper left', frameon=False)
                ax1.set_ylabel("Count (Stores/People)", fontsize=12, fontweight='bold', color='navy')
                ax1.set_xlabel("Sub-Industry Category", fontsize=12)
                ax1.grid(axis='y', linestyle='--', alpha=0.5)
            
            # 2. Line Chart - Secondary Axis
            if available_lines:
                ax2 = ax1.twinx()
                colors = {'면적당매출': 'firebrick', '영업기간': 'orange'}
                markers = {'면적당매출': 'o', '영업기간': 's'}

                for col in available_lines:
                    sns.lineplot(x=plot_df['소분류'], y=plot_df[col], ax=ax2,
                                 marker=markers.get(col, 'o'),
                                 color=colors.get(col, 'black'),
                                 linewidth=3, label=col)
                
                ax2.set_ylabel("")
                # [수정] 아래 텍스트 추가 코드를 삭제함
                # ax2.text(...) 
                ax2.legend(loc='upper right', frameon=False)

            # X축 라벨 포맷팅 (세로 회전 + 3단어 줄바꿈)
            current_labels = [item.get_text() for item in ax1.get_xticklabels()]
            
            def format_label(text):
                words = text.split()
                chunks = [' '.join(words[i:i+3]) for i in range(0, len(words), 3)]
                return '\n'.join(chunks)
            
            new_labels = [format_label(l) for l in current_labels]
            ax1.set_xticklabels(new_labels, rotation=90)

            plt.title(f"Status of {selected_major} (2023)", fontsize=20, fontweight='bold', y=1.05)
            st.pyplot(fig)

            with st.expander("View Raw Data"):
                st.dataframe(plot_df)

except Exception as e:
    st.error(f"❌ Error occurred: {e}")