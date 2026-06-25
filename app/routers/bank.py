import re
import io
import xml.etree.ElementTree as ET
from datetime import datetime, date
from typing import Optional
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.database import get_db
from app.models import Credit, Invoice

router = APIRouter(prefix="/api/bank", tags=["bank"])


def parse_dtposted(val):
    """Parse YYYYMMDDHHMMSS or YYYYMMDD to datetime."""
    if not val:
        return None
    s = str(val).split(".")[0].split("[")[0].strip()
    for fmt in ("%Y%m%d%H%M%S", "%Y%m%d"):
        try:
            return datetime.strptime(s[:len(fmt.replace("%", "XX").replace("X", ""))], fmt)
        except Exception:
            pass
    return None


def ofx_date_to_dt(s: str) -> Optional[datetime]:
    s = re.sub(r"\[.*\]", "", s).strip()
    for fmt in ("%Y%m%d%H%M%S", "%Y%m%d"):
        try:
            return datetime.strptime(s[:14] if fmt == "%Y%m%d%H%M%S" else s[:8], fmt)
        except Exception:
            pass
    return None


def parse_ofx_text(content: str) -> list[dict]:
    """Parse SGML-style OFX (not XML). Returns list of transaction dicts."""
    transactions = []
    # Split on STMTTRN blocks
    blocks = re.findall(r"<STMTTRN>(.*?)</STMTTRN>", content, re.DOTALL | re.IGNORECASE)
    if not blocks:
        # Try without closing tag (old OFX)
        blocks = re.split(r"<STMTTRN>", content, flags=re.IGNORECASE)[1:]

    for block in blocks:
        def get(tag):
            m = re.search(rf"<{tag}>(.*?)(?=<|\Z)", block, re.IGNORECASE | re.DOTALL)
            return m.group(1).strip() if m else ""

        trntype = get("TRNTYPE")
        dtposted = get("DTPOSTED")
        trnamt_s = get("TRNAMT").replace(",", ".")
        trnvasym = get("TRNVASYM") or get("CHECKNUM")
        reference_e2e = get("REFERENCE_E2E") or get("REFNUM")
        name = get("NAME")
        memo = get("MEMO")
        iban4 = get("IBAN4") or get("BANKACCTTO/ACCTID")
        trncosym = get("TRNCOSYM")
        trnspsym = get("TRNSPSYM")
        bankid2 = get("BANKID2")
        acctid3 = get("ACCTID3")
        currency = get("CURRENCY") or get("CURSYM") or "EUR"

        # Extract VS from REFERENCE_E2E if TRNVASYM empty
        if not trnvasym and reference_e2e:
            m = re.search(r"/VS(\d+)/", reference_e2e)
            if m:
                trnvasym = m.group(1)

        try:
            amt = float(trnamt_s)
        except Exception:
            amt = 0.0

        dt = ofx_date_to_dt(dtposted)

        transactions.append({
            "trntype": trntype,
            "dtposted": dt.timestamp() if dt else None,
            "trnamt": amt,
            "trnvasym": trnvasym or None,
            "trncosym": float(trncosym) if trncosym else None,
            "reference_e2e": reference_e2e or None,
            "name": name or None,
            "memo": memo or None,
            "iban4": iban4 or None,
            "trnspsym": trnspsym or None,
            "bankid2": float(bankid2) if bankid2 else None,
            "acctid3": acctid3 or None,
            "currency": currency or "EUR",
        })
    return transactions


