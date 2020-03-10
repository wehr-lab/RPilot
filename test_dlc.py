from autopilot.hardware.cameras import Camera_Spinnaker
from autopilot.hardware.jetson import Digital_Out_Jetson
from autopilot import prefs
import PySpin
from autopilot.transforms.dlc import DLC
import cv2
import threading
from time import sleep
import numpy as np

#from skvideo import io

prefs.add('LOGDIR', '/home/dlc/logs')

##############
dlc_tfm = DLC('/home/dlc/git/autopilot/spidernet/dlc-models/iteration-0/2020_03_05_3cm_angled_camera-1Mar5-trainset95shuffle1/train/pose_cfg.yaml')

led = Digital_Out_Jetson(33)


n_flashes = 5
for i in range(n_flashes):
    led.set(1)
    sleep(0.1)
    led.set(0)
    sleep(0.1)





cam = Camera_Spinnaker(serial='19269891', name="spincam")
cam.cam.PixelFormat.SetValue(PySpin.PixelFormat_Mono8)

cam.acquisition_mode = 'continuous'
cam.bin = (2,2)
cam.fps = 10
cam.exposure = 0.8
#cam.exposure = 'auto'

#fourcc = cv2.VideoWriter_fourcc(*'XVID')
#writer = cv2.VideoWriter('output.avi', fourcc, 30.0, (540,720), isColor=False)

#cam.cam.BeginAcquisition()


#frame = cam.cam.GetNextImage().GetNDArray()

#cam.capture()

class CamCap(object):
    def __init__(self, cam):
        self.cam = cam
        
        self.frame = None

        self.quitting = threading.Event()
        self.quitting.clear()

        self.cam.cam.BeginAcquisition()

        self.thread = threading.Thread(target=self._capture)
        self.thread.start()    

	    
        
    def _capture(self):
        
        while not self.quitting.is_set():
            self.frame = self.cam.cam.GetNextImage().GetNDArray()
        

camcap = CamCap(cam)

def spider_orientation(pts):
    # head parts x position
    head_parts = np.mean(pts[2:6,0])
    butt_parts = np.mean(pts[6:10,0])
    if head_parts > butt_parts:
        return 1
    else:
        return 0


        
im_num = 0
try:
    while True:
        if camcap.frame is None:
            print('frame is none {}'.format(im_num))
            im_num += 1
            continue
        frame = camcap.frame
        frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2RGB)
        #frame = cam.cam.GetNextImage().GetNDArray()
        #writer.write(frame)
        pts = dlc_tfm.process(frame)
        for i, pt in enumerate(pts):
            if i in (2,3,4,5):
                cv2.circle(frame, (pt[1],pt[0]), 2, (255,0,0), -1)
            elif i in (6,7,8,9):
                cv2.circle(frame, (pt[1],pt[0]), 2, (255,255,0), -1)
            else:
                cv2.circle(frame, (pt[1],pt[0]), 2, (255,255,255), -1)
        cv2.imshow('frame',frame)

        set_led = spider_orientation(pts)
        led.set(set_led)

        #fname = 'spider/image_{}.png'.format(str(im_num).zfill(4))
        #cv2.imwrite(fname, frame)
        #im_num += 1
    
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

except KeyboardInterrupt:
    cv2.destroyAllWindows()
    #writer.release()

finally:
    cam.release()




