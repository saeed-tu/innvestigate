# Begin: Python 2/3 compatibility header small
# Get Python 3 functionality:
from __future__ import \
    absolute_import, print_function, division, unicode_literals
from future.utils import raise_with_traceback, raise_from
# catch exception with: except Exception as e
from builtins import range, map, zip, filter
from io import open
import six
# End: Python 2/3 compatability header small


###############################################################################
###############################################################################
###############################################################################


import imp
import keras.backend
import keras.models
import matplotlib.pyplot as plt
import numpy as np
import os

import keras
from keras.datasets import mnist
from keras.models import Model
from keras.optimizers import RMSprop

import innvestigate
import innvestigate.utils as iutils
import innvestigate.utils.tests.networks.base
import innvestigate.utils.visualizations as ivis

from innvestigate.tools import Perturbation, PerturbationAnalysis

base_dir = os.path.dirname(__file__)
eutils = imp.load_source("utils", os.path.join(base_dir, "utils.py"))

keras.backend.set_image_data_format("channels_first")


###############################################################################
###############################################################################
###############################################################################


def fetch_data():
    # the data, shuffled and split between train and test sets
    (x_train, y_train), (x_test, y_test) = mnist.load_data()

    x_train = x_train.reshape(60000, 1, 28, 28)
    x_test = x_test.reshape(10000, 1, 28, 28)
    x_train = x_train.astype('float32')
    x_test = x_test.astype('float32')
    print(x_train.shape[0], 'train samples')
    print(x_test.shape[0], 'test samples')

    return x_train, y_train, x_test, y_test


def create_model():
    num_classes = 10

    network = innvestigate.utils.tests.networks.base.mlp_2dense(
        (None, 1, 28, 28),
        num_classes,
        dense_units=1024,
        dropout_rate=0.25)
    model_wo_sm = Model(inputs=network["in"], outputs=network["out"])
    model_w_sm = Model(inputs=network["in"], outputs=network["sm_out"])
    return model_wo_sm, model_w_sm


def train_model(model, data):
    batch_size = 128
    num_classes = 10
    epochs = 1

    x_train, y_train, x_test, y_test = data
    # convert class vectors to binary class matrices
    y_train = keras.utils.to_categorical(y_train, num_classes)
    y_test = keras.utils.to_categorical(y_test, num_classes)

    model.compile(loss='categorical_crossentropy',
                  optimizer=RMSprop(),
                  metrics=['accuracy'])

    history = model.fit(x_train, y_train,
                        batch_size=batch_size,
                        epochs=epochs,
                        verbose=0)
    score = model.evaluate(x_test, y_test, verbose=0)
    print('Test loss:', score[0])
    print('Test accuracy:', score[1])


def preprocess(X, zero_mean=False):
    X.copy()
    X /= 255
    if zero_mean:
        X -= 0.5
    return X


###############################################################################
###############################################################################
###############################################################################

if __name__ == "__main__":
    print("This script is deprecated and has been replaced by a Jupyter Notebook version (mnist_perturbation.ipynb).")
    num_classes = 10
    batch_size = 256
    data = fetch_data()
    data_preprocessed = (preprocess(data[0]), data[1],
                         preprocess(data[2]), data[3])
    x_test, y_test = data_preprocessed[2:]
    y_test = keras.utils.to_categorical(y_test, num_classes)
    generator = iutils.BatchSequence([x_test, y_test], batch_size=batch_size)

    # Build and train model
    model_without_softmax, model_with_softmax = create_model()
    train_model(model_with_softmax, data_preprocessed)
    model_without_softmax.set_weights(model_with_softmax.get_weights())

    # Setup analyzer
    method = ("lrp.z_baseline", {}, ivis.heatmap, "LRP-Z")
    analyzer = innvestigate.create_analyzer(method[0],
                                            model_without_softmax,
                                            **method[1])

    # Perturbation analysis
    perturbation_function = "mean"
    perturbation = Perturbation(perturbation_function, region_shape=(5, 5))
    perturbation_analysis = PerturbationAnalysis(analyzer, model_with_softmax, generator, perturbation, steps=10,
                                                 ratio=0.01)
    scores = perturbation_analysis.compute_perturbation_analysis()
    scores = np.array(scores)
    print("Scores:")
    print(scores)
    plt.plot(scores[:, 1])
    plt.xlabel("Perturbation steps")
    plt.ylabel("Test accuracy")
    plt.xticks(np.array(range(scores.shape[0])))
    plt.savefig("perturbation_analysis.pdf")

    # Plot perturbation steps
    steps = 5
    test_sample = generator[0][0][0:1]  # Select one sample

    plt.figure()
    plt.subplot(1, steps + 1, 1)
    plt.imshow(np.squeeze(test_sample), cmap="Greys_r")
    plt.axis("off")
    plt.title("Sample")

    for i in range(steps):
        test_sample = perturbation_analysis.compute_on_batch(test_sample)
        plt.subplot(1, steps + 1, i + 2)
        plt.imshow(np.squeeze(test_sample), cmap="Greys_r")
        plt.title("{} Step{}".format(i + 1, "" if i == 0 else "s"))
        plt.axis("off")
    plt.suptitle("Perturbated Samples")
    plt.tight_layout()  # Takes care of spaces between subfigures

    plt.savefig("perturbated_sample.pdf")

    keras.backend.clear_session()
