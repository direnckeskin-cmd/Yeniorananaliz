import streamlit as st
import pandas as pd
import numpy as np
import os

# Sayfa Ayarları
st.set_page_config(page_title="Oran Analiz Pro", page_icon="⚽", layout="centered")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EXCEL_PATH = os.path.join(BASE_DIR, "ORAN ANALİZ TABLOSU.xlsb")
CACHE_PATH = os.path.join(BASE_DIR, "cache_data.pkl")

# Streamlit Önbellekleme
@st.cache_data(show_spinner=False)
def load_data():
    # 1. Öncelik: Önbellek Dosyası (cache_data.pkl)
    if os.path.exists(CACHE_PATH):
        try:
            return pd.read_pickle(CACHE_PATH)
        except Exception as e:
            st.warning(f"⚠️ pkl dosyası okunamadı, excel deneniyor... Hata: {e}")
            pass
    
    # 2. Öncelik: Excel Dosyası (ORAN ANALİZ TABLOSU.xlsb)
    if os.path.exists(EXCEL_PATH):
        try:
            try:
                df = pd.read_excel(EXCEL_PATH, engine='pyxlsb', header=1)
            except Exception:
                df = pd.read_excel(EXCEL_PATH, header=1)

            df['MS1'] = pd.to_numeric(df['MS1'], errors='coerce')
            df['MSX'] = pd.to_numeric(df['MSX'], errors='coerce')
            df['MS2'] = pd.to_numeric(df['MS2'], errors='coerce')
            df_clean = df.dropna(subset=['MS1', 'MSX', 'MS2', 'İY SKOR', 'MS SKOR']).copy()
            df_clean.to_pickle(CACHE_PATH)
            return df_clean
        except Exception as e:
            st.error(f"Excel okunurken hata oluştu: {e}")
            return None
            
    return None

# Başlık
st.markdown("<h2 style='text-align: center; color: #00FF7F;'>⚽ ORAN ANALİZ VE PATTERN MOTORU</h2>", unsafe_allow_html=True)

# Veriyi Yükle
with st.spinner("📊 Veriler yükleniyor..."):
    df_clean = load_data()

if df_clean is None:
    mevcut_dosyalar = os.listdir(BASE_DIR)
    st.error("❌ Veri dosyası bulunamadı!")
    st.info(f"📂 Sunucu klasöründeki mevcut dosyalar: {mevcut_dosyalar}")
    st.warning("Lütfen GitHub deposuna 'cache_data.pkl' veya 'ORAN ANALİZ TABLOSU.xlsb' dosyasını yüklediğinizden emin olun.")
    st.stop()

st.success(f"✅ **{len(df_clean):,}** analize hazır maç hafızada!")

# Giriş Alanları
col1, col2, col3 = st.columns(3)
with col1:
    ms1_input = st.text_input("MS 1 Oranı", value="1.58")
with col2:
    msx_input = st.text_input("MS X Oranı", value="3.70")
with col3:
    ms2_input = st.text_input("MS 2 Oranı", value="3.31")

btn_analiz = st.button("ANALİZ ET 🚀", use_container_width=True, type="primary")

