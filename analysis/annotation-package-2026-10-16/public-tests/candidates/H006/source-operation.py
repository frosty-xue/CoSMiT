def pytorch_call(input,dim):
  return torch.cumprod(input,dim)