from fastapi import FastAPI, UploadFile, File, Body
from fastapi.responses import JSONResponse
import google.generativeai as genai
import os
import json
import pdfplumber
import pytesseract
from PIL import Image
import io
import traceback
import re
import smtplib
from email.mime.text import MIMEText

# ---- Gemini API Setup ----
genai.configure(api_key="AIzaSyA9laTe65QLd6vVw0KSCBxlB8MR4jOxtAo")  # Visible for hackathon/demo

app = FastAPI(title="Medical Billing & Claims Agent")

with open("rules.json") as f:
    RULES = json.load(f)

@app.get("/")
def root():
    return {"message": "Medical Billing & Claims Agent Running 🚀"}

@app.post("/extract")
async def extract_data(file: UploadFile = File(...)):
    try:
        print("File received:", file.filename)
        contents = await file.read()
        content_type = file.content_type
        text = ""

        if content_type == "application/pdf":
            print("Trying PDF extraction with pdfplumber...")
            with pdfplumber.open(io.BytesIO(contents)) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text
            print("Extracted text from PDF:", text[:200])
        elif content_type.startswith("image/"):
            print("Trying image OCR with pytesseract...")
            image = Image.open(io.BytesIO(contents))
            text = pytesseract.image_to_string(image)
            print("Extracted text from image:", text[:200])
        else:
            print("Attempting plain text extraction...")
            text = contents.decode("utf-8", errors="ignore")
            print("Loaded text file with content:", text[:200])
        
        if not text.strip():
            print("No readable text found.")
            return JSONResponse(status_code=400, content={"error": "No readable text found in the file."})

        # Strong Gemini information extraction prompt
        model = genai.GenerativeModel("gemini-1.5-pro")
        prompt = f"""
Extract as much medical billing information as possible from the provided text, even if data appears in a table, is scattered, or is part of sentences. If a field is not present or cannot be found, set it to null.

Return a JSON dictionary with these top-level keys:
- patient_name
- date_of_service
- provider_name
- provider_phone
- diagnosis_notes
- address
- insurance_id

If there are multiple services (charges), return them as an array under a top-level key "services":
"services": [
    {{
      "service_code": ...,
      "description": ...,
      "amount": ...
    }},
    ...
]

Do not return any Markdown formatting or explanation—ONLY raw JSON.

Here is the bill text:
{text}
"""

        print("Gemini prompt:", prompt[:500])
        response = model.generate_content(prompt)
        extracted_text = response.text
        print("Gemini response text:", extracted_text)

        # --- Exception Handling for Null/Bogus Output ---
        if (
            extracted_text is None
            or "null" in extracted_text.lower()
            or "no information" in extracted_text.lower()
            or re.search(r'"\s*patient_name\s*"\s*:\s*null', extracted_text)
        ):
            print("No useful data extracted for this input!")
            return JSONResponse(
                status_code=400,
                content={
                    "error": "No useful medical billing information could be extracted from the uploaded document. Please provide a proper medical bill."
                }
            )

        return {"extracted_data": extracted_text}
    
    except Exception as e:
        print("EXTRACT ERROR:", traceback.format_exc())
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/validate")
async def validate_claims(data: dict):
    try:
        print("Validation input:", data)

        patient_name = data.get("patient_name", "Unknown")
        date = data.get("date_of_service", "Unknown")
        services = data.get("services", [])

        # Fallback for single flat code/amount
        if not services:
            code = data.get("service_code")
            amount = data.get("amount")
            if code and amount is not None:
                services = [{"service_code": code, "amount": amount}]

        # If STILL no valid services, error out.
        if not services:
            return JSONResponse(
                status_code=400,
                content={"error": "No valid services found in submitted data. Please check the extraction."}
            )

        results = []
        for service in services:
            code = service.get("service_code")
            amount = service.get("amount")
            try:
                amount = float(amount)
            except (TypeError, ValueError):
                continue  # skip if it's not a valid number

            if not code or amount is None:
                continue
            if code not in RULES or not RULES[code]["covered"]:
                model = genai.GenerativeModel("gemini-1.5-pro")
                prompt = f"""Draft a formal appeal letter for denial of claim with code {code}.
                Patient: {patient_name}, Date: {date}, Amount: {amount}.
                Reason: Not covered by insurance."""
                response = model.generate_content(prompt)
                results.append({
                    "service_code": code,
                    "status": "denied",
                    "appeal_letter": response.text
                })
            elif amount > RULES[code]["max_amount"]:
                model = genai.GenerativeModel("gemini-1.5-pro")
                prompt = f"""Draft a formal appeal letter for denial due to overbilling.
                Patient: {patient_name}, Date: {date}, Amount: {amount}.
                Maximum allowed amount for code {code}: {RULES[code]['max_amount']}"""
                response = model.generate_content(prompt)
                results.append({
                    "service_code": code,
                    "status": "denied",
                    "appeal_letter": response.text
                })
            else:
                results.append({
                    "service_code": code,
                    "status": "approved",
                    "claim_form": {
                        "patient_name": patient_name,
                        "date": date,
                        "service_code": code,
                        "amount": amount
                    }
                })

        if not results:
            return JSONResponse(
                status_code=400,
                content={"error": "No valid service codes/amounts found for validation. Please check the extracted bill data."}
            )
        return {"results": results}

    except Exception as e:
        print("VALIDATE ERROR:", traceback.format_exc())
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/email_claim_form")
async def email_claim_form(claim_form: dict = Body(...)):
    """
    Email the generated claim form to a specified corporate/insurance address.
    """
    recipient_email = claim_form.get("to_email")
    claim_text = claim_form.get("claim_form_text")
    sender_email = "youraddress@gmail.com"       # Replace with your gmail or sender
    sender_password = "your_app_password"        # Use a Gmail app password here
    subject = "New Medical Claim Submission"
    msg = MIMEText(claim_text)
    msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = recipient_email
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, [recipient_email], msg.as_string())
        return {"status": "sent", "to": recipient_email}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
