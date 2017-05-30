import sys, getopt, datetime
import tensorflow as tf
from math import ceil
from random import choice
from tqdm import tqdm
from data_utility import *
from baseline import BaselineModel

checkpoint = "./baseline-2017-05-26_17-37-23-ep0.ckpt-5100"

###
# Graph execution
###
def mainFunc(argv):
    def printUsage():
        print('main.py -n <num_cores> -x <experiment>')
        print('num_cores = Number of cores requested from the cluster. Set to -1 to leave unset')
        print('experiment = experiment setup that should be executed. e.g \'baseline\'')

    num_cores = -1
    experiment = ""
    # Command line argument handling
    try:
        opts, args = getopt.getopt(argv, "n:x:", ["num_cores=", "experiment="])
    except getopt.GetoptError:
        printUsage()
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            printUsage()
            sys.exit()
        elif opt in ("-n", "--num_cores"):
            num_cores = int(arg)
        elif opt in ("-x", "--experiment"):
            if arg in ("baseline"):
                experiment = arg
            else:
                printUsage()
                sys.exit(2)

    print("Executing experiment {} with {} CPU cores".format(experiment, num_cores))
    if num_cores != -1:
        # We set the op_parallelism_threads in the ConfigProto and pass it to the TensorFlow session
        configProto = tf.ConfigProto(inter_op_parallelism_threads=num_cores,
                                     intra_op_parallelism_threads=num_cores)
    else:
        configProto = tf.ConfigProto()

    print("Initializing model")
    model = None
    if experiment == "baseline":
        model = BaselineModel(encoder_cell=conf.encoder_cell,
                              decoder_cell=conf.decoder_cell,
                              vocab_size=conf.vocabulary_size,
                              embedding_size=conf.word_embedding_size,
                              bidirectional=False,
                              attention=False,
                              debug=False)
    assert model != None
    #enc_inputs, dec_inputs, word_2_index, index_2_word = get_data_by_type('train')
    # Materialize validation data
    validation_enc_inputs, _, word_2_index, index_2_word = get_data_by_type('eval')


    print("Testing network")
    with tf.Session(config=configProto) as sess:
        global_step = 1

        saver = tf.train.Saver(max_to_keep=5, keep_checkpoint_every_n_hours=2)
        sess.run(tf.global_variables_initializer())
        saver.restore(sess, checkpoint)

        batch_in_epoch = 0
        print("Testing:")
        for data_batch, data_sentence_lengths, label_batch, label_sentence_lengths in tqdm(
                bucket_by_sequence_length(validation_enc_inputs, _, conf.batch_size, sort_data=False, shuffle_batches=False),
                total=ceil(len(validation_enc_inputs) / conf.batch_size)):

            batch_in_epoch += 1

            feed_dict = model.make_inference_inputs(data_batch, data_sentence_lengths)

            predictions = sess.run(model.decoder_prediction_inference, feed_dict).T

            for sentence in predictions:
                #print(sentence)
                print(" ".join(map(lambda x: index_2_word[x], sentence)))

            global_step += 1

            if global_step == 150:
                break


if __name__ == "__main__":
    mainFunc(sys.argv[1:])