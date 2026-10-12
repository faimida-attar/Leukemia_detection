import os
import re
import datetime
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter


DISEASE_FULL_NAMES = {
    "ALL": "Acute Lymphoblastic Leukemia",
    "AML": "Acute Myeloid Leukemia",
    "CLL": "Chronic Lymphocytic Leukemia",
    "CML": "Chronic Myeloid Leukemia",
    "Normal": "Normal Non-Leukemic Smear"
}


def _parse_dimensions(dim_str):
    """Parse width and height integers from dimension string like '4160 x 3120' or '4160 × 3120 pixels'."""
    if not dim_str or not isinstance(dim_str, str):
        return None, None
    matches = re.findall(r'\d+', dim_str)
    if len(matches) >= 2:
        try:
            return int(matches[0]), int(matches[1])
        except ValueError:
            pass
    return None, None


def _to_float(v, default=None):
    """Safely convert any numeric or string representation to a float."""
    if v is None:
        return default
    try:
        val = float(v)
        return val
    except (ValueError, TypeError):
        return default


def generate_excel_report(analysis_data, output_path):
    """
    Generate a professionally formatted, multi-sheet .xlsx Excel report for multiple-image leukemia analysis.

    Sheets:
    1. 'Summary & Statistics' - Aggregate batch metrics, leukemia subtype distribution, and clinical benchmark metrics.
    2. 'Slide Analysis Master Data' - Granular per-slide table with image properties, compression details,
       reconstruction metrics (PSNR, SSIM, MAE), model predictions, confidence scores, and class probabilities.
    """
    # -------------------------------------------------------------------------
    # 1. Normalize Input Data
    # -------------------------------------------------------------------------
    if isinstance(analysis_data, list):
        items = analysis_data
    elif isinstance(analysis_data, dict):
        if "items" in analysis_data and isinstance(analysis_data["items"], list):
            items = analysis_data["items"]
        elif "results" in analysis_data and isinstance(analysis_data["results"], list):
            items = analysis_data["results"]
        else:
            items = [analysis_data]
    else:
        items = []

    # Filter out empty or null items
    items = [it for it in items if isinstance(it, dict)]

    wb = Workbook()

    # -------------------------------------------------------------------------
    # 2. Typography, Colors & Border Design System
    # -------------------------------------------------------------------------
    font_main = "Segoe UI"

    title_font = Font(name=font_main, size=14, bold=True, color="FFFFFF")
    subtitle_font = Font(name=font_main, size=9.5, italic=True, color="E2E8F0")
    section_font = Font(name=font_main, size=11, bold=True, color="0F172A")
    header_font = Font(name=font_main, size=10, bold=True, color="FFFFFF")
    sub_header_font = Font(name=font_main, size=10, bold=True, color="0369A1")
    data_font = Font(name=font_main, size=9, color="1E293B")
    data_bold_font = Font(name=font_main, size=9, bold=True, color="1E293B")
    data_accent_font = Font(name=font_main, size=9, bold=True, color="1E40AF")
    small_desc_font = Font(name=font_main, size=8.5, color="475569")
    summary_label_font = Font(name=font_main, size=9.5, bold=True, color="1E3A8A")

    fill_brand = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")       # Dark Navy (#1E3A8A)
    fill_header = PatternFill(start_color="1E40AF", end_color="1E40AF", fill_type="solid")      # Navy Blue (#1E40AF)
    fill_sub_hdr = PatternFill(start_color="E0F2FE", end_color="E0F2FE", fill_type="solid")    # Sky Blue light (#E0F2FE)
    fill_metric_hdr = PatternFill(start_color="0284C7", end_color="0284C7", fill_type="solid") # Sky Accent (#0284C7)
    fill_zebra = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")      # Slate zebra (#F8FAFC)
    fill_total = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")      # Light Slate total (#F1F5F9)

    border_thin = Border(
        left=Side(style='thin', color='CBD5E1'),
        right=Side(style='thin', color='CBD5E1'),
        top=Side(style='thin', color='CBD5E1'),
        bottom=Side(style='thin', color='CBD5E1')
    )
    border_double = Border(
        left=Side(style='thin', color='CBD5E1'),
        right=Side(style='thin', color='CBD5E1'),
        top=Side(style='thin', color='CBD5E1'),
        bottom=Side(style='double', color='1E3A8A')
    )

    align_center = Alignment(horizontal='center', vertical='center', wrap_text=False)
    align_left = Alignment(horizontal='left', vertical='center', wrap_text=False)
    align_right = Alignment(horizontal='right', vertical='center', wrap_text=False)

    # -------------------------------------------------------------------------
    # 3. Compute Aggregates & Statistics
    # -------------------------------------------------------------------------
    total_count = len(items)
    completed_items = [it for it in items if it.get("status") != "processing"]
    valid_items = [it for it in completed_items if it.get("is_valid") is not False]
    invalid_count = len(completed_items) - len(valid_items)

    class_counts = {"ALL": 0, "AML": 0, "CLL": 0, "CML": 0, "Normal": 0}
    psnr_vals = []
    ssim_vals = []
    mae_vals = []
    reduction_vals = []
    ratio_vals = []
    orig_kb_vals = []
    comp_kb_vals = []
    hybrid_conf_vals = []
    resnet_conf_vals = []
    densenet_conf_vals = []

    for it in completed_items:
        # Prediction
        pred = (
            it.get("hybrid_pred") or
            it.get("hybrid", {}).get("prediction") or
            it.get("classification", {}).get("prediction") or
            it.get("resnet50_pred") or
            it.get("resnet50", {}).get("prediction")
        )
        if pred in class_counts:
            class_counts[pred] += 1

        # Reconstruction metrics
        rm = it.get("reconstruction_metrics", {})
        p = _to_float(rm.get("psnr_db") if rm.get("psnr_db") is not None else rm.get("psnr"))
        s = _to_float(rm.get("ssim"))
        m = _to_float(rm.get("mae"))

        if p is not None: psnr_vals.append(p)
        if s is not None: ssim_vals.append(s)
        if m is not None: mae_vals.append(m)

        # Sizes & Compression
        orig_b = _to_float(
            it.get("compression_information", {}).get("original_size_bytes") or
            it.get("compression", {}).get("original_size_bytes") or
            it.get("image_information", {}).get("file_size_bytes"),
            0.0
        )
        comp_b = _to_float(
            it.get("compression_information", {}).get("compressed_size_bytes") or
            it.get("compression", {}).get("compressed_size_bytes"),
            0.0
        )
        if orig_b > 0: orig_kb_vals.append(orig_b / 1024.0)
        if comp_b > 0: comp_kb_vals.append(comp_b / 1024.0)

        red = _to_float(it.get("compression_information", {}).get("reduction"))
        if red is not None:
            reduction_vals.append(red)
        elif orig_b > 0 and comp_b > 0:
            reduction_vals.append(((orig_b - comp_b) / orig_b) * 100.0)

        if comp_b > 0 and orig_b > 0:
            ratio_vals.append(orig_b / comp_b)

        # Confidence scores
        def _get_conf(val):
            v = _to_float(val)
            if v is None:
                return None
            return float(v * 100.0 if v <= 1.0 and v > 0 else v)

        h_c = _get_conf(it.get("hybrid_conf") or it.get("hybrid", {}).get("confidence") or it.get("classification", {}).get("confidence"))
        r_c = _get_conf(it.get("resnet50_conf") or it.get("resnet50", {}).get("confidence"))
        d_c = _get_conf(it.get("densenet_conf") or it.get("densenet121", {}).get("confidence") or it.get("densenet", {}).get("confidence"))

        if h_c is not None: hybrid_conf_vals.append(h_c)
        if r_c is not None: resnet_conf_vals.append(r_c)
        if d_c is not None: densenet_conf_vals.append(d_c)

    def _avg(lst):
        return sum(lst) / len(lst) if lst else 0.0

    # =========================================================================
    # SHEET 1: EXECUTIVE SUMMARY & STATISTICAL AGGREGATES
    # =========================================================================
    ws_summary = wb.active
    ws_summary.title = "Summary & Statistics"
    ws_summary.views.sheetView[0].showGridLines = True

    # 1. Title Banner (Columns A to E)
    ws_summary.merge_cells("A1:E1")
    title_cell = ws_summary["A1"]
    title_cell.value = "Leukemia Detection & Medical Image Reconstruction - Research Evaluation Report"
    title_cell.font = title_font
    title_cell.fill = fill_brand
    title_cell.alignment = align_left
    ws_summary.row_dimensions[1].height = 34

    ws_summary.merge_cells("A2:E2")
    sub_cell = ws_summary["A2"]
    sub_cell.value = (
        f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  |  "
        "Framework: GAN + CBAM Quality Restoration & ResNet50 + DenseNet121 Hybrid Classification"
    )
    sub_cell.font = subtitle_font
    sub_cell.fill = fill_brand
    sub_cell.alignment = align_left
    ws_summary.row_dimensions[2].height = 20

    # Style banner border cells
    for r in (1, 2):
        for c in range(1, 6):
            cell = ws_summary.cell(row=r, column=c)
            cell.border = border_thin
            cell.fill = fill_brand

    # 2. Section 1: Batch Processing Overview (5 Columns: A to E)
    ws_summary["A4"].value = "1. BATCH PROCESSING OVERVIEW"
    ws_summary["A4"].font = section_font

    kpi_headers = ["Total Processed Slides", "Valid Smear Slides", "Excluded / Invalid Slides", "Valid Processing Rate", "Mean PSNR (dB)"]
    for col_idx, kh in enumerate(kpi_headers, start=1):
        c = ws_summary.cell(row=5, column=col_idx, value=kh)
        c.font = sub_header_font
        c.fill = fill_sub_hdr
        c.border = border_thin
        c.alignment = align_center

    valid_rate = (len(valid_items) / total_count * 100.0) if total_count > 0 else 0.0
    mean_psnr_kpi = round(_avg(psnr_vals), 2)
    kpi_values = [total_count, len(valid_items), invalid_count, f"{valid_rate:.1f}%", f"{mean_psnr_kpi:.2f} dB"]
    for col_idx, kv in enumerate(kpi_values, start=1):
        c = ws_summary.cell(row=6, column=col_idx, value=kv)
        c.font = data_bold_font
        c.border = border_thin
        c.alignment = align_center
    ws_summary.row_dimensions[5].height = 24
    ws_summary.row_dimensions[6].height = 22

    # 3. Section 2: Leukemia Subtype Distribution (5 Columns: A to E)
    ws_summary["A8"].value = "2. LEUKEMIA SUBTYPE DISTRIBUTION"
    ws_summary["A8"].font = section_font

    dist_headers = ["Class Subtype", "Full Clinical Classification", "Case Count", "Distribution (%)", "Clinical Relevance"]
    for col_idx, dh in enumerate(dist_headers, start=1):
        c = ws_summary.cell(row=9, column=col_idx, value=dh)
        c.font = header_font
        c.fill = fill_header
        c.border = border_thin
        c.alignment = align_center
    ws_summary.row_dimensions[9].height = 24

    clin_notes = {
        "ALL": "Acute Lymphoblastic Leukemia — predominantly lymphoblast proliferation",
        "AML": "Acute Myeloid Leukemia — excessive myeloblast & myeloid lineage cells",
        "CLL": "Chronic Lymphocytic Leukemia — mature-appearing monoclonal B-cell accumulation",
        "CML": "Chronic Myeloid Leukemia — granulocytic lineage expansion & BCR-ABL1 marker",
        "Normal": "Normal Non-Leukemic Blood Smear — physiological leukocyte morphology"
    }

    curr_row = 10
    total_classified = sum(class_counts.values())
    for cls_key in ["ALL", "AML", "CLL", "CML", "Normal"]:
        cnt = class_counts[cls_key]
        pct = (cnt / total_classified * 100.0) if total_classified > 0 else 0.0

        row_vals = [
            cls_key,
            DISEASE_FULL_NAMES.get(cls_key, cls_key),
            cnt,
            round(pct, 2),
            clin_notes.get(cls_key, "")
        ]

        for col_idx, val in enumerate(row_vals, start=1):
            c = ws_summary.cell(row=curr_row, column=col_idx, value=val)
            c.font = data_bold_font if col_idx in (1, 3) else data_font
            c.border = border_thin
            if col_idx in (1, 3):
                c.alignment = align_center
            elif col_idx == 4:
                c.alignment = align_right
                c.number_format = '0.00"%"'
            else:
                c.alignment = align_left
        ws_summary.row_dimensions[curr_row].height = 20
        curr_row += 1

    # Total row for Distribution
    tot_row = curr_row
    ws_summary.cell(row=tot_row, column=1, value="TOTAL").font = data_bold_font
    ws_summary.cell(row=tot_row, column=2, value="All Analyzed Diagnostic Classes").font = data_bold_font
    ws_summary.cell(row=tot_row, column=3, value=total_classified).font = data_bold_font
    ws_summary.cell(row=tot_row, column=4, value=100.0 if total_classified > 0 else 0.0).font = data_bold_font
    ws_summary.cell(row=tot_row, column=4).number_format = '0.00"%"'
    ws_summary.cell(row=tot_row, column=5, value="100% Cohort Coverage").font = small_desc_font
    for col_idx in range(1, 6):
        c = ws_summary.cell(row=tot_row, column=col_idx)
        c.fill = fill_total
        c.border = border_double
        if col_idx in (1, 3): c.alignment = align_center
        elif col_idx == 4: c.alignment = align_right
        else: c.alignment = align_left
    ws_summary.row_dimensions[tot_row].height = 22

    # 4. Section 3: Aggregate Reconstruction & Model Performance Metrics (5 Columns: A to E)
    curr_row = tot_row + 2
    ws_summary.cell(row=curr_row, column=1, value="3. AGGREGATE RECONSTRUCTION & MODEL PERFORMANCE METRICS").font = section_font
    curr_row += 1

    metric_table_headers = ["Metric Name", "Mean / Aggregate Value", "Unit", "Benchmark / Threshold", "Clinical & Technical Interpretation"]
    for col_idx, mth in enumerate(metric_table_headers, start=1):
        c = ws_summary.cell(row=curr_row, column=col_idx, value=mth)
        c.font = header_font
        c.fill = fill_metric_hdr
        c.border = border_thin
        c.alignment = align_center
    ws_summary.row_dimensions[curr_row].height = 24
    curr_row += 1

    metrics_rows = [
        ("Peak Signal-to-Noise Ratio (PSNR)", round(_avg(psnr_vals), 2), "dB", "> 30.0 dB", "Higher indicates superior pixel restoration fidelity (>30 dB is medical-grade)"),
        ("Structural Similarity Index (SSIM)", round(_avg(ssim_vals), 4), "Index (0 to 1)", "> 0.8500", "Closer to 1.0 preserves cell boundaries, chromatin texture, and cytoplasm"),
        ("Mean Absolute Error (MAE)", round(_avg(mae_vals), 4), "Pixel Error", "< 0.0800", "Lower indicates minimal absolute pixel deviation after CBAM GAN attention"),
        ("Average Storage Reduction", round(_avg(reduction_vals), 2), "%", "> 75.0 %", "Bandwidth and storage footprint saved through intelligent JPEG compression"),
        ("Average Compression Ratio", round(_avg(ratio_vals), 2), ":1", "> 4.0:1", "Physical microscopic slide file size compression factor achieved"),
        ("Hybrid Ensemble Mean Confidence", round(_avg(hybrid_conf_vals), 2), "%", "> 90.0 %", "Average diagnostic certainty combining ResNet50 and DenseNet121 backbones"),
        ("ResNet50 Standalone Mean Confidence", round(_avg(resnet_conf_vals), 2), "%", "> 85.0 %", "Average certainty score from the standalone ResNet50 classifier"),
        ("DenseNet121 Standalone Mean Confidence", round(_avg(densenet_conf_vals), 2), "%", "> 85.0 %", "Average certainty score from the standalone DenseNet121 classifier"),
    ]

    for m_name, m_val, m_unit, m_bench, m_desc in metrics_rows:
        r_c1 = ws_summary.cell(row=curr_row, column=1, value=m_name)
        r_c2 = ws_summary.cell(row=curr_row, column=2, value=m_val)
        r_c3 = ws_summary.cell(row=curr_row, column=3, value=m_unit)
        r_c4 = ws_summary.cell(row=curr_row, column=4, value=m_bench)
        r_c5 = ws_summary.cell(row=curr_row, column=5, value=m_desc)

        r_c1.font = data_bold_font
        r_c2.font = data_accent_font
        r_c3.font = data_font
        r_c4.font = small_desc_font
        r_c5.font = small_desc_font

        r_c1.alignment = align_left
        r_c2.alignment = align_right
        r_c3.alignment = align_center
        r_c4.alignment = align_center
        r_c5.alignment = align_left

        for c_idx in range(1, 6):
            ws_summary.cell(row=curr_row, column=c_idx).border = border_thin
            if curr_row % 2 == 1:
                ws_summary.cell(row=curr_row, column=c_idx).fill = fill_zebra

        ws_summary.row_dimensions[curr_row].height = 20
        curr_row += 1


    # =========================================================================
    # SHEET 2: MASTER IMAGE ANALYSIS DATA TABLE
    # =========================================================================
    ws_data = wb.create_sheet(title="Slide Analysis Master Data")
    ws_data.views.sheetView[0].showGridLines = True
    ws_data.freeze_panes = "C2"  # Freeze headers (row 1) and Slide # + Filename (cols A-B)

    # Master Table Column Definitions (30 Complete Attributes)
    columns = [
        {"id": "index", "name": "Slide #", "min_width": 10, "align": align_center},
        {"id": "filename", "name": "Filename", "min_width": 32, "align": align_left},
        {"id": "validation", "name": "Validation Status", "min_width": 18, "align": align_center},
        {"id": "width", "name": "Width (px)", "min_width": 14, "align": align_right, "fmt": "#,##0"},
        {"id": "height", "name": "Height (px)", "min_width": 14, "align": align_right, "fmt": "#,##0"},
        {"id": "format", "name": "Image Format", "min_width": 15, "align": align_center},
        {"id": "color_mode", "name": "Color Mode", "min_width": 14, "align": align_center},
        {"id": "orig_kb", "name": "Original Size (KB)", "min_width": 18, "align": align_right, "fmt": "#,##0.00"},
        {"id": "orig_bytes", "name": "Original Size (Bytes)", "min_width": 20, "align": align_right, "fmt": "#,##0"},
        {"id": "comp_kb", "name": "Compressed Size (KB)", "min_width": 20, "align": align_right, "fmt": "#,##0.00"},
        {"id": "comp_bytes", "name": "Compressed Size (Bytes)", "min_width": 22, "align": align_right, "fmt": "#,##0"},
        {"id": "quality", "name": "Compression Quality (%)", "min_width": 24, "align": align_right, "fmt": "0.0"},
        {"id": "reduction", "name": "Size Reduction (%)", "min_width": 18, "align": align_right, "fmt": '0.00"%"'},
        {"id": "ratio", "name": "Compression Ratio (:1)", "min_width": 22, "align": align_right, "fmt": "0.00"},
        {"id": "psnr", "name": "PSNR (dB)", "min_width": 14, "align": align_right, "fmt": "0.00"},
        {"id": "ssim", "name": "SSIM (0 to 1)", "min_width": 16, "align": align_right, "fmt": "0.0000"},
        {"id": "mae", "name": "MAE (Pixel Error)", "min_width": 18, "align": align_right, "fmt": "0.0000"},
        {"id": "pred_class", "name": "Predicted Leukemia Class", "min_width": 24, "align": align_center},
        {"id": "full_diagnosis", "name": "Full Clinical Diagnosis", "min_width": 34, "align": align_left},
        {"id": "confidence", "name": "Hybrid Confidence (%)", "min_width": 22, "align": align_right, "fmt": '0.00"%"'},
        {"id": "resnet_pred", "name": "ResNet50 Prediction", "min_width": 20, "align": align_center},
        {"id": "resnet_conf", "name": "ResNet50 Confidence (%)", "min_width": 24, "align": align_right, "fmt": '0.00"%"'},
        {"id": "densenet_pred", "name": "DenseNet121 Prediction", "min_width": 22, "align": align_center},
        {"id": "densenet_conf", "name": "DenseNet121 Confidence (%)", "min_width": 26, "align": align_right, "fmt": '0.00"%"'},
        {"id": "prob_all", "name": "ALL Prob (%)", "min_width": 15, "align": align_right, "fmt": '0.00"%"'},
        {"id": "prob_aml", "name": "AML Prob (%)", "min_width": 15, "align": align_right, "fmt": '0.00"%"'},
        {"id": "prob_cll", "name": "CLL Prob (%)", "min_width": 15, "align": align_right, "fmt": '0.00"%"'},
        {"id": "prob_cml", "name": "CML Prob (%)", "min_width": 15, "align": align_right, "fmt": '0.00"%"'},
        {"id": "prob_normal", "name": "Normal Prob (%)", "min_width": 16, "align": align_right, "fmt": '0.00"%"'},
        {"id": "session_id", "name": "Session ID", "min_width": 26, "align": align_left}
    ]

    # Write Master Table Headers
    ws_data.row_dimensions[1].height = 28
    for col_idx, col in enumerate(columns, start=1):
        cell = ws_data.cell(row=1, column=col_idx, value=col["name"])
        cell.font = header_font
        cell.fill = fill_header
        cell.border = border_thin
        cell.alignment = align_center

    # Populate Granular Data Rows
    row_num = 2
    for idx, item in enumerate(items, start=1):
        # 1. Filename & Validation
        fname = (
            item.get("image_information", {}).get("filename") or
            item.get("selectedFileName") or
            item.get("filename") or
            f"Slide_{idx}.jpg"
        )
        is_val = item.get("is_valid") is not False
        val_status = item.get("validation_status") or ("Valid Blood Smear" if is_val else "Invalid Slide")

        # 2. Dimensions & Image Info
        dim_str = (
            item.get("image_information", {}).get("original_dimensions") or
            item.get("image_information", {}).get("dimensions") or
            item.get("original_dimensions") or
            item.get("dimensions") or ""
        )
        w, h = _parse_dimensions(dim_str)
        if not w and item.get("image_information", {}).get("width"):
            w = _to_float(item.get("image_information", {}).get("width"))
        if not h and item.get("image_information", {}).get("height"):
            h = _to_float(item.get("image_information", {}).get("height"))

        fmt = item.get("image_information", {}).get("format") or "JPEG"
        color_mode = item.get("image_information", {}).get("color_mode") or "RGB"

        # 3. Sizes & Compression Details
        orig_bytes = _to_float(
            item.get("compression_information", {}).get("original_size_bytes") or
            item.get("compression", {}).get("original_size_bytes") or
            item.get("image_information", {}).get("file_size_bytes"),
            0.0
        )
        comp_bytes = _to_float(
            item.get("compression_information", {}).get("compressed_size_bytes") or
            item.get("compression", {}).get("compressed_size_bytes"),
            0.0
        )
        orig_kb = round(orig_bytes / 1024.0, 2) if orig_bytes > 0 else 0.0
        comp_kb = round(comp_bytes / 1024.0, 2) if comp_bytes > 0 else 0.0

        qual = _to_float(item.get("compression_information", {}).get("quality"), 50.0)
        reduction = _to_float(item.get("compression_information", {}).get("reduction"))
        if reduction is not None:
            reduction = round(reduction, 2)
        elif orig_bytes > 0 and comp_bytes > 0:
            reduction = round(((orig_bytes - comp_bytes) / orig_bytes) * 100.0, 2)
        else:
            reduction = 0.0

        if comp_bytes > 0 and orig_bytes > 0:
            comp_ratio = round(orig_bytes / comp_bytes, 2)
        elif reduction > 0 and reduction < 100:
            comp_ratio = round(100.0 / (100.0 - reduction), 2)
        else:
            comp_ratio = 1.0

        # 4. Reconstruction Metrics
        rm = item.get("reconstruction_metrics", {})
        psnr_val = _to_float(rm.get("psnr_db") if rm.get("psnr_db") is not None else rm.get("psnr"))
        ssim_val = _to_float(rm.get("ssim"))
        mae_val = _to_float(rm.get("mae"))

        psnr_disp = round(psnr_val, 2) if psnr_val is not None else 0.0
        ssim_disp = round(ssim_val, 4) if ssim_val is not None else 0.0
        mae_disp = round(mae_val, 4) if mae_val is not None else 0.0

        # 5. Diagnostic Classification & Confidence
        pred_cls = (
            item.get("hybrid_pred") or
            item.get("hybrid", {}).get("prediction") or
            item.get("classification", {}).get("prediction") or
            item.get("resnet50_pred") or
            "N/A"
        )
        full_diag = DISEASE_FULL_NAMES.get(pred_cls, pred_cls)

        def _clean_conf(c_val):
            v = _to_float(c_val)
            if v is None:
                return 0.0
            return float(v * 100.0 if v <= 1.0 and v > 0 else v)

        hybrid_c = round(_clean_conf(item.get("hybrid_conf") or item.get("hybrid", {}).get("confidence") or item.get("classification", {}).get("confidence")), 2)
        r_pred = item.get("resnet50_pred") or item.get("resnet50", {}).get("prediction") or "N/A"
        r_conf = round(_clean_conf(item.get("resnet50_conf") or item.get("resnet50", {}).get("confidence")), 2)
        d_pred = item.get("densenet_pred") or item.get("densenet121", {}).get("prediction") or item.get("densenet", {}).get("prediction") or "N/A"
        d_conf = round(_clean_conf(item.get("densenet_conf") or item.get("densenet121", {}).get("confidence") or item.get("densenet", {}).get("confidence")), 2)

        # 6. Class Probabilities
        probs = (
            item.get("classification", {}).get("probabilities") or
            item.get("probabilities") or
            item.get("hybrid", {}).get("probabilities") or {}
        )
        def _get_prob(key):
            val = _to_float(probs.get(key), 0.0)
            return round(float(val * 100.0 if val <= 1.0 and val > 0 else val), 2)

        p_all = _get_prob("ALL")
        p_aml = _get_prob("AML")
        p_cll = _get_prob("CLL")
        p_cml = _get_prob("CML")
        p_normal = _get_prob("Normal")

        sess_id = item.get("session_id") or "N/A"

        # Assemble Row Values (30 items)
        row_data = [
            idx,
            fname,
            val_status,
            int(w) if w else "N/A",
            int(h) if h else "N/A",
            fmt,
            color_mode,
            orig_kb,
            int(orig_bytes),
            comp_kb,
            int(comp_bytes),
            qual,
            reduction,
            comp_ratio,
            psnr_disp,
            ssim_disp,
            mae_disp,
            pred_cls,
            full_diag,
            hybrid_c,
            r_pred,
            r_conf,
            d_pred,
            d_conf,
            p_all,
            p_aml,
            p_cll,
            p_cml,
            p_normal,
            sess_id
        ]

        ws_data.row_dimensions[row_num].height = 20
        for col_idx, (col_def, val) in enumerate(zip(columns, row_data), start=1):
            cell = ws_data.cell(row=row_num, column=col_idx, value=val)
            cell.font = data_bold_font if col_def["id"] in ("filename", "pred_class", "confidence") else data_font
            cell.alignment = col_def["align"]
            cell.border = border_thin

            if "fmt" in col_def and isinstance(val, (int, float)):
                cell.number_format = col_def["fmt"]

            # Alternating subtle zebra striping
            if row_num % 2 == 1:
                cell.fill = fill_zebra

        row_num += 1

    # -------------------------------------------------------------------------
    # 5. Master Table Final Summary & Average Row
    # -------------------------------------------------------------------------
    summary_row = row_num
    ws_data.row_dimensions[summary_row].height = 24

    summary_values = {
        "index": "SUMMARY",
        "filename": f"Total Cohort: {total_count} Slides",
        "validation": f"{len(valid_items)} Valid ({valid_rate:.1f}%)",
        "width": "-",
        "height": "-",
        "format": "-",
        "color_mode": "-",
        "orig_kb": round(_avg(orig_kb_vals), 2),
        "orig_bytes": int(sum(orig_kb_vals) * 1024) if orig_kb_vals else 0,
        "comp_kb": round(_avg(comp_kb_vals), 2),
        "comp_bytes": int(sum(comp_kb_vals) * 1024) if comp_kb_vals else 0,
        "quality": 50.0,
        "reduction": round(_avg(reduction_vals), 2),
        "ratio": round(_avg(ratio_vals), 2),
        "psnr": round(_avg(psnr_vals), 2),
        "ssim": round(_avg(ssim_vals), 4),
        "mae": round(_avg(mae_vals), 4),
        "pred_class": "Cohort Averages",
        "full_diagnosis": f"{total_classified} Diagnostic Classifications",
        "confidence": round(_avg(hybrid_conf_vals), 2),
        "resnet_pred": "-",
        "resnet_conf": round(_avg(resnet_conf_vals), 2),
        "densenet_pred": "-",
        "densenet_conf": round(_avg(densenet_conf_vals), 2),
        "prob_all": "-",
        "prob_aml": "-",
        "prob_cll": "-",
        "prob_cml": "-",
        "prob_normal": "-",
        "session_id": "-"
    }

    for col_idx, col_def in enumerate(columns, start=1):
        cid = col_def["id"]
        val = summary_values.get(cid, "-")
        cell = ws_data.cell(row=summary_row, column=col_idx, value=val)
        cell.font = summary_label_font
        cell.fill = fill_total
        cell.border = border_double
        cell.alignment = col_def["align"]

        if "fmt" in col_def and isinstance(val, (int, float)):
            cell.number_format = col_def["fmt"]

    # -------------------------------------------------------------------------
    # 6. Apply Excel AutoFilters to Master Table (Row 1 to summary_row - 1)
    # -------------------------------------------------------------------------
    last_col_letter = get_column_letter(len(columns))
    data_last_row = summary_row - 1 if summary_row > 2 else 2
    ws_data.auto_filter.ref = f"A1:{last_col_letter}{data_last_row}"

    # -------------------------------------------------------------------------
    # 7. Auto-Fit Column Widths with Generous Padding to Guarantee Zero Cut-Off
    # -------------------------------------------------------------------------
    # Sheet 1: Summary Sheet Widths
    for col in ws_summary.columns:
        col_letter = get_column_letter(col[0].column)
        max_len = 0
        for cell in col:
            # Skip title banner row in length calculation
            if cell.row in (1, 2):
                continue
            v_str = str(cell.value or "")
            if len(v_str) > max_len:
                max_len = len(v_str)
        ws_summary.column_dimensions[col_letter].width = max(max_len + 4, 18)

    # Sheet 2: Master Data Sheet Widths
    for col_idx, col_def in enumerate(columns, start=1):
        col_letter = get_column_letter(col_idx)
        max_len = len(col_def["name"])
        for r_idx in range(2, summary_row + 1):
            val_str = str(ws_data.cell(row=r_idx, column=col_idx).value or "")
            if len(val_str) > max_len:
                max_len = len(val_str)
        calculated_width = max(max_len + 3, col_def.get("min_width", 14))
        ws_data.column_dimensions[col_letter].width = calculated_width

    # -------------------------------------------------------------------------
    # 8. Save Workbook to Output Path
    # -------------------------------------------------------------------------
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    wb.save(output_path)
    return output_path
