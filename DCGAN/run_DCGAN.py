# -*- coding: utf-8 -*-
# @Author: aaronlai

import torch
import torch.optim as optim
import torchvision
import torchvision.transforms as transforms
import numpy as np

from torch.autograd import Variable
from DCGAN import DCGAN_Discriminator, DCGAN_Generator


def load_dataset(batch_size=10, download=True):
    """
    The output of torchvision datasets are PILImage images of range [0, 1].
    Transform them to Tensors of normalized range [-1, 1]
    """
    transform = transforms.Compose([transforms.ToTensor(),
                                    transforms.Normalize((0.5, 0.5, 0.5),
                                                         (0.5, 0.5, 0.5))])
    trainset = torchvision.datasets.MNIST(root='../data', train=True,
                                          download=download,
                                          transform=transform)
    trainloader = torch.utils.data.DataLoader(trainset, batch_size=batch_size,
                                              shuffle=True, num_workers=2)

    testset = torchvision.datasets.MNIST(root='../data', train=False,
                                         download=download,
                                         transform=transform)
    testloader = torch.utils.data.DataLoader(testset, batch_size=batch_size,
                                             shuffle=False, num_workers=2)

    return trainloader, testloader


def gen_noise(n_instance, n_dim=2):
    """generate 2-dim uniform random noise"""
    return torch.Tensor(np.random.uniform(low=-1.0, high=1.0,
                                          size=(n_instance, n_dim)))


def train_DCGAN(Dis_model, Gen_model, D_criterion, G_criterion, D_optimizer,
                G_optimizer, trainloader, n_epoch, batch_size, noise_dim,
                n_update_dis=1, n_update_gen=1, use_gpu=False, print_every=10,
                update_max=None):
    """train DCGAN and print out the losses for D and G"""
    for epoch in range(n_epoch):

        D_running_loss = 0.0
        G_running_loss = 0.0

        for i, data in enumerate(trainloader, 0):
            # get the inputs from true distribution
            true_inputs, _ = data
            if use_gpu:
                true_inputs = true_inputs.cuda()
            true_inputs = Variable(true_inputs)

            # get the inputs from the generator
            noises = gen_noise(batch_size, n_dim=noise_dim)
            if use_gpu:
                noises = noises.cuda()
            fake_inputs = Gen_model(Variable(noises))
            inputs = torch.cat([true_inputs, fake_inputs])

            # get the labels
            labels = np.zeros(2 * batch_size)
            labels[:batch_size] = 1
            labels = torch.from_numpy(labels.astype(np.float32))
            if use_gpu:
                labels = labels.cuda()
            labels = Variable(labels)

            # Discriminator
            D_optimizer.zero_grad()
            outputs = Dis_model(inputs)
            D_loss = D_criterion(outputs[:, 0], labels)
            if i % n_update_dis == 0:
                D_loss.backward(retain_variables=True)
                D_optimizer.step()

            # Generator
            if i % n_update_gen == 0:
                G_optimizer.zero_grad()
                G_loss = G_criterion(outputs[batch_size:, 0],
                                     labels[:batch_size])
                G_loss.backward()
                G_optimizer.step()

            # print statistics
            D_running_loss += D_loss.data[0]
            G_running_loss += G_loss.data[0]
            if i % print_every == (print_every - 1):
                print('[%d, %5d] D loss: %.3f ; G loss: %.3f' %
                      (epoch+1, i+1, D_running_loss / print_every,
                       G_running_loss / print_every))
                D_running_loss = 0.0
                G_running_loss = 0.0

            if update_max and i > update_max:
                break

    print('Finished Training')


def run_DCGAN(n_epoch=2, batch_size=50, use_gpu=False, dis_lr=1e-5,
              gen_lr=1e-4, n_update_dis=1, n_update_gen=1, noise_dim=10,
              D_featmap_dim=512, G_featmap_dim=1024, n_channel=1,
              update_max=None):
    # loading data
    trainloader, testloader = load_dataset(batch_size=batch_size)

    # initialize models
    Dis_model = DCGAN_Discriminator(featmap_dim=D_featmap_dim,
                                    n_channel=n_channel)
    Gen_model = DCGAN_Generator(featmap_dim=G_featmap_dim, n_channel=n_channel,
                                noise_dim=noise_dim)

    if use_gpu:
        Dis_model = Dis_model.cuda()
        Gen_model = Gen_model.cuda()

    # assign loss function and optimizer (Adam) to D and G
    D_criterion = torch.nn.BCELoss()
    D_optimizer = optim.Adam(Dis_model.parameters(), lr=dis_lr,
                             betas=(0.5, 0.999))

    G_criterion = torch.nn.BCELoss()
    G_optimizer = optim.Adam(Gen_model.parameters(), lr=gen_lr,
                             betas=(0.5, 0.999))

    train_DCGAN(Dis_model, Gen_model, D_criterion, G_criterion, D_optimizer,
                G_optimizer, trainloader, n_epoch, batch_size, noise_dim,
                n_update_dis, n_update_gen, update_max=update_max)


if __name__ == '__main__':
    run_DCGAN(D_featmap_dim=64, G_featmap_dim=128)
