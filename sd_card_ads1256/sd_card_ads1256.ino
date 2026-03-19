// This code belongs to the ADS1256 library developed by Curious Scientist
// A very detailed documentation can be found at:
// https://curiousscientist.tech/ads1256-custom-library

#include <ADS1256.h>
#include "FS.h"
#include "SD.h"
#include "SPI.h"

// #define ADS1256_SPI_ALREADY_STARTED  //prevent internal _spi->begin() to
// allow custom SPI initialization

// Platform-specific pin definitions
#if defined(ARDUINO_ARCH_RP2040)
#pragma message "Using RP2040"
// #define USE_SPI1 //Alternative USE_SPI for RP2040 - Uncomment to use SPI1
#if defined(USE_SPI1)
#pragma message "Using SPI1 (SPI1)"
#define SPI_MOSI 11
#define SPI_MISO 12
#define SPI_SCK 10
#define USE_SPI SPI1
#else
#pragma message "Using SPI (SPI0)"
#define SPI_MOSI 3 // 19
#define SPI_MISO 4 // 16
#define SPI_SCK 2  // 18
#define USE_SPI SPI
#endif
//-----------------------------------------

#elif defined(ARDUINO_ARCH_STM32)
#pragma message "Using STM32"
// #define USE_SPI2  //Uncomment to use SPI2
#if defined(USE_SPI2)
#pragma message "Using SPI2"
#define USE_SPI spi2
SPIClass spi2(PB15, PB14, PB13); // MOSI, MISO, SCK
#else
#pragma message "Using SPI (SPI1)"
#define USE_SPI SPI // Default SPI1, pre-instantiated as 'SPI' on PA7, PA6, PA5
#endif
                                 //-----------------------------------------
#elif defined(TEENSYDUINO)
#pragma message "Using Teensy"
// #define USE_SPI1 //Uncomment to use SPI1 on Teensy 4.0 or 4.1
// #define USE_SPI2 //Uncomment to use SPI2 on Teensy 4.0 or 4.1
#if defined(USE_SPI2)
#pragma message "Using SPI2 (SPI3)"
#define USE_SPI SPI2
#elif defined(USE_SPI1)
#pragma message "Using SPI1 (SPI2)"
#define USE_SPI SPI1
#else
#pragma message "Using SPI (SPI1)"
#define USE_SPI SPI
#endif
//-----------------------------------------

#elif defined(ARDUINO_ARCH_ESP32)
#pragma message "Using ESP32"
SPIClass hspi(HSPI);
#define USE_HSPI // Uncomment to use HSPI instead of VSPI
#if defined(USE_HSPI)
#pragma message "Using HSPI"
#define USE_SPI hspi
#else
#pragma message "Using VSPI"
#define USE_SPI SPI
#endif
//-----------------------------------------
#else // Default fallback (Arduino AVR)
#define SPI_MOSI MOSI
#define SPI_MISO MISO
#define SPI_SCK SCK
#define USE_SPI SPI
//-----------------------------------------
#endif

// Below a few examples of pin descriptions for different microcontrollers I
// used: ADS1256 A(2, ADS1256::PIN_UNUSED, 8, 10, 2.500, &USE_SPI); //DRDY,
// RESET, SYNC(PDWN), CS, VREF(float).    //Arduino Nano/Uno - OK ADS1256 A(7,
// ADS1256::PIN_UNUSED, 10, 9, 2.500, &USE_SPI); //DRDY, RESET, SYNC(PDWN), CS,
// VREF(float).      //ATmega32U4 -OK
ADS1256 A(4, 17, ADS1256::PIN_UNUSED, 16, 2.500,
          &USE_SPI); // DRDY, RESET, SYNC(PDWN), CS, VREF(float).   //ESP32
                     // WROOM 32 - OK (HSPI+VSPI)
// ADS1256 A(7, ADS1256::PIN_UNUSED, 8, 10, 2.500, &USE_SPI); //DRDY, RESET,
// SYNC(PDWN), CS, VREF(float).    //Teensy 4.0 - OK ADS1256 A(7,
// ADS1256::PIN_UNUSED, 6, 5, 2.500, &USE_SPI); //DRDY, RESET, SYNC(PDWN), CS,
// VREF(float).    //RP2040 Waveshare Mini - OK ADS1256 A(18, 20, 21, 19, 2.500,
// &USE_SPI); //DRDY, RESET, SYNC(PDWN), CS, VREF(float), SPI bus.  //RP2040
// Zero - OK
//  ADS1256 A(15, ADS1256::PIN_UNUSED, 14, 17, 2.500, &USE_SPI);  //DRDY, RESET,
//  SYNC(PDWN), CS, VREF(float), SPI bus.  //RP2040 Pico W - OK
// ADS1256 A(PA2, ADS1256::PIN_UNUSED, ADS1256::PIN_UNUSED, PA4, 2.500,
// &USE_SPI); //DRDY, RESET, SYNC(PDWN), CS, VREF(float). //STM32 "blue pill" -
// SPI1 - OK ADS1256 A(PB10, PB11, ADS1256::PIN_UNUSED, PB12, 2.500, &USE_SPI);
// // DRDY, RESET, SYNC, CS, VREF, SPI //STM32 "blue pill" - SPI2 - OK

long rawConversion = 0; // 24-bit raw value
float voltageValue = 0; // human-readable floating point value

int singleEndedChannels[8] = {
    SING_0, SING_1, SING_2, SING_3,
    SING_4, SING_5, SING_6, SING_7}; // Array to store the single-ended channels
