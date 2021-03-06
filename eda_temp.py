import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from keras.models import Model
import numpy as np
from keras.models import Sequential
from keras.layers.core import Dense, Activation, Flatten, Dropout
from keras.layers.convolutional import Convolution2D
from keras.layers.pooling import MaxPooling2D
from keras.optimizers import Adam
import os
import cv2
import json
#from imblearn.over_sampling import SMOTE
from collections import Counter

# use  CUDA_VISIBLE_DEVICES="0" ipython in the bash to use actual device 1

BATCH_SIZE = 64
cwd = os.getcwd()
df = pd.read_csv(cwd+'/data/track1mid/driving_log.csv', header=None, names=['center','right','left','steering','throttle','brake','speed']) #use for user collected data
#df = pd.read_csv(cwd+'/data/track1mid/driving_log.csv', header=0) #use for udacity data
# the header setup depends on the data file. check if the data already includes header.
## change df file addresses to full addresses

#impaths = list(map(lambda x: cwd+'/data/track1mid/'+x, df['center'])) #use for udacity data
impaths = list(map(lambda x: '/'.join(x.split('/')[:-2])+'/data/track1mid/'+'/'.join(x.split('/')[-2:]), df['center'])) #use for user collected data
dfs=pd.DataFrame()
dfs['path']=impaths
dfs['angle']=df['steering']
angles = np.array(dfs['angle'])
dfs['time']=dfs.index.values
dfs['speed']=df['speed']
# def sampledata(dfs):
#     X = np.array(dfs[['time','angle']])
#     y = np.array(list(map(lambda x: round(x*10), dfs['angle'])))
#     sm = SMOTE(kind='regular')
#     Xr, yr = sm.fit_sample(X, y)
#     return Xr, yr

def stopfinder(ang, spd):
    x_pre = None
    count = 0
    log = []
    avgspd = 0
    for x, s, i in zip(ang, spd, range(0,len(ang))):
        if (x == 0.0)&(x_pre != 0.0):
            count = 1
            idx = i
            avgspd = s
        elif (x == 0.0)&(x_pre == 0.0):
            count +=1
            avgspd += s
        elif (x!=0.0)&(x_pre==0.0):
            log.append([idx, count, avgspd/count])
            count = 0
            avgspd = 0
        x_pre = x
    if count>0:
        log.append([idx, count, avgspd/count])
    return log

# l = stopfinder(dfs['angle'], dfs['speed'])
# al = np.array(l)
# plt.hist(al[:,1],bins=[0,10,20,30,40,50,60,70,80,90])
# plt.show() # the result shows that there are quite long all-zeros.
# plt.plot(al[:,1],al[:,2],'*')
# plt.show() # it shows that there are quite a bit of flat road cases, and also there are excessively long stop, yet there is no zero speed.
# flatroad = list(filter(lambda x: (x[1]>10)&(x[2]>10), l))
# lowspeed = list(filter(lambda x: (x[2]<10), l))
# bin0 = np.arange(-1,1.1,0.1)
# plt.hist(angles, bin0)

def inversefreq(ang):
    """
    resamples data based on inverse frequency of the angle
    """
    bins = np.arange(-1.1,1.2,0.2) #check if there is 0 and make sure to choose a right bin size
    count, _ = np.histogram(ang,bins)
    prob = []
    for a in angles:
        for i in range(len(bins)-1):
            if (bins[i]<=a)&(a<bins[i+1]):
                prob.append(1/count[i])
    #list(map(lambda x: pmf[int(round(x*5)+5)], ang))
    prob = np.array(prob)
    return prob/prob.sum()

def resample(vec,prob, n):
    res = np.random.choice(vec, n, p=prob)
    return res

dfs['prob'] = inversefreq(df['steering'])
idxselect = resample(range(len(df)), dfs['prob'], 8000)
dfn = dfs.ix[idxselect]

