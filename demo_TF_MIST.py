
# 下载MNIST数据并解压
import os
current_path = os.path.dirname(__file__)
from six.moves import urllib
import zipfile

DATA_URL = 'http://mantchs.com/data/MNIST.zip'
DATA_DIR = os.path.join(current_path, 'dataset')
FILE = 'MNIST.zip'

if not os.path.exists(DATA_DIR):
    os.mkdir(DATA_DIR)

global n
n = 0
def reporthook(blocks_read,block_size,total_size):
    global n
    if not blocks_read:
        print("Connection opened")
    if blocks_read*block_size/1024.0 > n:
        n += 1000
        print("downloading MNIST: %d KB, totalsize: %d KB" % (blocks_read*block_size/1024.0,total_size/1024.0))

# 下载MNIST数据并解压
filepath, _ = urllib.request.urlretrieve(DATA_URL, os.path.join(DATA_DIR, FILE), reporthook)
with zipfile.ZipFile(os.path.join(DATA_DIR, FILE), 'r') as zip:
    zip.extractall(DATA_DIR)



from tensorflow.examples.tutorials.mnist import input_data
mnist = input_data.read_data_sets(DATA_DIR, one_hot=True)
mnist_train_num = mnist.train.images.shape[0]

import tensorflow as tf
from model_log.modellog import ModelLog
import numpy as np

# Parameters
learning_rate = 0.001
epochs = 500
batch_size = 1000
early_stop = 10
display_step = 1

# Network Parameters
n_hidden_1 = 128 # 1st layer number of neurons
n_hidden_2 = 0 # 2nd layer number of neurons
num_input = 784 # MNIST data input (img shape: 28*28)
num_classes = 10 # MNIST total classes (0-9 digits)

# 初始化 ModelLog
model_log = ModelLog('mantch', 'MNIST手写数字识别')
model_log.add_model_name('nn神经网络')

params = {'learning_rate':learning_rate, 'epochs':epochs, 'batch_size':batch_size, 'n_hidden_1':n_hidden_1,
          'n_hidden_2':n_hidden_2, 'num_input':num_input, 'num_classes':num_classes, 'early_stop':early_stop}
model_log.add_param(params, 'tf_params')

# tf Graph input
X = tf.placeholder("float", [None, num_input])
Y = tf.placeholder("float", [None, num_classes])

# Store layers weight & bias
weights = {
    'h1': tf.Variable(tf.random_normal([num_input, n_hidden_1])),
    'out1': tf.Variable(tf.random_normal([n_hidden_1, num_classes]))
}
biases = {
    'b1': tf.Variable(tf.random_normal([n_hidden_1])),
    'out': tf.Variable(tf.random_normal([num_classes]))
}


# Create model
def neural_net(x):
    # Hidden fully connected layer with 256 neurons
    layer_1 = tf.add(tf.matmul(x, weights['h1']), biases['b1'])
    out_layer = tf.matmul(layer_1, weights['out1']) + biases['out']
    return out_layer

# Construct model
logits = neural_net(X)
prediction = tf.nn.softmax(logits)

# Define loss and optimizer
loss_op = tf.reduce_mean(tf.nn.softmax_cross_entropy_with_logits(
    logits=logits, labels=Y))
optimizer = tf.train.AdamOptimizer(learning_rate=learning_rate)
train_op = optimizer.minimize(loss_op)

# Evaluate model
correct_pred = tf.equal(tf.argmax(prediction, 1), tf.argmax(Y, 1))
accuracy = tf.reduce_mean(tf.cast(correct_pred, tf.float32))

# Initialize the variables (i.e. assign their default value)
init = tf.global_variables_initializer()

# Start training
with tf.Session() as sess:

    # Run the initializer
    sess.run(init)
    best_loss = 100000
    best_epoch = 0

    for epoch in range(1, epochs + 1):

        loss = []
        for i in range(int(mnist_train_num / batch_size)):
            batch_x, batch_y = mnist.train.next_batch(batch_size)
            # Run optimization op (backprop)
            _, batch_loss = sess.run([train_op, loss_op], feed_dict={X: batch_x, Y: batch_y})
            loss.append(batch_loss)

        if epoch % display_step == 0 or epoch == 1:
            # Calculate batch loss and accuracy
            test_loss, acc = sess.run([loss_op, accuracy], feed_dict={X: mnist.test.images,
                                                                 Y: mnist.test.labels})

            loss = np.mean(loss)
            print("Epoch " + str(epoch) + ", Minibatch Loss= " + \
                  "{:.4f}".format(loss) + ", Training Accuracy= " + \
                  "{:.3f}".format(acc))

            # ModelLog 添加评估指标
            model_log.add_metric('train_loss', loss, epoch)
            model_log.add_metric('test_loss', test_loss, epoch)
            model_log.add_metric('test_acc', acc, epoch)


            if test_loss < best_loss:
                best_loss = test_loss
                best_epoch = epoch

            # 早停
            if epoch - best_epoch > 10:
                break


    # ModelLog 添加最好参数
    model_log.add_best_result('best_loss', best_loss, best_epoch)
    model_log.add_best_result('best_step', best_epoch, best_epoch)

    print("Optimization Finished!")

    # Calculate accuracy for MNIST test images
    print("Testing Accuracy:", \
        sess.run(accuracy, feed_dict={X: mnist.test.images,
                                      Y: mnist.test.labels}))
