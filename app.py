import streamlit as st
import pandas as pd
import numpy as np
import os
import re

st.set_page_config(page_title="Oran Analiz Pro", page_icon="⚽", layout="centered")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_PATH = os.path.join(BASE_DIR, "cache_data.pkl")

def find_excel_file():
    for f in os.listdir(BASE_DIR):
        if f.lower().endswith(('.xlsb', '.xlsx', '.xls')) and not f.startswith('~$'):
            return os.path.join(BASE_DIR, f)
    return None

@st.cache_data(show_spinner=False)
def load_data():
    if os.path.exists(CACHE_PATH):
        try:
            return pd.read_pickle(CACHE_PATH)
        except Exception:
            pass
    
    excel_path = find_excel_file()
    if excel_path:
        try:
            try:
                df = pd.read_excel(excel_path, engine='pyxlsb', header=1)
            except Exception:
                df = pd.read_excel(excel_path, header=1)

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

def skor_ayir(s):
    try:
        p = str(s).strip().split('-')
        return int(p[0]), int(p[1])
    except:
        return 0, 0

# Esnek Metin Parser (Sadece oran yazılsa bile çalışır)
def metin_parse_et(text):
    maclar = []
    lines = text.strip().split('\n')
    count = 1
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # İçindeki tüm oranları (ondalıklı sayıları) bul
        numbers = re.findall(r'\b\d+[\.,]\d+\b', line)
        if len(numbers) >= 3:
            ms1_str = numbers[-3].replace(',', '.')
            msx_str = numbers[-2].replace(',', '.')
            ms2_str = numbers[-1].replace(',', '.')
            
            # Sayılardan öncesini Maç Adı yap, yoksa Maç 1, Maç 2 at
            match_name_part = line
            for n in numbers[-3:]:
                match_name_part = match_name_part.replace(n, '')
            
            match_name = re.sub(r'[^\w\s\-\.]', '', match_name_part).strip()
            if not match_name:
                match_name = f"Maç {count}"
                count += 1
                
            maclar.append({
                "MAÇ": match_name,
                "MS1": ms1_str,
                "MSX": msx_str,
                "MS2": ms2_str
            })
    return maclar

st.markdown("<h2 style='text-align: center; color: #00FF7F;'>⚽ ORAN ANALİZ VE PATTERN MOTORU</h2>", unsafe_allow_html=True)

df_clean = load_data()
if df_clean is None:
    st.error("❌ Hafıza veri dosyası okunamadı!")
    st.stop()

st.success(f"✅ Hafızada **{len(df_clean):,}** maç aktif!")

tab1, tab2 = st.tabs(["🔍 Tek Maç Analizi", "📱 Otomatik Bülten Taraması"])

with tab1:
    col1, col2, col3 = st.columns(3)
    with col1: ms1_input = st.text_input("MS 1", value="1.83")
    with col2: msx_input = st.text_input("MS X", value="2.99")
    with col3: ms2_input = st.text_input("MS 2", value="2.80")

    if st.button("ANALİZ ET 🚀", use_container_width=True, type="primary"):
        try:
            ms1_v = float(ms1_input.strip().replace(',', '.'))
            msx_v = float(msx_input.strip().replace(',', '.'))
            ms2_v = float(ms2_input.strip().replace(',', '.'))
        except ValueError:
            st.error("Geçerli sayı girin!")
            st.stop()

        df_calc = df_clean.copy()
        df_calc['Mesafe'] = np.sqrt((df_calc['MS1'] - ms1_v)**2 + (df_calc['MSX'] - msx_v)**2 + (df_calc['MS2'] - ms2_v)**2)
        benzerler = df_calc.sort_values('Mesafe').head(15).copy()

        benzerler[['iy_e', 'iy_d']] = benzerler['İY SKOR'].apply(lambda x: pd.Series(skor_ayir(x)))
        benzerler[['ms_e', 'ms_d']] = benzerler['MS SKOR'].apply(lambda x: pd.Series(skor_ayir(x)))
        
        benzerler['iy_toplam'] = benzerler['iy_e'] + benzerler['iy_d']
        benzerler['ms_toplam'] = benzerler['ms_e'] + benzerler['ms_d']
        benzerler['kg_var'] = (benzerler['ms_e'] > 0) & (benzerler['ms_d'] > 0)
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

        st.subheader("🎯 İstatistik Yüzdeleri")
        c1, c2, c3 = st.columns(3)
        c1.metric("İY 0.5+", f"%{iy_05}")
        c2.metric("İY 1.5+", f"%{iy_15}")
        c3.metric("İY KG VAR", f"%{iy_kg}")

        c4, c5, c6 = st.columns(3)
        c4.metric("MS 2.5+", f"%{ms_25}")
        c5.metric("MS 3.5+", f"%{ms_35}")
        c6.metric("6+ GOL 🔥", f"%{ms_6plus}")

        c7, c8 = st.columns(2)
        c7.metric("MS KG VAR", f"%{kg_v}")
        c8.metric("2.Y KG VAR ⚽", f"%{y2_kg}")

