"""
Data transformations.

Experimental module.

Reusable transformations from one representation of data to another.
eg. converting frames of a video to locations of objects,
or locations of objects to area labels
"""

import cv2
import numpy as np
import threading
import multiprocessing
from queue import Queue

from autopilot.core.networking import Net_Node


class Transform(object):

    def __init__(self, processor, sink=None, **kwargs):
        self.processor = processor

        if sink is None:
            self.init_networking(**kwargs)
        else:
            self.sink = sink


    def init_networking(self, listens=None, **kwargs):
        """
        Spawn a :class:`.Net_Node` to :attr:`Hardware.node` for streaming or networked command

        Args:
            listens (dict): Dictionary mapping message keys to handling methods
            **kwargs: Passed to :class:`.Net_Node`

        Returns:

        """


        self.node = Net_Node(
            **kwargs
        )

        self.sink = self.node.get_stream(
            'stream', 'CONTINUOUS', upstream=to,
            ip=ip, port=port, subject=subject
        )


    def process(self, input):
        output = self.processor(input)

        if self.sink:
            if isinstance(Queue):
                self.sink.put_nowait(output)
            else:
                self.sink(output)
        else:
            return output




a = Transform(processor = DLC_Live_obj, sink = led.set)


#
#
# class Pipeline(multiprocessing.Process):
#
#     def __init__(self, input, stages):
#         """
#
#         Args:
#             stages: list of dictionaries with
#                 {'function': function to be called,
#                  'kwargs': additional keyword arguments to be given to function}
#         """
#
#         self.input = input
#         self.stages = stages
#
#         self.quitting = multiprocessing.Event()
#         self.quitting.clear()
#
#     def run(self):
#
#         # initialize stage objects
#         self.stage_objects = []
#         for stage in self.stages:
#             self.stage_objects.append(stage['function'](stage['kwargs']))
#
#         while not self.quitting.is_set():
#             output = self.input()
#             for stage in self.stages:
#                 output = self.stages.process(output)
#
#
#
#     def __call__(self, input):
#
#         for stage in self.stages:
#             if 'kwargs' in stage.keys():
#                 input = stage['function']
#             input = stage(input)
#
#         return input



class DLC(object):

    def __init__(self, camera):

        self.camera = camera

        self.quitting = threading.Event()
        self.quitting.clear()


    def transform(self):
        self._thread = threading.Thread(target=self._transform)


    def _transform(self):

        while not self.quitting.is_set():







class Img2Loc_binarymass(object):
    METHODS = ('largest')
    def __init__(self, dark_object=True, method="largest"):
        """

        Args:
            dark_object (bool): Is the object dark on a light background (default) or light on a dark background?
            method (str): one of "largest" (find the largest object in each frame)
        """

        self.dark_object = dark_object

        if method in self.METHODS:
            self.method = method
            self.method_fn = getattr(self, self.method)
        else:
            Exception("Unknown method, must be one of {}, got : {}".format(self.METHODS, method))

    def __call__(self, *args, **kwargs):
        return self.method_fn(*args, **kwargs)

    def largest(self, input, return_image=False):

        # TODO: Check if rgb or gray, convert if so

        # blur and binarize with otsu's method
        blur = cv2.GaussianBlur(input, (3,3),0)
        ret, thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY+cv2.THRESH_OTSU)

        # get connected components
        n_components, labels, stats, centroids = cv2.connectedComponentsWithStats(thresh)

        # find largest component
        largest_ind = np.argmax(stats[:,-1])

        # return centroid of largest object
        if return_image:
            return centroids[largest_ind], thresh
        else:
            return centroids[largest_ind]







#
# class Transform(object):
#     """
#     https://blog.usejournal.com/playing-with-inheritance-in-python-73ea4f3b669e
#     """
#
#     def __new__(cls, *args, **kwargs):
#         """
#         Choose a flavor of the particular transform.
#         Flavors should be named This2That_Flavor.
#
#         Args:
#             *args ():
#             **kwargs ():
#
#         Returns:
#
#         """
#         our_name = cls.__name__
#         print(cls)
#         print(our_name)
#
#         flavor = kwargs.get("flavor")
#
#         search_string = "_".join([our_name, flavor])
#
#         # find if there are any matches in our subclasses
#         if cls in Transform.__subclasses__():
#             print('getting subclass')
#             for i in cls.__subclasses__():
#                 if i.__name__ == search_string:
#                     print(i)
#                     #return super(cls).__new__(i)
#                     return i
#         else:
#             # otherwise we are the subclass
#             return super(cls).__new__(cls, *args, **kwargs)
#
#
#
#
# class Img2Loc(Transform):
#     def __init__(self, *args, **kwargs):
#         print('Img2Loc class')
#
# class Img2Loc_binarymass(Img2Loc):
#     def __init__(self, *args, **kwargs):
#         super(Img2Loc_binarymass, self).__init__()
#         print('binarymass class')
#

