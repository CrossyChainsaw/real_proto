from kivy.uix.image import Image
from kivy.clock import Clock
from kivy.graphics.texture import Texture
import cv2
import time
from model import predict_age

THRESHOLD = 70.0  # sharpness threshold


def is_image_sharp(frame, threshold):
    """Return True if frame is sharp enough."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    variance = cv2.Laplacian(gray, cv2.CV_64F).var()
    return variance > threshold


# ---------------- Kivy Camera Widget ----------------
class KivyCamera(Image):
    def __init__(self, capture, parent_screen, fps=30, **kwargs):
        super().__init__(**kwargs)
        self.capture = capture
        self.parent_screen = parent_screen  # store ScanScreen reference
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )

        # track start time for 30s warm-up
        self.start_time = time.time()

        # schedule frame updates
        Clock.schedule_interval(self.update, 1.0 / fps)

    def update(self, dt):
        ret, frame = self.capture.read()
        if not ret:
            return

        # Flip for a mirrored effect
        frame = cv2.flip(frame, -1)
        display_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Compute how long the camera has been running
        elapsed = time.time() - self.start_time

        if elapsed >= 2:
            # Only start detecting after 30 seconds
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(
                gray, scaleFactor=1.1, minNeighbors=5, minSize=(100, 100)
            )

            if len(faces) > 0 and is_image_sharp(frame, THRESHOLD):
                try:
                    age = predict_age(frame)
                    print("Predicted age:", age)
                    self.parent_screen.handle_ai_age_detected(age)
                except Exception as e:
                    print("Prediction error:", e)

        # Display the frame
        texture = Texture.create(size=(display_frame.shape[1], display_frame.shape[0]), colorfmt='rgb')
        texture.blit_buffer(display_frame.tobytes(), colorfmt='rgb', bufferfmt='ubyte')
        self.texture = texture