def eqhGray(X): # equalize histogram gray
    if X.shape[-1] ==3:
        Xg = np.array(list(map(lambda x: cv2.cvtColor(x, cv2.COLOR_RGB2GRAY), X)))
    elif X.shape[-1] ==1:
        Xg = X.reshape(X.shape[0],X.shape[1],X.shape[2])
    else:
        print("Error: wrong image dimension")
    Xe = np.array(list(map(lambda x: cv2.equalizeHist(x), Xg)))
    Xe = Xe.reshape(X.shape[0],X.shape[1],X.shape[2],1)
    return (Xe-Xe.mean())/255

def gen(paths, angles, batchsz):
    assert len(paths)==len(angles), "Number of features and targets don't match."
    means = [129.71298823491111, 137.72114920221057, 131.41576367092446] ## update this value when dataset is changed
    while 1:
        for offset in range(0, len(paths), batchsz):
            #x = range(25)[offset:offset+10]
            batch_X = preprocess3(np.array(list(map(lambda x: cv2.imread(x), paths[offset:offset+batchsz]))), means)
            # batch_X = eqhGray(np.array(list(map(lambda x: cv2.imread(x), paths[offset:offset+batchsz]))))
            batch_y = np.array(list(map(lambda x: x, angles[offset:offset+batchsz])))
            yield(batch_X, batch_y)

def dataexplore(paths):
    X = np.array(list(map(lambda x: cv2.imread(x), paths)))
    means = [X[:,:,:,i].mean() for i in range(3)]
    del X
    return means

def preprocess3(X, means):
    return np.concatenate([np.expand_dims((X[:,:,:,i]-means[i])/255.,axis=3) for i in range(3)], axis=3)

model = Sequential()
model.add(Convolution2D(32, 3, 3, input_shape=(160, 320, 3),border_mode='same',init='glorot_normal', activation='relu'))
model.add(Convolution2D(32, 3, 3, border_mode='same',init='glorot_normal', activation='relu'))
model.add(MaxPooling2D((2, 2),dim_ordering='tf'))
model.add(Dropout(0.5))
#model.add(Activation('relu'))
model.add(Convolution2D(64, 3, 3, border_mode='same',init='glorot_normal',activation='relu'))
model.add(Convolution2D(64, 3, 3, border_mode='same',init='glorot_normal',activation='relu'))
model.add(MaxPooling2D((2, 2),dim_ordering='tf'))
model.add(Dropout(0.5))
#model.add(Activation('relu'))
model.add(Flatten())
model.add(Dense(64))
model.add(Activation('relu'))
model.add(Dense(1))
model.add(Activation('tanh'))

#adam = Adam(lr=0.001, beta_1=0.9, beta_2=0.999, epsilon=1e-08, decay=0.0)
model.compile(loss='mse', optimizer='Adam', lr = 0.001)

model.fit_generator(gen(dfs['path'],dfs['angle'], BATCH_SIZE),samples_per_epoch=len(dfs['angle']), nb_epoch=10)

##
#http://stackoverflow.com/questions/38936016/keras-how-are-batches-and-epochs-used-in-fit-generator

# https://carnd-forums.udacity.com/questions/36051083/p3-some-reflection

# https://keras.io/getting-started/faq/#how-can-i-obtain-the-output-of-an-intermediate-layer
# intermediate_layer_model = Model(input=model.input,
#                                  output=model.get_layer(layer_name).output)
# intermediate_output = intermediate_layer_model.predict(data)

### EDA with dummy model
# g = gen(impaths[1000:2000], angles[1000:2000], 128) #take some data in the middle to avoid a lot of zero angles in the beginning
# g0 = next(g) #generate data as tuple
# X, y = g0
# #y = y.reshape((128,2))
# yp = model.predict(X, batch_size=128) #comparing yp and y by eyes suggest that the model+training sucks.
## Comment: it could be combination of these
## 1) model is too primitive,
## 2) needs data augmentation and preprocessing,
## 3) the ordered data can cause training problem (does randomizing help?),
## 4) there might be a discontinuity in the data if data collection has been pause and resumed,
## 5) may need speed information,  (the network fusion at the end can help- 3-4 parameters at the end + speed)

# model_json = model.to_json()
# with open("model.json", "w") as json_file:
#     json_file.write(model_json)
# # serialize weights to HDF5
# model.save_weights("model.h5")
model.save('model.h5')
