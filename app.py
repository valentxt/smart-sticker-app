from flask import Flask, render_template_string, request, jsonify
from PIL import Image, ImageStat
import io
import base64
import colorsys
from datetime import datetime

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="id">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Smart Sticker Inspector</title>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
  <style>
    :root {
      --bg-color: #f4f7f6;
      --card-bg: #ffffff;
      --text-color: #212529;
      --border-color: #dee2e6;
      --subtext-color: #6c757d;
    }

    body.dark-mode {
      --bg-color: #121212;
      --card-bg: #1e1e1e;
      --text-color: #e0e0e0;
      --border-color: #333333;
      --subtext-color: #a0a0a0;
    }

    body {
      font-family: system-ui, -apple-system, sans-serif;
      max-width: 500px;
      margin: 15px auto;
      padding: 10px;
      background-color: var(--bg-color);
      color: var(--text-color);
      transition: background-color 0.3s, color 0.3s;
    }

    .card {
      background-color: var(--card-bg);
      padding: 20px;
      border-radius: 14px;
      box-shadow: 0 4px 16px rgba(0,0,0,0.1);
      position: relative;
      margin-bottom: 15px;
    }

    .top-bar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 12px;
    }

    .app-title {
      font-size: 1.25em;
      font-weight: bold;
      margin: 0;
    }

    .theme-toggle {
      background: none;
      border: 1px solid var(--border-color);
      color: var(--text-color);
      padding: 5px 10px;
      border-radius: 16px;
      cursor: pointer;
      font-size: 0.8em;
      font-weight: 600;
    }

    label {
      font-weight: 600;
      display: block;
      text-align: left;
      margin-top: 10px;
      font-size: 0.85em;
      color: var(--text-color);
    }

    select, input[type="file"] {
      width: 100%;
      padding: 9px 12px;
      margin: 5px 0 10px 0;
      border: 1px solid var(--border-color);
      border-radius: 8px;
      box-sizing: border-box;
      font-size: 0.9em;
      background-color: var(--card-bg);
      color: var(--text-color);
    }

    img#imagePreview {
      max-width: 100%;
      max-height: 250px;
      object-fit: contain;
      border-radius: 8px;
      margin-top: 12px;
      display: none;
      border: 1px solid var(--border-color);
    }

    #reportArea {
      display: none;
      margin-top: 18px;
      padding: 16px;
      border-radius: 10px;
      text-align: left;
      line-height: 1.6;
      border: 1px dashed var(--border-color);
      background-color: var(--card-bg);
    }

    .warning-box {
      margin-top: 12px;
      padding: 10px 12px;
      background-color: #f8d7da;
      color: #721c24;
      border: 1px solid #f5c6cb;
      border-radius: 6px;
      font-size: 0.83em;
    }

    .loading {
      color: #0d6efd;
      font-weight: bold;
      display: none;
      margin-top: 15px;
      font-size: 0.9em;
    }

    .btn-group {
      display: flex;
      gap: 10px;
      margin-top: 15px;
    }

    .btn {
      flex: 1;
      padding: 10px;
      border: none;
      border-radius: 8px;
      cursor: pointer;
      font-weight: bold;
      display: none;
      font-size: 0.88em;
      transition: opacity 0.2s;
    }

    .btn:hover { opacity: 0.9; }
    .btn-reset { background-color: #6c757d; color: white; }
    .btn-export { background-color: #198754; color: white; }

    /* Style Khusus Kartu Kontak Pemilik */
    .contact-card {
      text-align: center;
      padding: 15px;
      font-size: 0.85em;
      line-height: 1.5;
    }
    
    .contact-email {
      display: inline-block;
      margin-top: 6px;
      padding: 6px 12px;
      background-color: rgba(13, 110, 253, 0.1);
      color: #0d6efd;
      border-radius: 20px;
      font-weight: bold;
      text-decoration: none;
      word-break: break-all;
    }

    body.dark-mode .contact-email {
      background-color: rgba(13, 110, 253, 0.25);
      color: #6ea8fe;
    }
  </style>
</head>
<body>

<div class="card" id="mainCard">
  <div class="top-bar">
    <h1 class="app-title">Smart Sticker Inspector</h1>
    <button class="theme-toggle" onclick="toggleTheme()" id="themeBtn">🌙 Gelap</button>
  </div>
  <p style="font-size: 0.82em; color: var(--subtext-color); margin: 0 0 10px 0; text-align: left;">
    Analisis indikator warna kesegaran bahan pangan secara presisi
  </p>

  <label for="productType">Pilih Jenis Produk:</label>
  <select id="productType">
    <option value="sapi">🥩 Daging Sapi / Kambing</option>
    <option value="ayam">🍗 Daging Ayam</option>
    <option value="ikan">🐟 Ikan / Seafood</option>
  </select>

  <label for="storageTemp">Pilih Suhu Penyimpanan:</label>
  <select id="storageTemp">
    <option value="chiller">🧊 Chiller / Kulkas (~4°C)</option>
    <option value="room">🌡️ Suhu Ruangan (~25°C)</option>
    <option value="freezer">❄️ Freezer (-18°C)</option>
  </select>

  <label for="imageInput">Unggah Foto Stiker Indikator:</label>
  <input type="file" id="imageInput" accept="image/*">
  
  <img id="imagePreview" alt="Pratinjau Stiker">

  <div id="loading" class="loading">⏳ Menganalisis warna sampel...</div>
  
  <div id="reportArea">
    <div id="resultBox"></div>
    <div id="healthWarning" class="warning-box" style="display: none;"></div>
  </div>

  <div class="btn-group">
    <button id="exportBtn" class="btn btn-export" onclick="exportReport()">📥 Unduh Laporan</button>
    <button id="resetBtn" class="btn btn-reset" onclick="resetForm()">🔄 Reset</button>
  </div>
</div>

<!-- Kartu Kontak Pemilik Website Terpisah -->
<div class="card contact-card">
  <p style="margin: 0; color: var(--subtext-color);">
    Hubungi pemilik website untuk melaporkan bug atau meminta fitur tambahan lainnya melalui Gmail tersebut:
  </p>
  <a href="mailto:airmeletupsgg@gmail.com" class="contact-email">✉️ airmeletupsgg@gmail.com</a>
</div>

<script>
  const imageInput = document.getElementById('imageInput');
  const productType = document.getElementById('productType');
  const storageTemp = document.getElementById('storageTemp');
  const imagePreview = document.getElementById('imagePreview');
  const loading = document.getElementById('loading');
  const reportArea = document.getElementById('reportArea');
  const resultBox = document.getElementById('resultBox');
  const healthWarning = document.getElementById('healthWarning');
  const resetBtn = document.getElementById('resetBtn');
  const exportBtn = document.getElementById('exportBtn');
  const themeBtn = document.getElementById('themeBtn');

  function toggleTheme() {
    document.body.classList.toggle('dark-mode');
    const isDark = document.body.classList.contains('dark-mode');
    themeBtn.innerText = isDark ? "☀️ Terang" : "🌙 Gelap";
  }

  imageInput.addEventListener('change', async function(e) {
    const file = e.target.files[0];
    if (!file) return;

    imagePreview.src = URL.createObjectURL(file);
    imagePreview.style.display = 'block';
    loading.style.display = 'block';
    reportArea.style.display = 'none';
    resetBtn.style.display = 'none';
    exportBtn.style.display = 'none';

    const reader = new FileReader();
    reader.onload = async function() {
      const base64Data = reader.result.split(',')[1];
      
      try {
        const response = await fetch('/analyze', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ 
            image: base64Data,
            product: productType.value,
            temp: storageTemp.value
          })
        });
        
        const resData = await response.json();
        if (resData.error) {
          alert("Error: " + resData.error);
          loading.style.display = 'none';
          resetBtn.style.display = 'block';
          return;
        }

        tampilkanHasil(resData);
      } catch (err) {
        alert("Gagal terhubung ke server!");
        loading.style.display = 'none';
        resetBtn.style.display = 'block';
      }
    };
    reader.readAsDataURL(file);
  });

  function tampilkanHasil(data) {
    loading.style.display = 'none';
    reportArea.style.display = 'block';
    resetBtn.style.display = 'block';
    exportBtn.style.display = 'block';

    const isDark = document.body.classList.contains('dark-mode');

    if (data.kategori === "SEGAR") {
      reportArea.style.backgroundColor = isDark ? "#122a18" : "#d1e7dd";
      reportArea.style.color = isDark ? "#a3e6b1" : "#0f5132";
      reportArea.style.borderColor = "#badbcc";
      healthWarning.style.display = 'none';
    } else if (data.kategori === "LAYAK") {
      reportArea.style.backgroundColor = isDark ? "#332a08" : "#fff3cd";
      reportArea.style.color = isDark ? "#ffe885" : "#664d03";
      reportArea.style.borderColor = "#ffecb5";
      healthWarning.style.display = 'none';
    } else {
      reportArea.style.backgroundColor = isDark ? "#361316" : "#f8d7da";
      reportArea.style.color = isDark ? "#f5a3a8" : "#842029";
      reportArea.style.borderColor = "#f5c2c7";
      
      healthWarning.style.display = 'block';
      healthWarning.innerHTML = `<strong>⚠️ Risiko Keamanan Pangan:</strong><br>${data.peringatan_kesehatan}`;
    }

    resultBox.innerHTML = `
      <div style="font-size: 0.8em; opacity: 0.85; margin-bottom: 8px;">Waktu Uji: ${data.waktu_uji}</div>
      <strong>Jenis Produk:</strong> ${data.nama_produk}<br>
      <strong>Penyimpanan:</strong> ${data.suhu_teks}<br>
      <strong>Status:</strong> ${data.status}<br>
      <strong>Estimasi pH:</strong> ${data.ph}<br>
      <strong>Sisa Waktu Simpan:</strong> ${data.sisa_waktu}<br>
      <strong>Analisis:</strong> ${data.alasan}<br><br>
      <small style="font-size: 0.78em; opacity: 0.75;">${data.detail_teknis}</small>
    `;
  }

  function exportReport() {
    html2canvas(document.getElementById('mainCard')).then(canvas => {
      const link = document.createElement('a');
      link.download = `Sertifikat_Kesegaran_${Date.now()}.png`;
      link.href = canvas.toDataURL('image/png');
      link.click();
    });
  }

  function resetForm() {
    imageInput.value = '';
    imagePreview.src = '';
    imagePreview.style.display = 'none';
    reportArea.style.display = 'none';
    resetBtn.style.display = 'none';
    exportBtn.style.display = 'none';
    loading.style.display = 'none';
  }
