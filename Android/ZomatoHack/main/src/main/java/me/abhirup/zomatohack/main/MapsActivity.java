package me.abhirup.zomatohack.main;

import android.Manifest;
import android.content.Context;
import android.content.pm.PackageManager;
import android.location.Location;
import android.location.LocationListener;
import android.location.LocationManager;
import android.os.AsyncTask;
import android.os.Bundle;
import android.support.v4.app.FragmentActivity;
import android.util.Log;
import android.widget.Toast;

import com.google.android.gms.maps.CameraUpdateFactory;
import com.google.android.gms.maps.GoogleMap;
import com.google.android.gms.maps.OnMapReadyCallback;
import com.google.android.gms.maps.SupportMapFragment;
import com.google.android.gms.maps.model.LatLng;
import com.google.android.gms.maps.model.Marker;
import com.google.android.gms.maps.model.MarkerOptions;
import com.google.android.gms.maps.model.TileOverlay;
import com.google.android.gms.maps.model.TileOverlayOptions;
import com.google.maps.android.heatmaps.HeatmapTileProvider;
import com.google.maps.android.heatmaps.WeightedLatLng;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.ArrayList;
import java.util.List;

public class MapsActivity extends FragmentActivity implements OnMapReadyCallback, LocationListener {
    private static final String TAG = "Heatmap";
    private static final int LOCATION_PERMISSION = 101;
    private GoogleMap map;
    private Marker marker;
    private TileOverlay overlay;
    private LocationManager locationManager;
    private boolean resumed;
    private boolean updateInFlight;
    private boolean heatmapInFlight;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_maps);
        locationManager = (LocationManager) getSystemService(Context.LOCATION_SERVICE);
        SupportMapFragment fragment = (SupportMapFragment) getSupportFragmentManager().findFragmentById(R.id.map);
        if (fragment == null) throw new IllegalStateException("The map fragment is missing.");
        fragment.getMapAsync(this);
    }

    @Override
    protected void onResume() {
        super.onResume();
        resumed = true;
        if (map != null) refreshHeatmap();
        startLocationUpdates();
    }

    @Override
    protected void onPause() {
        resumed = false;
        if (locationManager != null) locationManager.removeUpdates(this);
        super.onPause();
    }

    @Override
    public void onMapReady(GoogleMap googleMap) {
        map = googleMap;
        LatLng centre = new LatLng(12.9279, 77.6271);
        marker = map.addMarker(new MarkerOptions().position(centre).title("Demo starting position"));
        map.moveCamera(CameraUpdateFactory.newLatLngZoom(centre, 12));
        refreshHeatmap();
        startLocationUpdates();
    }

    private void startLocationUpdates() {
        if (!resumed || map == null) return;
        if (checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) != PackageManager.PERMISSION_GRANTED
                && checkSelfPermission(Manifest.permission.ACCESS_COARSE_LOCATION) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[]{Manifest.permission.ACCESS_FINE_LOCATION, Manifest.permission.ACCESS_COARSE_LOCATION}, LOCATION_PERMISSION);
            return;
        }
        if (locationManager == null || !locationManager.isProviderEnabled(LocationManager.NETWORK_PROVIDER)) {
            showError("Enable the network location provider to update your position.", null);
            return;
        }
        locationManager.requestLocationUpdates(LocationManager.NETWORK_PROVIDER, 60000, 10, this);
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] results) {
        super.onRequestPermissionsResult(requestCode, permissions, results);
        if (requestCode != LOCATION_PERMISSION) return;
        for (int result : results) {
            if (result == PackageManager.PERMISSION_GRANTED) {
                startLocationUpdates();
                return;
            }
        }
        showError("Location access was denied. The demo heatmap remains available.", null);
    }

    @Override
    public void onLocationChanged(Location location) {
        if (!resumed || map == null || updateInFlight) return;
        LatLng position = new LatLng(location.getLatitude(), location.getLongitude());
        if (marker != null) marker.remove();
        marker = map.addMarker(new MarkerOptions().position(position).title("Current location"));
        updateInFlight = true;
        new UpdateLocationTask().execute(position);
    }

    @Override public void onStatusChanged(String provider, int status, Bundle extras) {}
    @Override public void onProviderEnabled(String provider) { startLocationUpdates(); }
    @Override public void onProviderDisabled(String provider) { showError("The location provider was disabled.", null); }

    private void refreshHeatmap() {
        if (map != null && !heatmapInFlight) {
            heatmapInFlight = true;
            new GetHeatMapTask().execute();
        }
    }

    private void showHeatmap(JSONObject payload) throws JSONException {
        JSONArray zones = payload.getJSONArray("zones");
        if (zones.length() == 0) throw new JSONException("The heatmap contains no zones.");
        List<WeightedLatLng> points = new ArrayList<>();
        for (int index = 0; index < zones.length(); index++) {
            JSONObject zone = zones.getJSONObject(index);
            double score = zone.getDouble("score");
            if (Double.isNaN(score) || Double.isInfinite(score) || score < 0) {
                throw new JSONException("The heatmap contains an invalid score.");
            }
            points.add(new WeightedLatLng(new LatLng(zone.getDouble("latitude"), zone.getDouble("longitude")), score));
        }
        HeatmapTileProvider provider = new HeatmapTileProvider.Builder().weightedData(points).build();
        provider.setOpacity(0.75);
        provider.setRadius(100);
        if (overlay != null) overlay.remove();
        overlay = map.addTileOverlay(new TileOverlayOptions().tileProvider(provider));
    }

    private JSONObject request(String path, JSONObject body) throws IOException, JSONException {
        HttpURLConnection connection = (HttpURLConnection) new URL(BuildConfig.API_BASE_URL + path).openConnection();
        connection.setConnectTimeout(5000);
        connection.setReadTimeout(5000);
        try {
            if (body != null) {
                connection.setRequestMethod("POST");
                connection.setDoOutput(true);
                connection.setRequestProperty("Content-Type", "application/json; charset=utf-8");
                try (OutputStream stream = connection.getOutputStream()) {
                    stream.write(body.toString().getBytes("UTF-8"));
                }
            }
            int code = connection.getResponseCode();
            if (code < 200 || code >= 300) throw new IOException("The demo API returned HTTP " + code + ".");
            try (InputStream stream = connection.getInputStream();
                 ByteArrayOutputStream output = new ByteArrayOutputStream()) {
                byte[] buffer = new byte[1024];
                int count;
                while ((count = stream.read(buffer)) != -1) output.write(buffer, 0, count);
                return new JSONObject(output.toString("UTF-8"));
            }
        } finally {
            connection.disconnect();
        }
    }

    private void showError(String message, Exception error) {
        Log.e(TAG, message, error);
        if (resumed) Toast.makeText(this, message, Toast.LENGTH_LONG).show();
    }

    private class GetHeatMapTask extends AsyncTask<Void, Void, JSONObject> {
        private Exception failure;

        @Override protected JSONObject doInBackground(Void... unused) {
            try {
                return request("/heatmap/get_heatmap", null);
            } catch (IOException | JSONException error) {
                failure = error;
                return null;
            }
        }

        @Override protected void onPostExecute(JSONObject result) {
            heatmapInFlight = false;
            if (failure != null) {
                showError("The heatmap could not be loaded.", failure);
            } else if (resumed && map != null) {
                try {
                    showHeatmap(result);
                } catch (JSONException | IllegalArgumentException error) {
                    showError("The heatmap response was invalid.", error);
                }
            }
        }
    }

    private class UpdateLocationTask extends AsyncTask<LatLng, Void, JSONObject> {
        private Exception failure;

        @Override protected JSONObject doInBackground(LatLng... positions) {
            try {
                JSONObject body = new JSONObject().put("id", 2)
                        .put("latitude", positions[0].latitude).put("longitude", positions[0].longitude);
                return request("/heatmap/update_location", body);
            } catch (IOException | JSONException error) {
                failure = error;
                return null;
            }
        }

        @Override protected void onPostExecute(JSONObject result) {
            updateInFlight = false;
            if (failure != null) showError("The location could not be updated.", failure);
            else if (resumed) refreshHeatmap();
        }
    }
}
