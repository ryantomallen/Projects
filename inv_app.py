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

class MappingApp(App):
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
        base_url = "http://41.72.150.250"  # Fixed base URL

        # Payload for login
        payload = {
            "username": username,
            "password": password,
        }

        try:
            # Send POST request to login
            response = requests.post(f"{base_url}", json=payload)
            if response.status_code == 200:
                self.session_token = response.cookies  # Store session cookies
                self.show_popup("Success", "Login successful!")
                self.root.clear_widgets()
                self.root.add_widget(self.upload_screen())  # Move to the upload screen
            else:
                self.show_popup("Error", f"Login failed: {response.text}")
        except Exception as e:
            self.show_popup("Error", f"Failed to connect to API: {e}")

            try:
                # Correct Centric 8 login endpoint
                response = requests.post(f"{self.api_url}csi-requesthandler/RequestHandler", data=payload)
                if response.status_code == 200:
                    self.session_token = response.cookies  # Store session cookies
                    self.show_popup("Success", "Login successful!")
                    self.root.clear_widgets()
                    self.root.add_widget(self.upload_screen())  # Move to the next screen
                else:
                    # Handle API error response and show the actual message
                    error_message = response.text if response.text else "Login failed. Please check your credentials."
                    self.show_popup("Error", error_message)
            except Exception as e:
                self.show_popup("Error", f"Failed to connect to API: {e}")



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
        upload_button.bind(on_press=self.upload_file)
        layout.add_widget(upload_button)

        # Logout button
        logout_button = Button(text="Logout", size_hint_y=None, height=80, background_normal='', background_color=(0.9, 0.1, 0.1, 1), font_size=28)
        logout_button.bind(on_press=lambda x: self.reset_to_login())
        layout.add_widget(logout_button)

        return layout


    def upload_file(self, instance):
        """Upload CSV file and start mapping."""
        selected_file = self.file_chooser.selection

        if not selected_file:
            self.show_popup("Error", "Please select a CSV file to upload!")
            return

        try:
            with open(selected_file[0], "r") as file:
                # Use csv.Sniffer to detect the delimiter
                sample = file.read(1024)
                file.seek(0)  # Reset file pointer to the beginning
                sniffer = csv.Sniffer()
                delimiter = sniffer.sniff(sample).delimiter

                # Use the detected delimiter to read the CSV
                reader = csv.reader(file, delimiter=delimiter)
                self.csv_headers = next(reader)  # Extract headers (first row)

                # Check if headers exist, if not show error
                if not self.csv_headers:
                    self.show_popup("Error", "The CSV file has no headers.")
                    return

                self.root.clear_widgets()
                self.root.add_widget(self.mapping_screen())  # Now dynamically create the spinners based on headers
        except Exception as e:
            self.show_popup("Error", f"Failed to read file: \n{e}")

    def mapping_screen(self):
        """Mapping screen with checkboxes and generic field names."""
        layout = BoxLayout(orientation='vertical', padding=50, spacing=50)

        scrollview = ScrollView()
        mapping_layout = BoxLayout(orientation='vertical', size_hint_y=None)
        mapping_layout.bind(minimum_height=mapping_layout.setter('height'))

        # Create a list of generic field names
        field_options = [f"Field {i+1}" for i in range(len(self.csv_headers))]
        field_options.append("Skip")  # Allow skipping fields

        # Loop through CSV headers and dynamically create UI elements
        self.field_map_checkboxes = {}  # Store checkboxes for each header
        self.field_map_dropdowns = {}  # Store dropdowns for each header

        for header in self.csv_headers:
            row = BoxLayout(size_hint_y=None, height=100, padding=20)

            # Add checkbox for each field
            checkbox = CheckBox(size_hint_x=0.4)
            self.customize_checkbox(checkbox)  # Apply custom styling
            self.field_map_checkboxes[header] = checkbox
            row.add_widget(checkbox)


            # Display the CSV header name
            row.add_widget(Label(text=f"CSV Header: {header}", size_hint_x=0.4, font_size=28))

            # Add dropdown (initially disabled)
            dropdown = Spinner(
                text="Select Field",
                values=field_options,
                size_hint_x=0.5,
                disabled=True,  # Initially disabled
                background_color=(0.9, 0.9, 0.9, 1),
                font_size=24
            )
            self.field_map_dropdowns[header] = dropdown
            row.add_widget(dropdown)

            # Bind checkbox to enable/disable the dropdown
            checkbox.bind(active=lambda instance, value, h=header: self.toggle_dropdown(h, value))
            
            mapping_layout.add_widget(row)

        scrollview.add_widget(mapping_layout)
        layout.add_widget(scrollview)

        save_button = Button(text="Save Mapping and Process", size_hint_y=None, height=80, background_normal='', background_color=(0, 0.5, 1, 1), font_size=28)
        save_button.bind(on_press=self.save_mapping)
        layout.add_widget(save_button)

        return layout

    def toggle_dropdown(self, header, is_active):
        """Enable or disable the dropdown for a specific header based on checkbox state."""
        self.field_map_dropdowns[header].disabled = not is_active

    def save_mapping(self, instance):
        """Save mappings and process the CSV."""
        mapping_result = {header: spinner.text for header, spinner in self.field_map_dropdowns.items() if spinner.text != "Skip"}

        if not mapping_result:
            self.show_popup("Error", "No fields mapped! Please map at least one field.")
            return

        # Process CSV with the valid mapping
        self.process_csv(mapping_result)
        self.saved_mappings = mapping_result
        self.show_popup("Success", "Mappings saved successfully!")
      
        self.process_csv_rows()

    def process_csv(self, mapping_result):
        """Apply mappings to CSV rows and send them to the API."""
        try:
            with open(self.file_chooser.selection[0], "r") as file:
                reader = csv.DictReader(file)
                for row in reader:
                    mapped_data = {mapping_result[header]: value for header, value in row.items() if header in mapping_result}
                    self.send_to_api(mapped_data)
                self.show_popup("Success", "CSV data processed and sent successfully!")
        except Exception as e:
            self.show_popup("Error", f"Failed to process CSV: \n{e}")

    def send_to_api(self, file_path):
        """Send file to the REST API."""
        try:
            with open(file_path, 'rb') as f:
                files = {'file': f}
                response = requests.post(f"{self.api_url}/upload", files=files)
                if response.status_code == 200:
                    self.show_popup("Success", f"File uploaded: {response.json().get('file_path')}")
                else:
                    raise Exception(response.text)
        except Exception as e:
            self.show_popup("Error", f"Failed to upload file: \n{e}")


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