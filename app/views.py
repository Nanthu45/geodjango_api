import csv
import io
import json
import geojson
import datetime
from django.http import HttpResponse, FileResponse
from django.core.files.storage import default_storage
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from PIL import Image, ImageDraw
import rasterio
from shapely.geometry import LineString
from django.contrib.gis.geos import Point, LineString 
from .models import CsvData, Route, Location

# ------------------------------------------TASK_2--------------------------------------------------

# CSV file to Update data into PostgreSQL 
class Csv_to_Database(APIView):
    def post(self, request, *args, **kwargs):
        file = request.FILES.get('file')
        if not file:
            return Response({'error': 'No file uploaded.'}, status=400)
        
        decoded_file = file.read().decode('utf-8').splitlines()
        reader = csv.DictReader(decoded_file)
        csv_data_list = []
        coordinates = []

        for row in reader:
            original_time = row.get('Time')
            try:
                parsed_time = datetime.datetime.strptime(original_time, '%I:%M:%S %p').time()
            except ValueError:
                return Response({'error': f'Invalid time format: {original_time}'}, status=400)

            try:
                speed_kts = float(row.get('SpeedKts', '0'))
            except ValueError:
                speed_kts = 0.0

            try:
                speed_mph = float(row.get('SpeedMph', '0'))
            except ValueError:
                speed_mph = 0.0

            try:
                altitude_feet = float(row.get('AltitudeFeet', '0'))
            except ValueError:
                altitude_feet = 0.0

            try:
                latitude = float(row.get('Latitude', '0'))
                longitude = float(row.get('Longitude', '0'))
            except ValueError:
                latitude = longitude = 0.0

            coordinates.append((longitude, latitude))

            csv_data_list.append(CsvData(
                time=parsed_time,
                latitude=latitude,
                longitude=longitude,
                course=row.get('Course', ''),
                speed_kts=speed_kts,
                speed_mph=speed_mph,
                altitude_feet=altitude_feet,
                reporting_facility=row.get('Reporting Facility', '').strip()
            ))

        CsvData.objects.bulk_create(csv_data_list)

        return Response({'status': 'CSV data successfully uploaded.'})


# ------------------------------------------TASK_3-------------------------------------------

# Convert CSV into JSON file sort based on TIme
class CSV_to_Json(APIView):
    def post(self, request, *args, **kwargs):
        file = request.FILES.get('file')
        if not file:
            return Response({'error': 'No file uploaded.'}, status=400)

        decoded_file = file.read().decode('utf-8').splitlines()
        reader = csv.DictReader(decoded_file)
        csv_data_list = []

        for row in reader:
            original_time = row.get('Time')
            try:
                parsed_time = datetime.datetime.strptime(original_time, '%I:%M:%S %p').time()
            except ValueError:
                return Response({'error': f'Invalid time format: {original_time}'}, status=400)

            try:
                speed_kts = float(row.get('SpeedKts', '0'))
                speed_mph = float(row.get('SpeedMph', '0'))
                altitude_feet = float(row.get('AltitudeFeet', '0'))
                latitude = float(row.get('Latitude', '0'))
                longitude = float(row.get('Longitude', '0'))
            except ValueError:
                speed_kts = speed_mph = altitude_feet = latitude = longitude = 0.0

            csv_data_list.append({
                'time': parsed_time.isoformat(),
                'latitude': latitude,
                'longitude': longitude,
                'course': row.get('Course', ''),
                'speed_kts': speed_kts,
                'speed_mph': speed_mph,
                'altitude_feet': altitude_feet,
                'reporting_facility': row.get('Reporting Facility', '').strip(),
            })

        sorted_data = sorted(csv_data_list, key=lambda x: x['time'])
        json_data = json.dumps(sorted_data, indent=4)

        response = HttpResponse(json_data, content_type='application/json')
        response['Content-Disposition'] = 'attachment; filename=sorted_data.json'
        return response


# ------------------------------------------TASK_4-----------------------------------------------

#Convert CSV into GeoJSON sort based on TIme
class CSV_to_GeoJson(APIView):
    def post(self, request, *args, **kwargs):
        file = request.FILES.get('file')
        if not file:
            return Response({'error': 'No file uploaded.'}, status=400)

        decoded_file = file.read().decode('utf-8').splitlines()
        reader = csv.DictReader(decoded_file)
        coordinates = []

        for row in reader:
            try:
                latitude = float(row.get('Latitude', '0'))
                longitude = float(row.get('Longitude', '0'))
            except ValueError:
                latitude = longitude = 0.0

            coordinates.append((longitude, latitude))

        geojson_data = geojson.Feature(
            geometry=geojson.LineString(list(coordinates)),
            properties={}
        )

        response = HttpResponse(geojson.dumps(geojson_data, indent=4), content_type='application/json')
        response['Content-Disposition'] = 'attachment; filename=sorted_data.geojson'
        return response


# ------------------------------------------TASK_5------------------------------------------------

