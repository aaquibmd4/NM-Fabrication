import streamlit as st
import sqlite3
import pandas as pd
from fpdf import FPDF
from datetime import datetime
import os
import json
import urllib.parse
import base64

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('nm_database.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row 
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS sites 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, site_name TEXT, phone TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS bills 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, site_name TEXT, bill_title TEXT, 
                  date TEXT, total REAL, items TEXT, advance REAL, balance REAL)''')
    conn.commit()
    return conn

conn = init_db()

# --- PDF GENERATION ---
class NM_PDF(FPDF):
    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=False)

    def header(self):
        logo_path = r'D:\NM\logo.png'
        if os.path.exists(logo_path):
            self.image(logo_path, 10, 12, h=40)
        
        self.set_xy(55, 20)
        self.set_font('Arial', 'B', 24)
        self.set_text_color(0, 51, 102)
        self.cell(0, 10, 'NM Fabrication', 0, 1, 'L')
        
        self.set_x(55)
        self.set_font('Arial', '', 9)
        self.set_text_color(80, 80, 80)
        self.cell(0, 5, 'Aazad Nagar, Gandhi Market Main Road, Malegaon. (Nashik) 423203', 0, 1, 'L')
        
        self.set_x(55)
        self.set_font('Arial', 'B', 10)
        self.set_text_color(0, 0, 0)
        self.cell(0, 7, 'Contact: IMRAN NM  |  +91 7972068835', 0, 1, 'L')
        
        self.set_draw_color(0, 51, 102)
        self.line(10, 58, 200, 58)
        self.set_y(65)

def generate_nm_pdf(site_name, bill_title, items_df, g_total, advance, balance):
    pdf = NM_PDF()
    pdf.add_page()
    current_date = datetime.now().strftime('%d-%m-%Y')
    
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(130, 8, txt=f"Site: {site_name}", ln=0)
    pdf.set_font("Arial", '', 10)
    pdf.cell(0, 8, txt=f"Date: {current_date}", ln=1, align='R')
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(0, 8, txt=f"Bill Title: {bill_title}", ln=1)
    
    pdf.set_fill_color(0, 51, 102) 
    pdf.set_text_color(255, 255, 255)
    pdf.cell(75, 10, " Item", 1, 0, 'L', True)
    pdf.cell(20, 10, "Nos", 1, 0, 'C', True)
    pdf.cell(30, 10, "Qty", 1, 0, 'C', True)
    pdf.cell(30, 10, "Rate", 1, 0, 'C', True)
    pdf.cell(35, 10, "Total", 1, 1, 'C', True)
    
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", size=10)
    for _, row in items_df.iterrows():
        n, q, r = row.get('Nos', 0), row.get('Qty', 0), row.get('Rate', 0)
        pdf.cell(75, 9, f" {row.get('Item','')}", 1, 0, 'L')
        pdf.cell(20, 9, str(int(n)) if n > 0 else "-", 1, 0, 'C')
        pdf.cell(30, 9, f"{q} {row.get('Unit','-')}" if q > 0 else "-", 1, 0, 'C')
        pdf.cell(30, 9, f"{r:.2f}", 1, 0, 'C')
        amt = q*r if q>0 else (n*r if n>0 else r)
        pdf.cell(35, 9, f"{amt:.2f}", 1, 1, 'C')
    
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(155, 8, "Grand Total: ", 0, 0, 'R')
    pdf.cell(35, 8, f"{g_total:.2f}", 1, 1, 'C')
    pdf.set_text_color(0, 128, 0)
    pdf.cell(155, 8, "Advance Paid: ", 0, 0, 'R')
    pdf.cell(35, 8, f"{advance:.2f}", 1, 1, 'C')
    pdf.set_text_color(200, 0, 0)
    pdf.cell(155, 8, "Balance Due: ", 0, 0, 'R')
    pdf.cell(35, 8, f"{balance:.2f}", 1, 1, 'C')

    footer_y = 230 
    qr_path = r'D:\NM\qr.png'
    if os.path.exists(qr_path):
        pdf.image(qr_path, 15, footer_y, h=40) 
        pdf.set_xy(15, footer_y + 42)
        pdf.set_font("Arial", 'B', 9)
        pdf.cell(40, 5, "Scan to Pay", 0, 0, 'C')

    sig_path = r'D:\NM\signature.png'
    if os.path.exists(sig_path):
        pdf.image(sig_path, 168, footer_y - 2, h=28) 
        pdf.set_xy(155, footer_y + 28)
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(40, 5, "________________", 0, 1, 'R')
        pdf.set_x(155)
        pdf.cell(40, 5, "For NM Fabrication", 0, 1, 'R')

    return bytes(pdf.output())

# --- UTILS ---
def show_pdf(bytes_data):
    base64_pdf = base64.b64encode(bytes_data).decode('utf-8')
    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="600" type="application/pdf"></iframe>'
    st.markdown(pdf_display, unsafe_allow_html=True)

# --- NAVIGATION ---
if "page" not in st.session_state: st.session_state.page = "Dashboard"
if "history" not in st.session_state: st.session_state.history = ["Dashboard"]

def go_to(page, site=None, bill_id=None):
    st.session_state.history.append(st.session_state.page)
    st.session_state.page = page
    if site: st.session_state.selected_site = site
    if bill_id: st.session_state.edit_bill_id = bill_id
    st.rerun()

def go_back():
    if len(st.session_state.history) > 0:
        st.session_state.page = st.session_state.history.pop()
        st.rerun()

# --- APP UI ---
st.set_page_config(page_title="NM Fabrication", page_icon="⚒️", layout="centered")

# Custom Back/Home Nav
if st.session_state.page != "Dashboard":
    c1, c2 = st.columns([1, 5])
    if c1.button("⬅️ Back"): go_back()
    if c2.button("🏠 Home"): 
        st.session_state.history = ["Dashboard"]
        go_to("Dashboard")

if st.session_state.page == "Dashboard":
    # Logo and Title Center Aligned
    logo_path = r'D:\NM\logo.png'
    if os.path.exists(logo_path):
        # Bada logo display karne ke liye width badha di hai
        st.image(logo_path, width=250)
    
    st.title("NM Fabrication")
    st.divider()
    
    if st.button("📝 Create New Bill", use_container_width=True): go_to("Add New Bill")
    if st.button("📂 View All Bills", use_container_width=True): go_to("Bills")
    if st.button("🏗️ Site Directory", use_container_width=True): go_to("Site List")
    if st.button("➕ Add New Site", use_container_width=True): go_to("Add New Site")

elif st.session_state.page == "Add New Site":
    st.header("➕ Register Site")
    s_name = st.text_input("Customer/Site Name")
    s_phone = st.text_input("WhatsApp Number")
    if st.button("💾 Save Site"):
        if s_name:
            conn.cursor().execute("INSERT INTO sites (site_name, phone) VALUES (?,?)", (s_name, s_phone))
            conn.commit()
            st.success("Site Saved!")
            go_to("Site List")

elif st.session_state.page == "Site List":
    st.header("🏗️ Site Directory")
    sites = pd.read_sql_query("SELECT * FROM sites", conn)
    for _, s in sites.iterrows():
        with st.container(border=True):
            col1, col2, col3 = st.columns([3, 1, 1])
            if col1.button(f"📁 {s['site_name']}", key=f"site_btn_{s['id']}", use_container_width=True):
                go_to("Bills", site=s['site_name'])
            if col2.button("✏️", key=f"edit_s_{s['id']}"):
                st.session_state.edit_site_id = s['id']
                go_to("Edit Site")
            if col3.button("🗑️", key=f"del_s_{s['id']}"):
                conn.cursor().execute("DELETE FROM sites WHERE id=?", (s['id'],))
                conn.commit()
                st.rerun()

elif st.session_state.page == "Edit Site":
    st.header("✏️ Edit Site")
    site_id = st.session_state.get('edit_site_id')
    site_data = conn.cursor().execute("SELECT * FROM sites WHERE id=?", (site_id,)).fetchone()
    new_name = st.text_input("Name", value=site_data['site_name'])
    new_phone = st.text_input("Phone", value=site_data['phone'])
    if st.button("Update"):
        conn.cursor().execute("UPDATE sites SET site_name=?, phone=? WHERE id=?", (new_name, new_phone, site_id))
        conn.commit()
        go_back()

elif st.session_state.page == "Bills":
    target = st.session_state.get('selected_site')
    st.header(f"📂 Bills: {target if target else 'All'}")
    query = "SELECT * FROM bills WHERE site_name=? ORDER BY id DESC" if target else "SELECT * FROM bills ORDER BY id DESC"
    bills = pd.read_sql_query(query, conn, params=(target,) if target else ())
    
    for _, b in bills.iterrows():
        with st.expander(f"📄 {b['bill_title']} ({b['date']})"):
            st.write(f"**Total: ₹{b['total']} | Balance: ₹{b['balance']}**")
            
            c1, c2, c3, c4 = st.columns(4)
            items_list = json.loads(b['items'])
            pdf_bytes = generate_nm_pdf(b['site_name'], b['bill_title'], pd.DataFrame(items_list), b['total'], b['advance'], b['balance'])
            
            if c1.button("👁️ View", key=f"v_{b['id']}"):
                show_pdf(pdf_bytes)
            
            c2.download_button("📥 PDF", data=pdf_bytes, file_name=f"Bill_{b['id']}.pdf", key=f"dl_{b['id']}")
            
            if c3.button("✏️ Edit", key=f"ed_b_{b['id']}"):
                st.session_state.rows = items_list
                go_to("Add New Bill", site=b['site_name'], bill_id=b['id'])
                
            if c4.button("🗑️ Delete", key=f"del_b_{b['id']}"):
                conn.cursor().execute("DELETE FROM bills WHERE id=?", (b['id'],))
                conn.commit()
                st.rerun()

elif st.session_state.page == "Add New Bill":
    edit_id = st.session_state.get('edit_bill_id')
    st.header("✏️ Edit Bill" if edit_id else "📝 New Bill")
    
    sites_df = pd.read_sql_query("SELECT site_name FROM sites", conn)
    s_choice = st.selectbox("Site", sites_df['site_name'].tolist())
    
    if edit_id and 'rows' not in st.session_state:
        bill_data = conn.cursor().execute("SELECT * FROM bills WHERE id=?", (edit_id,)).fetchone()
        st.session_state.rows = json.loads(bill_data['items'])
        b_title_val = bill_data['bill_title']
        adv_val = bill_data['advance']
    elif 'rows' not in st.session_state:
        st.session_state.rows = [{"Item": "", "Nos": 0, "Qty": 0.0, "Unit": "Kg", "Rate": 0.0}]
        b_title_val = ""
        adv_val = 0.0
    else:
        b_title_val = ""
        adv_val = 0.0

    b_title = st.text_input("Bill Title", value=b_title_val)

    grand_total = 0
    for i, row in enumerate(st.session_state.rows):
        with st.container(border=True):
            st.session_state.rows[i]['Item'] = st.text_input("Item", value=row['Item'], key=f"it_{i}")
            c1, c2, c3, c4 = st.columns([1,1,1,2])
            st.session_state.rows[i]['Nos'] = c1.number_input("Nos", value=int(row['Nos']), key=f"n_{i}")
            st.session_state.rows[i]['Qty'] = c2.number_input("Qty", value=float(row['Qty']), key=f"q_{i}")
            st.session_state.rows[i]['Unit'] = c3.selectbox("Unit", ["Kg", "R feet", "Sq. feet", "-"], index=["Kg", "R feet", "Sq. feet", "-"].index(row['Unit']), key=f"u_{i}")
            st.session_state.rows[i]['Rate'] = c4.number_input("Rate", value=float(row['Rate']), key=f"r_{i}")
            
            q, n, r = st.session_state.rows[i]['Qty'], st.session_state.rows[i]['Nos'], st.session_state.rows[i]['Rate']
            amt = q * r if q > 0 else (n * r if n > 0 else r)
            grand_total += amt
            st.write(f"Item Total: ₹{amt:.2f}")

    if st.button("➕ Add Item"):
        st.session_state.rows.append({"Item": "", "Nos": 0, "Qty": 0.0, "Unit": "Kg", "Rate": 0.0})
        st.rerun()

    st.divider()
    adv = st.number_input("Advance Paid", value=adv_val)
    bal = grand_total - adv
    st.subheader(f"Grand Total: ₹{grand_total:.2f} | Balance: ₹{bal:.2f}")

    if st.button("💾 SAVE BILL", use_container_width=True):
        bill_date = datetime.now().strftime("%d-%m-%Y")
        items_json = json.dumps(st.session_state.rows)
        if edit_id:
            conn.cursor().execute("UPDATE bills SET site_name=?, bill_title=?, total=?, items=?, advance=?, balance=? WHERE id=?",
                                  (s_choice, b_title, grand_total, items_json, adv, bal, edit_id))
        else:
            conn.cursor().execute("INSERT INTO bills (site_name, bill_title, date, total, items, advance, balance) VALUES (?,?,?,?,?,?,?)",
                                  (s_choice, b_title, bill_date, grand_total, items_json, adv, bal))
        conn.commit()
        if 'rows' in st.session_state: del st.session_state.rows
        if 'edit_bill_id' in st.session_state: del st.session_state.edit_bill_id
        go_to("Bills", site=s_choice)