"""
OCR utility module for character recognition.
Provides a simple interface for OCR predictions.
"""

import numpy as np
from util.CaptchaUtils import predict_ocr as predict_ocr_model


def ocr_predict(image: np.ndarray, model_path: str = "./models/ocr.onnx", use_gpu: bool = False) -> str:
    """
    Predict text from an image using OCR model.
    
    Args:
        image (np.ndarray): Input image in OpenCV format (numpy.ndarray).
        model_path (str): Path to the ONNX OCR model. Defaults to "./models/ocr.onnx".
        use_gpu (bool): Whether to use GPU for inference. Defaults to False.
        
    Returns:
        str: Predicted character from the image.
        
    Raises:
        Exception: If OCR prediction fails.
    """
    return predict_ocr_model(model_path, image, use_gpu)
