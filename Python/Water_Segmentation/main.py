from roboflow import Roboflow
rf = Roboflow(api_key="uqaeruMcDIkdXyVudaZi")
project = rf.workspace("tf-adddz").project("airsim-water-segmentation")
version = project.version(1)
dataset = version.download("png-mask-semantic")
                

import torch
x = torch.rand(5, 3)
print(x)
torch.cuda.is_available()