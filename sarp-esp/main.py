import time
import builtins
from machine import Pin, PWM, Timer
import rp2
from serial import SerialComm
from hcsr04 import HCSR04
from imu import MPU6050
from machine import I2C, freq
import neopixel
import gc



gc.collect()

# Limit switch pins
# 10 11 12 13

# Ultasonic Sensor Pins (trig, echo)
# u1
# 14 15

# u2
# 16 17

# u3
# 18 19

# u4
# 20 21

# imu
# sda pin: 0
# scl pin: 1

# stepper r pins
# en: 2 step: 3 dir: 4 led: 8

# stepper l pins
# en: 5 step: 6 dir: 7 led: 9



class Stepper:
    def __init__(self, enable_pin, step_pin, dir_pin, led_pin, invert_dir=False, count_pin=None):
        # Initialize pins and variables
        self.en_pin = Pin(enable_pin, Pin.OUT)
        self.en_pin.value(0)
        self.step_pin = PWM(Pin(step_pin))
        self.dir_pin = Pin(dir_pin, Pin.OUT)
        self.count_pin = count_pin
        self.decelerate = False
        self.invert_dir = invert_dir
        self.dir = 1 if invert_dir else 0
        self.min_freq = 15
        self.max_freq = 4000
        self.np = neopixel.NeoPixel(Pin(led_pin), 10)
        self.led_index = -1
        self.freq = 0
        self.pos = 0
        self.direction = 0
        self.step_size = 0
        self.target_freq = 0
        self.timer = Timer()

        # Initialize the PIO state machine for step counting
#         @rp2.asm_pio()
#         def step_counter():
#             wrap_target()
#             wait(1, pin, 0)  # Wait for the pin to go high
#             wait(0, pin, 0)  # Wait for the pin to go low
#             irq(rel(0))  # Trigger an interrupt for each complete pulse
#             wrap()
# 
#         self.sm = rp2.StateMachine(step_pin, step_counter, freq=5000, in_base=Pin(step_pin))
#         self.sm.irq(self._pio_callback)
#         self.sm.active(1)
# 
#     def _pio_callback(self, sm):
#         if self.dir_pin.value() == 1:
#             self.pos += 1
#         else:
#             self.pos -= 1
#         if self.pos >= 1200 or self.pos <= -1200:
#             self.pos = 0
# #         print("wri", self.pos)

    # Method to accelerate the stepper motor to a target frequency
    def accelerate(self, target_freq):
        if target_freq < self.freq:
            self.decelerate = True
        else:
            self.decelerate = False
        freq_diff = abs(target_freq - self.freq)
        self.target_freq = target_freq
        self.step_size = 50  # Hz
        timer_period = 20  # ms
        # Start the timer
        self.timer.init(
            period=timer_period, mode=Timer.PERIODIC, callback=self._change_freq
        )

    # Callback method to change the frequency of the stepper motor
    def _change_freq(self, timer):
        if self.freq < self.target_freq and not self.decelerate:
            self.freq += self.step_size
            self.step_pin.freq(abs(self.freq))
        elif self.freq > self.target_freq and self.decelerate:
            self.freq -= self.step_size
            self.step_pin.freq(abs(self.freq))
        else:
            # Stop the timer when the target frequency is reached
            self.freq = self.target_freq
            self.step_pin.freq(abs(self.freq))
            self.timer.deinit()

    # Method to step the stepper motor at a certain frequency
    def step(self, freq):
        self.en_pin.value(0)
        self.freq = freq
        self.step_pin.freq(abs(self.freq))
        self.step_pin.duty_u16(int((30 / 100) * 65_535))

    # Method to stop the stepper motor
    def stop(self):
        self.freq = 0
        self.step_pin.duty_u16(0)
#         self.sm.active(0)
        self.en_pin.value(1)
        self.timer.deinit()

    # Callback method for step interrupt
    def _step_callback(self, pin):
        if self.dir_pin.value() == 1:
            self.pos += 1
        else:
            self.pos -= 1
        if self.pos >= 1200 or self.pos <= -1200:
            self.pos = 0

    def update_leds(self, led_index):
        # Update the LEDs
        for i in range(10):
            if i <= led_index:
                self.np[i] = (0, 30, 60)
            else:
                self.np[i] = (0, 0, 0)
        self.np.write()

    # Property for frequency
    @property
    def freq(self):
        return self._freq

    # Setter for frequency
    @freq.setter
    def freq(self, value):
        if abs(value) > self.max_freq:
            self._freq = self.max_freq
        else:
            self._freq = value

        if abs(self._freq) < self.min_freq:
            self._freq = -self.min_freq if self.decelerate else self.min_freq

        if self._freq < 0:
            self.dir_pin.value(1 - self.dir)
            self.direction = -1
        else:
            self.dir_pin.value(self.dir)
            self.direction = 1

        steps = (self.max_freq - self.min_freq) / 10

        if self._freq == 0 or ((abs(value) - self.min_freq) / steps) <= 0:
            self.update_leds(-1)  # Turn off all LEDs
            return

        led_index = round((abs(self._freq) - self.min_freq) / steps)
        if self.led_index != led_index:
            self.led_index = led_index
            self.update_leds(self.led_index)

s_r = Stepper(2, 3, 4, 8)
s_l = Stepper(5, 6, 7, 9, invert_dir=True)  # step_pin, dir_pin, steps_per_rev=600, invert_dir=False

