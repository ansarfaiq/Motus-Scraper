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

# موٹس ڈاٹ جی او وی کے لیے بالکل سادہ اور تیز اسکریپنگ فنکشن (بغیر پلے رائٹ کے)
def scrape_motus_dot_data(dot_number):
    # آپ کا بتایا ہوا بالکل صحیح لنک
    url = f"https://motus.dot.gov/customer/{dot_number}/account" 
    
    # یہ ہیڈرز ویب سائٹ کو یہ یقین دلائیں گے کہ یہ ایک عام براؤزر ہے
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
    }
    
    try:
        # ڈائریکٹ لنک ہٹ کرنا (سپر فاسٹ)
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # --- موٹس پورٹل کے مطابق ڈیٹا نکالنا ---
            
            # 1. کمپنی کا نام (اگر h1 یا h2 ٹیگ میں ہو)
            name_tag = soup.find("h1") or soup.find("h2") or soup.find("title")
            company_name = name_tag.text.strip() if name_tag else "Not Found"
            
            # اگر نام میں ویب سائٹ کا ٹائٹل آ رہا ہو تو اسے صاف کرنا
            company_name = company_name.replace(" - Motus", "").strip()
            
            # 2. فون نمبر تلاش کرنا
            phone = "Not Found"
            # پورے پیج کے ٹیکسٹ میں سے فون نمبر کا پیٹرن ڈھونڈنا
            phone_match = re.search(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', response.text)
            if phone_match:
                phone = phone_match.group(0)
            
            # 3. ای میل تلاش کرنا
            email = "Not Found"
            email_match = re.search(r'[\w\.-]+@[\w\.-]+', response.text)
            if email_match:
                email = email_match.group(0)
            
            # 4. اسٹیٹس
            status = "Active"
            if "Inactive" in response.text or "Suspended" in response.text:
                status = "Inactive"
                
            return {
                "USDOT": dot_number,
                "Company Name": company_name,
                "Phone": phone,
                "Email": email,
                "Status": status
            }
        else:
            return {"USDOT": dot_number, "Company Name": "Blocked/Error", "Phone": "N/A", "Email": "N/A", "Status": f"HTTP {response.status_code}"}
            
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
    # نمبرز کو الگ کرنا
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
                
                # ریئل ٹائم میں ٹیبل اپڈیٹ ہونا
                df = pd.DataFrame(all_results)
                results_table.dataframe(df, use_container_width=True)
                
            progress_bar.progress((index + 1) / len(dot_numbers))
            
        st.success("Scraping complete! 🎉")
        
        # --- ڈاؤن لوڈ کا بٹن ---
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
