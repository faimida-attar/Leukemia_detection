import torch
import torch.nn as nn

class GANDiscriminator(nn.Module):
    """
    Discriminator network for adversarial training in microscopy image reconstruction.
    """
    def __init__(self, in_channels=3):
        super(GANDiscriminator, self).__init__()
        
        def conv_block(in_f, out_f, stride=1, normalize=True):
            layers = [nn.Conv2d(in_f, out_f, kernel_size=3, stride=stride, padding=1, bias=False)]
            if normalize:
                layers.append(nn.BatchNorm2d(out_f))
            layers.append(nn.LeakyReLU(0.2, inplace=True))
            return layers

        self.model = nn.Sequential(
            *conv_block(in_channels, 64, stride=1, normalize=False),
            *conv_block(64, 64, stride=2),
            *conv_block(64, 128, stride=1),
            *conv_block(128, 128, stride=2),
            *conv_block(128, 256, stride=1),
            *conv_block(256, 256, stride=2),
            nn.AdaptiveAvgPool2d(1),
            nn.Flatten(),
            nn.Linear(256, 1024),
            nn.LeakyReLU(0.2, inplace=True),
            nn.Linear(1024, 1),
            nn.Sigmoid()
        )

    def forward(self, x):
        return self.model(x)
