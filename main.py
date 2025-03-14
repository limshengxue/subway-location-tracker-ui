import os
import streamlit as st
import folium
from streamlit_folium import folium_static
import requests
import json
from typing import List, Dict, Any
import pandas as pd
from dotenv import load_dotenv
from streamlit_folium import st_folium

# Set page configuration
st.set_page_config(
    page_title="Subway Outlet Map Viewer",
    page_icon="🗺️",
    layout="wide"
)

# Define the data structure for outlets
class Outlet:
    def __init__(self, data: Dict[str, Any]):
        self.id = data.get("id", "")
        self.name = data.get("name", "")
        self.address = data.get("address", "")
        self.latitude = data.get("latitude", 0)
        self.longitude = data.get("longitude", 0)
        self.operating_hours = data.get("operating_hours", "")
        self.waze_link = data.get("waze_link", "")
        self.all_overlapping = data.get("all_overlapping", [])
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "address": self.address,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "operating_hours": self.operating_hours,
            "waze_link": self.waze_link
        }

# Function to fetch data from backend
def fetch_outlet_data():
    try:
        url = os.environ.get("BACKEND_URL") + "outlets"
        response = requests.get(url)
        response.raise_for_status()
        st.session_state.outlet_data = response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching data: {e}")

# Function to create the map with outlet markers
def create_map(outlets: List[Outlet], selected_outlet_id: str = None):
    # Calculate the center of the map
    if outlets:
        center_lat = sum(outlet.latitude for outlet in outlets) / len(outlets)
        center_lng = sum(outlet.longitude for outlet in outlets) / len(outlets)
    else:
        # Default to Kuala Lumpur if no outlets
        center_lat = 3.139003
        center_lng = 101.686855

    # Create a map
    m = folium.Map(location=[center_lat, center_lng], zoom_start=12)
    
    # Create a feature group for markers
    markers = folium.FeatureGroup(name="Outlets")
    
    # Add markers for each outlet
    for outlet in outlets:
        # Create a simple popup without JavaScript events
        popup_html = f"""
        <div style="width: 200px">
            <h4>{outlet.name}</h4>
            <p>{outlet.address}</p>
        </div>
        """
        icon = folium.Icon(color='blue', icon='store', prefix='fa')
    
        # If this is the selected outlet, use a different icon
        if selected_outlet_id and outlet.id == selected_outlet_id:
            icon = folium.Icon(color='red', icon='star', prefix='fa')
        
        marker = folium.Marker(
            location=[outlet.latitude, outlet.longitude],
            popup=folium.Popup(popup_html, max_width=300),
            tooltip=folium.Tooltip(text=outlet.name, style=("background-color: #f0f0f0; padding: 5px; border-radius: 5px;")),
            icon=icon
        )
        marker.add_to(markers)

    markers.add_to(m)

    # Use st_folium to render the map and capture click events
    map_data = st_folium(
        m,
        feature_group_to_add=markers,
        width=800,
        height=600,
        returned_objects=["last_object_clicked"]
    )

    # Check if a marker was clicked
    if (map_data["last_object_clicked"] and 
        "last_clicked_location" not in st.session_state or 
        map_data["last_object_clicked"] != st.session_state.get("last_clicked_location")):
        
        # Update session state with the clicked location
        st.session_state["last_clicked_location"] = map_data["last_object_clicked"]
        
        # Check if a marker was clicked
        if map_data["last_object_clicked"] is not None:
            # Find which outlet was clicked based on coordinates
            clicked_lat = map_data["last_object_clicked"]["lat"]
            clicked_lng = map_data["last_object_clicked"]["lng"]
        
            # Find the matching outlet (using a small margin of error for float comparison)
            for outlet in outlets:
                if (abs(outlet.latitude - clicked_lat) < 0.0001 and 
                    abs(outlet.longitude - clicked_lng) < 0.0001):
                    st.session_state.selected_outlet_id = outlet.id
                    #print(st.session_state.selected_outlet_id)
                    st.rerun()  # Rerun to update the map with the new selected outlet

    
    # If a specific outlet is selected, zoom to it
    if selected_outlet_id:
        for outlet in outlets:
            if outlet.id == selected_outlet_id:
                m.location = [outlet.latitude, outlet.longitude]
                m.zoom_start = 18
                print('zoomed')
                break
    
    return m

