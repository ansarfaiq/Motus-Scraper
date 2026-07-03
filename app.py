import re
import sys
import os
import csv
import threading
import requests
from bs4 import BeautifulSoup
import streamlit as st

# ایکسل فائل ہینڈلنگ کے لیے
try:
    from openpyxl import load_workbook
except ImportError:
    load_workbook = None

# اسٹریم لٹ پیج کی بنیادی سیٹنگز
st.set_page_config(page_title="Motus Data Scraper", page_icon="🚚", layout="wide")

st.title("🚚 Motus Data Scraper")
st.subheader("⚡ Real-time Table View | Upload TXT / CSV / XLSX ⚡")

# یوزر سے ان پٹ لینے کا حصہ
col1, col2 = st.columns([2, 1])

with col1:
    user_input = st.text_area(
        "📝 Enter USDOT Numbers manually (comma or space separated):",
        value="655322\n5094822\n7270293",
        height=150
    )

with col2:
    uploaded_file = st.file_uploader("📂 Load File (.txt, .csv, .xlsx)", type=["txt", "csv", "xlsx"])

# بٹنز
start_btn = st.button("▶ Start Scraping", type="primary")
clear_btn = st.button("🗑 Clear Table")

# اسکریپنگ کا مین فنکشن (جو بغیر براؤزر کے ڈائریکٹ ریکویسٹ بھیجے گا)
def scrape_dot_data(dot_number):
    # یہاں آپ کی مطلوبہ ویب سائٹ کا یو آر ایل آئے گا، مثال کے طور پر:
    url = f"https://ai.fmcsa.dot.gov/SMS/Carrier/{dot_number}/CompleteProfile.aspx"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        # ڈائریکٹ ویب سائٹ کو ہٹ کرنا بغیر کسی براؤزر کے
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # ----------------------------------------------------
            # نوٹ: یہاں آپ کا پرانا بیوٹی فل سوپ (BeautifulSoup) کا لاجک ائے گا
            # جو ڈیٹا نکالتا ہے (جیسے کمپنی کا نام، ای میل، فون وغیرہ)
            # عارضی طور پر میں ایک ڈمی رزلٹ بنا رہا ہوں:
            # ----------------------------------------------------
            
            # مثال کے طور پر نام نکالنا (اگر آپ کے پاس ٹیگ کا پتا ہو)
            company_name_tag = soup.find('h2') # یا جو بھی ٹیگ آپ ڈھونڈ رہے تھے
            company_name = company_name_tag.text.strip() if company_name_tag else "Not Found"
            
            return {
                "USDOT": dot_number,
                "Company Name": company_name,
                "Status": "Success"
            }
        else:
            return {"USDOT": dot_number, "Company Name": "Blocked/Error", "Status": f"HTTP {response.status_code}"}
            
    except Exception as e:
        return {"USDOT": dot_number, "Company Name": "Failed to Connect", "Status": str(e)}

# جب یوزر اسٹارٹ بٹن دبائے
if start_btn:
    # ڈاٹ نمبرز کو الگ کرنا
    dot_numbers = [d.strip() for d in re.split(r'[\s,]+', user_input) if d.strip()]
    
    if not dot_numbers:
        st.warning("بھرائے مہربانی پہلے USDOT نمبرز درج کریں۔")
    else:
        st.write("### 📊 Extracted Data:")
        
        # ڈیٹا دکھانے کے لیے ایک خالی ٹیبل بنانا
        results_table = st.empty()
        all_results = []
        
        progress_bar = st.progress(0)
        
        # لوپ چلا کر ایک ایک کر کے ڈیٹا نکالنا
        for index, dot in enumerate(dot_numbers):
            with st.spinner(f"Scraping DOT: {dot}..."):
                res = scrape_dot_data(dot)
                all_results.append(res)
                
                # ٹیبل کو ریئل ٹائم اپڈیٹ کرنا
                results_table.dataframe(all_results)
                
            # پروگریس بار اپڈیٹ کرنا
            progress_bar.progress((index + 1) / len(dot_numbers))
            
        st.success("Scraping complete! 🎉")
