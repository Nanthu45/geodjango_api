from django.urls import path
from .views import Csv_to_Database, upload_csv_form,CSV_to_Json,Latlong_PSQLPoint,Latlong_PSQLPoint
from .views import TIFF_DrawTrajectory,CSV_to_TransformedGeoJson,CSV_to_GeoJson

urlpatterns = [
    path('upload_csv_tiff/', upload_csv_form, name='upload-form'),
    path('csv_uploaded/', Csv_to_Database.as_view(), name='csv_upload'),
    path('json_downloaded/', CSV_to_Json.as_view(), name='json_download'),
    path('geojson_download-/', CSV_to_GeoJson.as_view(), name='geojson_download'),
    path('transformed-geojson_downloaded/', CSV_to_TransformedGeoJson.as_view(), name='transformed_geojson_download'), 
    path('trajectory_geotiff/', TIFF_DrawTrajectory.as_view(), name='load_geotiff_and_draw_trajectory'),  
    path('latlong_to_geompsql/', Latlong_PSQLPoint.as_view(), name='lat_long_to_geompsql_point'),
    path('latlong_to_linstring/',Latlong_PSQLPoint.as_view(), name='lat_long_to_linestring'),
]




