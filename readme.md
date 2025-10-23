# 🧾 Prescription PDF Extraction System

## Overview

This project extracts **structured data** from pharmacy or healthcare **prescription PDFs**.

This pipeline reads the PDF, uses **LLM-based parsing** to populate all required variables, and outputs a canonical JSON matching your internal form fields.

It supports **both OpenAI and Vertex AI (Gemini)** through a unified LangChain interface.

---

## ✨ Features

* ✅ **Dual-provider**: Run on OpenAI (`gpt-4o-mini`, `gpt-4o`) or Vertex AI (`gemini-1.5-pro`)
* 🧠 **LangChain integration**: easily plug into workflows (e.g., n8n, Airflow, etc.)
* 🖼️ **Vision + Text hybrid**: converts scanned PDFs to images if OCR text is sparse
* 🧩 **Canonical JSON schema**: covers all fields from order metadata to clinical data
* 🪶 **Safe defaults**: missing fields are returned as empty strings
* 🧰 **Post-processing**: cleans numeric and date formats (`YYYY-MM-DD`)

---

## 📁 Canonical JSON Schema

Your prescription payload always conforms to this structure:

```jsonc
{
  "order_metadata": {...},
  "patient_information": {...},
  "prescriber_information": {...},
  "payment": {...},
  "shipping_delivery": {...},
  "medication_prescription_data": {...},
  "clinical": {...}
}
```

