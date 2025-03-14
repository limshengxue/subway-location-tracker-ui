from typing import Any, Dict


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