# Function to display outlet details    
def display_outlet_details(outlets: List[Outlet]):
    selected_outlet = next(
                (o for o in outlets if o.id == st.session_state.selected_outlet_id), 
                None
            )
    
    # back button
    if st.button("Back"):
        st.session_state.selected_outlet_id = None
        st.rerun()
    
    # Display selected outlet details
    if selected_outlet:
        st.subheader(selected_outlet.name)
        st.write(f"**Address:** {selected_outlet.address}")
        st.write(f"**Operating Hours:** {selected_outlet.operating_hours}")
        
        # Display nearby outlets from overlapping data
        if selected_outlet.all_overlapping:
            st.subheader("Nearby Outlets")
            nearby_outlets = []
            
            for overlap in selected_outlet.all_overlapping:
                # Skip if the outlet info is not in the expected format
                if not isinstance(overlap, dict):
                    continue
                    
                outlet2 = overlap.get("outlet2", {})
                if outlet2.get("id") != selected_outlet.id:
                    nearby_outlets.append({
                        "Name": outlet2.get("name", ""),
                        "Distance (km)": round(overlap.get("distance", 0), 2)
                    })
                
                outlet1 = overlap.get("outlet1", {})
                if outlet1.get("id") != selected_outlet.id:
                    nearby_outlets.append({
                        "Name": outlet1.get("name", ""),
                        "Distance (km)": round(overlap.get("distance", 0), 2)
                    })
            
            if nearby_outlets:
                nearby_df = pd.DataFrame(nearby_outlets)
                nearby_df = nearby_df.sort_values("Distance (km)")
                st.dataframe(nearby_df, hide_index=True)
    
        # Add a Waze navigation button
        if selected_outlet.waze_link:
            st.markdown(f"[Navigate with Waze]({selected_outlet.waze_link})")


def display_outlets_list(outlets: List[Outlet]):
    st.subheader("Outlets")
        
    # Search bar
    search_query = st.text_input("Search outlets", "")
        
    # Filter outlets based on search query
    filtered_outlets = outlets
        
    if search_query:
        filtered_outlets = [
            outlet for outlet in outlets
            if (outlet.address is not None and search_query.lower() in outlet.address.lower()) or
            search_query.lower() in outlet.name.lower()
        ]

    st.markdown(
        """
        <style>
        div.stButton > button {
            white-space: pre-line; /* Ensures text wraps */
            text-align: left; /* Aligns text to left */
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    with st.container(height=400):
        for outlet in filtered_outlets:
            button_label = f"**{outlet.name}**  \n{outlet.address}"
            if st.button(button_label, key=f"btn_{outlet.id}", use_container_width=True):
                st.session_state.selected_outlet_id = outlet.id
                st.rerun()    
   

# Main application
def main():
    # load env variables
    load_dotenv()
    
    st.title("Subway Outlets Location Tracker")
    
    # Initialize session state for the selected outlet
    if "selected_outlet_id" not in st.session_state:
        st.session_state.selected_outlet_id = None
    
    # Layout with columns for sidebar and map
    col1, col2 = st.columns([1, 2])
    
    # Get outlet data from the backend
    if "outlet_data" not in st.session_state:
        fetch_outlet_data()

    # Handle empty data case
    if not st.session_state.get("outlet_data"):
        st.warning("No outlet data available. Please check the backend API URL.")
        return
    
    # Process outlets data
    outlets = [Outlet(data) for data in st.session_state.outlet_data.get("outlets", [])]
    
    with col1:
        # Display details for selected outlet
        if st.session_state.selected_outlet_id:
            display_outlet_details(outlets)
        else:
            display_outlets_list(outlets)
    
    with col2:
        # Create the map
        m = create_map(outlets, st.session_state.selected_outlet_id)
        
        # Use st_folium with specific settings to prevent unnecessary reruns
        map_data = st_folium(
            m, 
            width=725,
            key="map",
            # These settings help prevent reruns on map interactions
            feature_group_to_add=None,
            zoom=None,
            returned_objects=["last_active_drawing"],
            use_container_width=True
        )
        
        # Check if a marker was clicked (not just map interaction)
        if map_data and "last_active_drawing" in map_data and map_data["last_active_drawing"]:
            # Get the marker name (which we set to outlet id)
            clicked_id = map_data["last_active_drawing"].get("name")
            
            # Only update state and rerun if an actual marker was clicked
            # and it's different from the currently selected outlet
            if clicked_id and clicked_id != st.session_state.selected_outlet_id:
                st.session_state.selected_outlet_id = clicked_id
                st.rerun()

if __name__ == "__main__":
    main()