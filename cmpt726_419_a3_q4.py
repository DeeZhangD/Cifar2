# -*- coding: utf-8 -*-
"""CMPT726_419_A3_Q4.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1RcawICyHSDej3PivMWHCftgogs-yKp1O

# **CMPT 726/419 A3 Q4: Neural Networks in PyTorch**

Do not edit any cells until told to do so—the ones directly below should not be changed so you can access the required data and model for this problem.
"""

from tqdm.notebook import tqdm
import csv

import torch
import torch.nn as nn
from torch.optim import Adam, SGD
from torch.utils.data import Dataset, DataLoader, Subset
from torch.optim.lr_scheduler import CosineAnnealingLR

from torchvision import transforms
from torchvision.datasets import CIFAR10

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

class XYDataset(Dataset):
    """A basic dataset where the underlying data is a list of (x,y) tuples. Data
    returned from the dataset should be a (transform(x), y) tuple.
    Args:
    source      -- a list of (x,y) data samples
    transform   -- a torchvision.transforms transform
    """
    def __init__(self, source, transform=transforms.ToTensor()):
        super(XYDataset, self).__init__()
        self.source = source
        self.transform = transform

    def __len__(self): return len(self.source)
    
    def __getitem__(self, idx):
        x,y = self.source[idx]
        return self.transform(x), y

def build_dataset():
    """Returns the subset of the CIFAR-10 dataset containing only horses and
    deer, with the labels for each class modified to zero and one respectively.
    """
    transform = transforms.Compose([
        transforms.RandomHorizontalFlip(),
        transforms.RandomResizedCrop(32, scale=(0.75, 1.0)),
        transforms.ToTensor()])

    data = CIFAR10(root=".", train=True, download=True)
    data = [(x, (0 if y == 2 else 1)) for x,y in data if y in {2, 5}]
    return XYDataset(data, transform=transform)

def generate_test_predictions(model):
    """Generates test predictions using [model]."""
    data_te = torch.load("cifar2_te.pt")
    loader = DataLoader(data_te, batch_size=128, num_workers=6, shuffle=False)
    preds = []
    with torch.no_grad():
        for x,_ in loader:
            fx = model(x.to(device))
            preds += (fx > .5).float().view(-1).cpu().tolist()

    with open("test_predictions.csv", "w+") as f:
        writer = csv.writer(f)
        writer.writerow(["Id", "Category"])
        for idx,p in enumerate(preds):
            writer.writerow([str(idx), str(int(p))])
    tqdm.write("Wrote model predictions to test_predictions.csv")

class NN(nn.Module):
    """A simple ConvNet for binary classification."""
    def __init__(self):
        super(NN, self).__init__()
        self.c1 = nn.Conv2d(3, 32, kernel_size=3)
        self.c2 = nn.Conv2d(32, 32, kernel_size=3)
        self.fc = nn.Linear(25088, 1)
        self.relu = nn.ReLU()
        self.sigmoid = nn.Sigmoid()

    def forward(self, x):
        bs = len(x)
        fx = self.c1(x)
        fx = self.relu(fx)
        fx = self.c2(fx)
        fx = self.relu(fx)
        fx = fx.view(bs, -1)
        fx = self.fc(fx)
        fx = self.sigmoid(fx)
        return fx.view(-1)

"""
### ----- EDIT NO CODE ABOVE THIS CELL -----
### ----- EDIT CODE BENEATH THIS CELL -----



"""

def validate(model, loader):
    """Returns a (acc_val, loss_val) tuple, where [acc_val] and [loss_val] are
    respectively the validation accuracy and loss of [model] on the data in
    [loader].

    Args:
    model   -- a model, already moved onto the GPU
    loader  -- a DataLoader over validation data
    """
    
    acc_val, loss_val = 0, 0
    loss_fn = nn.BCELoss(reduction="mean")
    ##### YOUR CODE STARTS HERE (redefine [acc_val] and [loss_val] somewhere) ##
    with torch.no_grad():
      correct = 0
      total = 0
      for data in tqdm(loader):
        images, labels  = data
        outputs = model(images)

        preds = []
        preds = (outputs > .5).int().view(-1).cpu().tolist()

        get_tensor = []
        for i in labels:
          get_tensor.append(i.item())
        
        
        for (i,j) in zip(preds,get_tensor):
          if i == j:
            correct+=1
        loss = loss_fn(outputs, labels.float())
        total += labels.size(0)
        loss_val += loss.item()
        #print(outputs.data)
        #predicted = torch.max(outputs)
        #print(predicted)
        #acc_val += torch.eq(predicted,labels).sum().item()
      acc_val = correct/ total *100 
      loss_val /= len(loader) 
    ##### YOUR CODE ENDS HERE   ################################################
    return acc_val, loss_val

def one_epoch(model, optimizer, loader):
    """Returns a (model, optimizer, avg_loss) tuple after training [model] on
    the data in [loader] for one epoch.

    Args:
    model       -- the neural network to train, already moved onto the GPU
    optimizer   -- the optimizer used to train [model]
    loader      -- a DataLoader with data to train [model] on

    Returns
    model       -- [model] after training for one epoch
    optimizer   -- the optimizer used to train [model]
    avg_loss    -- the average loss of [model] on each batch of [loader]
    """
    
    avg_loss = 0
    loss_fn = nn.BCELoss(reduction="mean")
    ##### YOUR CODE STARTS HERE (redefine [avg_loss] somewhere) ################
    #model.train()
   
    for data in loader:
      inputs, labels = data # get list of [batch,labels]
      inputs, labels = inputs.to(device), labels.to(device) #send inputs and targets to the GPU 
      
      optimizer.zero_grad() # zero the parameter gradients
      outputs = model(inputs)
      #loss, logits = model(batch, labels=labels)
      loss = loss_fn(outputs, labels.float())
      loss.backward()#back
      optimizer.step()#update
      
      avg_loss += loss.item() 
    avg_loss /= len(loader)
    
    ##### YOUR CODE ENDS HERE   ################################################
    return model, optimizer, avg_loss

