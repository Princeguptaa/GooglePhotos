import os
import math
from PIL import Image, ImageDraw, ImageFont

def get_font(name="arial.ttf", size=20, bold=False):
    font_paths = [
        os.path.join(r"C:\Windows\Fonts", "arialbd.ttf" if bold else "arial.ttf"),
        os.path.join(r"C:\Windows\Fonts", "calibrib.ttf" if bold else "calibri.ttf"),
        os.path.join(r"C:\Windows\Fonts", "segoeuib.ttf" if bold else "segoeui.ttf"),
        name
    ]
    for path in font_paths:
        try:
            return ImageFont.truetype(path, size)
        except (IOError, OSError):
            continue
    return ImageFont.load_default()

def draw_rounded_rect(draw, bbox, radius, fill=None, outline=None, width=1):
    draw.rounded_rectangle(bbox, radius=radius, fill=fill, outline=outline, width=width)

def draw_qr_code(draw, pos, size=90):
    x, y = pos
    draw.rectangle([x, y, x + size, y + size], fill=(255, 255, 255), outline=(40, 40, 40), width=2)
    step = size // 9
    for i in range(1, 8):
        for j in range(1, 8):
            if (i in [1, 2, 6, 7] and j in [1, 2, 6, 7]) or ((i * 3 + j * 5) % 2 == 0):
                draw.rectangle([x + i * step, y + j * step, x + (i + 1) * step - 1, y + (j + 1) * step - 1], fill=(20, 20, 20))

def draw_barcode(draw, pos, width=180, height=45):
    x, y = pos
    cur_x = x
    while cur_x < x + width:
        bar_w = 2 if (cur_x % 5 == 0 or cur_x % 7 == 0) else 1
        draw.rectangle([cur_x, y, cur_x + bar_w, y + height], fill=(30, 30, 30))
        cur_x += bar_w + (2 if cur_x % 3 == 0 else 1)

