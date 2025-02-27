from __future__ import print_function
import os
import argparse
import torch
import torch.nn as nn
import torch.nn.functional as F
import torchvision
import torch.optim as optim
from torchvision import datasets, transforms
import numpy as np
from models.vggnet import *
from models.resnet import *
from models.densenet import *
from models.mynet import *

parser = argparse.ArgumentParser(description='PyTorch CIFAR Standard Training')
parser.add_argument('--batch-size', type=int, default=128, metavar='N',
                    help='input batch size for training (default: 128)')
parser.add_argument('--test-batch-size', type=int, default=128, metavar='N',
                    help='input batch size for testing (default: 128)')
parser.add_argument('--epochs', type=int, default=300, metavar='N',
                    help='number of epochs to train')
parser.add_argument('--weight-decay', '--wd', default=2e-4,
                    type=float, metavar='W')
parser.add_argument('--lr', type=float, default=0.1, metavar='LR',
                    help='learning rate')
parser.add_argument('--momentum', type=float, default=0.9, metavar='M',
                    help='SGD momentum')
parser.add_argument('--no-cuda', action='store_true', default=False,
                    help='disables CUDA training')
parser.add_argument('--epsilon', type=float, default=0.031,
                    help='perturbation')
parser.add_argument('--num-steps', type=int, default=10,
                    help='perturb number of steps')
parser.add_argument('--step-size', type=float, default=0.007,
                    help='perturb step size')
parser.add_argument('--beta', type=float, default=6.0,
                    help='regularization, i.e., 1/lambda in TRADES')
parser.add_argument('--seed', type=int, default=1, metavar='S',
                    help='random seed (default: 1)')
parser.add_argument('--log-interval', type=int, default=100, metavar='N',
                    help='how many batches to wait before logging training status')
parser.add_argument('--model', default='resnet18',
                    help='model name for training')
parser.add_argument('--dataset', default='cifar10', help='use what dataset')
parser.add_argument('--save-freq', '-s', default=1, type=int, metavar='N',
                    help='save frequency')

args = parser.parse_args()

# settings
model_dir='./model-'+args.model+'-'+args.dataset
    
if not os.path.exists(model_dir):
    os.makedirs(model_dir)
use_cuda = not args.no_cuda and torch.cuda.is_available()
torch.manual_seed(args.seed)
device = torch.device("cuda" if use_cuda else "cpu")
kwargs = {'num_workers': 1, 'pin_memory': True} if use_cuda else {}

# setup data loader
if args.dataset=='cifar10':
    transform_train = transforms.Compose([
        transforms.RandomCrop(32, padding=4),
        transforms.RandomHorizontalFlip(),
        transforms.ToTensor(),
    ])
elif args.dataset=='fashionminist':
        transform_train = transforms.Compose([
        transforms.ToTensor(),
    ])
        
transform_test = transforms.Compose([
    transforms.ToTensor(),
])
resize_transform = transforms.Compose([transforms.Resize((32, 32)),
                                       transforms.ToTensor()])
if args.dataset=='cifar10': 
    trainset = torchvision.datasets.CIFAR10(root='./data', train=True, download=True, transform=transform_train)
    train_loader = torch.utils.data.DataLoader(trainset, batch_size=args.batch_size, shuffle=True, **kwargs)
    testset = torchvision.datasets.CIFAR10(root='./data', train=False, download=True, transform=transform_test)
    test_loader = torch.utils.data.DataLoader(testset, batch_size=args.test_batch_size, shuffle=False, **kwargs)
elif args.dataset=='fashionminist' and args.model!='densenet121':
    trainset = torchvision.datasets.FashionMNIST(root='./data', train=True, download=True, transform=transform_train)
    train_loader = torch.utils.data.DataLoader(trainset, batch_size=args.batch_size, shuffle=True, **kwargs)
    testset = torchvision.datasets.FashionMNIST(root='./data', train=False, download=True, transform=transform_test)
    test_loader = torch.utils.data.DataLoader(testset, batch_size=args.test_batch_size, shuffle=False, **kwargs)    
elif args.dataset=='fashionminist' and args.model=='densenet121':
    trainset = torchvision.datasets.FashionMNIST(root='./data', train=True, download=True, transform=resize_transform)
    train_loader = torch.utils.data.DataLoader(trainset, batch_size=args.batch_size, shuffle=True, **kwargs)
    testset = torchvision.datasets.FashionMNIST(root='./data', train=False, download=True, transform=resize_transform)
    test_loader = torch.utils.data.DataLoader(testset, batch_size=args.test_batch_size, shuffle=False, **kwargs)
    
