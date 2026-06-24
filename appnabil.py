import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import rasterio
from rasterio.enums import Resampling
import io
import base64
import os

def parse_mtl(mtl_content):
    """
    Parses Landsat MTL metadata file and returns a dictionary of keys and values.
    """
    params = {}
    for line in mtl_content.splitlines():
        if "=" in line:
            parts = line.split("=")
            key = parts[0].strip()
            val = parts[1].strip()
            try:
                if val.startswith('"') and val.endswith('"'):
                    val = val[1:-1]
                else:
                    val = float(val)
            except ValueError:
                pass
            params[key] = val
    return params

def extract_calibration_constants(mtl_params, satelit, band_num=10):
    """
    Extracts RADIANCE_MULT, RADIANCE_ADD, K1, K2 for the given band from MTL parameters.
    """
    m_l, a_l, k1, k2 = None, None, None, None
    for key, val in mtl_params.items():
        if key.startswith(f"RADIANCE_MULT_BAND_{band_num}"):
            m_l = val
        elif key.startswith(f"RADIANCE_ADD_BAND_{band_num}"):
            a_l = val
        elif key.startswith(f"K1_CONSTANT_BAND_{band_num}"):
            k1 = val
        elif key.startswith(f"K2_CONSTANT_BAND_{band_num}"):
            k2 = val
                
    return m_l, a_l, k1, k2

# --- PENGATURAN HALAMAN (MANDATORY) ---
st.set_page_config(
    page_title="GeoHeat",
    page_icon="🌋",
    layout="wide"
)

# =========================
# HEADER GEOHEAT
# =========================

st.markdown("""
<style>
.main {
    background-color: #f4f6f8;
}

/* Responsif ukuran font untuk mobile */
.geoheat-title {
    font-size: clamp(34px, 7vw, 60px);
    font-weight: 800;
    margin-bottom: 8px;
    line-height: 1.1;
}

.geo-blue {
    color: #0D47A1;
}

.heat-orange {
    color: #F57C00;
}

/* Memperbaiki tinggi baris agar tidak menumpuk saat teks wrap di HP */
.subtitle {
    color: #334155 !important;
    font-size: clamp(12px, 3.5vw, 20px);
    font-weight: 600;
    line-height: 1.4;
    letter-spacing: 0.03em;
}
</style>
""", unsafe_allow_html=True)

col1, col2 = st.columns([1,4])

with col1:
    st.image(
        "logo_geoheat.png",
        width=160
    )

with col2:
    st.markdown("""
    <div>
    <div class="geoheat-title">
        <span class="geo-blue">Geo</span><span class="heat-orange">Heat</span>
    </div>
    <div class="subtitle">
        LAND SURFACE TEMPERATURE MAPPING PLATFORM
    </div>
    </div>
    """, unsafe_allow_html=True)

# --- ENKODE GAMBAR LATAR BELAKANG KE BASE64 ---
bg_img_base64 = ""
bg_img_path = os.path.join(os.path.dirname(__file__), "background.jpg")
if os.path.exists(bg_img_path):
    with open(bg_img_path, "rb") as image_file:
        bg_img_base64 = base64.b64encode(image_file.read()).decode("utf-8")