"""Next, write a function to take a set of hyperparameters and return a `(model, acc_val)` tuple with the model having been trained with the hyperparameters and `acc_val` being the validation accuracy of the model after training.

Note the `**kwargs` in the function definition. This means that the function can take
any number of keyword arguments as input, and they will be accessible inside the function despite not being specified in the function definition, and they will be accessible within dictionary named `kwargs` inside the function.

_By passing in arguments this way, you can define whatever hyperparameters you want to use and pass them in!_
"""

def train_and_validate(data_tr, data_val, **hyperparameters):
    """Returns a (model, acc_val) tuple where [model] is a neural
    network of the NN class trained with [hyperparameters] on [data_tr] and 
    validated on [data_val], and [acc_val] is the validation accuracy of the
    model after training.

    Args:
    data_tr         -- Dataset of training data
    data_val        -- Dataset of validation data
    hyperparameters -- kwarg dictionary of hyperparameters
    """
    model, acc_val = NN(), 0
    ##### YOUR CODE STARTS HERE (redefine [model] and [acc_val] somewhere) #####
   
    optimizer = SGD(model.parameters(),hyperparameters["LR"],hyperparameters["momentum"],hyperparameters["Weight_decay"])

    batch_size = hyperparameters["Batch_size"]
    trainloader = torch.utils.data.DataLoader(data_tr, batch_size=batch_size, shuffle=True, num_workers=2)
   
    for epoch in range(hyperparameters["NUM_EPOCH"]):
      model, optimizer, avg_loss = one_epoch(model, optimizer, trainloader)
      #print("Average LOSS at epoch", epoch+1 ,': ', avg_loss)
      model.to(device)

    valloader = torch.utils.data.DataLoader(data_val, batch_size=batch_size,shuffle=False, num_workers=2)
    acc_val,loss_val = validate(model, valloader)
    ##### YOUR CODE ENDS HERE   ################################################
    return model, acc_val

################################################################################
# Do hyperparameter search using train_and_validate(). You should call
# generate_test_predictions() on the model you eventually compute as best to 
# get test predictions to submit to Kaggle. You should also split off some of
# the 
data = build_dataset()  # You should use this data for training and validation
best_model = NN()       # You should at some point name the model you want to
                        # generate test predictions with `best_model`
                        
##### YOUR CODE STARTS HERE ####################################################

#loader = torch.utils.data.DataLoader(data, batch_size=128,shuffle=True, num_workers=2)
#for i in data:
#  print(i)
#data_val = torch.split(data,2,0)
data_tr_size = int(len(data)*0.7) # set 3:2 for training size: validayion size 
data_val_size = len(data) - data_tr_size
data_tr, data_val = torch.utils.data.random_split(data,[data_tr_size , data_val_size]) # split 
# hyperparameters = {'NUM_EPOCH':20,'LR':0.01,'momentum':0.9,"Weight_decay":10e-6,"Batch_size":50}
# acc_val = 0.0 
# best_model, acc_val = train_and_validate(data_tr, data_val, **hyperparameters)
# print("epcho ############################## 1 \n","hyperparameters: ",hyperparameters, '\n',"Accuracy value: ",acc_val,'%')

# acc_val = 0.0 
# hyperparameters = {'NUM_EPOCH':20,'LR':0.01,'momentum':0.9,"Weight_decay":10e-6,"Batch_size":128}
# best_model,acc_val = train_and_validate(data_tr,data_val,**hyperparameters)
# print("epcho ############################## 2 \n","hyperparameters: ",hyperparameters, '\n',"Accuracy value: ",acc_val,'%')
# acc_val = 0.0 
# hyperparameters = {'NUM_EPOCH':100,'LR':0.01,'momentum':0.9,"Weight_decay":10e-6,"Batch_size":128}
# best_model,acc_val = train_and_validate(data_tr,data_val,**hyperparameters)
# print("epcho ############################ 3 \n","hyperparameters: ",hyperparameters, '\n',"Accuracy value: ",acc_val,'%')
# acc_val = 0.0 
# hyperparameters = {'NUM_EPOCH':120,'LR':0.001,'momentum':0.9,"Weight_decay":10e-6,"Batch_size":128}
# best_model,acc_val = train_and_validate(data_tr,data_val,**hyperparameters)
# print("epcho ############################ 3.5 \n","hyperparameters: ",hyperparameters, '\n',"Accuracy value: ",acc_val,'%')
# #81.83333333333334 % leaning rate decrease lead to less accuracy 
acc_val = 0.0 
hyperparameters = {'NUM_EPOCH':135,'LR':0.01,'momentum':0.9,"Weight_decay":10e-6,"Batch_size":128}
best_model,acc_val = train_and_validate(data_tr,data_val,**hyperparameters)
#print("epcho ############################ 4 \n","hyperparameters: ",hyperparameters, '\n',"Accuracy value: ",acc_val,'%')
#85.66666666666667 %


##### YOUR CODE ENDS HERE   ####################################################

generate_test_predictions(best_model)