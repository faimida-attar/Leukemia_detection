import os
import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage, HRFlowable

def generate_pdf_report(analysis_results, output_pdf_path):
    """
    Generate a professional academic research report PDF for the leukemia analysis session.
    """
    doc = SimpleDocTemplate(
        output_pdf_path,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    
    # Custom bright medical styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#1e40af'),
        alignment=1, # Center
        spaceAfter=6
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontSize=11,
        leading=14,
        textColor=colors.HexColor('#475569'),
        alignment=1,
        spaceAfter=15
    )

    heading2_style = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontSize=13,
        leading=16,
        textColor=colors.HexColor('#0369a1'),
        spaceBefore=12,
        spaceAfter=6
    )

    normal_style = ParagraphStyle(
        'NormalText',
        parent=styles['Normal'],
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor('#1e293b')
    )

    disclaimer_style = ParagraphStyle(
        'DisclaimerText',
        parent=styles['Normal'],
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor('#dc2626'),
        alignment=1
    )

    story = []

    # Title & Subtitle
    story.append(Paragraph("Next-Generation Reconstruction-Driven Deep Learning Framework", title_style))
    story.append(Paragraph("Leukemia Detection & Analysis Research Report", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#2563eb'), spaceAfter=12))

    # General Information Table
    info_data = [
        [Paragraph("<b>Report Date:</b>", normal_style), Paragraph(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), normal_style),
         Paragraph("<b>Validation Status:</b>", normal_style), Paragraph(f"<font color='green'><b>{analysis_results.get('validation_status', 'Valid')}</b></font>", normal_style)],
        [Paragraph("<b>File Name:</b>", normal_style), Paragraph(str(analysis_results.get('image_information', {}).get('filename', 'slide.png')), normal_style),
         Paragraph("<b>Dimensions:</b>", normal_style), Paragraph(str(analysis_results.get('image_information', {}).get('dimensions', 'N/A')), normal_style)],
        [Paragraph("<b>Compression Level:</b>", normal_style), Paragraph(f"{analysis_results.get('compression_information', {}).get('quality', 50)}%", normal_style),
         Paragraph("<b>Size Reduction:</b>", normal_style), Paragraph(f"{analysis_results.get('compression_information', {}).get('reduction', 0)}%", normal_style)],
    ]
    info_table = Table(info_data, colWidths=[110, 160, 120, 150])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f0f9ff')),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#bae6fd')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e0f2fe')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 10))

    # Reconstruction Metrics
    story.append(Paragraph("1. GAN + CBAM Reconstruction Evaluation Metrics", heading2_style))
    recon_metrics = analysis_results.get('reconstruction_metrics', {})
    metrics_data = [
        [Paragraph("<b>Metric</b>", normal_style), Paragraph("<b>Value</b>", normal_style), Paragraph("<b>Interpretation</b>", normal_style)],
        [Paragraph("PSNR (Peak Signal-to-Noise Ratio)", normal_style), Paragraph(f"<b>{recon_metrics.get('psnr', 'N/A')} dB</b>", normal_style), Paragraph("Higher indicates superior signal reconstruction fidelity", normal_style)],
        [Paragraph("SSIM (Structural Similarity Index)", normal_style), Paragraph(f"<b>{recon_metrics.get('ssim', 'N/A')}</b>", normal_style), Paragraph("Structural similarity score (1.0 = identical)", normal_style)],
        [Paragraph("MAE (Mean Absolute Error)", normal_style), Paragraph(f"<b>{recon_metrics.get('mae', 'N/A')}</b>", normal_style), Paragraph("Lower indicates minimal pixel error deviation", normal_style)],
    ]
    metrics_table = Table(metrics_data, colWidths=[200, 100, 240])
    metrics_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#dbeafe')),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#93c5fd')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#eff6ff')),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(metrics_table)
    story.append(Spacer(1, 10))

    # Classification Result
    story.append(Paragraph("2. ResNet50 Multiclass Leukemia Classification Result", heading2_style))
    cls_res = analysis_results.get('classification', {})
    prediction = cls_res.get('prediction', 'N/A')
    full_name = cls_res.get('full_name', 'N/A')
    confidence = cls_res.get('confidence', 0.0) * 100.0

    cls_data = [
        [Paragraph("<b>Predicted Leukemia Type:</b>", normal_style), Paragraph(f"<font color='#1e40af' size=11><b>{prediction} ({full_name})</b></font>", normal_style)],
        [Paragraph("<b>Model Confidence Score:</b>", normal_style), Paragraph(f"<b>{confidence:.2f}%</b>", normal_style)]
    ]
    cls_table = Table(cls_data, colWidths=[180, 360])
    cls_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(cls_table)
    story.append(Spacer(1, 10))

    # Class Probabilities Breakdown Table
    probs = cls_res.get('probabilities', {})
    if probs:
        prob_header = [Paragraph("<b>Class</b>", normal_style), Paragraph("<b>Full Class Description</b>", normal_style), Paragraph("<b>Probability</b>", normal_style)]
        prob_rows = [prob_header]
        class_full_names = {
            "ALL": "Acute Lymphoblastic Leukemia",
            "AML": "Acute Myeloid Leukemia",
            "CLL": "Chronic Lymphocytic Leukemia",
            "CML": "Chronic Myeloid Leukemia",
            "Normal": "Normal Non-Leukemic Smear"
        }
        for k, v in probs.items():
            p_str = f"{v*100.0:.2f}%"
            prob_rows.append([
                Paragraph(f"<b>{k}</b>", normal_style),
                Paragraph(class_full_names.get(k, k), normal_style),
                Paragraph(f"<b>{p_str}</b>", normal_style)
            ])
        prob_table = Table(prob_rows, colWidths=[100, 300, 140])
        prob_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#e0f2fe')),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#bae6fd')),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#f0f9ff')),
            ('TOPPADDING', (0,0), (-1,-1), 3),
            ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ]))
        story.append(prob_table)
        story.append(Spacer(1, 12))

    # Image Artifacts (Original, Compressed, Reconstructed, GradCAM)
    story.append(Paragraph("3. Microscopic Image Artifacts & Grad-CAM Explainability", heading2_style))
    img_paths = analysis_results.get('image_paths', {})
    
    img_cells = []
    if img_paths.get('original') and os.path.exists(img_paths['original']):
        img_cells.append([Paragraph("<b>Original Slide</b>", normal_style), RLImage(img_paths['original'], width=120, height=120)])
    if img_paths.get('reconstructed') and os.path.exists(img_paths['reconstructed']):
        img_cells.append([Paragraph("<b>GAN+CBAM Output</b>", normal_style), RLImage(img_paths['reconstructed'], width=120, height=120)])
    if img_paths.get('gradcam') and os.path.exists(img_paths['gradcam']):
        img_cells.append([Paragraph("<b>Grad-CAM Overlay</b>", normal_style), RLImage(img_paths['gradcam'], width=120, height=120)])

    if img_cells:
        headers = [c[0] for c in img_cells]
        imgs = [c[1] for c in img_cells]
        img_table = Table([headers, imgs], colWidths=[180]*len(img_cells))
        img_table.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
            ('TOPPADDING', (0,0), (-1,-1), 5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ]))
        story.append(img_table)

    story.append(Spacer(1, 15))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#cbd5e1'), spaceAfter=10))

    # Research Disclaimer
    story.append(Paragraph(
        "<b>RESEARCH DISCLAIMER:</b> This report is generated automatically by a deep learning research prototype framework. "
        "The classification outputs, metrics, and Grad-CAM visualizations are intended strictly for academic evaluation and clinical research support. "
        "This application does not provide an official medical diagnosis.",
        disclaimer_style
    ))

    doc.build(story)
    return output_pdf_path