# --- CSS CUSTOM UNTUK TAMPILAN SUPER PREMIUM ---
st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');
    
    html, body, [data-testid="stAppViewContainer"] {{
        font-family: 'Plus Jakarta Sans', sans-serif;
        background-image: linear-gradient(to right, rgba(255, 255, 255, 1) 0%, rgba(255, 255, 255, 0.96) 40%, rgba(255, 255, 255, 0.2) 80%, rgba(255, 255, 255, 0) 100%), url("data:image/jpeg;base64,{bg_img_base64}");
        background-size: cover;
        background-position: right center;
        background-attachment: fixed;
    }}
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {{
        background: #ffffff !important;
        border-right: 1px solid #e2e8f0 !important;
    }}
    
    /* Desain Kartu Glassmorphism dengan proteksi warna teks gelap */
    div[data-testid="stVerticalBlockBorder"] {{
        background: rgba(255, 255, 255, 0.96) !important;
        backdrop-filter: blur(12px) !important;
        -webkit-backdrop-filter: blur(12px) !important;
        padding: clamp(1rem, 3vw, 2.2rem) !important;
        border-radius: 20px !important;
        border: 1px solid rgba(226, 232, 240, 0.9) !important;
        box-shadow: 0 10px 30px -10px rgba(15, 23, 42, 0.1) !important;
        margin-bottom: 1.5rem !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }}
    
    /* Memaksa semua teks di dalam kontainer putih agar berwarna gelap (Fix tulisan hilang) */
    div[data-testid="stVerticalBlockBorder"] *, 
    div[data-testid="stVerticalBlockBorder"] p, 
    div[data-testid="stVerticalBlockBorder"] div,
    div[data-testid="stVerticalBlockBorder"] li {{
        color: #1e293b !important;
    }}
    
    div[data-testid="stVerticalBlockBorder"]:hover {{
        background: #ffffff !important;
        box-shadow: 0 20px 40px -15px rgba(15, 23, 42, 0.15) !important;
        border: 1px solid rgba(226, 232, 240, 1) !important;
        transform: translateY(-2px);
    }}
    
    /* Judul Bagian di dalam Kartu */
    .card-title {{
        color: #0f172a !important;
        font-size: 1.35rem !important;
        font-weight: 800 !important;
        margin-bottom: 1.2rem !important;
        border-left: 5px solid #3b82f6 !important;
        padding-left: 12px !important;
        letter-spacing: -0.02em !important;
    }}
    
    /* Kartu Statistik Berwarna (Metrik Kustom) - Tetap Putih */
    .metric-grid {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 1rem;
        margin-bottom: 2rem;
    }}
    .metric-box {{
        padding: 1.5rem;
        border-radius: 14px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }}
    .metric-box * {{
        color: #ffffff !important;
    }}
    .metric-box:hover {{
        transform: translateY(-4px);
        box-shadow: 0 8px 25px rgba(0,0,0,0.18);
    }}
    .m-blue {{ background: linear-gradient(135deg, #1e40af, #3b82f6); }}
    .m-red {{ background: linear-gradient(135deg, #b91c1c, #ef4444); }}
    .m-teal {{ background: linear-gradient(135deg, #0f766e, #14b8a6); }}
    .m-purple {{ background: linear-gradient(135deg, #6d28d9, #8b5cf6); }}
    
    .metric-label {{ font-size: 0.85rem; font-weight: 600; opacity: 0.9; text-transform: uppercase; letter-spacing: 0.05em;}}
    .metric-val {{ font-size: 1.9rem; font-weight: 800; margin-top: 0.25rem; }}
    
    /* Tabel Teori */
    .teori-table {{
        width: 100%; border-collapse: collapse; margin-top: 1rem;
        background: rgba(255, 255, 255, 0.4);
        border-radius: 12px;
        overflow: hidden;
    }}
    .teori-table th {{
        background-color: #1e3a8a; color: white !important; text-align: left; padding: 14px; font-weight: 700;
    }}
    .teori-table td {{
        padding: 14px; border-bottom: 1px solid rgba(226, 232, 240, 0.6); font-size: 0.95rem; color: #1e293b !important;
    }}
    </style>
""", unsafe_allow_html=True)

# --- SIDEBAR NAVIGASI (MULTI-HALAMAN) ---
with st.sidebar:
    st.markdown("### MENU NAVIGASI")
    menu = st.radio( "Pilih Menu : ",
        ["Beranda (Home)", "Tentang Aplikasi (About)"]
    )

# ==============================================================================
# MENU 1: DASHBOARD UTAMA
# ==============================================================================
if menu == "Beranda (Home)":
    
    # Initialize session state for keeping results
    if 'lst_results' not in st.session_state:
        st.session_state.lst_results = None

    # Kartu Input Data
    with st.container(border=True):
        st.markdown('<div class="card-title">Unggah Data Landsat</div>', unsafe_allow_html=True)
        
        satelit = st.selectbox("Pilih Jenis Satelit :", ["Landsat 8", "Landsat 9"])
        data_level = st.selectbox("Pilih Level Data :", ["Landsat Collection 2 Level-1", "Landsat Collection 2 Level-2"])
        
        col1, col2 = st.columns(2)
        with col1:
            if data_level == "Landsat Collection 2 Level-1":
                mtl_file = st.file_uploader("Unggah Berkas Metadata Landsat (MTL.txt)", type=["txt"])
            else:
                mtl_file = None

            if data_level == "Landsat Collection 2 Level-1":
                b10_file = st.file_uploader("Unggah Band 10 (Thermal)", type=["tif", "tiff"])
            else:
                b10_file = st.file_uploader("Unggah ST_B10 (Surface Temperature)", type=["tif", "tiff"])
        with col2:
            b4_file = st.file_uploader("Unggah Band 4 (Red)", type=["tif", "tiff"])
            b5_file = st.file_uploader("Unggah Band 5 (NIR)", type=["tif", "tiff"])
            
    
    # Tombol Eksekusi Panjang Penuh (Full Width)
    if st.button("GENERATE DATA SPASIAL LST", type="primary", use_container_width=True):
        if b10_file is not None:
            with st.spinner("Sedang memproses algoritma downsampling spasial dan hukum fisika LST..."):
                try:
                    # Membaca Berkas dengan Rasterio Downsampling Aman RAM
                    with rasterio.open(b10_file) as src_meta:
                        meta_asli = src_meta.meta.copy()
                        t_height = int(src_meta.height / 15)
                        t_width = int(src_meta.width / 15)
                        
                        b10 = src_meta.read(
                            1, out_shape=(t_height, t_width), resampling=Resampling.bilinear
                        ).astype('float64')
                        
                        new_transform = src_meta.transform * src_meta.transform.scale(
                            (src_meta.width / t_width),
                            (src_meta.height / t_height)
                        )
                        crs_asli = src_meta.crs
                    
                    # Logika Pemilihan Konstanta Kalibrasi Satelit
                    M_L, A_L, K1, K2 = None, None, None, None
                    used_mtl = False
                    
                    if mtl_file is not None:
                        try:
                            mtl_content = mtl_file.getvalue().decode("utf-8")
                            mtl_params = parse_mtl(mtl_content)
                            
                            band_num = 10
                            m_l_parse, a_l_parse, k1_parse, k2_parse = extract_calibration_constants(mtl_params, satelit, band_num)
                            
                            if None not in (m_l_parse, a_l_parse, k1_parse, k2_parse):
                                M_L, A_L, K1, K2 = m_l_parse, a_l_parse, k1_parse, k2_parse
                                used_mtl = True
                            else:
                                st.warning("⚠️ Beberapa parameter kalibrasi tidak ditemukan dalam berkas MTL. Menggunakan nilai default.")
                        except Exception as parse_err:
                            st.warning(f"⚠️ Gagal membaca berkas MTL ({parse_err}). Menggunakan nilai default.")

                    if not used_mtl:
                        M_L = 0.0003342
                        A_L = 0.1
                        K1 = 774.89
                        K2 = 1321.07
                    
                    # Hitung Radiance & Brightness Temperature
                    if data_level == "Landsat Collection 2 Level-1":
                        st.info("Metode: DN → Radiance → Brightness Temperature → NDVI → LSE → LST")
                        radiance = (M_L * b10) + A_L
                        radiance[radiance <= 0] = 0.001
                        kelvin = (K2 / np.log((K1 / radiance) + 1))
                    else:
                        st.info("Metode: ST_B10 → NDVI → LSE → LST")
                        surface_temp_kelvin = ((b10 * 0.00341802)+ 149.0)
                        kelvin = surface_temp_kelvin
                    
                    # Hitung Koreksi Emisivitas Menggunakan NDVI
                    if b4_file is not None and b5_file is not None:
                        with rasterio.open(b4_file) as src4:
                            b4 = src4.read(1, out_shape=(t_height, t_width), resampling=Resampling.bilinear).astype('float64')
                        with rasterio.open(b5_file) as src5:
                            b5 = src5.read(1, out_shape=(t_height, t_width), resampling=Resampling.bilinear).astype('float64')
                        
                        ndvi = (b5 - b4) / (b5 + b4 + 1e-10)
                        ndvi_min, ndvi_max = np.nanmin(ndvi), np.nanmax(ndvi)
                        
                        Pv = ((ndvi - ndvi_min) / (ndvi_max - ndvi_min + 1e-10)) ** 2
                        emissivity = 0.004 * Pv + 0.986
                        
                        lst_celcius = (kelvin / (1 + (10.8 * kelvin / 14388) * np.log(emissivity))) - 273.15
                        
                        metode_text_base = "Metode Split-Window dengan Koreksi Emisivitas Permukaan Bumi (NDVI Sobrino 2004)"
                    else:
                        lst_celcius = kelvin - 273.15
                        metode_text_base = "Metode At-Sensor Brightness Temperature Standar (Asumsi Blackbody)"
                    
                    if data_level == "Landsat Collection 2 Level-1":
                        if used_mtl:
                            calibration_detail = (
                                f"Kalibrasi Dinamis dari MTL "
                                f"(M_L={M_L:.7f}, A_L={A_L:.5f}, "
                                f"K1={K1:.2f}, K2={K2:.2f})"
                            )
                        else:
                            calibration_detail = (
                                f"Kalibrasi Default "
                                f"(M_L={M_L:.7f}, A_L={A_L:.5f}, "
                                f"K1={K1:.2f}, K2={K2:.2f})"
                            )
                    else:
                        calibration_detail = (
                            "Surface Temperature (ST_B10) "
                            "Collection 2 Level-2"
                        )
                        
                    metode_text = f"{metode_text_base}. {calibration_detail}"

                    # Data Cleaning Piksel Liar / Gangguan Awan
                    lst_celcius[lst_celcius < -5] = np.nan
                    lst_celcius[lst_celcius > 55] = np.nan
                    
                    # Nilai Statistik deskriptif
                    s_min, s_max = np.nanmin(lst_celcius), np.nanmax(lst_celcius)
                    s_mean, s_med = np.nanmean(lst_celcius), np.nanmedian(lst_celcius)

                    # Generate GeoTIFF bytes in-memory
                    out_meta = {
                        'driver': 'GTiff',
                        'dtype': 'float32',
                        'nodata': np.nan,
                        'width': t_width,
                        'height': t_height,
                        'count': 1,
                        'crs': crs_asli,
                        'transform': new_transform
                    }
                    
                    with rasterio.io.MemoryFile() as memfile:
                        with memfile.open(**out_meta) as dst:
                            dst.write(lst_celcius.astype('float32'), 1)
                        tif_bytes = memfile.read()
                    
                    # Save results to session state
                    st.session_state.lst_results = {
                        'lst_celcius': lst_celcius,
                        'metode_text': metode_text,
                        's_min': s_min,
                        's_max': s_max,
                        's_mean': s_mean,
                        's_med': s_med,
                        'tif_bytes': tif_bytes
                    }
                    
                except Exception as e:
                    st.error(f"Terjadi kesalahan teknis pemrosesan data: {e}")
        else:
            st.warning("⚠️ Mohon unggah berkas thermal Band 10 terlebih dahulu ⚠️")

    # Render results if available in session state
    if st.session_state.lst_results is not None:
        res = st.session_state.lst_results
        
        # TAMPILKAN METRIK KUSTOM BERWARNA (HTML/CSS)
        st.success(f"Proses Berhasil! Digunakan: {res['metode_text']}")
        st.caption(f"Level Data: {data_level}")
        
        st.markdown(f"""
            <div class="metric-grid">
                <div class="metric-box m-blue">
                    <div class="metric-label">Suhu Terendah</div>
                    <div class="metric-val">{res['s_min']:.1f} °C</div>
                </div>
                <div class="metric-box m-red">
                    <div class="metric-label">Suhu Tertinggi</div>
                    <div class="metric-val">{res['s_max']:.1f} °C</div>
                </div>
                <div class="metric-box m-teal">
                    <div class="metric-label">Rata-rata Spasial</div>
                    <div class="metric-val">{res['s_mean']:.1f} °C</div>
                </div>
                <div class="metric-box m-purple">
                    <div class="metric-label">Nilai Tengah (Median)</div>
                    <div class="metric-val">{res['s_med']:.1f} °C</div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # Peta dan Histogram dalam Kartu Putih
        with st.container(border=True):
            dl_col1, dl_col2 = st.columns([3, 1])
            with dl_col1:
                st.markdown('<div class="card-title" style="margin-bottom: 0px;">Peta &amp; Hasil Analisis Spasial LST</div>', unsafe_allow_html=True)
            with dl_col2:
                st.download_button(
                    label="Download Peta LST (.TIF)",
                    data=res['tif_bytes'],
                    file_name="Peta_LST.tif",
                    mime="image/tiff",
                    use_container_width=True
                )
                
            st.markdown('<div style="height: 20px;"></div>', unsafe_allow_html=True)
            
            g_col1, g_col2 = st.columns(2)
            
            with g_col1:
                st.markdown('<div class="card-title">Peta Zonasi Suhu Permukaan Bumi (LST)</div>', unsafe_allow_html=True)
                fig_map, ax_map = plt.subplots(figsize=(6, 4.5))
                fig_map.patch.set_facecolor('#ffffff')
                im = ax_map.imshow(res['lst_celcius'], cmap='jet')
                fig_map.colorbar(im, ax=ax_map, label='Suhu (°C)')
                ax_map.axis('off')
                st.pyplot(fig_map)
                
            with g_col2:
                st.markdown('<div class="card-title">Grafik Distribusi Frekuensi Suhu</div>', unsafe_allow_html=True)
                fig_hist, ax_hist = plt.subplots(figsize=(6, 4.5))
                fig_hist.patch.set_facecolor('#ffffff')
                ax_hist.hist(res['lst_celcius'][~np.isnan(res['lst_celcius'])].flatten(), bins=30, color='#3b82f6', edgecolor='white')
                ax_hist.set_xlabel('Suhu Permukaan (°C)')
                ax_hist.set_ylabel('Jumlah Piksel')
                ax_hist.grid(axis='y', linestyle='--', alpha=0.7)
                st.pyplot(fig_hist)


# ==============================================================================
# MENU 2: TEORI PERHITUNGAN LST
# ==============================================================================
elif menu == "Tentang Aplikasi (About)":

    with st.container(border=True):
        st.markdown(
            '<div class="card-title">GeoHeat</div>',
            unsafe_allow_html=True
        )
        st.markdown(
            """
            <div style='text-align: justify;'>
            GeoHeat merupakan aplikasi berbasis web yang dikembangkan untuk menghasilkan peta
            <b>Land Surface Temperature (LST)</b> dari citra satelit Landsat 8 atau Landsat 9.
            Aplikasi ini dirancang untuk membantu proses identifikasi awal area yang berpotensi
            memiliki aktivitas panas bumi melalui analisis distribusi temperatur permukaan.
            </div>
            """,
            unsafe_allow_html=True
        )

    with st.container(border=True):
        st.markdown(
            '<div class="card-title">Tujuan Aplikasi</div>',
            unsafe_allow_html=True
        )
        st.markdown(
            """
            <div style='text-align: justify;'>
            Menyediakan platform yang mudah digunakan untuk menghitung dan memvisualisasikan temperatur permukaan dari data penginderaan jauh tanpa memerlukan perangkat lunak GIS yang kompleks.
            </div>
            """,
            unsafe_allow_html=True
        )

    with st.container(border=True):
        st.markdown(
            '<div class="card-title">Data Input</div>',
            unsafe_allow_html=True
        )
        st.markdown(
            """
            <div style='text-align: justify;'>
            - <b>Band 10 (Thermal Infrared)</b> : Untuk memperoleh informasi suhu permukaan melalui perhitungan Brightness Temperature.<br>
            - <b>Band 4 (Red) dan Band 5 (NIR)</b> : Untuk menghitung NDVI yang digunakan dalam estimasi emisivitas permukaan (LSE).<br>
            - <b>Metadata Landsat (MTL)</b> : Untuk mengambil nilai ML, AL, K1, dan K2. 
            </div>
            """,
            unsafe_allow_html=True
        )

    with st.container(border=True):
        st.markdown(
            '<div class="card-title">Data yang Didukung</div>',
            unsafe_allow_html=True
        )
        st.markdown(
            """
            <div style='text-align: justify;'>
            - Landsat 8 OLI/TIRS<br>
            - Landsat 9 OLI/TIRS
            </div>
            """,
            unsafe_allow_html=True
        )

    with st.container(border=True):
        st.markdown(
            '<div class="card-title">Perhitungan</div>',
            unsafe_allow_html=True
        )
        st.markdown("""
            <table class="teori-table">
                <tr><th>Tahapan</th><th>Persamaan</th></tr>
                <tr><td>1. Top of Atmosphere Radiance</td><td>Lλ = ML * Qcal + AL</td></tr>
                <tr><td>2. Brightness Temperature (Kelvin)</td><td>BT = K2 / ln((K1 / Lλ) + 1)</td></tr>
                <tr><td>3. Normalized Difference Vegetation Index</td><td>NDVI = (NIR − Red) / (NIR + Red)</td></tr>
                <tr><td>4. Proporsi Vegetasi</td><td>PV = ((NDVI − NDVImin) / (NDVImax − NDVImin))²</td></tr>    
                <tr><td>5. Land Surface Emissivity</td><td>LSE = (0.004 × PV) + 0.986</td></tr>
                <tr><td>6. Land Surface Temperature</td><td>LST = BT / (1 + (λ * BT / ρ) * ln(ε))</td></tr>
            </table>
        """, unsafe_allow_html=True)

        st.markdown(
            """
            <div style='text-align: justify; margin-top: 15px;'>
            <b>Keterangan :</b><br>
            - <b>Lλ</b> = Spectral Radiance (W/m²·sr·μm)<br>
            - <b>ML</b> = Radiance Multiplicative Scaling Factor<br>
            - <b>AL</b> = Radiance Additive Scaling Factor<br>
            - <b>Qcal</b> = Nilai Digital Number (DN)<br><br>
            - <b>BT</b> = Brightness Temperature (Kelvin)<br>
            - <b>K1 / K2</b> = Konstanta Kalibrasi Termal Landsat<br><br>
            - <b>LST</b> = Land Surface Temperature (°C)<br>
            - <b>W</b> = Panjang gelombang efektif Band 10 Landsat (10.895 μm)<br>
            - <b>ε (LSE)</b> = Land Surface Emissivity
            </div>
            """,
            unsafe_allow_html=True
        )

    with st.container(border=True):
        st.markdown(
            '<div class="card-title">Luaran</div>',
            unsafe_allow_html=True
        )
        st.markdown(
            """
            <div style='text-align: justify;'>
            - Peta Land Surface Temperature (LST)<br>
            - Statistik temperatur permukaan (minimum, maksimum, rata-rata, dan median)<br>
            - Visualisasi distribusi temperatur<br>
            - File GeoTIFF yang dapat digunakan pada QGIS dan ArcGIS
            </div>
            """,
            unsafe_allow_html=True
        )

    with st.container(border=True):
        st.markdown(
            '<div class="card-title">Manfaat</div>',
            unsafe_allow_html=True
        )
        st.markdown(
            """
            <div style='text-align: justify;'>
            GeoHeat dapat digunakan sebagai alat bantu pembelajaran geologi, penginderaan jauh, dan eksplorasi panas bumi untuk mendukung identifikasi awal zona anomali temperatur permukaan secara cepat dan efisien.
            </div>
            """,
            unsafe_allow_html=True
)
