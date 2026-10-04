import numpy as np

def generate_editing_steps(score_metrics, stats, image_array=None):
    """
    Generates a complete, multi-stage editing workflow tailored to the 
    image diagnostics, covering global adjustments, tonal balance, 
    color cast corrections, and detail management.
    """
    mode = score_metrics.get("detected_mode", "General Photography")
    steps = []

    # Safe channel metrics extraction
    r_mean = float(stats.get('Red', {}).get('mean', 0))
    g_mean = float(stats.get('Green', {}).get('mean', 0))
    b_mean = float(stats.get('Blue', {}).get('mean', 0))
    
    avg_shadow_clip = sum(stats[c]["shadow_clipped"] for c in stats) / 3.0 if stats else 0.0
    avg_highlight_clip = sum(stats[c]["highlight_clipped"] for c in stats) / 3.0 if stats else 0.0

    # --- ASTROPHOTOGRAPHY MODE PIPELINE ---
    if mode == "Astrophotography":
        
        # Step 1: Sky Gradient & Light Pollution
        steps.append({
            "title": "Remove Light Pollution & Horizon Gradient",
            "action": "Apply a Linear Gradient Mask from the bottom horizon upward, lowering Exposure (-0.50 EV) and shifting White Balance warmer. In PixInsight, run Automatic Background Extractor (ABE).",
            "reasoning": "Atmospheric airglow and urban light bleed create an unnatural brightness gradient across the lower sky, washing out stars near the horizon."
        })

        # Step 2: White Balance & Color Neutralization
        steps.append({
            "title": "Neutralize Sky Background Color Cast",
            "action": "Adjust White Balance to ~3800K–4200K and tweak Tint to align Red and Blue channel baselines.",
            "reasoning": f"Channel baselines (R:{r_mean:.0f}, G:{g_mean:.0f}, B:{b_mean:.0f}) show color dominance. Aligning RGB baselines turns atmospheric tint into deep space darks."
        })

        # Step 3: Non-Linear Stretching & Core Detail
        steps.append({
            "title": "Set Black Point & Non-Linear Curves Stretch",
            "action": "In Curves, clip the lower 1% of dark pixels to establish the black point, then stretch mid-tones with an S-curve to reveal nebulosity and dust lanes.",
            "reasoning": "RAW astronomical data holds faint signal near the noise floor. Non-linear stretching pulls subtle nebulae into view without blowing out star cores."
        })

        # Step 4: Foreground Masking & Landscape Separation
        steps.append({
            "title": "Isolate & Balance Foreground Elements",
            "action": "Use AI Sky Selection to isolate trees and terrain. Drop foreground highlights to remove glare and add +15 Clarity for branch definition.",
            "reasoning": "Landscapes and foreground trees require separate tone mapping from the sky to prevent harsh halos or artificial horizon edges."
        })

        # Step 5: Noise Reduction & Star Reduction
        steps.append({
            "title": "Apply Background Noise Reduction & Star Minimization",
            "action": "Apply targeted Luminance Noise Reduction (+25 to +35) to sky regions, and use a star reduction tool or lower Clarity on star centers.",
            "reasoning": "Smoothing sensor noise in empty sky background focuses attention on primary targets without bloated stars dominating the frame."
        })

    # --- GENERAL PHOTOGRAPHY MODE PIPELINE ---
    else:
        mean_lum = score_metrics.get("mean_lum", 50.0)

        # Step 1: Global Exposure & Tone Calibration
        exp_action = "Increase global Exposure (+0.30 to +0.60 EV)" if mean_lum < 50 else "Decrease global Exposure (-0.30 to -0.60 EV)"
        steps.append({
            "title": "Establish Base Exposure & Tonal Anchor",
            "action": f"{exp_action} and set White/Black clipping points in the basic panel.",
            "reasoning": f"Average frame luminance sits at {mean_lum:.1f}%. Dialing in base exposure anchors mid-tones before fine-tuning dynamic range."
        })

        # Step 2: Dynamic Range & Highlight/Shadow Recovery
        steps.append({
            "title": "Balance Highlights & Recover Shadow Detail",
            "action": f"Lower Highlights (-30 to -50) and boost Shadows (+20 to +40).",
            "reasoning": f"Current channel clipping shows {avg_shadow_clip:.1f}% shadow compression and {avg_highlight_clip:.1f}% highlight compression. Rebalancing recovers hidden textures."
        })

        # Step 3: Color Temperature & Saturation Balance
        steps.append({
            "title": "Fine-Tune White Balance & Color Vibrance",
            "action": "Adjust Temp/Tint to eliminate unintended color casts, then boost Vibrance (+15) while keeping Saturation neutral.",
            "reasoning": f"Channel statistics (R:{r_mean:.0f}, G:{g_mean:.0f}, B:{b_mean:.0f}) highlight color distributions that need balancing to avoid dominant color shifts."
        })

        # Step 4: Local Contrast & Subject Separation
        steps.append({
            "title": "Apply Selective Subject Masking & Local Contrast",
            "action": "Create a radial/subject mask over key areas and add +10 to +20 Texture and Clarity.",
            "reasoning": "Enhancing local contrast selectively draws viewer focus to primary subjects without adding global noise."
        })

        # Step 5: Sharpening & Noise Reduction Pass
        steps.append({
            "title": "Apply Targeted Sharpening & Masking",
            "action": "Apply Amount +40 Sharpening with Masking set to 60+ (hold Option/Alt while dragging) to protect smooth gradients.",
            "reasoning": "Targeted sharpening ensures edges remain crisp while preventing sensor grain from showing up in flat or out-of-focus areas."
        })

    return steps