def parse_pdf_transactions(data: bytes) -> list[dict]:
    """Extract bank transactions from a Slovak bank PDF statement."""
    import pdfplumber

    transactions = []
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        full_text = "\n".join(page.extract_text() or "" for page in pdf.pages)

    # Try to detect Slovak bank format patterns
    # Pattern: date  description  VS/KS/SS  amount  balance
    # Tatra banka / VÚB / ČSOB / Sporiteľňa all have slightly different formats
    # Common: date in DD.MM.YYYY, amount with comma decimal, VS somewhere in memo

    lines = full_text.split("\n")

    date_pattern = re.compile(r"\b(\d{1,2})\.(\d{1,2})\.(\d{4})\b")
    amount_pattern = re.compile(r"([+-]?\s*\d{1,3}(?:\s*\d{3})*[,\.]\d{2})\s*(EUR|€)?")

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        dm = date_pattern.search(line)
        if not dm:
            i += 1
            continue

        # Found a date — look for amount on same or next line
        amt_match = amount_pattern.search(line)
        combined = line
        if not amt_match and i + 1 < len(lines):
            combined = line + " " + lines[i + 1]
            amt_match = amount_pattern.search(combined)

        if not amt_match:
            i += 1
            continue

        amt_str = amt_match.group(1).replace(" ", "").replace(",", ".")
        try:
            amt = float(amt_str)
        except Exception:
            i += 1
            continue

        # Collect context lines for memo/VS
        context = combined
        for j in range(i + 1, min(i + 5, len(lines))):
            context += " " + lines[j]

        # Extract variable symbol
        vs_match = re.search(r"\bVS[:\s]*(\d{1,10})\b", context, re.IGNORECASE)
        trnvasym = vs_match.group(1) if vs_match else None

        # Also check /VS.../
        if not trnvasym:
            vs_match2 = re.search(r"/VS(\d+)/", context)
            if vs_match2:
                trnvasym = vs_match2.group(1)

        # Determine CREDIT or DEBIT
        trntype = "CREDIT" if amt > 0 else "DEBIT"

        dt_str = f"{dm.group(3)}{dm.group(2).zfill(2)}{dm.group(1).zfill(2)}"
        dt = ofx_date_to_dt(dt_str)

        transactions.append({
            "trntype": trntype,
            "dtposted": dt.timestamp() if dt else None,
            "trnamt": amt,
            "trnvasym": trnvasym,
            "name": None,
            "memo": context[:255],
            "iban4": None,
            "reference_e2e": None,
            "trncosym": None,
            "trnspsym": None,
            "bankid2": None,
            "acctid3": None,
            "currency": "EUR",
        })
        i += 1

    return transactions


