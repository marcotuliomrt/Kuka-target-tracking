#include <Servo.h>

#define shotpin 2

Servo myservo;  // create servo object to control a servo

void setup() {
  Serial.begin(9600);  // initialize serial communication at 9600 bits per second
  myservo.attach(10);  // attaches the servo on pin 9 to the servo object
  pinMode(shotpin, OUTPUT);    // sets the digital pin 13 as output

  //start positions
  digitalWrite(shotpin, LOW);  // sets the digital pin 13 off
  myservo.write(8);  // set the servo to 60 degrees
}

void loop() {
  if (Serial.available()) {  // check if there is incoming serial data
    char x = Serial.read();  // read the incoming character
    if (x == 'a') {  // if the character is 'a'
      digitalWrite(shotpin, LOW);  // sets the digital pin 13 off    
      myservo.write(8);  // set the servo to 0 degrees
      delay(300);            // waits for a second
      myservo.write(45);  // set the servo to 60 degrees
      delay(300);            // waits for a second
      myservo.write(8);  // set the servo to 60 degrees
      delay(300);            // waits for a second
      
    }
    else if (x == 'b'){
      digitalWrite(shotpin, HIGH); // sets the digital pin 13 on
      delay(10);            // waits for a second
      digitalWrite(shotpin, LOW);  // sets the digital pin 13 off   
    }
    else if (x == 'c'){
      myservo.write(8);  // set the servo to 0 degrees
      delay(500);            // waits for a second 
    }
    else if (x == 'd'){
      myservo.write(45);  // set the servo to 0 degrees
      delay(500);            // waits for a second
    }
  
  }
}
