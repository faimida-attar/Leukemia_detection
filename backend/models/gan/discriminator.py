import torch
import torch.nn as nn

class GANDiscriminator(nn.Module):
    """
    Discriminator network for adversarial training in microscopy image reconstruction (GAN + CBAM).
    Evaluates whether an image is a genuine high-resolution blood smear slide or a generated reconstruction.
    
    Structure:
    - 6 Conv2d + BatchNorm + LeakyReLU feature-extraction blocks (with strided downsampling)
    - Adaptive Average Pooling & Flattening
    - Fully Connected Linear layers outputting classification score/logit
    """
    def __init__(self, in_channels=3, use_sigmoid=False):
        super(GANDiscriminator, self).__init__()
        
        def conv_block(in_f, out_f, stride=1, normalize=True):
            layers = [nn.Conv2d(in_f, out_f, kernel_size=3, stride=stride, padding=1, bias=False)]
            if normalize:
                layers.append(nn.BatchNorm2d(out_f))
            layers.append(nn.LeakyReLU(0.2, inplace=True))
            return layers

        self.model = nn.Sequential(
            *conv_block(in_channels, 64, stride=1, normalize=False),  # layers 0, 1
            *conv_block(64, 64, stride=2),                             # layers 2, 3, 4
            *conv_block(64, 128, stride=1),                            # layers 5, 6, 7
            *conv_block(128, 128, stride=2),                           # layers 8, 9, 10
            *conv_block(128, 256, stride=1),                           # layers 11, 12, 13
            *conv_block(256, 256, stride=2),                           # layers 14, 15, 16
            nn.AdaptiveAvgPool2d(1),                                   # layer 17
            nn.Flatten(),                                              # layer 18
            nn.Linear(256, 1024),                                      # layer 19
            nn.LeakyReLU(0.2, inplace=True),                           # layer 20
            nn.Linear(1024, 1)                                         # layer 21
        )
        self.use_sigmoid = use_sigmoid
        self.sigmoid = nn.Sigmoid()

    def forward(self, x):
        out = self.model(x)
        if self.use_sigmoid:
            out = self.sigmoid(out)
        return out
