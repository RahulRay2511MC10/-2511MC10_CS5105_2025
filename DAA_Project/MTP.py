import streamlit as st
from datetime import date
import tempfile
import os
import zipfile
import shutil
import logging
from collections import defaultdict

import pandas as pd
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from PIL import Image, ImageOps

# ==============================
# CONFIGURABLE AUTHORS
# ==============================
AUTHORS = ["Gulshan", "Rahul"]  


# ==============================
# CORE PROCESSING LOGIC
# (refactored from your Colab script)
# ==============================
def generate_outputs(input_xlsx_path, images_dir, out_root, buffer_seats=5, layout="dense"):
    """
    Core function that takes:
      - input_xlsx_path: path to input_data_tt.xlsx
      - images_dir: directory with student images (optional)
      - out_root: directory where outputs will be written
      - buffer_seats: buffer seats per room
      - layout: "dense" or "sparse"

    Creates PDFs, Excels, and a final outputs.zip in out_root.
    Returns path to the final ZIP file.
    """

    # --------- Helper functions (mostly from your original code) ---------
    def safe_str(x):
        if pd.isna(x):
            return ""
        return str(x).strip()

    def split_cell(s):
        if s is None:
            return []
        return [p.strip() for p in str(s).replace(",", ";").split(";") if p.strip()]

    def detect_col(df, candidates):
        cols = df.columns.tolist()
        low = {c.lower(): c for c in cols}
        for c in candidates:
            if c in cols:
                return c
            if c.lower() in low:
                return low[c.lower()]
        return None

    def extract_floor(room_id: str) -> int:
        """
        Extract floor number from room id.
        Examples:
          "6103"  -> 6
          "10303" -> 10
          "B-104" -> 1
        """
        s = room_id.strip()
        digits = ""
        started = False
        for ch in s:
            if ch.isdigit():
                digits += ch
                started = True
            elif started:
                break
        if digits == "":
            return 0
        try:
            return int(digits)
        except ValueError:
            return 0

    # ----------------------------------------------------
    # LOGGING (allocation.log, errors.txt)
    # ----------------------------------------------------
    os.makedirs(out_root, exist_ok=True)
    log_path = os.path.join(out_root, "allocation.log")
    err_path = os.path.join(out_root, "errors.txt")

    # Reset logging handlers for Streamlit reruns
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    logging.basicConfig(
        level=logging.INFO,
        filename=log_path,
        filemode="w",
        format="%(asctime)s %(levelname)s: %(message)s",
    )

    err_logger = logging.getLogger("errors")
    fh = logging.FileHandler(err_path, mode="w")
    fh.setLevel(logging.ERROR)
    fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s: %(message)s"))
    err_logger.addHandler(fh)

    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    logging.getLogger().addHandler(console)

    # ----------------------------------------------------
    # IMAGE / PLACEHOLDER
    # ----------------------------------------------------
    os.makedirs(images_dir, exist_ok=True)
    placeholder_path = os.path.join(images_dir, "placeholder.png")
    if not os.path.exists(placeholder_path):
        try:
            im = Image.new("RGB", (300, 300), (240, 240, 240))
            im.save(placeholder_path)
            logging.info("Created placeholder image at %s", placeholder_path)
        except Exception as e:
            err_logger.error("Could not create placeholder image: %s", e)

    def find_student_image(roll):
        if not roll:
            return None
        # Direct exact filename matches
        for ext in (".jpg", ".jpeg", ".png", ".JPG", ".JPEG", ".PNG"):
            p = os.path.join(images_dir, roll + ext)
            if os.path.exists(p):
                return p
        # Case-insensitive search
        if os.path.isdir(images_dir):
            target = roll.lower()
            for fname in os.listdir(images_dir):
                name, e = os.path.splitext(fname)
                if name.lower() == target and e.lower() in (".jpg", ".jpeg", ".png"):
                    return os.path.join(images_dir, fname)
        if os.path.exists(placeholder_path):
            return placeholder_path
        return None

    # ----------------------------------------------------
    # PDF ATTENDANCE (3 per row, header once, footer once)
    # ----------------------------------------------------
    def write_pdf_attendance(pdf_path, date_str, session, subject, room_id, assigned, roll_to_name,
                             title_text="IITP Attendance System",
                             columns=3,
                             photo_w_mm=22, photo_h_mm=22,
                             cell_padding_mm=3):
        """
        Attendance sheet:
          - 3 students per row
          - Header only on first page
          - Invigilator table only on last page
        """
        page_w, page_h = A4
        margin = 8 * mm
        usable_w = page_w - 2 * margin
        usable_h = page_h - 2 * margin

        photo_w = photo_w_mm * mm
        photo_h = photo_h_mm * mm
        pad = cell_padding_mm * mm

        # HEADER / FOOTER AREA
        title_h = 10 * mm
        meta_h = 10 * mm
        header_h = title_h + meta_h + 2 * mm

        invig_row_h = 9 * mm
        invig_rows = 8
        invig_h = invig_rows * invig_row_h + 8 * mm

        grid_h = usable_h - header_h - invig_h - 4 * mm
        col_w = usable_w / columns

        cell_h = max(photo_h + 10 * mm, 36 * mm)
        rows_per_page = max(1, int(grid_h // cell_h))
        cells_per_page = rows_per_page * columns

        total_students = len(assigned)
        c = canvas.Canvas(pdf_path, pagesize=A4)
        c.setTitle(f"{subject}_{room_id}_{date_str}_{session}")

        def draw_header():
            x0 = margin
            y1 = page_h - margin
            c.setLineWidth(2)
            c.rect(margin, margin, page_w - 2 * margin, page_h - 2 * margin)

            title_y = y1 - 6 * mm
            c.setFont("Helvetica-Bold", 16)
            c.drawCentredString(page_w / 2, title_y, title_text)

            meta_y = title_y - 7 * mm
            c.setFont("Helvetica", 9)
            meta = f"Date: {date_str} | Shift: {session} | Room No: {room_id} | Student count: {total_students}"
            c.drawString(x0 + 4 * mm, meta_y, meta)

            subj_y = meta_y - 6 * mm
            subj_text = f"Subject: {subject} | Stud Present:             | Stud Absent:            "
            c.drawString(x0 + 4 * mm, subj_y, subj_text)

        def draw_border_only():
            c.setLineWidth(2)
            c.rect(margin, margin, page_w - 2 * margin, page_h - 2 * margin)

        def draw_invigilator_table():
            x0 = margin
            y0 = margin
            left_x = x0 + 8 * mm
            right_x = page_w - margin - 8 * mm
            bottom_y = y0 + 6 * mm

            c.setFont("Helvetica-Bold", 9)
            title_y = bottom_y + invig_h - 5 * mm
            c.drawCentredString((left_x + right_x) / 2, title_y, "Invigilator Name & Signature")

            col1_w = 20 * mm
            col3_w = 45 * mm
            col2_w = (right_x - left_x) - (col1_w + col3_w)
            row_h = invig_row_h
            start_y = bottom_y + 4 * mm

            # header row
            header_y = start_y + (invig_rows - 1) * row_h
            c.setFont("Helvetica", 8)
            c.rect(left_x, header_y, right_x - left_x, row_h, stroke=1, fill=0)
            c.line(left_x + col1_w, header_y, left_x + col1_w, header_y + row_h)
            c.line(left_x + col1_w + col2_w, header_y,
                   left_x + col1_w + col2_w, header_y + row_h)
            c.drawString(left_x + 3 * mm, header_y + row_h - 6, "Sl No.")
            c.drawString(left_x + col1_w + 3 * mm, header_y + row_h - 6, "Name")
            c.drawString(left_x + col1_w + col2_w + 3 * mm, header_y + row_h - 6, "Signature")

            # remaining rows
            for i in range(invig_rows - 1):
                ry = start_y + i * row_h
                c.rect(left_x, ry, right_x - left_x, row_h, stroke=1, fill=0)
                c.line(left_x + col1_w, ry, left_x + col1_w, ry + row_h)
                c.line(left_x + col1_w + col2_w, ry, left_x + col1_w + col2_w, ry + row_h)

        # draw pages
        for page_index in range((total_students + cells_per_page - 1) // cells_per_page):
            start = page_index * cells_per_page
            end = min(total_students, start + cells_per_page)
            page_students = assigned[start:end]

            is_first = (page_index == 0)
            is_last = (page_index == ((total_students + cells_per_page - 1) // cells_per_page - 1))

            if is_first:
                draw_header()
            else:
                draw_border_only()

            grid_top_y = (page_h - margin) - header_h
            x0 = margin

            for idx, roll in enumerate(page_students):
                row = idx // columns
                col = idx % columns
                cell_x = x0 + col * (usable_w / columns)
                cell_y = grid_top_y - (row + 1) * cell_h

                c.setLineWidth(0.5)
                c.rect(cell_x, cell_y, usable_w / columns, cell_h, stroke=1, fill=0)

                img_x = cell_x + pad
                img_y = cell_y + cell_h - pad - photo_h

                img_path = find_student_image(roll)
                if img_path and os.path.exists(img_path):
                    try:
                        pil_img = Image.open(img_path)
                        pil_img = ImageOps.exif_transpose(pil_img)
                        iw, ih = pil_img.size
                        ratio = min(photo_w / iw, photo_h / ih)
                        draw_w = iw * ratio
                        draw_h = ih * ratio
                        px = img_x + (photo_w - draw_w) / 2
                        py = img_y + (photo_h - draw_h) / 2
                        c.drawImage(ImageReader(pil_img), px, py,
                                    width=draw_w, height=draw_h,
                                    preserveAspectRatio=True, mask='auto')
                    except Exception:
                        c.rect(img_x, img_y, photo_w, photo_h)
                        c.setFont("Helvetica", 6)
                        c.drawCentredString(img_x + photo_w / 2, img_y + photo_h / 2, "No Image")
                else:
                    c.rect(img_x, img_y, photo_w, photo_h)
                    c.setFont("Helvetica", 6)
                    c.drawCentredString(img_x + photo_w / 2, img_y + photo_h / 2, "No Image Available")

                text_x = img_x + photo_w + pad
                text_top = img_y + photo_h
                name = roll_to_name.get(roll, "").strip() or "Unknown Name"
                c.setFont("Helvetica-Bold", 9)
                c.drawString(text_x, text_top - 1 * mm, name[:40])
                c.setFont("Helvetica", 8)
                c.drawString(text_x, text_top - 7 * mm, f"Roll: {roll}")
                sign_y = cell_y + 8 * mm
                c.line(text_x, sign_y, text_x + (usable_w / columns - photo_w - 4 * pad), sign_y)
                c.setFont("Helvetica", 7)
                c.drawString(text_x, sign_y - 4, "Sign:")

            if is_last:
                draw_invigilator_table()

            if not is_last:
                c.showPage()

        c.save()

    # ----------------------------------------------------
    # XLSX ATTENDANCE
    # ----------------------------------------------------
    def write_xlsx_attendance(xlsx_path, date_str, session, subject, room_id, assigned, roll_to_name):
        df = pd.DataFrame([
            {
                "roll_number": r,
                "student_name": roll_to_name.get(r, "Unknown Name"),
                "student_signature": ""
            } for r in assigned
        ])

        writer = pd.ExcelWriter(xlsx_path, engine="xlsxwriter")
        sheet_name = "Attendance"[:31]
        df.to_excel(writer, sheet_name=sheet_name, index=False, startrow=3)
        workbook = writer.book
        worksheet = writer.sheets[sheet_name]

        header = f"{date_str} | {session} | {subject} | Room {room_id}"
        worksheet.merge_range(0, 0, 2, 4, header)

        footer_start = 3 + len(df) + 2
        worksheet.write(footer_start, 0, "Role")
        worksheet.write(footer_start, 1, "Name")
        worksheet.write(footer_start, 2, "Signature")

        row = footer_start + 1
        for i in range(1, 6):
            worksheet.write(row, 0, f"TA{i}")
            row += 1
        for i in range(1, 6):
            worksheet.write(row, 0, f"Invigilator{i}")
            row += 1

        writer.close()

    # ----------------------------------------------------
    # LOAD INPUT WORKBOOK
    # ----------------------------------------------------
    if not os.path.exists(input_xlsx_path):
        raise FileNotFoundError(f"Input workbook not found at {input_xlsx_path}")

    xls = pd.ExcelFile(input_xlsx_path)
    need = ['in_timetable', 'in_course_roll_mapping', 'in_roll_name_mapping', 'in_room_capacity']
    for s in need:
        if s not in xls.sheet_names:
            raise ValueError(f"Workbook missing sheet: {s}")

    timetable = pd.read_excel(input_xlsx_path, sheet_name='in_timetable')
    course_roll = pd.read_excel(input_xlsx_path, sheet_name='in_course_roll_mapping')
    roll_name_df = pd.read_excel(input_xlsx_path, sheet_name='in_roll_name_mapping')
    rooms_df = pd.read_excel(input_xlsx_path, sheet_name='in_room_capacity')

    # ----------------------------------------------------
    # BUILD MAPPINGS
    # ----------------------------------------------------
    roll_col = detect_col(course_roll, ['rollno', 'roll_no', 'roll', 'role', 'Roll'])
    course_col = detect_col(course_roll, ['course_code', 'course', 'subject', 'subcode'])
    if not roll_col or not course_col:
        roll_col, course_col = course_roll.columns[0], course_roll.columns[1]

    subj_to_rolls = defaultdict(list)
    for _, r in course_roll.iterrows():
        c = safe_str(r[course_col])
        ro = safe_str(r[roll_col])
        if c and ro:
            subj_to_rolls[c].append(ro)

    for k in subj_to_rolls:
        subj_to_rolls[k] = sorted(subj_to_rolls[k])

    rn_col = detect_col(roll_name_df, ['roll', 'rollno', 'roll_no', 'Roll'])
    name_col = detect_col(roll_name_df, ['name', 'student_name', 'Name'])
    if not rn_col or not name_col:
        rn_col, name_col = roll_name_df.columns[0], roll_name_df.columns[1]

    roll_to_name = {}
    for _, r in roll_name_df.iterrows():
        roll = safe_str(r[rn_col])
        name = safe_str(r[name_col]) or "Unknown Name"
        if roll:
            roll_to_name[roll] = name

    room_col = detect_col(rooms_df, ['Room No.', 'Room', 'room_no', 'room_id'])
    cap_col = detect_col(rooms_df, ['Exam Capacity', 'capacity', 'Cap'])
    block_col = detect_col(rooms_df, ['Block', 'Building', 'Block No'])
    if not room_col or not cap_col:
        room_col, cap_col = rooms_df.columns[0], rooms_df.columns[1]

    rooms = []
    for _, r in rooms_df.iterrows():
        rid = safe_str(r[room_col])
        try:
            cap = int(r[cap_col])
        except Exception:
            try:
                cap = int(float(r[cap_col]))
            except Exception:
                cap = 0
        bldg = safe_str(r[block_col]) if block_col else ""
        floor = extract_floor(rid)
        rooms.append({
            "room_id": rid,
            "capacity": cap,
            "building": bldg,
            "floor": floor
        })

    rooms = sorted(rooms, key=lambda x: (x['building'], x['floor'], -x['capacity'], x['room_id']))

    # ----------------------------------------------------
    # TIMETABLE → LIST OF (DATE, SESSION, SUBJECTS)
    # ----------------------------------------------------
    date_col = detect_col(timetable, ['Date', 'date'])
    morning_col = detect_col(timetable, ['Morning', 'morning'])
    evening_col = detect_col(timetable, ['Evening', 'evening'])
    if not date_col:
        date_col = timetable.columns[0]

    schedule = []
    for _, r in timetable.iterrows():
        date_raw = r[date_col]
        try:
            date_str = pd.to_datetime(date_raw).strftime("%d_%m_%Y")
        except Exception:
            date_str = safe_str(date_raw).replace("/", "_").replace("-", "_")
        for col, sess in [(morning_col, 'Morning'), (evening_col, 'Evening')]:
            if not col:
                continue
            raw = r[col]
            if pd.isna(raw):
                continue
            if str(raw).strip().upper() == "NO EXAM":
                continue
            subs = split_cell(raw)
            if subs:
                schedule.append({"date": date_str, "session": sess, "subjects": subs})

    # ----------------------------------------------------
    # CAPACITY HELPERS
    # ----------------------------------------------------
    def subject_capacity_in_room(room, layout_):
        eff_total = room['eff_total']  # C - B
        per_subject = eff_total if layout_ == "dense" else eff_total // 2
        return min(room['free'], per_subject)

    # ----------------------------------------------------
    # SUBJECT → ROOM ALLOCATION
    # ----------------------------------------------------
    def allocate_subject_multi(subj, rolls, rooms_avail, layout_):
        total_needed = len(rolls)
        if total_needed == 0:
            return [], []

        by_building = defaultdict(list)
        for r in rooms_avail:
            by_building[r['building']].append(r)

        b_caps = {
            b: sum(subject_capacity_in_room(room, layout_) for room in rlist)
            for b, rlist in by_building.items()
        }

        def simulate_building(rlist):
            sim_rooms = sorted(
                rlist,
                key=lambda r: (r['floor'], r['free'], -r['capacity'], r['room_id'])
            )
            remaining = total_needed
            plan = []
            for room in sim_rooms:
                cap = subject_capacity_in_room(room, layout_)
                if cap <= 0:
                    continue
                take = min(cap, remaining)
                if take <= 0:
                    continue
                plan.append((room, take))
                remaining -= take
                if remaining == 0:
                    break
            return plan, remaining

        allocations = []
        remaining_rolls = rolls.copy()

        best_plan = None
        for bldg, rlist in by_building.items():
            if b_caps.get(bldg, 0) < total_needed:
                continue
            plan, rem = simulate_building(rlist)
            if rem == 0 and plan:
                rooms_used = len(plan)
                floors = [room['floor'] for room, _ in plan]
                floor_gap = max(floors) - min(floors)
                waste = sum(room['free'] - take for room, take in plan)
                if best_plan is None:
                    best_plan = {
                        "building": bldg,
                        "plan": plan,
                        "rooms_used": rooms_used,
                        "floor_gap": floor_gap,
                        "waste": waste
                    }
                else:
                    if (rooms_used < best_plan['rooms_used'] or
                        (rooms_used == best_plan['rooms_used'] and floor_gap < best_plan['floor_gap']) or
                        (rooms_used == best_plan['rooms_used'] and floor_gap == best_plan['floor_gap'] and waste < best_plan['waste'])):
                        best_plan = {
                            "building": bldg,
                            "plan": plan,
                            "rooms_used": rooms_used,
                            "floor_gap": floor_gap,
                            "waste": waste
                        }

        if best_plan:
            for room, take in best_plan['plan']:
                assigned = remaining_rolls[:take]
                remaining_rolls = remaining_rolls[take:]
                room['free'] -= take
                allocations.append((room['room_id'], assigned))
            return allocations, remaining_rolls

        # multi-building allocation fallback
        building_order = sorted(b_caps.keys(), key=lambda b: b_caps[b], reverse=True)
        for bldg in building_order:
            rlist = sorted(
                by_building[bldg],
                key=lambda r: (r['floor'], r['free'], -r['capacity'], r['room_id'])
            )
            for room in rlist:
                if not remaining_rolls:
                    break
                cap = subject_capacity_in_room(room, layout_)
                if cap <= 0:
                    continue
                take = min(cap, len(remaining_rolls))
                if take <= 0:
                    continue
                assigned = remaining_rolls[:take]
                remaining_rolls = remaining_rolls[take:]
                room['free'] -= take
                allocations.append((room['room_id'], assigned))
            if not remaining_rolls:
                break

        return allocations, remaining_rolls

    # ----------------------------------------------------
    # MAIN LOOP (per day & session)
    # ----------------------------------------------------
    master_rows = []
    seats_rows = []
    had_unallocated = False

    for entry in schedule:
        date_ = entry["date"]
        session = entry["session"]
        subs = entry["subjects"]

        logging.info("Processing %s %s with subjects: %s", date_, session, ", ".join(subs))

        # clash check
        sets = [set(subj_to_rolls.get(s, [])) for s in subs]
        inter = set()
        if sets:
            inter = sets[0].copy()
            for s in sets[1:]:
                inter &= s
        if inter:
            msg = f"CLASH on {date_} {session}: rolls {sorted(inter)}"
            logging.error(msg)
            err_logger.error(msg)
            master_rows.append({
                "date": date_, "session": session,
                "subject": "__CLASH__", "room_id": "",
                "allocated_count": 0,
                "rolls": ";".join(sorted(inter)),
                "seats_left": ""
            })
            continue

        eff_per_room = [max(0, r['capacity'] - buffer_seats) for r in rooms]
        total_capacity = sum(eff_per_room)
        total_students = sum(len(subj_to_rolls.get(s, [])) for s in subs)
        if total_students > total_capacity:
            msg = f"Cannot allocate due to excess students on {date_} {session} (students={total_students}, capacity={total_capacity})"
            logging.error(msg)
            err_logger.error(msg)

        date_dir = os.path.join(out_root, date_)
        morning_dir = os.path.join(date_dir, "Morning")
        evening_dir = os.path.join(date_dir, "Evening")
        os.makedirs(morning_dir, exist_ok=True)
        os.makedirs(evening_dir, exist_ok=True)
        target_session_dir = morning_dir if session.lower().startswith("m") else evening_dir

        rooms_avail = []
        for base, eff in zip(rooms, eff_per_room):
            rooms_avail.append({
                "room_id": base["room_id"],
                "capacity": base["capacity"],
                "building": base["building"],
                "floor": base["floor"],
                "eff_total": eff,
                "free": eff
            })

        subs_sorted = sorted(subs, key=lambda s: len(subj_to_rolls.get(s, [])), reverse=True)

        for subj in subs_sorted:
            rolls = subj_to_rolls.get(subj, []).copy()
            allocations, remaining = allocate_subject_multi(subj, rolls, rooms_avail, layout)

            for room_id, assigned in allocations:
                if not assigned:
                    continue
                pdf_path = os.path.join(target_session_dir, f"{subj}_{room_id}.pdf")
                xlsx_path = os.path.join(target_session_dir, f"{subj}_{room_id}.xlsx")
                write_pdf_attendance(pdf_path, date_, session, subj, room_id, assigned, roll_to_name)
                write_xlsx_attendance(xlsx_path, date_, session, subj, room_id, assigned, roll_to_name)

                free_now = next((r_["free"] for r_ in rooms_avail if r_["room_id"] == room_id), "")
                master_rows.append({
                    "date": date_, "session": session, "subject": subj,
                    "room_id": room_id,
                    "allocated_count": len(assigned),
                    "rolls": ";".join(assigned),
                    "seats_left": free_now
                })

            if remaining:
                had_unallocated = True
                msg = f"Unallocated students for {subj} on {date_} {session}: {len(remaining)}"
                logging.error(msg)
                err_logger.error(msg)
                master_rows.append({
                    "date": date_, "session": session, "subject": subj,
                    "room_id": "__UNALLOCATED__",
                    "allocated_count": len(rolls) - len(remaining),
                    "rolls": ";".join(rolls[:len(rolls) - len(remaining)]),
                    "seats_left": ""
                })

        for r_ in rooms_avail:
            seats_rows.append({
                "date": date_, "session": session,
                "room_id": r_["room_id"],
                "capacity": r_["capacity"],
                "eff_total": r_["eff_total"],
                "free": r_["free"]
            })

    # ----------------------------------------------------
    # WRITE MASTER OVERALL SEATING
    # ----------------------------------------------------
    master_df = pd.DataFrame(master_rows)
    master_out = os.path.join(out_root, "op_overall_seating_arrangement.xlsx")
    if not master_df.empty:
        cols_to_keep = [c for c in master_df.columns if c != "seats_left"]
        master_df[cols_to_keep].to_excel(master_out, index=False)

    # ----------------------------------------------------
    # WRITE op_seats_left.xlsx
    # ----------------------------------------------------
    seats_df = pd.DataFrame(seats_rows)
    seats_out = os.path.join(out_root, "op_seats_left.xlsx")
    writer = pd.ExcelWriter(seats_out, engine="xlsxwriter")
    if not seats_df.empty:
        for (date_, session), grp in seats_df.groupby(["date", "session"]):
            tmp = grp.copy()
            tmp["Seat Capacity"] = tmp["capacity"]
            tmp["Seat Allocated"] = tmp["eff_total"] - tmp["free"]
            tmp["Seat Left"] = tmp["Seat Capacity"] - tmp["Seat Allocated"]
            out = tmp[["room_id", "Seat Capacity", "Seat Allocated", "Seat Left"]].rename(
                columns={"room_id": "Room No"}
            )
            sheet_name = f"{date_}_{session}"[:31]
            out.to_excel(writer, sheet_name=sheet_name, index=False)
    writer.close()

    # ----------------------------------------------------
    # FINAL ZIP
    # ----------------------------------------------------
    zip_path = os.path.join(out_root, "outputs.zip")
    if os.path.exists(zip_path):
        os.remove(zip_path)
    shutil.make_archive(out_root, "zip", out_root)
    # shutil.make_archive creates out_root + ".zip"
    zip_path = out_root + ".zip"

    if had_unallocated:
        logging.warning("Some students could not be allocated. Check errors.txt and master file.")

    return zip_path


# ==============================
# STREAMLIT UI
# ==============================
def main():
    st.title("DAA Project")

    # Today's date
    today_str = date.today().strftime("%d-%m-%Y")
    st.write(today_str)

    # Authors
    st.write("Authors: " + " & ".join(AUTHORS))

    st.markdown("---")

    st.subheader("Input Files")

    input_file = st.file_uploader(
        "Upload input_data_tt.xlsx",
        type=["xlsx"],
        help="The main timetable & mapping workbook"
    )

    images_zip = st.file_uploader(
        "Upload images.zip (optional)",
        type=["zip"],
        help="Zip of student photos named by roll number"
    )

    st.markdown("---")
    st.subheader("Configuration")

    buffer_seats = st.number_input(
        "Buffer seats per room",
        min_value=0,
        max_value=100,
        value=5,
        step=1
    )

    layout = st.selectbox(
        "Layout type",
        options=["dense", "sparse"],
        index=0,
        help="dense = full use of seats; sparse = per-subject uses half"
    )

    st.markdown("---")

    run_clicked = st.button("Run Process")

    if run_clicked:
        if input_file is None:
            st.error("Please upload input_data_tt.xlsx before running.")
            return

        with st.spinner("Processing seating arrangement and generating outputs..."):
            # Create temp working directory
            work_dir = tempfile.mkdtemp()
            input_xlsx_path = os.path.join(work_dir, "input_data_tt.xlsx")

            # Save uploaded Excel
            with open(input_xlsx_path, "wb") as f:
                f.write(input_file.getbuffer())

            # Prepare images directory
            images_dir = os.path.join(work_dir, "images")
            os.makedirs(images_dir, exist_ok=True)

            # If images.zip provided, extract it
            if images_zip is not None:
                zip_path = os.path.join(work_dir, "images.zip")
                with open(zip_path, "wb") as f:
                    f.write(images_zip.getbuffer())
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(images_dir)

            out_root = os.path.join(work_dir, "outputs")
            os.makedirs(out_root, exist_ok=True)

            # Run core logic
            zip_out_path = generate_outputs(
                input_xlsx_path=input_xlsx_path,
                images_dir=images_dir,
                out_root=out_root,
                buffer_seats=buffer_seats,
                layout=layout
            )

            # Load zip as bytes for download
            with open(zip_out_path, "rb") as f:
                zip_bytes = f.read()

        st.success("Processing complete! Download your outputs below.")

        st.download_button(
            label="Download outputs.zip",
            data=zip_bytes,
            file_name="outputs.zip",
            mime="application/zip"
        )


if __name__ == "__main__":
    main()
