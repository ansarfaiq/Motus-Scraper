import re
import sys
import os
import csv
import pandas as pd
from bs4 import BeautifulSoup
import streamlit as st

# اسٹریم لٹ پیج کی بنیادی سیٹنگز
st.set_page_config(page_title="Motus DOT Data Scraper", page_icon="🚚", layout="wide")

# پلے رائٹ کو کلاؤڈ پر خود بخود بیک اینڈ پر انسٹال کرنے کا فکسڈ طریقہ
@st.cache_resource
def initialize_playwright():
    with st.spinner("Initializing background settings... Please wait."):
        # یہ کلاؤڈ کے اندر ہی پلے رائٹ اور اس کا کرومیم شیل ڈاؤن لوڈ کر دے گا
        os.system("python -m playwright install chromium")
        os.system("python -m playwright install-deps")

# ایپ چلتے ہی یہ سیٹنگ بیک اینڈ پر کنفیگر ہو جائے گی
initialize_playwright()

# پلے رائٹ کو اب امپورٹ کریں گے تاکہ اوپر انسٹالیشن پہلے مکمل ہو جائے
from playwright.sync_api import sync_playwright

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

# پلے رائٹ کے ذریعے سیکیور پورٹل سے ڈیٹا نکالنے والا اصل فنکشن
def scrape_motus_dot_data(dot_number):
    url = f"https://motus.dot.gov/customer/{dot_number}/account" 
    
    try:
        with sync_playwright() as p:
            # ہیڈ لیس براؤزر لانچ کرنا (بغیر نو سینڈ باکس کے کلاؤڈ پر بلاک ہو جاتا ہے)
            browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-setuid-sandbox"])
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            
            # پیج پر جانا اور نیٹ ورک کے پرسکون ہونے کا انتظار کرنا
            page.goto(url, timeout=45000, wait_until="networkidle")
            
            # 5 سیکنڈ کا اضافی انتظار تاکہ جاوا اسکرپٹ کا ڈیٹا لوڈ ہو جائے
            page.wait_for_timeout(5000)
            
            html = page.content()
            soup = BeautifulSoup(html, 'html.parser')
            browser.close()
            
            company_name = "Not Found"
            phone = "Not Found"
            email = "Not Found"
            status = "Active"
            
            # 1. اسٹیٹس نکالنا (Active / Inactive)
            if "Inactive" in html or "OOS" in html:
                status = "Inactive"
            elif "Active" in html:
                status = "Active"
            
            # 2. اسکرین شاٹ کے مطابق ٹیبل کا ڈیٹا نکالنا
            # ہم پورے پیج کے تمام TD اور TH ایلیمنٹس کو اسکین کریں گے
            cells = soup.find_all(["td", "th", "span", "div"])
            for cell in cells:
                text = cell.text.strip()
                
                if "Legal Business Name" in text:
                    nxt = cell.find_next()
                    if nxt: company_name = nxt.text.strip()
                    
                if "Business Telephone No." in text:
                    nxt = cell.find_next()
                    if nxt: phone = nxt.text.strip()
                    
                if "Business Email" in text:
                    nxt = cell.find_next()
                    if nxt: email = nxt.text.strip()
            
            # بیک اپ طریقہ: اگر اوپر سے نہ ملے تو پورے پیج کے ٹیکسٹ سے نکالنا
            if company_name == "Not Found":
                match = re.search(r'Legal Business Name\s+(.*)', soup.text)
                if match: company_name = match.group(1).split('\n')[0].strip()
                
            if phone == "Not Found":
                match = re.search(r'Business Telephone No\.\s+(.*)', soup.text)
                if match: phone = match.group(1).split('\n')[0].strip()
                
            if email == "Not Found":
                match = re.search(r'Business Email\s+(.*)', soup.text)
                if match: email = match.group(1).split('\n')[0].strip()

            return {
                "USDOT": dot_number,
                "Company Name": company_name,
                "Phone": phone,
                "Email": email,
                "Status": status
            }
            
    except Exception as e:
        return {
            "USDOT": dot_number,
            "Company Name": "Error/Blocked",
            "Phone": "N/A",
            "Email": "N/A",
            "Status": f"Failed: {str(e)[:20]}"
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
            with st.spinner(f"Scraping DOT from Motus Portal: {dot}..."):
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
            file_name="motus_portal_data.csv",
            mime="text/csv",
            type="primary"
        )
