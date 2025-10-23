# extract_invoice_langchain.py
from __future__ import annotations
import os, io, json, base64, tempfile, re
from typing import Dict, Any, List, Tuple
from dataclasses import dataclass
from datetime import datetime

import fitz  # PyMuPDF
from pdf2image import convert_from_path
from PIL import Image

# --- LangChain providers ---
from langchain_openai import ChatOpenAI
from langchain_google_vertexai import ChatVertexAI
from langchain.schema import SystemMessage, HumanMessage

# ---------------- Canonical schema ----------------
CANONICAL_SCHEMA: Dict[str, Any] = {
  "order_metadata": {
    "order_id": "", "order_date": "", "foreign_order_id": "", "document_type": "",
    "priority": "", "status": "", "activity": "", "due_on": "", "manager": "",
    "location": "", "practice_id": "", "source_system": "", "creation_user": "",
    "last_modified_user": ""
  },
  "patient_information": {
    "patient_id": "", "patient_first_name": "", "patient_last_name": "",
    "patient_dob": "", "patient_age": "", "patient_gender": "", "patient_pregnancy": "",
    "patient_species": "", "patient_ethnicity": "", "patient_weight_kg": "",
    "patient_height_cm": "", "patient_phone": "", "patient_email": "",
    "patient_address_line1": "", "patient_address_line2": "", "patient_city": "",
    "patient_state": "", "patient_zip": "", "patient_country": "",
    "patient_insurance_provider": "", "patient_insurance_id": "", "patient_group_number": ""
  },
  "prescriber_information": {
    "prescriber_id": "", "prescriber_first_name": "", "prescriber_last_name": "",
    "prescriber_npi": "", "prescriber_phone": "", "prescriber_fax": "",
    "prescriber_email": "", "prescriber_clinic_name": "", "prescriber_address_line1": "",
    "prescriber_address_line2": "", "prescriber_city": "", "prescriber_state": "",
    "prescriber_zip": "", "prescriber_license": "", "prescriber_license_expiration_date": "",
    "prescriber_dea": "", "prescriber_dea_expiration_date": "", "prescriber_controlled_license": "",
    "prescriber_controlled_license_expiration": "", "prescriber_discipline": ""
  },
  "payment": {
    "payor": "", "payor_lastname": "", "payor_firstname": "", "payor_address": "",
    "payor_address_line1": "", "payor_address_line2": "", "payor_city": "",
    "payor_state": "", "payor_zip": ""
  },
  "shipping_delivery": {
    "shipping_method": "", "ship_date": "", "delivery_date": "", "tracking_number": "",
    "courier": "", "shipping_address_line1": "", "shipping_address_line2": "",
    "shipping_city": "", "shipping_state": "", "shipping_zip": "",
    "shipping_contact_name": "", "shipping_contact_phone": ""
  },
  "medication_prescription_data": {
    "rx_number": "", "fill_date": "", "drug_name": "", "strength": "", "form": "",
    "ndc_code": "", "sig": "", "days_supply": "", "quantity_dispensed": "",
    "refills_remaining": "", "lot_number": "", "expiration_date": "", "unit_price": "",
    "ingredient_cost": "", "dispensing_fee": "", "tax_amount": "", "line_total": "",
    "pharmacy_notes": ""
  },
  "clinical": {
    "patient_allergies": "", "patient_diseases": "", "patient_medication_history": "", "patient_encounters": ""
  }
}

# --------------- Utility: schema & post-processing ---------------
def schema_keys_nested(schema: Dict[str, Any]) -> Dict[str, List[str]]:
    """Return a dict of section -> flat list of keys (for instructions/validation)."""
    out = {}
    for section, content in schema.items():
        if isinstance(content, dict):
            out[section] = list(content.keys())
        else:
            out[section] = []  # not expected here
    return out

