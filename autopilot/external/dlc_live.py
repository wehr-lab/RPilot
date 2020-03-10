"""
DeepLabCut2.0 Toolbox (deeplabcut.org)
© A. & M. Mathis Labs
https://github.com/AlexEMG/DeepLabCut
Please see AUTHORS for contributors.
https://github.com/AlexEMG/DeepLabCut/blob/master/AUTHORS
Licensed under GNU Lesser General Public License v3.0
"""

'''
Python class to perform inference on individual images using specified DLC network (e.g. to be used on live camera feed).
Please see companion GUI for full program to record video while performing inference.
GK 12/05/2019
'''

import cv2
import os
from pathlib import Path
import numpy as np
from deeplabcut.utils import auxiliaryfunctions
from deeplabcut.pose_estimation_tensorflow.nnet import predict
from deeplabcut.pose_estimation_tensorflow.config import load_config
from skimage.util import img_as_ubyte

import tensorflow as tf




class DLCLive(object):
    '''
    Parameters:
    -----------
    config : string
        Full path of the config.yaml file as a string.
    cropping : list of int
        cropping parameters in pixel number: [x1, x2, y1, y2]
    iteration : int, optional
        which iteration to use
    shuffle: int, optional
        An integer specifying the shuffle index of the training dataset used for training the network. The default is 1.
    trainingsetindex: int, optional
        Integer specifying which TrainingsetFraction to use. By default the first (note that TrainingFraction is a list in config.yaml).
    gputouse: int, optional
        Natural number indicating the number of your GPU (see number in nvidia-smi). If you do not have a GPU put None.
        See: https://nvidia.custhelp.com/app/answers/detail/a_id/3751/~/useful-nvidia-smi-queries
    useFrozen: bool, optional
        use frozen tensorflow model (speeds up inference)
    TFGPUinference: bool, optional
        Perform inference on GPU with Tensorflow code. Introduced in "Pretraining boosts out-of-domain robustness for pose estimation" by
        Alexander Mathis, Mert Yüksekgönül, Byron Rogers, Matthias Bethge, Mackenzie W. Mathis Source: https://arxiv.org/abs/1909.11229
    dynamic: triple containing (state,detectiontreshold,margin)
        If the state is true, then dynamic cropping will be performed. That means that if an object is detected (i.e. any body part > detectiontreshold),
        then object boundaries are computed according to the smallest/largest x position and smallest/largest y position of all body parts. This  window is
        expanded by the margin and from then on only the posture within this crop is analyzed (until the object is lost, i.e. <detectiontreshold). The
        current position is utilized for updating the crop window for the next frame (this is why the margin is important and should be set large
        enough given the movement of the animal).
    processor: dlc pose processor object, optional
        User-defined processor object. Must contain two methods: process and save.
        The 'process' method takes in a pose, performs some processing, and returns processed pose.
        The 'save' method saves any valuable data created by or used by the processor
        Processors can be used for two main purposes:
        i) to run a forward predicting model that will predict the future pose from past history of poses (history can be stored in the processor object, but is not stored in this DLCLive object)
        ii) to trigger external hardware based on pose estimation (e.g. see 'TeensyLaser' processor)
    '''

    def __init__(self, config, cropping=None,
                 fps=100, iteration=None, shuffle=1, trainingsetindex=0,
                 gputouse=None, useFrozen=True, TFGPUinference=False, dynamic=(False,.5,10),
                 processor=None):

        self.cropping = cropping
        self.iteration = iteration
        self.shuffle = shuffle
        self.trainingsetindex = trainingsetindex
        self.gputouse = gputouse
        self.useFrozen = useFrozen
        self.TFGPUinference = TFGPUinference
        self.dynamic = dynamic
        self.processor = processor
        self.setup_prediction(config)

    def setup_prediction(self, config):
        ##################################
        ### GET DLC CONFIG INFO
        ### from deeplabcut.analyze_videos
        ##################################

        if self.gputouse is not None: #gpu selection
                os.environ['CUDA_VISIBLE_DEVICES'] = str(self.gputouse)

        self.cfg = auxiliaryfunctions.read_config(config)
        if self.iteration is not None:
            self.cfg['iteration'] = self.iteration
        trainFraction = self.cfg['TrainingFraction'][self.trainingsetindex]

        if self.cropping is not None:
            self.cfg['cropping']=True
            self.cfg['x1'], self.cfg['x2'], self.cfg['y1'], self.cfg['y2'] = self.cropping
            print("Overwriting cropping parameters:", self.cropping)

        self.cfg["project_path"] = os.path.dirname(config)
        modelfolder = os.path.join(self.cfg["project_path"],str(auxiliaryfunctions.GetModelFolder(trainFraction, self.shuffle, self.cfg)))
        path_test_config = Path(modelfolder) / 'test' / 'pose_cfg.yaml'
        try:
            self.dlc_cfg = load_config(str(path_test_config))
        except FileNotFoundError:
            raise FileNotFoundError("It seems the model for shuffle %s and trainFraction %s does not exist."%(self.shuffle, trainFraction))

        # Check which snapshots are available and sort them by # iterations
        try:
          Snapshots = np.array([fn.split('.')[0]for fn in os.listdir(os.path.join(modelfolder , 'train'))if "index" in fn])
        except FileNotFoundError:
          raise FileNotFoundError("Snapshots not found! It seems the dataset for shuffle %s has not been trained/does not exist.\n Please train it before using it to analyze videos.\n Use the function 'train_network' to train the network for shuffle %s."%(shuffle,shuffle))

        if self.cfg['snapshotindex'] == 'all':
            print("Snapshotindex is set to 'all' in the config.yaml file. Running video analysis with all snapshots is very costly! Use the function 'evaluate_network' to choose the best the snapshot. For now, changing snapshot index to -1!")
            snapshotindex = -1
        else:
            snapshotindex = self.cfg['snapshotindex']

        increasing_indices = np.argsort([int(m.split('-')[1]) for m in Snapshots])
        Snapshots = Snapshots[increasing_indices]

        print("Using %s" % Snapshots[snapshotindex], "for model", modelfolder)

        ##################################################
        # Load and setup CNN part detector
        ##################################################

        # Check if data already was generated:
        self.dlc_cfg['init_weights'] = os.path.join(modelfolder , 'train', Snapshots[snapshotindex])
        trainingsiterations = (self.dlc_cfg['init_weights'].split(os.sep)[-1]).split('-')[-1]

        # Update number of output and batchsize
        self.dlc_cfg['num_outputs'] = self.dlc_cfg.get('num_outputs', 1)
        self.dlc_cfg['batch_size'] = 1

        if self.dynamic[0]: #state=true
            #(state,detectiontreshold,margin)=dynamic
            print("Starting analysis in dynamic cropping mode with parameters:", self.dynamic)
            self.dlc_cfg['num_outputs']=1
            self.TFGPUinference=False
            print("Switching num_outputs (per animal) to 1 and TFGPUinference to False (all these features are not supported in this mode).")

        # Name for scorer:
        self.scorer, self.scorerlegacy = auxiliaryfunctions.GetScorerName(self.cfg, self.shuffle, trainFraction, trainingsiterations=trainingsiterations)
        if self.dlc_cfg['num_outputs']>1:
            if self.TFGPUinference:
                print("Switching to numpy-based keypoint extraction code, as multiple point extraction is not supported by TF code currently.")
                self.TFGPUinference=False
            print("Extracting ", self.dlc_cfg['num_outputs'], "instances per bodypart")

        if self.useFrozen:
            self.sess, self.inputs, self.outputs = predict.setup_frozen_prediction(self.dlc_cfg)
        elif self.TFGPUinference:
            self.sess, self.inputs, self.outputs = predict.setup_GPUpose_prediction(self.dlc_cfg)
            self.pose_tensor = predict.extract_GPUprediction(self.outputs, self.dlc_cfg)
        else:
            self.sess, self.inputs, self.outputs = predict.setup_pose_prediction(self.dlc_cfg)

    def get_pose(self, frame):

        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame = img_as_ubyte(frame) if not self.cfg['cropping'] else img_as_ubyte(frame[self.cfg['y1']:self.cfg['y2'],self.cfg['x1']:self.cfg['x2']])
        if self.useFrozen:
            pose = self.sess.run(self.outputs, feed_dict={self.inputs: np.expand_dims(frame, axis=0).astype(float)})
        elif self.TFGPUinference:
            pose = self.sess.run(self.pose_tensor, feed_dict={self.inputs: np.expand_dims(frame, axis=0).astype(float)})
            pose[:, [0,1,2]] = pose[:, [1,0,2]]
        else:
            pose = predict.getpose(frame, self.dlc_cfg, self.sess, self.inputs, self.outputs)

        if self.processor:
            pose = self.processor.process(pose)

        return pose

    def __call__(self, frame):
        return self.get_pose(frame)