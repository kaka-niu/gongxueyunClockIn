#!/usr/bin/env python3
"""Simple test to verify imports work correctly."""

try:
    print("Testing import of step.clockIn...")
    from step.clockIn import clock_in
    print("✓ Import successful: from step.clockIn import clock_in")
    
    print("\nTesting import of util.ocr...")
    from util.ocr import ocr_predict
    print("✓ Import successful: from util.ocr import ocr_predict")
    
    print("\nTesting import of util.image_utils...")
    from util.image_utils import get_text_coordinates, save_snapshot
    print("✓ Import successful: from util.image_utils import get_text_coordinates, save_snapshot")
    
    print("\n✓ All imports successful!")
    
except Exception as e:
    print(f"✗ Import failed: {e}")
    import traceback
    traceback.print_exc()
    exit(1)
