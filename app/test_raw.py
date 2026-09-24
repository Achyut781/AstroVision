import rawpy
import imageio.v3 as iio
import numpy as np

def load_raw_image(file_path):
    try:
        # Engine 1: Traditional RAW using rawpy
        with rawpy.imread(file_path) as raw:
            # out_type=np.uint16 is critical to preserve the high dynamic range
            image_data = raw.postprocess(out_type=np.uint16)
            engine = "rawpy (Traditional RAW)"
            return image_data, engine
            
    except Exception as raw_error:
        # Engine 2: Fallback to imageio for Apple ProRAW / Linear DNGs
        try:
            image_data = iio.imread(file_path)
            engine = "imageio (ProRAW / Linear DNG)"
            return image_data, engine
            
        except Exception as iio_error:
            # If both fail, the file is unreadable or corrupted
            raise RuntimeError(f"Rawpy failed: {raw_error} | Imageio failed: {iio_error}")

# Run the test
file_path = "test.dng"  # Swap this back and forth with your iPhone DNG

try:
    print(f"Attempting to load {file_path}...")
    data, used_engine = load_raw_image(file_path)
    
    print(f"Success! Processed using {used_engine}")
    print(f"Array shape (Height x Width x Channels): {data.shape}")
    print(f"Data type: {data.dtype}")
    
except Exception as e:
    print(f"Error: {e}")
