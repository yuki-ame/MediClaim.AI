import streamlit as st
import requests
import re
import json

st.title("Medical Billing Claims Agent Demo")

uploaded_file = st.file_uploader("Upload a medical bill (PDF/Image/Text)", type=["pdf", "png", "jpg", "jpeg", "txt"])
API_URL = "http://localhost:8000"

def clean_gemini_json(raw):
    match = re.search(r'({.*)', raw, re.DOTALL)
    if match:
        json_part = match.group(1)
    else:
        json_part = raw
    json_part = re.sub(r"^\s*``` json", "", json_part, flags=re.MULTILINE)
    json_part = re.sub(r"^\s*```", "", json_part, flags=re.MULTILINE)
    json_part = re.sub(r"\s*``` \s*$", "", json_part, flags=re.MULTILINE)
    return json_part.strip()

# Use session_state to persist between button clicks
if 'extracted' not in st.session_state: st.session_state['extracted'] = None
if 'validated' not in st.session_state: st.session_state['validated'] = None
if 'claim_form_text' not in st.session_state: st.session_state['claim_form_text'] = ""

if uploaded_file is not None:
    st.write("File uploaded:", uploaded_file.name)
    if uploaded_file.type.startswith("image/"):
        st.image(uploaded_file, caption="Uploaded Bill Preview", use_column_width=True)
    if st.button("Extract Data"):
        files = {'file': (uploaded_file.name, uploaded_file, uploaded_file.type)}
        with st.spinner("Extracting..."):
            response = requests.post(f"{API_URL}/extract", files=files)
        if response.ok:
            result = response.json()
            raw_text = result.get("extracted_data", "")
            clean_json = clean_gemini_json(raw_text)
            try:
                extracted = json.loads(clean_json)
                st.session_state['extracted'] = extracted
            except Exception as e:
                st.error("Could not parse extracted data as JSON")
                st.write(clean_json)
                st.session_state['extracted'] = None

if st.session_state['extracted']:
    extracted = st.session_state['extracted']
    st.markdown("""
<div style="background:#fff;border-radius:12px;padding:32px;width:480px;margin:auto;box-shadow:0 2px 8px #8882; color:#222;">
  <div style="display:flex;justify-content:space-between;">
    <h3 style="margin:0; color:#222;">Extracted Medical Data</h3>
  </div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:28px;margin-top:20px; color:#222;">
    <div><b>Patient Name</b><br>{patient_name}</div>
    <div><b>Date of Service</b><br>{date_of_service}</div>
    <div><b>Service Code</b><br>{service_code}</div>
    <div><b>Amount</b><br>${amount}</div>
    <div><b>Provider</b><br>{provider_name}</div>
    <div><b>Address</b><br>{address}</div>
    <div><b>Phone</b><br>{provider_phone}</div>
    <div><b>Insurance ID</b><br>{insurance_id}</div>
  </div>
  <hr style="margin:20px 0;">
  <div style="font-size:1.15em; color:#222;">
    <b>Diagnosis/Notes</b><br>{diagnosis_notes}
  </div>
</div>
""".format(
    patient_name=extracted.get("patient_name", ""),
    date_of_service=extracted.get("date_of_service", ""),
    service_code=extracted.get("service_code", ""),
    amount=extracted.get("amount", ""),
    provider_name=extracted.get("provider_name", ""),
    address=extracted.get("address", ""),
    provider_phone=extracted.get("provider_phone", ""),
    insurance_id=extracted.get("insurance_id", ""),
    diagnosis_notes=extracted.get("diagnosis_notes", "")
), unsafe_allow_html=True)
    

    if st.button("Validate Claim"):
        with st.spinner("Validating..."):
            validate_resp = requests.post(f"{API_URL}/validate", json=extracted)
    try:
        val_res = validate_resp.json()
    except Exception:
        st.error("Could not parse validation server response!")
        st.write(validate_resp.text)
        st.session_state['validated'] = False
    else:
        if 'error' in val_res:
            st.error(val_res['error'])
            st.session_state['validated'] = False
        elif not val_res.get("results"):
            st.error("No valid services found for validation. Please check extracted data.")
            st.json(val_res)
            st.session_state['validated'] = False
        else:
            all_ok = all(item["status"]=="approved" for item in val_res["results"])
            if all_ok:
                st.success("All Validations Passed. Ready to generate claim form.")
                st.session_state['validated'] = True
            else:
                st.error("Validation failed!")
                st.json(val_res)
                st.session_state['validated'] = False



if st.session_state['validated']:
    if st.button("Generate Claim Form"):
        with st.spinner("Generating claim form..."):
            gen_resp = requests.post(f"{API_URL}/generate_claim_form", json=st.session_state['extracted'])
        if gen_resp.ok:
            claim_data = gen_resp.json()
            form_text = claim_data.get("claim_form_text", "")
            st.session_state['claim_form_text'] = form_text
        else:
            st.error("Failed to generate claim form.")

if st.session_state['claim_form_text']:
    form_text = st.session_state['claim_form_text']
    st.markdown("#### Generated Claim Form")
    st.text_area("Claim Form", form_text, height=300)
    st.download_button("Download", form_text, file_name="claim_form.txt")
    to_email = st.text_input("Corporate/TPA Email to send claim:")
    if st.button("Send Claim Form by Email"):
        email_payload = {"to_email": to_email, "claim_form_text": form_text}
        with st.spinner("Sending email..."):
            mail_resp = requests.post(f"{API_URL}/email_claim_form", json=email_payload)
        if mail_resp.ok:
            st.success(f"Claim form sent to {to_email}!")
        else:
            st.error(f"Failed to send email: {mail_resp.content}")
