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

# اسکرین شاٹ کے مطابق بالکل فکسڈ ڈیٹا نکالنے والا فنکشن
def scrape_motus_dot_data(dot_number):
    url = f"https://motus.dot.gov/customer/{dot_number}/account" 
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            company_name = "Not Found"
            phone = "Not Found"
            email = "Not Found"
            status = "Active"
            
            # 1. اسٹیٹس نکالنا (USDOT #6553522 - Active والی لائن سے)
            main_heading = soup.find(text=re.compile(r'USDOT\s*#'))
            if not main_heading:
                # متبادل اگر وہ کسی ٹیگ کے اندر ہو
                for tag in soup.find_all(['h2', 'h3', 'div']):
                    if "USDOT #" in tag.text:
                        main_heading = tag.text
                        break
            
            if main_heading and "Inactive" in str(main_heading):
                status = "Inactive"
            elif main_heading and "Active" in str(main_heading):
                status = "Active"

            # 2. ٹیبل کے اندر سے مخصوص فیلڈز (Name, Phone, Email) نکالنا
            # ہم پورے پیج کے تمام <td> یا <th> ٹیگز کو چیک کریں گے
            all_cells = soup.find_all(["td", "th", "div"])
            
            for i, cell in enumerate(all_results := all_cells):
                cell_text = cell.text.strip()
                
                # کمپنی کا نام نکالنا
                if "Legal Business Name" in cell_text:
                    # اس سے اگلا والا سیل یا اس کے اندر کا ٹیکسٹ ڈیٹا ہوگا
                    next_sibling = cell.find_next()
                    if next_sibling:
                        company_name = next_sibling.text.strip()
                
                # فون نمبر نکالنا
                if "Business Telephone No." in cell_text:
                    next_sibling = cell.find_next()
                    if next_sibling:
                        phone = next_sibling.text.strip()
                
                # ای میل نکالنا
                if "Business Email" in cell_text:
                    next_sibling = cell.find_next()
                    if next_sibling:
                        email = next_sibling.text.strip()

            # اگر اوپر والے طریقے سے نہ ملے تو ڈائریکٹ ٹیکسٹ سرچ کا متبادل (Backup Match)
            if company_name == "Not Found" or phone == "Not Found" or email == "Not Found":
                for row in soup.find_all(["tr", "div"]):
                    row_text = row.text.strip()
                    if "Legal Business Name" in row_text and company_name == "Not Found":
                        company_name = row_text.replace("Legal Business Name", "").strip()
                    if "Business Telephone No." in row_text and phone == "Not Found":
                        phone = row_text.replace("Business Telephone No.", "").strip()
                    if "Business Email" in row_text and email == "Not Found":
                        email = row_text.replace("Business Email", "").strip()

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
