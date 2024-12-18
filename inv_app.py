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
import csv
import requests


class MappingApp(App):
    def build(self):
        self.api_url = None
        self.mappings = {}
        self.csv_headers = []
        return self.login_screen()


    def login_screen(self):
        """Login screen layout."""
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
 
 
        layout.add_widget(Label(text="API Environment URL"))
        self.url_input = TextInput(hint_text="Enter API URL", multiline=False)
        layout.add_widget(self.url_input)
 
 
        layout.add_widget(Label(text="Email"))
        self.email_input = TextInput(hint_text="Enter Email", multiline=False)
        layout.add_widget(self.email_input)
 
 
        layout.add_widget(Label(text="Password"))
        self.password_input = TextInput(hint_text="Enter Password", multiline=False, password=True)
        layout.add_widget(self.password_input)
 
 
        login_button = Button(text="Login")
        login_button.bind(on_press=self.authenticate)
        layout.add_widget(login_button)
 
 
        return layout
 
 
    def authenticate(self, instance):
        email = self.email_input.text
        password = self.password_input.text
        self.api_url = self.url_input.text.strip()
 
 
        if email == "fake@name.com" and password == "helloworld" and self.api_url:
            self.root.clear_widgets()
            self.root.add_widget(self.upload_screen())
        else:
            self.show_popup("Error", "Invalid login credentials or missing API URL!")
 
 
    def upload_screen(self):
        """Upload screen layout."""
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
 
 
        title = Label(text="Upload CSV File", font_size=18)
        layout.add_widget(title)
 
 
        self.file_chooser = FileChooserListView(filters=["*.csv"])
        layout.add_widget(self.file_chooser)
 
 
        upload_button = Button(text="Upload and Map")
        upload_button.bind(on_press=self.upload_file)
        layout.add_widget(upload_button)
 
 
        logout_button = Button(text="Logout")
        logout_button.bind(on_press=lambda x: self.reset_to_login())
        layout.add_widget(logout_button)
 
 
        return layout
 
 
    def upload_file(self, instance):
       
        selected_file = self.file_chooser.selection

        if selected_file:
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
                    
                    self.root.clear_widgets() 
                    self.root.add_widget(self.mapping_screen())  # Now dynamically create the spinners based on headers
            except Exception as e:
                self.show_popup("Error", f"Failed to read file: \n{e}")
        else:
            self.show_popup("Error", "No file selected!")
 
 
    def mapping_screen(self):
        """Mapping screen with checkboxes and generic field names."""
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

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
            row = BoxLayout(size_hint_y=None, height=40, padding=5)
            
            # Add checkbox for each field
            checkbox = CheckBox(size_hint_x=0.1)
            self.field_map_checkboxes[header] = checkbox
            row.add_widget(checkbox)

            # Display the CSV header name
            row.add_widget(Label(text=f"CSV Header: {header}", size_hint_x=0.4))

            # Add dropdown (initially disabled)
            dropdown = Spinner(
                text="Select Field",
                values=field_options,
                size_hint_x=0.5,
                disabled=True  # Initially disabled
            )
            self.field_map_dropdowns[header] = dropdown
            row.add_widget(dropdown)

            # Bind checkbox to enable/disable the dropdown
            checkbox.bind(active=lambda instance, value, h=header: self.toggle_dropdown(h, value))
            
            mapping_layout.add_widget(row)

        scrollview.add_widget(mapping_layout)
        layout.add_widget(scrollview)

        save_button = Button(text="Save Mapping and Process")
        save_button.bind(on_press=self.save_mapping)
        layout.add_widget(save_button)

        return layout

 
    def toggle_dropdown(self, header, is_active):
        """Enable or disable the dropdown for a specific header based on checkbox state."""
        self.field_map_dropdowns[header].disabled = not is_active

 
    def save_mapping(self, instance):
        """Save mappings and process the CSV."""
        mapping_result = {header: spinner.text for header, spinner in self.mappings.items() if spinner.text != "Skip"}
 
 
        if not mapping_result:
            self.show_popup("Error", "No fields mapped! Please map at least one field.")
            return
 
 
        self.process_csv(mapping_result)
 
 
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
 
 
    def send_to_api(self, data):
        """Send mapped row to the REST API."""
        try:
            response = requests.post(f"{self.api_url}/upload", json=data)
            if response.status_code != 200:
                raise Exception(response.text)
        except Exception as e:
            self.show_popup("Error", f"Failed to send data: \n{e}")
 
 
    def reset_to_login(self):
        """Reset the app to the login screen."""
        self.root.clear_widgets()
        self.root.add_widget(self.login_screen())


    def show_popup(self, title, message):
        """Display a popup message."""
        popup = Popup(title=title, content=Label(text=message), size_hint=(0.6, 0.4))
        popup.open()




if __name__ == "__main__":
    MappingApp().run()