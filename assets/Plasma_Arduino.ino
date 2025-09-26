#define LIGHTER_PIN 7    // Plasma lighter relay (active-low)


bool lighterActive = false;
unsigned long lighterStartTime = 0;
const unsigned long LIGHTER_DURATION = 3500;  // XXX-milisecond pulse for lighter

void setup() {
  Serial.begin(9600);  // Start serial communication
  pinMode(LIGHTER_PIN, OUTPUT);
  digitalWrite(LIGHTER_PIN, HIGH);  // Start with lighter off (active-low)
  
  Serial.println("System ready. L1 for lighter pulse. Box close triggers lighter.");
}

void loop() {
  unsigned long currentTime = millis();

  // Check for serial commands
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    command.trim();
    
    // Lighter manual pulse trigger (active-low)
     if (command == "L1" && !lighterActive) {
      digitalWrite(LIGHTER_PIN, LOW);  // Activate lighter
      lighterActive = true;
      lighterStartTime = currentTime;
      Serial.println("Lighter ON (3.5s pulse)");
    }
  }

  // Lighter auto-off after Xs (active-low)
  if (lighterActive && (currentTime - lighterStartTime >= LIGHTER_DURATION)) {
    digitalWrite(LIGHTER_PIN, HIGH);  // Deactivate lighter
    lighterActive = false;
    Serial.println("Lighter OFF");
  }

  delay(50);  // Debounce
}