#Based on altitude column and Transform the coordinates of the aircraft into image-pixel coordinates and download as GeoJSON
class CSV_to_TransformedGeoJson(APIView):
    def post(self, request, *args, **kwargs):
        file = request.FILES.get('file')
        if not file:
            return Response({'error': 'No file uploaded.'}, status=400)

        decoded_file = file.read().decode('utf-8').splitlines()
        reader = csv.DictReader(decoded_file)
        coordinates = []

        for row in reader:
            try:
                latitude = float(row.get('Latitude', '0'))
                longitude = float(row.get('Longitude', '0'))
            except ValueError:
                latitude = longitude = 0.0

            coordinates.append((longitude, latitude))

        pixel_coordinates = self.transform_coordinates_to_pixels(coordinates)

        geojson_data = geojson.Feature(
            geometry=geojson.LineString(list(pixel_coordinates)),
            properties={}
        )

        response = HttpResponse(geojson.dumps(geojson_data, indent=4), content_type='application/json')
        response['Content-Disposition'] = 'attachment; filename=sorted_transformed_data.geojson'
        return response

    def transform_coordinates_to_pixels(self, coordinates):
        pixel_coordinates = []
        for lon, lat in coordinates:
            x = (lon + 180) * (256 / 360)  
            y = (lat + 90) * (256 / 180) 
            pixel_coordinates.append((x, y))
        return pixel_coordinates



# ------------------------------------------TASK_6--------------------------------------------------------

# Upload tiff file to draw a tracjectory line using coordinate
class TIFF_DrawTrajectory(APIView):
    def post(self, request, *args, **kwargs):
        tiff_file = request.FILES.get('tifffile')
        csv_file = request.FILES.get('csvfile')

        if not tiff_file or not csv_file:
            return Response({'error': 'Both GeoTIFF and CSV files are required.'}, status=status.HTTP_400_BAD_REQUEST)

        tiff_path = default_storage.save('tmp/world.tif', tiff_file)
        csv_path = default_storage.save('tmp/flight_data.csv', csv_file)
        
        try:
            with rasterio.open(tiff_path) as src:
                image_array = src.read()
                img = Image.fromarray(image_array.transpose(1, 2, 0))
            
            flight_points = []
            with default_storage.open(csv_path, 'r') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    try:
                        lat = float(row['Latitude'])
                        lon = float(row['Longitude'])

                        row, col = src.index(lon, lat)
                        flight_points.append((col, row))
                    except ValueError as e:
                        return Response({'error': f'Invalid data in CSV file: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)
                    except KeyError as e:
                        return Response({'error': f'Missing required column in CSV: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)
            
            draw = ImageDraw.Draw(img)
            draw.line(flight_points, fill='yellow', width=2)
            
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            buffer.seek(0)

            response = FileResponse(buffer, as_attachment=False, content_type='image/png')
            response['Content-Disposition'] = 'inline; filename="trajectory.png"'
            return response

        except rasterio.errors.RasterioError as e:
            return Response({'error': f'Error processing GeoTIFF file: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': f'An unexpected error occurred: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



# ------------------------------------------TASK_7---------------------------------------------------------------


# Convert lat,long as PSQL gemetry point
class Latlong_PSQLPoint(APIView):
    def get(self, request, *args, **kwargs):
        return render(request, 'upload.html')

    def post(self, request, *args, **kwargs):
        if 'file' not in request.FILES:
            return Response({'error': 'No file uploaded'}, status=400)

        file = request.FILES['file']
        file_content = file.read().decode('utf-8')
        csv_reader = csv.DictReader(io.StringIO(file_content))

        for row in csv_reader:
            try:
                latitude = float(row['Latitude'])
                longitude = float(row['Longitude'])
                point = Point(longitude, latitude)  
                Location.objects.create(point=point)
                
            except ValueError as e:
                return Response({'error': f'Invalid data in file: {str(e)}'}, status=400)
            except KeyError as e:
                return Response({'error': f'Missing required column in file: {str(e)}'}, status=400)

        return Response({'status': 'PostgreSQL Geometry View Point created successfully'}, status=201)



# ------------------------------------------TASK_8------------------------------------------



# Convert lat,long to linestring
class Creating_linestring(APIView):
    def post(self, request, *args, **kwargs):
        file = request.FILES.get('file')
        if not file:
            return Response({'error': 'No file uploaded'}, status=400)

        file_content = file.read().decode('utf-8')
        csv_reader = csv.DictReader(io.StringIO(file_content))

        points = []
        for row in csv_reader:
            try:
                latitude = float(row['Latitude'])
                longitude = float(row['Longitude'])
                points.append((longitude, latitude))
            except ValueError as e:
                return Response({'error': f'Invalid data in file: {str(e)}'}, status=400)
            except KeyError as e:
                return Response({'error': f'Missing required column: {str(e)}'}, status=400)

        if points:
            line_string = LineString(points)
            route_name = request.data.get('name', 'Unnamed Route')
            Route.objects.create(name=route_name, path=line_string)

            return Response({'status': 'LineString created successfully'}, status=201)
        else:
            return Response({'error': 'No valid data found in the file'}, status=400)



# HTML Rendering
from django.shortcuts import render
def upload_csv_form(request):
    return render(request, 'file_upload.html')
