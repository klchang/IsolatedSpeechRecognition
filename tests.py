import numpy as np
import os
file_paths = []
labels = []
spoken_word = []
for f in os.listdir('audio'):
    for w in os.listdir('audio/' + f):  
        file_paths.append('audio/' + f + '/' + w)
        labels.append(f)
        if f not in spoken_word:
            spoken_word.append(f)
print('List of spoken words:', spoken_word)
print set(labels)

from scipy.io import wavfile

data = np.zeros((len(file_paths), 32000))
maxsize = -1
for n,file in enumerate(file_paths):
    _, d = wavfile.read(file)
    data[n, :d.shape[0]] = d
    if d.shape[0] > maxsize:
        maxsize = d.shape[0]
data = data[:, :maxsize]
print('Number of total files:', data.shape[0])
all_labels = np.zeros(data.shape[0])
for n, l in enumerate(set(labels)):
    all_labels[np.array([i for i, _ in enumerate(labels) if _ == l])] = n
    
print('Labels and label indices', all_labels)
print data.shape

#import python_speech_features as speech
#all_obs = np.zeros([500, 13, 43])
#for n,file in enumerate(file_paths):
#    all_obs[n,]=speech.mfcc(data[n,:]).T
#print all_obs.shape

import scipy

def stft(x, fftsize=64, overlap_pct=.5):
    hop = int(fftsize * (1 - overlap_pct))
    w = scipy.hanning(fftsize + 1)[:-1]    
    raw = np.array([np.fft.rfft(w * x[i:i + fftsize]) for i in range(0, len(x) - fftsize, hop)])
    return raw[:, :(fftsize // 2)]

from numpy.lib.stride_tricks import as_strided


def peakfind(stft_data, n_peaks, l_size=3, r_size=3, c_size=3, f=np.mean):
    window_size = l_size + r_size + c_size
    shape = stft_data.shape[:-1] + (stft_data.shape[-1] - window_size + 1, window_size)
    strides = stft_data.strides + (stft_data.strides[-1],)
    xs = as_strided(stft_data, shape=shape, strides=strides)
    def is_peak(stft_data):
        centered = (np.argmax(data) == l_size + int(c_size/2))
        l = stft_data[:l_size]
        c = stft_data[l_size:l_size + c_size]
        r = stft_data[-r_size:]
        passes = np.max(c) > np.max([f(l), f(r)])
        if centered and passes:
            return np.max(c)
        else:
            return -1
    r = np.apply_along_axis(is_peak, 1, xs)
    top = np.argsort(r, None)[::-1]
    heights = r[top[:n_peaks]]
    top[top > -1] = top[top > -1] + l_size + int(c_size / 2.)
    return heights, top[:n_peaks]

all_obs = []
for i in range(data.shape[0]):
    d = np.abs(stft(data[i, :]))
    n_dim = 5
    obs = np.zeros((n_dim, d.shape[0]))
    for r in range(d.shape[0]):
        _, t = peakfind(d[r, :], n_peaks=n_dim)
        obs[:, r] = t.copy()
    if i % 50 == 0:
        print("Processed observation %s" % i)
    all_obs.append(obs)
    
all_obs = np.atleast_3d(all_obs)
print all_obs.shape


import scipy.stats as st
import numpy as np
from hmm.continuous.GMHMM import GMHMM
#from hmm.discrete.DiscreteHMM import DiscreteHMM
import numpy

def test_simple(obs):
    n = 5
    m = 5
    d = 218
    pi = numpy.array([0.5, 0.5, 0.5, 0.5, 0.5])
    A = numpy.ones((n,n),dtype=numpy.double)/float(n)
    
    w = numpy.ones((n,m),dtype=numpy.double)
    means = numpy.ones((n,m,d),dtype=numpy.double)
    covars = [[ numpy.matrix(numpy.eye(d,d)) for j in xrange(m)] for i in xrange(n)]
    n_iter = 20
    '''w[0][0] = 0.5
    w[0][1] = 0.5
    w[1][0] = 0.5
    w[1][1] = 0.5    
    means[0][0][0] = 0.5
    means[0][0][1] = 0.5
    means[0][1][0] = 0.5    
    means[0][1][1] = 0.5
    means[1][0][0] = 0.5
    means[1][0][1] = 0.5
    means[1][1][0] = 0.5    
    means[1][1][1] = 0.5 '''

    gmmhmm = GMHMM(n,m,d,A,means,covars,w,pi,init_type='user',verbose=True)
    
    print "Doing Baum-welch"
    #gmmhmm.train(obs,10)
    if len(obs.shape) == 2:
        for i in range(n_iter):
            gmmhmm.train(obs)
            print
            print "Pi",gmmhmm.pi
            print "A",gmmhmm.A
            print "weights", gmmhmm.w
            print "means", gmmhmm.means
            print "covars", gmmhmm.covars
            
    elif len(obs.shape) == 3:
        count = obs.shape[0]
        for n in range(count):
            for i in range(n_iter):
                gmmhmm.train(obs[n, :, :])
                print
                print "Pi",gmmhmm.pi
                print "A",gmmhmm.A
                print "weights", gmmhmm.w
                print "means", gmmhmm.means
                print "covars", gmmhmm.covars


def test(self, obs):
    if len(obs.shape) == 2:
        self._mapB(obs)
        log_likelihood, _ = self.forwardbackward(obs, cache=True)
        return log_likelihood
    elif len(obs.shape) == 3:
        count = obs.shape[0]
        out = np.zeros((count,))
        for n in range(count):
            self._mapB(obs[n, :, :])
            log_likelihood, _ = self.forwardbackward(obs[n, :, :], cache=True)
            out[n] = log_likelihood
        return out

from sklearn.cross_validation import StratifiedShuffleSplit
sss = StratifiedShuffleSplit(all_labels, test_size=0.1, random_state=0)

for n,i in enumerate(all_obs):
    all_obs[n] /= all_obs[n].sum(axis=0)
    

for train_index, test_index in sss:
    X_train, X_test = all_obs[train_index, ...], all_obs[test_index, ...]
    y_train, y_test = all_labels[train_index], all_labels[test_index]
ys = set(all_labels)

'''We need to call test_simple function in test.py for each model.'''


ms = [test_simple(X_train[y_train == y, :, :]) for y in ys]

#_ = [model.train(X_train[y_train == y, :, :]) for model, y in zip(ms, ys)]
ps = [test(X_test) for model in ms]
res = np.vstack(ps1)
predicted_label = np.argmax(res, axis=0)
#dictionary = ['apple', 'banana', 'elephant', 'dog', 'frog', 'cat', 'jack', 'gorgeous', 'Intelligent', 'hello']
dictionary = ['nine', 'seven', 'six', 'two', 'eight', 'five', 'three', 'zero', 'four', 'one']
spoken_word = []
for i in predicted_label:
    spoken_word.append(dictionary[i])
print spoken_word
missed = (predicted_label != y_test)
print('Test accuracy: %.2f percent' % (100 * (1 - np.mean(missed))))