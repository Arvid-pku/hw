from tqdm import  tqdm_notebook
from nltk.tokenize import word_tokenize
import jsonlines
from collections import defaultdict
import csv
import numpy as np
import torch
from torch.utils.data import (TensorDataset, DataLoader, RandomSampler, SequentialSampler, Dataset)
from sklearn.model_selection import train_test_split

def load_data(filepath):
    labels = []
    texts = []
    with open(filepath, 'r') as f:
        for dic in jsonlines.Reader(f):
            if 'answer' in dic.keys():
                if dic['answer']:
                    labels.append(1)
                else:
                    labels.append(0)
            else:
                labels.append(1)
            texts.append(dic['title'].lower().strip()
            +' [<sep>] '
            +dic['passage'].lower().strip()
            +' [<sep>] '
            +dic['question'].lower().strip())
    return labels, texts



def write_data(tofile, fromfile, labelis):
    with open(fromfile, 'r') as f:
        tf = open(tofile, 'w')
        for label, line in zip(labelis, f):
            tf.write(str(label+1)+line[1:])
        tf.close()



def tokenize(sents, wd2idx):
    tokenized_sents = []
    wd2idx['<pad>'] = 0
    wd2idx['<unk>'] = 1
    idx = 2
    for sent in sents:
        tokenized_sent = word_tokenize(sent)
        tokenized_sents.append(tokenized_sent)
        for token in tokenized_sent:
            if token not in wd2idx:
                wd2idx[token] = idx
                idx += 1
    return tokenized_sents, wd2idx

def encode(tokenized_sents, wd2idx):
    input_ids = []
    for tokenized_sent in tokenized_sents:
        # tokenized_sent += ['<pad>']*(max_len - len(tokenized_sent))
        input_id = [wd2idx[token] for token in tokenized_sent]
        input_ids.append(input_id)
    return np.array(input_ids)

def load_prevec(wd2idx, filepath):
    fprevec = open(filepath, 'r')
    dim = int(fprevec.readline().split()[1])
    embeddings = np.random.uniform(-0.25, 0.25, (len(wd2idx), dim))
    count = 0
    for wdembd in tqdm_notebook(fprevec):
        wd = wdembd.rstrip().split(' ')[0]
        embd = wdembd.rstrip().split(' ')[1:]
        if wd in wd2idx:
            count += 1
            embeddings[wd2idx[wd]] = np.array(embd, dtype=np.float32)
    return embeddings

def collate_fn(batch):
    token_idx = list(map(lambda x: x[0], batch))
    tag_idx = list(map(lambda x: x[1], batch))
    max_length = max(len(row) for row in token_idx)
    x_padded = np.array([row + [0] * (max_length - len(row)) for row in token_idx])
    return torch.tensor(x_padded), torch.tensor(tag_idx)

class myDataset(Dataset):
    def __init__(self, inputs, labels):
        self.inputs = inputs
        self.labels = labels

    def __len__(self):
        return len(self.labels)

    def __getitem__(self, idx):
        return (self.inputs[idx], self.labels[idx])


def data_loader(train_inputs, val_inputs, train_labels, val_labels, batch_size=64):

    #torch.tensor(train_inputs)
    #train_inputs, val_inputs, train_labels, val_labels =  tuple(torch.tensor(data) for data in [train_inputs, val_inputs, train_labels, val_labels])
    
    train_data = myDataset(train_inputs, train_labels)
    train_sampler = RandomSampler(train_data)
    train_dataloader = DataLoader(train_data, sampler=train_sampler, batch_size=batch_size, num_workers=8, collate_fn=collate_fn)
    
    val_data = myDataset(val_inputs, val_labels)
    val_sampler = SequentialSampler(val_data)
    val_dataloader = DataLoader(val_data, sampler=val_sampler, batch_size=batch_size, collate_fn=collate_fn)

    return train_dataloader, val_dataloader

def get_dataloader(filepath, devpath, prepath, batch_size):
    wd2idx = {}
    labels, texts = load_data(filepath=filepath)
    dlabels, dtexts = load_data(filepath=devpath)

    tokenized_sents, wd2idx = tokenize(texts, wd2idx=wd2idx)
    dtokenized_sents, wd2idx = tokenize(dtexts, wd2idx=wd2idx)

    input_ids = encode(tokenized_sents, wd2idx)
    dinput_ids = encode(dtokenized_sents, wd2idx)

    embeddings = load_prevec(wd2idx, prepath)
    embeddings = torch.tensor(embeddings)

    train_inputs, val_inputs, train_labels, val_labels = input_ids, dinput_ids, labels, dlabels
    train_dataloader, val_dataloader = data_loader(train_inputs, val_inputs, train_labels, val_labels, batch_size=batch_size)
    return wd2idx, embeddings, train_dataloader, val_dataloader