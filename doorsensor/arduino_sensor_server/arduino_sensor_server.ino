/* HC-SR04 distance sensor and server.
 *
 * Pin configuration:
 *  HC-SR04:
 *    VCC  => Arduino 5v
 *    GND  => Arduino GND
 *    Echo => Arduino pin 6
 *    Trig => Arduino pin 5
 *
 *  LED indicators:
 *    Out of range positive     => Arduino pin 8 + ~300 ohm resistor
 *    In range positive         => Arduino pin 9 + ~300 ohm resistor
 *    Client connected positive => Arduino pin 3 + ~300 ohm resistor
 *    All negative              => Arduino GND
 *
 * Distance calculation from: http://goo.gl/kJ8Gl
 */

#include <SPI.h>
#include <Ethernet.h>

// Pin configuration.
#define ECHO_PIN 6
#define TRIGGER_PIN 5
#define MAX_RANGE_LED_PIN 8
#define IN_RANGE_LED_PIN 9
#define DATA_RECEIVED_PIN 3

// 1/(speed of sound), where (speed of sound) = 333.1 * .6 * (air temp in C)
#define PACE_OF_SOUND 29.1  // microseconds per centimeter

byte MAC[] = { 
    0xCA, 0xFE, 0xBA, 0xBE, 0xF0, 0x0D };
//IPAddress IP(192,168,1,47);
EthernetServer SERVER(80);


void setup() {
  Serial.begin(9600);

  // Setup pins.
  pinMode(TRIGGER_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  pinMode(MAX_RANGE_LED_PIN, OUTPUT);
  pinMode(IN_RANGE_LED_PIN, OUTPUT);

  // Start the server (using DHCP; ensure dd-wrt has a static lease assigned).
  Ethernet.begin(MAC);
  SERVER.begin();
  Serial.print("Server started at ");
  Serial.println(Ethernet.localIP());
}


long getDistance() {
  long duration;
  // TODO: check if this is needed
  digitalWrite(TRIGGER_PIN, LOW);
  delayMicroseconds(2);

  // Toggle the trigger.
  digitalWrite(TRIGGER_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIGGER_PIN, LOW);

  // Check the echo time.
  duration = pulseIn(ECHO_PIN, HIGH);

  // Calculate the distance.
  return (duration / 2.0) / PACE_OF_SOUND;
}


void serveClient(EthernetClient &client, long distance) {
  Serial.println("writing response");
  client.println("HTTP/1.0 200 OK");
  client.println("Content-Type: text/plain");
  client.println("Refresh: 1");
  client.println();
  client.print(distance);
  Serial.println("response sent, sleeping 200ms");
  delay(200);
}


bool readClient(EthernetClient &client) {
  // Empty the request buffer, looking for a blank line
  Serial.println("Reading from client...");
  bool isNewline = false ;
  while (client.connected()) {
    int bytesAvailable = client.available();
    if (!bytesAvailable) {
      Serial.println("Read buffer emptied.");
      continue;
    }
    
    char c = client.read();
    Serial.print(c);
    if (isNewline && c == '\n') {
      Serial.println("Found blank line, client must be ready!");
      return true;
    }
    isNewline = (c == '\n' || (isNewline && c == '\r'));
  }

  Serial.println("Client disconnected.");
  return false;
}


void maybeAnswerHTTPRequest(long distance) {
  EthernetClient client = SERVER.available();
  if (client) {
    Serial.println("Client connected");
    digitalWrite(DATA_RECEIVED_PIN, HIGH);
    if (readClient(client)) {
      Serial.println("Request received");
      serveClient(client, distance);
    }
    Serial.println("closing connection");
    client.stop();
    digitalWrite(DATA_RECEIVED_PIN, LOW);
  }
}


void toggleLights(long distance) {
  if (distance < 10) {
    digitalWrite(MAX_RANGE_LED_PIN, HIGH);
    digitalWrite(IN_RANGE_LED_PIN, LOW);
  } else {
    digitalWrite(MAX_RANGE_LED_PIN, LOW);
    digitalWrite(IN_RANGE_LED_PIN, HIGH);
  }
  Serial.print(distance);
  Serial.println(" cm");
}


void loop() {
  long distance = getDistance();

  toggleLights(distance);
  maybeAnswerHTTPRequest(distance);

  delay(200);
}

/* vim: set filetype=cpp et ts=2 sw=2 : */
