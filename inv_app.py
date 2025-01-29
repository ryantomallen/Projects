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
from kivy.clock import Clock
import csv
import requests
import json

class MappingApp(App):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.base_url = "http://41.72.150.250/csi-requesthandler/api/v2/"
        self.endpoint = None
        self.field_mappings = {}  # To store user-defined field mappings
        self.csv_headers = []  # To store CSV headers
        self.session_token = None
        self.endpoint_input = None

    def customize_checkbox(self, checkbox):
        
        # Define background appearance
        with checkbox.canvas.before:
            Color(0.8, 0.8, 0.8, 1)  # Light gray for unchecked state
            Rectangle(size=checkbox.size, pos=checkbox.pos)

        # Ensure background updates dynamically when the widget resizes or moves
        checkbox.bind(size=self.update_checkbox_background, pos=self.update_checkbox_background)

    def update_checkbox_background(self, checkbox, *args):
        
        checkbox.canvas.before.clear()
        with checkbox.canvas.before:
            Color(0.8, 0.8, 0.8, 1)  # Light gray for unchecked state
            Rectangle(size=checkbox.size, pos=checkbox.pos)

    def build(self):
        self.api_url = None
        self.mappings = {}
        self.csv_headers = []
        return self.login_screen()

    def login_screen(self):
       
        layout = BoxLayout(orientation='vertical', padding=60, spacing=60)
        
    

        # Heading for Email
        layout.add_widget(Label(text="Username", font_size=40, color=(1, 1, 1, 1)))  # White color
        
        # Text input for Email
        self.username_input = TextInput(hint_text="Enter Username", multiline=False, size_hint_y=None, height=100, font_size=32)
        layout.add_widget(self.username_input)

        # Heading for Password
        layout.add_widget(Label(text="Password", font_size=40, color=(1, 1, 1, 1)))  # White color
        
        # Text input for Password
        self.password_input = TextInput(hint_text="Enter Password", multiline=False, password=True, size_hint_y=None, height=100, font_size=32)
        layout.add_widget(self.password_input)

        # Login button
        login_button = Button(text="Login", size_hint_y=None, height=100, background_normal='', background_color=(0, 0.5, 1, 1), font_size=32)
        login_button.bind(on_press=self.authenticate)
        layout.add_widget(login_button)

        return layout

    def authenticate(self, instance):
       
        username = self.username_input.text.strip()
        password = self.password_input.text.strip()
        base_url = 'http://41.72.150.250/csi-requesthandler/api/v2/'
        endpoint = 'session'
        login_url = f"{base_url}{endpoint}"

        # Payload and headers for login
        payload = {
            "username": username,
            "password": password,
        }
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json"
        }

        try:
            # Send POST request to login
            response = requests.post(login_url, json=payload, headers=headers)

            # Check if the request was successful
            if response.status_code == 200:
                # Parse the token from the response
                try:
                    token = response.json().get('token')
                    if not token:
                        raise ValueError("Token not found in the login response.")
                    self.session_token = token  # Store token for further requests
                    self.show_popup("Success", "Login successful!")
                    self.root.clear_widgets()
                    self.root.add_widget(self.upload_screen())  # Move to the next screen
                except (ValueError, KeyError) as e:
                    self.show_popup("Error", f"Unexpected login response format: {e}")
            else:
                # Handle API error response
                self.show_popup("Error", f"Login failed: {response.text}")
        except requests.exceptions.RequestException as e:
            # Handle connection errors
            self.show_popup("Error", f"Failed to connect to API auth: {e}")

        self.base_url = "http://41.72.150.250/csi-requesthandler/api/v2/"

    def upload_screen(self):
        
        layout = BoxLayout(orientation='vertical', padding=50, spacing=50)

        # Title label
        title = Label(text="Upload CSV File", font_size=36, color=(0, 0, 0, 1))
        layout.add_widget(title)

        # File chooser
        self.file_chooser = FileChooserListView(filters=["*.csv"], size_hint_y=None, height=600)
        layout.add_widget(self.file_chooser)

        # Upload button
        upload_button = Button(text="Upload and Map", size_hint_y=None, height=80, background_normal='', background_color=(0, 0.5, 1, 1), font_size=28)
        upload_button.bind(on_press=self.upload_csv)
        layout.add_widget(upload_button)

        # Logout button
        logout_button = Button(text="Logout", size_hint_y=None, height=80, background_normal='', background_color=(0.9, 0.1, 0.1, 1), font_size=28)
        logout_button.bind(on_press=lambda x: self.reset_to_login())
        layout.add_widget(logout_button)

        return layout


    def upload_csv(self, instance):
    
        try:
            if not self.file_chooser.selection:
                raise ValueError("No file selected. Please select a CSV file.")

            # Get the selected file path
            file_path = self.file_chooser.selection[0]

            # Open and process the CSV file
            with open(file_path, 'r') as csv_file:
                reader = csv.DictReader(csv_file)
                self.csv_headers = reader.fieldnames  # Extract headers
                self.show_popup("Success", "File uploaded successfully!")
                self.root.clear_widgets()
                self.root.add_widget(self.endpoint_input_screen())  # Transition to endpoint input screen
        except Exception as e:
            self.show_popup("Error", f"Failed to process CSV file: {e}")


    def show_mapping_screen(self):
   
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

        layout.add_widget(Label(text="Map CSV Headers to API Fields", font_size=24))

        self.field_map_dropdowns = {}
        for header in self.csv_headers:
            hbox = BoxLayout(size_hint_y=None, height=40)
            hbox.add_widget(Label(text=header, size_hint_x=0.3))
            
            dropdown = Spinner(
                text="Select API Field",
                values=self.api_fields,  # Dynamically fetched API fields
                size_hint_x=0.7
            )
            self.field_map_dropdowns[header] = dropdown
            hbox.add_widget(dropdown)
            layout.add_widget(hbox)

        # Add Key Identifier Selection Dropdown
        layout.add_widget(Label(text="Select Key Identifier (Unique Record ID)", font_size=20))
        self.key_identifier_spinner = Spinner(
            text="Select Key Column",
            values=self.csv_headers,  # Use CSV headers as selectable keys
            size_hint_x=1.0
        )
        layout.add_widget(self.key_identifier_spinner)

        save_button = Button(text="Save Mapping", size_hint_y=None, height=50)
        save_button.bind(on_press=self.validate_and_save_mapping)
        layout.add_widget(save_button)

        self.root.clear_widgets()
        self.root.add_widget(layout)

    

    

      
        #self.process_csv() 
    def validate_and_save_mapping(self, instance):
        
        self.field_mappings = {
            header: dropdown.text for header, dropdown in self.field_map_dropdowns.items() if dropdown.text != "Select API Field"
        }

        if not self.field_mappings:
            self.show_popup("Error", "No fields mapped! Please map at least one field.")
            return

        self.key_identifier = self.key_identifier_spinner.text
        if self.key_identifier == "Select Key Column":
            self.show_popup("Error", "Please select a key identifier column!")
            return

        try:
            selected_file = self.file_chooser.selection[0]
            with open(selected_file, 'r') as csv_file:
                reader = csv.DictReader(csv_file)
                key_values = []
                duplicate_keys = set()

                for row in reader:
                    key_value = row.get(self.key_identifier)
                    if key_value in key_values:
                        duplicate_keys.add(key_value)
                    key_values.append(key_value)

            if duplicate_keys:
                self.show_popup("Warning", f"Duplicate values detected in the key identifier column. "
                                        f"These records will be skipped: {', '.join(duplicate_keys)}")

        except Exception as e:
            self.show_popup("Error", f"Failed to validate key identifier column: {e}")
            return

        self.show_popup("Success", "Mappings and key identifier saved successfully!")
        self.process_csv_rows_with_endpoint(duplicate_keys)  # Pass duplicate keys for skipping


    def process_csv_rows_with_endpoint(self, duplicate_keys=set()):
        
        try:
            selected_file = self.file_chooser.selection[0]
            with open(selected_file, 'r') as csv_file:
                reader = csv.DictReader(csv_file)
                skipped_rows = []

                for row in reader:
                    key_value = row.get(self.key_identifier)
                    if not key_value:
                        skipped_rows.append(f"Missing key identifier in row: {row}")
                        continue  # Skip records with missing keys

                    if key_value in duplicate_keys:
                        skipped_rows.append(f"Duplicate key {key_value} in row: {row}")
                        continue  # Skip duplicate keys

                    payload = {}
                    for csv_header, api_field in self.field_mappings.items():
                        if csv_header in row:
                            value = row[csv_header]
                            expected_type = self.api_fields.get(api_field, "string")

                            if expected_type in ["float", "int"]:
                                if self.is_number(value):
                                    payload[api_field] = float(value) if expected_type == "float" else int(value)
                                else:
                                    raise ValueError(f"Invalid number for field '{api_field}': {value}")
                            elif expected_type == "NoneType" and not value:
                                payload[api_field] = None
                            else:
                                payload[api_field] = value  

                    exists = self.check_if_record_exists(key_value)
                    if exists:
                        self.update_existing_record(payload, key_value)
                    else:
                        self.send_to_api(payload)

            if skipped_rows:
                self.show_popup("Warning", f"The following records were skipped:\n{chr(10).join(skipped_rows)}")

        except Exception as e:
            self.show_popup("Error", f"Failed to process CSV rows: {e}")




    def is_number(self, value):
        
        try:
            float(value)
            return True
        except ValueError:
            return False
    
    
    def send_to_api(self, payload):
    
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "Cookie": self.session_token
        }
        try:
            # Remove any trailing slash from base_url and leading slash from endpoint
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

        # Input for the endpoint
        layout.add_widget(Label(text="Enter the REST API Endpoint", font_size=28))
        self.endpoint_input = TextInput(  # Properly define the widget
            hint_text="Enter endpoint (e.g. avatars)",
            multiline=False,
            font_size=24
        )
        layout.add_widget(self.endpoint_input)

        # Submit button
        submit_button = Button(
            text="Fetch API Fields",
            size_hint_y=None,
            height=80,
            background_normal='',
            background_color=(0, 0.5, 1, 1),
            font_size=24
        )

        submit_button.unbind(on_press=self.fetch_api_fields) 
        submit_button.bind(on_press=lambda instance: Clock.schedule_once(self.fetch_api_fields, 0.2))
        layout.add_widget(submit_button)

        return layout
    
    def set_endpoint_and_process_data(self, instance):
        
        if not hasattr(self, 'endpoint_input') or self.endpoint_input is None:
            self.show_popup("Error", "Internal Error: 'endpoint_input' is not initialized!")
            return

        endpoint = self.endpoint_input.text.strip()
        if not endpoint:
            self.show_popup("Error", "Please enter a valid endpoint.")
            return

        self.endpoint = endpoint.lstrip("/")  # Normalize endpoint
        Clock.schedule_once(self.validate_api_endpoint, 1)

    def validate_api_endpoint(self, dt):
        
        try:
            # Construct the full URL from base URL and endpoint
            full_url = f"{self.base_url.rstrip('/')}/{self.endpoint.lstrip('/')}"
            
            # Use headers and cookies for API authentication
            headers = {"accept": "application/json"}
            response = requests.get(full_url, headers=headers, cookies=self.session_token)

            # Check API response
            if response.status_code == 200:
                self.show_popup("Success", "API endpoint validated successfully!")
                Clock.schedule_once(self.delayed_show_mapping_screen, 0.5)  # Proceed to the next screen after delay
            else:
                self.show_popup("Error", f"API connection failed: {response.status_code} - {response.text}")

        except Exception as e:
            self.show_popup("Error", f"Failed to connect to API val end: {e}")


    def delayed_show_mapping_screen(self, dt):
        
        self.root.clear_widgets()
        self.root.add_widget(self.show_mapping_screen())


    def reset_to_login(self):
        
        self.root.clear_widgets()
        self.root.add_widget(self.login_screen())

    def show_popup(self, title, message):
        
        popup = Popup(title=title, content=Label(text=message), size_hint=(0.6, 0.4))
        popup.open()

    def fetch_endpoint_data(self, endpoint):
        
        full_url = f"{self.api_url}{endpoint}"  # Construct full URL
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
        if not hasattr(self, 'endpoint_input'):
            print("Debug: endpoint_input attribute does not exist.")
        elif self.endpoint_input is None:
            print("Debug: endpoint_input is None.")
        else:
            print(f"Debug: endpoint_input value is '{self.endpoint_input.text.strip()}'")
        endpoint = self.endpoint_input.text.strip()
        if not endpoint:
            self.show_popup("Error", "Please enter a valid endpoint.")
            return

        if not endpoint.startswith("/"):
            endpoint = "/" + endpoint
        self.endpoint = endpoint

        try:
            # Fetch existing avatars to deduce fields
            full_url = f"{self.base_url.rstrip('/')}/{self.endpoint.lstrip('/')}"
            headers = {"accept": "application/json", "Cookie": self.session_token}
            response = requests.get(full_url, headers=headers)

            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list) and len(data) > 0:
                    # Deduce fields and types from the first record
                    self.api_fields = {key: type(value).__name__ for key, value in data[0].items()}
                    self.show_popup("Success", "API fields and types fetched successfully!")
                    self.root.clear_widgets()
                    self.root.add_widget(self.show_mapping_screen())
                else:
                    self.show_popup("Error", "No data found at the endpoint to deduce fields.")
            else:
                self.show_popup("Error", f"Failed to fetch data: {response.status_code} - {response.text}")
        
        except AttributeError as e:
            if "fbind" in str(e):  # Check if error is related to fbind
            
                return
        except Exception as e:
            self.show_popup("Error", f"Failed to connect to API: {e}")


    def check_if_record_exists(self, key_value):
   
        try:
            url = f"{self.base_url.rstrip('/')}/{self.endpoint.lstrip('/')}?filter={self.key_identifier}={key_value}"
            headers = {"accept": "application/json", "Cookie": self.session_token}
            response = requests.get(url, headers=headers)

            if response.status_code == 200:
                data = response.json()
                return len(data) > 0  # If the API returns a record, it exists
            else:
                return False
        except Exception as e:
            print(f"Error checking record existence: {e}")
            return False

    def update_existing_record(self, payload, key_value):
      
        try:
            url = f"{self.base_url.rstrip('/')}/{self.endpoint.lstrip('/')}/{key_value}"
            headers = {
                "accept": "application/json",
                "Content-Type": "application/json",
                "Cookie": self.session_token
            }
            response = requests.put(url, json=payload, headers=headers)

            if response.status_code == 200:
                print(f"Record {key_value} updated successfully!")
            else:
                print(f"Failed to update record {key_value}: {response.text}")
        except Exception as e:
            print(f"Error updating record {key_value}: {e}")

if __name__ == "__main__":
    MappingApp().run()