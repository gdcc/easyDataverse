from typing import List
from easyDataverse import Dataset
from easyDataverse.core.base import DataverseBase


def test_netcdf_parser():
    """Tests the extraction of data from NetCDF"""

    class BoundingBox(DataverseBase):
        east_longitude: float
        west_longitude: float
        north_longitude: float
        south_longitude: float

    class Geospatial(DataverseBase):
        _metadatablock_name: str = "geospatial"
        bounding_box: List[BoundingBox] = []

        def add_bounding_box(
            self,
            east_longitude: float,
            west_longitude: float,
            north_longitude: float,
            south_longitude: float,
        ):
            return self.bounding_box.append(
                BoundingBox(
                    east_longitude=east_longitude,
                    west_longitude=west_longitude,
                    north_longitude=north_longitude,
                    south_longitude=south_longitude,
                )
            )

    # Simulate a dataset that has a geospatial metadatablock
    dataset = Dataset()
    dataset.add_metadatablock(Geospatial())

    # Parse the NetCDF file
    dataset.parse_netcdf_file("./tests/fixtures/parsers/test_netcdf.nc")

    expected = {
        "east_longitude": -10.0,
        "north_longitude": 90.0,
        "south_longitude": -90.0,
        "west_longitude": -180.0,
    }

    assert (
        dataset.geospatial.bounding_box[0].dict() == expected
    ), "The bounding box extracted from the NetCDF file does not match the expected values."
