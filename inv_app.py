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
        self.endpoint = "avatars"
    def customize_checkbox(self, checkbox):
        """Apply custom styling to a CheckBox."""
        # Define the background appearance
        with checkbox.canvas.before:
            Color(0.8, 0.8, 0.8, 1)  # Light gray for unchecked state
            Rectangle(size=checkbox.size, pos=checkbox.pos)

        # Ensure the background updates dynamically when the widget resizes or moves
        checkbox.bind(size=self.update_checkbox_background, pos=self.update_checkbox_background)

    def update_checkbox_background(self, checkbox, *args):
        """Update the background rectangle when the CheckBox is resized or moved."""
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
        """Login screen layout."""
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
        """
        Authenticate the user using the fixed base URL.
        """
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
            self.show_popup("Error", f"Failed to connect to API: {e}")

        self.base_url = "http://41.72.150.250/csi-requesthandler/api/v2/"

    def upload_screen(self):
        """Upload screen layout."""
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
        """
        Handle the upload button press and process the selected file from the FileChooser.
        """
        try:
            # Ensure a file is selected
            if not self.file_chooser.selection:
                raise ValueError("No file selected. Please select a CSV file.")

            # Get the selected file path
            file_path = self.file_chooser.selection[0]

            # Open and process the CSV file
            with open(file_path, 'r') as csv_file:
                reader = csv.DictReader(csv_file)
                self.csv_headers = reader.fieldnames
                self.show_popup("Success", "File uploaded successfully!")
                self.show_mapping_screen()
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
                values=["node_name", "description", "default_3d_viewable", "images", "referenced_documents", "size_ranges"],
                size_hint_x=0.7
            )
            self.field_map_dropdowns[header] = dropdown
            hbox.add_widget(dropdown)
            layout.add_widget(hbox)

        save_button = Button(text="Save Mapping", size_hint_y=None, height=50)
        save_button.bind(on_press=self.save_mapping)
        layout.add_widget(save_button)

        self.root.clear_widgets()
        self.root.add_widget(layout)


    def toggle_dropdown(self, header, is_active):
        """Enable or disable the dropdown for a specific header based on checkbox state."""
        self.field_map_dropdowns[header].disabled = not is_active

    def save_mapping(self, instance):
        """
        Save the user-defined field mappings.
        """
        self.field_mappings = {header: dropdown.text for header, dropdown in self.field_map_dropdowns.items() if dropdown.text != "Select API Field"}
        
        if not self.field_mappings:
            self.show_popup("Error", "No fields mapped. Please map at least one field.")
            return
        
        self.show_popup("Success", "Mappings saved successfully!")
        self.process_csv_rows()

    def save_mapping(self, instance):
        """
        Save mappings and process the CSV.
        """
        self.field_mappings = {
            header: dropdown.text for header, dropdown in self.field_map_dropdowns.items() if dropdown.text != "Select API Field"
        }

        if not self.field_mappings:
            self.show_popup("Error", "No fields mapped! Please map at least one field.")
            return

        self.show_popup("Success", "Mappings saved successfully!")
        self.process_csv_rows()

      
        #self.process_csv() 

    def process_csv_rows(self):
    
        try:
            selected_file = self.file_chooser.selection[0]
            with open(selected_file, 'r') as csv_file:
                reader = csv.DictReader(csv_file)
                for row in reader:
                    # Dynamically construct payload, handling missing fields
                    payload = {
                        api_field: row[csv_header]
                        for csv_header, api_field in self.field_mappings.items()
                        if csv_header in row
                    }
                    print("Constructed Payload:", payload)  # Debug the payload
                    self.send_to_api(payload)
            self.show_popup("Success", "All rows processed and sent successfully!")
        except Exception as e:
            self.show_popup("Error", f"Failed to process CSV rows: {e}")
    
    
    def send_to_api(self, payload):
        """
        Send the constructed payload to the API.
        """
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "Cookie": self.session_token  # Assuming token is set during login
        }
        try:
            response = requests.post(self.base_url + "avatars", json=payload, headers=headers)
            if response.status_code == 200:
                print("Data sent successfully:", response.json())
            else:
                print("API error:", response.status_code, response.text)
                raise Exception(f"API error: {response.text}")
        except Exception as e:
            print("Error sending data:", e)
            self.show_popup("Error", f"Failed to send data: {e}")


    def reset_to_login(self):
        """Reset the app to the login screen."""
        self.root.clear_widgets()
        self.root.add_widget(self.login_screen())

    def show_popup(self, title, message):
        """Display a popup message."""
        popup = Popup(title=title, content=Label(text=message), size_hint=(0.6, 0.4))
        popup.open()

    def fetch_endpoint_data(self, endpoint):
        """
        Fetch data from a dynamically provided endpoint.
        """
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

if __name__ == "__main__":
    MappingApp().run()