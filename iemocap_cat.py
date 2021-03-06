#!/usr/bin/env python3.6
""" Speech emotion recognition, categorical model
on IEMOCAP dataset. Prepared for ISST 2019.
Author: Bagus Tris Atmaja (bagus@ep.its.ac.id)
Cite the following paper if you use (take benefit) from this code:
B.T. Atmaja, Kiyoaki Shirai, Masato Akagi. Deep learning-based 
Dimensional and Categorical Emotion Recognition on Written and 
Spoken Text. ISST 2019.
"""
# uncomment to run on GPU
import os
#os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"   # see issue #152
#os.environ["CUDA_VISIBLE_DEVICES"] = ""

# importing necessary module
import numpy as np
import os
import sys
import copy

from keras.models import Sequential, Model
from keras.layers.core import Dense, Activation
from keras.layers import LSTM, Input, Flatten, Embedding, Dropout, CuDNNGRU
from keras.layers.wrappers import TimeDistributed
from keras.layers.normalization import BatchNormalization
from sklearn.preprocessing import label_binarize
from keras.preprocessing.text import Tokenizer
from keras.preprocessing.sequence import pad_sequences
from keras.preprocessing import sequence

from sklearn.metrics import precision_recall_fscore_support
from sklearn.metrics import confusion_matrix
from plot_confusion_matrix import *

code_path = os.path.dirname(os.path.realpath(os.getcwd()))
emotions_used = np.array(['ang', 'dis', 'fea', 'exc', 'sad', 'sur'])
data_path = '/media/bagus/data01/dataset/IEMOCAP_full_release/'
sessions = ['Session1', 'Session2', 'Session3', 'Session4', 'Session5']

np.random.seed(135)

import pickle
with open('/media/bagus/data01/dataset/IEMOCAP_full_release/data_collected_full.pickle', 'rb') as handle:
    data = pickle.load(handle)

text = [t['transcription'] for t in data if t['emotion'] in emotions_used]
print(len(text))

#MAX_SEQUENCE_LENGTH = 500
MAX_SEQUENCE_LENGTH = len(max(text, key=len))

tokenizer = Tokenizer()
tokenizer.fit_on_texts(text)

token_tr_X = tokenizer.texts_to_sequences(text)
x_train_text = []

x_train_text = sequence.pad_sequences(token_tr_X, maxlen=MAX_SEQUENCE_LENGTH)

import codecs
EMBEDDING_DIM = 300

word_index = tokenizer.word_index
print('Found %s unique tokens' % len(word_index))

# choose between GloVe or FastText
#file_loc = '/media/bagus/data01/github/IEMOCAP-Emotion-Detection/data/glove.840B.300d.txt'
file_loc = '/media/bagus/data01/dataset/fasttext/crawl-300d-2M-subword/crawl-300d-2M-subword.vec'
print (file_loc)

gembeddings_index = {}
with codecs.open(file_loc, encoding='utf-8') as f:
    for line in f:
        values = line.split(' ')
        word = values[0]
        gembedding = np.asarray(values[1:], dtype='float32')
        gembeddings_index[word] = gembedding
#
f.close()
print('G Word embeddings:', len(gembeddings_index))

nb_words = len(word_index) +1
g_word_embedding_matrix = np.zeros((nb_words, EMBEDDING_DIM))
for word, i in word_index.items():
    gembedding_vector = gembeddings_index.get(word)
    if gembedding_vector is not None:
        g_word_embedding_matrix[i] = gembedding_vector
        
print('G Null word embeddings: %d' % np.sum(np.sum(g_word_embedding_matrix, axis=1) == 0))

# load emotion label
Y=[e['emotion'] for e in data if e['emotion'] in emotions_used]    
Y = label_binarize(Y, emotions_used)

Y.shape

# starting deeplearning
model = Sequential()
#model.add(Embedding(nb_words, EMBEDDING_DIM, input_length=MAX_SEQUENCE_LENGTH))
model.add(Embedding(nb_words,
                    EMBEDDING_DIM,
                    weights = [g_word_embedding_matrix],
                    input_length = MAX_SEQUENCE_LENGTH,
                    trainable = True))
model.add(CuDNNGRU(512, return_sequences=True))
model.add(CuDNNGRU(256, return_sequences=False))
model.add(Dense(512, activation='relu'))
model.add(Dense(6, activation='softmax'))

model.compile(loss='categorical_crossentropy', 
              optimizer='rmsprop', 
              metrics=['acc'])
model.summary()

# uncomment to save model plot
from keras.utils import plot_model
plot_model(model, show_shapes=True, show_layer_names=False, to_file='model_gru.pdf')

hist = model.fit(x_train_text[:2700], Y[:2700], 
                 batch_size=32, epochs=30, validation_split=0.2, verbose=1)
                 
loss, acc1 = model.evaluate(x_train_text[2700:], Y[2700:])
print(max(hist.history['val_acc']), acc1)

y_pred = model.predict(x_train_text[2700:])
y_pred = np.argmax(y_pred, axis=-1)
y_true = np.argmax(Y[2700:], axis=-1)
precision_recall_fscore_support(y_true, y_pred, average='weighted')

# plot confusion matrix
ax = plot_confusion_matrix(y_true, y_pred, classes=emotions_used, normalize=True,
                      title='Normalized confusion matrix')

#ax.figure.savefig('confmat_ie.pdf', bbox_inches="tight")

#fig = plt.figure()
#ax = fig.add_axes([1, 1, 1, 1])
fig, ax = plt.subplots()
ax.plot(hist.history['acc'], label='acc')
ax.plot(hist.history['val_acc'], label='val_acc')
ax.legend(loc='best', fontsize=10)
ax.figure.savefig('acc_ie.pdf', bbox_inches='tight')
