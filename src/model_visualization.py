#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import csv
import pickle
import warnings
import argparse
import numpy as np
from glob import glob
from sklearn.metrics import precision_recall_fscore_support, classification_report

##############################
# define key functions
##############################

def optimalThreshold(pr_list):
    pr_list = np.asarray(pr_list)
    pr_list = pr_list[np.where(pr_list[:,2] != 0)]
    pr_list = pr_list[np.where(pr_list[:,2] != 1)]
    loc = np.where(pr_list[:,2]>=0.998)[0]
    if len(loc) == 0:
        return pr_list[np.argmax(pr_list[:,2])][0]
    else:
        filtered = pr_list[loc]
        return filtered[np.argmax(filtered[:,1])][0]

def thresholdRNN(pickle_file):
    y_test = np.load("./data/rnn/y_test.npy")
    # main processing
    probs = np.load(glob("./pickles/"+pickle_file+"/prob*")[0])
    thresholds = np.linspace(0,1,19)
    pr_list = []
    for value in thresholds:
        out = np.where(probs >= value, 1, 0)
        res = precision_recall_fscore_support(y_test,out)[:2]
        pr_list.append([value,res[0][0],res[1][0]])
    with open("./pickles/"+pickle_file+"/precision_recall_test.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(i for i in ["threshold","precision","recall"])
        writer.writerows(pr_list)
    optimal = optimalThreshold(pr_list)
    out = np.where(probs >= 0.5, 1, 0)
    with open("./pickles/"+pickle_file+"/classification_report_test.txt", "w") as f:
        f.write(classification_report(y_test,out,digits=4))
    out = np.where(probs >= optimal, 1, 0)
    with open("./pickles/"+pickle_file+"/classification_report_test_optimal.txt", "w") as f:
        f.write("Optimal threshold: "+str(optimal)+"\n")
        f.write(classification_report(y_test,out,digits=4))

def thresholdSVM(pickle_file):
    y_test = np.load("./data/svm/y_test.npy")
    # main processing
    probs = np.load(glob("./pickles/"+pickle_file+"/prob*")[0])
    mean = np.mean(probs)
    std = np.std(probs)
    thresholds = np.linspace(mean-std,mean+std,19)
    pr_list = []
    for value in thresholds:
        out = np.where(probs >= value, 1, -1)
        res = precision_recall_fscore_support(y_test,out)[:2]
        pr_list.append([value,res[0][0],res[1][0]])
    with open("./pickles/"+pickle_file+"/precision_recall_test.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(i for i in ["threshold","precision","recall"])
        writer.writerows(pr_list)
    optimal = optimalThreshold(pr_list)
    out = np.where(probs >= 0, 1, -1)
    with open("./pickles/"+pickle_file+"/classification_report_test.txt", "w") as f:
        f.write(classification_report(y_test,out,digits=4))
    out = np.where(probs >= optimal, 1, -1)
    with open("./pickles/"+pickle_file+"/classification_report_test_optimal.txt", "w") as f:
        f.write("Optimal threshold: "+str(optimal)+"\n")
        f.write(classification_report(y_test,out,digits=4))
        
def importanceSVM(pickle_file):
    with open("./data/svm/words/integer_index_tokens.pickle","rb") as f:
        word_dict = pickle.load(f)
    full_name = glob("./pickles/"+pickle_file+"/best*")[0]
    with open(full_name,"rb") as f:
        model = pickle.load(f)
    word_dict = {v:k for k,v in word_dict.items()}
    words_top = np.argsort(np.abs(model.coef_[0]))[-10:]
    words_bottom = np.argsort(np.abs(model.coef_[0]))[:10]
    x_top = [word_dict[el] for el in words_top]
    y_top = [np.abs(model.coef_[0][el]) for el in words_top]    
    x_bottom = [word_dict[el] for el in words_bottom]
    y_bottom = [np.abs(model.coef_[0][el]) for el in words_bottom]
    with open("./pickles/"+pickle_file+"/top_words.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(i for i in ["word","coefficient"])
        writer.writerows(zip(x_top,y_top))
    with open("./pickles/"+pickle_file+"/bottom_words.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(i for i in ["word","coefficient"])
        writer.writerows(zip(x_bottom,y_bottom))

##############################
# main command call
##############################

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--padding-tokens", type=int, default = 500,
                        help="maximum length of email padding for tokens <default:500>")
    parser.add_argument("--padding-char", type=int, default = 1000,
                        help="maximum length of email padding for characters <default:1000>")
    requiredNamed = parser.add_argument_group('required named arguments')
    requiredNamed.add_argument('-p', '--pickle', type=str,
                               help="pickle directory name for stored model, or input 'all' to run on all models", 
                               required=True)
    args = parser.parse_args()
    files = glob("./pickles/20*")
    # run evaluations based on pickle input
    if args.pickle != "all":
        if "rnn" in args.pickle:
            thresholdRNN(args.pickle)
            warnings.warn("combined plots only possible with '-p all' option")
        elif "svm" in args.pickle:
            thresholdSVM(args.pickle)
            warnings.warn("combined plots only possible with '-p all' option")
            if "linear" in args.pickle:
                os.system("Rscript plot_models.R --type svm")
    else:
        for file in files:
            filename = os.path.basename(file)
            if "rnn" in file:
                thresholdRNN(filename)
            elif "svm" in file:
                thresholdSVM(filename)
                if "linear" in file:
                    os.system("Rscript plot_models.R --type svm")
        os.system("Rscript plot_models.R --type combined")

##############################
# comments/to-dos
##############################

## schema:
# plot threshold values on PR curve with orientation on non-spam class to select best model, to answer qn. 1, plot PR curves with F1-contour lines
# create classification reports for best thresholds, to answer qn. 2 (combined plot)
# 1st table with basic F1 performance, then charts with thresholds, then combined confusion matrices
# then table with adjust thresholds, precision on non-spam, recall on spam and overall F1 performance
# lastly table with blind dataset and F1 performances to find most robust models
# make nice tables, think of how to present uniform classifier

## extra:
# add charts and more structured information on github, with separate docs on function implementation
# make more structured data download systems, with dialogue oriented approach