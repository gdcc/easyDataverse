from typing import Dict
from dotted_dict import DottedDict

try:
    import netCDF4 as nc
except ImportError:
    raise ImportError(
        "NetCDF4 is required to use this module. You may need to install it with 'pip install netCDF4'"
    )


def parse_netcdf(path: str) -> Dict:
    """Parses a NetCDF file and extracts the bounding box from it."""

    try:
        netcdf_ds = nc.Dataset(path)
    except OSError:
        raise ValueError(f"File at {path} is not a valid NetCDF file.")

    # Extract the bounding box
    bounding_box = extract_bounding_box_from_netcdf(netcdf_ds)

    return {
        "bounding_box": bounding_box,
    }


def extract_bounding_box_from_netcdf(netcdf_ds: nc.Dataset) -> Dict[str, float]:
    """
    Extracts the bounding box of a NetCDF file and adds it to the dataset,
    if the 'geospatial' metadatablock is present.

    Args:
        path (str): Path to the NetCDF file.
        dataset (Dataset): Dataset object to which the bounding box should be added.
    """

    # Check if the required metadata is present
    if not has_longitude_and_latidue(netcdf_ds):
        raise ValueError(
            f"The provided NetCDF file does not have the required min/max longitude and min/max latitude variables."
        )

    # Extract the bounding box
    return DottedDict(
        east_longitude=shift_longitude_interval(netcdf_ds.geospatial_lon_max),
        west_longitude=shift_longitude_interval(netcdf_ds.geospatial_lon_min),
        north_longitude=float(netcdf_ds.geospatial_lat_max),
        south_longitude=float(netcdf_ds.geospatial_lat_min),
    )


def has_longitude_and_latidue(netcdf_ds: nc.Dataset) -> bool:
    """Checks whether a NetCDF file has the required longitude and latitude variables"""

    return (
        hasattr(netcdf_ds, "geospatial_lat_min")
        and hasattr(netcdf_ds, "geospatial_lat_max")
        and hasattr(netcdf_ds, "geospatial_lon_min")
        and hasattr(netcdf_ds, "geospatial_lon_max")
    )


def is_float(number_string: str) -> bool:
    """Checks whether a string is a float"""

    try:
        float(number_string)
        return True
    except ValueError:
        return False


def shift_longitude_interval(degree_string: str) -> float:
    """
    Takes a longitude and transforms it to the [-180°, 180°] interval if deg > 180°

    Substraction of 360° ensures conformity to the desired interval. Since
    the interval itself is cyclic everything over 180° naturally will end
    up in the desired negative degree interval.

    """

    assert is_float(
        degree_string
    ), f"Expected numeric string, got '{degree_string}' instead, which is not a number."

    if isinstance(degree_string, str):
        degree = float(degree_string)

    if degree > 180:
        return degree - 360

    return degree
