/*
  ForestWatch AI — ESP32 -> hosted Flask dashboard example

  This is the Wi-Fi/HTTP upload helper only. It does NOT perform audio
  classification by itself. Call sendForestWatchAlert() after your deployed
  Edge Impulse audio model returns a prediction.

  Arduino IDE libraries: ArduinoJson is not required for this simple example.
  Board: ESP32 Dev Module
*/
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>

const char* WIFI_SSID = "YOUR_WIFI_NAME";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";
// Use the HTTPS URL provided by Render, without a trailing slash.
const char* SERVER_BASE_URL = "https://YOUR-SERVICE.onrender.com";
// Set the same value as DEVICE_API_KEY in your Render environment settings.
const char* DEVICE_API_KEY = "REPLACE_WITH_YOUR_LONG_RANDOM_KEY";
const char* NODE_NAME = "FORESTWATCH-NODE-01";

void connectForestWatchWiFi() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("Connecting to Wi-Fi");
  unsigned long started = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - started < 20000) {
    delay(500);
    Serial.print('.');
  }
  Serial.println();
  if (WiFi.status() == WL_CONNECTED) {
    Serial.print("Wi-Fi connected. IP: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("Wi-Fi connection timed out.");
  }
}

// confidence may be 0.0–1.0 (e.g. 0.94). Use NaN for unavailable GPS.
bool sendForestWatchAlert(const String& label, float confidence,
                          double latitude, double longitude) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("Not connected to Wi-Fi; alert not sent.");
    return false;
  }

  // Prototype convenience only. For a production deployment, validate the
  // server TLS certificate instead of disabling certificate verification.
  WiFiClientSecure client;
  client.setInsecure();
  HTTPClient http;
  const String url = String(SERVER_BASE_URL) + "/device/alert";
  if (!http.begin(client, url)) {
    Serial.println("Could not start HTTPS request.");
    return false;
  }

  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-API-Key", DEVICE_API_KEY);

  String body = "{\"node\":\"" + String(NODE_NAME) +
                "\",\"threat\":\"" + label +
                "\",\"label\":\"" + label +
                "\",\"confidence\":" + String(confidence, 4) +
                ",\"source\":\"esp32-audio\"";
  if (isfinite(latitude) && isfinite(longitude) &&
      latitude >= -90 && latitude <= 90 &&
      longitude >= -180 && longitude <= 180) {
    body += ",\"lat\":" + String(latitude, 6) +
            ",\"lng\":" + String(longitude, 6);
  } else {
    body += ",\"lat\":null,\"lng\":null";
  }
  body += "}";

  int status = http.POST(body);
  String response = http.getString();
  http.end();
  Serial.printf("ForestWatch upload HTTP status: %d\n", status);
  Serial.println(response);
  return status >= 200 && status < 300;
}

void setup() {
  Serial.begin(115200);
  connectForestWatchWiFi();
  Serial.println("ForestWatch Wi-Fi uploader ready.");
  Serial.println("Next: call sendForestWatchAlert(label, confidence, lat, lng)");
  Serial.println("only after your Edge Impulse audio model produces a prediction.");
}

void loop() {
  // Do not generate fake detections here. Integrate the call into your actual
  // audio-classification loop once the Edge Impulse Arduino library is ready.
  delay(1000);
}