with tab2:
    st.markdown("### 📱 Otomatik Bülten Tarayıcı")
    st.info("İster sadece oranları yapıştır, ister maç isimleriyle kopyala!")

    user_paste = st.text_area("Bülten Metnini veya Oranları Yapıştır (Her satıra bir maç):", height=200)

    if st.button("🔥 BÜLTENİ TARA VE POTANSİYELLERİ BUL", type="primary", use_container_width=True):
        if not user_paste.strip():
            st.warning("Lütfen taranacak oranları yapıştırın!")
        else:
            bulten_maclar = metin_parse_et(user_paste)
            
            if not bulten_maclar:
                st.error("Metin içinde oranlar (1.55 3.33 3.86 gibi) tespit edilemedi.")
            else:
                st.success(f"🔍 Toplam **{len(bulten_maclar)}** maç başarıyla algılandı ve taranıyor...")

                tarama_sonuclari = []
                for m in bulten_maclar:
                    try:
                        m_1 = float(m['MS1'])
                        m_x = float(m['MSX'])
                        m_2 = float(m['MS2'])
                    except:
                        continue

                    df_calc = df_clean.copy()
                    df_calc['Mesafe'] = np.sqrt((df_calc['MS1'] - m_1)**2 + (df_calc['MSX'] - m_x)**2 + (df_calc['MS2'] - m_2)**2)
                    benzerler = df_calc.sort_values('Mesafe').head(15).copy()

                    benzerler[['iy_e', 'iy_d']] = benzerler['İY SKOR'].apply(lambda x: pd.Series(skor_ayir(x)))
                    benzerler[['ms_e', 'ms_d']] = benzerler['MS SKOR'].apply(lambda x: pd.Series(skor_ayir(x)))

                    iy_toplam = benzerler['iy_e'] + benzerler['iy_d']
                    ms_toplam = benzerler['ms_e'] + benzerler['ms_d']
                    y2_e = benzerler['ms_e'] - benzerler['iy_e']
                    y2_d = benzerler['ms_d'] - benzerler['iy_d']

                    iy_kg = round(((benzerler['iy_e'] > 0) & (benzerler['iy_d'] > 0)).mean() * 100)
                    y2_kg = round(((y2_e > 0) & (y2_d > 0)).mean() * 100)
                    ms_kg = round(((benzerler['ms_e'] > 0) & (benzerler['ms_d'] > 0)).mean() * 100)
                    ms_35 = round((ms_toplam >= 4).mean() * 100)

                    puan = iy_kg + y2_kg + ms_35

                    tarama_sonuclari.append({
                        "MAÇ": m['MAÇ'],
                        "ORANLAR (1-X-2)": f"{m_1} - {m_x} - {m_2}",
                        "İY KG %": f"%{iy_kg}",
                        "2.Y KG %": f"%{y2_kg}",
                        "MS 3.5+ %": f"%{ms_35}",
                        "MS KG %": f"%{ms_kg}",
                        "POTANSİYEL PUANI": puan
                    })

                res_df = pd.DataFrame(tarama_sonuclari)

                if not res_df.empty:
                    res_df = res_df.sort_values(by="POTANSİYEL PUANI", ascending=False)
                    st.subheader("🚀 İki Yarıda da KG / Gol Patlaması Potansiyeli En Yüksek Maçlar")
                    st.dataframe(res_df, use_container_width=True)
