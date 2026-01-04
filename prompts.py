"""Prompt templates for the receipt extraction app."""

MARKDOWN_INSTRUCTION = """
You are extracting information from a receipt or invoice that may span multiple pages. Preserve reading order across pages. Do not hallucinate missing fields. Return ONLY markdown without code fences.
Use this layout:

# {document_name}
- Document type: receipt or invoice; if unsure say unknown
- Vendor: name and address in one line
- Date: ISO-8601 if possible, else as seen
- Receipt/Invoice #: value if present, else blank
- Currency: 3-letter code if possible
## Totals
- Subtotal: numeric or blank
- Tax: numeric or blank
- Shipping/Freight: numeric or blank; treat shipping and freight as the same charge
- Tip: numeric or blank
- Total: numeric or blank
- Payment method: card/cash/etc. if present
## Line items
| Description | Qty | Unit price | Amount |
|---|---:|---:|---:|
| ... |
## Notes
Additional notes or disclaimers; if none, leave blank.
""".strip()


JSON_INSTRUCTION = """
Extract structured data from a receipt or invoice that may span multiple pages. Preserve reading order across pages. Do not hallucinate missing fields; use nulls for missing data. Treat shipping and freight as the same charge under the "shipping" field. Return ONLY a valid JSON object, no markdown, no backticks.
Schema:
{{
  "document_name": string,
  "document_type": "receipt"|"invoice"|"unknown",
  "vendor": {{
    "name": string|null,
    "address": string|null,
    "phone": string|null,
    "tax_id": string|null
  }},
  "invoice_or_receipt_number": string|null,
  "date": string|null,
  "currency": string|null,
  "subtotal": number|null,
  "tax": number|null,
  "shipping": number|null,
  "tip": number|null,
  "total": number|null,
  "payment_method": string|null,
  "line_items": [{{
    "description": string,
    "quantity": number|null,
    "unit_price": number|null,
    "amount": number|null
  }}],
  "notes": string|null,
  "confidence": {{
    "overall": number,
    "fields": {{
      "vendor.name": number,
      "date": number,
      "total": number
    }}
  }}
}}
""".strip()


JSON_REPAIR_PROMPT = """
The previous response was not valid JSON. Return ONLY valid JSON that conforms to the requested schema. Do not include explanations or markdown.
""".strip()
