"""Prompt template for gold analysis.

Targets Indonesian retail gold investors (Antam/Pegadaian-style per-gram
pricing). The verified price is embedded as-is; the agent's web search is
used only to explain price context (macro drivers, news, technical
commentary), never to look up or second-guess the price itself.
"""

from investment_agent.domain.models import PriceSnapshot
from investment_agent.infrastructure.formatting import format_rupiah


def _describe_change(change_pct: float | None) -> str:
    if change_pct is None:
        return "tidak tersedia"
    if change_pct > 0:
        return f"naik {change_pct:.2f}%"
    if change_pct < 0:
        return f"turun {abs(change_pct):.2f}%"
    return "stabil (0%)"


def build_gold_prompt(price_snapshot: PriceSnapshot) -> str:
    """Build the reasoning prompt sent to the Claude Agent SDK for gold analysis."""
    formatted_price = format_rupiah(price_snapshot.price)
    change_desc = _describe_change(price_snapshot.change_pct)

    context = (
        "Anda adalah analis pasar emas berpengalaman yang melayani investor ritel emas fisik "
        "di Indonesia (mengacu pada patokan harga Antam/Pegadaian per gram).\n\n"
        "DATA HARGA TERVERIFIKASI (jangan diragukan atau dicari ulang - gunakan apa adanya):\n"
        f"- Harga emas saat ini: {formatted_price} per gram\n"
        f"- Perubahan 24 jam: {change_desc} (per {price_snapshot.as_of.isoformat()})\n\n"
        "TUGAS ANDA:\n"
        "Gunakan web search untuk mengumpulkan konteks TERKINI (berita dan data beberapa hari "
        "terakhir) mengenai:\n"
        "1. Pergerakan harga emas global (XAU/USD) dan nilai tukar Rupiah terhadap Dolar AS "
        "(USD/IDR), karena keduanya menentukan harga emas domestik.\n"
        "2. Kebijakan moneter bank sentral utama (terutama The Fed) yang mempengaruhi arah "
        "suku bunga dan daya tarik emas sebagai aset non-yield.\n"
        "3. Faktor geopolitik dan risiko makro global yang mendorong permintaan aset "
        "safe-haven.\n"
        "4. Aktivitas pembelian emas oleh bank sentral (termasuk Bank Indonesia bila "
        "relevan).\n"
        "5. Faktor musiman/domestik Indonesia yang mempengaruhi permintaan emas ritel (mis. "
        "musim pernikahan, Ramadan/Lebaran, awal tahun ajaran/investasi).\n"
        "6. Gambaran teknikal terkini emas (tren, level support/resistance, indikator "
        "momentum) dari analisis pasar yang tersedia.\n\n"
        "ATURAN PENTING:\n"
        "- JANGAN gunakan web search untuk mencari atau mengoreksi angka harga - harga di "
        "atas adalah satu-satunya angka yang sah.\n"
        '- Semua nilai mata uang Rupiah dalam jawaban Anda WAJIB ditulis dengan format "Rp" '
        '(misalnya "Rp1.985.000"), JANGAN PERNAH menulis "IDR".\n'
        "- Tulis seluruh isi jawaban dalam Bahasa Indonesia.\n"
        "- Jawaban HARUS berupa satu objek JSON valid saja, tanpa teks lain di luar JSON, "
        "tanpa markdown code fence.\n\n"
        "FORMAT JSON YANG WAJIB DIKEMBALIKAN (semua key wajib diisi):\n"
    )

    schema = (
        "{\n"
        '  "key_drivers": ["3-5 string, masing-masing satu faktor utama penggerak harga saat '
        'ini, singkat dan spesifik"],\n'
        '  "technical_summary": "ringkasan analisis teknikal: tren, level support/resistance '
        'dalam Rp/gram bila memungkinkan, dan momentum",\n'
        '  "fundamental_summary": "ringkasan analisis fundamental: kebijakan moneter, nilai '
        'tukar, geopolitik, dan faktor domestik Indonesia",\n'
        '  "recommendation": "BUY" | "SELL" | "NEUTRAL",\n'
        '  "confidence_level": 0.0-1.0 (keyakinan berdasarkan kualitas dan konsistensi sumber '
        "yang ditemukan),\n"
        '  "risk_scenario": "satu skenario risiko konkret yang dapat membuat rekomendasi ini '
        'keliru, dan pemicunya"\n'
        "}"
    )

    return context + schema
