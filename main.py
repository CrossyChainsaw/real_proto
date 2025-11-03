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

Window.clearcolor = (1, 1, 1, 1)
Window.size = (800, 600)

PRODUCTS = [
    {"name": "Apple", "price": 0.50},
    {"name": "Banana", "price": 0.30},
    {"name": "Milk", "price": 1.20},
    {"name": "Beer", "price": 3.00},
]

# ---------------- Draggable Product ----------------
class DraggableProduct(Widget):
    color = ListProperty([1, 0, 0, 1])
    product = ObjectProperty(None)
    scanned = False
    disabled_drag = False

    def __init__(self, product, **kwargs):
        super().__init__(**kwargs)
        self.product = product
        self.size = (50, 50)
        self.size_hint = (None, None)
        self.pos = (0, 0)

        with self.canvas:
            Color(*self.color)
            self.rect = Rectangle(pos=self.pos, size=self.size)
            Color(0, 0, 0, 1)
            self.border = Line(rectangle=(*self.pos, *self.size), width=1.5)

        self.label = Label(
            text=product["name"],
            size_hint=(None, None),
            size=self.size,
            pos=self.pos,
            text_size=self.size,
            halign="center",
            valign="middle",
            color=(0, 0, 0, 1)
        )
        self.add_widget(self.label)
        self.bind(pos=self.update_graphics_pos, size=self.update_graphics_pos)

    def update_graphics_pos(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size
        self.border.rectangle = (*self.pos, *self.size)
        self.label.pos = self.pos
        self.label.size = self.size
        self.label.text_size = self.size

    def on_touch_down(self, touch):
        if self.disabled_drag:
            return False
        if self.collide_point(*touch.pos):
            touch.grab(self)
            self._offset_x = self.x - touch.x
            self._offset_y = self.y - touch.y
            return True
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if self.disabled_drag:
            return False
        if touch.grab_current is self:
            self.x = touch.x + self._offset_x
            self.y = touch.y + self._offset_y
            scanner = self.parent.scanner_area
            if self.collide_widget(scanner) and not self.scanned:
                self.parent.add_to_cart(self.product)
                self.scanned = True
                self.parent.enable_proceed()
            return True
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        if touch.grab_current is self:
            touch.ungrab(self)
            return True
        return super().on_touch_up(touch)


# ---------------- Kivy Camera Widget ----------------
class KivyCamera(Image):
    def __init__(self, capture, fps=30, **kwargs):
        super().__init__(**kwargs)
        self.capture = capture
        Clock.schedule_interval(self.update, 1.0 / fps)

    def update(self, dt):
        ret, frame = self.capture.read()
        if ret:
            frame = cv2.flip(frame, -1)  # horizontal flip for mirror
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            texture = Texture.create(size=(frame.shape[1], frame.shape[0]), colorfmt='rgb')
            texture.blit_buffer(frame.tobytes(), colorfmt='rgb', bufferfmt='ubyte')
            self.texture = texture


# ---------------- Scan Screen ----------------
class ScanScreen(FloatLayout):
    scanner_area = ObjectProperty(None)
    cart_layout = ObjectProperty(None)
    total_label = ObjectProperty(None)
    cart = []

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.products_widgets = []
        self.setup_ui()
        self.create_products()

    # ---------------- UI Setup ----------------
    def setup_ui(self):
        with self.canvas.before:
            Color(1, 1, 1, 1)
            self.bg_rect = Rectangle(pos=self.pos, size=Window.size)
        self.bind(size=self.update_bg, pos=self.update_bg)

        self.total_label = Label(
            text="Total: $0.00",
            size_hint=(None, None),
            size=(200, 50),
            pos=(550, 560),
            color=(0, 0, 0, 1)
        )
        self.add_widget(self.total_label)

        self.cart_layout = BoxLayout(
            orientation='vertical',
            size_hint=(None, None),
            size=(200, 250),
            pos=(550, 300)
        )
        self.add_widget(self.cart_layout)

        self.scanner_area = Widget(
            size_hint=(None, None),
            size=(200, 150),
            pos=(550, 100)
        )
        with self.scanner_area.canvas:
            Color(0.8, 0.8, 0.8, 1)
            Rectangle(pos=self.scanner_area.pos, size=self.scanner_area.size)
            Color(0, 0, 0, 1)
            Line(rectangle=(*self.scanner_area.pos, *self.scanner_area.size), width=2)
        self.add_widget(self.scanner_area)

        self.proceed_button = Button(
            text="Proceed",
            size_hint=(None, None),
            size=(150, 50),
            pos=(50, 50),
            disabled=True
        )
        self.proceed_button.bind(on_press=self.on_proceed)
        self.add_widget(self.proceed_button)

    def update_bg(self, *args):
        self.bg_rect.size = self.size
        self.bg_rect.pos = self.pos

    # ---------------- Product Handling ----------------
    def create_products(self):
        start_x = 20
        start_y = 400
        spacing = 70
        colors = [[1, 0, 0, 1], [0, 1, 0, 1], [0, 0, 1, 1], [1, 1, 0, 1]]
        for idx, p in enumerate(PRODUCTS):
            prod = DraggableProduct(product=p)
            prod.pos = (start_x + idx * spacing, start_y)
            prod.color = colors[idx % len(colors)]
            self.add_widget(prod)
            self.products_widgets.append(prod)

    def add_to_cart(self, product):
        self.cart.append(product)
        self.update_cart()

    def update_cart(self):
        self.cart_layout.clear_widgets()
        for item in self.cart:
            self.cart_layout.add_widget(Label(
                text=f"{item['name']} - ${item['price']:.2f}",
                size_hint_y=None,
                height=30,
                color=(0, 0, 0, 1)
            ))
        total = sum(i['price'] for i in self.cart)
        self.total_label.text = f"Total: ${total:.2f}"

    def enable_proceed(self):
        self.proceed_button.disabled = False

    # ---------------- Proceed Logic ----------------
    def on_proceed(self, instance):
        # Disable proceed button immediately to prevent multiple clicks
        self.proceed_button.disabled = True

        # Stop further dragging of products
        for prod in self.products_widgets:
            prod.disabled_drag = True

        beer_in_cart = any(item["name"].lower() == "beer" for item in self.cart)
        if beer_in_cart:
            self.ask_ai_check()
        else:
            self.show_pay_button()


    def ask_ai_check(self):
        content = BoxLayout(orientation='vertical', spacing=10, padding=10)
        content.add_widget(Label(text="Do you want to automatically check your age using AI?"))
        btn_layout = BoxLayout(spacing=10)
        yes_btn = Button(text="Yes")
        no_btn = Button(text="No")
        btn_layout.add_widget(yes_btn)
        btn_layout.add_widget(no_btn)
        content.add_widget(btn_layout)

        popup = Popup(title="Age Verification", content=content, size_hint=(None, None), size=(400, 200))
        popup.open()
        yes_btn.bind(on_release=lambda x: self.ai_age_check(popup))
        no_btn.bind(on_release=lambda x: self.ask_medewerker_login(popup))

    # ---------------- AI Age Check ----------------
    # ---------------- AI Age Check ----------------
    def ai_age_check(self, popup):
        popup.dismiss()

        # Open camera
        self.cam_capture = cv2.VideoCapture(0)
        
        # Layout for camera + cancel button
        layout = FloatLayout(size=(640, 480))

        # Make camera fill the entire layout
        self.cam_widget = KivyCamera(
            capture=self.cam_capture,
            fps=30,
            size_hint=(1, 1),       # Fill horizontally & vertically
            pos_hint={'x': 0, 'y': 0}  # Start at bottom-left
        )
        layout.add_widget(self.cam_widget)

        # Cancel button on top
        cancel_btn = Button(
            text="Cancel",
            size_hint=(None, None),
            size=(200, 50),
            pos_hint={'center_x': 0.5, 'y': 0.02}  # centered horizontally, 2% from bottom
        )
        cancel_btn.bind(on_release=self.cancel_ai_age_check)
        layout.add_widget(cancel_btn)

        # Show popup
        self.cam_popup = Popup(
            title="AI Age Check",
            content=layout,
            size_hint=(None, None),
            size=(640, 480)
        )
        self.cam_popup.open()

    def cancel_ai_age_check(self, instance):
        # Stop camera
        if hasattr(self, "cam_capture") and self.cam_capture.isOpened():
            self.cam_capture.release()
        # Close popup
        self.cam_popup.dismiss()

        # Store references so we can remove later
        self.overlay_widget = Widget(size=Window.size, size_hint=(None, None), pos=(0, 0))
        with self.overlay_widget.canvas:
            Color(1, 1, 1, 0.5)
            Rectangle(pos=(0, 0), size=Window.size)
        self.add_widget(self.overlay_widget)

        self.notice_label = Label(
            text="Medewerker is on the way to check your identification",
            size_hint=(None, None),
            size=(500, 50),
            pos=(Window.width/2 - 250, Window.height/2 + 20),
            color=(0, 0, 0, 1),
            halign="center",
            valign="middle",
            text_size=(500, 50)
        )
        self.add_widget(self.notice_label)

        # ---------------- Medewerker Login Button ----------------
        self.medewerker_btn = Button(
            text="Medewerker Login",
            size_hint=(None, None),
            size=(200, 50),
            pos=(Window.width/2 - 100, Window.height/2 - 40)
        )
        self.medewerker_btn.bind(on_release=self.start_medewerker_login)
        self.add_widget(self.medewerker_btn)

    def start_medewerker_login(self, instance):
        # Remove overlay and button
        if hasattr(self, "overlay_widget"):
            self.remove_widget(self.overlay_widget)
            del self.overlay_widget
        if hasattr(self, "notice_label"):
            self.remove_widget(self.notice_label)
            del self.notice_label
        if hasattr(self, "medewerker_btn"):
            self.remove_widget(self.medewerker_btn)
            del self.medewerker_btn

        # Show the actual login popup
        self.ask_medewerker_login()



    def confirm_age_ai(self, instance):
        if hasattr(self, "cam_capture") and self.cam_capture.isOpened():
            self.cam_capture.release()
        self.cam_popup.dismiss()
        age = 18  # replace with AI detection
        if age >= 18:
            self.show_pay_button()
        else:
            self.remove_beer_completely()

    # ---------------- Medewerker Login ----------------
    def ask_medewerker_login(self, popup=None):
        if popup:
            popup.dismiss()
        content = BoxLayout(orientation='vertical', spacing=10, padding=10)
        self.code_input = TextInput(hint_text="Enter code", multiline=False)
        btn = Button(text="Login")
        content.add_widget(self.code_input)
        content.add_widget(btn)
        popup = Popup(title="Medewerker Login", content=content, size_hint=(None, None), size=(400, 200))
        popup.open()
        btn.bind(on_release=lambda x: self.verify_medewerker(popup))

    def verify_medewerker(self, popup):
        if self.code_input.text == "0000":
            popup.dismiss()
            self.show_medewerker_panel()
        else:
            self.code_input.text = ""
            self.code_input.hint_text = "Wrong code, try again"

    def show_medewerker_panel(self):
        content = BoxLayout(orientation='vertical', spacing=10, padding=10)
        content.add_widget(Label(text="Is the klant 18 or older?"))
        btn_layout = BoxLayout(spacing=10)
        older_btn = Button(text="Yes")
        younger_btn = Button(text="No")
        btn_layout.add_widget(older_btn)
        btn_layout.add_widget(younger_btn)
        content.add_widget(btn_layout)
        popup = Popup(title="Age Verification", content=content, size_hint=(None, None), size=(400, 200))
        popup.open()
        older_btn.bind(on_release=lambda x: self.age_ok(popup))
        younger_btn.bind(on_release=lambda x: self.age_not_ok(popup))

    def age_ok(self, popup):
        popup.dismiss()
        # Remove overlay and notice if they exist
        if hasattr(self, "overlay_widget"):
            self.remove_widget(self.overlay_widget)
            del self.overlay_widget
        if hasattr(self, "notice_label"):
            self.remove_widget(self.notice_label)
            del self.notice_label

        self.show_pay_button()


    def age_not_ok(self, popup):
        popup.dismiss()
        # Remove overlay and notice if they exist
        if hasattr(self, "overlay_widget"):
            self.remove_widget(self.overlay_widget)
            del self.overlay_widget
        if hasattr(self, "notice_label"):
            self.remove_widget(self.notice_label)
            del self.notice_label

        self.show_pay_button()
        self.remove_beer_completely()

    def remove_beer_completely(self):
        self.cart = [p for p in self.cart if p["name"].lower() != "beer"]
        for prod in self.products_widgets[:]:
            if prod.product["name"].lower() == "beer":
                self.remove_widget(prod)
                self.products_widgets.remove(prod)
        self.update_cart()

    def show_pay_button(self):
        self.pay_button = Button(
            text="Pay",
            size_hint=(None, None),
            size=(150, 50),
            pos=(220, 50)
        )
        self.pay_button.bind(on_press=self.on_pay)
        self.add_widget(self.pay_button)

    def on_pay(self, instance):
        self.remove_widget(self.pay_button)
        overlay = Widget(size=Window.size, size_hint=(None, None), pos=(0, 0))
        with overlay.canvas:
            Color(1, 1, 1, 0.5)
            Rectangle(pos=(0, 0), size=Window.size)
        self.add_widget(overlay)

        thank_you = Label(
            text="Thank you for testing the prototype!",
            size_hint=(None, None),
            size=(400, 50),
            pos=(Window.width/2 - 200, Window.height/2 - 25),
            color=(0, 0, 0, 1),
            halign="center",
            valign="middle",
            text_size=(400, 50)
        )
        self.add_widget(thank_you)


# ---------------- App ----------------
class CheckoutApp(App):
    def build(self):
        return ScanScreen()


if __name__ == "__main__":
    CheckoutApp().run()