class Heartbeat:
    def __init__(self, timeout=4000):
        from machine import WDT
        self.wdt = WDT(timeout=timeout)  # enable it with a timeout of 2s
        self.sent = False
        self._internal_timer = time.ticks_ms()
        self._timeout = timeout/2 #half of WDT timeout
        
        
    def beat(self):
        #If the time since the last beat is greater than the timeout, send a heartbeat
        if time.ticks_diff(time.ticks_ms(), self._internal_timer) > self._timeout and not self.sent:
            print('h')
            self.sent = True
            self._internal_timer = time.ticks_ms()
            
            
    
    def feed(self):
        if self.sent:
            self.wdt.feed()
            self._internal_timer = time.ticks_ms()
            self.sent = False
            print("Im Fed")
        
    def virtual_reset(self):
        if time.ticks_diff(time.ticks_ms(), self._internal_timer) > self._timeout*2 and self.sent == True:
            print("I am resetting")
            time.sleep(0.5)
            self._internal_timer = time.ticks_ms()
            self.sent = False
            
        
        
        
        

class Sensors:
    def __init__(self):
        self.types = {
            "ultrasonic": {"poll_rate": 0.1, "sensor": {}},
            "imu": {"poll_rate": 0.1, "sensor": {}},
            "bumper": {"poll_rate": 0.1, "sensor": {}},
            "adc": {"poll_rate": 0.1, "sensor": {}},
        }
        self.timers = {}

    def create_ultrasonic(self, id, trigger, echo):
        self.types["ultrasonic"]["sensor"][id] = HCSR04(trigger, echo)

    def create_imu(self, id, sda, scl):
        i2c = I2C(0, sda=Pin(sda), scl=Pin(scl), freq=400000)
        self.types["imu"]["sensor"][id] = MPU6050(i2c)

    def create_bumper(self, id, pin):
        self.types["bumper"]["sensor"][id] = Pin(pin, Pin.IN, Pin.PULL_DOWN)

    def poll_ultrasonic(self, id):
        
        print(
            (
            "u "
            + str(id)
            + " "
            + str(self.types["ultrasonic"]["sensor"][id].distance_cm())
            )
        )

    def poll_imu(self, id):
        imu = self.types["imu"]["sensor"][id]
        print(
            f"i {id} {imu.accel.x} {imu.accel.y} {imu.accel.z} {imu.gyro.x} {imu.gyro.y} {imu.gyro.z}"
        )

    def poll_bumper(self, id):
        print("b " + str(id) + " " + str(self.types["bumper"]["sensor"][id].value()))

    def start_polling(self, sensor_type, id):
        if sensor_type in self.timers:
            self.timers[sensor_type].deinit()  # stop previous timer
        self.timers[sensor_type] = Timer(-1)
        self.timers[sensor_type].init(
            freq=self.types[sensor_type]["poll_rate"],
            mode=Timer.PERIODIC,
            callback=lambda t: getattr(self, f"poll_{sensor_type}")(id),
        )

    def set_poll_rate(self, sensor_type, poll_rate):
        self.types[sensor_type]["poll_rate"] = poll_rate
    def stop_polling(self, sensor_type):
        self.timers[sensor_type].deinit()
        del self.timers[sensor_type]


#sensors = Sensors()
# sensors.create_ultrasonic(1, 22, 26)
# sensors.create_ultrasonic(2, 16, 17)
# sensors.create_ultrasonic(3, 18, 19)
# sensors.create_ultrasonic(4, 20, 21)
# sensors.create_imu(1, 0, 1)



ultrasonic_flag = False
IMU_flag = False


def IMUprint():
    global IMU_flag
    IMU_flag = True


def getdist():
    global ultrasonic_flag
    ultrasonic_flag = True


    
    

def send_sensory_data(comms):
    global ultrasonic_flag, IMU_flag
    if ultrasonic_flag:
        sensors.poll_ultrasonic(1)
        sensors.poll_ultrasonic(2)
        sensors.poll_ultrasonic(3)
        sensors.poll_ultrasonic(4)
        ultrasonic_flag = False

# def handle_emergency(stepper_l, stepper_r, sensors):
#     emergency_ultrasonic = sensors.types["ultrasonic"]["sensor"][1].distance_cm()
#     if  emergency_ultrasonic < 10.0:
#         return True

#     # Uncomment this block if IMU functionality is fully implemented
#     if IMU_flag:
#         sensors.poll_imu(1)
#         IMU_flag = False

timer_for_ultrasonic = Timer()
timer_for_imu = Timer()



def main():
    time.sleep(0.1)
    freq(80000000)
    print(freq())
    comms = None

    for i in range(3):
        try:
            comms = SerialComm()
            break
        except Exception as e:
            print(f"Failed to initialize serial port. {str(e)}")
            pass
    
#     timer_for_imu.init(
#         freq=5, mode=Timer.PERIODIC, callback=lambda t: IMUprint()
#         )
    s_r.en_pin.value(1)
    s_l.en_pin.value(1)
    
    hb = Heartbeat(8000)
    while True:
        hb.beat() #Send a heartbeat
        try:
            msg = comms.read_parse()
        except Exception as e:
            print(type(e))

        #send_sensory_data(comms)
#         if handle_emergency(s_r, s_l, sensors):

        if msg is not None:
            mystring = ""
            for data in msg:
                mystring += str(data) + " "
            #print(mystring)
            if msg[0] == "s":
                if msg[1] == "r":
                    stepper = s_r
                elif msg[1] == "l":
                    stepper = s_l
                else:
                    continue

                if int(float(msg[2])) == 0:
                    stepper.stop()
                    print(stepper.pos)

                else:
                    stepper.step(stepper.freq)
                    stepper.accelerate(int(float(msg[2])))
                    speed = int(float(msg[2]))
            elif msg[0] == "h":
                hb.feed()
                
                

        gc.collect()


if __name__ == "__main__":
    main()