👉 [See full schema here](#canonical-schema-details) for all keys.

---

## ⚙️ Installation

```bash
pip install langchain langchain-openai langchain-google-vertexai \
            pydantic pdf2image pymupdf pillow
# Poppler is required for pdf2image
```

---

## 🔑 Environment Setup

### For OpenAI

```bash
export OPENAI_API_KEY=sk-yourkey
```

### For Vertex AI

```bash
export GOOGLE_CLOUD_PROJECT=your-gcp-project
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
```

---

## 🚀 Usage

### **OpenAI Example**

```bash
python extract_prescription_langchain.py \
  --pdf prescriptions/9830438.pdf \
  --provider openai \
  --model gpt-4o-mini \
  --out /data/out/prescription_payload.json
```

### **Vertex AI Example**

```bash
python extract_prescription_langchain.py \
  --pdf /prescriptions/9830438.pdf \
  --provider vertex \
  --model gemini-1.5-pro \
  --location us-central1 \
  --out /data/out/prescription_payload.json
```

### **Force text-only mode**

Skips image conversion if you only expect selectable text:

```bash
python extract_prescription_langchain.py --pdf prescription.pdf --no-vision
```

---

## 🧩 n8n Integration

1. **Mount** the script in your n8n container.
2. **Execute Command Node**:

   * OpenAI:

     ```bash
     python /data/bin/extract_prescription_langchain.py \
       --pdf /data/prescriptions/prescription.pdf \
       --provider openai --model gpt-4o-mini \
       --out /data/out/prescription_payload.json
     ```
   * Vertex:

     ```bash
     python /data/bin/extract_prescription_langchain.py \
       --pdf /data/prescriptions/prescription.pdf \
       --provider vertex --model gemini-1.5-pro \
       --location us-central1 \
       --out /data/out/prescription_payload.json
     ```
3. **Set Node** → map output JSON fields to your left-side form variables.

---

## 🧱 Canonical Schema Details

### **1. Order Metadata**

`order_id`, `order_date`, `foreign_order_id`, `document_type`, `priority`,
`status`, `activity`, `due_on`, `manager`, `location`, `practice_id`,
`source_system`, `creation_user`, `last_modified_user`

### **2. Patient Information**

`patient_id`, `patient_first_name`, `patient_last_name`, `patient_dob`, `patient_age`,
`patient_gender`, `patient_pregnancy`, `patient_species`, `patient_ethnicity`,
`patient_weight_kg`, `patient_height_cm`, `patient_phone`, `patient_email`,
`patient_address_line1`, `patient_address_line2`, `patient_city`, `patient_state`,
`patient_zip`, `patient_country`, `patient_insurance_provider`,
`patient_insurance_id`, `patient_group_number`

### **3. Prescriber / Provider Information**

`prescriber_id`, `prescriber_first_name`, `prescriber_last_name`, `prescriber_npi`,
`prescriber_phone`, `prescriber_fax`, `prescriber_email`, `prescriber_clinic_name`,
`prescriber_address_line1`, `prescriber_address_line2`, `prescriber_city`,
`prescriber_state`, `prescriber_zip`, `prescriber_license`,
`prescriber_license_expiration_date`, `prescriber_dea`,
`prescriber_dea_expiration_date`, `prescriber_controlled_license`,
`prescriber_controlled_license_expiration`, `prescriber_discipline`

### **4. Payment**

`payor`, `payor_lastname`, `payor_firstname`, `payor_address`,
`payor_address_line1`, `payor_address_line2`, `payor_city`, `payor_state`, `payor_zip`

### **5. Shipping & Delivery**

`shipping_method`, `ship_date`, `delivery_date`, `tracking_number`, `courier`,
`shipping_address_line1`, `shipping_address_line2`, `shipping_city`,
`shipping_state`, `shipping_zip`, `shipping_contact_name`, `shipping_contact_phone`

### **6. Medication / Prescription Data**

`rx_number`, `fill_date`, `drug_name`, `strength`, `form`, `ndc_code`, `sig`,
`days_supply`, `quantity_dispensed`, `refills_remaining`, `lot_number`,
`expiration_date`, `unit_price`, `ingredient_cost`, `dispensing_fee`,
`tax_amount`, `line_total`, `pharmacy_notes`

### **7. Clinical**

`patient_allergies`, `patient_diseases`, `patient_medication_history`, `patient_encounters`

---

## 🧠 Output Example

```json
{
  "order_metadata": {
    "order_id": "98304348",
    "order_date": "2025-10-22",
    "foreign_order_id": "",
    "document_type": "New Rx",
    "priority": "Normal",
    "status": "",
    "activity": "",
    "due_on": "",
    "manager": "",
    "location": "",
    "practice_id": "",
    "source_system": "ieRx",
    "creation_user": "",
    "last_modified_user": ""
  },
  "patient_information": {
    "patient_id": "",
    "patient_first_name": "Tracy",
    "patient_last_name": "Hardyman",
    "patient_dob": "1969-06-08",
    "patient_age": "",
    "patient_gender": "F",
    "patient_pregnancy": "",
    "patient_species": "",
    "patient_ethnicity": "",
    "patient_weight_kg": "",
    "patient_height_cm": "",
    "patient_phone": "6513866946",
    "patient_email": "hardymantracy@hotmail.com",
    "patient_address_line1": "26705 Flower Valley Rd",
    "patient_address_line2": "",
    "patient_city": "Red Wing",
    "patient_state": "MN",
    "patient_zip": "55066",
    "patient_country": "US",
    "patient_insurance_provider": "",
    "patient_insurance_id": "",
    "patient_group_number": ""
  },
  "prescriber_information": {
    "prescriber_id": "",
    "prescriber_first_name": "Daniel",
    "prescriber_last_name": "Frunsch",
    "prescriber_npi": "8888964854",
    "prescriber_phone": "",
    "prescriber_fax": "",
    "prescriber_email": "",
    "prescriber_clinic_name": "Brello",
    "prescriber_address_line1": "8836 W Cage Blvd Ste 201B",
    "prescriber_address_line2": "",
    "prescriber_city": "Kennewick",
    "prescriber_state": "WA",
    "prescriber_zip": "99336",
    "prescriber_license": "MD.45014 AL",
    "prescriber_license_expiration_date": "",
    "prescriber_dea": "",
    "prescriber_dea_expiration_date": "",
    "prescriber_controlled_license": "",
    "prescriber_controlled_license_expiration": "",
    "prescriber_discipline": ""
  },
  "payment": {
    "payor": "Prescriber",
    "payor_lastname": "Kaira",
    "payor_firstname": "Sail",
    "payor_address": "5908 Breckenridge Pkwy",
    "payor_address_line1": "5908 Breckenridge Pkwy",
    "payor_address_line2": "",
    "payor_city": "Tampa",
    "payor_state": "FL",
    "payor_zip": "33619"
  },
  "shipping_delivery": {
    "shipping_method": "",
    "ship_date": "",
    "delivery_date": "",
    "tracking_number": "",
    "courier": "",
    "shipping_address_line1": "26705 Flower Valley Rd",
    "shipping_address_line2": "",
    "shipping_city": "Red Wing",
    "shipping_state": "MN",
    "shipping_zip": "55066",
    "shipping_contact_name": "Tracy Hardyman",
    "shipping_contact_phone": "6513866946"
  },
  "medication_prescription_data": {
    "rx_number": "",
    "fill_date": "",
    "drug_name": "Semaglutide/Pyridoxine 5mg-8mg/mL MDV Inj Sol",
    "strength": "5mg-8mg/mL",
    "form": "MDV Inj Sol",
    "ndc_code": "",
    "sig": "INJECT 1 UNITS (0.9 MG) SUBCUTANEOUSLY ONCE WEEKLY FOR 4 WEEKS. DISCARD ANY REMAINING AFTER 28 DAYS.",
    "days_supply": "28",
    "quantity_dispensed": "1",
    "refills_remaining": "1",
    "lot_number": "",
    "expiration_date": "",
    "unit_price": "",
    "ingredient_cost": "",
    "dispensing_fee": "",
    "tax_amount": "",
    "line_total": "",
    "pharmacy_notes": ""
  },
  "clinical": {
    "patient_allergies": "",
    "patient_diseases": "",
    "patient_medication_history": "",
    "patient_encounters": ""
  }
}
```

