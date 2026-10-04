import numpy as np
import plotly.graph_objects as go

def calculate_channel_stats(image_array):
    """
    Calculates signal metrics and clipping percentages for RGB channels.
    """
    stats = {}
    channels = ['Red', 'Green', 'Blue']
    
    max_val = 65535 if image_array.dtype == np.uint16 else 255
    
    for i, color in enumerate(channels):
        channel_data = image_array[:, :, i]
        
        shadow_clipped = np.sum(channel_data == 0) / channel_data.size * 100
        highlight_clipped = np.sum(channel_data >= max_val - 1) / channel_data.size * 100
        
        # Cast NumPy values to native Python types so JSON can serialize them
        stats[color] = {
            "mean": float(np.mean(channel_data)),
            "std": float(np.std(channel_data)),
            "min": int(np.min(channel_data)),
            "max": int(np.max(channel_data)),
            "shadow_clipped": float(shadow_clipped),
            "highlight_clipped": float(highlight_clipped)
        }
        
    return stats, max_val



def generate_histogram_plot(image_array, max_val):
    """
    Generates an interactive Plotly RGB histogram.
    """
    fig = go.Figure()
    colors = ['red', 'green', 'blue']
    channel_names = ['Red', 'Green', 'Blue']
    
    step = max(1, image_array.shape[0] // 500)
    sampled_array = image_array[::step, ::step, :]

    for i, color in enumerate(colors):
        channel_data = sampled_array[:, :, i].ravel()
        
        counts, bins = np.histogram(channel_data, bins=128, range=(0, max_val))
        
        fig.add_trace(go.Scatter(
            x=bins[:-1], 
            y=counts,
            name=channel_names[i],
            line=dict(color=color, width=1.5),
            fill='tozeroy',
            opacity=0.4
        ))

    fig.update_layout(
        title="RGB Signal Distribution (Histogram)",
        xaxis_title="Pixel Intensity",
        yaxis_title="Pixel Count",
        template="plotly_dark",
        margin=dict(l=20, r=20, t=40, b=20),
        height=320,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    return fig


def calculate_image_score(image_array, stats, mode="Auto"):
    """
    Evaluates image quality with mode support for both Astrophotography 
    and General Photography, returning detailed sub-metric breakdowns.
    """
    if image_array.ndim == 3:
        luminance = 0.299 * image_array[:, :, 0] + 0.587 * image_array[:, :, 1] + 0.114 * image_array[:, :, 2]
    else:
        luminance = image_array

    max_val = 65535 if image_array.dtype == np.uint16 else 255
    norm_lum = luminance / max_val * 100.0

    mean_lum = np.mean(norm_lum)
    std_lum = np.std(norm_lum)
    # Auto-detect mode if set to "Auto"
    # Adjusted threshold: Lower mean luminance or high shadow percentage triggers Astro mode
    # Auto-detect mode using multi-factor histogram analysis
    # Auto-detect mode using signal mass & active pixel analysis
    if mode == "Auto":
        # 1. Mask out absolute black letterboxing/padding (pixels <= 1% brightness)
        active_mask = norm_lum > 1.0
        active_pixels = norm_lum[active_mask] if np.sum(active_mask) > 0 else norm_lum

        # 2. Calculate peak position (mode) of active pixel histogram
        counts, bin_edges = np.histogram(active_pixels, bins=50, range=(0, 100))
        peak_bin_center = (bin_edges[np.argmax(counts)] + bin_edges[np.argmax(counts) + 1]) / 2.0

        # 3. Calculate percentage of active pixels residing in the bottom shadow/mid region (< 35% intensity)
        dark_signal_mass = np.sum(active_pixels < 35.0) / active_pixels.size * 100.0

        # ASTRO DECISION LOGIC:
        # If the histogram peak sits in the lower 25% OR over 60% of active pixels are dark signal mass
        mode = "Astrophotography" if (peak_bin_center < 25.0 or dark_signal_mass > 60.0) else "General Photography"



    # --- ASTROPHOTOGRAPHY MODE ---
    if mode == "Astrophotography":
        dark_threshold = np.percentile(luminance, 25)
        background_pixels = luminance[luminance <= dark_threshold]
        bg_noise = np.std(background_pixels) if background_pixels.size > 0 else 1.0
        
        m1_score = max(0, 100 - (bg_noise * 4))
        m1_label = "Background Noise"
        
        signal_range = np.max(luminance) - np.mean(background_pixels) if background_pixels.size > 0 else 1.0
        m2_score = min(100, (signal_range / np.max(luminance)) * 100) if np.max(luminance) > 0 else 0
        m2_label = "Dynamic Range"

        avg_highlight_clip = sum(stats[c]['highlight_clipped'] for c in stats) / 3.0
        m3_score = max(0, 100 - (avg_highlight_clip * 10))
        m3_label = "Highlight Protection"

        final_score = (m1_score * 0.4) + (m2_score * 0.4) + (m3_score * 0.2)
        
    # --- GENERAL PHOTOGRAPHY MODE ---
    else:
        exposure_delta = abs(mean_lum - 50.0)
        m1_score = max(0, 100 - (exposure_delta * 1.8))
        m1_label = "Exposure Balance"

        m2_score = min(100, (std_lum / 25.0) * 100)
        m2_label = "Contrast & Dynamics"

        avg_shadow_clip = sum(stats[c]['shadow_clipped'] for c in stats) / 3.0
        avg_highlight_clip = sum(stats[c]['highlight_clipped'] for c in stats) / 3.0
        clipping_penalty = (avg_shadow_clip * 1.5) + (avg_highlight_clip * 2.0)
        m3_score = max(0, 100 - clipping_penalty)
        m3_label = "Detail Preservation"

        final_score = (m1_score * 0.4) + (m2_score * 0.3) + (m3_score * 0.3)

    final_score = round(max(0, min(100, final_score)), 1)

    if final_score >= 80:
        grade = "Excellent (Well-Exposed)" if mode != "Astrophotography" else "Excellent (Ideal for Stacking)"
    elif final_score >= 60:
        grade = "Good (Minor Imbalance)"
    else:
        grade = "Suboptimal (Imbalanced)"

    return {
        "score": final_score,
        "grade": grade,
        "detected_mode": mode,
        "mean_lum": round(float(mean_lum), 1),
        "std_lum": round(float(std_lum), 1),
        "sub_scores": [
            {"label": m1_label, "score": round(float(m1_score), 1)},
            {"label": m2_label, "score": round(float(m2_score), 1)},
            {"label": m3_label, "score": round(float(m3_score), 1)}
        ]
    }
def generate_clipping_mask(image_array, max_val):
    """
    Generates a visual mask overlaying red on blown highlights 
    and blue on crushed shadows.
    """
    # Safely convert to 8-bit for web display
    scale_factor = 257 if image_array.dtype == np.uint16 else 1
    mask_display = (image_array / scale_factor).astype(np.uint8)
        
    # Create boolean masks identifying pure black (0) and pure white (max_val)
    shadow_mask = np.any(image_array == 0, axis=-1)
    highlight_mask = np.any(image_array >= (max_val - 1), axis=-1)
    
    # Paint the flagged pixels (RGB)
    # Paint the flagged pixels (RGB)
    mask_display[shadow_mask] = [0, 255, 255]      # Neon Cyan for crushed shadows
    mask_display[highlight_mask] = [255, 0, 255]   # Neon Magenta for blown highlights

    
    return mask_display