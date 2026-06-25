import re
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List, Tuple
from app.database import get_db
from app.models import Imposition

router = APIRouter(prefix="/api/imposition", tags=["imposition"])


@router.get("")
async def list_imposition(
    format: Optional[str] = None,
    vazba_typ: Optional[str] = None,
    skip: int = 0,
    limit: int = 200,
    db: AsyncSession = Depends(get_db),
):
    q = select(Imposition)
    if format:
        q = q.where(Imposition.format == format)
    if vazba_typ:
        q = q.where(Imposition.vazba_typ == vazba_typ)
    q = q.order_by(Imposition.id.desc()).offset(skip).limit(limit)
    result = await db.execute(q)
    return result.scalars().all()


@router.get("/{imp_id}")
async def get_imposition(imp_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Imposition).where(Imposition.id == imp_id))
    return result.scalar_one_or_none()


@router.post("")
async def create_imposition(data: dict, db: AsyncSession = Depends(get_db)):
    imp = Imposition(**data)
    db.add(imp)
    await db.commit()
    await db.refresh(imp)
    return imp


@router.put("/{imp_id}")
async def update_imposition(imp_id: int, data: dict, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Imposition).where(Imposition.id == imp_id))
    imp = result.scalar_one_or_none()
    if not imp:
        return {"error": "not found"}
    for k, v in data.items():
        if hasattr(imp, k):
            setattr(imp, k, v)
    await db.commit()
    await db.refresh(imp)
    return imp


@router.delete("/{imp_id}")
async def delete_imposition(imp_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Imposition).where(Imposition.id == imp_id))
    imp = result.scalar_one_or_none()
    if imp:
        await db.delete(imp)
        await db.commit()
    return {"ok": True}


# ── Imposition script generation ──────────────────────────────────────────────

def parse_ranges(text: str) -> List[int]:
    """Parse comma-separated page ranges like '1,3-9,12' into sorted list of ints."""
    pages = []
    if not text:
        return pages
    for part in text.split(","):
        part = part.strip()
        if not part:
            continue
        m = re.match(r"^(\d+)-(\d+)$", part)
        if m:
            pages.extend(range(int(m.group(1)), int(m.group(2)) + 1))
        elif re.match(r"^\d+$", part):
            pages.append(int(part))
    return sorted(set(pages))


def pages_to_ranges(pages: List[int]) -> str:
    """Convert sorted list of ints to compact range string like '1,3-9,12'."""
    if not pages:
        return ""
    pages = sorted(set(pages))
    ranges = []
    start = pages[0]
    end = pages[0]
    for p in pages[1:]:
        if p == end + 1:
            end = p
        else:
            ranges.append(str(start) if start == end else f"{start}-{end}")
            start = end = p
    ranges.append(str(start) if start == end else f"{start}-{end}")
    return ",".join(ranges)


def build_pdftk_blocks(cb_pages_set: set, max_page: int) -> List[Tuple[str, int, int]]:
    """Return list of (type, start, end) blocks where type is 'K' or 'C'."""
    blocks = []
    if not cb_pages_set or max_page < 1:
        return blocks
    current_type = None
    block_start = 1
    for p in range(1, max_page + 1):
        t = "K" if p in cb_pages_set else "C"
        if t != current_type:
            if current_type is not None:
                blocks.append((current_type, block_start, p - 1))
            current_type = t
            block_start = p
    if current_type is not None:
        blocks.append((current_type, block_start, max_page))
    return blocks


def blocks_to_cat(blocks: List[Tuple[str, int, int]]) -> str:
    parts = []
    for t, s, e in blocks:
        parts.append(f"{t}{s}" if s == e else f"{t}{s}-{e}")
    return " ".join(parts)


