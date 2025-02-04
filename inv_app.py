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
import os
import time

class MappingApp(App):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # We'll store & load config from this file
        self.config_filename = "mapping_config.json"
        # load config at startup
        self.config_data = self.load_config()
        self.base_url = self.config_data.get("base_url", "")
        self.saved_username = self.config_data.get("username", "")
        self.endpoint = self.config_data.get("endpoint", "")
        self.key_column = self.config_data.get("key_column", None)
        self.field_mappings = self.config_data.get("field_mappings", {})
        self.csv_headers = []
        self.session_token = None
        self.rows_to_process = []
        self.current_row_index = 0
        self.api_fields = {}
        self.results_log = []

    def build(self):
        return self.login_screen()

  
    #LOGIN SCREEN
    
    def login_screen(self):
        layout = BoxLayout(orientation='vertical', padding=60, spacing=60)

        layout.add_widget(Label(text="Environmental URL", font_size=40, color=(1, 1, 1, 1)))
        self.base_url_input = TextInput(
            hint_text="Enter URL starting with http://",
            multiline=False,
            size_hint_y=None,
            height=100,
            font_size=32
        )
       
        if self.base_url:
            self.base_url_input.text = self.base_url
        layout.add_widget(self.base_url_input)

        layout.add_widget(Label(text="Username", font_size=40, color=(1, 1, 1, 1)))
        self.username_input = TextInput(
            hint_text="Enter Username",
            multiline=False,
            size_hint_y=None,
            height=100,
            font_size=32
        )
        # Pre-fill if we had a saved username
        if self.saved_username:
            self.username_input.text = self.saved_username
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

               
                self.config_data["base_url"] = self.base_url
                self.config_data["username"] = username
               

                self.root.clear_widgets()
                # If we already had an endpoint saved could skip or show next screen
                if self.endpoint:
                    # Possibly skip endpoint input
                    self.root.add_widget(self.upload_screen())
                else:
                    #normal flow
                    self.root.add_widget(self.upload_screen())

            else:
                self.show_popup("Error", f"Login failed: {response.text}")
        except requests.exceptions.RequestException as e:
            self.show_popup("Error", f"Failed to connect: {e}")

    
     #UPLOAD SCREEN
   
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
        if not self.file_chooser.selection:
            self.show_popup("Error", "No file selected.")
            return

        file_path = self.file_chooser.selection[0]
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                self.csv_headers = reader.fieldnames or []
            self.show_popup("Success", "File uploaded successfully!")

            self.root.clear_widgets()
            
            if self.endpoint:
                # skip or show mapping
                self.root.add_widget(self.endpoint_input_screen(skip_if_pre_filled=True))
            else:
                self.root.add_widget(self.endpoint_input_screen(skip_if_pre_filled=False))

        except Exception as e:
            self.show_popup("Error", f"Failed to process CSV: {e}")

   
    #ENDPOINT INPUT SCREEN
    
    def endpoint_input_screen(self, skip_if_pre_filled=False):
        layout = BoxLayout(orientation='vertical', padding=50, spacing=50)

        if skip_if_pre_filled and self.endpoint:
           
            pass

        layout.add_widget(Label(text="Enter the REST API Endpoint", font_size=28))
        self.endpoint_input = TextInput(
            hint_text="...",
            multiline=False,
            font_size=24
        )
        if self.endpoint:
            self.endpoint_input.text = self.endpoint  # pre-fill

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
                    self.api_fields = {k: type(v).__name__ for k, v in data[0].items()}
                    self.show_popup("Success", "API fields and types fetched successfully!")
                    
                    self.config_data["endpoint"] = self.endpoint
                    
                    # Clear the current screen
                    self.root.clear_widgets()
                    # Always show the mapping screen
                    self.root.add_widget(self.show_key_and_mapping_screen())
                else:
                    self.show_popup("Error", "No data found at the endpoint to deduce fields.")
            else:
                self.show_popup("Error", f"Failed to fetch data: {resp.status_code} - {resp.text}")
        except requests.exceptions.RequestException as e:
            self.show_popup("Error", f"Error fetching endpoint: {e}")


    
    #KEY COLUMN/MAPPING SCREEN
    
    def show_key_and_mapping_screen(self):
        layout = BoxLayout(orientation='vertical', spacing=20, padding=20)

        layout.add_widget(Label(text="Select Key Column and Map Fields (or Skip)", font_size=24))

        key_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=40)
        key_row.add_widget(Label(text="Key Column:", size_hint_x=0.3))
        self.key_column_spinner = Spinner(
            text="Select Key Column",
            values=self.csv_headers,
            size_hint_x=0.7
        )
        key_row.add_widget(self.key_column_spinner)
        layout.add_widget(key_row)

        if self.key_column and self.key_column in self.csv_headers:
            # pre-select saved key column
            self.key_column_spinner.text = self.key_column

        layout.add_widget(Label(text="Map CSV Headers to API Fields", font_size=20))

        self.field_map_dropdowns = {}
        spinner_choices = list(self.api_fields.keys()) + ["Skip Field"]

        for csv_header in self.csv_headers:
            row = BoxLayout(orientation='horizontal', size_hint_y=None, height=40)
            row.add_widget(Label(text=csv_header, size_hint_x=0.3))

            dropdown = Spinner(
                text="Select API Field",
                values=spinner_choices,
                size_hint_x=0.7
            )
            self.field_map_dropdowns[csv_header] = dropdown
            row.add_widget(dropdown)
            layout.add_widget(row)

            
            saved_field = self.field_mappings.get(csv_header)
            if saved_field:
                dropdown.text = saved_field

        save_button = Button(
            text="Save and Proceed",
            size_hint_y=None,
            height=50
        )
        save_button.bind(on_press=self.handle_key_column_and_mapping)
        layout.add_widget(save_button)

        return layout

    def handle_key_column_and_mapping(self, instance):
        chosen_key = self.key_column_spinner.text.strip()
        if chosen_key not in self.csv_headers:
            self.show_popup("Error", "Please select a valid key column.")
            return

        if not self.check_for_duplicates(chosen_key):
            return
        self.key_column = chosen_key

        temp_mappings = {}
        for csv_header, spinner_widget in self.field_map_dropdowns.items():
            api_field = spinner_widget.text
            if api_field not in ("Skip Field", "Select API Field"):
                temp_mappings[csv_header] = api_field

        if not temp_mappings:
            self.show_popup("Error", "No fields mapped! Please map at least one field.")
            return

        self.field_mappings = temp_mappings

        self.show_popup("Success", f"Key column '{self.key_column}' and mappings saved!")
        # Store in config
        self.config_data["key_column"] = self.key_column
        self.config_data["field_mappings"] = self.field_mappings

        self.start_csv_processing()

    def check_for_duplicates(self, column_name):
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

   
    #PROCESS CSV
   
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
            self.results_log.clear()
            self.process_next_row()
        except Exception as e:
            self.show_popup("Error", f"Failed to read CSV: {e}")

    def process_next_row(self):
        if self.current_row_index >= len(self.rows_to_process):
            self.show_final_summary_screen()
            return

        row = self.rows_to_process[self.current_row_index]
        try:
            payload = self.build_payload(row)
        except Exception as e:
            self.results_log.append({
                "row_index": self.current_row_index,
                "status": "fail",
                "error": f"Data conversion error: {e}",
                "action": None
            })
            self.current_row_index += 1
            self.process_next_row()
            return

        key_value = row.get(self.key_column, None)
        if not key_value:
            self.results_log.append({
                "row_index": self.current_row_index,
                "status": "fail",
                "error": "No key value found in this row",
                "action": None
            })
            self.current_row_index += 1
            self.process_next_row()
            return

        existing_id = self.fetch_id_by_key_value(self.key_column, key_value)

        if existing_id is not None:
            #Update or Create
            self.show_update_or_create_popup(existing_id, payload, key_value)
        else:
            self.create_record(payload, row_index=self.current_row_index)
            self.current_row_index += 1
            self.process_next_row()

    def fetch_id_by_key_value(self, key_column, key_value):
        api_field_for_key = self.field_mappings.get(key_column)
        if not api_field_for_key:
            return None

        url = f"{self.base_url}/csi-requesthandler/api/v2/{self.endpoint}?{api_field_for_key}={key_value}"
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "Cookie": self.session_token
        }

        success, result = self._request_with_retry("GET", url, headers=headers)
        if not success:
            print(f"Fetch ID request failed: {result}")
            return None

        resp = result
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, list) and len(data) > 0:
                return data[0].get("id")
            elif isinstance(data, dict):
                return data.get("id")
            return None
        else:
            return None

    def show_update_or_create_popup(self, resource_id, payload, key_value):
        layout = BoxLayout(orientation='vertical', spacing=10, padding=10)
        msg = (
            f"Key '{key_value}' already exists (id={resource_id}).\n"
            "Choose an action:"
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
            self.update_record(resource_id, payload, row_index=self.current_row_index)
            self.current_row_index += 1
            self.process_next_row()

        def on_create(instance):
            popup.dismiss()
            self.create_record(payload, row_index=self.current_row_index)
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

    def is_number(self, val):
        try:
            float(val)
            return True
        except ValueError:
            return False

    
    #C/U
    
    def create_record(self, payload, row_index):
        url = f"{self.base_url}/csi-requesthandler/api/v2/{self.endpoint}"
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "Cookie": self.session_token
        }

        success, result = self._request_with_retry("POST", url, headers=headers, json=payload)
        if success:
            resp = result
            #200 or 201 as success
            if resp.status_code in (200, 201):
                self.results_log.append({
                    "row_index": row_index,
                    "status": "success",
                    "error": None,
                    "action": "create"
                })
            else:
                self.results_log.append({
                    "row_index": row_index,
                    "status": "fail",
                    "error": f"Create error: {resp.status_code} - {resp.text}",
                    "action": "create"
                })
        else:
            self.results_log.append({
                "row_index": row_index,
                "status": "fail",
                "error": f"Create request exception: {result}",
                "action": "create"
            })

    def update_record(self, resource_id, payload, row_index):
        url = f"{self.base_url}/csi-requesthandler/api/v2/{self.endpoint}/{resource_id}"
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "Cookie": self.session_token
        }

        success, result = self._request_with_retry("PUT", url, headers=headers, json=payload)
        if success:
            resp = result
            if resp.status_code in (200, 201):
                self.results_log.append({
                    "row_index": row_index,
                    "status": "success",
                    "error": None,
                    "action": "update"
                })
            else:
                self.results_log.append({
                    "row_index": row_index,
                    "status": "fail",
                    "error": f"Update error: {resp.status_code} - {resp.text}",
                    "action": "update"
                })
        else:
            self.results_log.append({
                "row_index": row_index,
                "status": "fail",
                "error": f"Update request exception: {result}",
                "action": "update"
            })

    def _request_with_retry(self, method, url, headers=None, json=None, max_retries=3, backoff_factor=1):
        
        attempt = 0
        while attempt < max_retries:
            try:
                if method.upper() == "POST":
                    resp = requests.post(url, headers=headers, json=json)
                elif method.upper() == "PUT":
                    resp = requests.put(url, headers=headers, json=json)
                elif method.upper() == "GET":
                    resp = requests.get(url, headers=headers)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")

                # Retry on 5xx
                if 500 <= resp.status_code < 600:
                    if attempt < max_retries - 1:
                        sleep_time = backoff_factor * (2 ** attempt)
                        time.sleep(sleep_time)
                    attempt += 1
                else:
                    return (True, resp)

            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                if attempt < max_retries - 1:
                    sleep_time = backoff_factor * (2 ** attempt)
                    time.sleep(sleep_time)
                attempt += 1
                if attempt >= max_retries:
                    return (False, e)
            except Exception as e:
                return (False, e)

        return (False, f"Request failed after {max_retries} attempts.")

    
    #LASTMINUTE
    
    def show_final_summary_screen(self):
        layout = BoxLayout(orientation='vertical', spacing=10, padding=10)

        total_rows = len(self.results_log)
        success_count = sum(1 for r in self.results_log if r["status"] == "success")
        fail_count = total_rows - success_count

        summary_text = (
            f"Processing complete!\n\n"
            f"Total rows processed: {total_rows}\n"
            f"Successes: {success_count}\n"
            f"Failures: {fail_count}\n"
        )

        summary_label = Label(text=summary_text, size_hint_y=None, height=200)
        layout.add_widget(summary_label)

        export_button = Button(text="Export CSV Log", size_hint_y=None, height=50)
        export_button.bind(on_press=self.on_export_csv_pressed)
        layout.add_widget(export_button)

        save_config_button = Button(text="Save Config", size_hint_y=None, height=50)
        save_config_button.bind(on_press=self.on_save_config_pressed)
        layout.add_widget(save_config_button)

        close_button = Button(text="Close / Return to Main Menu", size_hint_y=None, height=50)
        close_button.bind(on_press=lambda x: self.reset_to_login())
        layout.add_widget(close_button)

        self.root.clear_widgets()
        self.root.add_widget(layout)

    def on_export_csv_pressed(self, instance):
        output_filename = "results_log.csv"
        self.export_results_to_csv(output_filename)
        self.show_popup("Export", f"Results log saved to {output_filename}")

    def on_save_config_pressed(self, instance):
       
        self.config_data["base_url"] = self.base_url
        self.config_data["endpoint"] = self.endpoint
        self.config_data["key_column"] = self.key_column
        self.config_data["field_mappings"] = self.field_mappings

        self.save_config(self.config_data)
        self.show_popup("Save Config", "Configuration saved to file!")

    def export_results_to_csv(self, filename):
        import csv
        fieldnames = ["row_index", "status", "error", "action"]
        try:
            with open(filename, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for entry in self.results_log:
                    writer.writerow(entry)
            print(f"Exported results log to {filename}")
        except Exception as e:
            self.show_popup("Error", f"Could not write CSV: {e}")

    def reset_to_login(self):
        self.root.clear_widgets()
        self.root.add_widget(self.login_screen())

    def show_popup(self, title, message):
        popup = Popup(title=title, content=Label(text=message), size_hint=(0.6, 0.4))
        popup.open()

    def load_config(self):
        
        if os.path.exists(self.config_filename):
            try:
                with open(self.config_filename, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                print("Loaded config from file:", data)
                return data
            except Exception as e:
                print("Error reading config file:", e)
                return {}
        return {}

    def save_config(self, data):
       
        try:
            with open(self.config_filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            print("Saved config to file:", data)
        except Exception as e:
            print("Error saving config file:", e)


if __name__ == "__main__":
    MappingApp().run()
