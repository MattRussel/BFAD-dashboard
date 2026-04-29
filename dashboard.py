import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

st.set_page_config(layout="wide")

st.sidebar.title("🚲 Bike Sharing Dashboard")
st.sidebar.markdown("Analisis data *Bike Sharing* berbasis data **hourly** dan **daily**")
st.sidebar.markdown("---")

# ========================
# LOAD DATA
# ========================
@st.cache_data
def load_data():
    df_day = pd.read_csv("day.csv")
    df_hour = pd.read_csv("hour.csv")

    df_day['dteday'] = pd.to_datetime(df_day['dteday'])
    df_hour['dteday'] = pd.to_datetime(df_hour['dteday'])

    return df_day, df_hour

df_day, df_hour = load_data()

# ========================
# SIDEBAR FILTER
# ========================
st.sidebar.header("🔎 Filter Data")

# Mapping musim
season_map = {1: 'Semi', 2: 'Panas', 3: 'Gugur', 4: 'Dingin'}
df_day['season_label'] = df_day['season'].map(season_map)

# Filter musim
selected_seasons = st.sidebar.multiselect(
    "🌦️ Filter Musim",
    options=df_day['season_label'].unique(),
    default=df_day['season_label'].unique()
)

# Filter hari kerja
working_filter = st.sidebar.selectbox(
    "📅 Filter Hari Kerja",
    options=["Semua", "Hari Kerja", "Libur"]
)

# Filter tanggal
min_date = df_day['dteday'].min()
max_date = df_day['dteday'].max()

date_range = st.sidebar.date_input(
    "📆 Pilih Rentang Tanggal",
    [min_date, max_date],
    min_value=min_date,
    max_value=max_date
)

# ========================
# APPLY FILTER
# ========================
start_date, end_date = date_range

df_day_filtered = df_day[
    (df_day['dteday'] >= pd.to_datetime(start_date)) &
    (df_day['dteday'] <= pd.to_datetime(end_date)) &
    (df_day['season_label'].isin(selected_seasons))
]

# Filter working day
if working_filter == "Hari Kerja":
    df_day_filtered = df_day_filtered[df_day_filtered['workingday'] == 1]
elif working_filter == "Libur":
    df_day_filtered = df_day_filtered[df_day_filtered['workingday'] == 0]

# Sinkron ke hourly
df_hour_filtered = df_hour[df_hour['dteday'].isin(df_day_filtered['dteday'])].copy()

# ========================
# AGREGASI HARIAN
# ========================
daily_hour = df_hour_filtered.groupby('dteday')['cnt'].sum().reset_index()
daily_hour['pct_change'] = daily_hour['cnt'].pct_change() * 100
daily_hour['drop_15'] = daily_hour['pct_change'] <= -15

# ========================
# TABS
# ========================
tab1, tab2, tab3, tab4 = st.tabs([
    "⏰ Pola Jam",
    "⚠️ Penurunan & Cuaca",
    "🌦️ Musim & Hari Kerja",
    "📊 Segmentasi Waktu"
])

# ========================
# TAB 1: POLA JAM
# ========================
with tab1:
    st.header("⏰ Pola Penyewaan Berdasarkan Jam")

    hourly_pattern = df_hour_filtered.groupby('hr')['cnt'].mean().reset_index()

    fig, ax = plt.subplots()
    sns.lineplot(x='hr', y='cnt', data=hourly_pattern, marker='o', ax=ax)
    ax.set_title('Sewa Sepeda Berdasarkan Jam (Rata-rata)')
    ax.set_xlabel('Jam')
    ax.set_ylabel('Jumlah Penyewaan')
    st.pyplot(fig)

# ========================
# TAB 2: PENURUNAN & CUACA
# ========================
with tab2:
    st.header("⚠️ Analisis Penurunan ≥ 15%")

    drop_days = daily_hour[daily_hour['drop_15'] == True]

    col1, col2 = st.columns(2)

    with col1:
        st.metric("Jumlah Hari Turun ≥15%", len(drop_days))

    with col2:
        st.metric("Total Hari", len(daily_hour))

    st.dataframe(drop_days.head())

    st.subheader("🌡️ Pengaruh Cuaca")

    df_analysis = pd.merge(df_hour_filtered, daily_hour[['dteday', 'drop_15']], on='dteday')

    df_analysis['temp_real'] = df_analysis['temp'] * 41
    df_analysis['hum_real'] = df_analysis['hum'] * 100

    col1, col2 = st.columns(2)

    with col1:
        fig, ax = plt.subplots()
        sns.boxplot(x='drop_15', y='temp_real', data=df_analysis, ax=ax)
        ax.set_title('Suhu saat Penurunan ≥15%')
        ax.set_xlabel('Penurunan ≥15%')
        ax.set_ylabel('Suhu (Celsius)')
        st.pyplot(fig)

    with col2:
        fig, ax = plt.subplots()
        sns.boxplot(x='drop_15', y='hum_real', data=df_analysis, ax=ax)
        ax.set_title('Kelembaban saat Penurunan ≥15%')
        ax.set_xlabel('Penurunan ≥15%')
        ax.set_ylabel('Kelembapan')
        st.pyplot(fig)

# ========================
# TAB 3: MUSIM & HARI KERJA
# ========================
with tab3:
    st.header("🌦️ Pengaruh Musim & Hari Kerja")

    season_working = df_day_filtered.groupby(['season_label', 'workingday'])['cnt'].mean().reset_index()

    fig, ax = plt.subplots()
    sns.barplot(x='season_label', y='cnt', hue='workingday', data=season_working, ax=ax)
    ax.set_title('Hari Kerja vs Libur per Musim')
    ax.set_xlabel('Musim')
    ax.set_ylabel('Rata-rata Penyewaan')
    ax.legend(title='Working Day (1=Ya)')
    st.pyplot(fig)

# ========================
# TAB 4: SEGMENTASI WAKTU
# ========================
with tab4:
    st.header("📊 Segmentasi Waktu")

    def categorize_hour(hr):
        if 7 <= hr <= 9 or 17 <= hr <= 19:
            return 'Peak Hour'
        elif 10 <= hr <= 16:
            return 'Mid Day'
        else:
            return 'Off Peak'

    df_hour_filtered['time_segment'] = df_hour_filtered['hr'].apply(categorize_hour)

    time_segment_analysis = df_hour_filtered.groupby('time_segment')['cnt'].mean().reset_index()

    fig, ax = plt.subplots()
    sns.barplot(x='time_segment', y='cnt', data=time_segment_analysis, ax=ax)
    ax.set_title('Demand Berdasarkan Segment Waktu')
    ax.set_xlabel('Pembagian Waktu')
    ax.set_ylabel('Rata-rata Penyewaan')
    st.pyplot(fig)

# ========================
# INSIGHT
# ========================
st.header("📌 Insight Utama")

st.markdown("""
### 🔍 Temuan Penting:
- Penggunaan sepeda tinggi pada jam sibuk (pagi & sore)
- Musim tertentu memiliki permintaan lebih tinggi
- Hari dengan penurunan ≥15% cenderung: suhu lebih rendah, kelembaban lebih tinggi
- Penyewaan pada hari kerja lebih tinggi dibanding hari libur
- Peak Hour: demand tertinggi
- Off-peak: rendah, bisa menjadi peluang promo

### 🎯 Rekomendasi:
- Tambahkan promo saat cuaca buruk
- Memberikan promo pada hari libur untuk meningkatkan penggunaan
- Mengoptimalkan strategi berdasarkan kondisi cuaca
""")