def draw_avatar(draw, pos, size=(90, 110)):
    x, y = pos
    w, h = size
    draw.rectangle([x, y, x + w, y + h], fill=(220, 230, 242), outline=(150, 165, 185), width=2)
    # Head
    head_r = w // 4
    head_cx = x + w // 2
    head_cy = y + h // 3 + 4
    draw.ellipse([head_cx - head_r, head_cy - head_r, head_cx + head_r, head_cy + head_r], fill=(130, 145, 165))
    # Shoulders
    draw.chord([x + 10, y + h // 2, x + w - 10, y + h + 20], 180, 360, fill=(130, 145, 165))

def generate_aadhaar_card(filepath, name, dob, no_str, full_ocr_text):
    W, H = 820, 520
    img = Image.new('RGB', (W, H), color=(242, 244, 247))
    draw = ImageDraw.Draw(img)

    # Card shadow & body
    draw_rounded_rect(draw, [25, 20, W - 25, H - 20], radius=16, fill=(255, 255, 255), outline=(205, 212, 222), width=2)

    # Tricolor header bar
    draw.rectangle([27, 22, W - 27, 34], fill=(255, 153, 51))
    draw.rectangle([27, 34, W - 27, 44], fill=(255, 255, 255))
    draw.rectangle([27, 44, W - 27, 56], fill=(19, 136, 8))

    # Gov header text
    f_title = get_font(size=18, bold=True)
    f_sub = get_font(size=14, bold=False)
    draw.text((60, 68), "Government of India", fill=(30, 41, 59), font=f_title)
    draw.text((60, 92), "Unique Identification Authority of India (UIDAI)", fill=(100, 116, 139), font=f_sub)

    # Decorative blue emblem circle
    draw.ellipse([W - 110, 64, W - 60, 114], fill=(234, 242, 255), outline=(59, 130, 246), width=2)
    f_emblem = get_font(size=12, bold=True)
    draw.text((W - 100, 82), "UIDAI", fill=(37, 99, 235), font=f_emblem)

    # Thin separator line
    draw.line([45, 126, W - 45, 126], fill=(226, 232, 240), width=2)

    # Avatar
    draw_avatar(draw, (60, 150), size=(110, 135))

    # Card info
    f_label = get_font(size=13, bold=False)
    f_val = get_font(size=17, bold=True)

    draw.text((195, 150), "Aadhaar Card", fill=(180, 83, 9), font=get_font(size=14, bold=True))

    draw.text((195, 180), "Name:", fill=(100, 116, 139), font=f_label)
    draw.text((195, 200), name, fill=(15, 23, 42), font=f_val)

    draw.text((195, 235), "DOB:", fill=(100, 116, 139), font=f_label)
    draw.text((195, 255), dob, fill=(15, 23, 42), font=f_val)

    draw.text((195, 290), "Gender: Male", fill=(71, 85, 105), font=f_label)

    # QR Code on right
    draw_qr_code(draw, (W - 190, 155), size=120)

    # Red divider bar
    draw.rectangle([45, 360, W - 45, 366], fill=(220, 38, 38))

    # Aadhaar Number in big bold font
    f_num = get_font(size=30, bold=True)
    draw.text((60, 385), no_str, fill=(220, 38, 38), font=f_num)

    f_caption = get_font(size=14, bold=False)
    draw.text((60, 435), "Aadhaar — Unique Identification Authority of India (Proof of Identity)", fill=(71, 85, 105), font=f_caption)

    # Full searchable OCR text footprint in high-contrast clean baseline
    f_ocr = get_font(size=11, bold=False)
    draw.text((60, 470), full_ocr_text, fill=(148, 163, 184), font=f_ocr)

    img.save(filepath, quality=95)

def generate_payment_receipt(filepath, recipient, amount_str, date_str, ref_str, full_ocr_text):
    W, H = 720, 860
    img = Image.new('RGB', (W, H), color=(241, 245, 249))
    draw = ImageDraw.Draw(img)

    # Card container
    draw_rounded_rect(draw, [35, 30, W - 35, H - 30], radius=18, fill=(255, 255, 255), outline=(218, 224, 233), width=2)

    # Top green success icon
    draw.ellipse([W // 2 - 38, 65, W // 2 + 38, 141], fill=(16, 185, 129))
    cx, cy = W // 2, 103
    draw.line([(cx - 15, cy - 1), (cx - 4, cy + 11)], fill=(255, 255, 255), width=5)
    draw.line([(cx - 4, cy + 11), (cx + 17, cy - 12)], fill=(255, 255, 255), width=5)

    # Success title
    f_succ = get_font(size=20, bold=True)
    draw.text((W // 2 - 95, 155), "Payment Successful", fill=(15, 23, 42), font=f_succ)

    # Big Amount
    f_amt = get_font(size=42, bold=True)
    clean_amt = amount_str.replace("Rs ", "₹").replace("Amount: ", "")
    amt_text = clean_amt if clean_amt.startswith("₹") else f"₹{clean_amt}"
    draw.text((W // 2 - 80, 195), amt_text, fill=(15, 23, 42), font=f_amt)

    # "Paid to" recipient
    f_to = get_font(size=16, bold=False)
    f_name = get_font(size=20, bold=True)
    draw.text((W // 2 - 30, 260), "Paid to", fill=(100, 116, 139), font=f_to)
    draw.text((W // 2 - len(recipient) * 6, 285), recipient, fill=(15, 23, 42), font=f_name)

    # Dashed divider
    for x in range(65, W - 65, 14):
        draw.line([x, 335, x + 8, 335], fill=(203, 213, 225), width=2)

    # Transaction details container
    draw_rounded_rect(draw, [65, 360, W - 65, 680], radius=12, fill=(248, 250, 252), outline=(226, 232, 240), width=1)

    details = [
        ("Transaction Type:", "Payment Receipt"),
        ("Paid To:", recipient),
        ("Amount:", amount_str if "Rs" in amount_str else f"Rs {amount_str}"),
        ("Date & Time:", f"{date_str}, 02:45 PM"),
        ("Transaction Ref:", ref_str),
        ("Payment Mode:", "UPI / Bank Transfer"),
        ("Status:", "Completed (Verified)")
    ]

    f_dlabel = get_font(size=14, bold=False)
    f_dval = get_font(size=15, bold=True)
    y_pos = 385
    for lbl, val in details:
        draw.text((90, y_pos), lbl, fill=(100, 116, 139), font=f_dlabel)
        draw.text((270, y_pos), val, fill=(30, 41, 59), font=f_dval)
        y_pos += 40

    # Barcode & footer
    draw_barcode(draw, (W // 2 - 90, 705), width=180, height=40)
    f_foot = get_font(size=13, bold=False)
    draw.text((W // 2 - 110, 755), "Unified Payments Interface (UPI)", fill=(100, 116, 139), font=f_foot)

    # Full searchable OCR text
    f_ocr = get_font(size=11, bold=False)
    draw.text((65, 795), full_ocr_text, fill=(148, 163, 184), font=f_ocr)

    img.save(filepath, quality=95)

def generate_prescription(filepath, patient, doctor, meds, full_ocr_text):
    W, H = 750, 960
    img = Image.new('RGB', (W, H), color=(245, 247, 250))
    draw = ImageDraw.Draw(img)

    # Pad body
    draw_rounded_rect(draw, [30, 25, W - 30, H - 25], radius=14, fill=(255, 255, 255), outline=(218, 224, 233), width=2)

    # Clinic Header
    draw.rectangle([32, 27, W - 32, 135], fill=(13, 148, 136))
    cx, cy = 68, 70
    draw.rectangle([cx - 4, cy - 18, cx + 4, cy + 18], fill=(255, 255, 255))
    draw.rectangle([cx - 18, cy - 4, cx + 18, cy + 4], fill=(255, 255, 255))

    f_clinic = get_font(size=22, bold=True)
    draw.text((105, 45), "CAREWELL MULTISPECIALTY CLINIC", fill=(255, 255, 255), font=f_clinic)

    f_doc = get_font(size=17, bold=True)
    f_deg = get_font(size=13, bold=False)
    draw.text((105, 78), doctor, fill=(204, 251, 241), font=f_doc)
    draw.text((105, 102), "MBBS, MD (General Medicine) | Reg No: DMC-48291", fill=(204, 251, 241), font=f_deg)

    # Patient info box
    draw.rectangle([50, 155, W - 50, 225], fill=(240, 253, 250), outline=(204, 251, 241), width=1)
    f_pinfo = get_font(size=15, bold=True)
    f_psub = get_font(size=14, bold=False)
    draw.text((70, 170), f"Prescription — Patient: {patient}", fill=(15, 23, 42), font=f_pinfo)
    draw.text((70, 195), "Age: 36 Yrs | Sex: M | Date: 18 March 2026 | Weight: 68 kg", fill=(71, 85, 105), font=f_psub)

    # Rx symbol
    f_rx = get_font(size=44, bold=True)
    draw.text((70, 245), "Rx", fill=(13, 148, 136), font=f_rx)

    # Medicine List
    f_medtitle = get_font(size=17, bold=True)
    f_meddose = get_font(size=14, bold=False)
    y_med = 310
    for idx, med in enumerate(meds, start=1):
        draw_rounded_rect(draw, [70, y_med, W - 70, y_med + 65], radius=8, fill=(248, 250, 252), outline=(226, 232, 240), width=1)
        draw.text((90, y_med + 12), f"{idx}. Tab. {med}", fill=(15, 23, 42), font=f_medtitle)
        draw.text((90, y_med + 38), "1 tablet twice daily after meals (1-0-1) x 5 days", fill=(100, 116, 139), font=f_meddose)
        y_med += 85

    # Advice
    f_advlabel = get_font(size=15, bold=True)
    f_adv = get_font(size=14, bold=False)
    draw.text((70, y_med + 20), "General Advice:", fill=(15, 23, 42), font=f_advlabel)
    draw.text((70, y_med + 48), "• Drink plenty of warm fluids & rest well.", fill=(71, 85, 105), font=f_adv)
    draw.text((70, y_med + 72), "• Review in OPD after 3 days if symptoms persist.", fill=(71, 85, 105), font=f_adv)

    # Doctor signature seal
    draw.ellipse([W - 240, H - 210, W - 90, H - 90], outline=(37, 99, 235), width=2)
    f_seal = get_font(size=12, bold=True)
    draw.text((W - 225, H - 165), "CAREWELL CLINIC", fill=(37, 99, 235), font=f_seal)
    draw.text((W - 215, H - 145), "VERIFIED & SIGNED", fill=(37, 99, 235), font=f_seal)
    draw.text((W - 220, H - 120), "Dr. Anita Sharma", fill=(37, 99, 235), font=f_seal)

    # Searchable footprint
    f_ocr = get_font(size=11, bold=False)
    draw.text((50, H - 65), full_ocr_text, fill=(148, 163, 184), font=f_ocr)

    img.save(filepath, quality=95)

def generate_invoice(filepath, company, inv_no, date_str, total_str, full_ocr_text):
    W, H = 750, 960
    img = Image.new('RGB', (W, H), color=(243, 244, 246))
    draw = ImageDraw.Draw(img)

    # Body
    draw_rounded_rect(draw, [30, 25, W - 30, H - 25], radius=12, fill=(255, 255, 255), outline=(218, 224, 233), width=2)

    # Header
    f_comp = get_font(size=24, bold=True)
    f_sub = get_font(size=14, bold=False)
    draw.text((55, 45), company, fill=(15, 23, 42), font=f_comp)
    draw.text((55, 78), "Commercial Retail & Business Services | GSTIN: 07AAAAA0000A1Z5", fill=(100, 116, 139), font=f_sub)

    # Title
    f_title = get_font(size=20, bold=True)
    draw.text((W - 200, 45), "TAX INVOICE", fill=(37, 99, 235), font=f_title)
    f_inv = get_font(size=14, bold=True)
    draw.text((W - 200, 75), f"Invoice {inv_no}", fill=(71, 85, 105), font=f_inv)

    draw.line([50, 115, W - 50, 115], fill=(226, 232, 240), width=2)

    # Meta
    f_lbl = get_font(size=13, bold=False)
    f_v = get_font(size=15, bold=True)
    draw.text((55, 135), "Bill To:", fill=(100, 116, 139), font=f_lbl)
    draw.text((55, 155), "Customer Order / Account", fill=(15, 23, 42), font=f_v)

    draw.text((W - 240, 135), "Billing Date:", fill=(100, 116, 139), font=f_lbl)
    draw.text((W - 240, 155), f"{date_str} 2026", fill=(15, 23, 42), font=f_v)

    # Items Table
    draw.rectangle([50, 200, W - 50, 240], fill=(241, 245, 249))
    f_th = get_font(size=14, bold=True)
    draw.text((65, 212), "Description", fill=(51, 65, 85), font=f_th)
    draw.text((380, 212), "Qty", fill=(51, 65, 85), font=f_th)
    draw.text((470, 212), "Rate", fill=(51, 65, 85), font=f_th)
    draw.text((W - 140, 212), "Amount", fill=(51, 65, 85), font=f_th)

    items = [
        ("Cloud Infrastructure / Goods Supply", "1", total_str, total_str),
        ("Standard Maintenance & Support", "1", "Included", "0.00"),
        ("Taxes & Surcharges (GST 18%)", "—", "Included", "0.00")
    ]
    y_row = 260
    f_td = get_font(size=14, bold=False)
    for desc, qty, rate, amt in items:
        draw.text((65, y_row), desc, fill=(30, 41, 59), font=f_td)
        draw.text((385, y_row), qty, fill=(30, 41, 59), font=f_td)
        draw.text((470, y_row), rate, fill=(30, 41, 59), font=f_td)
        draw.text((W - 140, y_row), amt, fill=(30, 41, 59), font=f_td)
        draw.line([50, y_row + 30, W - 50, y_row + 30], fill=(241, 245, 249), width=1)
        y_row += 45

    # Total Box
    draw_rounded_rect(draw, [W - 320, 480, W - 50, 560], radius=8, fill=(238, 242, 255), outline=(199, 210, 254), width=2)
    f_totlabel = get_font(size=14, bold=False)
    f_totval = get_font(size=24, bold=True)
    draw.text((W - 300, 492), "Grand Total Amount:", fill=(67, 56, 202), font=f_totlabel)
    draw.text((W - 300, 516), f"Total: {total_str}", fill=(67, 56, 202), font=f_totval)

    # Barcode
    draw_barcode(draw, (65, 500), width=200, height=45)
    f_bar = get_font(size=12, bold=False)
    draw.text((65, 555), f"Auth Reference: {inv_no}", fill=(100, 116, 139), font=f_bar)

    # Signatory stamp
    draw.rectangle([W - 250, 680, W - 70, 760], outline=(203, 213, 225), width=1)
    f_sig = get_font(size=12, bold=False)
    draw.text((W - 235, 735), "Authorized Signatory", fill=(100, 116, 139), font=f_sig)

    # Searchable footprint
    f_ocr = get_font(size=11, bold=False)
    draw.text((50, H - 65), full_ocr_text, fill=(148, 163, 184), font=f_ocr)

    img.save(filepath, quality=95)

def generate_marksheet(filepath, student, roll_no, cgpa, full_ocr_text):
    W, H = 750, 960
    img = Image.new('RGB', (W, H), color=(245, 245, 245))
    draw = ImageDraw.Draw(img)

    # Formal border
    draw_rounded_rect(draw, [25, 20, W - 25, H - 20], radius=8, fill=(255, 255, 255), outline=(153, 27, 27), width=3)
    draw_rounded_rect(draw, [32, 27, W - 32, H - 27], radius=6, fill=None, outline=(220, 38, 38), width=1)

    # University header
    f_uni = get_font(size=24, bold=True)
    f_sub = get_font(size=15, bold=True)
    f_sm = get_font(size=13, bold=False)

    draw.text((W // 2 - 145, 55), "UNIVERSITY OF DELHI", fill=(153, 27, 27), font=f_uni)
    draw.text((W // 2 - 40, 88), "ESTD. 1922", fill=(153, 27, 27), font=f_sm)
    draw.text((W // 2 - 165, 120), "STATEMENT OF MARKS / GRADE CARD", fill=(30, 41, 59), font=f_sub)
    draw.text((W // 2 - 120, 145), "Semester Examination 2025-2026", fill=(100, 116, 139), font=f_sm)

    draw.line([60, 180, W - 60, 180], fill=(203, 213, 225), width=2)

    # Student metadata
    f_lbl = get_font(size=14, bold=False)
    f_val = get_font(size=16, bold=True)

    draw.text((70, 200), "Semester Mark Sheet", fill=(180, 83, 9), font=f_val)
    draw.text((70, 235), "Student Name:", fill=(100, 116, 139), font=f_lbl)
    draw.text((180, 235), student, fill=(15, 23, 42), font=f_val)

    draw.text((70, 270), "Roll No:", fill=(100, 116, 139), font=f_lbl)
    draw.text((180, 270), roll_no, fill=(15, 23, 42), font=f_val)

    draw.text((W - 270, 235), "Course: B.Tech (CS)", fill=(51, 65, 85), font=f_lbl)
    draw.text((W - 270, 270), "Session: 2024-2026", fill=(51, 65, 85), font=f_lbl)

    # Grade Table
    draw.rectangle([60, 315, W - 60, 355], fill=(241, 245, 249))
    f_th = get_font(size=14, bold=True)
    draw.text((80, 326), "Paper Code & Subject", fill=(30, 41, 59), font=f_th)
    draw.text((420, 326), "Credits", fill=(30, 41, 59), font=f_th)
    draw.text((510, 326), "Grade", fill=(30, 41, 59), font=f_th)
    draw.text((600, 326), "Points", fill=(30, 41, 59), font=f_th)

    courses = [
        ("CS-301 Data Structures & Algorithms", "4", "A+", "10"),
        ("CS-302 Database Management Systems", "4", "A", "9"),
        ("CS-303 Operating Systems & Architecture", "4", "A", "9"),
        ("CS-304 Computer Networks & Protocols", "4", "B+", "8"),
        ("CS-305 Software Engineering Lab", "2", "A+", "10")
    ]
    y_crs = 375
    f_td = get_font(size=14, bold=False)
    for cname, cr, gr, pt in courses:
        draw.text((80, y_crs), cname, fill=(51, 65, 85), font=f_td)
        draw.text((435, y_crs), cr, fill=(51, 65, 85), font=f_td)
        draw.text((520, y_crs), gr, fill=(51, 65, 85), font=f_td)
        draw.text((615, y_crs), pt, fill=(51, 65, 85), font=f_td)
        draw.line([60, y_crs + 30, W - 60, y_crs + 30], fill=(241, 245, 249), width=1)
        y_crs += 45

    # CGPA Badge
    draw_rounded_rect(draw, [60, y_crs + 30, W - 60, y_crs + 110], radius=10, fill=(254, 242, 242), outline=(252, 165, 165), width=2)
    f_res = get_font(size=22, bold=True)
    draw.text((85, y_crs + 50), f"Result: PASS | CGPA: {cgpa}", fill=(153, 27, 27), font=f_res)
    draw.text((85, y_crs + 80), "Classification: FIRST DIVISION WITH DISTINCTION", fill=(185, 28, 28), font=f_lbl)

    # University seal stamp
    draw.ellipse([W - 220, H - 200, W - 90, H - 70], outline=(153, 27, 27), width=2)
    f_seal = get_font(size=12, bold=True)
    draw.text((W - 195, H - 150), "UNIVERSITY SEAL", fill=(153, 27, 27), font=f_seal)
    draw.text((W - 185, H - 130), "CONTROLLER", fill=(153, 27, 27), font=f_seal)

    # Searchable footprint
    f_ocr = get_font(size=11, bold=False)
    draw.text((50, H - 55), full_ocr_text, fill=(148, 163, 184), font=f_ocr)

    img.save(filepath, quality=95)

def generate_id_card(filepath, name, dept_or_title, emp_id, full_ocr_text):
    W, H = 820, 520
    img = Image.new('RGB', (W, H), color=(241, 245, 249))
    draw = ImageDraw.Draw(img)

    # Card body
    draw_rounded_rect(draw, [25, 20, W - 25, H - 20], radius=16, fill=(255, 255, 255), outline=(203, 213, 225), width=2)

    # Lanyard slot
    draw_rounded_rect(draw, [W // 2 - 35, 30, W // 2 + 35, 45], radius=6, fill=(226, 232, 240), outline=(203, 213, 225), width=1)

    # Header Banner
    draw.rectangle([27, 58, W - 27, 130], fill=(30, 58, 138))
    f_corp = get_font(size=20, bold=True)
    f_corp_sub = get_font(size=13, bold=False)
    draw.text((55, 75), "NEXUS ENTERPRISES GLOBAL", fill=(255, 255, 255), font=f_corp)
    draw.text((55, 102), "EMPLOYEE IDENTITY CARD", fill=(191, 219, 254), font=f_corp_sub)

    # Avatar
    draw_avatar(draw, (60, 160), size=(130, 160))

    # Details
    f_label = get_font(size=13, bold=False)
    f_val = get_font(size=20, bold=True)

    draw.text((225, 160), "Employee ID Card" if "Employee" in full_ocr_text else "ID Card", fill=(37, 99, 235), font=get_font(size=15, bold=True))

    draw.text((225, 195), "Employee Name:", fill=(100, 116, 139), font=f_label)
    draw.text((225, 218), name, fill=(15, 23, 42), font=f_val)

    if dept_or_title:
        draw.text((225, 260), "Department:", fill=(100, 116, 139), font=f_label)
        draw.text((225, 282), dept_or_title, fill=(15, 23, 42), font=get_font(size=17, bold=True))

    draw.text((225, 325), "Employee ID:", fill=(100, 116, 139), font=f_label)
    draw.text((225, 348), emp_id, fill=(30, 58, 138), font=get_font(size=18, bold=True))

    # Barcode
    draw_barcode(draw, (60, 390), width=240, height=45)
    f_bar = get_font(size=12, bold=False)
    draw.text((60, 442), f"SECURITY CARD • {emp_id}", fill=(100, 116, 139), font=f_bar)

    # Searchable footprint
    f_ocr = get_font(size=11, bold=False)
    draw.text((60, 475), full_ocr_text, fill=(148, 163, 184), font=f_ocr)

    img.save(filepath, quality=95)

def main():
    os.makedirs('mock_data', exist_ok=True)

    # 1. Samrat Mehta Aadhaar Card
    generate_aadhaar_card(
        os.path.join('mock_data', 'IMG_20260512_104519.jpg'),
        name="Samrat Mehta",
        dob="12/05/1995",
        no_str="XXXX XXXX 4532",
        full_ocr_text="Aadhaar Card Name: Samrat Mehta DOB: 12/05/1995 No: XXXX XXXX 4532"
    )

    # 2. Vikram Singh Payment Receipt (Distractor 1)
    generate_payment_receipt(
        os.path.join('mock_data', 'IMG_20260122_161540.jpg'),
        recipient="Vikram Singh",
        amount_str="Rs 1,500",
        date_str="22 Jan 2026",
        ref_str="TXN1029384",
        full_ocr_text="Payment Receipt Amount: Rs 1,500 To: Vikram Singh Date: 22 Jan 2026"
    )

    # 3. Meera Devi ID Card (Distractor 2)
    generate_id_card(
        os.path.join('mock_data', 'IMG_20260405_091218.jpg'),
        name="Meera Devi",
        dept_or_title="Administration",
        emp_id="EMP-4421",
        full_ocr_text="ID Card Name: Meera Devi Employee ID: EMP-4421"
    )

    # 4. Electronics Hub Invoice (Distractor 3)
    generate_invoice(
        os.path.join('mock_data', 'IMG_20260128_145022.jpg'),
        company="Electronics Hub",
        inv_no="#INV-2026-0187",
        date_str="January",
        total_str="Rs 12,899",
        full_ocr_text="Invoice #INV-2026-0187 January 2026 Electronics Hub Total: Rs 12,899"
    )

    # 5. Priya Patel Marksheet
    generate_marksheet(
        os.path.join('mock_data', 'IMG_20260620_154530.jpg'),
        student="Priya Patel",
        roll_no="2024/CS/0156",
        cgpa="8.7",
        full_ocr_text="Semester Mark Sheet University of Delhi Student: Priya Patel Roll No: 2024/CS/0156 CGPA: 8.7"
    )

    # 6. Ramesh Kumar Prescription (Paracetamol)
    generate_prescription(
        os.path.join('mock_data', 'IMG_20260318_112005.jpg'),
        patient="Ramesh Kumar",
        doctor="Dr. Anita Sharma",
        meds=["Paracetamol 500mg", "Amoxicillin 250mg"],
        full_ocr_text="Prescription Dr. Anita Sharma Patient: Ramesh Kumar Paracetamol 500mg Amoxicillin 250mg"
    )

    # 7. Samrat Mehta Payment Receipt (Rs 6,500)
    generate_payment_receipt(
        os.path.join('mock_data', 'IMG_20260315_142011.jpg'),
        recipient="Samrat Mehta",
        amount_str="Rs 6,500",
        date_str="15 March 2026",
        ref_str="TXN9847321",
        full_ocr_text="Payment Receipt Amount: Rs 6,500 To: Samrat Mehta Date: 15 March 2026 Ref: TXN9847321"
    )

    # 8. Grocery Mart Invoice (March 2026)
    generate_invoice(
        os.path.join('mock_data', 'IMG_20260312_183045.jpg'),
        company="Grocery Mart",
        inv_no="#INV-2026-0312",
        date_str="March",
        total_str="Rs 2,340",
        full_ocr_text="Invoice #INV-2026-0312 March 2026 Grocery Mart Total: Rs 2,340"
    )

    # 9. Manoj Kumar Payment Receipt (Rs 3,200)
    generate_payment_receipt(
        os.path.join('mock_data', 'IMG_20260810_131254.jpg'),
        recipient="Manoj Kumar",
        amount_str="Rs 3,200",
        date_str="10 Aug 2026",
        ref_str="TXN8877112",
        full_ocr_text="Payment Receipt Amount: Rs 3,200 To: Manoj Kumar Date: 10 Aug 2026 Ref: TXN8877112"
    )

    # 10. Manoj Kumar Employee ID Card
    generate_id_card(
        os.path.join('mock_data', 'IMG_20260811_094015.jpg'),
        name="Manoj Kumar",
        dept_or_title="Operations",
        emp_id="EMP-9021",
        full_ocr_text="Employee ID Card Name: Manoj Kumar Department: Operations EMP-9021"
    )

    # 11. Prince Gupta Aadhaar Card
    generate_aadhaar_card(
        os.path.join('mock_data', 'IMG_20260815_120530.jpg'),
        name="Prince Gupta",
        dob="15/08/1998",
        no_str="XXXX XXXX 9120",
        full_ocr_text="Aadhaar Card Name: Prince Gupta DOB: 15/08/1998 UIDAI No: XXXX XXXX 9120"
    )

    # 12. Prince Gupta Mark Sheet
    generate_marksheet(
        os.path.join('mock_data', 'IMG_20260816_163012.jpg'),
        student="Prince Gupta",
        roll_no="2024/CS/0156",
        cgpa="8.7",
        full_ocr_text="Semester Mark Sheet University of Delhi Student: Prince Gupta Roll No: 2024/CS/0156 CGPA: 8.7"
    )

    # 13. Cloud Hub Technologies Invoice (September 2026)
    generate_invoice(
        os.path.join('mock_data', 'IMG_20260918_103022.jpg'),
        company="Cloud Hub Technologies",
        inv_no="#INV-2026-0914",
        date_str="September",
        total_str="Rs 8,450",
        full_ocr_text="Invoice #INV-2026-0914 September 2026 Cloud Hub Technologies Total: Rs 8,450"
    )

    # 14. Sunita Rao Generic Prescription
    generate_prescription(
        os.path.join('mock_data', 'IMG_20260322_171540.jpg'),
        patient="Sunita Rao",
        doctor="Dr. Anita Sharma",
        meds=["Cetirizine 10mg", "Vitamin D3"],
        full_ocr_text="Prescription Dr. Anita Sharma Patient: Sunita Rao Cetirizine 10mg Vitamin D3"
    )

    print("Generated 14 realistic document photos in mock_data/.")

if __name__ == '__main__':
    main()