</script>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        data = request.json
        base64_img = data.get('image')
        product = data.get('product', 'sapi')
        temp = data.get('temp', 'chiller')
        
        if not base64_img:
            return jsonify({"error": "Data gambar tidak ditemukan"}), 400

        # 1. Dekode Gambar
        img_bytes = base64.b64decode(base64_img)
        image = Image.open(io.BytesIO(img_bytes)).convert('RGB')
        
        # 2. Crop 30% Area Tengah Stiker
        w, h = image.size
        crop_box = (w * 0.35, h * 0.35, w * 0.65, h * 0.65)
        cropped = image.crop(crop_box)
        
        # 3. Hitung Warna RGB & HSV
        stat = ImageStat.Stat(cropped)
        r, g, b = [int(x) for x in stat.mean]
        h_float, s_float, v_float = colorsys.rgb_to_hsv(r/255.0, g/255.0, b/255.0)
        hue, sat, val = h_float * 360, s_float * 100, v_float * 100

        nama_produk_map = {"sapi": "Daging Sapi / Kambing", "ayam": "Daging Ayam", "ikan": "Ikan / Seafood"}
        suhu_map = {"chiller": "Chiller / Kulkas (4°C)", "room": "Suhu Ruangan (25°C)", "freezer": "Freezer (-18°C)"}
        
        nama_produk = nama_produk_map.get(product, "Daging Sapi")
        suhu_teks = suhu_map.get(temp, "Chiller (4°C)")

        # Rentang Warna HSV Indikator Betalain
        is_magenta_violet = (hue >= 280 and hue <= 350)
        is_deep_red_purple = (hue >= 351 or hue <= 15) and (b > g) and (r > 80)
        is_dark_purple_shadow = (r > 40 and b > 40 and g < r) and (sat > 20) and (val < 50)

        peringatan_kesehatan = ""

        if is_magenta_violet or is_deep_red_purple or is_dark_purple_shadow:
            status = "SEGAR (Sangat Baik)"
            kategori = "SEGAR"
            ph = "<= 5,8 (Asam)"
            alasan = "Pigmen betalain stabil. Kadar kesegaran tinggi dan belum ada pembusukan."
            
            if temp == "freezer":
                sisa_waktu = "3 - 6 Bulan"
            elif temp == "chiller":
                sisa_waktu = "2 - 3 Hari" if product == "sapi" else ("1 - 2 Hari" if product == "ayam" else "24 Jam")
            else:
                sisa_waktu = "4 - 6 Jam (Segera Masukkan Kulkas)"

        elif (hue >= 340 or hue <= 25) and (sat < 65 or val > 60) and (r > g) and (r > b):
            status = "LAYAK KONSUMSI"
            kategori = "LAYAK"
            ph = "~ 6,4 (Mendekati Netral)"
            alasan = "Pelepasan gas nitrogen (TVB-N) terdeteksi. Masih aman dimasak tetapi harus segera diolah."
            
            if temp == "freezer":
                sisa_waktu = "~1 - 2 Minggu (Segera Diolah)"
            elif temp == "chiller":
                sisa_waktu = "~12 - 18 Jam" if product == "sapi" else ("~8 - 12 Jam" if product == "ayam" else "~4 - 6 Jam")
            else:
                sisa_waktu = "< 2 Jam (Segera Olah Sekarang)"

        else:
            status = "TIDAK LAYAK KONSUMSI"
            kategori = "TIDAK_LAYAK"
            ph = ">= 7,5 (Basa)"
            alasan = "Pigmen terdegradasi akibat amoniak. Produk telah membusuk dan tidak aman dikonsumsi."
            sisa_waktu = "0 Jam (Segera Buang)"
            peringatan_kesehatan = "Produk terindikasi mengalami degradasi protein dan mengandung akumulasi amoniak/alkaloid. Berisiko tinggi menyebabkan keracunan makanan atau infeksi bakteri pembusuk."

        detail_teknis = f"Sampel RGB: ({r},{g},{b}) | HSV: ({int(hue)}°, {int(sat)}%, {int(val)}%)"
        waktu_uji = datetime.now().strftime("%d-%m-%Y %H:%M WIB")

        return jsonify({
            "nama_produk": nama_produk,
            "suhu_teks": suhu_teks,
            "status": status,
            "kategori": kategori,
            "ph": ph,
            "sisa_waktu": sisa_waktu,
            "alasan": alasan,
            "peringatan_kesehatan": peringatan_kesehatan,
            "detail_teknis": detail_teknis,
            "waktu_uji": waktu_uji
        })

    if __name__ == '__main__':
    app.run()
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
