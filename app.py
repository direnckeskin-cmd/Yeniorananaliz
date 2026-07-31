import streamlit as st
import pandas as pd
import numpy as np
import os
import io

# Sayfa Ayarları
st.set_page_config(page_title="Oran Analiz Pro", page_icon="⚽", layout="centered")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_PATH = os.path.join(BASE_DIR, "cache_data.pkl")

# Klasördeki Hafıza Dosyasını Bul
def find_excel_file():
    for f in os.listdir(BASE_DIR):
        if f.lower().endswith(('.xlsb', '.xlsx', '.xls')) and not f.startswith('~$'):
            return os.path.join(BASE_DIR, f)
    return None

# Streamlit Önbellekleme
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

# Skor ayırma fonksiyonu
def skor_ayir(s):
    try:
        p = str(s).strip().split('-')
        return int(p[0]), int(p[1])
    except:
        return 0, 0

# Başlık
st.markdown("<h2 style='text-align: center; color: #00FF7F;'>⚽ ORAN ANALİZ VE PATTERN MOTORU</h2>", unsafe_allow_html=True)

df_clean = load_data()

if df_clean is None:
    st.error("❌ Hafıza veri dosyası okunamadı!")
    st.stop()

st.success(f"✅ Hafızada **{len(df_clean):,}** maç aktif!")

# Sekmeler (Tablar)
tab1, tab2 = st.tabs(["🔍 Tek Maç Analizi", "📱 Otomatik Bülten Taraması"])

# ==================== SEKME 1: TEK MAÇ ANALİZİ ====================
with tab1:
    col1, col2, col3 = st.columns(3)
    with col1:
        ms1_input = st.text_input("MS 1", value="1.58")
    with col2:
        msx_input = st.text_input("MS X", value="3.70")
    with col3:
        ms2_input = st.text_input("MS 2", value="3.31")

    btn_analiz = st.button("ANALİZ ET 🚀", use_container_width=True, type="primary")

    if btn_analiz:
        try:
            ms1_v = float(ms1_input.strip().replace(',', '.'))
            msx_v = float(msx_input.strip().replace(',', '.'))
            ms2_v = float(ms2_input.strip().replace(',', '.'))
        except ValueError:
            st.error("Geçerli sayı girin!")
            st.stop()

        df_calc = df_clean.copy()
        df_calc['Mesafe'] = np.sqrt(
            (df_calc['MS1'] - ms1_v)**2 + 
            (df_calc['MSX'] - msx_v)**2 + 
            (df_calc['MS2'] - ms2_v)**2
        )
        benzerler = df_calc.sort_values('Mesafe').head(15).copy()

        benzerler[['iy_e', 'iy_d']] = benzerler['İY SKOR'].apply(lambda x: pd.Series(skor_ayir(x)))
        benzerler[['ms_e', 'ms_d']] = benzerler['MS SKOR'].apply(lambda x: pd.Series(skor_ayir(x)))
        
        benzerler['iy_toplam'] = benzerler['iy_e'] + benzerler['iy_d']
        benzerler['ms_toplam'] = benzerler['ms_e'] + benzerler['ms_d']
        benzerler['kg_var'] = (benzerler['ms_e'] > 0) & (benzerler['ms_d'] > 0)
        benzerler['2y_e'] = benzerler['ms_e'] - benzerler['iy_e']
        benzerler['2y_d'] = benzerler['ms_d'] - benzerler['iy_d']

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

        st.markdown("---")
        st.subheader("📋 Benzer Maçlar")
        lines = []
        lines.append(f"<span style='color:#00FF66;'>{'SEZON/LİG':<12} | {'MAÇ':<20} | {'İY':<4} | {'MS':<4} | {'HT/FT':<7} | {'DURUM'}</span>")
        lines.append(f"<span style='color:#00FF66;'>{'-'*67}</span>")

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
                line_str = f"{tarih:<12} | {mac_adi:<20} | {iy_s:<4} | {ms_s:<4} | {ht_ft:<7} | {durum} 🔥"
                lines.append(f"<span style='color:#00E5FF; font-weight:bold;'>{line_str}</span>")
            elif is_donus:
                line_str = f"{tarih:<12} | {mac_adi:<20} | {iy_s:<4} | {ms_s:<4} | {ht_ft} 🔥 | {durum}"
                lines.append(f"<span style='color:#FF8C00; font-weight:bold;'>{line_str}</span>")
            else:
                line_str = f"{tarih:<12} | {mac_adi:<20} | {iy_s:<4} | {ms_s:<4} | {ht_ft:<7} | {durum}"
                lines.append(f"<span style='color:#00FF66;'>{line_str}</span>")

        st.markdown(f"<div style='background-color:#000; padding:15px; border-radius:8px; font-family:monospace; font-size:12px; white-space:pre; overflow-x:auto;'>{'<br>'.join(lines)}</div>", unsafe_allow_html=True)

