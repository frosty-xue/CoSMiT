def pytorch_call(t, clip_value_min, clip_value_max):
    clip_value_min = torch.max(clip_value_min, clip_value_max.new_ones(1) * float('-inf'))
    clip_value_max = torch.max(clip_value_min, clip_value_max)
    return torch.clamp(t, clip_value_min, clip_value_max)