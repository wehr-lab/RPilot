import Jetson.GPIO as GPIO
GPIO.setmode(GPIO.BOARD)

class Digital_Out_Jetson(object):

    states = {
        0: GPIO.LOW,
        1: GPIO.HIGH
    }

    def __init__(self, pin, initial=0):
        self.pin = pin

        GPIO.setup(pin, GPIO.OUT, initial=self.states[initial])


    def set(self, state):
        if state in self.states.keys():
            state = self.states[state]
        elif state in self.states.values():
            pass
        else:
            raise ValueError('Must be one of {} or {}'.format(self.states.keys(), self.states.values()))

        GPIO.output(self.pin, state)
