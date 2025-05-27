import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pymongo import MongoClient
from dateutil import parser
import re
from nltk.corpus import stopwords
from wordcloud import WordCloud
import nltk

# ✅ Download stopwords (jika pertama kali)
nltk.download('stopwords')

# ================================
# 🔌 Koneksi ke MongoDB Atlas via secrets.toml
# ================================
client = MongoClient(st.secrets["MONGO_URI"])
collection = client['silatdb']['silat_artikel']

# ================================
# 📥 Ambil data dari MongoDB
# ================================
@st.cache_data
def load_data():
    data = list(collection.find({}, {'_id': 0}))
    return pd.DataFrame(data)

df = load_data()

if df.empty:
    st.error("❌ Data tidak ditemukan di MongoDB.")
    st.stop()

# ================================
# 🧹 Parsing tanggal dan konten
# ================================
def parse_tanggal(tanggal):
    if not tanggal:
        return None
    try:
        return parser.parse(tanggal, dayfirst=True, fuzzy=True)
    except:
        return None

if 'date' in df.columns:
    df['tanggal'] = df['date'].apply(parse_tanggal)
    df = df.dropna(subset=['tanggal'])

# ================================
# 🧹 Bersihkan konten untuk WordCloud
# ================================
stop_words = set(stopwords.words('indonesian'))

def bersihkan_teks(teks):
    if not teks or not isinstance(teks, str):
        return ''
    tokens = re.findall(r'\b\w+\b', teks.lower())
    tokens = [t for t in tokens if t not in stop_words]
    return ' '.join(tokens)

if 'content' in df.columns:
    df['clean_content'] = df['content'].apply(bersihkan_teks)
else:
    df['clean_content'] = ''

# ================================
# 🎨 Streamlit UI
# ================================
st.title("📊 Artikel Pencak Silat - Scraping Dashboard")

# ================================
# 🧭 Sidebar Filter
# ================================
st.sidebar.header("🔍 Filter Artikel")

# Filter sumber berita
sumber_list = df['sumber'].dropna().unique().tolist()
selected_sumber = st.sidebar.multiselect("Sumber Berita", options=sumber_list, default=sumber_list)

# Filter rentang tanggal
min_date = df['tanggal'].min().date()
max_date = df['tanggal'].max().date()
start_date, end_date = st.sidebar.date_input("Rentang Tanggal", [min_date, max_date])

# ================================
# 🔍 Terapkan Filter
# ================================
filtered_df = df[
    (df['sumber'].isin(selected_sumber)) &
    (df['tanggal'].dt.date >= start_date) &
    (df['tanggal'].dt.date <= end_date)
]

# ================================
# 📄 Tabel Data Artikel
# ================================
st.subheader("📄 Data Artikel Terfilter")
if not filtered_df.empty:
    st.dataframe(filtered_df[['title', 'sumber', 'tanggal', 'link']])
else:
    st.warning("❌ Tidak ada data untuk filter yang dipilih.")

# ================================
# 📊 Jumlah Artikel per Sumber
# ================================
if not filtered_df.empty:
    st.subheader("📈 Jumlah Artikel per Sumber")
    sumber_count = filtered_df['sumber'].value_counts()
    st.bar_chart(sumber_count)

# ================================
# 📈 Tren Artikel per Tanggal
# ================================
if not filtered_df.empty:
    st.subheader("🕒 Tren Artikel per Tanggal")
    trend = filtered_df.groupby(filtered_df['tanggal'].dt.date).size().reset_index(name='jumlah')
    fig, ax = plt.subplots(figsize=(10, 4))
    sns.lineplot(data=trend, x='tanggal', y='jumlah', marker='o', ax=ax)
    ax.set_title("Tren Jumlah Artikel")
    st.pyplot(fig)

# ================================
# ☁️ WordCloud dari Artikel
# ================================
if not filtered_df.empty:
    st.subheader("☁️ WordCloud dari Konten Artikel")
    all_text = ' '.join(filtered_df['clean_content'].dropna())
    if all_text.strip():
        wordcloud = WordCloud(width=800, height=400, background_color='white').generate(all_text)
        fig_wc, ax_wc = plt.subplots(figsize=(10, 5))
        ax_wc.imshow(wordcloud, interpolation='bilinear')
        ax_wc.axis('off')
        st.pyplot(fig_wc)
    else:
        st.info("Konten terlalu sedikit untuk dibuat WordCloud.")
