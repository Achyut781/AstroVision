import rawpy
import imageio.v3 as iio
import numpy as np

def load_raw_image(file_path):
    """
    Dual-engine loader supporting standard camera RAWs (rawpy) 
    and Apple ProRAW / Linear DNGs (imageio).
    """
    try:
        with rawpy.imread(file_path) as raw:
            image_data = raw.postprocess(out_type=np.uint16)
            engine = "rawpy (Traditional RAW)"
            return image_data, engine
    except Exception as raw_error:
        try:
            image_data = iio.imread(file_path)
            engine = "imageio (ProRAW / Linear DNG)"
            return image_data, engine
        except Exception as iio_error:
            raise RuntimeError(f"Rawpy: {raw_error} | Imageio: {iio_error}")
