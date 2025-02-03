import kivy
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.popup import Popup
import csv
import requests
import json

class MappingApp(App):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Dynamically set by user
        self.base_url = ""
        self.endpoint = None

        # CSV data
        self.csv_headers = []
        self.field_mappings = {}

        # Login/Session
        self.session_token = None

        # Row-by-row processing
        self.rows_to_process = []
        self.current_row_index = 0
        self.key_column = None
        self.api_fields = {}  # e.g., { "description": "float", ... }

    def build(self):
        """ Start with the login screen """
        return self.login_screen()

    # ---------------------------------------------------------------------
    # 1) LOGIN SCREEN
    # ---------------------------------------------------------------------
    def login_screen(self):
        layout = BoxLayout(orientation='vertical', padding=60, spacing=60)

        # Base URL
        layout.add_widget(Label(text="Base URL", font_size=40, color=(1, 1, 1, 1)))
        self.base_url_input = TextInput(
            hint_text="Enter Base URL (e.g. http://129.232.225.154)",
            multiline=False,
            size_hint_y=None,
            height=100,
            font_size=32
        )
        layout.add_widget(self.base_url_input)

        # Username
        layout.add_widget(Label(text="Username", font_size=40, color=(1, 1, 1, 1)))
        self.username_input = TextInput(
            hint_text="Enter Username",
            multiline=False,
            size_hint_y=None,
            height=100,
            font_size=32
        )
        layout.add_widget(self.username_input)

        # Password
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

        # Login Button
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
        """ Attempt to log in with user-provided base_url, username, password """
        entered_url = self.base_url_input.text.strip()
        if not entered_url:
            self.show_popup("Error", "Please enter a valid base URL.")
            return
        self.base_url = entered_url

        username = self.username_input.text.strip()
        password = self.password_input.text.strip()
        login_url = f"{self.base_url}/csi-requesthandler/api/v2/session"

        try:
            response = requests.post(
                login_url,
                json={"username": username, "password": password},
                headers={"accept": "application/json", "Content-Type": "application/json"}
            )
            if response.status_code == 200:
                token = response.json().get('token')
                if not token:
                    raise ValueError("Token not found in the login response.")
                self.session_token = token
                self.show_popup("Success", "Login successful!")

                # Move to CSV upload screen
                self.root.clear_widgets()
                self.root.add_widget(self.upload_screen())
            else:
                self.show_popup("Error", f"Login failed: {response.text}")
        except requests.exceptions.RequestException as e:
            self.show_popup("Error", f"Failed to connect: {e}")

    # ---------------------------------------------------------------------
    # 2) UPLOAD SCREEN
    # ---------------------------------------------------------------------
    def upload_screen(self):
        layout = BoxLayout(orientation='vertical', padding=50, spacing=50)

        layout.add_widget(Label(text="Upload CSV File", font_size=36, color=(0, 0, 0, 1)))

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
        """ After user selects a CSV file, parse it and store the headers """
        if not self.file_chooser.selection:
            self.show_popup("Error", "No file selected.")
            return

        file_path = self.file_chooser.selection[0]
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                self.csv_headers = reader.fieldnames or []
            self.show_popup("Success", "File uploaded successfully!")

            # Move to endpoint input screen
            self.root.clear_widgets()
            self.root.add_widget(self.endpoint_input_screen())
        except Exception as e:
            self.show_popup("Error", f"Failed to process CSV: {e}")

    # ---------------------------------------------------------------------
    # 3) ENDPOINT INPUT SCREEN
    # ---------------------------------------------------------------------
    def endpoint_input_screen(self):
        layout = BoxLayout(orientation='vertical', padding=50, spacing=50)

        layout.add_widget(Label(text="Enter the REST API Endpoint", font_size=28))
        self.endpoint_input = TextInput(
            hint_text="e.g. avatars",
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

    def fetch_api_fields(self, instance):
        """ Retrieve sample data from the chosen endpoint to deduce available API fields + types. """
        endpoint_str = self.endpoint_input.text.strip()
        if not endpoint_str:
            self.show_popup("Error", "Please enter a valid endpoint.")
            return
        self.endpoint = endpoint_str

        full_url = f"{self.base_url}/csi-requesthandler/api/v2/{self.endpoint}"
        headers = {"accept": "application/json", "Cookie": self.session_token}

        try:
            resp = requests.get(full_url, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list) and len(data) > 0:
                    # Deduce field types from the first record
                    self.api_fields = {k: type(v).__name__ for k, v in data[0].items()}
                    self.show_popup("Success", "API fields and types fetched successfully!")

                    # Now show the key/mapping screen
                    new_screen = self.show_key_and_mapping_screen()
                    self.root.clear_widgets()
                    self.root.add_widget(new_screen)
                else:
                    self.show_popup("Error", "No data found to deduce fields.")
            else:
                self.show_popup("Error", f"Failed to fetch data: {resp.status_code} - {resp.text}")
        except requests.exceptions.RequestException as e:
            self.show_popup("Error", f"Error fetching endpoint: {e}")

    # ---------------------------------------------------------------------
    # 4) KEY COLUMN + MAPPING SCREEN
    # ---------------------------------------------------------------------
    def show_key_and_mapping_screen(self):
        """
        Returns a layout that lets the user choose:
          1) Which CSV column is the unique key
          2) How to map each CSV header to an API field
        """
        layout = BoxLayout(orientation='vertical', spacing=20, padding=20)

        layout.add_widget(Label(text="Select Key Column and Map Fields", font_size=24))

        # Key Column spinner
        key_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=40)
        key_row.add_widget(Label(text="Key Column:", size_hint_x=0.3))
        self.key_column_spinner = Spinner(
            text="Select Key Column",
            values=self.csv_headers,
            size_hint_x=0.7
        )
        key_row.add_widget(self.key_column_spinner)
        layout.add_widget(key_row)

        # Mapping section
        layout.add_widget(Label(text="Map CSV Headers to API Fields", font_size=20))
        self.field_map_dropdowns = {}

        for csv_header in self.csv_headers:
            row = BoxLayout(orientation='horizontal', size_hint_y=None, height=40)
            row.add_widget(Label(text=csv_header, size_hint_x=0.3))

            dropdown = Spinner(
                text="Select API Field",
                values=list(self.api_fields.keys()),
                size_hint_x=0.7
            )
            self.field_map_dropdowns[csv_header] = dropdown
            row.add_widget(dropdown)
            layout.add_widget(row)

        # Save and Proceed
        save_button = Button(
            text="Save and Proceed",
            size_hint_y=None,
            height=50
        )
        save_button.bind(on_press=self.handle_key_column_and_mapping)
        layout.add_widget(save_button)

        return layout

    def handle_key_column_and_mapping(self, instance):
        """ Validate key column, check duplicates, and store CSV->API mappings. """
        chosen_key = self.key_column_spinner.text.strip()
        if chosen_key not in self.csv_headers:
            self.show_popup("Error", "Please select a valid key column.")
            return

        # Duplicate check
        if not self.check_for_duplicates(chosen_key):
            return

        self.key_column = chosen_key

        # Gather field mappings
        temp_mappings = {}
        for csv_header, spinner_widget in self.field_map_dropdowns.items():
            api_field = spinner_widget.text
            if api_field != "Select API Field":
                temp_mappings[csv_header] = api_field

        if not temp_mappings:
            self.show_popup("Error", "No fields mapped! Please map at least one field.")
            return

        self.field_mappings = temp_mappings
        self.show_popup("Success", f"Key column '{self.key_column}' and mappings saved!")

        self.start_csv_processing()

    def check_for_duplicates(self, column_name):
        """ Ensure the chosen key column has no duplicates in the CSV """
        try:
            file_path = self.file_chooser.selection[0]
        except (IndexError, AttributeError):
            self.show_popup("Error", "No CSV file selected for duplicates check.")
            return False

        seen = set()
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    val = row.get(column_name, "")
                    if val in seen:
                        self.show_popup("Error", f"Duplicate '{val}' found in column '{column_name}'.")
                        return False
                    seen.add(val)
        except Exception as e:
            self.show_popup("Error", f"Failed reading CSV: {e}")
            return False

        return True

    # ---------------------------------------------------------------------
    # 5) PROCESS CSV ROWS
    # ---------------------------------------------------------------------
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
        """ 
        Called iteratively until all rows in the CSV are processed.
        Determine if we do create or update based on record existence.
        """
        if self.current_row_index >= len(self.rows_to_process):
            self.show_popup("Success", "All rows processed!")
            return

        row = self.rows_to_process[self.current_row_index]

        # Convert CSV data -> payload
        try:
            payload = self.build_payload(row)
        except Exception as e:
            self.show_popup("Error", f"Row {self.current_row_index}: {e}")
            self.current_row_index += 1
            self.process_next_row()
            return

        # Get key value from CSV row
        key_value = row.get(self.key_column, None)
        if not key_value:
            self.show_popup("Error", f"No key value found for row {self.current_row_index}. Skipping.")
            self.current_row_index += 1
            self.process_next_row()
            return

        # Check if record exists on server
        existing_id = self.fetch_id_by_key_value(self.key_column, key_value)
        if existing_id is not None:
            # Prompt user to update or create new
            self.show_update_or_create_popup(existing_id, payload, key_value)
        else:
            # Create new
            self.create_record(payload)
            self.current_row_index += 1
            self.process_next_row()

    def fetch_id_by_key_value(self, key_column, key_value):
        """
        Instead of /{api_field_for_key}={key_value},
        we do /{endpoint}?{api_field_for_key}={key_value},
        e.g. /avatars?description=77.652
        """
        # 1) Find the mapped API field name
        api_field_for_key = self.field_mappings.get(key_column)
        if not api_field_for_key:
            print(f"Error: Key column '{key_column}' not mapped to any API field!")
            return None

        # 2) Construct URL with query parameter
        url = f"{self.base_url}/csi-requesthandler/api/v2/{self.endpoint}?{api_field_for_key}={key_value}"
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "Cookie": self.session_token
        }

        try:
            resp = requests.get(url, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                # If the endpoint returns a list when searching, we might take the first result:
                if isinstance(data, list) and len(data) > 0:
                    # e.g., data = [ {"id": 123, "description": 77.652}, ...]
                    return data[0].get("id")
                elif isinstance(data, dict):
                    # e.g., data = {"id": 123, "description": 77.652}
                    return data.get("id")
                else:
                    # No results
                    return None
            else:
                # Possibly 404 or other code
                return None
        except Exception as e:
            print(f"Error fetching ID by key: {e}")
            return None

    def show_update_or_create_popup(self, resource_id, payload, key_value):
        layout = BoxLayout(orientation='vertical', spacing=10, padding=10)
        msg = (
            f"An item with key '{key_value}' already exists (id={resource_id}).\n"
            f"Choose an action:"
        )
        message_label = Label(text=msg, size_hint_y=None, height=80)
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
            self.update_record(resource_id, payload)
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
        """ Convert CSV row to a payload dict using self.field_mappings and self.api_fields. """
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

    def is_number(self, val):
        try:
            float(val)
            return True
        except ValueError:
            return False

    # ---------------------------------------------------------------------
    # 6) CREATE & UPDATE
    # ---------------------------------------------------------------------
    def create_record(self, payload):
        """ POST {base_url}/csi-requesthandler/api/v2/{endpoint} """
        url = f"{self.base_url}/csi-requesthandler/api/v2/{self.endpoint}"
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "Cookie": self.session_token
        }
        try:
            resp = requests.post(url, json=payload, headers=headers)
            if resp.status_code == 200:
                print("Created new record successfully.")
            else:
                self.show_popup("Error", f"Failed to create record: {resp.text}")
        except Exception as e:
            self.show_popup("Error", f"Create error: {e}")

    def update_record(self, resource_id, payload):
        """ PUT {base_url}/csi-requesthandler/api/v2/{endpoint}/{resource_id} """
        url = f"{self.base_url}/csi-requesthandler/api/v2/{self.endpoint}/{resource_id}"
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "Cookie": self.session_token
        }
        try:
            resp = requests.put(url, json=payload, headers=headers)
            if resp.status_code == 200:
                print(f"Updated record {resource_id} successfully.")
            else:
                self.show_popup("Error", f"Failed to update record {resource_id}: {resp.text}")
        except Exception as e:
            self.show_popup("Error", f"Update error: {e}")

    # ---------------------------------------------------------------------
    # 7) MISC UTILITY
    # ---------------------------------------------------------------------
    def reset_to_login(self):
        self.root.clear_widgets()
        self.root.add_widget(self.login_screen())

    def show_popup(self, title, message):
        popup = Popup(title=title, content=Label(text=message), size_hint=(0.6, 0.4))
        popup.open()

if __name__ == "__main__":
    MappingApp().run()