int differentialChannels[4] = {
    DIFF_0_1, DIFF_2_3, DIFF_4_5,
    DIFF_6_7}; // Array to store the differential channels
int inputChannel =
    0; // Number used to pick the channel from the above two arrays
char inputMode = ' '; // can be 's' and 'd': single-ended and differential

int pgaValues[7] = {PGA_1,  PGA_2,  PGA_4, PGA_8,
                    PGA_16, PGA_32, PGA_64}; // Array to store the PGA settings
int pgaSelection = 0; // Number used to pick the PGA value from the above array

int drateValues[16] = {
    DRATE_30000SPS, DRATE_15000SPS, DRATE_7500SPS, DRATE_3750SPS, DRATE_2000SPS,
    DRATE_1000SPS,  DRATE_500SPS,   DRATE_100SPS,  DRATE_60SPS,   DRATE_50SPS,
    DRATE_30SPS,    DRATE_25SPS,    DRATE_15SPS,   DRATE_10SPS,   DRATE_5SPS,
    DRATE_2SPS}; // Array to store the sampling rates

int drateSelection =
    0; // Number used to pick the sampling rate from the above array

String registers[11] = {
    "STATUS", "MUX",  "ADCON", "DRATE", "IO",  "OFC0",
    "OFC1",   "OFC2", "FSC0",  "FSC1",  "FSC2"}; // Array to store the registers

int registerToRead = 0;       // Register number to be read
int registerToWrite = 0;      // Register number to be written
int registerValueToWrite = 0; // Value to be written in the selected register

String readFile(fs::FS &fs, const char * path) {
  Serial.printf("Reading file: %s\n", path);

  File file = fs.open(path);
  if (!file || file.isDirectory()) {
    Serial.println("- failed to open file for reading");
    return ""; // Return a default value
  }

  String content = file.readString();
  file.close();

  Serial.println("Read value: "+content);
  return content;
}

void writeFile(fs::FS &fs, const char * path, const char * message){
  Serial.printf("Writing file: %s\n", path);

  File file = fs.open(path, FILE_WRITE);
  if(!file){
    Serial.println("Failed to open file for writing");
    return;
  }
  if(file.print(message)){
    Serial.println("File written");
  } else {
    Serial.println("Write failed");
  }
  file.close();
}

void setup() {
  Serial.setRxBufferSize(4096);
  Serial.setTxBufferSize(4096);
  Serial.begin(
      2000000); // The value does not matter if you use an MCU with native USB
  if(!SD.begin(5)){
    Serial.println("Card Mount Failed");
    return;
  }
  while (!Serial) {
    ; // Wait until the serial becomes available
  }

  Serial.println(
      "ADS1256 - Custom Library Demo File by Curious Scientist - 2025-05-28");

#if defined(ARDUINO_ARCH_RP2040) // If RP2040 is used, we need to pass the SPI
                                 // pins
  SPI.setSCK(SPI_SCK);
  SPI.setTX(SPI_MOSI);
  SPI.setRX(SPI_MISO);
#endif

#if defined(USE_HSPI)    // If ESP32 is used, we need to start SPI with a
                         // non-strapping MISO pin
  hspi.begin(33, 34, 2); // SCK, MISO (safe), MOSI
#endif

  A.InitializeADC(); // See the documentation for every details
  // Setting up CS, RESET, SYNC and SPI
  // Assigning default values to: STATUS, MUX, ADCON, DRATE
  // Performing a SYSCAL

  // Below is a demonstration to change the values through the built-on
  // functions of the library Set a PGA value
  A.setPGA(PGA_4); // 0b00000000 - DEC: 0
  //--------------------------------------------

  // Set input channels
  A.setMUX(DIFF_6_7); // 0b01100111 - DEC: 103
  //--------------------------------------------

  // Set DRATE
  A.setDRATE(DRATE_30000SPS); // 0b00010011 - DEC: 19
  //--------------------------------------------

  // Read back the above 3 values to check if the writing was succesful
  Serial.print("PGA: ");
  Serial.println(A.getPGA());
  delay(100);
  //--
  Serial.print("MUX: ");
  Serial.println(A.readRegister(MUX_REG));
  delay(100);
  //--
  Serial.print("DRATE: ");
  Serial.println(A.readRegister(DRATE_REG));
  delay(100);

  // Freeze the display for 3 sec
  delay(3000);
  String currentCount = readFile(SD, "/counter.txt");
        int currentCountInt = currentCount.toInt();
        currentCountInt += 1;
        writeFile(SD, "/counter.txt", String(currentCountInt).c_str());

        String fileName = "/" + String(currentCountInt) + ".bin";
        Serial.printf("Starting 25s log to: %s\n", fileName.c_str());

        File dataFile = SD.open(fileName.c_str(), FILE_WRITE);
        if (!dataFile) {
            Serial.println("SD Error: Could not open file.");
        }

        unsigned long startTime = millis();
        unsigned long duration = 25000; // 25 seconds in milliseconds

        while (millis() - startTime < duration) {
            float timeAndchannels[5];
            timeAndchannels[0] = millis();
            for (int j = 1; j < 5; j++) {
                timeAndchannels[j] = A.convertToVoltage(A.cycleDifferential());
            }

            dataFile.write((uint8_t*)timeAndchannels, sizeof(timeAndchannels));
        }

        dataFile.close();
        A.stopConversion();
        
        Serial.println("\nLogging Complete.");
        Serial.printf("File saved as: %s\n", fileName.c_str());
}

void loop() {
    
}