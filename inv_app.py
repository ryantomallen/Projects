import kivy
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from kivy.uix.checkbox import CheckBox
from kivy.graphics import Color, Rectangle
import csv
import requests
import json

class MappingApp(App):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.base_url = "http://41.72.150.250/csi-requesthandler/api/v2/"
        self.endpoint = None
        self.field_mappings = {}  # CSV header -> API field
        self.csv_headers = []
        self.session_token = None

        # For row-by-row processing:
        self.rows_to_process = []
        self.current_row_index = 0
        self.key_column = None
        self.skip_key_logic = False  # If user picks "Skip Key Column"
        self.api_fields = {}

    def customize_checkbox(self, checkbox):
        with checkbox.canvas.before:
            Color(0.8, 0.8, 0.8, 1)  # Light gray for unchecked state
            Rectangle(size=checkbox.size, pos=checkbox.pos)
        checkbox.bind(size=self.update_checkbox_background, pos=self.update_checkbox_background)

    def update_checkbox_background(self, checkbox, *args):
        checkbox.canvas.before.clear()
        with checkbox.canvas.before:
            Color(0.8, 0.8, 0.8, 1)
            Rectangle(size=checkbox.size, pos=checkbox.pos)

    def build(self):
        self.api_url = None
        self.mappings = {}
        self.csv_headers = []
        return self.login_screen()

    def login_screen(self):
        layout = BoxLayout(orientation='vertical', padding=60, spacing=60)

        layout.add_widget(Label(text="Username", font_size=40, color=(1, 1, 1, 1)))
        self.username_input = TextInput(
            hint_text="Enter Username",
            multiline=False,
            size_hint_y=None,
            height=100,
            font_size=32
        )
        layout.add_widget(self.username_input)

        layout.add_widget(Label(text="Password", font_size=40, color=(1, 1, 1, 1)))
        self.password_input = TextInput(
            hint_text="Enter Password",
            multiline=False,
            password=True,
            size_hint_y=None,
            height=100,
            font_size=32
        )
        layout.add_widget(self.password_input)

        login_button = Button(
            text="Login",
            size_hint_y=None,
            height=100,
            background_normal='',
            background_color=(0, 0.5, 1, 1),
            font_size=32
        )
        login_button.bind(on_press=self.authenticate)
        layout.add_widget(login_button)

        return layout

    def authenticate(self, instance):
        username = self.username_input.text.strip()
        password = self.password_input.text.strip()
        base_url = 'http://41.72.150.250/csi-requesthandler/api/v2/'
        endpoint = 'session'
        login_url = f"{base_url}{endpoint}"

        payload = {
            "username": username,
            "password": password,
        }
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json"
        }

        try:
            response = requests.post(login_url, json=payload, headers=headers)

            if response.status_code == 200:
                try:
                    token = response.json().get('token')
                    if not token:
                        raise ValueError("Token not found in the login response.")
                    self.session_token = token
                    self.show_popup("Success", "Login successful!")
                    self.root.clear_widgets()
                    self.root.add_widget(self.upload_screen())
                except (ValueError, KeyError) as e:
                    self.show_popup("Error", f"Unexpected login response format: {e}")
            else:
                self.show_popup("Error", f"Login failed: {response.text}")
        except requests.exceptions.RequestException as e:
            self.show_popup("Error", f"Failed to connect to API: {e}")

        self.base_url = "http://41.72.150.250/csi-requesthandler/api/v2/"

    def upload_screen(self):
        layout = BoxLayout(orientation='vertical', padding=50, spacing=50)

        title = Label(text="Upload CSV File", font_size=36, color=(0, 0, 0, 1))
        layout.add_widget(title)

        self.file_chooser = FileChooserListView(filters=["*.csv"], size_hint_y=None, height=600)
        layout.add_widget(self.file_chooser)

        upload_button = Button(
            text="Upload and Map",
            size_hint_y=None,
            height=80,
            background_normal='',
            background_color=(0, 0.5, 1, 1),
            font_size=28
        )
        upload_button.bind(on_press=self.upload_csv)
        layout.add_widget(upload_button)

        logout_button = Button(
            text="Logout",
            size_hint_y=None,
            height=80,
            background_normal='',
            background_color=(0.9, 0.1, 0.1, 1),
            font_size=28
        )
        logout_button.bind(on_press=lambda x: self.reset_to_login())
        layout.add_widget(logout_button)

        return layout

    def upload_csv(self, instance):
        try:
            if not self.file_chooser.selection:
                raise ValueError("No file selected. Please select a CSV file.")

            file_path = self.file_chooser.selection[0]
            with open(file_path, 'r') as csv_file:
                reader = csv.DictReader(csv_file)
                self.csv_headers = reader.fieldnames
                self.show_popup("Success", "File uploaded successfully!")
                self.root.clear_widgets()
                self.root.add_widget(self.endpoint_input_screen())
        except Exception as e:
            self.show_popup("Error", f"Failed to process CSV file: {e}")

    
    def show_key_and_mapping_screen(self):
       
        layout = BoxLayout(orientation='vertical', spacing=20, padding=20)

        layout.add_widget(Label(text="Select Key Column and Map Fields", font_size=24))

        # Key Column row
        key_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=40)
        key_row.add_widget(Label(text="Key Column:", size_hint_x=0.3))

        # Add "Skip Key Column" to the spinner values:
        key_column_values = list(self.csv_headers) + ["Skip Key Column"]
        self.key_column_spinner = Spinner(
            text="Select Key Column",
            values=key_column_values,
            size_hint_x=0.7
        )
        key_row.add_widget(self.key_column_spinner)
        layout.add_widget(key_row)

        # Mapping Section
        layout.add_widget(Label(text="Map CSV Headers to API Fields", font_size=20))

        self.field_map_dropdowns = {}
        # We add "Skip Field" to each field's Spinner
        field_choices = list(self.api_fields.keys()) + ["Skip Field"]

        for csv_header in self.csv_headers:
            row = BoxLayout(orientation='horizontal', size_hint_y=None, height=40)
            row.add_widget(Label(text=csv_header, size_hint_x=0.3))

            dropdown = Spinner(
                text="Select API Field",
                values=field_choices,
                size_hint_x=0.7
            )
            self.field_map_dropdowns[csv_header] = dropdown
            row.add_widget(dropdown)
            layout.add_widget(row)

        save_button = Button(
            text="Save and Proceed",
            size_hint_y=None,
            height=50
        )
        save_button.bind(on_press=self.handle_key_column_and_mapping)
        layout.add_widget(save_button)

        self.root.clear_widgets()
        self.root.add_widget(layout)

    def handle_key_column_and_mapping(self, instance):
       
        selected_key_column = self.key_column_spinner.text.strip()

        # Case 1: "Skip Key Column"
        if selected_key_column == "Skip Key Column":
            self.skip_key_logic = True
            self.key_column = None
        else:
            self.skip_key_logic = False
            if selected_key_column not in self.csv_headers:
                self.show_popup("Error", "Please select a valid key column.")
                return
            self.key_column = selected_key_column

            # Check for duplicates if we're NOT skipping key logic
            if not self.check_for_duplicates(self.key_column):
                return  # If there's a duplicate, a popup was shown and we stop here

        # Build the field mappings
        temp_mappings = {}
        for csv_header, spinner_widget in self.field_map_dropdowns.items():
            chosen_api_field = spinner_widget.text
            # If user chooses "Skip Field", we do not add it to mappings
            # If user chooses "Select API Field", also skip
            if chosen_api_field not in ("Skip Field", "Select API Field"):
                temp_mappings[csv_header] = chosen_api_field

        if not temp_mappings:
            self.show_popup("Error", "No fields mapped! Please map at least one field or choose 'Skip Field' for all.")
            return

        self.field_mappings = temp_mappings

        self.show_popup("Success", f"Key column '{self.key_column}' (skip={self.skip_key_logic}) and mappings saved!")

        # Now start row-by-row processing
        self.start_csv_processing()

    def check_for_duplicates(self, column_name):
       
        file_path = None
        if self.file_chooser and self.file_chooser.selection:
            file_path = self.file_chooser.selection[0]
        else:
            self.show_popup("Error", "CSV file not found. Please upload again.")
            return False

        seen_keys = set()
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    key_value = row.get(column_name, "")
                    if key_value in seen_keys:
                        self.show_popup("Error", f"Duplicate values found in '{column_name}' column.")
                        return False
                    seen_keys.add(key_value)
        except Exception as e:
            self.show_popup("Error", f"Failed to read CSV for key validation: {e}")
            return False

        return True

    

    def start_csv_processing(self):
        try:
            file_path = self.file_chooser.selection[0]
        except (IndexError, AttributeError):
            self.show_popup("Error", "No CSV file selected.")
            return

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                self.rows_to_process = list(reader)

            self.current_row_index = 0
            self.process_next_row()
        except Exception as e:
            self.show_popup("Error", f"Failed to read CSV: {e}")

    def process_next_row(self):
        if self.current_row_index >= len(self.rows_to_process):
            self.show_popup("Success", "All rows processed!")
            return

        row = self.rows_to_process[self.current_row_index]

        # Convert the CSV row -> payload
        try:
            payload = self.build_payload(row)
        except Exception as e:
            self.show_popup("Error", f"Row {self.current_row_index}: {e}")
            self.current_row_index += 1
            self.process_next_row()
            return

        # If skipping key logic, always create:
        if self.skip_key_logic:
            self.create_record(payload)
            self.current_row_index += 1
            self.process_next_row()
            return

        # Otherwise, do create/update logic
        key_value = row.get(self.key_column, None)
        if not key_value:
            # Key not found => skip or error
            self.show_popup(
                "Error",
                f"No key value found in column '{self.key_column}' for row {self.current_row_index}. Skipping..."
            )
            self.current_row_index += 1
            self.process_next_row()
            return

        # If record exists, popup to update or create
        if self.record_exists(key_value):
            self.show_update_or_create_popup(key_value, payload)
        else:
            self.create_record(payload)
            self.current_row_index += 1
            self.process_next_row()

    def show_update_or_create_popup(self, key_value, payload):
        layout = BoxLayout(orientation='vertical', spacing=10, padding=10)
        message_label = Label(
            text=f"Avatar with ID '{key_value}' already exists.\nChoose an action:",
            size_hint_y=None,
            height=80
        )
        layout.add_widget(message_label)

        button_box = BoxLayout(orientation='horizontal', spacing=10, size_hint_y=None, height=50)

        update_btn = Button(text="Update Existing")
        create_btn = Button(text="Create New")

        button_box.add_widget(update_btn)
        button_box.add_widget(create_btn)
        layout.add_widget(button_box)

        popup = Popup(
            title="Duplicate Found",
            content=layout,
            size_hint=(0.6, 0.4),
            auto_dismiss=False
        )

        def on_update(instance):
            popup.dismiss()
            self.update_record(key_value, payload)
            self.current_row_index += 1
            self.process_next_row()

        def on_create(instance):
            popup.dismiss()
            self.create_record(payload)
            self.current_row_index += 1
            self.process_next_row()

        update_btn.bind(on_press=on_update)
        create_btn.bind(on_press=on_create)

        popup.open()

    def build_payload(self, row):
        
        payload = {}
        for csv_header, api_field in self.field_mappings.items():
            csv_value = row.get(csv_header, "")

            expected_type = self.api_fields.get(api_field, "string")
            if expected_type in ("float", "int"):
                if self.is_number(csv_value):
                    converted_value = float(csv_value) if expected_type == "float" else int(csv_value)
                else:
                    raise ValueError(f"Invalid number for field '{api_field}': {csv_value}")
            elif expected_type == "NoneType" and not csv_value:
                converted_value = None
            else:
                converted_value = csv_value

            payload[api_field] = converted_value

        return payload

    def is_number(self, value):
        try:
            float(value)
            return True
        except ValueError:
            return False

    def record_exists(self, key_value):
        if not key_value:
            return False

        headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "Cookie": self.session_token
        }
        check_url = f"{self.base_url}avatars/{key_value}"
        try:
            response = requests.get(check_url, headers=headers)
            return (response.status_code == 200)
        except:
            return False

    def update_record(self, key_value, payload):
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "Cookie": self.session_token
        }
        url = f"{self.base_url}avatars/{key_value}"
        response = requests.put(url, json=payload, headers=headers)
        if response.status_code == 200:
            print(f"Record {key_value} updated successfully.")
        else:
            self.show_popup("Error", f"Failed to update record {key_value}: {response.text}")

    def create_record(self, payload):
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "Cookie": self.session_token
        }
        url = f"{self.base_url}avatars"
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 200:
            print("Record created successfully.")
        else:
            self.show_popup("Error", f"Failed to create record: {response.text}")

        def send_to_api(self, payload):
            headers = {
                "accept": "application/json",
                "Content-Type": "application/json",
                "Cookie": self.session_token
            }
            try:
                full_url = f"{self.base_url.rstrip('/')}/{self.endpoint.lstrip('/')}"
                response = requests.post(full_url, json=payload, headers=headers)
                if response.status_code == 200:
                    print("Data sent successfully:", response.json())
                    self.show_popup("Success", f"Data sent: {response.json()}")
                else:
                    error_details = response.json().get("message", response.text)
                    print("API error:", response.status_code, error_details)
                    self.show_popup("Error", f"API error: {response.status_code} - {error_details}")
            except Exception as e:
                print("Error sending data:", e)
                self.show_popup("Error", f"Failed to send data: {e}")

    def endpoint_input_screen(self):
        layout = BoxLayout(orientation='vertical', padding=50, spacing=50)

        layout.add_widget(Label(text="Enter the REST API Endpoint", font_size=28))
        self.endpoint_input = TextInput(
            hint_text="Enter endpoint (e.g. avatars)",
            multiline=False,
            font_size=24
        )
        layout.add_widget(self.endpoint_input)

        submit_button = Button(
            text="Fetch API Fields",
            size_hint_y=None,
            height=80,
            background_normal='',
            background_color=(0, 0.5, 1, 1),
            font_size=24
        )
        submit_button.bind(on_press=self.fetch_api_fields)
        layout.add_widget(submit_button)

        return layout

    def set_endpoint_and_process_data(self, instance):
        endpoint = self.endpoint_input.text.strip()
        if not endpoint:
            self.show_popup("Error", "Please enter a valid endpoint.")
            return

        self.endpoint = endpoint.lstrip("/")

    def reset_to_login(self):
        self.root.clear_widgets()
        self.root.add_widget(self.login_screen())

    def show_popup(self, title, message):
        popup = Popup(title=title, content=Label(text=message), size_hint=(0.6, 0.4))
        popup.open()

    def fetch_endpoint_data(self, endpoint):
        full_url = f"{self.api_url}{endpoint}"
        try:
            response = requests.get(full_url, cookies=self.session_token)
            if response.status_code == 200:
                data = response.json()
                self.show_popup("Success", f"Data fetched successfully: {data}")
            else:
                self.show_popup("Error", f"Failed to fetch data: {response.text}")
        except Exception as e:
            self.show_popup("Error", f"Error fetching data: {e}")

    def fetch_api_fields(self, instance):
        endpoint = self.endpoint_input.text.strip()
        if not endpoint:
            self.show_popup("Error", "Please enter a valid endpoint.")
            return

        if not endpoint.startswith("/"):
            endpoint = "/" + endpoint
        self.endpoint = endpoint

        try:
            full_url = f"{self.base_url.rstrip('/')}/{self.endpoint.lstrip('/')}"
            headers = {"accept": "application/json", "Cookie": self.session_token}
            response = requests.get(full_url, headers=headers)

            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list) and len(data) > 0:
                    self.api_fields = {
                        key: type(value).__name__
                        for key, value in data[0].items()
                    }
                    self.show_popup("Success", "API fields and types fetched successfully!")
                    self.root.clear_widgets()
                    self.root.add_widget(self.show_key_and_mapping_screen())
                else:
                    self.show_popup("Error", "No data found at the endpoint to deduce fields.")
            else:
                self.show_popup(
                    "Error",
                    f"Failed to fetch data: {response.status_code} - {response.text}"
                )
        except AttributeError as e:
            if "fbind" in str(e):
                return
        except Exception as e:
            self.show_popup("Error", f"Failed to connect to API: {e}")


if __name__ == "__main__":
    MappingApp().run()
