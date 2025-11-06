import torch
from torchvision import models, transforms
from PIL import Image
import torch.nn as nn
import cv2
from ultralytics import YOLO

# ==== CONFIG ====
YOLO_MODEL_PATH = "yolov8n-face.pt"  # YOLO face detector
OUTPUT_SIZE = 224
PADDING_RATIO = 0.0
# =================

# ------------------------- Load Age Model -------------------------
def load_age_model(weights_path, device):
    """Load VGG16-based age prediction model."""
    model = models.vgg16(weights=models.VGG16_Weights.IMAGENET1K_V1)
    model.classifier[6] = nn.Linear(4096, 101)
    nn.init.xavier_normal_(model.classifier[6].weight)
    nn.init.zeros_(model.classifier[6].bias)

    checkpoint = torch.load(weights_path, map_location=device)
    if 'model_state_dict' in checkpoint:
        state_dict = checkpoint['model_state_dict']
    else:
        state_dict = checkpoint

    model.load_state_dict(state_dict)
    model.to(device)
    model.eval()
    return model

# ------------------------- Crop & Resize -------------------------
def crop_and_resize(img, box, size=OUTPUT_SIZE, pad_ratio=PADDING_RATIO):
    """Crop, pad, and resize a face from a NumPy image."""
    h_img, w_img = img.shape[:2]
    x1, y1, x2, y2 = box
    w, h = x2 - x1, y2 - y1
    pad_w, pad_h = pad_ratio * w, pad_ratio * h

    x1, y1 = max(0, x1 - pad_w), max(0, y1 - pad_h)
    x2, y2 = min(w_img, x2 + pad_w), min(h_img, y2 + pad_h)

    cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
    half_size = max(x2 - x1, y2 - y1) / 2
    x1, x2 = int(max(0, cx - half_size)), int(min(w_img, cx + half_size))
    y1, y2 = int(max(0, cy - half_size)), int(min(h_img, cy + half_size))

    crop = img[y1:y2, x1:x2]
    crop = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
    crop = cv2.rotate(crop, cv2.ROTATE_180)
    resized = cv2.resize(crop, (size, size), interpolation=cv2.INTER_AREA)
    return Image.fromarray(resized)

# ------------------------- Prepare Face -------------------------
class FacePreparer:
    """Detects and crops faces from frames using YOLO."""
    def __init__(self, yolo_model_path=YOLO_MODEL_PATH):
        self.yolo = YOLO(yolo_model_path)

    def from_frame(self, frame):
        """Return a PIL Image of the first detected face."""
        results = self.yolo(frame)
        boxes = results[0].boxes.xyxy
        if len(boxes) == 0:
            raise ValueError("No face detected in the frame.")
        x1, y1, x2, y2 = boxes[0].tolist()
        return crop_and_resize(frame, (x1, y1, x2, y2))

# ------------------------- Predict Age -------------------------
def predict_age_from_frame(model, frame, device, face_preparer=None):
    """
    Predict age from an OpenCV frame (NumPy array).
    - model: age prediction model
    - frame: BGR image
    - device: torch.device
    - face_preparer: optional FacePreparer instance
    """
    if face_preparer is None:
        face_preparer = FacePreparer()

    # Detect and crop face
    face = face_preparer.from_frame(frame)

    face.save('gezicht.png')
    

    # Preprocess for VGG16
    preprocess = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406],
                             std=[0.229, 0.224, 0.225])
    ])
    img_tensor = preprocess(face).unsqueeze(0).to(device)

    # Predict age
    model.eval()
    with torch.no_grad():
        output = model(img_tensor)
        predicted_age = torch.argmax(output, dim=1).item()
    return predicted_age

# ------------------------- Initialize -------------------------
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = load_age_model("./epoch_008.pth", device)
face_preparer = FacePreparer()

def predict_age(frame):
    """Convenience function for KivyCamera frames."""
    return predict_age_from_frame(model, frame, device, face_preparer)