def train(args, model, device, train_loader, optimizer, epoch):
    model.train()
    for batch_idx, (data, target) in enumerate(train_loader):
        if args.dataset=='fashionminist' and args.model!='densenet121':              
            # 因为FashionMNIST输入为单通道图片，需要转换为三通道
            data = np.array(data)
            data = data.transpose((1, 0, 2, 3))  # array 转置
            data = np.concatenate((data, data, data), axis=0)  # 维度拼接
            data = data.transpose((1, 0, 2, 3))  # array 转置回来
            data = torch.tensor(data)  # 将 numpy 数据格式转为 tensor         
        data, target = data.to(device), target.to(device)

        optimizer.zero_grad()
        output = model(data)
        loss = F.cross_entropy(output,target)
        loss.backward()
        optimizer.step()

        # print progress
        if batch_idx % args.log_interval == 0:
            print('Train Epoch: {} [{}/{} ({:.0f}%)]\tLoss: {:.6f}'.format(
                epoch, batch_idx * len(data), len(train_loader.dataset),
                       100. * batch_idx / len(train_loader), loss.item()))

def eval_train(model, device, train_loader):
    model.eval()
    train_loss = 0
    correct = 0
    with torch.no_grad():
        for data, target in train_loader:
            if args.dataset=='fashionminist' and args.model!='densenet121':              
                # 因为FashionMNIST输入为单通道图片，需要转换为三通道
                data = np.array(data)
                data = data.transpose((1, 0, 2, 3))  # array 转置
                data = np.concatenate((data, data, data), axis=0)  # 维度拼接
                data = data.transpose((1, 0, 2, 3))  # array 转置回来
                data = torch.tensor(data)  # 将 numpy 数据格式转为 tensor         
            data, target = data.to(device), target.to(device)
            output = model(data)
            train_loss += F.cross_entropy(output, target, size_average=False).item()
            pred = output.max(1, keepdim=True)[1]
            correct += pred.eq(target.view_as(pred)).sum().item()
    train_loss /= len(train_loader.dataset)
    print('Training: Average loss: {:.4f}, Accuracy: {}/{} ({:.0f}%)'.format(
        train_loss, correct, len(train_loader.dataset),
        100. * correct / len(train_loader.dataset)))
    training_accuracy = correct / len(train_loader.dataset)
    return train_loss, training_accuracy


def eval_test(model, device, test_loader):
    model.eval()
    test_loss = 0
    correct = 0
    with torch.no_grad():
        for data, target in test_loader:
            if args.dataset=='fashionminist' and args.model!='densenet121':              
                # 因为FashionMNIST输入为单通道图片，需要转换为三通道
                data = np.array(data)
                data = data.transpose((1, 0, 2, 3))  # array 转置
                data = np.concatenate((data, data, data), axis=0)  # 维度拼接
                data = data.transpose((1, 0, 2, 3))  # array 转置回来
                data = torch.tensor(data)  # 将 numpy 数据格式转为 tensor 
            data, target = data.to(device), target.to(device)
            output = model(data)
            test_loss += F.cross_entropy(output, target, size_average=False).item()
            pred = output.max(1, keepdim=True)[1]
            correct += pred.eq(target.view_as(pred)).sum().item()
    test_loss /= len(test_loader.dataset)
    print('Test: Average loss: {:.4f}, Accuracy: {}/{} ({:.0f}%)'.format(
        test_loss, correct, len(test_loader.dataset),
        100. * correct / len(test_loader.dataset)))
    test_accuracy = correct / len(test_loader.dataset)
    return test_loss, test_accuracy


def adjust_learning_rate(optimizer, epoch):
    """decrease the learning rate"""
    lr = args.lr
    if epoch >= 75:
        lr = args.lr * 0.1
    if epoch >= 90:
        lr = args.lr * 0.01
    if epoch >= 100:
        lr = args.lr * 0.001
    for param_group in optimizer.param_groups:
        param_group['lr'] = lr


def main():
    # init model, ResNet18() or vgg16_bn() and so on
    if args.model=='vgg16':
        model = vgg16_bn().to(device)
    elif args.model=='resnet18':
        model = ResNet18().to(device)
    elif args.model=='resnet34':
        model = ResNet34().to(device)
    elif args.model=='densenet121':
        model = DenseNet121(num_classes=10, grayscale=False).to(device)
    elif args.model=='smallcnn':
        model = SmallCNN().to(device)
        
    optimizer = optim.SGD(model.parameters(), lr=args.lr, momentum=args.momentum, weight_decay=args.weight_decay)

    for epoch in range(1, args.epochs + 1):
        # adjust learning rate for SGD
        adjust_learning_rate(optimizer, epoch)

        # adversarial training
        train(args, model, device, train_loader, optimizer, epoch)

        # evaluation on natural examples
        print('================================================================')
        eval_train(model, device, train_loader)
        eval_test(model, device, test_loader)
        print('================================================================')

        # save checkpoint
        if epoch % args.save_freq == 0:
            torch.save(model.state_dict(),
                       os.path.join(model_dir, 'Standard-'+args.dataset+'-model-'+args.model+'-epoch{}.pt'.format(epoch)))
            torch.save(optimizer.state_dict(),
                       os.path.join(model_dir, 'opt-Standard-'+args.dataset+'-'+args.model+'-checkpoint_epoch{}.tar'.format(epoch)))


if __name__ == '__main__':
    main()