@router.post("/import-ofx")
async def import_ofx(file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    """Import OFX/QFX bank statement file."""
    content = await file.read()
    try:
        text = content.decode("utf-8")
    except Exception:
        text = content.decode("latin-1")

    transactions = parse_ofx_text(text)
    if not transactions:
        raise HTTPException(400, "No transactions found in OFX file")

    imported = 0
    skipped = 0
    for t in transactions:
        # Check duplicate by dtposted + trnamt + trnvasym
        existing = await db.execute(
            select(Credit).where(
                Credit.dtposted == t["dtposted"],
                Credit.trnamt == t["trnamt"],
                Credit.trnvasym == t["trnvasym"],
            )
        )
        if existing.scalar_one_or_none():
            skipped += 1
            continue
        obj = Credit(**t)
        db.add(obj)
        imported += 1

    await db.commit()
    return {"imported": imported, "skipped": skipped, "total": len(transactions)}


@router.post("/import-pdf")
async def import_pdf(file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    """Import Slovak bank PDF statement."""
    data = await file.read()
    transactions = parse_pdf_transactions(data)
    if not transactions:
        raise HTTPException(400, "No transactions could be extracted from PDF. Try OFX export from your bank.")

    imported = 0
    skipped = 0
    for t in transactions:
        existing = await db.execute(
            select(Credit).where(
                Credit.dtposted == t["dtposted"],
                Credit.trnamt == t["trnamt"],
            )
        )
        if existing.scalar_one_or_none():
            skipped += 1
            continue
        obj = Credit(**t)
        db.add(obj)
        imported += 1

    await db.commit()
    return {"imported": imported, "skipped": skipped, "total": len(transactions)}


@router.post("/match-invoices")
async def match_invoices(db: AsyncSession = Depends(get_db)):
    """Match bank CREDIT transactions to invoices by variable symbol."""
    # Get all CREDIT transactions with a variable symbol
    credits_result = await db.execute(
        select(Credit).where(
            Credit.trntype == "CREDIT",
            Credit.trnvasym != None,
            Credit.trnvasym != "",
            Credit.trnamt > 0,
        )
    )
    credits = credits_result.scalars().all()

    matched = []
    unmatched_credits = []

    for c in credits:
        vs = (c.trnvasym or "").strip()
        if not vs:
            continue

        inv_result = await db.execute(
            select(Invoice).where(Invoice.cislo_faktury == vs)
        )
        invoice = inv_result.scalar_one_or_none()

        if not invoice:
            unmatched_credits.append({
                "credit_id": c.id,
                "trnamt": c.trnamt,
                "trnvasym": vs,
                "name": c.name,
                "dtposted": c.dtposted,
            })
            continue

        # Update invoice payment status
        paid_amount = c.trnamt
        old_zostava = invoice.zostava_uhradit or 0
        new_zostava = max(0.0, old_zostava - paid_amount)

        dt = None
        if c.dtposted:
            try:
                dt = datetime.fromtimestamp(c.dtposted)
            except Exception:
                pass

        invoice.zostava_uhradit = new_zostava
        if new_zostava == 0:
            invoice.datum_uhrady = dt

        # Recalculate dni_po_splatnosti
        if invoice.datum_splatnosti:
            ref_date = dt.date() if dt else date.today()
            delta = (ref_date - invoice.datum_splatnosti.date()).days
            invoice.dni_po_splatnosti = max(0, delta) if new_zostava > 0 else 0

        matched.append({
            "credit_id": c.id,
            "invoice_id": invoice.id,
            "cislo_faktury": invoice.cislo_faktury,
            "trnamt": paid_amount,
            "old_zostava": old_zostava,
            "new_zostava": new_zostava,
            "odberatel": invoice.odberatel,
        })

    await db.commit()
    return {
        "matched": matched,
        "matched_count": len(matched),
        "unmatched_count": len(unmatched_credits),
        "unmatched": unmatched_credits,
    }


@router.get("/match-preview")
async def match_preview(db: AsyncSession = Depends(get_db)):
    """Preview potential matches without updating invoices."""
    credits_result = await db.execute(
        select(Credit).where(
            Credit.trntype == "CREDIT",
            Credit.trnvasym != None,
            Credit.trnvasym != "",
            Credit.trnamt > 0,
        )
    )
    credits = credits_result.scalars().all()

    matches = []
    unmatched = []
    for c in credits:
        vs = (c.trnvasym or "").strip()
        if not vs:
            continue
        inv_result = await db.execute(
            select(Invoice).where(Invoice.cislo_faktury == vs)
        )
        invoice = inv_result.scalar_one_or_none()
        dt_str = ""
        if c.dtposted:
            try:
                dt_str = datetime.fromtimestamp(c.dtposted).strftime("%d.%m.%Y")
            except Exception:
                pass
        if invoice:
            matches.append({
                "credit_id": c.id,
                "invoice_id": invoice.id,
                "cislo_faktury": invoice.cislo_faktury,
                "trnamt": c.trnamt,
                "zostava_uhradit": invoice.zostava_uhradit,
                "odberatel": invoice.odberatel,
                "name": c.name,
                "dtposted": dt_str,
                "already_paid": (invoice.zostava_uhradit or 0) <= 0,
            })
        else:
            unmatched.append({
                "credit_id": c.id,
                "trnvasym": vs,
                "trnamt": c.trnamt,
                "name": c.name,
                "dtposted": dt_str,
            })

    return {"matches": matches, "unmatched": unmatched}


@router.post("/manual-match")
async def manual_match(data: dict, db: AsyncSession = Depends(get_db)):
    """Manually link a bank transaction to an invoice."""
    credit_id = data.get("credit_id")
    invoice_id = data.get("invoice_id")

    credit_result = await db.execute(select(Credit).where(Credit.id == credit_id))
    c = credit_result.scalar_one_or_none()
    if not c:
        raise HTTPException(404, "Bank transaction not found")

    inv_result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    invoice = inv_result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(404, "Invoice not found")

    old_zostava = invoice.zostava_uhradit or 0
    new_zostava = max(0.0, old_zostava - (c.trnamt or 0))
    invoice.zostava_uhradit = new_zostava

    dt = None
    if c.dtposted:
        try:
            dt = datetime.fromtimestamp(c.dtposted)
        except Exception:
            pass
    if new_zostava == 0:
        invoice.datum_uhrady = dt

    if invoice.datum_splatnosti and dt:
        delta = (dt.date() - invoice.datum_splatnosti.date()).days
        invoice.dni_po_splatnosti = max(0, delta) if new_zostava > 0 else 0

    await db.commit()
    return {"ok": True, "new_zostava": new_zostava, "cislo_faktury": invoice.cislo_faktury}
