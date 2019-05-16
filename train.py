from __future__ import print_function

import numpy as np
import os
import sys
import tensorflow as tf



from keras import backend as K
from keras.callbacks import ModelCheckpoint
from keras.callbacks import TensorBoard
from keras.optimizers import Adam

from data import load_data
from data import oversample
from net import dice_coef
from net import dice_coef_loss
from net import unet
from model_dilation import get_frontend
import pdb


train_images_path = '/media/alexshakouri/TOURO Mobile USB3.02/Research/Code/brain-segmentation-master/data/dataAll_128'
valid_images_path = '/media/alexshakouri/TOURO Mobile USB3.02/Research/Code/brain-segmentation-master/data/dataAllVal_128'
init_weights_path = '/media/alexshakouri/TOURO Mobile USB3.02/Research/Code/brain-segmentation-master/Rat_Brain_Sementation/results/weights_multiLabel_unet_whaaaa.h5'
weights_path = '/media/alexshakouri/TOURO Mobile USB3.02/Research/Code/brain-segmentation-master/Rat_Brain_Sementation/results/'
log_path = '/media/alexshakouri/TOURO Mobile USB3.02/Research/Code/brain-segmentation-master/Rat_Brain_Sementation/results/logs/multiLabel1_unet_test'



#train_images_path = '/home/ashakour/MRI_segmentation/data/dataAll_128/'
#valid_images_path = '/home/ashakour/MRI_segmentation/data/dataAllVal_128/'


##train_images_path = '/home/ashakour/MRI_segmentation/flair-segmentation/data_128/'
##valid_images_path = '/home/ashakour/MRI_segmentation/flair-segmentation/dataVal_128/'

#init_weights_path = '/home/ashakour/MRI_segmentation/Rat_Brain_Sementation/results/weights_dilation_128_WHAT.h5'
#weights_path = '/home/ashakour/MRI_segmentation/Rat_Brain_Sementation/results/'
#log_path = '/home/ashakour/MRI_segmentation/Rat_Brain_Sementation/results/logs/singleLabel1_dilation_dice_1'



cross_val = True

gpu = '0'

epochs = 128
batch_size = 32
base_lr = 1e-6
decay_lr = 0.00 # ADAM optimizer doesn't need decay as the base_lr is a max for it. 
imageDim = 128
num_classes = 1
class_weight = [1,1]

def create_weighted_binary_crossentropy(class_weight):
    def weighted_binary_crossentropy(y_true, y_pred):

        # Original binary crossentropy (see losses.py):
        # K.mean(K.binary_crossentropy(y_true, y_pred), axis=-1)

        # Calculate the binary crossentropy
        b_ce = K.binary_crossentropy(y_true, y_pred)

        # Apply the weights
        weight_vector = y_true * class_weight[1] + (1. - y_true) * class_weight[0]
        weighted_b_ce = weight_vector * b_ce
        # Return the mean error
        return K.mean(weighted_b_ce)
    return weighted_binary_crossentropy

def train():
    imgs_train, imgs_mask_train, imgs_names_train = load_data(train_images_path, num_classes)

    mean = np.mean(imgs_train)
    std = np.std(imgs_train)

    imgs_train -= mean
    imgs_train /= std

    imgs_valid, imgs_mask_valid, _ = load_data(valid_images_path, num_classes)

    imgs_valid -= mean
    imgs_valid /= std

    imgs_train, imgs_mask_train = oversample(imgs_train, imgs_mask_train, imgs_names_train, num_classes)

    #model is unet
    model = unet(num_classes)
    #model dilated convolutions
    #model = get_frontend(imageDim,imageDim, num_classes)


    if os.path.exists(init_weights_path):
        model.load_weights(init_weights_path)

    #Optimal weighting per class (binary cross entropy)
    class_weight[1] = np.size(imgs_mask_train)/np.sum(imgs_mask_train)
    class_weight[0] = np.size(imgs_mask_train)/(np.size(imgs_mask_train) - np.sum(imgs_mask_train)) 

    optimizer = Adam(lr=base_lr)#, decay=decay_lr)
    model.compile(optimizer=optimizer,
                  #loss=create_weighted_binary_crossentropy(class_weight),
                  #metrics=['acc', dice_coef])
		  loss=dice_coef_loss,
                  metrics=[dice_coef])

    if not os.path.exists(log_path):
        os.mkdir(log_path)

    save_model = ModelCheckpoint(filepath=os.path.join(weights_path, "weights_multiLabel_unet_test_{epoch:03d}.h5"), period=50)
    training_log = TensorBoard(log_dir=log_path)

    model.fit(imgs_train, imgs_mask_train,
              validation_data=(imgs_valid, imgs_mask_valid),
              batch_size=batch_size,
              epochs=epochs,
              shuffle=True,
              callbacks=[training_log, save_model])

    if not os.path.exists(weights_path):
        os.mkdir(weights_path)
    model.save_weights(os.path.join(
        weights_path, 'weights_multilabl_unet_test_{}.h5'.format(epochs)))


if __name__ == '__main__':
    config = tf.ConfigProto()
    config.gpu_options.allow_growth = True
    config.allow_soft_placement = True
    sess = tf.Session(config=config)
    K.set_session(sess)

    if len(sys.argv) > 1:
        gpu = sys.argv[1]
    device = '/gpu:' + gpu

    with tf.device(device):
        train()
