from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader


def main() -> None:
    pdf_path = Path(__file__).resolve().parents[2] / "Servicio_de_Verificacion_de_Descarga_Masiva_2023.pdf"
    if not pdf_path.exists():
        raise SystemExit(f"PDF not found: {pdf_path}")

    reader = PdfReader(str(pdf_path))

    terms = [
        "rechaz",
        "rechazada",
        "rechazado",
        "no se encontr",
        "sin registros",
        "sin resultados",
        "paquete",
        "paquetes",
        "5002",
        "5000",
        "codigo",
        "estatus",
        "status",
        "verific",
    ]

    hit_pages: list[int] = []
    for i, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").lower()
        if any(term in text for term in terms):
            hit_pages.append(i)

    print("pages:", len(reader.pages))
    print("hit_pages:", hit_pages)

    # Focus on the pages that usually contain status tables/codes
    focus_pages = [p for p in hit_pages if p >= 7]
    for i in focus_pages[:5]:
        text = (reader.pages[i - 1].extract_text() or "")
        print("\n=== page", i, "===")
        print(text[:4000])


if __name__ == "__main__":
    main()
