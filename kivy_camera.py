from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.popup import Popup
from kivy.graphics import Color, Rectangle, Line
from kivy.core.window import Window
from kivy.properties import ListProperty, ObjectProperty
from kivy.uix.image import Image
from kivy.clock import Clock
from kivy.graphics.texture import Texture
import cv2
from model import predict_age


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
        Clock.schedule_interval(self.update, 1.0 / fps)
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )


    def update(self, dt):
        ret, frame = self.capture.read()
        if not ret:
            return
        
        frame = cv2.flip(frame, -1)  # mirror
        display_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Detect faces
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(100, 100))
        
        if len(faces) > 0 and is_image_sharp(frame, threshold=20.0):
            try:
                age = predict_age(frame)
                print("Predicted age:", age)
                self.parent_screen.handle_ai_age_detected(age)
            except Exception as e:
                print("Prediction error:", e)


        
        # Display frame
        texture = Texture.create(size=(display_frame.shape[1], display_frame.shape[0]), colorfmt='rgb')
        texture.blit_buffer(display_frame.tobytes(), colorfmt='rgb', bufferfmt='ubyte')
        self.texture = texture
