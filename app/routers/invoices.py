import io
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from app.database import get_db
from app.models import Invoice, Item, Project, Firma, FiremneUdaje

router = APIRouter(prefix="/api/invoices", tags=["invoices"])


@router.get("")
async def list_invoices(
    search: Optional[str] = None,
    nezaplatene: Optional[bool] = None,
    po_splatnosti: Optional[bool] = None,
    id_projektu: Optional[int] = None,
    skip: int = 0,
    limit: int = 300,
    db: AsyncSession = Depends(get_db),
):
    q = select(Invoice)
    if search:
        q = q.where(Invoice.odberatel.ilike(f"%{search}%"))
    if nezaplatene:
        q = q.where(Invoice.zostava_uhradit > 0)
    if po_splatnosti:
        q = q.where(Invoice.dni_po_splatnosti > 0)
    if id_projektu:
        q = q.where(Invoice.id_projektu == id_projektu)
    q = q.order_by(Invoice.datum_vystavenia.desc()).offset(skip).limit(limit)
    result = await db.execute(q)
    return result.scalars().all()


@router.get("/{invoice_id}")
async def get_invoice(invoice_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    return result.scalar_one_or_none()


@router.post("")
async def create_invoice(data: dict, db: AsyncSession = Depends(get_db)):
    allowed = {c.key for c in Invoice.__table__.columns} - {"id"}
    inv = Invoice(**{k: v for k, v in data.items() if k in allowed})
    db.add(inv)
    await db.commit()
    await db.refresh(inv)
    return inv


@router.put("/{invoice_id}")
async def update_invoice(invoice_id: int, data: dict, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    inv = result.scalar_one_or_none()
    if not inv:
        return {"error": "not found"}
    allowed = {c.key for c in Invoice.__table__.columns} - {"id"}
    for k, v in data.items():
        if k in allowed:
            setattr(inv, k, v)
    await db.commit()
    await db.refresh(inv)
    return inv


@router.delete("/{invoice_id}")
async def delete_invoice(invoice_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    inv = result.scalar_one_or_none()
    if inv:
        await db.delete(inv)
        await db.commit()
    return {"ok": True}


@router.get("/{invoice_id}/polozky")
async def get_invoice_items(invoice_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    inv = result.scalar_one_or_none()
    if not inv:
        raise HTTPException(404, "Faktúra nenájdená")
    # Items are linked via cislo_faktury string
    items_result = await db.execute(
        select(Item).where(Item.cislo_faktury == inv.cislo_faktury)
    )
    items = items_result.scalars().all()
    return [
        {
            "id": i.id,
            "id_projektu": i.id_projektu,
            "popis": i.popis,
            "podpopis": i.podpopis,
            "mj": i.mj,
            "pocet": i.pocet,
            "jc": i.jc,
            "cena": i.cena,
            "zlava": i.zlava,
            "sadzba_dph": i.sadzba_dph,
            "cena_s_dph": i.cena_s_dph,
        }
        for i in items
    ]


@router.get("/{invoice_id}/pdf")
async def generate_invoice_pdf(invoice_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    inv = result.scalar_one_or_none()
    if not inv:
        raise HTTPException(404, "Faktúra nenájdená")

    # Load supplier details
    ud_result = await db.execute(select(FiremneUdaje).where(FiremneUdaje.id == 1))
    ud = ud_result.scalar_one_or_none()

    # Load customer firm if linked
    firma = None
    if inv.firma_id:
        f_result = await db.execute(select(Firma).where(Firma.id == inv.firma_id))
        firma = f_result.scalar_one_or_none()

    # Load linked items via cislo_faktury
    items_result = await db.execute(
        select(Item).where(Item.cislo_faktury == inv.cislo_faktury)
    )
    items = items_result.scalars().all()

    # Load project if linked
    projekt = None
    if inv.id_projektu:
        p_result = await db.execute(select(Project).where(Project.id == inv.id_projektu))
        projekt = p_result.scalar_one_or_none()

    pdf_bytes = _build_pdf(inv, ud, firma, items, projekt)
    filename = f"faktura_{inv.cislo_faktury or inv.id}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _fmt_date(val) -> str:
    if not val:
        return ""
    if isinstance(val, str):
        try:
            val = datetime.fromisoformat(val.replace("Z", ""))
        except Exception:
            return val
    return val.strftime("%d.%m.%Y")


def _fmt_num(val, decimals=2) -> str:
    if val is None:
        return "0,00"
    return f"{val:,.{decimals}f}".replace(",", " ").replace(".", ",")


def _register_fonts():
    """Register Liberation Sans TTF for full Unicode/Slovak support. Cached after first call."""
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    import os
    if "LiberationSans" in pdfmetrics.getRegisteredFontNames():
        return
    base = "/usr/share/fonts/truetype/liberation"
    try:
        pdfmetrics.registerFont(TTFont("LiberationSans", f"{base}/LiberationSans-Regular.ttf"))
        pdfmetrics.registerFont(TTFont("LiberationSans-Bold", f"{base}/LiberationSans-Bold.ttf"))
        pdfmetrics.registerFont(TTFont("LiberationSans-Italic", f"{base}/LiberationSans-Italic.ttf"))
        from reportlab.pdfbase.pdfmetrics import registerFontFamily
        registerFontFamily("LiberationSans",
            normal="LiberationSans", bold="LiberationSans-Bold",
            italic="LiberationSans-Italic", boldItalic="LiberationSans-Bold")
    except Exception:
        pass  # Fallback to Helvetica if fonts not found


def _build_pdf(inv, ud, firma, items, projekt) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
    )
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_RIGHT, TA_CENTER, TA_LEFT
    from reportlab.pdfbase import pdfmetrics
    import os

    _register_fonts()
    FONT = "LiberationSans" if "LiberationSans" in pdfmetrics.getRegisteredFontNames() else "Helvetica"
    FONT_BOLD = f"{FONT}-Bold" if FONT == "LiberationSans" else "Helvetica-Bold"

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=15*mm, rightMargin=15*mm,
        topMargin=12*mm, bottomMargin=15*mm,
    )

    styles = getSampleStyleSheet()
    W = A4[0] - 30*mm  # usable width

    def style(name="Normal", **kw):
        kw.setdefault("fontName", FONT)
        s = ParagraphStyle(name + "_" + str(id(kw)), parent=styles[name], **kw)
        return s

    DARK = colors.HexColor("#1a2b45")
    ACCENT = colors.HexColor("#2563eb")
    LIGHT = colors.HexColor("#f1f5f9")
    GRAY = colors.HexColor("#64748b")

    story = []

    # ── Header: logo + title ──────────────────────────────────────────────────
    logo_path = os.path.join("static", "logo.png")
    logo_cell = ""
    if os.path.exists(logo_path):
        from reportlab.platypus import Image as RLImage
        logo_cell = RLImage(logo_path, width=40*mm, height=15*mm, kind="proportional")

    title_p = Paragraph(
        f'<font color="#2563eb" size="22"><b>FAKTÚRA</b></font>',
        style("Normal", alignment=TA_RIGHT)
    )
    num_p = Paragraph(
        f'<font color="#64748b" size="10">č. {inv.cislo_faktury or ""}</font>',
        style("Normal", alignment=TA_RIGHT)
    )

    hdr_table = Table(
        [[logo_cell or Paragraph("", styles["Normal"]), [title_p, num_p]]],
        colWidths=[W * 0.5, W * 0.5],
    )
    hdr_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
    ]))
    story.append(hdr_table)
    story.append(Spacer(1, 6*mm))
    story.append(HRFlowable(width="100%", thickness=1.5, color=ACCENT, spaceAfter=5*mm))

    # ── Dodávateľ / Odberateľ ────────────────────────────────────────────────
    def addr_block(label, name, addr, city, psc, ico, ic_dph, dic):
        lines = [f'<b><font color="#2563eb" size="8">{label}</font></b><br/>']
        if name:
            lines.append(f'<b><font size="10">{name}</font></b><br/>')
        if addr:
            lines.append(f'<font size="9">{addr}</font><br/>')
        if psc or city:
            lines.append(f'<font size="9">{psc or ""} {city or ""}</font><br/>')
        if ico:
            lines.append(f'<font size="8" color="#64748b">IČO: {ico}</font><br/>')
        if ic_dph:
            lines.append(f'<font size="8" color="#64748b">IČ DPH: {ic_dph}</font><br/>')
        if dic:
            lines.append(f'<font size="8" color="#64748b">DIČ: {dic}</font>')
        return Paragraph("".join(lines), style("Normal", leading=13))

    dod_name = ud.nazov if ud else ""
    dod_addr = ud.adresa if ud else ""
    dod_city = ud.mesto if ud else ""
    dod_psc = ud.psc if ud else ""
    dod_ico = ud.ico if ud else ""
    dod_ic_dph = ud.ic_dph if ud else ""
    dod_dic = ud.dic if ud else ""

    if firma:
        odb_name = firma.nazov or inv.odberatel or ""
        odb_addr = firma.adresa or ""
        odb_city = firma.mesto or ""
        odb_psc = firma.psc or ""
        odb_ico = firma.ico or ""
        odb_ic_dph = firma.ic_dph or ""
        odb_dic = firma.dic or ""
    else:
        odb_name = inv.odberatel or ""
        odb_addr = odb_city = odb_psc = odb_ico = odb_ic_dph = odb_dic = ""

    addr_table = Table(
        [[
            addr_block("DODÁVATEĽ", dod_name, dod_addr, dod_city, dod_psc, dod_ico, dod_ic_dph, dod_dic),
            addr_block("ODBERATEĽ", odb_name, odb_addr, odb_city, odb_psc, odb_ico, odb_ic_dph, odb_dic),
        ]],
        colWidths=[W * 0.5, W * 0.5],
    )
    addr_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, 0), (0, 0), LIGHT),
        ("BACKGROUND", (1, 0), (1, 0), colors.white),
        ("BOX", (0, 0), (0, 0), 0.5, colors.HexColor("#cbd5e1")),
        ("BOX", (1, 0), (1, 0), 0.5, colors.HexColor("#cbd5e1")),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(addr_table)
    story.append(Spacer(1, 5*mm))

    # ── Invoice meta ─────────────────────────────────────────────────────────
    iban_val = inv.iban or (ud.iban if ud else "") or ""
    swift_val = inv.swift or (ud.swift if ud else "") or ""
    banka_val = (ud.banka if ud else "") or ""

    meta_rows = [
        ["Dátum vystavenia:", _fmt_date(inv.datum_vystavenia),
         "Variabilný symbol:", inv.vs or inv.cislo_faktury or ""],
        ["Dátum splatnosti:", _fmt_date(inv.datum_splatnosti),
         "Forma úhrady:", inv.forma_uhrady or "bankový prevod"],
        ["IBAN:", iban_val, "SWIFT/BIC:", swift_val],
    ]
    if banka_val:
        meta_rows.append(["Banka:", banka_val, "", ""])
    if projekt:
        meta_rows.append(["Projekt:", f"{projekt.id} – {projekt.nazov_projektu or ''}", "", ""])

    meta_table = Table(
        meta_rows,
        colWidths=[W * 0.2, W * 0.3, W * 0.2, W * 0.3],
    )
    meta_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("FONTNAME", (0, 0), (-1, -1), FONT),
        ("FONTNAME", (0, 0), (0, -1), FONT_BOLD),
        ("FONTNAME", (2, 0), (2, -1), FONT_BOLD),
        ("TEXTCOLOR", (0, 0), (0, -1), DARK),
        ("TEXTCOLOR", (2, 0), (2, -1), DARK),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#e2e8f0")),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 5*mm))

    # ── Items table ───────────────────────────────────────────────────────────
    popis_label = inv.popis or ""
    if items:
        col_w = [W * 0.04, W * 0.38, W * 0.08, W * 0.08, W * 0.1, W * 0.08, W * 0.08, W * 0.08, W * 0.08]
        header = [
            Paragraph("<b>#</b>", style("Normal", fontSize=7, alignment=TA_CENTER)),
            Paragraph("<b>Popis</b>", style("Normal", fontSize=7)),
            Paragraph("<b>MJ</b>", style("Normal", fontSize=7, alignment=TA_CENTER)),
            Paragraph("<b>Počet</b>", style("Normal", fontSize=7, alignment=TA_RIGHT)),
            Paragraph("<b>Jedn. cena</b>", style("Normal", fontSize=7, alignment=TA_RIGHT)),
            Paragraph("<b>Zľava %</b>", style("Normal", fontSize=7, alignment=TA_RIGHT)),
            Paragraph("<b>Cena bez DPH</b>", style("Normal", fontSize=7, alignment=TA_RIGHT)),
            Paragraph("<b>DPH %</b>", style("Normal", fontSize=7, alignment=TA_RIGHT)),
            Paragraph("<b>Cena s DPH</b>", style("Normal", fontSize=7, alignment=TA_RIGHT)),
        ]
        rows = [header]
        for idx, it in enumerate(items, 1):
            rows.append([
                Paragraph(str(idx), style("Normal", fontSize=8, alignment=TA_CENTER)),
                Paragraph(it.popis or "", style("Normal", fontSize=8)),
                Paragraph(it.mj or "ks", style("Normal", fontSize=8, alignment=TA_CENTER)),
                Paragraph(_fmt_num(it.pocet, 0) if it.pocet and it.pocet == int(it.pocet or 0) else _fmt_num(it.pocet), style("Normal", fontSize=8, alignment=TA_RIGHT)),
                Paragraph(_fmt_num(it.jc), style("Normal", fontSize=8, alignment=TA_RIGHT)),
                Paragraph(_fmt_num(it.zlava, 1) if it.zlava else "—", style("Normal", fontSize=8, alignment=TA_RIGHT)),
                Paragraph(_fmt_num(it.cena), style("Normal", fontSize=8, alignment=TA_RIGHT)),
                Paragraph(_fmt_num(it.sadzba_dph * 100 if it.sadzba_dph and it.sadzba_dph < 2 else it.sadzba_dph, 0), style("Normal", fontSize=8, alignment=TA_RIGHT)),
                Paragraph(_fmt_num(it.cena_s_dph), style("Normal", fontSize=8, alignment=TA_RIGHT)),
            ])
        items_table = Table(rows, colWidths=col_w, repeatRows=1)
        items_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), DARK),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, -1), FONT),
            ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#e2e8f0")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 3),
            ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(items_table)
    else:
        # No linked items — show popis as single line
        story.append(Paragraph(
            f'Popis: {popis_label}',
            style("Normal", fontSize=9)
        ))
    story.append(Spacer(1, 5*mm))

    # ── Totals ────────────────────────────────────────────────────────────────
    # In this DB: suma_bez_dph = base, suma_s_dph = VAT amount, suma_k_uhrade = total
    suma_bez = inv.suma_bez_dph or 0
    suma_dph = inv.suma_s_dph or 0          # stored as VAT amount, not total
    k_uhrade = inv.suma_k_uhrade or (suma_bez + suma_dph)
    suma_celkom = suma_bez + suma_dph        # reconstruct total

    totals_data = [
        ["Základ DPH:", f"{_fmt_num(suma_bez)} €"],
        ["DPH:", f"{_fmt_num(suma_dph)} €"],
        ["Celkom s DPH:", f"{_fmt_num(suma_celkom)} €"],
        ["K úhrade:", f"{_fmt_num(k_uhrade)} €"],
    ]
    totals_table = Table(
        totals_data,
        colWidths=[W * 0.75, W * 0.25],
    )
    totals_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("FONTNAME", (0, 0), (0, -1), FONT_BOLD),
        ("FONTNAME", (1, 0), (1, -1), FONT),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("FONTNAME", (0, 3), (-1, 3), FONT_BOLD),
        ("FONTSIZE", (0, 3), (-1, 3), 11),
        ("TEXTCOLOR", (0, 3), (-1, 3), ACCENT),
        ("BACKGROUND", (0, 3), (-1, 3), colors.HexColor("#eff6ff")),
        ("BOX", (0, 3), (-1, 3), 1, ACCENT),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (1, 0), (1, -1), 5),
        ("LINEABOVE", (0, 3), (-1, 3), 0.5, ACCENT),
    ]))
    story.append(totals_table)

    # ── Note / poznamka ───────────────────────────────────────────────────────
    poznamka = inv.poznamka or (ud.poznamka_fa if ud else None)
    if poznamka:
        story.append(Spacer(1, 5*mm))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#e2e8f0")))
        story.append(Spacer(1, 2*mm))
        story.append(Paragraph(
            f'<font size="8" color="#64748b">{poznamka}</font>',
            style("Normal")
        ))

    # ── Footer ────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 5*mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#e2e8f0")))
    footer_parts = []
    if ud:
        if ud.telefon:
            footer_parts.append(f"Tel: {ud.telefon}")
        if ud.email:
            footer_parts.append(f"E-mail: {ud.email}")
        if ud.web:
            footer_parts.append(ud.web)
    story.append(Paragraph(
        f'<font size="7" color="#94a3b8">{" | ".join(footer_parts)}</font>',
        style("Normal", alignment=TA_CENTER)
    ))

    doc.build(story)
    return buf.getvalue()
