import re
import sys
import os
import csv
import pandas as pd
import requests
from bs4 import BeautifulSoup
import streamlit as st

# اسٹریم لٹ پیج کی بنیادی سیٹنگز
st.set_page_config(page_title="Motus DOT Data Scraper", page_icon="🚚", layout="wide")

st.title("🚚 Motus DOT Data Scraper")
st.subheader("⚡ Real-time Table View | Upload TXT / CSV / XLSX ⚡")

# یوزر ان پٹ کا حصہ
col1, col2 = st.columns([2, 1])

with col1:
    user_input = st.text_area(
        "📝 Enter USDOT Numbers manually (comma or space separated):",
        value="6553522",
        height=150
    )

with col2:
    uploaded_file = st.file_uploader("📂 Load File (.txt, .csv, .xlsx)", type=["txt", "csv", "xlsx"])

start_btn = st.button("▶ Start Scraping", type="primary")

# بغیر کسی براؤزر کے، خالص ٹیکسٹ میچنگ کے ذریعے اسکرین شاٹ کے مطابق ڈیٹا نکالنے والا فنکشن
def scrape_motus_dot_data(dot_number):
    url = f"https://motus.dot.gov/customer/{dot_number}/account" 
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=20)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # پورے صفحے کا صاف ٹیکسٹ نکالنا
            page_text = soup.get_text(separator="\n")
            # صاف لائنوں کی لسٹ بنانا
            lines = [line.strip() for line in page_text.split("\n") if line.strip()]
            
            company_name = "Not Found"
            phone = "Not Found"
            email = "Not Found"
            status = "Active"
            
            # 1. اسٹیٹس تلاش کرنا (USDOT #6553522 - Active والی لائن سے)
            for line in lines:
                if f"USDOT #{dot_number}" in line or "USDOT #" in line:
                    if "Inactive" in line:
                        status = "Inactive"
                    break
            
            # 2. لسٹ کے اندر ٹیکسٹ پوزیشنز کے ذریعے ڈیٹا نکالنا (اسکرین شاٹ فکسڈ میچ)
            for i, line in enumerate(lines):
                # اگر لائن میں 'Legal Business Name' لکھا ہو، تو عام طور پر اگلی لائن ڈیٹا ہوگی
                if "Legal Business Name" in line and i + 1 < len(lines):
                    # چیک کریں کہ اگلی لائن کوئی دوسرا لیبل تو نہیں ہے
                    if not any(keyword in lines[i+1] for keyword in ["Doing Business As", "Principal Place", "Mailing Address", "Business Telephone", "Business Email"]):
                        company_name = lines[i+1]
                
                # فون نمبر تلاش کرنا
                if "Business Telephone No." in line and i + 1 < len(lines):
                    if not any(keyword in lines[i+1] for keyword in ["Company Officials", "Business Email", "Form of Business"]):
                        phone = lines[i+1]
                
                # ای میل تلاش کرنا
                if "Business Email" in line and i + 1 < len(lines):
                    if not any(keyword in lines[i+1] for keyword in ["Company Officials", "Business Telephone"]):
                        email = lines[i+1]
            
            # بیک اپ ریجیکس (Regex) اگر اوپر والا طریقہ مس ہو جائے
            if company_name == "Not Found" or phone == "Not Found" or email == "Not Found":
                # پورے ٹیکسٹ میں سے ریجیکس پیٹرن سرچ
                full_text_flat = " ".join(lines)
                
                name_match = re.search(r'Legal Business Name\s+([A-Z0-aligned\s,.\u00c0-\u017f]+?)(?=Doing Business|Principal|$)', full_text_flat, re.IGNORECASE)
                if name_match and company_name == "Not Found":
                    company_name = name_match.group(1).strip()
                    
                phone_match = re.search(r'Business Telephone No\.\s+(\+?\d{1,3}[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})', full_text_flat)
                if phone_match and phone == "Not Found":
                    phone = phone_match.group(1).strip()
                    
                email_match = re.search(r'Business Email\s+([\w\.-]+@[\w\.-]+)', full_text_flat)
                if email_match and email == "Not Found":
                    email = email_match.group(1).strip()

            return {
                "USDOT": dot_number,
                "Company Name": company_name,
                "Phone": phone,
                "Email": email,
                "Status": status
            }
        else:
            return {"USDOT": dot_number, "Company Name": "Error/Blocked", "Phone": "N/A", "Email": "N/A", "Status": f"HTTP {response.status_code}"}
            
    except Exception as e:
        return {
            "USDOT": dot_number,
            "Company Name": "Error",
            "Phone": "N/A",
            "Email": "N/A",
            "Status": "Connection Failed"
        }

# جب بٹن دبایا جائے
if start_btn:
    dot_numbers = [d.strip() for d in re.split(r'[\s,]+', user_input) if d.strip()]
    
    if not dot_numbers:
        st.warning("بھرائے مہربانی پہلے USDOT نمبرز درج کریں۔")
    else:
        st.write("### 📊 Extracted Data:")
        
        results_table = st.empty()
        all_results = []
        
        progress_bar = st.progress(0)
        
        for index, dot in enumerate(dot_numbers):
            with st.spinner(f"Scraping DOT: {dot}..."):
                res = scrape_motus_dot_data(dot)
                all_results.append(res)
                
                df = pd.DataFrame(all_results)
                results_table.dataframe(df, use_container_width=True)
                
            progress_bar.progress((index + 1) / len(dot_numbers))
            
        st.success("Scraping complete! 🎉")
        
        # --- ایکسل / CSV ڈاؤن لوڈ کا بٹن ---
        st.write("---")
        st.subheader("💾 Export Data")
        
        csv_data = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Data as CSV",
            data=csv_data,
            file_name="motus_dot_data.csv",
            mime="text/csv",
            type="primary"
        )