if btn_analiz:
    try:
        ms1_v = float(ms1_input.strip().replace(',', '.'))
        msx_v = float(msx_input.strip().replace(',', '.'))
        ms2_v = float(ms2_input.strip().replace(',', '.'))
    except ValueError:
        st.error("Lütfen oranları geçerli sayı olarak girin! (Örn: 1.85)")
        st.stop()

    # Yakınlık Hesaplama
    df_calc = df_clean.copy()
    df_calc['Mesafe'] = np.sqrt(
        (df_calc['MS1'] - ms1_v)**2 + 
        (df_calc['MSX'] - msx_v)**2 + 
        (df_calc['MS2'] - ms2_v)**2
    )
    benzerler = df_calc.sort_values('Mesafe').head(15).copy()

    def skor_ayir(s):
        try:
            p = str(s).strip().split('-')
            return int(p[0]), int(p[1])
        except:
            return 0, 0

    benzerler[['iy_e', 'iy_d']] = benzerler['İY SKOR'].apply(lambda x: pd.Series(skor_ayir(x)))
    benzerler[['ms_e', 'ms_d']] = benzerler['MS SKOR'].apply(lambda x: pd.Series(skor_ayir(x)))
    
    benzerler['iy_toplam'] = benzerler['iy_e'] + benzerler['iy_d']
    benzerler['ms_toplam'] = benzerler['ms_e'] + benzerler['ms_d']
    benzerler['kg_var'] = (benzerler['ms_e'] > 0) & (benzerler['ms_d'] > 0)

    def get_ht_ft(row):
        ht = '1' if row['iy_e'] > row['iy_d'] else ('2' if row['iy_d'] > row['iy_e'] else 'X')
        ft = '1' if row['ms_e'] > row['ms_d'] else ('2' if row['ms_d'] > row['ms_e'] else 'X')
        return f"{ht}/{ft}"

    benzerler['HT/FT'] = benzerler.apply(get_ht_ft, axis=1)

    def get_durum(row):
        tags = []
        ht = '1' if row['iy_e'] > row['iy_d'] else ('2' if row['iy_d'] > row['iy_e'] else 'X')
        ft = '1' if row['ms_e'] > row['ms_d'] else ('2' if row['ms_d'] > row['ms_e'] else 'X')
        if row['ms_toplam'] <= 1: tags.append("KISIR")
        elif row['ms_toplam'] >= 3: tags.append("GOL")
        if ht in ['1', '2'] and ft in ['1', '2'] and ht != ft: tags.append("!!DN")
        if row['ms_toplam'] >= 6: tags.append("!!6+")
        if row['kg_var']: tags.append("[KG]")
        return " ".join(tags) if tags else "0-0"

    benzerler['DURUM'] = benzerler.apply(get_durum, axis=1)

    # İstatistik Hesaplamaları (Genişletilmiş)
    benzerler['2y_e'] = benzerler['ms_e'] - benzerler['iy_e']
    benzerler['2y_d'] = benzerler['ms_d'] - benzerler['iy_d']

    iy_05 = round((benzerler['iy_toplam'] >= 1).mean() * 100)
    iy_15 = round((benzerler['iy_toplam'] >= 2).mean() * 100)
    iy_kg = round(((benzerler['iy_e'] > 0) & (benzerler['iy_d'] > 0)).mean() * 100)

    ms_25 = round((benzerler['ms_toplam'] >= 3).mean() * 100)
    ms_35 = round((benzerler['ms_toplam'] >= 4).mean() * 100)
    ms_6plus = round((benzerler['ms_toplam'] >= 6).mean() * 100)

    kg_v = round(benzerler['kg_var'].mean() * 100)
    y2_kg = round(((benzerler['2y_e'] > 0) & (benzerler['2y_d'] > 0)).mean() * 100)

    # İstatistik Kutuları
    st.subheader("🎯 İstatistik Yüzdeleri")
    
    col1_m, col2_m, col3_m = st.columns(3)
    col1_m.metric("İY 0.5+", f"%{iy_05}")
    col2_m.metric("İY 1.5+", f"%{iy_15}")
    col3_m.metric("İY KG VAR", f"%{iy_kg}")

    col4_m, col5_m, col6_m = st.columns(3)
    col4_m.metric("MS 2.5+", f"%{ms_25}")
    col5_m.metric("MS 3.5+", f"%{ms_35}")
    col6_m.metric("6+ GOL 🔥", f"%{ms_6plus}")

    col7_m, col8_m = st.columns(2)
    col7_m.metric("MS KG VAR", f"%{kg_v}")
    col8_m.metric("2.Y KG VAR ⚽", f"%{y2_kg}")

    # En Olası Skorlar
    st.markdown("---")
    st.subheader("📊 En Olası Skorlar")
    skor_counts = benzerler['MS SKOR'].value_counts()
    for skor, count in skor_counts.head(5).items():
        pct = (count / len(benzerler)) * 100
        st.write(f"• **{skor}** — %{pct:.1f}")

    # Terminal Tablo
    st.markdown("---")
    st.subheader("📋 Benzer Maçlar")
    
    lines = []
    header_line = f"{'SEZON/LİG':<12} | {'MAÇ':<20} | {'İY':<4} | {'MS':<4} | {'HT/FT':<7} | {'DURUM'}"
    sep_line = "-" * 67

    lines.append(f"<span style='color:#00FF66;'>{header_line}</span>")
    lines.append(f"<span style='color:#00FF66;'>{sep_line}</span>")

    for _, row in benzerler.iterrows():
        tarih = str(row.get('SEZON', ''))[:11]
        ev = str(row.get('EV SAHİBİ', ''))[:9]
        dep = str(row.get('DEPLASMAN', ''))[:9]
        mac_adi = f"{ev}-{dep}"
        iy_s = str(row.get('İY SKOR', ''))
        ms_s = str(row.get('MS SKOR', ''))
        ht_ft = str(row.get('HT/FT', ''))
        durum = str(row.get('DURUM', ''))

        is_donus = ht_ft in ['1/2', '2/1']
        is_6plus = row['ms_toplam'] >= 6

        if is_6plus:
            ht_ft_disp = f"{ht_ft} 🔥" if is_donus else ht_ft
            durum_disp = f"{durum} 🔥" if "🔥" not in durum else durum
            line_str = f"{tarih:<12} | {mac_adi:<20} | {iy_s:<4} | {ms_s:<4} | {ht_ft_disp:<7} | {durum_disp}"
            lines.append(f"<span style='color:#00E5FF; font-weight:bold;'>{line_str}</span>")
        elif is_donus:
            ht_ft_disp = f"{ht_ft} 🔥"
            line_str = f"{tarih:<12} | {mac_adi:<20} | {iy_s:<4} | {ms_s:<4} | {ht_ft_disp:<7} | {durum}"
            lines.append(f"<span style='color:#FF8C00; font-weight:bold;'>{line_str}</span>")
        else:
            line_str = f"{tarih:<12} | {mac_adi:<20} | {iy_s:<4} | {ms_s:<4} | {ht_ft:<7} | {durum}"
            lines.append(f"<span style='color:#00FF66;'>{line_str}</span>")

    content_html = "<br>".join(lines)

    terminal_box = f"""
    <div style="
        background-color: #000000;
        padding: 15px;
        border-radius: 8px;
        font-family: 'Courier New', Consolas, monospace;
        font-size: 13px;
        line-height: 1.5;
        white-space: pre;
        overflow-x: auto;
        word-break: keep-all;
        word-wrap: normal;
        border: 1px solid #222;
    ">
{content_html}
    </div>
    """
    st.markdown(terminal_box, unsafe_allow_html=True)