def ensure_all_fields(result: Dict[str, Any], schema: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure every section/key exists; fill '' for missing."""
    out = {}
    for section, content in schema.items():
        sec_val = result.get(section, {}) if isinstance(result, dict) else {}
        if not isinstance(sec_val, dict):
            sec_val = {}
        fixed = {}
        for k in content.keys():
            v = sec_val.get(k, "")
            if v is None: v = ""
            fixed[k] = v
        out[section] = fixed
    return out

_DATE_FIELDS = re.compile(r"(date|dob|expiration|due_on|ship_date|delivery_date)$", re.I)
_NUMERIC_HINT = re.compile(r"(amount|price|total|fee|paid|tax|qty|quantity|zip|npi|dea|phone|rx|order_id|invoice|weight|height|days_supply|unit_price|line_total)$", re.I)

def normalize_date(s: str) -> str:
    s = (s or "").strip()
    if not s: return ""
    fmts = ["%Y-%m-%d","%m/%d/%Y","%d/%m/%Y","%m-%d-%Y","%d-%m-%Y","%b %d, %Y","%d %b %Y"]
    for f in fmts:
        try: return datetime.strptime(s, f).strftime("%Y-%m-%d")
        except Exception: pass
    return s

def postprocess_all(d: Dict[str, Any]) -> Dict[str, Any]:
    for section, content in d.items():
        for k, v in content.items():
            if v is None:
                content[k] = ""
                continue
            if isinstance(v, (int, float)):  # leave as-is
                continue
            s = str(v).strip()
            if _NUMERIC_HINT.search(k):
                s = s.replace("$", "").replace(",", "").strip()
            if _DATE_FIELDS.search(k):
                s = normalize_date(s)
            content[k] = s
    return d

# --------------- PDF ingestion ---------------
def extract_text_with_pymupdf(pdf_path: str) -> Tuple[str, List[str]]:
    doc = fitz.open(pdf_path)
    texts, per_page = [], []
    for i in range(len(doc)):
        t = doc[i].get_text("text")
        texts.append(t)
        per_page.append(t)
    doc.close()
    return "\n\n".join(texts), per_page

def pdf_to_b64_images(pdf_path: str, dpi: int = 200) -> List[str]:
    imgs = convert_from_path(pdf_path, dpi=dpi)
    b64s = []
    for im in imgs:
        with io.BytesIO() as buf:
            im.save(buf, format="PNG")
            b64s.append(base64.b64encode(buf.getvalue()).decode("utf-8"))
    return b64s

# --------------- LLM prompts ---------------
SYSTEM = (
    "You are an expert invoice parser for pharmacy/health invoices.\n"
    "Return ONLY a JSON object that exactly matches the provided canonical schema keys.\n"
    "If a field is not present in the document, set it to an empty string \"\".\n"
    "Rules:\n"
    "- Dates as YYYY-MM-DD when possible.\n"
    "- Numbers as plain numerals (no currency symbols or commas).\n"
    "- Do not invent or infer beyond the document.\n"
)

def build_user_instruction(schema: Dict[str, Any]) -> str:
    return (
        "Canonical schema (section -> keys). Produce JSON with exactly these sections and keys:\n"
        + json.dumps(schema_keys_nested(schema), indent=2)
        + "\n\nExtract values from the attached document (or accompanying text)."
    )

# --------------- Provider wiring (OpenAI / Vertex) ---------------
@dataclass
class ProviderConfig:
    provider: str  # "openai" or "vertex"
    model: str     # e.g., "gpt-4o-mini" or "gemini-1.5-pro"
    location: str = "us-central1"  # used by Vertex

def make_llm(cfg: ProviderConfig):
    if cfg.provider == "openai":
        # response_format is enforced by ChatOpenAI via tool calling or JSON mode; we keep the output checked in code.
        return ChatOpenAI(model=cfg.model, temperature=0)
    elif cfg.provider == "vertex":
        return ChatVertexAI(model_name=cfg.model, temperature=0, location=cfg.location)
    else:
        raise ValueError("provider must be 'openai' or 'vertex'")

def messages_for_text(schema: Dict[str, Any], plain_text: str):
    return [
        SystemMessage(content=SYSTEM),
        HumanMessage(content=f"{build_user_instruction(schema)}\n\nDocument text:\n{plain_text[:150000]}"),
    ]

def messages_for_images(schema: Dict[str, Any], b64_images: List[str]):
    # Build a multi-part HumanMessage content (vision)
    content_parts: List[dict] = [{"type": "text", "text": build_user_instruction(schema)}]
    # Attach images
    for b64 in b64_images:
        content_parts.append({"type": "image_url", "image_url": f"data:image/png;base64,{b64}"})
    return [SystemMessage(content=SYSTEM), HumanMessage(content=content_parts)]

# --------------- Extraction orchestrator ---------------
def extract_invoice(pdf_path: str, cfg: ProviderConfig, use_vision_if_needed: bool = True) -> Dict[str, Any]:
    # 1) Try text first
    text, pages = extract_text_with_pymupdf(pdf_path)
    avg_len = sum(len(p) for p in pages) / max(1, len(pages))
    text_ok = avg_len > 300  # heuristic: scanned pages often have very little extracted text

    llm = make_llm(cfg)
    if text_ok:
        msgs = messages_for_text(CANONICAL_SCHEMA, text)
    else:
        if not use_vision_if_needed:
            msgs = messages_for_text(CANONICAL_SCHEMA, text)  # fall back with whatever was extracted
        else:
            # 2) Vision path: convert pages to images
            b64_images = pdf_to_b64_images(pdf_path, dpi=220)
            msgs = messages_for_images(CANONICAL_SCHEMA, b64_images)

    resp = llm.invoke(msgs)
    raw = resp.content if isinstance(resp.content, str) else json.dumps(resp.content)

    # Best-effort JSON parse
    try:
        parsed = json.loads(raw)
    except Exception:
        # Sometimes models wrap in code fences; strip and retry
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.DOTALL)
        try:
            parsed = json.loads(cleaned)
        except Exception:
            parsed = {}

    # 3) Guarantee full shape + post-process
    shaped = ensure_all_fields(parsed, CANONICAL_SCHEMA)
    shaped = postprocess_all(shaped)
    return shaped

# --------------- CLI ---------------
if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True, help="Path to the invoice PDF")
    ap.add_argument("--provider", choices=["openai", "vertex"], default="openai")
    ap.add_argument("--model", default="gpt-4o-mini", help="OpenAI: gpt-4o-mini/gpt-4o; Vertex: gemini-1.5-pro")
    ap.add_argument("--location", default="us-central1", help="Vertex location/region")
    ap.add_argument("--no-vision", action="store_true", help="Disable vision even if text is sparse")
    ap.add_argument("--out", default="invoice_payload.json", help="Output JSON path")
    args = ap.parse_args()

    cfg = ProviderConfig(provider=args.provider, model=args.model, location=args.location)
    data = extract_invoice(args.pdf, cfg, use_vision_if_needed=not args.no_vision)

    with open(args.out, "w") as f:
        json.dump(data, f, indent=2)
    print(f"Wrote {args.out}")
