import streamlit as st
from PIL import Image
import numpy as np
import tempfile
import os
import json 
import fpdf
from core.raw_processor import load_raw_image
from core.metadata import extract_metadata
from core.diagnostics import calculate_channel_stats, generate_histogram_plot, calculate_image_score, generate_clipping_mask
from core.recommendations import generate_editing_steps



st.set_page_config(page_title="AstroVision", layout="wide")

st.title("AstroVision")
st.caption("RAW Intelligence & Photo Analysis Platform")

# Sidebar Configuration
st.sidebar.header("Analysis Settings")
analysis_mode = st.sidebar.selectbox(
    "Scoring Mode",
    options=["Auto Detect", "Astrophotography", "General Photography"],
    help="Select 'Auto Detect' to let AstroVision automatically categorize day vs. night photos."
)

uploaded_file = st.file_uploader(
    "Upload a RAW Photograph (.DNG, .RAW, .CR2, .NEF, .ARW)", 
    type=["dng", "raw", "cr2", "nef", "arw"]
)

if uploaded_file is not None:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".dng") as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        tmp_path = tmp_file.name

    try:
        # Load Image & Metadata
        image_array, engine_used = load_raw_image(tmp_path)
        meta = extract_metadata(tmp_path)
        
        # Calculate Diagnostics
        stats, max_val = calculate_channel_stats(image_array)
        fig = generate_histogram_plot(image_array, max_val)
        
        # Determine actual mode string for evaluator
        mode_param = "Auto" if analysis_mode == "Auto Detect" else analysis_mode
        score_metrics = calculate_image_score(image_array, stats, mode=mode_param)

        # Top Section: Image Preview & Metadata
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("Image Preview")
            
            # Interactive Clipping Mask Toggle
            show_mask = st.toggle("Show Clipping Mask (Magenta = Highlights, Cyan = Shadows)")

            
            if show_mask:
                mask_array = generate_clipping_mask(image_array, max_val)
                preview_img = Image.fromarray(mask_array)
            else:
                # Safe 8-bit conversion for normal preview display
                scale_factor = 257 if image_array.dtype == np.uint16 else 1
                preview_img = Image.fromarray((image_array / scale_factor).astype('uint8'))
                
            st.image(preview_img, use_container_width=True)
            st.info(f"Engine: **{engine_used}**")

            
        with col2:
            st.subheader("Camera Metadata")
            st.metric("Camera", meta["Camera"])
            st.metric("ISO", meta["ISO"])
            st.metric("Shutter Speed", meta["Shutter Speed"])
            st.metric("Aperture", meta["Aperture"])
            st.metric("Focal Length", meta["Focal Length"])
            st.metric("Resolution", f"{image_array.shape[1]} x {image_array.shape[0]}")

        st.divider()

                # Quality Score Banner & Detailed Breakdown Cards
        st.subheader("Photo Quality Analysis")
        a_col1, a_col2, a_col3, a_col4 = st.columns(4)
        a_col1.metric("Overall Score", f"{score_metrics['score']} / 100")
        a_col2.metric("Assessment", score_metrics['grade'])
        a_col3.metric("Evaluated Mode", score_metrics['detected_mode'])
        a_col4.metric("Avg Luminance", f"{score_metrics['mean_lum']}%")

        st.markdown("##### Sub-Metric Breakdown")
        card_cols = st.columns(3)
        for idx, sub in enumerate(score_metrics["sub_scores"]):
            with card_cols[idx]:
                st.caption(f"**{sub['label']}** — `{sub['score']}/100`")
                st.progress(int(sub['score']) / 100)
        
        st.divider()

        # Bottom Section: Diagnostics & Histogram
        st.subheader("Signal Diagnostics")
        
        diag_col1, diag_col2 = st.columns([2, 1])
        
        with diag_col1:
            st.plotly_chart(fig, use_container_width=True)
            
        with diag_col2:
            st.markdown("### Channel Metrics")
            for channel in ['Red', 'Green', 'Blue']:
                st.markdown(f"**{channel} Channel**")
                c_col1, c_col2 = st.columns(2)
                c_col1.caption(f"Crushed Shadows: `{stats[channel]['shadow_clipped']:.2f}%`")
                c_col2.caption(f"Blown Highlights: `{stats[channel]['highlight_clipped']:.2f}%`")

                st.divider()

                # Tailored Editing Steps
        st.subheader("Tailored Post-Processing Guide")
        st.caption("Step-by-step editing recipes generated specifically for this photograph.")

        # Pass image_array as well so gradient analysis can run
        editing_steps = generate_editing_steps(score_metrics, stats, image_array=image_array)

        for idx, step in enumerate(editing_steps, 1):
            with st.expander(f"**Step {idx}: {step['title']}**", expanded=True):
                st.markdown(f"**🛠️ Action:** {step['action']}")
                st.markdown(f"**💡 Why this is needed:** {step['reasoning']}")



    except Exception as e:
        st.error(f"Failed to process image: {e}")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        from fpdf import FPDF
        import tempfile
        
        st.markdown("---")
        st.subheader("Export Diagnostics")
        
        # 1. Initialize PDF
        pdf = FPDF()
        pdf.add_page()
        
        # 2. Add Title
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 10, "AstroVision Diagnostic Report", ln=True, align="C")
        pdf.ln(10)
        
        # 3. Add Core Metrics
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, f"File Analysis: {uploaded_file.name}", ln=True)
        pdf.set_font("Arial", '', 12)
        pdf.cell(0, 8, f"Evaluated Mode: {score_metrics['detected_mode']}", ln=True)
        pdf.cell(0, 8, f"Overall Score: {score_metrics['score']} / 100", ln=True)
        pdf.cell(0, 8, f"Assessment: {score_metrics['grade']}", ln=True)
        pdf.ln(5)
        
        # 4. Add Sub-Metrics
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, "Sub-Metric Breakdown:", ln=True)
        pdf.set_font("Arial", '', 12)
        for sub in score_metrics["sub_scores"]:
            pdf.cell(0, 8, f"- {sub['label']}: {sub['score']}/100", ln=True)
        pdf.ln(5)
        
        # 5. Add Channel Diagnostics
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, "Channel Clipping:", ln=True)
        pdf.set_font("Arial", '', 12)
        for channel in ['Red', 'Green', 'Blue']:
            shadows = stats[channel]['shadow_clipped']
            highlights = stats[channel]['highlight_clipped']
            pdf.cell(0, 8, f"{channel} Channel: {shadows:.2f}% Shadows | {highlights:.2f}% Highlights", ln=True)
        
        # 6. Save to temp file and read as bytes for Streamlit
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
            pdf.output(tmp_pdf.name)
            with open(tmp_pdf.name, "rb") as f:
                pdf_bytes = f.read()
                
        # 7. Render Download Button
        
        st.download_button(
            label="⬇️ Download PDF Report",
            data=pdf_bytes,
            file_name=f"{uploaded_file.name.split('.')[0]}_report.pdf",
            mime="application/pdf",
            type="primary"
        )

else:
    st.info("Please drag and drop or select a RAW photograph above to run diagnostics.")
