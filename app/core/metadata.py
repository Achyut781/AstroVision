import exifread

def extract_metadata(file_path):
    """
    Extracts exposure and camera details from RAW/DNG EXIF metadata.
    """
    metadata = {
        "Camera": "Unknown",
        "Lens": "Unknown",
        "ISO": "Unknown",
        "Shutter Speed": "Unknown",
        "Aperture": "Unknown",
        "Focal Length": "Unknown"
    }
    
    try:
        with open(file_path, 'rb') as f:
            tags = exifread.process_file(f, details=False)
            
            # Camera Make and Model
            make = str(tags.get('Image Make', '')).strip()
            model = str(tags.get('Image Model', '')).strip()
            if make and model:
                metadata["Camera"] = f"{make} {model}"
            elif model:
                metadata["Camera"] = model
                
            # Exposure parameters
            if 'EXIF ISOSpeedRatings' in tags:
                metadata["ISO"] = str(tags['EXIF ISOSpeedRatings'])
            if 'EXIF ExposureTime' in tags:
                metadata["Shutter Speed"] = f"{tags['EXIF ExposureTime']} s"
            if 'EXIF FNumber' in tags:
                metadata["Aperture"] = f"f/{float(tags['EXIF FNumber'].values[0]):.1f}"
            if 'EXIF FocalLength' in tags:
                metadata["Focal Length"] = f"{float(tags['EXIF FocalLength'].values[0]):.1f} mm"
                
    except Exception as e:
        print(f"Error reading EXIF metadata: {e}")
        
    return metadata