def generate_pdftk_komplet(cb_strany: str, max_page: int) -> str:
    cb_set = set(parse_ranges(cb_strany))
    if not cb_set:
        return ""
    blocks = build_pdftk_blocks(cb_set, max_page)
    cat_str = blocks_to_cat(blocks)
    return f"pdftk K=CBK.pdf C=FAR.pdf cat {cat_str}  output KOMPLET.pdf"


def generate_pdftk_kratky(cb_strany_v_dokumente: str, na_far: str) -> str:
    """Generate short pdftk using sequential K/C numbering."""
    cb_range = (cb_strany_v_dokumente or "").strip()
    if not cb_range:
        return ""
    far_sheets, _ = _parse_na_far_info(na_far)
    if far_sheets == 0:
        return f"pdftk K=CBK.pdf cat K{cb_range} output 01_KOMPLET.pdf"
    c_part = "C1" if far_sheets == 1 else f"C1-{far_sheets}"
    return f"pdftk K=CBK.pdf C=FAR.pdf cat  {c_part} K{cb_range} output 01_KOMPLET.pdf"



def _parse_na_far_info(na_far: str) -> Tuple[int, int]:
    """Return (far_sheets, far_doc_pages).
    far_sheets = number of insert sheets (C pages in FAR.pdf).
    far_doc_pages = total document page positions occupied by inserts in KOMPLET.
    """
    if not na_far:
        return 0, 0
    sheets = 0
    max_page = 0
    for line in na_far.splitlines():
        line = line.strip()
        if not line:
            continue
        if any(kw in line for kw in ["tlačiarni", "tlaciarni", "FAR tlač", "CB tlač"]):
            continue
        if re.search(r"\d", line):
            sheets += 1
            # Find max page number mentioned in this line
            nums = [int(x) for x in re.findall(r"\d+", line)]
            if nums:
                max_page = max(max_page, max(nums))
    return sheets, max_page


def generate_pdftk_cb_tlac(cb_strany_v_dokumente: str, na_far: str) -> str:
    far_sheets, far_doc_pages = _parse_na_far_info(na_far)
    cb_range = (cb_strany_v_dokumente or "").strip()
    if not cb_range:
        return ""
    cb_pages = parse_ranges(cb_range)
    if not cb_pages:
        return ""
    total_komplet = far_sheets + len(cb_pages)
    cb_start = far_doc_pages + 1
    if cb_start > total_komplet:
        return ""
    return f"pdftk K=01_KOMPLET.pdf cat K{cb_start}-{total_komplet} output 02_CBTLAC.pdf"


def generate_pdftk_vkladacky(cb_strany_v_dokumente: str, na_far: str) -> str:
    far_sheets, far_doc_pages = _parse_na_far_info(na_far)
    if far_doc_pages == 0:
        return ""
    page_range = "K1" if far_doc_pages == 1 else f"K1-{far_doc_pages}"
    return f"pdftk K=01_KOMPLET.pdf cat {page_range} output 03_VKLADACKY.pdf"


@router.post("/{imp_id}/generate")
async def generate_scripts(imp_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Imposition).where(Imposition.id == imp_id))
    imp = result.scalar_one_or_none()
    if not imp:
        raise HTTPException(404, "Záznam nenájdený")

    cb_strany = imp.cb_strany or ""
    cb_strany_v_dok = imp.cb_strany_v_dokumente or ""
    na_far = imp.na_far or ""
    stran = imp.stran or 0

    # Determine max content page
    cb_pages = parse_ranges(cb_strany)
    max_page = max(cb_pages) if cb_pages else stran

    imp.pdftk_komplet = generate_pdftk_komplet(cb_strany, max_page)
    imp.pdftk_komplet_kratky = generate_pdftk_kratky(cb_strany_v_dok, na_far)
    imp.pdftk_cb_tlac = generate_pdftk_cb_tlac(cb_strany_v_dok, na_far)
    imp.pdftk_vkladacky = generate_pdftk_vkladacky(cb_strany_v_dok, na_far)

    await db.commit()
    await db.refresh(imp)
    return imp
