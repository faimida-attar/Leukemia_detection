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


def generate_excel_report(analysis_data, output_path):
    """
    Generate a documented, multi-sheet .xlsx Excel report for analyzed leukemia images.
    
    Sheets:
    1. 'Executive Summary' - Aggregate statistics, batch metrics, and classification distribution.
    2. 'Image Analysis Master Data' - Detailed per-image data with properties, compression,
       reconstruction metrics, predictions, and model probabilities.
    """
    # Normalize input data into a list of items
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

    # Define reusable professional styling tokens
    font_main = "Segoe UI"
    
    title_font = Font(name=font_main, size=15, bold=True, color="FFFFFF")
    subtitle_font = Font(name=font_main, size=10, italic=True, color="E2E8F0")
    section_font = Font(name=font_main, size=11, bold=True, color="0F172A")
    header_font = Font(name=font_main, size=10, bold=True, color="FFFFFF")
    sub_header_font = Font(name=font_main, size=10, bold=True, color="0369A1")
    data_font = Font(name=font_main, size=9, color="1E293B")
    data_bold_font = Font(name=font_main, size=9, bold=True, color="1E293B")
    data_accent_font = Font(name=font_main, size=9, bold=True, color="1E40AF")
    small_desc_font = Font(name=font_main, size=8.5, italic=True, color="64748B")

    fill_brand = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")       # Dark Navy (#1E3A8A)
    fill_header = PatternFill(start_color="1E40AF", end_color="1E40AF", fill_type="solid")      # Navy Blue (#1E40AF)
    fill_sub_hdr = PatternFill(start_color="E0F2FE", end_color="E0F2FE", fill_type="solid")    # Sky Blue light (#E0F2FE)
    fill_metric_hdr = PatternFill(start_color="0284C7", end_color="0284C7", fill_type="solid") # Sky Accent (#0284C7)
    fill_zebra = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")      # Very light slate (#F8FAFC)
    fill_total = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")      # Light Slate (#F1F5F9)

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

    align_center = Alignment(horizontal='center', vertical='center', wrap_text=True)
    align_left = Alignment(horizontal='left', vertical='center')
    align_right = Alignment(horizontal='right', vertical='center')

    # =========================================================================
    # SHEET 1: EXECUTIVE SUMMARY & STATISTICAL AGGREGATES
    # =========================================================================
    ws_summary = wb.active
    ws_summary.title = "Summary & Statistics"
    ws_summary.views.sheetView[0].showGridLines = True

    # 1. Title Banner
    ws_summary.merge_cells("A1:G1")
    title_cell = ws_summary["A1"]
    title_cell.value = "Leukemia Detection & Medical Image Reconstruction — Research Evaluation Report"
    title_cell.font = title_font
    title_cell.fill = fill_brand
    title_cell.alignment = align_left
    ws_summary.row_dimensions[1].height = 36

    ws_summary.merge_cells("A2:G2")
    sub_cell = ws_summary["A2"]
    sub_cell.value = (
        f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  |  "
        "Framework: GAN + CBAM Quality Restoration & ResNet50 + DenseNet121 Hybrid Classification"
    )
    sub_cell.font = subtitle_font
    sub_cell.fill = fill_brand
    sub_cell.alignment = align_left
    ws_summary.row_dimensions[2].height = 20

    # Calculate Aggregates
    total_count = len(items)
    completed_items = [it for it in items if it.get("status") != "processing"]
    valid_items = [it for it in completed_items if it.get("is_valid") is not False]
    invalid_count = len(completed_items) - len(valid_items)

    class_counts = {"ALL": 0, "AML": 0, "CLL": 0, "CML": 0, "Normal": 0}
    psnr_vals = []
    ssim_vals = []
    mae_vals = []
    mse_vals = []
    reduction_vals = []
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
        p = rm.get("psnr_db") if rm.get("psnr_db") is not None else rm.get("psnr")
        s = rm.get("ssim")
        m = rm.get("mae")
        mse_val = rm.get("mse")

        if p is not None and isinstance(p, (int, float)):
            psnr_vals.append(float(p))
        if s is not None and isinstance(s, (int, float)):
            ssim_vals.append(float(s))
        if m is not None and isinstance(m, (int, float)):
            mae_vals.append(float(m))
        if mse_val is not None and isinstance(mse_val, (int, float)):
            mse_vals.append(float(mse_val))

        # Compression reduction
        red = it.get("compression_information", {}).get("reduction")
        if red is not None and isinstance(red, (int, float)):
            reduction_vals.append(float(red))
        else:
            ob = it.get("compression_information", {}).get("original_size_bytes", 0)
            cb = it.get("compression_information", {}).get("compressed_size_bytes", 0)
            if ob > 0 and cb > 0:
                reduction_vals.append(((ob - cb) / ob) * 100.0)

        # Confidences (convert 0-1 range to 0-100% if needed)
        def _get_conf(val):
            if val is None or not isinstance(val, (int, float)):
                return None
            return float(val * 100.0 if val <= 1.0 and val > 0 else val)

        h_c = _get_conf(it.get("hybrid_conf") or it.get("hybrid", {}).get("confidence") or it.get("classification", {}).get("confidence"))
        r_c = _get_conf(it.get("resnet50_conf") or it.get("resnet50", {}).get("confidence"))
        d_c = _get_conf(it.get("densenet_conf") or it.get("densenet121", {}).get("confidence") or it.get("densenet", {}).get("confidence"))

        if h_c is not None: hybrid_conf_vals.append(h_c)
        if r_c is not None: resnet_conf_vals.append(r_c)
        if d_c is not None: densenet_conf_vals.append(d_c)

    # 2. Section: Overview Key-Performance-Indicators Table
    ws_summary["A4"].value = "1. BATCH PROCESSING OVERVIEW"
    ws_summary["A4"].font = section_font

    kpi_headers = ["Total Processed Slides", "Valid Smear Slides", "Excluded / Invalid Slides", "Valid Processing Rate"]
    for col_idx, kh in enumerate(kpi_headers, start=1):
        c = ws_summary.cell(row=5, column=col_idx, value=kh)
        c.font = sub_header_font
        c.fill = fill_sub_hdr
        c.border = border_thin
        c.alignment = align_center

    valid_rate = (len(valid_items) / total_count * 100.0) if total_count > 0 else 0.0
    kpi_values = [total_count, len(valid_items), invalid_count, f"{valid_rate:.1f}%"]
    for col_idx, kv in enumerate(kpi_values, start=1):
        c = ws_summary.cell(row=6, column=col_idx, value=kv)
        c.font = data_bold_font
        c.border = border_thin
        c.alignment = align_center
    ws_summary.row_dimensions[5].height = 24
    ws_summary.row_dimensions[6].height = 24

    # 3. Section: Diagnostic Subtype Classification Distribution
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

    # 4. Section: Aggregate Evaluation Metrics (Reconstruction & Model Confidence)
    curr_row = tot_row + 2
    ws_summary.cell(row=curr_row, column=1, value="3. AGGREGATE RECONSTRUCTION & MODEL PERFORMANCE METRICS").font = section_font
    curr_row += 1

    metric_table_headers = ["Metric Name", "Mean / Aggregate Value", "Unit", "Clinical & Technical Interpretation"]
    for col_idx, mth in enumerate(metric_table_headers, start=1):
        c = ws_summary.cell(row=curr_row, column=col_idx, value=mth)
        c.font = header_font
        c.fill = fill_metric_hdr
        c.border = border_thin
        c.alignment = align_center
    ws_summary.row_dimensions[curr_row].height = 24
    curr_row += 1

    def _avg(lst):
        return sum(lst) / len(lst) if lst else 0.0

    metrics_rows = [
        ("Peak Signal-to-Noise Ratio (PSNR)", round(_avg(psnr_vals), 2), "dB", "Higher indicates superior pixel restoration fidelity (>30 dB is medical-grade)"),
        ("Structural Similarity Index (SSIM)", round(_avg(ssim_vals), 4), "Index (0 to 1)", "Closer to 1.0 preserves cell boundaries, chromatin texture, and cytoplasm"),
        ("Mean Absolute Error (MAE)", round(_avg(mae_vals), 4), "Pixel Error", "Lower indicates minimal absolute pixel deviation after CBAM GAN attention"),
        ("Mean Squared Error (MSE)", round(_avg(mse_vals), 6), "Squared Error", "Lower represents reduced noise variance across restored microscopy images"),
        ("Average Storage Reduction", round(_avg(reduction_vals), 2), "%", "Bandwidth and storage footprint saved through intelligent JPEG compression"),
        ("Hybrid Ensemble Mean Confidence", round(_avg(hybrid_conf_vals), 2), "%", "Average diagnostic certainty combining ResNet50 and DenseNet121 backbones"),
        ("ResNet50 Standalone Mean Confidence", round(_avg(resnet_conf_vals), 2), "%", "Average certainty score from the standalone ResNet50 classifier"),
        ("DenseNet121 Standalone Mean Confidence", round(_avg(densenet_conf_vals), 2), "%", "Average certainty score from the standalone DenseNet121 classifier"),
    ]

    for m_name, m_val, m_unit, m_desc in metrics_rows:
        r_c1 = ws_summary.cell(row=curr_row, column=1, value=m_name)
        r_c2 = ws_summary.cell(row=curr_row, column=2, value=m_val)
        r_c3 = ws_summary.cell(row=curr_row, column=3, value=m_unit)
        r_c4 = ws_summary.cell(row=curr_row, column=4, value=m_desc)

        r_c1.font = data_bold_font
        r_c2.font = data_accent_font
        r_c3.font = data_font
        r_c4.font = small_desc_font

        r_c1.alignment = align_left
        r_c2.alignment = align_right
        r_c3.alignment = align_center
        r_c4.alignment = align_left

        for c_idx in range(1, 5):
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

    # Master Table Column Definitions
    columns = [
        {"id": "index", "name": "Slide #", "width": 10, "align": align_center},
        {"id": "filename", "name": "Filename", "width": 30, "align": align_left},
        {"id": "validation", "name": "Validation Status", "width": 18, "align": align_center},
        {"id": "width", "name": "Width (px)", "width": 14, "align": align_right, "fmt": "#,##0"},
        {"id": "height", "name": "Height (px)", "width": 14, "align": align_right, "fmt": "#,##0"},
        {"id": "format", "name": "Image Format", "width": 15, "align": align_center},
        {"id": "color_mode", "name": "Color Mode", "width": 14, "align": align_center},
        {"id": "orig_kb", "name": "Original Size (KB)", "width": 18, "align": align_right, "fmt": "#,##0.00"},
        {"id": "orig_bytes", "name": "Original Size (Bytes)", "width": 20, "align": align_right, "fmt": "#,##0"},
        {"id": "comp_kb", "name": "Compressed Size (KB)", "width": 20, "align": align_right, "fmt": "#,##0.00"},
        {"id": "comp_bytes", "name": "Compressed Size (Bytes)", "width": 22, "align": align_right, "fmt": "#,##0"},
        {"id": "quality", "name": "Compression Quality (%)", "width": 24, "align": align_right, "fmt": "0.0"},
        {"id": "reduction", "name": "Size Reduction (%)", "width": 18, "align": align_right, "fmt": '0.00"%"'},
        {"id": "ratio", "name": "Compression Ratio (:1)", "width": 22, "align": align_right, "fmt": "0.00"},
        {"id": "psnr", "name": "PSNR (dB)", "width": 14, "align": align_right, "fmt": "0.00"},
        {"id": "ssim", "name": "SSIM (0 to 1)", "width": 16, "align": align_right, "fmt": "0.0000"},
        {"id": "mae", "name": "MAE (Pixel Error)", "width": 18, "align": align_right, "fmt": "0.0000"},
        {"id": "mse", "name": "MSE (Squared Error)", "width": 20, "align": align_right, "fmt": "0.000000"},
        {"id": "pred_class", "name": "Predicted Leukemia Class", "width": 24, "align": align_center},
        {"id": "full_diagnosis", "name": "Full Clinical Diagnosis", "width": 32, "align": align_left},
        {"id": "confidence", "name": "Hybrid Confidence (%)", "width": 22, "align": align_right, "fmt": '0.00"%"'},
        {"id": "resnet_pred", "name": "ResNet50 Prediction", "width": 20, "align": align_center},
        {"id": "resnet_conf", "name": "ResNet50 Confidence (%)", "width": 24, "align": align_right, "fmt": '0.00"%"'},
        {"id": "densenet_pred", "name": "DenseNet121 Prediction", "width": 22, "align": align_center},
        {"id": "densenet_conf", "name": "DenseNet121 Confidence (%)", "width": 26, "align": align_right, "fmt": '0.00"%"'},
        {"id": "prob_all", "name": "ALL Prob (%)", "width": 15, "align": align_right, "fmt": '0.00"%"'},
        {"id": "prob_aml", "name": "AML Prob (%)", "width": 15, "align": align_right, "fmt": '0.00"%"'},
        {"id": "prob_cll", "name": "CLL Prob (%)", "width": 15, "align": align_right, "fmt": '0.00"%"'},
        {"id": "prob_cml", "name": "CML Prob (%)", "width": 15, "align": align_right, "fmt": '0.00"%"'},
        {"id": "prob_normal", "name": "Normal Prob (%)", "width": 16, "align": align_right, "fmt": '0.00"%"'},
        {"id": "session_id", "name": "Session ID", "width": 26, "align": align_left}
    ]

    # Write Master Table Headers
    ws_data.row_dimensions[1].height = 28
    for col_idx, col in enumerate(columns, start=1):
        cell = ws_data.cell(row=1, column=col_idx, value=col["name"])
        cell.font = header_font
        cell.fill = fill_header
        cell.border = border_thin
        cell.alignment = align_center

    # Populate Data Rows
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
            item.get("original_dimensions") or ""
        )
        w, h = _parse_dimensions(dim_str)
        fmt = item.get("image_information", {}).get("format") or "JPEG"
        color_mode = item.get("image_information", {}).get("color_mode") or "RGB"

        # 3. Sizes & Compression
        orig_bytes = (
            item.get("compression_information", {}).get("original_size_bytes") or
            item.get("compression", {}).get("original_size_bytes") or
            item.get("image_information", {}).get("file_size_bytes") or 0
        )
        comp_bytes = (
            item.get("compression_information", {}).get("compressed_size_bytes") or
            item.get("compression", {}).get("compressed_size_bytes") or 0
        )
        orig_kb = round(orig_bytes / 1024.0, 2) if orig_bytes else 0.0
        comp_kb = round(comp_bytes / 1024.0, 2) if comp_bytes else 0.0

        qual = float(item.get("compression_information", {}).get("quality", 50))
        reduction = item.get("compression_information", {}).get("reduction")
        if reduction is not None:
            reduction = float(reduction)
        elif orig_bytes > 0 and comp_bytes > 0:
            reduction = round(((orig_bytes - comp_bytes) / orig_bytes) * 100.0, 2)
        else:
            reduction = 0.0

        if comp_bytes > 0:
            comp_ratio = round(orig_bytes / comp_bytes, 2)
        elif reduction > 0 and reduction < 100:
            comp_ratio = round(100.0 / (100.0 - reduction), 2)
        else:
            comp_ratio = 1.0

        # 4. Reconstruction Metrics
        rm = item.get("reconstruction_metrics", {})
        psnr_val = rm.get("psnr_db") if rm.get("psnr_db") is not None else rm.get("psnr", 0.0)
        ssim_val = rm.get("ssim", 0.0)
        mae_val = rm.get("mae", 0.0)
        mse_val = rm.get("mse", 0.0)

        # 5. Predictions & Confidence
        pred_cls = (
            item.get("hybrid_pred") or
            item.get("hybrid", {}).get("prediction") or
            item.get("classification", {}).get("prediction") or
            item.get("resnet50_pred") or
            "N/A"
        )
        full_diag = DISEASE_FULL_NAMES.get(pred_cls, pred_cls)

        def _clean_conf(c_val):
            if c_val is None:
                return 0.0
            return float(c_val * 100.0 if c_val <= 1.0 and c_val > 0 else c_val)

        hybrid_c = _clean_conf(item.get("hybrid_conf") or item.get("hybrid", {}).get("confidence") or item.get("classification", {}).get("confidence"))
        r_pred = item.get("resnet50_pred") or item.get("resnet50", {}).get("prediction") or "N/A"
        r_conf = _clean_conf(item.get("resnet50_conf") or item.get("resnet50", {}).get("confidence"))
        d_pred = item.get("densenet_pred") or item.get("densenet121", {}).get("prediction") or item.get("densenet", {}).get("prediction") or "N/A"
        d_conf = _clean_conf(item.get("densenet_conf") or item.get("densenet121", {}).get("confidence") or item.get("densenet", {}).get("confidence"))

        # 6. Probabilities
        probs = (
            item.get("classification", {}).get("probabilities") or
            item.get("probabilities") or
            item.get("hybrid", {}).get("probabilities") or {}
        )
        def _get_prob(key):
            val = probs.get(key, 0.0)
            return float(val * 100.0 if val <= 1.0 and val > 0 else val)

        p_all = _get_prob("ALL")
        p_aml = _get_prob("AML")
        p_cll = _get_prob("CLL")
        p_cml = _get_prob("CML")
        p_normal = _get_prob("Normal")

        sess_id = item.get("session_id") or "N/A"

        # Map to columns
        row_data = [
            idx,
            fname,
            val_status,
            w or "N/A",
            h or "N/A",
            fmt,
            color_mode,
            orig_kb,
            orig_bytes,
            comp_kb,
            comp_bytes,
            qual,
            reduction,
            comp_ratio,
            round(float(psnr_val), 2),
            round(float(ssim_val), 4),
            round(float(mae_val), 4),
            round(float(mse_val), 6),
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

            # Alternating row background for visual excellence
            if row_num % 2 == 1:
                cell.fill = fill_zebra

        row_num += 1

    # Auto-adjust column widths for both sheets
    for ws in [ws_summary, ws_data]:
        for col in ws.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                # Skip merged banner row in length calculation
                if ws == ws_summary and cell.row in (1, 2):
                    continue
                val_str = str(cell.value or "")
                if len(val_str) > max_len:
                    max_len = len(val_str)
            # Add padding
            ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

    # Save to output path
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    wb.save(output_path)
    return output_path
