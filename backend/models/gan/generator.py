import torch
import torch.nn as nn
from models.cbam.cbam_module import CBAM

class ResidualCBAMBlock(nn.Module):
    """
    Residual Block enhanced with Convolutional Block Attention Module (CBAM)
    """
    def __init__(self, channels):
        super(ResidualCBAMBlock, self).__init__()
        self.conv1 = nn.Conv2d(channels, channels, kernel_size=3, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(channels)
        self.relu = nn.ReLU(inplace=True)
        self.conv2 = nn.Conv2d(channels, channels, kernel_size=3, padding=1, bias=False)
        self.bn2 = nn.BatchNorm2d(channels)
        self.cbam = CBAM(channels, ratio=16)

    def forward(self, x):
        residual = x
        out = self.conv1(x)
        out = self.bn1(out)
        out = self.relu(out)
        out = self.conv2(out)
        out = self.bn2(out)
        out = self.cbam(out)
        return out + residual


class GANCBAMGenerator(nn.Module):
    """
    Reconstruction Generator with CBAM Attention for Compressed Microscopy Images.
    Restores high-frequency features, nucleus details, and cell boundary sharpness
    lost during lossy JPEG compression.
    """
    def __init__(self, in_channels=3, out_channels=3, num_res_blocks=4):
        super(GANCBAMGenerator, self).__init__()
        
        # Initial Feature Extraction Layer
        self.initial_conv = nn.Sequential(
            nn.Conv2d(in_channels, 64, kernel_size=7, padding=3, bias=False),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True)
        )
        
        # Residual Blocks with CBAM Attention
        res_blocks = []
        for _ in range(num_res_blocks):
            res_blocks.append(ResidualCBAMBlock(64))
        self.res_blocks = nn.Sequential(*res_blocks)
        
        # Reconstruction & Refinement Layer
        self.refine_conv = nn.Sequential(
            nn.Conv2d(64, 64, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True)
        )
        
        # Output Reconstruction Layer (returns RGB normalized [0, 1])
        self.final_conv = nn.Sequential(
            nn.Conv2d(64, out_channels, kernel_size=7, padding=3),
            nn.Sigmoid()
        )

    def forward(self, x):
        initial = self.initial_conv(x)
        features = self.res_blocks(initial)
        refined = self.refine_conv(features)
        reconstruction = self.final_conv(refined + initial)
        return reconstruction
