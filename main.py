import os
import streamlit as st
import folium
import requests
from typing import List
import pandas as pd
from dotenv import load_dotenv
from streamlit_folium import st_folium
from models import Outlet
from utils import get_last_updated_time
from qa import qa

# Set page configuration
st.set_page_config(
    page_title="Subway Outlets Location Tracker",
    page_icon="🗺️",
    layout="wide"
)

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
def create_map(outlets: List[Outlet], selected_outlet : Outlet):
    # Calculate the center of the map
    if outlets:
        center_lat = sum(outlet.latitude for outlet in outlets) / len(outlets)
        center_lng = sum(outlet.longitude for outlet in outlets) / len(outlets)
    else:
        # Default to Kuala Lumpur if no outlets
        center_lat = float(os.getenv("DEFAULT_CENTER_LAT"))
        center_lng = float(os.getenv("DEFAULT_CENTER_LNG"))

    # Create a map
    m = folium.Map(location=[center_lat, center_lng], zoom_start=12)
    
    # Create a feature group for markers
    markers = folium.FeatureGroup(name="Outlets")

    # get selected outlet overlapping outlets
    overlapping_outlets_ids = []
    if selected_outlet:
        for overlap in selected_outlet.all_overlapping:
            if overlap.get("outlet1").get("id") != selected_outlet.id:
                overlapping_outlets_ids.append(overlap.get("outlet1").get("id"))
            if overlap.get("outlet2").get("id") != selected_outlet.id:
                overlapping_outlets_ids.append(overlap.get("outlet2").get("id"))

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
        if selected_outlet and outlet.id == selected_outlet.id:
            icon = folium.Icon(color='red', icon='star', prefix='fa')
        
        # if this is a overlapping outlet, use a different icon
        if outlet.id in overlapping_outlets_ids:
            icon = folium.Icon(color='orange', icon='exclamation', prefix='fa')
        
        # create the marker
        marker = folium.Marker(
            location=[outlet.latitude, outlet.longitude],
            popup=folium.Popup(popup_html, max_width=300),
            tooltip=folium.Tooltip(text=outlet.name, style=("background-color: #f0f0f0; padding: 5px; border-radius: 5px;")),
            icon=icon
        )
        
        # Add the marker to the feature group
        marker.add_to(markers)

    # Add the feature group to the map
    markers.add_to(m)

    # zoom map to selected outlet
    if selected_outlet:
        margin = 0.02
        m.fit_bounds(
            [[selected_outlet.latitude - margin, selected_outlet.longitude - margin], 
            [selected_outlet.latitude + margin, selected_outlet.longitude + margin]]
        )

        # Add a geodesic circle with a 5 km radius
        folium.Circle(
            location=[selected_outlet.latitude, selected_outlet.longitude],
            radius=5000,  # 5 km in meters
            color='blue',
            fill=True,
            fill_color='blue',
            fill_opacity=0.2
        ).add_to(m)

    # Use st_folium to render the map and capture click events
    map_data = st_folium(
        m,
        feature_group_to_add=markers,
        width=800,
        height=600,
        use_container_width=True,
        key="map",
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
                    st.session_state.selected_outlet = outlet
                    st.rerun()

    return map_data

# Function to display outlet details    
def display_outlet_details(selected_outlet: Outlet):
    # back button
    if st.button("Back"):
        st.session_state.selected_outlet = None
        st.rerun()
    
    # Display selected outlet details
    if selected_outlet:
        st.subheader(selected_outlet.name)
        
        if selected_outlet.address is not None:
            st.markdown(f"**Address:**<br>{selected_outlet.address.replace('\n', '<br>')}", unsafe_allow_html=True)
        else:
            st.markdown("**Address:**<br>Not available", unsafe_allow_html=True)

         # Add a Waze navigation button
        if selected_outlet.waze_link:
            st.markdown(
                f"""
                <a href='{selected_outlet.waze_link}' target='_blank'>
                    <img src='https://www.waze.com/favicon.ico' width='16' height='16' style='vertical-align: middle;'>
                    Navigate with Waze
                </a>
                <br>
                """,
                unsafe_allow_html=True
            )

        # add line break
        st.markdown("<br>", unsafe_allow_html=True)

        if selected_outlet.operating_hours is not None:
            st.markdown(f"**Operating Hours:**<br>{selected_outlet.operating_hours.replace('\n', '<br>')}", unsafe_allow_html=True)
        else:
            st.markdown("**Operating Hours:**<br>Not available", unsafe_allow_html=True)

        
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

def display_outlets_list(outlets: List[Outlet]):
    last_updated = get_last_updated_time(st.session_state.outlet_data["last_updated"])

    st.write("Data last updated on:", last_updated)

    # Search bar
    search_query = st.text_input("Search outlets", "", placeholder="Search by name or address")
        
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
                st.session_state.selected_outlet = outlet
                st.rerun()    
   

# Main application
def main():
    # load env variables
    load_dotenv()
    
    st.title("Subway Outlets Location Tracker")
    
    # Initialize session state for the selected outlet
    if "selected_outlet" not in st.session_state:
        st.session_state.selected_outlet = None
    
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
        if st.session_state.selected_outlet:
            display_outlet_details(st.session_state.selected_outlet)
        else:
            display_outlets_list(outlets)
    
    with col2:
        # Create the map
        m = create_map(outlets, st.session_state.selected_outlet)
    
    # show divider
    st.markdown("---")
    
    # Display qa
    qa()

        

if __name__ == "__main__":
    main()