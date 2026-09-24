import cv2
import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image

class GradCAM:
    """
    Gradient-weighted Class Activation Mapping (Grad-CAM)
    Generates explainability heatmaps targeting the final convolutional layer
    of the ResNet50 classifier to highlight key cellular features.
    """
    def __init__(self, model, target_layer):
        self.model = model
        self.target_layer = target_layer
        self.gradients = None
        self.activations = None

        # Register forward and backward hooks
        self.forward_handle = self.target_layer.register_forward_hook(self.save_activations)
        self.backward_handle = self.target_layer.register_full_backward_hook(self.save_gradients)

    def remove_hooks(self):
        if hasattr(self, 'forward_handle') and self.forward_handle:
            self.forward_handle.remove()
        if hasattr(self, 'backward_handle') and self.backward_handle:
            self.backward_handle.remove()

    def save_activations(self, module, input, output):
        self.activations = output.detach()

    def save_gradients(self, module, grad_input, grad_output):
        self.gradients = grad_output[0].detach()

    def generate_heatmap(self, input_tensor, target_class_idx=None):
        self.model.zero_grad()
        output = self.model(input_tensor)

        if target_class_idx is None:
            target_class_idx = torch.argmax(output, dim=1).item()

        score = output[0, target_class_idx]
        score.backward()

        # Global average pooling of gradients
        pooled_gradients = torch.mean(self.gradients, dim=[0, 2, 3])
        activations = self.activations[0]

        # Weight activation maps with pooled gradients
        for i in range(activations.shape[0]):
            activations[i, :, :] *= pooled_gradients[i]

        heatmap = torch.mean(activations, dim=0).cpu().numpy()
        heatmap = np.maximum(heatmap, 0)
        
        if np.max(heatmap) > 0:
            heatmap /= np.max(heatmap)

        return heatmap, target_class_idx

    def overlay_heatmap(self, heatmap, original_cv2_img, alpha=0.5):
        """
        Resize heatmap to match image size, apply JET colormap, and blend with original image.
        Returns BGR blended image and standalone RGB colormap heatmap.
        """
        h, w = original_cv2_img.shape[:2]
        resized_heatmap = cv2.resize(heatmap, (w, h))
        
        # Convert to 0-255 uint8
        heatmap_uint8 = np.uint8(255 * resized_heatmap)
        
        # Apply JET colormap (blue = low activation, red/yellow = high activation)
        colormap = cv2.applyColorMap(heatmap_uint8, cv2.COLORMAP_JET)
        
        # Superimpose colormap on original microscopy image
        blended = cv2.addWeighted(original_cv2_img, 1.0 - alpha, colormap, alpha, 0)
        
        return blended, colormap
