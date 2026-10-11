def pytorch_call(input,min=None,max=None):
  return torch.clip(input,min,max)