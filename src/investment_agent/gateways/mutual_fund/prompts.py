"""Prompt template for mutual fund analysis.

Targets Indonesian retail mutual fund investors. The verified NAV is
embedded as-is; the agent's web search is used only to explain price
context (fund holdings news, market conditions, category outlook), never
to look up or second-guess the NAV itself.
"""

from investment_agent.domain.models import PriceSnapshot
from investment_agent.gateways.mutual_fund.models import MutualFundProduct
from investment_agent.infrastructure.formatting import format_rupiah


def _format_nav(value: float, currency: str) -> str:
    if currency == "IDR":
        return format_rupiah(value)
    return f"{currency} {value:,.4f}"


def _describe_change(change_pct: float | None) -> str:
    if change_pct is None:
        return "tidak tersedia"
    if change_pct > 0:
        return f"naik {change_pct:.2f}%"
    if change_pct < 0:
        return f"turun {abs(change_pct):.2f}%"
    return "stabil (0%)"


def build_mutual_fund_prompt(price_snapshot: PriceSnapshot, product: MutualFundProduct) -> str:
    """Build the reasoning prompt sent to the Claude Agent SDK for mutual fund analysis."""
    formatted_nav = _format_nav(price_snapshot.price, price_snapshot.currency)
    change_desc = _describe_change(price_snapshot.change_pct)

    context = (
        "Anda adalah analis reksadana berpengalaman yang melayani investor ritel reksadana "
        "di Indonesia.\n\n"
        "DATA NAV TERVERIFIKASI (jangan diragukan atau dicari ulang - gunakan apa adanya):\n"
        f"- Nama reksadana: {product.fund_name}\n"
        f"- Kategori: {product.fund_type_text}\n"
        f"- Manajer investasi: {product.investment_manager.full_name}\n"
        f"- Profil risiko: {product.risk_profile}\n"
        f"- NAV per unit saat ini: {formatted_nav}\n"
        f"- Perubahan harian: {change_desc} (per {price_snapshot.as_of.date().isoformat()})\n\n"
        "TUGAS ANDA:\n"
        "Gunakan web search untuk mengumpulkan konteks TERKINI (berita dan data beberapa hari "
        "terakhir) mengenai:\n"
        "1. Kondisi pasar yang relevan dengan kategori reksadana ini (mis. suku bunga dan pasar "
        "obligasi untuk pendapatan tetap, IHSG dan sentimen pasar saham untuk ekuitas, kondisi "
        "likuiditas perbankan untuk pasar uang).\n"
        "2. Kebijakan moneter bank sentral (BI/The Fed) yang relevan dengan kategori reksadana "
        "ini.\n"
        "3. Berita terkait manajer investasi atau isu spesifik pada instrumen-instrumen utama "
        "portofolio, bila ditemukan.\n"
        "4. Faktor makro Indonesia (inflasi, nilai tukar Rupiah, geopolitik) yang relevan "
        "dengan kategori reksadana ini.\n\n"
        "ATURAN PENTING:\n"
        "- JANGAN gunakan web search untuk mencari atau mengoreksi angka NAV - NAV di atas "
        "adalah satu-satunya angka yang sah.\n"
        '- Semua nilai mata uang Rupiah dalam jawaban Anda WAJIB ditulis dengan format "Rp" '
        '(misalnya "Rp1.985.000"), JANGAN PERNAH menulis "IDR".\n'
        "- Tulis seluruh isi jawaban dalam Bahasa Indonesia.\n"
        "- Jawaban HARUS berupa satu objek JSON valid saja, tanpa teks lain di luar JSON, "
        "tanpa markdown code fence.\n\n"
        "FORMAT JSON YANG WAJIB DIKEMBALIKAN (semua key wajib diisi):\n"
    )

    schema = (
        "{\n"
        '  "key_drivers": ["3-5 string, masing-masing satu faktor utama penggerak NAV saat '
        'ini, singkat dan spesifik"],\n'
        '  "technical_summary": "ringkasan analisis teknikal: tren NAV, momentum, dan '
        'perbandingan terhadap kategori sejenis",\n'
        '  "fundamental_summary": "ringkasan analisis fundamental: kondisi pasar, kebijakan '
        'moneter, dan faktor makro yang relevan dengan kategori reksadana ini",\n'
        '  "recommendation": "BUY" | "SELL" | "NEUTRAL",\n'
        '  "confidence_level": 0.0-1.0 (keyakinan berdasarkan kualitas dan konsistensi sumber '
        "yang ditemukan),\n"
        '  "risk_scenario": "satu skenario risiko konkret yang dapat membuat rekomendasi ini '
        'keliru, dan pemicunya"\n'
        "}"
    )

    return context + schema
