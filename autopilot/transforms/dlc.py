import os

os.environ['DLClight'] = 'True'  # so wxpython is not required.

import numpy as np
import tensorflow as tf
from easydict import EasyDict as edict

vers = (tf.__version__).split('.')
if int(vers[0]) == 1 and int(vers[1]) > 12:
    TF = tf.compat.v1
else:
    TF = tf

import deeplabcut
from deeplabcut.pose_estimation_tensorflow.config import load_config
from deeplabcut.pose_estimation_tensorflow.nnet.net_factory import pose_net

class DLC(object):
    def __init__(self, cfg_path):

        self.cfg_path
        self.cfg = edict(load_config(cfg_path))




    ### Code for TF inference on GPU
    # introduced https://arxiv.org/pdf/1909.11229.pdf
    def setup_GPUpose_prediction(self):
        ''' Adapted from DLC '''
        TF.reset_default_graph()
        inputs = TF.placeholder(TF.float32, shape=[self.cfg.batch_size, None, None, 3])
        net_heads = pose_net(self.cfg).inference(inputs)
        outputs = [net_heads['pose']]

        restorer = TF.train.Saver()
        sess = TF.Session()

        sess.run(TF.global_variables_initializer())
        sess.run(TF.local_variables_initializer())

        # Restore variables from disk.
        restorer.restore(sess, self.cfg.init_weights)

        return sess, inputs, outputs


    def store_model(self):
        """
        Load a saved checkpoint, freeze and save the graph.

        ----------
        cfg_path : string
            Full path to the trained model that you want to store.

        Examples
        --------
        >>> store_model('/home/alex/TEST-Franz-2020-03-03/dlc-models/iteration-0/TESTMar3-trainset95shuffle1/train/snapshot100000')

        >>> store_model('C:\\Users\\CLOWNCAT\\Desktop\\TEST-Franz-2020-03-03\\dlc-models\\iteration-0\\TESTMar3-trainset95shuffle1\\train\\snapshot100000')
        Adapted from https://leimao.github.io/blog/Save-Load-Inference-From-TF-Frozen-Graph/
        """
        from tensorflow.python.tools import freeze_graph


        sess, _, _ = setup_GPUpose_prediction(self.cfg)
        pbtxt_file = self.cfg.init_weights + '_frozen.pbtxt' if self.cfg.batch_size == 1 else self.cfg.init_weights + '_frozen_batch.pbtxt'
        pb_file = self.cfg.init_weights + '_frozen.pb' if self.cfg.batch_size == 1 else self.cfg.init_weights + '_frozen_batch.pb'
        TF.train.write_graph(sess.graph.as_graph_def(), '', pbtxt_file, as_text=True)
        freeze_graph.freeze_graph(pbtxt_file, '', False,
                                  self.cfg.init_weights, "concat_1",
                                  "save/restore_all", "save/Const:0",
                                  pb_file, True, '')


    def setup_frozen_prediction(self):
        pb_file = self.cfg.init_weights + '_frozen.pb' if self.cfg.batch_size == 1 else self.cfg.init_weights + '_frozen_batch.pb'

        if not os.path.isfile(pb_file):
            print("Frozen model not found, freezing model now...")
            self.store_model()
            print("Freezing complete!")


        graph = TF.Graph()
        with TF.gfile.GFile(pb_file, 'rb') as f:
            graph_def = TF.GraphDef()
            graph_def.ParseFromString(f.read())

        with graph.as_default():
            inputs = TF.placeholder(TF.float32, shape=[self.cfg.batch_size, None, None, 3])
            TF.import_graph_def(graph_def, {'Placeholder': inputs}, name='Placeholder')
        graph.finalize()

        sess = TF.Session(graph=graph)
        outputs = graph.get_tensor_by_name("Placeholder_1/concat_1:0")

        return sess, inputs, outputs