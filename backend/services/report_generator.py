import os
import io
import base64
import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image as RLImage,
    HRFlowable,
    KeepTogether
)

def _get_rl_image(img_source, width=105, height=105):
    """
    Safely load an image for ReportLab from either a local file path,
    a base64 data URI, or a raw base64 string.
    """
    if not img_source:
        return None
    try:
        # 1. Local file path check
        if isinstance(img_source, str) and os.path.exists(img_source):
            return RLImage(img_source, width=width, height=height)

        # 2. Base64 data URL or raw string
        if isinstance(img_source, str) and (img_source.startswith('data:image') or len(img_source) > 200):
            raw_b64 = img_source.split(',', 1)[1] if ',' in img_source else img_source
            img_bytes = base64.b64decode(raw_b64)
            buf = io.BytesIO(img_bytes)
            buf.seek(0)
            return RLImage(buf, width=width, height=height)
    except Exception as e:
        print(f"Warning: Failed to load image for PDF report: {e}")
    return None

def generate_pdf_report(analysis_results, output_pdf_path):
    """
    Generate a professional academic research report PDF matching the exact
    research benchmark format with dynamic metrics, dimensions, and artifacts.
    """
    if isinstance(analysis_results, list):
        analysis_results = analysis_results[0] if len(analysis_results) > 0 else {}

    # Target printable area: Letter is 612 x 792 pt.
    # Margins: 32 left/right, 26 top/bottom -> usable width = 548 pt, usable height = 740 pt.
    doc = SimpleDocTemplate(
        output_pdf_path,
        pagesize=letter,
        rightMargin=32,
        leftMargin=32,
        topMargin=26,
        bottomMargin=26
    )

    styles = getSampleStyleSheet()

    # Medical research document typography
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=15,
        leading=19,
        textColor=colors.HexColor('#1e40af'),
        alignment=1,  # Center
        spaceAfter=3
    )

    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor('#475569'),
        alignment=1,
        spaceAfter=6
    )

    heading2_style = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontSize=11,
        leading=14,
        textColor=colors.HexColor('#0369a1'),
        spaceBefore=7,
        spaceAfter=4,
        keepWithNext=True
    )

    normal_style = ParagraphStyle(
        'NormalText',
        parent=styles['Normal'],
        fontSize=8.5,
        leading=11.5,
        textColor=colors.HexColor('#1e293b')
    )


    story = []

    # Title & Subtitle Banner
    story.append(Paragraph("Next-Generation Reconstruction-Driven Deep Learning Framework", title_style))
    story.append(Paragraph("Leukemia Detection & Analysis Research Report", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#2563eb'), spaceAfter=8))

    # Dynamic Metadata Extraction
    img_info = analysis_results.get('image_information', {})
    fname = (
        img_info.get('filename') or
        analysis_results.get('selectedFileName') or
        analysis_results.get('filename') or
        analysis_results.get('file_name') or
        'slide.png'
    )
    dims = (
        img_info.get('original_dimensions') or
        img_info.get('dimensions') or
        analysis_results.get('original_dimensions') or
        analysis_results.get('dimensions') or
        'N/A'
    )
    orig_sz = (
        img_info.get('original_file_size_formatted') or
        analysis_results.get('original_file_size_formatted') or
        analysis_results.get('original_size_formatted') or
        'N/A'
    )
    recon_sz = (
        img_info.get('reconstructed_file_size_formatted') or
        analysis_results.get('reconstructed_file_size_formatted') or
        analysis_results.get('reconstructed_size_formatted') or
        'N/A'
    )
    v_stat = (
        analysis_results.get('validation_status') or
        analysis_results.get('validation_details', {}).get('status') or
        ('Valid Microscopy Image' if analysis_results.get('is_valid') is not False else 'Invalid Image')
    )

    # General Information Table (4-column layout matching exact format)
    info_data = [
        [Paragraph("<b>Report Date:</b>", normal_style),
         Paragraph(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), normal_style),
         Paragraph("<b>Validation Status:</b>", normal_style),
         Paragraph(f"<font color='green'><b>{v_stat}</b></font>", normal_style)],
        [Paragraph("<b>File Name:</b>", normal_style),
         Paragraph(str(fname), normal_style),
         Paragraph("<b>Dimensions:</b>", normal_style),
         Paragraph(str(dims), normal_style)],
        [Paragraph("<b>Original Size:</b>", normal_style),
         Paragraph(str(orig_sz), normal_style),
         Paragraph("<b>Reconstructed Size:</b>", normal_style),
         Paragraph(str(recon_sz), normal_style)],
    ]
    info_table = Table(info_data, colWidths=[105, 170, 115, 158])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f0f9ff')),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#bae6fd')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e0f2fe')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 6))

    # 1. GAN + CBAM Reconstruction Evaluation Metrics
    story.append(Paragraph("1. GAN + CBAM Reconstruction Evaluation Metrics", heading2_style))
    recon_metrics = analysis_results.get('reconstruction_metrics', {})
    p_raw = recon_metrics.get('psnr_db') if recon_metrics.get('psnr_db') is not None else recon_metrics.get('psnr', 'N/A')
    p_val = f"{p_raw:.2f}" if isinstance(p_raw, (int, float)) else str(p_raw)

    s_raw = recon_metrics.get('ssim', 'N/A')
    s_val = f"{s_raw:.4f}" if isinstance(s_raw, (int, float)) else str(s_raw)

    m_raw = recon_metrics.get('mae', 'N/A')
    m_val = f"{m_raw:.4f}" if isinstance(m_raw, (int, float)) else str(m_raw)

    metrics_data = [
        [Paragraph("<b>Metric</b>", normal_style),
         Paragraph("<b>Value</b>", normal_style),
         Paragraph("<b>Interpretation</b>", normal_style)],
        [Paragraph("PSNR (Peak Signal-to-Noise Ratio)", normal_style),
         Paragraph(f"<b>{p_val} dB</b>", normal_style),
         Paragraph("Higher indicates superior signal reconstruction fidelity", normal_style)],
        [Paragraph("SSIM (Structural Similarity Index)", normal_style),
         Paragraph(f"<b>{s_val}</b>", normal_style),
         Paragraph("Structural similarity score (1.0 = identical)", normal_style)],
        [Paragraph("MAE (Mean Absolute Error)", normal_style),
         Paragraph(f"<b>{m_val}</b>", normal_style),
         Paragraph("Lower indicates minimal pixel error deviation", normal_style)],
    ]
    metrics_table = Table(metrics_data, colWidths=[200, 100, 248])
    metrics_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#dbeafe')),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#93c5fd')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#eff6ff')),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
    ]))
    story.append(metrics_table)
    story.append(Spacer(1, 6))

    # 2. Hybrid Multiclass Leukemia Classification Result
    story.append(Paragraph("2. Hybrid Multiclass Leukemia Classification Result", heading2_style))
    cls_res = analysis_results.get('classification', {})
    prediction = (
        analysis_results.get('hybrid_pred') or
        analysis_results.get('hybrid', {}).get('prediction') or
        cls_res.get('prediction', 'N/A')
    )
    disease_map = {
        "ALL": "Acute Lymphoblastic Leukemia",
        "AML": "Acute Myeloid Leukemia",
        "CLL": "Chronic Lymphocytic Leukemia",
        "CML": "Chronic Myeloid Leukemia",
        "Normal": "Normal Non-Leukemic Smear"
    }
    full_name = cls_res.get('full_name') or disease_map.get(prediction, prediction)
    c_raw = (
        analysis_results.get('hybrid_conf') or
        analysis_results.get('hybrid', {}).get('confidence') or
        cls_res.get('confidence', 0.0)
    )
    confidence = float(c_raw * 100.0 if (isinstance(c_raw, (int, float)) and c_raw <= 1.0 and c_raw > 0) else (c_raw or 0.0))

    cls_data = [
        [Paragraph("<b>Predicted Leukemia Type:</b>", normal_style),
         Paragraph(f"<font color='#1e40af' size=10><b>{prediction} ({full_name})</b></font>", normal_style)],
        [Paragraph("<b>Hybrid Model Confidence Score:</b>", normal_style),
         Paragraph(f"<b>{confidence:.2f}%</b>", normal_style)]
    ]
    cls_table = Table(cls_data, colWidths=[180, 368])
    cls_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(cls_table)
    story.append(Spacer(1, 6))

    # Multiclass Probabilities Breakdown Table
    probs = (
        analysis_results.get('hybrid', {}).get('probabilities') or
        cls_res.get('probabilities') or
        analysis_results.get('probabilities', {})
    )
    if probs:
        prob_header = [
            Paragraph("<b>Class</b>", normal_style),
            Paragraph("<b>Full Class Description</b>", normal_style),
            Paragraph("<b>Probability</b>", normal_style)
        ]
        prob_rows = [prob_header]
        class_full_names = {
            "ALL": "Acute Lymphoblastic Leukemia",
            "AML": "Acute Myeloid Leukemia",
            "CLL": "Chronic Lymphocytic Leukemia",
            "CML": "Chronic Myeloid Leukemia",
            "Normal": "Normal Non-Leukemic Smear"
        }
        for k in ["ALL", "AML", "CLL", "CML", "Normal"]:
            if k in probs:
                v = probs[k]
                p_str = f"{v*100.0:.2f}%" if v <= 1.0 else f"{v:.2f}%"
                prob_rows.append([
                    Paragraph(f"<b>{k}</b>", normal_style),
                    Paragraph(class_full_names.get(k, k), normal_style),
                    Paragraph(f"<b>{p_str}</b>", normal_style)
                ])
        # Include any extra classes if present
        for k, v in probs.items():
            if k not in ["ALL", "AML", "CLL", "CML", "Normal"]:
                p_str = f"{v*100.0:.2f}%" if v <= 1.0 else f"{v:.2f}%"
                prob_rows.append([
                    Paragraph(f"<b>{k}</b>", normal_style),
                    Paragraph(class_full_names.get(k, k), normal_style),
                    Paragraph(f"<b>{p_str}</b>", normal_style)
                ])

        prob_table = Table(prob_rows, colWidths=[90, 310, 148])
        prob_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#e0f2fe')),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#bae6fd')),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#f0f9ff')),
            ('TOPPADDING', (0,0), (-1,-1), 2),
            ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ]))
        story.append(prob_table)
        story.append(Spacer(1, 7))

    # 3. Microscopic Image Artifacts & Grad-CAM Explainability
    img_paths = analysis_results.get('image_paths', {})
    images_dict = analysis_results.get('images', {})

    orig_img = _get_rl_image(img_paths.get('original') or images_dict.get('original'), width=105, height=105)
    recon_img = _get_rl_image(img_paths.get('reconstructed') or images_dict.get('reconstructed'), width=105, height=105)
    gradcam_img = _get_rl_image(img_paths.get('gradcam') or images_dict.get('gradcam'), width=105, height=105)

    img_cells = []
    if orig_img:
        img_cells.append((Paragraph("<b>Original Slide</b>", normal_style), orig_img))
    if recon_img:
        img_cells.append((Paragraph("<b>GAN+CBAM Output</b>", normal_style), recon_img))
    if gradcam_img:
        img_cells.append((Paragraph("<b>Grad-CAM Overlay</b>", normal_style), gradcam_img))

    sec3_elements = []
    sec3_elements.append(Paragraph("3. Microscopic Image Artifacts & Grad-CAM Explainability", heading2_style))

    if img_cells:
        headers = [c[0] for c in img_cells]
        imgs = [c[1] for c in img_cells]
        col_w = int(548 / len(img_cells))
        img_table = Table([headers, imgs], colWidths=[col_w] * len(img_cells))
        img_table.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
            ('TOPPADDING', (0,0), (-1,-1), 3),
            ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ]))
        sec3_elements.append(img_table)



    # Keep Section 3 together so table headers and images never get separated across pages
    story.append(KeepTogether(sec3_elements))

    doc.build(story)
    return output_pdf_path