# ==================== SEKME 2: OTOMATİK BÜLTEN TARAMA ====================
with tab2:
    st.markdown("### 📱 Telefon Uyumlu Bülten Tarayıcı")
    st.info("İster Excel yükle, ister maçları ve oranları metin olarak yapıştır!")

    input_mode = st.radio("Veri Giriş Yöntemi Seç:", ["📝 Metin Olarak Yapıştır (Çok Hızlı)", "📁 Excel / CSV Dosyası Yükle"])

    bulten_maclar = []

    if input_mode == "📝 Metin Olarak Yapıştır (Çok Hızlı)":
        example_text = "Girona-Castellon 1.83 2.99 2.80\nSantos-UCV 1.58 3.70 3.31"
        user_paste = st.text_area("Maçları ve oranları yapıştır (Her satıra bir maç):", value=example_text, height=150)
        
        if user_paste:
            for line in user_paste.strip().split('\n'):
                parts = line.strip().split()
                if len(parts) >= 4:
                    # Son 3 değer oranlar, önceki kısım maç adı
                    try:
                        ms2_val = parts[-1]
                        msx_val = parts[-2]
                        ms1_val = parts[-3]
                        m_name = " ".join(parts[:-3])
                        bulten_maclar.append({"MAÇ": m_name, "MS1": ms1_val, "MSX": msx_val, "MS2": ms2_val})
                    except:
                        continue

    else:
        uploaded_file = st.file_uploader("Telefondan Bülten Excel/CSV Seç", type=['xlsx', 'xls', 'csv'])
        if uploaded_file is not None:
            try:
                if uploaded_file.name.endswith('.csv'):
                    b_df = pd.read_csv(uploaded_file)
                else:
                    b_df = pd.read_excel(uploaded_file)
                
                # Standart kolon isimlerini yakala
                for _, r in b_df.iterrows():
                    bulten_maclar.append({
                        "MAÇ": r.get('MAÇ', r.get('Mac', 'Maç')),
                        "MS1": r.get('MS1', r.get('1', 0)),
                        "MSX": r.get('MSX', r.get('X', 0)),
                        "MS2": r.get('MS2', r.get('2', 0))
                    })
            except Exception as e:
                st.error(f"Dosya okuma hatası: {e}")

    btn_tara = st.button("🔥 BÜLTENİ TARA VE POTANSİYELLERİ BUL", type="primary", use_container_width=True)

    if btn_tara:
        if not bulten_maclar:
            st.warning("Lütfen taranacak maç veya dosya ekleyin!")
        else:
            tarama_sonuclari = []

            for m in bulten_maclar:
                try:
                    m_1 = float(str(m['MS1']).replace(',', '.'))
                    m_x = float(str(m['MSX']).replace(',', '.'))
                    m_2 = float(str(m['MS2']).replace(',', '.'))
                except:
                    continue

                df_calc = df_clean.copy()
                df_calc['Mesafe'] = np.sqrt(
                    (df_calc['MS1'] - m_1)**2 + 
                    (df_calc['MSX'] - m_x)**2 + 
                    (df_calc['MS2'] - m_2)**2
                )
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

                # İki Yarı KG Potansiyel Puanı
                puan = iy_kg + y2_kg + ms_35

                tarama_sonuclari.append({
                    "MAÇ": m['MAÇ'],
                    "ORANLAR": f"{m_1} - {m_x} - {m_2}",
                    "İY KG %": f"%{iy_kg}",
                    "2.Y KG %": f"%{y2_kg}",
                    "MS 3.5+ %": f"%{ms_35}",
                    "MS KG %": f"%{ms_kg}",
                    "POTANSİYEL PUANI": puan
                })

            res_df = pd.DataFrame(tarama_sonuclari)

            if not res_df.empty:
                res_df = res_df.sort_values(by="POTANSİYEL PUANI", ascending=False)
                st.subheader("🚀 İki Yarıda da KG Patlama Potansiyeli Yüksek Maçlar")
                st.dataframe(res_df, use_container_width=True)
            else:
                st.info("Uygun maç bulunamadı.")
